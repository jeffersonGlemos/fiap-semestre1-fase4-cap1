"""Testes da API FastAPI (api/main.py) — health, predict (5 alvos) e sensores.

Pula automaticamente se ``fastapi`` não estiver instalado.
"""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

ALVOS = {"rendimento", "volume_irrigacao", "necessidade_fertilizacao", "umidade", "ph"}

ENTRADA = {
    "temperatura": 30, "n": 40, "p": 30, "k": 50,
    "umidade": 40, "ph": 5.2, "estado_bomba": 0, "id_pivo": "p2",
}


@pytest.fixture
def client(monkeypatch):
    import api.main as m

    monkeypatch.setattr(m, "DATA_SOURCE", "cloud")  # lê parquet/csv + joblib do repo
    return TestClient(m.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_feature_columns_alinhadas_ao_treino():
    """A API deve usar os MESMOS nomes de feature do treino (regressão do bug)."""
    import api.main as m

    assert "estado_bomba_bin" in m.FEATURE_COLUMNS
    assert "estado_bomba" not in m.FEATURE_COLUMNS      # nome antigo NÃO pode voltar
    assert {"umidade", "ph"} <= set(m.FEATURE_COLUMNS)


def test_predict_usa_modelos_reais(client, models_dir):
    r = client.post("/api/predict", json=ENTRADA)
    assert r.status_code == 200
    body = r.json()
    assert body["fonte_modelo"] == "joblib"            # NÃO 'stub' → modelos aplicados
    assert set(body["previsoes"]) == ALVOS
    # pelo menos um alvo com valor não trivial (previsão real, não tudo zero)
    assert any(abs(v) > 0.01 for v in body["previsoes"].values())
    assert len(body["sugestoes"]) >= 1


def test_sensores_cloud(client):
    r = client.get("/api/sensores?limit=3")
    assert r.status_code == 200
    assert len(r.json()) == 3
