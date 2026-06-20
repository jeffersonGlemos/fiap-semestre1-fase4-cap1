"""Testes de consistência entre módulos, do metrics.json e de arquivos referenciados."""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALVOS = ["rendimento", "volume_irrigacao", "necessidade_fertilizacao", "umidade", "ph"]


def test_nomes_de_feature_consistentes_treino_inferencia():
    from ml import train, suggest

    # nome canônico do estado da bomba (regressão do bug estado_bomba vs _bin)
    assert "estado_bomba_bin" in train.BASE_FEATURES
    assert "estado_bomba_bin" in suggest.FEATURE_COLUMNS
    # o superconjunto de inferência inclui as features de contexto
    assert {"umidade", "ph"} <= set(suggest.FEATURE_COLUMNS)
    # toda BASE_FEATURES do treino está no superconjunto de inferência
    assert set(train.BASE_FEATURES) <= set(suggest.FEATURE_COLUMNS)


def test_metrics_json_estrutura_e_desempenho():
    metrics = json.loads((PROJECT_ROOT / "models" / "metrics.json").read_text(encoding="utf-8"))
    assert "targets" in metrics
    for alvo in ALVOS:
        assert alvo in metrics["targets"], f"alvo ausente em metrics.json: {alvo}"
        tm = metrics["targets"][alvo]["test_metrics"]
        assert {"mae", "mse", "rmse", "r2"} <= set(tm)
        feat_cols = metrics["targets"][alvo]["feature_columns"]
        assert alvo not in feat_cols  # sem leakage também no artefato salvo
    # features por-alvo: engenheirados têm umidade/ph; rendimento bem ajustado
    assert {"umidade", "ph"} <= set(metrics["targets"]["rendimento"]["feature_columns"])
    assert metrics["targets"]["rendimento"]["test_metrics"]["r2"] > 0.7


@pytest.mark.parametrize(
    "rel",
    [
        "README.md",
        "requirements.txt",
        "docker-compose.yml",
        ".streamlit/config.toml",
        "ml/JeffersonLemos_RM572399_fase4_cap1.ipynb",
        "ml/prepare_dataset.py",
        "ml/train.py",
        "ml/suggest.py",
        "api/main.py",
        "db/connection.py",
        "db/ingest.py",
        "streamlit/app.py",
        "data/processed/dataset_ml.csv",
        "models/metrics.json",
    ],
)
def test_arquivo_referenciado_existe(rel):
    assert (PROJECT_ROOT / rel).exists(), f"arquivo do projeto ausente: {rel}"


def test_readme_nao_referencia_notebook_inexistente():
    txt = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "ml/notebook.ipynb" not in txt  # ref quebrada antiga não pode voltar


def test_todos_os_modelos_existem():
    models_dir = PROJECT_ROOT / "models"
    for alvo in ALVOS:
        assert (models_dir / f"modelo_{alvo}.joblib").exists()
