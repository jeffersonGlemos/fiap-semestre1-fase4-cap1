"""Testes de db/ — ingestão IoT→DB engine-agnóstica (SQLite) e leitura para o ML."""

import pytest

from db import connection, ingest


def test_dialeto_sqlite(sqlite_db):
    # engine SQLite (default) → placeholders '?', CREATE IF NOT EXISTS, LIMIT
    assert connection.is_oracle() is False
    assert "?" in connection.insert_sql()
    assert "IF NOT EXISTS" in connection.create_table_sql()
    assert "LIMIT" in connection.select_sql(5)
    assert "FETCH FIRST" not in connection.select_sql(5)


def test_ingest_once_idempotente(sqlite_db, raw_csv):
    n1 = ingest.ingest_once(path=str(raw_csv))
    c1 = ingest.contar_linhas()
    ingest.ingest_once(path=str(raw_csv))          # re-rodar não deve duplicar
    c2 = ingest.contar_linhas()
    assert n1 > 0
    assert c1 == c2 == n1


def test_ingest_once_append(sqlite_db, raw_csv):
    base = ingest.ingest_once(path=str(raw_csv))
    ingest.ingest_once(path=str(raw_csv), reset=False)   # modo append acrescenta
    assert ingest.contar_linhas() == 2 * base


def test_loop_adiciona_lotes(sqlite_db, raw_csv):
    base = ingest.ingest_once(path=str(raw_csv))
    ingest.ingest_loop(
        path=str(raw_csv), interval=0, batch_size=5,
        max_ciclos=3, simular_tempo_real=True,
    )
    assert ingest.contar_linhas() == base + 15


def test_ler_dados_dict_e_dataframe(sqlite_db, raw_csv):
    ingest.ingest_once(path=str(raw_csv))
    linhas = ingest.ler_dados(limit=3)
    assert len(linhas) == 3
    assert "ID_PIVO" in linhas[0] and "UMIDADE" in linhas[0]

    df = ingest.ler_dados(limit=5, as_dataframe=True)
    assert len(df) == 5
    assert "CAPTURADO_EM" in df.columns


def test_contar_linhas_tabela_inexistente(sqlite_db):
    # sem ingestão e sem tabela criada → 0 (não levanta exceção)
    assert ingest.contar_linhas() == 0
