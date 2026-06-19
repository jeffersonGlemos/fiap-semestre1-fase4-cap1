"""Treino multi-alvo dos modelos de regressao do FarmTech Solutions (Fase 4, Cap 1).

Pipeline de Machine Learning supervisionado para o Assistente Agricola Inteligente.

Para cada alvo de regressao definido no contrato canonico do projeto, este script:
  1. Carrega o dataset processado (``data/processed/dataset_ml.parquet``).
  2. Monta a matriz de features ``X`` (com one-hot de ``id_pivo``) e o vetor alvo ``y``.
  3. Faz o split treino/teste 80/20 (``random_state=42``).
  4. Treina e ajusta tres familias de modelos (LinearRegression, Ridge,
     RandomForestRegressor) via ``GridSearchCV`` (cv=5).
  5. Seleciona o melhor estimador por R^2 e o avalia no conjunto de teste
     (MAE, MSE, RMSE, R^2).
  6. Persiste o melhor modelo em ``models/modelo_<alvo>.joblib`` e agrega
     todas as metricas em ``models/metrics.json``.

Autor: Jefferson Goncalves Lemos - RM 572399
Disciplina: Inteligencia Artificial - FIAP

Uso:
    python3 ml/train.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split

# --------------------------------------------------------------------------- #
# Constantes / caminhos do projeto
# --------------------------------------------------------------------------- #
# Raiz do projeto: .../fase4cap1 (este arquivo vive em fase4cap1/ml/train.py).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "dataset_ml.parquet"
MODELS_DIR = PROJECT_ROOT / "models"
METRICS_PATH = MODELS_DIR / "metrics.json"

RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5

# Alvos de regressao (contrato canonico). Tres engenheirados + dois reais.
TARGETS: list[str] = [
    "rendimento",
    "volume_irrigacao",
    "necessidade_fertilizacao",
    "umidade",
    "ph",
]

# Features de entrada do modelo (contrato canonico).
# Observacao: 'id_pivo' entra como one-hot (p1/p2/p3); 'estado_bomba' como 1/0;
# 'hora' e 'dia_semana' sao derivadas de 'capturado_em' (geradas no prepare_dataset.py).
BASE_FEATURES: list[str] = [
    "temperatura",
    "n",
    "p",
    "k",
    "estado_bomba_bin",
    "hora",
    "dia_semana",
]
PIVOT_COLUMN = "id_pivo"
PIVOT_DUMMY_PREFIX = "id_pivo"


# --------------------------------------------------------------------------- #
# Carregamento e preparacao dos dados
# --------------------------------------------------------------------------- #
def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    """Carrega o dataset processado em parquet.

    Args:
        path: Caminho do arquivo ``dataset_ml.parquet``.

    Returns:
        DataFrame com features e alvos prontos para o treino.

    Raises:
        FileNotFoundError: Se o parquet nao existir (instrui rodar o prepare).
    """
    csv_path = path.with_suffix(".csv")
    if path.exists():
        try:
            return pd.read_parquet(path)
        except (ImportError, ValueError):
            pass  # pyarrow ausente → tenta o CSV irmao
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(
        f"Dataset processado nao encontrado em '{path}' nem '{csv_path}'.\n"
        "Gere-o primeiro executando:  python3 ml/prepare_dataset.py"
    )


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Monta a matriz de features ``X`` conforme o contrato.

    Aplica one-hot em ``id_pivo`` (p1/p2/p3) via ``pd.get_dummies`` e garante a
    presenca de todas as colunas-base. Espera que ``hora``, ``dia_semana`` e
    ``estado_bomba`` (1=ON/0=OFF) ja existam no dataset processado.

    Args:
        df: DataFrame carregado do parquet.

    Returns:
        DataFrame somente com as colunas de entrada do modelo.
    """
    # One-hot de id_pivo -> id_pivo_p1, id_pivo_p2, id_pivo_p3.
    if PIVOT_COLUMN in df.columns:
        dummies = pd.get_dummies(df[PIVOT_COLUMN], prefix=PIVOT_DUMMY_PREFIX)
    else:
        # Caso o parquet ja venha com as dummies materializadas.
        dummies = df[[c for c in df.columns if c.startswith(f"{PIVOT_DUMMY_PREFIX}_")]]

    base = df[[c for c in BASE_FEATURES if c in df.columns]].copy()
    X = pd.concat([base, dummies], axis=1)

    # Converte dummies booleanas para int (0/1) por consistencia entre versoes.
    X = X.astype({col: "int8" for col in dummies.columns})
    return X


