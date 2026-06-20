"""
Ingestão IoT → Oracle — FarmTech Solutions, Fase 4, Cap 1.

Autor: Jefferson Gonçalves Lemos · RM 572399 · IA — FIAP.

IR ALÉM 1 — Pipeline de integração entre os sensores de campo (IoT) e o banco
Oracle XE reusado do Cap-3 (``1-semestre/Cap-3/fase3_cap1``).

Este script tem duas responsabilidades:

1. **Ingestão (escrita):** lê ``data/raw/seed_data.csv`` e insere as leituras na
   tabela ``SENSORES_FARMTECH`` via ``executemany`` (INSERT em lote). Pode rodar
   em modo único (``--once``) ou em modo contínuo (``--loop``), simulando a
   chegada periódica de novas leituras dos pivôs de irrigação.

2. **Leitura (serviço para o ML):** a função :func:`ler_dados_oracle` faz um
   SELECT na tabela e devolve os registros prontos para alimentar os modelos de
   regressão (``ml/`` e ``streamlit/app.py`` quando ``DATA_SOURCE=local``).

Variáveis de ambiente
---------------------
ORACLE_DSN / ORACLE_USER / ORACLE_PASSWORD   conexão (ver ``db/connection.py``)
DATA_PATH    caminho do CSV bruto (default: ``data/raw/seed_data.csv`` do projeto)

Uso (CLI)
---------
    python -m db.ingest --once
    python -m db.ingest --loop --interval 5 --batch-size 3
    python -m db.ingest --loop --interval 10 --batch-size 5 --simular-tempo-real
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import time
from datetime import datetime
from typing import Any, Iterable

from db.connection import (
    DB_ENGINE,
    count_sql,
    criar_tabela,
    get_connection,
    insert_sql,
    select_sql,
    wait_for_connection,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Caminho do dataset bruto (CSV de sensores).
# Default: data/raw/seed_data.csv relativo à raiz do projeto fase4cap1.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_PATH = os.path.join(_PROJECT_ROOT, "data", "raw", "seed_data.csv")
DATA_PATH: str = os.getenv("DATA_PATH", DEFAULT_DATA_PATH)

# Colunas da tabela, na ordem dos binds do INSERT.
COLUNAS = ("ID_PIVO", "UMIDADE", "TEMPERATURA", "PH", "N", "P", "K", "ESTADO_BOMBA", "CAPTURADO_EM")


# ---------------------------------------------------------------------------
# Leitura / parsing do CSV
# ---------------------------------------------------------------------------
def carregar_csv(path: str = DATA_PATH) -> list[tuple[Any, ...]]:
    """Lê o CSV bruto e devolve uma lista de tuplas prontas para o ``executemany``.

    Parameters
    ----------
    path : str
        Caminho do arquivo ``seed_data.csv``.

    Returns
    -------
    list[tuple]
        Cada tupla segue a ordem de :data:`COLUNAS`.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV não encontrado: {path}")

    linhas: list[tuple[Any, ...]] = []
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            linhas.append(
                (
                    row["ID_PIVO"],
                    float(row["UMIDADE"]),
                    float(row["TEMPERATURA"]),
                    float(row["PH"]),
                    int(row["N"]),
                    int(row["P"]),
                    int(row["K"]),
                    row["ESTADO_BOMBA"],
                    row["CAPTURADO_EM"],
                )
            )
    logger.info("CSV carregado: %d linhas de %s", len(linhas), path)
    return linhas


