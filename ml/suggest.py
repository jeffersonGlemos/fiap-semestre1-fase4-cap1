"""Geração de recomendações de manejo agrícola a partir das previsões dos modelos.

FarmTech Solutions — Fase 4, Capítulo 1 (Assistente Agrícola Inteligente).
Autor: Jefferson Gonçalves Lemos · RM 572399 · Inteligência Artificial — FIAP.

Este módulo é a camada de "tradução" entre os modelos de regressão treinados
(ml/train.py) e o gestor da fazenda: a partir de uma leitura de sensores, carrega
os modelos persistidos, prevê os alvos (rendimento, volume de irrigação,
necessidade de fertilização, umidade e pH) e converte essas previsões em
recomendações de manejo em linguagem natural (Português BR).

Esqueleto FUNCIONAL: as funções já operam de ponta a ponta desde que os modelos
existam em ``models/``. Caso ainda não tenham sido treinados, o bloco de exemplo
em ``__main__`` demonstra apenas a regra de sugestão a partir de previsões fictícias.
"""

from __future__ import annotations

import os
from typing import Dict, List

import joblib
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes canônicas (alinhadas ao contrato do projeto)
# ---------------------------------------------------------------------------

# Alvos de regressão -> nome do arquivo joblib em models/
ALVOS = [
    "rendimento",
    "volume_irrigacao",
    "necessidade_fertilizacao",
    "umidade",
    "ph",
]

# Superconjunto de features candidatas (id_pivo já em one-hot). Cada modelo usa
# apenas o subconjunto que viu no treino — 'prever' reindexa por
# 'feature_names_in_' de cada modelo. 'umidade' e 'ph' são leituras de contexto:
# entram como feature dos alvos engenheirados, mas são ignoradas pelos modelos
# que preveem a si mesmas (sem leakage).
FEATURE_COLUMNS = [
    "temperatura",
    "n",
    "p",
    "k",
    "estado_bomba_bin",   # 1 = ON, 0 = OFF
    "hora",
    "dia_semana",
    "umidade",            # contexto (feature dos alvos engenheirados)
    "ph",                 # contexto (feature dos alvos engenheirados)
    "id_pivo_p1",
    "id_pivo_p2",
    "id_pivo_p3",
]

ID_PIVOS = ("p1", "p2", "p3")

# Constantes agronômicas usadas nas regras de recomendação.
PH_BOM_MIN, PH_BOM_MAX = 6.0, 7.0
UMIDADE_ALVO_IRRIGACAO = 65.0
N_IDEAL, P_IDEAL, K_IDEAL = 70.0, 60.0, 60.0

# Limiares das regras de manejo.
LIMIAR_IRRIGAR_MM = 5.0          # acima disso recomenda irrigar
LIMIAR_SOLO_ADEQUADO_MM = 1.0    # abaixo/igual disso considera solo adequado
LIMIAR_FERTILIZAR = 50.0         # necessidade_fertilizacao alta
LIMIAR_RENDIMENTO_BAIXO = 40.0   # rendimento previsto baixo


# ---------------------------------------------------------------------------
# Carregamento dos modelos
# ---------------------------------------------------------------------------

def carregar_modelos(models_dir: str) -> Dict[str, object]:
    """Carrega os modelos de regressão persistidos em disco.

    Args:
        models_dir: diretório onde estão os arquivos ``modelo_<alvo>.joblib``.

    Returns:
        Dicionário ``{alvo: modelo_sklearn}`` para cada alvo encontrado.

    Raises:
        FileNotFoundError: se nenhum modelo for encontrado no diretório.
    """
    # Nota de segurança: joblib.load desserializa pickle e só deve apontar para
    # artefatos confiáveis. Aqui carregamos exclusivamente modelos gerados pelo
    # próprio projeto (ml/train.py) e versionados em models/ — fonte confiável.
    modelos: Dict[str, object] = {}
    for alvo in ALVOS:
        caminho = os.path.join(models_dir, f"modelo_{alvo}.joblib")
        if os.path.exists(caminho):
            modelos[alvo] = joblib.load(caminho)
    if not modelos:
        raise FileNotFoundError(
            f"Nenhum modelo 'modelo_<alvo>.joblib' encontrado em {models_dir!r}. "
            "Execute ml/train.py para treinar e salvar os modelos."
        )
    return modelos


# ---------------------------------------------------------------------------
# Montagem da entrada e previsão
# ---------------------------------------------------------------------------

