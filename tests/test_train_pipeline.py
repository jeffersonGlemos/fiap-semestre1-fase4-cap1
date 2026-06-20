"""Testes do laço de treino de ml/train.py (train_target, save_model, save_metrics).

Usa um grid REDUZIDO (monkeypatch de candidate_models) e uma amostra pequena para
exercitar o pipeline de treino sem rodar o GridSearchCV completo (que é lento).
"""

import json

import joblib
import pytest
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import train_test_split

from ml import train


@pytest.fixture
def grid_reduzido(monkeypatch):
    """Substitui o grid pesado (RandomForest/GridSearch grande) por um mínimo e rápido."""
    monkeypatch.setattr(train, "candidate_models", lambda: {
        "linear_regression": {"estimator": LinearRegression(), "param_grid": {}},
        "ridge": {"estimator": Ridge(random_state=42), "param_grid": {"alpha": [1.0]}},
    })


@pytest.fixture
def amostra(project_root):
    df = train.load_dataset(project_root / "data" / "processed" / "dataset_ml.parquet")
    return df.sample(n=min(300, len(df)), random_state=42)


def test_train_target_retorna_estimador_e_metricas(grid_reduzido, amostra):
    extras = [c for c in train.features_para_alvo("rendimento") if c not in train.BASE_FEATURES]
    X = train.build_features(amostra, extra_features=extras)
    y = amostra["rendimento"].astype(float)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42)

    estimador, metrics = train.train_target("rendimento", X_tr, X_te, y_tr, y_te)

    assert metrics["best_model"] in {"linear_regression", "ridge"}
    assert {"mae", "mse", "rmse", "r2"} <= set(metrics["test_metrics"])
    assert metrics["n_train"] == len(X_tr) and metrics["n_test"] == len(X_te)
    # o estimador selecionado realmente prevê
    assert len(estimador.predict(X_te)) == len(X_te)


def test_save_model_e_metrics_roundtrip(tmp_path, amostra):
    X = train.build_features(amostra, extra_features=[])
    y = amostra["umidade"].astype(float)
    est = LinearRegression().fit(X, y)

    caminho = train.save_model(est, "umidade", models_dir=tmp_path)
    assert caminho.exists()
    # joblib.load aqui é seguro: o artefato foi criado por este próprio teste (não há fonte externa).
    recarregado = joblib.load(caminho)
    assert hasattr(recarregado, "predict")

    metrics_path = tmp_path / "metrics.json"
    train.save_metrics({"targets": {"umidade": {"test_metrics": {"r2": 0.7}}}}, metrics_path)
    dados = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert dados["targets"]["umidade"]["test_metrics"]["r2"] == 0.7


def test_load_dataset_ausente_orienta(tmp_path):
    with pytest.raises(FileNotFoundError):
        train.load_dataset(tmp_path / "nao_existe.parquet")