def _com_timestamp_atual(linha: tuple[Any, ...]) -> tuple[Any, ...]:
    """Retorna a linha com ``CAPTURADO_EM`` substituído pelo instante atual.

    Usado no modo ``--simular-tempo-real`` para que as leituras inseridas no
    loop pareçam ter chegado "agora" dos sensores.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (*linha[:-1], agora)


# ---------------------------------------------------------------------------
# Escrita (ingestão)
# ---------------------------------------------------------------------------
def inserir_linhas(conn, linhas: Iterable[tuple[Any, ...]]) -> int:
    """Insere um lote de linhas em ``SENSORES_FARMTECH`` via ``executemany``.

    Funciona tanto no SQLite quanto no Oracle (o SQL vem de
    ``connection.insert_sql()``, no dialeto do engine ativo).

    Parameters
    ----------
    conn
        Conexão ativa (sqlite3 ou oracledb).
    linhas : Iterable[tuple]
        Tuplas na ordem de :data:`COLUNAS`.

    Returns
    -------
    int
        Quantidade de linhas inseridas (e comitadas).
    """
    linhas = list(linhas)
    if not linhas:
        return 0
    cur = conn.cursor()
    try:
        cur.executemany(insert_sql(), linhas)
    finally:
        cur.close()
    conn.commit()
    return len(linhas)


def ingest_once(path: str = DATA_PATH, simular_tempo_real: bool = False) -> int:
    """Ingestão única: insere TODO o conteúdo do CSV de uma vez.

    Parameters
    ----------
    path : str
        Caminho do CSV.
    simular_tempo_real : bool
        Se ``True``, reescreve ``CAPTURADO_EM`` com o instante atual.

    Returns
    -------
    int
        Total de linhas inseridas.
    """
    linhas = carregar_csv(path)
    if simular_tempo_real:
        linhas = [_com_timestamp_atual(l) for l in linhas]
    conn = wait_for_connection()
    try:
        criar_tabela(conn)  # idempotente (cria a tabela no SQLite novo)
        total = inserir_linhas(conn, linhas)
        logger.info("Ingestão única concluída: %d linhas inseridas.", total)
        return total
    finally:
        conn.close()


def ingest_loop(
    path: str = DATA_PATH,
    interval: float = 5.0,
    batch_size: int = 3,
    simular_tempo_real: bool = True,
    max_ciclos: int | None = None,
) -> int:
    """Ingestão contínua: insere o CSV em lotes, num intervalo fixo.

    Simula a ingestão contínua de um datalogger/IoT: a cada ``interval``
    segundos, envia ``batch_size`` leituras para o Oracle. Ao chegar ao fim do
    CSV, recomeça do início (ciclo), permitindo rodar indefinidamente.
    Interrompa com ``Ctrl+C``.

    Parameters
    ----------
    path : str
        Caminho do CSV.
    interval : float
        Segundos entre os lotes.
    batch_size : int
        Número de leituras por lote.
    simular_tempo_real : bool
        Se ``True``, cada leitura recebe ``CAPTURADO_EM`` = instante atual.
    max_ciclos : int | None
        Limite opcional de lotes (útil para testes). ``None`` = infinito.

    Returns
    -------
    int
        Total acumulado de linhas inseridas até a interrupção.
    """
    linhas = carregar_csv(path)
    if not linhas:
        logger.warning("CSV vazio — nada a ingerir.")
        return 0

    conn = wait_for_connection()
    criar_tabela(conn)  # idempotente (cria a tabela no SQLite novo)
    total = 0
    idx = 0
    ciclo = 0
    try:
        while max_ciclos is None or ciclo < max_ciclos:
            lote = linhas[idx : idx + batch_size]
            if not lote:  # chegou ao fim → recomeça o ciclo
                idx = 0
                lote = linhas[idx : idx + batch_size]
            if simular_tempo_real:
                lote = [_com_timestamp_atual(l) for l in lote]
            inseridos = inserir_linhas(conn, lote)
            total += inseridos
            idx += batch_size
            ciclo += 1
            logger.info(
                "Lote %d: +%d linhas (acumulado=%d). Aguardando %.1fs...",
                ciclo, inseridos, total, interval,
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Loop interrompido pelo usuário. Total inserido: %d", total)
    finally:
        conn.close()
    return total


# ---------------------------------------------------------------------------
# Leitura (serviço para o ML)
# ---------------------------------------------------------------------------
def ler_dados(limit: int | None = None, as_dataframe: bool = False):
    """Lê leituras de ``SENSORES_FARMTECH`` para alimentar o pipeline de ML.

    Faz um SELECT ordenado por ``CAPTURADO_EM`` e devolve os registros. Esta é a
    porta de entrada usada pelo ``ml/`` e pelo ``streamlit/app.py`` quando
    ``DATA_SOURCE=local`` (fonte = banco SQL: SQLite por padrão, ou o Oracle do
    Cap-3 quando ``DB_ENGINE=oracle``).

    Parameters
    ----------
    limit : int | None
        Número máximo de linhas (``None`` = todas).
    as_dataframe : bool
        Se ``True``, devolve um ``pandas.DataFrame`` (import tardio); caso
        contrário, uma lista de dicionários ``{coluna: valor}``.

    Returns
    -------
    list[dict] | pandas.DataFrame
        Registros com as colunas de :data:`COLUNAS`.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(select_sql(limit))
            colunas = [d[0] for d in cur.description]
            registros = [dict(zip(colunas, row)) for row in cur.fetchall()]
        finally:
            cur.close()
    finally:
        conn.close()

    logger.info("SELECT retornou %d linhas de SENSORES_FARMTECH.", len(registros))

    if as_dataframe:
        import pandas as pd  # import tardio — só quando necessário

        return pd.DataFrame(registros, columns=colunas)
    return registros


# Alias retrocompatível (o módulo antes expunha 'ler_dados_oracle').
ler_dados_oracle = ler_dados


def contar_linhas() -> int:
    """Retorna a contagem de linhas em ``SENSORES_FARMTECH`` (0 se a tabela não existir)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(count_sql())
            return int(cur.fetchone()[0])
        except Exception:  # noqa: BLE001 - tabela ainda não criada
            return 0
        finally:
            cur.close()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingestão IoT → Oracle (SENSORES_FARMTECH) — FarmTech Fase 4 Cap 1.",
    )
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument(
        "--once",
        action="store_true",
        help="Insere todo o CSV de uma vez e encerra.",
    )
    modo.add_argument(
        "--loop",
        action="store_true",
        help="Ingestão contínua em lotes (simula IoT). Interrompa com Ctrl+C.",
    )
    parser.add_argument(
        "--path", default=DATA_PATH, help=f"Caminho do CSV (default: {DATA_PATH})."
    )
    parser.add_argument(
        "--interval", type=float, default=5.0, help="Segundos entre lotes (modo --loop)."
    )
    parser.add_argument(
        "--batch-size", type=int, default=3, help="Leituras por lote (modo --loop)."
    )
    parser.add_argument(
        "--max-ciclos", type=int, default=None, help="Limite de lotes (modo --loop, opcional)."
    )
    parser.add_argument(
        "--simular-tempo-real",
        action="store_true",
        help="Reescreve CAPTURADO_EM com o instante atual (leituras 'ao vivo').",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Ponto de entrada da CLI."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)

    if args.once:
        ingest_once(path=args.path, simular_tempo_real=args.simular_tempo_real)
    elif args.loop:
        ingest_loop(
            path=args.path,
            interval=args.interval,
            batch_size=args.batch_size,
            simular_tempo_real=args.simular_tempo_real,
            max_ciclos=args.max_ciclos,
        )


if __name__ == "__main__":
    main()