def _montar_features(entrada: Dict[str, object]) -> pd.DataFrame:
    """Converte um dicionário de leitura bruta em um DataFrame de 1 linha.

    Normaliza ``estado_bomba`` ('ON'/'OFF' ou 1/0) e expande ``id_pivo`` em
    one-hot (id_pivo_p1/p2/p3), garantindo a ordem canônica de FEATURE_COLUMNS.

    Args:
        entrada: dicionário com chaves de feature. Espera, no mínimo,
            ``temperatura, n, p, k, estado_bomba, id_pivo, hora, dia_semana``.

    Returns:
        DataFrame com uma linha e colunas em FEATURE_COLUMNS.
    """
    estado = entrada.get("estado_bomba", 0)
    if isinstance(estado, str):
        estado = 1 if estado.strip().upper() == "ON" else 0

    id_pivo = str(entrada.get("id_pivo", "p1")).lower()

    linha = {
        "temperatura": float(entrada.get("temperatura", 0.0)),
        "n": float(entrada.get("n", 0.0)),
        "p": float(entrada.get("p", 0.0)),
        "k": float(entrada.get("k", 0.0)),
        "estado_bomba_bin": int(estado),
        "id_pivo_p1": 1 if id_pivo == "p1" else 0,
        "id_pivo_p2": 1 if id_pivo == "p2" else 0,
        "id_pivo_p3": 1 if id_pivo == "p3" else 0,
        "hora": int(entrada.get("hora", 0)),
        "dia_semana": int(entrada.get("dia_semana", 0)),
        # Leituras de contexto: usadas pelos alvos engenheirados (rendimento etc.).
        "umidade": float(entrada.get("umidade", 0.0)),
        "ph": float(entrada.get("ph", 0.0)),
    }
    return pd.DataFrame([linha], columns=FEATURE_COLUMNS)


def prever(modelos: Dict[str, object], entrada: Dict[str, object]) -> Dict[str, float]:
    """Gera as previsões de todos os alvos para uma única leitura.

    Args:
        modelos: dicionário ``{alvo: modelo}`` retornado por ``carregar_modelos``.
        entrada: leitura de sensores (ver ``_montar_features``).

    Returns:
        Dicionário ``{alvo: valor_previsto_float}``.
    """
    X = _montar_features(entrada)
    previsoes: Dict[str, float] = {}
    for alvo, modelo in modelos.items():
        # Cada modelo usa apenas as features que viu no treino (features por-alvo).
        # Reindexa pela ordem/conjunto de 'feature_names_in_' do próprio modelo.
        nomes = getattr(modelo, "feature_names_in_", None)
        Xm = X.reindex(columns=list(nomes), fill_value=0) if nomes is not None else X
        previsoes[alvo] = float(modelo.predict(Xm)[0])
    return previsoes


# ---------------------------------------------------------------------------
# Regras de recomendação
# ---------------------------------------------------------------------------

