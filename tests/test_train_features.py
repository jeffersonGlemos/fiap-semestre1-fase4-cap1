"""Testes de ml/train.py — features por-alvo e ausência de data leakage."""

import pytest

from ml import train

ENGENHEIRADOS = ["rendimento", "volume_irrigacao", "necessidade_fertilizacao"]
REAIS = ["umidade", "ph"]


def test_alvo_nunca_e_feature_de_si_mesmo():
    """Sem data leakage: o alvo não pode aparecer em suas próprias features."""
    for alvo in train.TARGETS:
        assert alvo not in train.features_para_alvo(alvo)


def test_engenheirados_recebem_contexto():
    """rendimento/volume/necessidade dependem de umidade+ph → devem recebê-las."""
    for alvo in ENGENHEIRADOS:
        cols = train.features_para_alvo(alvo)
        assert "umidade" in cols and "ph" in cols


def test_reais_usam_so_base():
    """umidade/ph (alvos reais) não usam contexto (não recebem umidade/ph)."""
    for alvo in REAIS:
        cols = train.features_para_alvo(alvo)
        assert "umidade" not in cols and "ph" not in cols


def test_build_features_contagem_e_nomes(raw_csv):
    df = train.load_dataset.__wrapped__ if hasattr(train.load_dataset, "__wrapped__") else None
    import pandas as pd

    df = pd.read_csv(raw_csv)
    df.columns = [c.lower() for c in df.columns]
    df["estado_bomba_bin"] = (df["estado_bomba"].str.upper() == "ON").astype(int)
    df["hora"] = 12
    df["dia_semana"] = 0

    X_eng = train.build_features(df, extra_features=["umidade", "ph"])
    X_base = train.build_features(df, extra_features=[])
    assert "estado_bomba_bin" in X_eng.columns
    assert "umidade" in X_eng.columns and "ph" in X_eng.columns
    assert "umidade" not in X_base.columns and "ph" not in X_base.columns
    # one-hot de id_pivo com prefixo id_pivo_
    assert any(c.startswith("id_pivo_") for c in X_eng.columns)


def test_evaluate_retorna_metricas():
    m = train.evaluate([1.0, 2.0, 3.0], [1.1, 1.9, 3.2])
    assert set(m) == {"mae", "mse", "rmse", "r2"}
    assert all(isinstance(v, float) for v in m.values())
    assert m["rmse"] == pytest.approx(m["mse"] ** 0.5)
