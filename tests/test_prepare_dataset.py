"""Testes de ml/prepare_dataset.py — engenharia de features e dos alvos simulados."""

import pytest

from ml import prepare_dataset as pp

TARGET_RANGES = {
    "rendimento": (0.0, 80.0),
    "volume_irrigacao": (0.0, 40.0),
    "necessidade_fertilizacao": (0.0, 100.0),
}


@pytest.fixture(scope="module")
def df_processado(raw_csv, tmp_path_factory):
    out = tmp_path_factory.mktemp("proc") / "dataset_ml.parquet"
    return pp.prepare_dataset(csv_path=raw_csv, out_path=out), out


def test_funcao_sino_e_relu():
    assert pp.bell(5.0, 5.0, 1.0) == pytest.approx(1.0)   # 1.0 no ótimo
    assert 0.0 < pp.bell(8.0, 5.0, 1.0) < 1.0             # decai fora do ótimo
    assert pp.relu(-3) == 0 and pp.relu(4) == 4


def test_features_derivadas(df_processado):
    df, _ = df_processado
    for col in ("hora", "dia_semana", "estado_bomba_bin"):
        assert col in df.columns, f"coluna derivada ausente: {col}"
    assert set(df["estado_bomba_bin"].unique()) <= {0, 1}
    assert df["hora"].between(0, 23).all()
    assert df["dia_semana"].between(0, 6).all()


def test_alvos_engenheirados_nas_faixas(df_processado):
    df, _ = df_processado
    for alvo, (lo, hi) in TARGET_RANGES.items():
        assert alvo in df.columns, f"alvo ausente: {alvo}"
        assert df[alvo].min() >= lo - 1e-6
        assert df[alvo].max() <= hi + 1e-6
    # os alvos reais permanecem
    assert "umidade" in df.columns and "ph" in df.columns


def test_rendimento_depende_de_umidade_e_ph(df_processado):
    """Sanidade da heurística: rendimento alto exige umidade e pH próximos do ótimo."""
    df, _ = df_processado
    bom = df[(df["umidade"].between(55, 70)) & (df["ph"].between(6.0, 7.0))]
    ruim = df[(df["umidade"] < 40) | (df["ph"] < 4.5)]
    if len(bom) and len(ruim):
        assert bom["rendimento"].mean() > ruim["rendimento"].mean()


def test_roundtrip_salvar_ler(df_processado):
    df, out = df_processado
    df2 = pp.ler_processado(out)
    assert len(df2) == len(df)
    assert set(df2.columns) == set(df.columns)