def sugerir_acoes(previsoes: Dict[str, float], leitura_atual: Dict[str, object]) -> List[str]:
    """Converte as previsões em recomendações de manejo em texto.

    Regras aplicadas (cada uma pode gerar uma recomendação):
      * Irrigação: volume_irrigacao previsto > 5 mm -> recomenda irrigar com o
        volume estimado; se ~0 mm -> solo adequado, não irrigar.
      * Fertilização: necessidade_fertilizacao > 50 -> recomenda adubação NPK,
        citando o nutriente mais deficiente (com base na leitura atual).
      * Rendimento: rendimento previsto < 40 sacas/ha -> alerta e sugere revisar
        pH e umidade.
      * pH: fora da faixa 6.0–7.0 -> recomenda correção (calagem se ácido).

    Args:
        previsoes: dicionário ``{alvo: valor}`` (ver ``prever``).
        leitura_atual: leitura de sensores corrente (umidade, ph, n, p, k, ...),
            usada para contextualizar as recomendações.

    Returns:
        Lista de strings com as recomendações. Lista vazia significa que nenhuma
        ação foi disparada (situação dentro dos parâmetros).
    """
    acoes: List[str] = []

    # --- Regra de irrigação -------------------------------------------------
    volume = previsoes.get("volume_irrigacao")
    if volume is not None:
        if volume > LIMIAR_IRRIGAR_MM:
            acoes.append(
                f"Irrigação recomendada: aplicar aproximadamente {volume:.1f} mm "
                f"para aproximar a umidade do alvo de {UMIDADE_ALVO_IRRIGACAO:.0f}%."
            )
        elif volume <= LIMIAR_SOLO_ADEQUADO_MM:
            acoes.append(
                "Solo com umidade adequada: não é necessário irrigar no momento."
            )
        else:
            acoes.append(
                f"Irrigação leve opcional: déficit estimado de {volume:.1f} mm "
                "(dentro de uma faixa tolerável)."
            )

    # --- Regra de fertilização ---------------------------------------------
    necessidade = previsoes.get("necessidade_fertilizacao")
    if necessidade is not None and necessidade > LIMIAR_FERTILIZAR:
        nutriente = _nutriente_mais_deficiente(leitura_atual)
        sufixo = f" O nutriente mais deficiente é {nutriente}." if nutriente else ""
        acoes.append(
            f"Adubação NPK recomendada: índice de necessidade de fertilização "
            f"em {necessidade:.0f}/100 (alto).{sufixo}"
        )

    # --- Regra de rendimento ------------------------------------------------
    rendimento = previsoes.get("rendimento")
    if rendimento is not None and rendimento < LIMIAR_RENDIMENTO_BAIXO:
        acoes.append(
            f"Atenção: rendimento previsto baixo ({rendimento:.1f} sacas/ha). "
            "Revise pH e umidade do solo para destravar a produtividade."
        )

    # --- Regra de pH --------------------------------------------------------
    # Prioriza o pH previsto; se ausente, usa a leitura atual.
    ph = previsoes.get("ph", leitura_atual.get("ph"))
    if ph is not None:
        ph = float(ph)
        if ph < PH_BOM_MIN:
            acoes.append(
                f"pH ácido ({ph:.1f}): recomenda-se calagem para elevar o pH à "
                f"faixa ideal de {PH_BOM_MIN:.1f}–{PH_BOM_MAX:.1f}."
            )
        elif ph > PH_BOM_MAX:
            acoes.append(
                f"pH alcalino ({ph:.1f}): recomenda-se correção (ex.: enxofre "
                f"elementar) para retornar à faixa ideal de "
                f"{PH_BOM_MIN:.1f}–{PH_BOM_MAX:.1f}."
            )

    return acoes


def _nutriente_mais_deficiente(leitura_atual: Dict[str, object]) -> str:
    """Identifica qual macronutriente (N, P ou K) está mais distante do ideal.

    Compara as leituras atuais de N, P e K com seus valores ideais e retorna o
    nome do nutriente com maior déficit relativo. Retorna string vazia se não
    houver dados de N/P/K na leitura.

    Args:
        leitura_atual: leitura de sensores corrente (espera chaves 'n', 'p', 'k').

    Returns:
        'N', 'P', 'K' ou '' (quando indeterminado).
    """
    deficits = {}
    for nome, chave, ideal in (("N", "n", N_IDEAL), ("P", "p", P_IDEAL), ("K", "k", K_IDEAL)):
        valor = leitura_atual.get(chave)
        if valor is not None:
            # Déficit relativo ao ideal (apenas faltas contam; 0 se já suprido).
            deficits[nome] = max(0.0, (ideal - float(valor)) / ideal)
    if not deficits or max(deficits.values()) <= 0:
        return ""
    return max(deficits, key=deficits.get)


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Leitura fictícia de sensores (solo seco, NPK baixo, pH ácido).
    leitura_exemplo = {
        "temperatura": 31.0,
        "n": 35.0,
        "p": 25.0,
        "k": 50.0,
        "estado_bomba": "OFF",
        "id_pivo": "p1",
        "hora": 14,
        "dia_semana": 2,
        "umidade": 42.0,
        "ph": 5.4,
    }

    models_dir = os.environ.get(
        "MODELS_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "models"),
    )

    try:
        modelos = carregar_modelos(models_dir)
        previsoes_exemplo = prever(modelos, leitura_exemplo)
        print("Previsões dos modelos:")
        for alvo, valor in previsoes_exemplo.items():
            print(f"  - {alvo}: {valor:.2f}")
    except FileNotFoundError as exc:
        # Fallback: sem modelos treinados, demonstra apenas as regras de manejo
        # usando previsões fictícias coerentes com a leitura acima.
        print(f"[aviso] {exc}")
        print("Usando previsões fictícias para demonstrar as regras de manejo.\n")
        previsoes_exemplo = {
            "rendimento": 28.5,
            "volume_irrigacao": 18.4,
            "necessidade_fertilizacao": 63.0,
            "umidade": 44.0,
            "ph": 5.4,
        }

    print("\nRecomendações de manejo:")
    for i, acao in enumerate(sugerir_acoes(previsoes_exemplo, leitura_exemplo), start=1):
        print(f"  {i}. {acao}")
