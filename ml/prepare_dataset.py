"""Preparação do dataset de Machine Learning — FarmTech Solutions (Fase 4, Cap. 1).

Este módulo lê o CSV bruto de leituras dos pivôs de irrigação
(``data/raw/seed_data.csv``), aplica engenharia de atributos e ENGENHEIRA
três alvos de regressão SIMULADOS por heurística agronômica, salvando o
resultado em ``data/processed/dataset_ml.parquet``.

TRANSPARÊNCIA (importante):
    Os alvos ``rendimento``, ``volume_irrigacao`` e ``necessidade_fertilizacao``
    NÃO são medições reais coletadas em campo. Eles são SIMULADOS a partir de
    funções heurísticas agronômicas (curvas de resposta tipo "sino" em torno de
    valores ótimos de umidade, pH, temperatura e NPK), com adição de ruído
    gaussiano para evitar um problema perfeitamente determinístico. O objetivo é
    didático: permitir treinar e avaliar modelos de regressão sobre relações
    plausíveis, sem disponibilidade de safras rotuladas reais.

    Já os alvos ``umidade`` e ``ph`` são valores REAIS, presentes no dataset
    original (medidos pelos sensores), e por isso não são engenheirados aqui.

Autor: Jefferson Gonçalves Lemos — RM 572399
Disciplina: Inteligência Artificial — FIAP
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Caminhos (relativos a este arquivo, via pathlib)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_CSV = BASE_DIR / "data" / "raw" / "seed_data.csv"
PROCESSED_PARQUET = BASE_DIR / "data" / "processed" / "dataset_ml.parquet"

# ---------------------------------------------------------------------------
# Constantes agronômicas (heurística para engenharia dos alvos)
# ---------------------------------------------------------------------------
UMIDADE_OPT, UMIDADE_SD = 62.5, 12.0
PH_OPT, PH_SD = 6.5, 0.6
TEMP_OPT, TEMP_SD = 25.0, 7.0
N_IDEAL, P_IDEAL, K_IDEAL = 70.0, 60.0, 60.0
NPK_SD = 25.0
UMIDADE_ALVO_IRRIGACAO = 65.0

# Gerador de números aleatórios reprodutível (numpy seed 42)
rng = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def bell(x, opt, sd):
    """Curva de resposta gaussiana (sino) normalizada em 0..1.

    Retorna ``exp(-0.5 * ((x - opt) / sd) ** 2)``, valendo 1 quando ``x == opt``
    e decaindo suavemente conforme ``x`` se afasta do ótimo ``opt``. Aceita
    escalares ou arrays do numpy.
    """
    x = np.asarray(x, dtype=float)
    return np.exp(-0.5 * ((x - opt) / sd) ** 2)


def relu(x):
    """ReLU: ``max(0, x)``, aplicada elemento a elemento."""
    return np.maximum(0.0, np.asarray(x, dtype=float))


# ---------------------------------------------------------------------------
# Pipeline de preparação
# ---------------------------------------------------------------------------
def load_raw(csv_path: Path = RAW_CSV) -> pd.DataFrame:
    """Lê o CSV bruto e normaliza os nomes das colunas para minúsculo."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Deriva atributos temporais e binários a partir das colunas brutas."""
    df = df.copy()

    # Parse do timestamp e derivação de hora e dia da semana
    df["capturado_em"] = pd.to_datetime(df["capturado_em"], errors="coerce")
    df["hora"] = df["capturado_em"].dt.hour
    df["dia_semana"] = df["capturado_em"].dt.dayofweek  # 0=segunda ... 6=domingo

    # Estado da bomba: ON -> 1, OFF -> 0
    df["estado_bomba_bin"] = (
        df["estado_bomba"].astype(str).str.strip().str.upper().eq("ON").astype(int)
    )

    return df


