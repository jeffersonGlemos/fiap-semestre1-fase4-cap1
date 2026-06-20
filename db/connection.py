"""
Conexão de banco — engine-agnóstica (FarmTech Solutions, Fase 4, Cap 1).

Autor: Jefferson Gonçalves Lemos · RM 572399 · IA — FIAP.

IR ALÉM 1 — Integração IoT → banco SQL.

Por padrão usa **SQLite** (arquivo local, zero configuração) para que a ingestão
dos dados de sensores rode e seja demonstrável em qualquer máquina, sem depender
de container. Para reusar o **Oracle XE** provisionado no Cap-3
(``1-semestre/Cap-3/fase3_cap1``), basta ``DB_ENGINE=oracle`` — o módulo
``oracledb`` só é importado nesse caso (import preguiçoso).

A camada de dialeto (placeholders, tipos, LIMIT) é abstraída para que
``db/ingest.py`` funcione igual nos dois engines.

Variáveis de ambiente
---------------------
DB_ENGINE        ``sqlite`` (default) ou ``oracle``
SQLITE_PATH      caminho do arquivo SQLite (default: ``db/farmtech.db``)
ORACLE_DSN       DSN ``host:porta/service`` (default: ``localhost:1521/XEPDB1``)
ORACLE_USER      usuário Oracle (default: ``system``)
ORACLE_PASSWORD  senha Oracle (default: ``farmtech123``)
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine e parâmetros — lidos do ambiente.
# ---------------------------------------------------------------------------
DB_ENGINE: str = os.getenv("DB_ENGINE", "sqlite").lower()

_DB_DIR = Path(__file__).resolve().parent
SQLITE_PATH: str = os.getenv("SQLITE_PATH", str(_DB_DIR / "farmtech.db"))

ORACLE_DSN: str = os.getenv("ORACLE_DSN", "localhost:1521/XEPDB1")
ORACLE_USER: str = os.getenv("ORACLE_USER", "system")
ORACLE_PASSWORD: str = os.getenv("ORACLE_PASSWORD", "farmtech123")

TABELA = "SENSORES_FARMTECH"


def is_oracle() -> bool:
    """True se o engine configurado for Oracle."""
    return DB_ENGINE == "oracle"


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------
def get_connection():
    """Abre e retorna uma nova conexão conforme ``DB_ENGINE``.

    - ``oracle``: usa ``oracledb`` em *thin mode* (sem Instant Client). O módulo
      só é importado aqui, então o modo SQLite não exige ``oracledb`` instalado.
    - ``sqlite`` (default): cria/abre o arquivo ``SQLITE_PATH``.

    É responsabilidade do chamador fechar a conexão (ou usar :func:`db_connection`).
    """
    if is_oracle():
        import oracledb  # import preguiçoso — só no modo oracle

        logger.debug("Conectando ao Oracle em %s (user=%s)", ORACLE_DSN, ORACLE_USER)
        return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

    import sqlite3

    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Conectando ao SQLite em %s", SQLITE_PATH)
    return sqlite3.connect(SQLITE_PATH)


def wait_for_connection(retries: int = 30, delay: float = 2.0):
    """Tenta conectar repetidamente até o banco responder.

    Útil para o Oracle do Cap-3, que pode levar minutos para subir. No SQLite a
    conexão é imediata (uma tentativa basta).
    """
    last_exc: Exception | None = None
    tentativas = 1 if not is_oracle() else retries
    for attempt in range(1, tentativas + 1):
        try:
            conn = get_connection()
            if attempt > 1:
                logger.info("Conexão estabelecida na tentativa %d/%d", attempt, tentativas)
            return conn
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Banco indisponível (tentativa %d/%d): %s", attempt, tentativas, exc)
            time.sleep(delay)
    raise TimeoutError(f"Banco inacessível após {tentativas} tentativas. Último erro: {last_exc}")


@contextmanager
def db_connection() -> Iterator[object]:
    """Context manager que abre e fecha a conexão automaticamente.

    Faz ``rollback`` em caso de exceção e sempre fecha a conexão na saída.
    """
    conn = get_connection()
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:  # pragma: no cover - alguns drivers podem não suportar
            pass
        raise
    finally:
        conn.close()


# Alias retrocompatível (o módulo antes expunha 'oracle_connection').
oracle_connection = db_connection


# ---------------------------------------------------------------------------
# Dialeto SQL — placeholders, tipos e LIMIT diferem entre engines.
# ---------------------------------------------------------------------------
def create_table_sql() -> str:
    """DDL de criação da tabela ``SENSORES_FARMTECH`` para o engine atual."""
    if is_oracle():
        return (
            f"CREATE TABLE {TABELA} (ID_PIVO VARCHAR2(30) NOT NULL, UMIDADE NUMBER(5,2), "
            "TEMPERATURA NUMBER(5,2), PH NUMBER(5,2), N NUMBER(3), P NUMBER(3), K NUMBER(3), "
            "ESTADO_BOMBA VARCHAR2(3), CAPTURADO_EM TIMESTAMP)"
        )
    return (
        f"CREATE TABLE IF NOT EXISTS {TABELA} (ID_PIVO TEXT NOT NULL, UMIDADE REAL, "
        "TEMPERATURA REAL, PH REAL, N INTEGER, P INTEGER, K INTEGER, "
        "ESTADO_BOMBA TEXT, CAPTURADO_EM TEXT)"
    )


def insert_sql() -> str:
    """INSERT com placeholders e conversão de timestamp por engine."""
    cols = "ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM"
    if is_oracle():
        return (
            f"INSERT INTO {TABELA} ({cols}) "
            "VALUES (:1, :2, :3, :4, :5, :6, :7, :8, "
            "TO_TIMESTAMP(:9, 'YYYY-MM-DD HH24:MI:SS'))"
        )
    return f"INSERT INTO {TABELA} ({cols}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"


def select_sql(limit: int | None = None) -> str:
    """SELECT ordenado por ``CAPTURADO_EM``, com LIMIT no dialeto do engine."""
    sql = (
        "SELECT ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM "
        f"FROM {TABELA} ORDER BY CAPTURADO_EM"
    )
    if limit is not None:
        sql += f" FETCH FIRST {int(limit)} ROWS ONLY" if is_oracle() else f" LIMIT {int(limit)}"
    return sql


def count_sql() -> str:
    """COUNT(*) da tabela."""
    return f"SELECT COUNT(*) FROM {TABELA}"


def criar_tabela(conn) -> None:
    """Cria ``SENSORES_FARMTECH`` se não existir (idempotente nos dois engines)."""
    cur = conn.cursor()
    try:
        if is_oracle():
            # No Oracle a tabela já vem do schema do Cap-3; tenta criar e ignora
            # ORA-00955 (objeto já existe).
            try:
                cur.execute(create_table_sql())
            except Exception as exc:  # noqa: BLE001
                if "955" not in str(exc):
                    raise
        else:
            cur.execute(create_table_sql())
        conn.commit()
    finally:
        cur.close()


if __name__ == "__main__":
    # Smoke test de conectividade + criação da tabela.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with db_connection() as _conn:
        criar_tabela(_conn)
        _cur = _conn.cursor()
        _cur.execute("SELECT 1 FROM DUAL" if is_oracle() else "SELECT 1")
        _cur.fetchone()
        _cur.close()
    logger.info("OK — engine=%s acessível e tabela %s pronta.", DB_ENGINE, TABELA)
