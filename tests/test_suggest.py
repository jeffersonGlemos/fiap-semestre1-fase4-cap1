"""Testes de ml/suggest.py — montagem de features, previsão e regras de manejo."""

import pytest

from ml import suggest

LEITURA_SECA = {
    "temperatura": 31.0, "n": 35.0, "p": 25.0, "k": 50.0,
    "estado_bomba": "OFF", "id_pivo": "p1", "hora": 14, "dia_semana": 2,
    "umidade": 40.0, "ph": 5.2,
}


def test_montar_features_colunas():
    X = suggest._montar_features(LEITURA_SECA)
    assert list(X.columns) == suggest.FEATURE_COLUMNS
    # contrato por-alvo: nomes alinhados ao treino
    assert "estado_bomba_bin" in X.columns
    assert "umidade" in X.columns and "ph" in X.columns
    assert {"id_pivo_p1", "id_pivo_p2", "id_pivo_p3"} <= set(X.columns)


def test_estado_bomba_string_para_binario():
    X_on = suggest._montar_features({**LEITURA_SECA, "estado_bomba": "ON"})
    X_off = suggest._montar_features({**LEITURA_SECA, "estado_bomba": "OFF"})
    assert int(X_on["estado_bomba_bin"].iloc[0]) == 1
    assert int(X_off["estado_bomba_bin"].iloc[0]) == 0


def test_prever_com_modelos_reais(models_dir):
    modelos = suggest.carregar_modelos(str(models_dir))
    assert {"rendimento", "volume_irrigacao", "necessidade_fertilizacao", "umidade", "ph"} <= set(modelos)
    previsoes = suggest.prever(modelos, LEITURA_SECA)
    assert set(previsoes) == set(modelos)
    assert all(isinstance(v, float) for v in previsoes.values())
    # solo seco/ácido → volume de irrigação previsto positivo
    assert previsoes["volume_irrigacao"] > 0


def test_sugerir_acoes_regras():
    previsoes = {
        "volume_irrigacao": 20.0, "necessidade_fertilizacao": 60.0,
        "rendimento": 10.0, "umidade": 40.0, "ph": 5.0,
    }
    acoes = suggest.sugerir_acoes(previsoes, {"n": 30, "p": 30, "k": 30, "ph": 5.0})
    assert isinstance(acoes, list) and acoes
    blob = " ".join(acoes).lower()
    assert "irriga" in blob            # volume > limiar → recomenda irrigar
    assert ("ph" in blob) or ("calagem" in blob)   # pH ácido → correção


def test_sugerir_acoes_solo_adequado():
    """pH e volume bons → não deve recomendar irrigação pesada nem calagem."""
    previsoes = {
        "volume_irrigacao": 0.5, "necessidade_fertilizacao": 5.0,
        "rendimento": 70.0, "umidade": 65.0, "ph": 6.5,
    }
    acoes = suggest.sugerir_acoes(previsoes, {"n": 70, "p": 60, "k": 60, "ph": 6.5})
    blob = " ".join(acoes).lower()
    assert "calagem" not in blob
