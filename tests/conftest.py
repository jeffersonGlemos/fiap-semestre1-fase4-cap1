"""Fixtures compartilhadas dos testes do FarmTech Solutions (Fase 4, Cap 1).

Importante sobre sys.path: a raiz do projeto é adicionada ao FINAL de ``sys.path``
(``append``, não ``insert(0)``) de propósito — assim os pacotes do projeto
(``db``, ``ml``, ``api``) ficam importáveis SEM sombrear o pacote ``streamlit``
instalado (existe um diretório local ``streamlit/`` que viraria namespace package
se a raiz fosse prefixada).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import pytest  # noqa: E402

RAW_CSV = PROJECT_ROOT / "data" / "raw" / "seed_data.csv"
MODELS_DIR = PROJECT_ROOT / "models"


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def raw_csv() -> Path:
    if not RAW_CSV.exists():
        pytest.skip(f"CSV bruto ausente: {RAW_CSV}")
    return RAW_CSV


@pytest.fixture
def sqlite_db(tmp_path, monkeypatch):
    """Aponta o pacote ``db`` para um SQLite temporário e isolado por teste."""
    import db.connection as conn

    dbfile = tmp_path / "farmtech_test.db"
    monkeypatch.setattr(conn, "DB_ENGINE", "sqlite")
    monkeypatch.setattr(conn, "SQLITE_PATH", str(dbfile))
    return dbfile


@pytest.fixture(scope="session")
def models_dir() -> Path:
    if not MODELS_DIR.exists() or not list(MODELS_DIR.glob("modelo_*.joblib")):
        pytest.skip("modelos .joblib ausentes — rode ml/train.py")
    return MODELS_DIR
