"""Teste do dashboard Streamlit (streamlit/app.py) via AppTest.

Roda o AppTest num SUBPROCESSO com cwd em ``streamlit/`` — assim ``import
streamlit`` resolve para o pacote instalado, sem sombrear com o diretório local
``streamlit/``. Pula automaticamente se o Streamlit não estiver instalado.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STREAMLIT_DIR = PROJECT_ROOT / "streamlit"

_SCRIPT = r"""
import logging
logging.disable(logging.WARNING)
try:
    from streamlit.testing.v1 import AppTest
except Exception:
    print("MODULE_MISSING")
    raise SystemExit(0)
at = AppTest.from_file("app.py").run(timeout=180)
print("EXC", len(at.exception))
print("ERRORS", len(at.error))
print("METRICS", len(at.metric))
print("SUBHEADERS", len(at.subheader))
"""


def _run(env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        cwd=str(STREAMLIT_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.mark.parametrize("modo", ["cloud"])
def test_dashboard_roda_sem_excecoes(modo):
    r = _run({"DATA_SOURCE": modo})
    out = r.stdout
    if "MODULE_MISSING" in out:
        pytest.skip("streamlit não instalado neste ambiente")
    assert "EXC 0" in out, f"app teve exceções em modo {modo}:\n{out}\nSTDERR:\n{r.stderr[-1500:]}"
    assert "ERRORS 0" in out, f"app exibiu st.error em modo {modo}:\n{out}"
    # 6 abas (subheaders) e métricas renderizadas (KPIs + previsões)
    assert "SUBHEADERS 6" in out
    assert "METRICS 9" in out
