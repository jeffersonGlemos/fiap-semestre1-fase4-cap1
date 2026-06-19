"""
Módulo de conexão Oracle — FarmTech Solutions, Fase 4, Cap 1.

Autor: Jefferson Gonçalves Lemos · RM 572399 · IA — FIAP.

IR ALÉM 1 — Integração IoT → Oracle.
Este módulo REUSA o banco Oracle XE provisionado no Cap-3
(``1-semestre/Cap-3/fase3_cap1``). Nenhum container de banco é subido aqui:
o docker-compose deste projeto sobe apenas a API (FastAPI) e o Streamlit.

A conexão usa o driver ``oracledb`` em *thin mode*, ou seja, NÃO exige a
instalação do Oracle Instant Client. Os parâmetros são lidos de variáveis de
ambiente, com defaults apontando para o Oracle do Cap-3 exposto em
``localhost:1521`` (service ``XEPDB1``).

Variáveis de ambiente
---------------------
ORACLE_DSN       DSN no formato ``host:porta/service``  (default: ``localhost:1521/XEPDB1``)
ORACLE_USER      Usuário do banco                        (default: ``system``)
ORACLE_PASSWORD  Senha do banco                          (default: ``farmtech123``)

Exemplos
--------
>>> from db.connection import get_connection
>>> conn = get_connection()
>>> with conn.cursor() as cur:
...     cur.execute("SELECT COUNT(*) FROM SENSORES_FARMTECH")
...     print(cur.fetchone()[0])
>>> conn.close()

Ou usando o context manager (fecha a conexão automaticamente):

>>> from db.connection import oracle_connection
>>> with oracle_connection() as conn:
...     with conn.cursor() as cur:
...         cur.execute("SELECT * FROM SENSORES_FARMTECH FETCH FIRST 5 ROWS ONLY")
...         rows = cur.fetchall()
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Iterator

import oracledb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parâmetros de conexão — lidos do ambiente, com defaults apontando para o
# Oracle XE do Cap-3 (localhost:1521/XEPDB1).
# ---------------------------------------------------------------------------
ORACLE_DSN: str = os.getenv("ORACLE_DSN", "localhost:1521/XEPDB1")
ORACLE_USER: str = os.getenv("ORACLE_USER", "system")
ORACLE_PASSWORD: str = os.getenv("ORACLE_PASSWORD", "farmtech123")


def get_connection() -> oracledb.Connection:
    """Abre e retorna uma nova conexão com o Oracle (thin mode).

    Lê ``ORACLE_DSN``, ``ORACLE_USER`` e ``ORACLE_PASSWORD`` do ambiente.
    O *thin mode* do ``oracledb`` dispensa o Instant Client, bastando o
    pacote Python instalado.

    Returns
    -------
    oracledb.Connection
        Conexão ativa. É responsabilidade do chamador fechá-la
        (``conn.close()``) ou usar o context manager :func:`oracle_connection`.

    Raises
    ------
    oracledb.Error
        Se o banco não estiver acessível ou as credenciais forem inválidas.
    """
    logger.debug("Conectando ao Oracle em %s (user=%s)", ORACLE_DSN, ORACLE_USER)
    return oracledb.connect(
        user=ORACLE_USER,
        password=ORACLE_PASSWORD,
        dsn=ORACLE_DSN,
    )


def wait_for_connection(retries: int = 30, delay: float = 2.0) -> oracledb.Connection:
    """Tenta conectar repetidamente até o Oracle responder.

    Útil logo após subir o container do Cap-3, que pode levar alguns minutos
    para ficar pronto (``DATABASE IS READY TO USE``).

    Parameters
    ----------
    retries : int
        Número máximo de tentativas.
    delay : float
        Segundos de espera entre tentativas.

    Returns
    -------
    oracledb.Connection

    Raises
    ------
    TimeoutError
        Quando todas as tentativas se esgotam.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            conn = get_connection()
            logger.info("Conexão Oracle estabelecida na tentativa %d/%d", attempt, retries)
            return conn
        except oracledb.Error as exc:
            last_exc = exc
            logger.warning("Oracle indisponível (tentativa %d/%d): %s", attempt, retries, exc)
            time.sleep(delay)
    raise TimeoutError(
        f"Oracle inacessível após {retries} tentativas. Último erro: {last_exc}"
    )


@contextmanager
def oracle_connection() -> Iterator[oracledb.Connection]:
    """Context manager que abre e fecha a conexão automaticamente.

    Em caso de exceção dentro do bloco, faz ``rollback``; caso contrário,
    encerra normalmente. A conexão é sempre fechada na saída.

    Yields
    ------
    oracledb.Connection

    Examples
    --------
    >>> with oracle_connection() as conn:
    ...     with conn.cursor() as cur:
    ...         cur.execute("SELECT 1 FROM DUAL")
    ...         cur.fetchone()
    """
    conn = get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Teste rápido de conectividade (smoke test).
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        with oracle_connection() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute("SELECT 1 FROM DUAL")
                _cur.fetchone()
        logger.info("OK — conexão com %s funcionando.", ORACLE_DSN)
    except Exception as _exc:  # noqa: BLE001
        logger.error("Falha ao conectar em %s: %s", ORACLE_DSN, _exc)
        raise