def build_targets(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Extrai o dicionario de vetores-alvo presentes no dataset.

    Args:
        df: DataFrame carregado do parquet.

    Returns:
        Mapa ``{nome_alvo: serie}`` apenas para os alvos disponiveis.
    """
    available = {t: df[t] for t in TARGETS if t in df.columns}
    missing = [t for t in TARGETS if t not in df.columns]
    if missing:
        print(f"[aviso] alvos ausentes no dataset e ignorados: {missing}")
    return available


# --------------------------------------------------------------------------- #
# Definicao dos modelos / grids de busca
# --------------------------------------------------------------------------- #
def candidate_models() -> dict[str, dict]:
    """Define os estimadores candidatos e suas grades de busca.

    Grades propositalmente pequenas (esqueleto). Os pontos de tuning fino
    estao marcados com TODO para expansao posterior.

    Returns:
        Mapa ``{nome: {"estimator": ..., "param_grid": {...}}}``.
    """
    return {
        "linear_regression": {
            # Baseline linear: sem hiperparametros relevantes.
            "estimator": LinearRegression(),
            "param_grid": {},
        },
        "ridge": {
            # Regularizacao L2 para controlar variancia.
            "estimator": Ridge(random_state=RANDOM_STATE),
            # TODO(tuning): ampliar a grade de alpha (ex.: logspace(-3, 3)).
            "param_grid": {"alpha": [0.1, 1.0, 10.0]},
        },
        "random_forest": {
            # Modelo nao-linear (captura interacoes entre NPK/umidade/temperatura).
            "estimator": RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1),
            # TODO(tuning): adicionar max_features, min_samples_leaf, etc.
            "param_grid": {
                "n_estimators": [200, 400],
                "max_depth": [None, 12],
            },
        },
    }


# --------------------------------------------------------------------------- #
# Treino / avaliacao por alvo
# --------------------------------------------------------------------------- #
def evaluate(y_true, y_pred) -> dict[str, float]:
    """Calcula as metricas de regressao do contrato (MAE, MSE, RMSE, R^2)."""
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def train_target(
    target_name: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> tuple[object, dict]:
    """Treina os candidatos para um alvo e retorna o melhor modelo + metricas.

    Para cada familia de modelo roda ``GridSearchCV(cv=5)`` otimizando R^2,
    seleciona globalmente o melhor por R^2 de validacao cruzada e o reavalia
    no conjunto de teste.

    Args:
        target_name: Nome do alvo (apenas para logging).
        X_train, X_test: Matrizes de features de treino/teste.
        y_train, y_test: Vetores-alvo de treino/teste.

    Returns:
        Tupla ``(melhor_estimador_ajustado, metricas_dict)`` onde
        ``metricas_dict`` agrega info de cada candidato, o vencedor e as
        metricas de teste do vencedor.
    """
    print(f"\n=== Alvo: {target_name} ===")
    candidates = candidate_models()

    per_model: dict[str, dict] = {}
    best_name: str | None = None
    best_estimator = None
    best_cv_r2 = -np.inf

    for name, spec in candidates.items():
        search = GridSearchCV(
            estimator=spec["estimator"],
            param_grid=spec["param_grid"],
            scoring="r2",
            cv=CV_FOLDS,
            n_jobs=-1,
        )
        search.fit(X_train, y_train)

        cv_r2 = float(search.best_score_)
        per_model[name] = {
            "cv_r2": cv_r2,
            "best_params": search.best_params_,
        }
        print(f"  - {name:<18} cv_r2={cv_r2:.4f}  params={search.best_params_}")

        if cv_r2 > best_cv_r2:
            best_cv_r2 = cv_r2
            best_name = name
            best_estimator = search.best_estimator_

    # Avaliacao final do vencedor no conjunto de teste (holdout).
    y_pred = best_estimator.predict(X_test)
    test_metrics = evaluate(y_test, y_pred)
    print(
        f"  >> melhor: {best_name} | teste "
        f"R2={test_metrics['r2']:.4f} RMSE={test_metrics['rmse']:.4f} "
        f"MAE={test_metrics['mae']:.4f}"
    )

    metrics = {
        "best_model": best_name,
        "best_cv_r2": best_cv_r2,
        "candidates": per_model,
        "test_metrics": test_metrics,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    return best_estimator, metrics


def save_model(estimator, target_name: str, models_dir: Path = MODELS_DIR) -> Path:
    """Persiste o melhor estimador em ``models/modelo_<alvo>.joblib``."""
    models_dir.mkdir(parents=True, exist_ok=True)
    out_path = models_dir / f"modelo_{target_name}.joblib"
    # compress=3 reduz drasticamente o tamanho (RandomForest comprime ~5x),
    # viabilizando versionar os modelos no repo para o deploy (IR ALÉM 2).
    joblib.dump(estimator, out_path, compress=3)
    return out_path


def save_metrics(all_metrics: dict, path: Path = METRICS_PATH) -> None:
    """Agrega e grava todas as metricas em ``models/metrics.json``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(all_metrics, fh, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Orquestracao
# --------------------------------------------------------------------------- #
def main() -> None:
    """Executa o pipeline completo de treino multi-alvo."""
    print("FarmTech Solutions - Treino multi-alvo (Fase 4, Cap 1)")
    print(f"Dataset : {DATA_PATH}")
    print(f"Modelos : {MODELS_DIR}")

    df = load_dataset(DATA_PATH)
    X = build_features(df)
    targets = build_targets(df)
    feature_names = list(X.columns)
    print(f"\nFeatures ({len(feature_names)}): {feature_names}")
    print(f"Linhas no dataset: {len(df)}")

    all_metrics: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "cv_folds": CV_FOLDS,
        "features": feature_names,
        "targets": {},
    }

    for target_name, y in targets.items():
        # Split 80/20 por alvo (mesmo random_state => mesma particao de linhas).
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
        )

        best_estimator, metrics = train_target(
            target_name, X_train, X_test, y_train, y_test
        )

        out_path = save_model(best_estimator, target_name)
        metrics["model_path"] = str(out_path.relative_to(PROJECT_ROOT))
        all_metrics["targets"][target_name] = metrics
        print(f"  modelo salvo em: {out_path}")

    save_metrics(all_metrics, METRICS_PATH)
    print(f"\nMetricas agregadas salvas em: {METRICS_PATH}")
    print("Treino concluido.")


if __name__ == "__main__":
    main()