def engineer_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Engenheira (SIMULA) os três alvos por heurística agronômica.

    Aplica as fórmulas EXATAS do contrato do projeto, com ruído gaussiano
    reprodutível (rng seed 42).
    """
    df = df.copy()
    n = len(df)

    umidade = df["umidade"].to_numpy(dtype=float)
    ph = df["ph"].to_numpy(dtype=float)
    temperatura = df["temperatura"].to_numpy(dtype=float)
    n_val = df["n"].to_numpy(dtype=float)
    p_val = df["p"].to_numpy(dtype=float)
    k_val = df["k"].to_numpy(dtype=float)

    # --- rendimento (sacas/ha, 0..80) ---
    f_npk = np.mean(
        np.vstack(
            [
                bell(n_val, N_IDEAL, NPK_SD),
                bell(p_val, P_IDEAL, NPK_SD),
                bell(k_val, K_IDEAL, NPK_SD),
            ]
        ),
        axis=0,
    )
    rendimento = (
        80.0
        * bell(umidade, UMIDADE_OPT, UMIDADE_SD)
        * bell(ph, PH_OPT, PH_SD)
        * f_npk
        * bell(temperatura, TEMP_OPT, TEMP_SD)
        + rng.normal(0.0, 3.0, n)
    )
    df["rendimento"] = np.clip(rendimento, 0.0, 80.0)

    # --- volume_irrigacao (mm, 0..40) ---
    volume_irrigacao = (
        relu(UMIDADE_ALVO_IRRIGACAO - umidade) * 0.8
        + 0.15 * relu(temperatura - 20.0)
        + rng.normal(0.0, 1.5, n)
    )
    df["volume_irrigacao"] = np.clip(volume_irrigacao, 0.0, 40.0)

    # --- necessidade_fertilizacao (índice 0..100) ---
    necessidade_fertilizacao = (
        (relu(N_IDEAL - n_val) + relu(P_IDEAL - p_val) + relu(K_IDEAL - k_val))
        / (N_IDEAL + P_IDEAL + K_IDEAL)
        * 100.0
        + rng.normal(0.0, 3.0, n)
    )
    df["necessidade_fertilizacao"] = np.clip(necessidade_fertilizacao, 0.0, 100.0)

    return df


def prepare_dataset(
    csv_path: Path = RAW_CSV, out_path: Path = PROCESSED_PARQUET
) -> pd.DataFrame:
    """Executa o pipeline completo e salva o parquet processado."""
    df = load_raw(csv_path)
    df = engineer_features(df)
    df = engineer_targets(df)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    salvar_processado(df, out_path)

    return df


def salvar_processado(df: pd.DataFrame, out_path: Path = PROCESSED_PARQUET) -> Path:
    """Salva o dataset processado.

    Tenta gravar em Parquet (formato preferido). Se o ``pyarrow`` não estiver
    instalado no ambiente, faz fallback transparente para CSV (mesmo diretório,
    extensão ``.csv``), garantindo portabilidade entre máquinas.

    Returns:
        O caminho efetivamente escrito.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(out_path, engine="pyarrow", index=False)
        print(f"[OK] Dataset processado salvo em: {out_path}")
        return out_path
    except (ImportError, ValueError) as exc:  # pyarrow ausente → fallback CSV
        csv_path = out_path.with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        print(
            f"[AVISO] pyarrow indisponível ({exc.__class__.__name__}); "
            f"salvo em CSV: {csv_path}"
        )
        return csv_path


def ler_processado(parquet_path: Path = PROCESSED_PARQUET) -> pd.DataFrame:
    """Carrega o dataset processado aceitando Parquet OU CSV (fallback).

    Procura primeiro o ``.parquet``; se ausente ou se ``pyarrow`` não estiver
    instalado, usa o ``.csv`` irmão. Levanta ``FileNotFoundError`` se nenhum
    existir (instruindo a rodar ``prepare_dataset.py``).
    """
    parquet_path = Path(parquet_path)
    csv_path = parquet_path.with_suffix(".csv")
    if parquet_path.exists():
        try:
            return pd.read_parquet(parquet_path)
        except (ImportError, ValueError):
            pass  # pyarrow ausente → tenta CSV abaixo
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(
        f"Dataset processado não encontrado ({parquet_path} nem {csv_path}). "
        "Rode primeiro: python ml/prepare_dataset.py"
    )


def main() -> None:
    """Ponto de entrada de linha de comando."""
    print(f"Lendo CSV bruto: {RAW_CSV}")
    df = prepare_dataset()  # o caminho efetivo (parquet ou csv) é impresso em salvar_processado

    print(f"Linhas processadas: {len(df)}\n")

    targets = [
        "rendimento",
        "volume_irrigacao",
        "necessidade_fertilizacao",
        "umidade",
        "ph",
    ]
    print("Estatísticas descritivas dos alvos:")
    with pd.option_context("display.width", 120, "display.max_columns", None):
        print(df[targets].describe())

    print(
        "\nNota: rendimento, volume_irrigacao e necessidade_fertilizacao são "
        "SIMULADOS por heurística agronômica (transparência)."
    )


if __name__ == "__main__":
    main()
