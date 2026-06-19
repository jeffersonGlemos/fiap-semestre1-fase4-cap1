"""
FarmTech Solutions — Fase 4, Capítulo 1 · Assistente Agrícola Inteligente
API fina (FastAPI) — camada de serviço da arquitetura híbrida.

Autor : Jefferson Gonçalves Lemos · RM 572399
Disciplina : Inteligência Artificial — FIAP

Esta API é deliberadamente "fina": ela apenas orquestra peças que vivem em
outros pacotes do projeto, sem reimplementar regra de negócio.

    GET  /health           → verificação de saúde (liveness).
    GET  /api/sensores     → leituras dos sensores (Oracle se DATA_SOURCE=local,
                             ou Parquet versionado se DATA_SOURCE=cloud).
    POST /api/predict       → previsões dos 5 alvos de regressão + sugestões
                             agronômicas (carrega models/*.joblib em cache).

Arquitetura híbrida (ver CONTRATO do projeto):

    DATA_SOURCE=local  → consome o Oracle XE reaproveitado do Cap-3
                         (tabela SENSORES_FARMTECH) através do pacote ``db``.
    DATA_SOURCE=cloud  → ambiente sem Oracle (ex.: Streamlit Cloud); lê o
                         dataset processado em ``data/processed/dataset_ml.parquet``
                         e os modelos versionados em ``models/*.joblib``.

Variáveis de ambiente reconhecidas:

    DATA_SOURCE        local | cloud           (default: local)
    MODELS_DIR         caminho da pasta de modelos joblib
    DATA_PATH          caminho do Parquet processado
    ORACLE_DSN / ORACLE_USER / ORACLE_PASSWORD → usadas pelo pacote ``db``

Como executar localmente (a partir da raiz do projeto):

    uvicorn api.main:app --reload --port 8000

Observação sobre imports (sys.path):
    Os pacotes irmãos ``db`` e ``ml`` ficam na raiz do projeto, e não dentro
    de ``api/``. Para que ``import db`` / ``import ml`` funcionem tanto via
    ``uvicorn api.main:app`` (raiz já no path) quanto ao rodar este arquivo
    diretamente, adicionamos a raiz do projeto ao ``sys.path`` logo abaixo.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

# --------------------------------------------------------------------------- #
# Resolução de caminhos e sys.path                                            #
# --------------------------------------------------------------------------- #
# Estrutura:  <PROJECT_ROOT>/api/main.py  →  PROJECT_ROOT = pai de api/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    # Garante que os pacotes irmãos `db` e `ml` (na raiz) sejam importáveis.
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("farmtech.api")

# --------------------------------------------------------------------------- #
# Configuração por ambiente                                                   #
# --------------------------------------------------------------------------- #
DATA_SOURCE: str = os.getenv("DATA_SOURCE", "local").strip().lower()
MODELS_DIR: Path = Path(os.getenv("MODELS_DIR", str(PROJECT_ROOT / "models")))
DATA_PATH: Path = Path(
    os.getenv("DATA_PATH", str(PROJECT_ROOT / "data" / "processed" / "dataset_ml.parquet"))
)

# Mapa alvo de regressão → arquivo do modelo serializado (joblib).
# A ordem aqui define a ordem das previsões devolvidas pela API.
TARGET_MODELS: Dict[str, str] = {
    "rendimento": "modelo_rendimento.joblib",
    "volume_irrigacao": "modelo_volume_irrigacao.joblib",
    "necessidade_fertilizacao": "modelo_necessidade_fertilizacao.joblib",
    "umidade": "modelo_umidade.joblib",
    "ph": "modelo_ph.joblib",
}

# Ordem canônica das features de entrada do modelo (deve casar com ml/train.py).
# id_pivo é codificado em one-hot (p1/p2/p3); hora e dia_semana derivam de capturado_em.
FEATURE_COLUMNS: List[str] = [
    "temperatura",
    "n",
    "p",
    "k",
    "estado_bomba",
    "id_pivo_p1",
    "id_pivo_p2",
    "id_pivo_p3",
    "hora",
    "dia_semana",
]

# --------------------------------------------------------------------------- #
# Aplicação FastAPI                                                           #
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="FarmTech Solutions — Assistente Agrícola Inteligente",
    description=(
        "API de previsões agronômicas (regressão) e leitura de sensores IoT. "
        "Fase 4, Capítulo 1 — FIAP."
    ),
    version="1.0.0",
)


# --------------------------------------------------------------------------- #
# Schemas (Pydantic)                                                          #
# --------------------------------------------------------------------------- #
class SensorReading(BaseModel):
    """Uma leitura de sensor (linha de SENSORES_FARMTECH / Parquet)."""

    id_pivo: str = Field(..., examples=["p1"])
    umidade: Optional[float] = None
    temperatura: Optional[float] = None
    ph: Optional[float] = None
    n: Optional[float] = None
    p: Optional[float] = None
    k: Optional[float] = None
    estado_bomba: Optional[str] = Field(None, examples=["ON"])
    capturado_em: Optional[str] = None
    periodo: Optional[str] = Field(
        None,
        description="Coluna virtual do Oracle (manhã/tarde/noite). Pode ser None no Parquet.",
    )


class PredictRequest(BaseModel):
    """Features de entrada para a previsão dos 5 alvos de regressão.

    ``estado_bomba`` aceita 1/0 (1=ON, 0=OFF) ou as strings "ON"/"OFF".
    ``id_pivo`` deve ser um de {p1, p2, p3} (codificado em one-hot internamente).
    ``capturado_em`` é opcional; se informado, ``hora`` e ``dia_semana`` são
    derivadas dele. Caso contrário, usam-se os valores explícitos (ou defaults).
    """

    temperatura: float = Field(..., ge=-10, le=60, examples=[25.0])
    n: float = Field(..., ge=0, le=200, examples=[70.0])
    p: float = Field(..., ge=0, le=200, examples=[60.0])
    k: float = Field(..., ge=0, le=200, examples=[60.0])
    estado_bomba: int = Field(1, description="1=ON, 0=OFF", examples=[1])
    id_pivo: str = Field("p1", examples=["p1"])
    capturado_em: Optional[str] = Field(
        None, description="Timestamp ISO; deriva hora e dia_semana se presente."
    )
    hora: Optional[int] = Field(None, ge=0, le=23, examples=[14])
    dia_semana: Optional[int] = Field(None, ge=0, le=6, examples=[2])

    @field_validator("estado_bomba", mode="before")
    @classmethod
    def _coerce_bomba(cls, v: Union[int, str]) -> int:
        """Converte "ON"/"OFF" (ou bool) para 1/0 antes da validação numérica."""
        if isinstance(v, str):
            return 1 if v.strip().upper() in {"ON", "1", "TRUE", "LIGADA"} else 0
        return int(bool(v)) if isinstance(v, bool) else int(v)

    @field_validator("id_pivo")
    @classmethod
    def _valida_pivo(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"p1", "p2", "p3"}:
            raise ValueError("id_pivo deve ser p1, p2 ou p3")
        return v


class PredictResponse(BaseModel):
    """Resposta da rota de previsão."""

    previsoes: Dict[str, float] = Field(
        ..., description="Valor previsto para cada um dos 5 alvos de regressão."
    )
    sugestoes: List[str] = Field(
        default_factory=list,
        description="Recomendações de manejo derivadas das previsões (ml/suggest.py).",
    )
    fonte_modelo: str = Field(
        ..., description="'joblib' quando os modelos foram carregados; 'stub' caso contrário."
    )


# --------------------------------------------------------------------------- #
# Carregamento de modelos (cache)                                            #
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def load_models() -> Dict[str, Any]:
    """Carrega e cacheia os modelos joblib de ``MODELS_DIR``.

    Usa ``functools.lru_cache`` para que o disco seja lido apenas na primeira
    requisição (os modelos ficam residentes em memória no processo do uvicorn).

    Retorna um dicionário ``{nome_alvo: estimador_sklearn}``. Alvos cujo arquivo
    ainda não exista são simplesmente omitidos (degradação graciosa enquanto o
    pipeline de treino — ml/train.py — não foi executado).
    """
    # Segurança: joblib.load desserializa pickle e permitiria execução de código
    # se a fonte fosse não-confiável. Aqui os .joblib são artefatos do PRÓPRIO
    # projeto (gerados por ml/train.py e versionados no repo), portanto confiáveis.
    import joblib  # import tardio: só necessário quando há previsão real

    modelos: Dict[str, Any] = {}
    for alvo, arquivo in TARGET_MODELS.items():
        caminho = MODELS_DIR / arquivo
        if caminho.exists():
            try:
                modelos[alvo] = joblib.load(caminho)
                logger.info("Modelo carregado: %s", caminho)
            except Exception as exc:  # pragma: no cover - robustez de runtime
                logger.warning("Falha ao carregar %s: %s", caminho, exc)
        else:
            logger.warning("Modelo ausente (ainda não treinado): %s", caminho)
    return modelos


@lru_cache(maxsize=1)
def load_metrics() -> Dict[str, Any]:
    """Lê ``models/metrics.json`` (MAE/MSE/RMSE/R² por alvo), se existir."""
    caminho = MODELS_DIR / "metrics.json"
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            logger.warning("metrics.json inválido: %s", exc)
    return {}


# --------------------------------------------------------------------------- #
# Helpers de features                                                         #
# --------------------------------------------------------------------------- #
def _build_feature_row(req: PredictRequest) -> Dict[str, float]:
    """Monta o dicionário de features na ordem canônica ``FEATURE_COLUMNS``.

    Deriva ``hora``/``dia_semana`` de ``capturado_em`` quando este é informado;
    aplica one-hot em ``id_pivo``.
    """
    hora = req.hora
    dia_semana = req.dia_semana

    if req.capturado_em:
        try:
            ts = datetime.fromisoformat(req.capturado_em.replace("Z", "+00:00"))
            hora = ts.hour if hora is None else hora
            dia_semana = ts.weekday() if dia_semana is None else dia_semana
        except ValueError:
            logger.warning("capturado_em não-ISO ignorado: %r", req.capturado_em)

    # Defaults neutros caso nada tenha sido informado.
    hora = 12 if hora is None else int(hora)
    dia_semana = 0 if dia_semana is None else int(dia_semana)

    return {
        "temperatura": float(req.temperatura),
        "n": float(req.n),
        "p": float(req.p),
        "k": float(req.k),
        "estado_bomba": float(req.estado_bomba),
        "id_pivo_p1": 1.0 if req.id_pivo == "p1" else 0.0,
        "id_pivo_p2": 1.0 if req.id_pivo == "p2" else 0.0,
        "id_pivo_p3": 1.0 if req.id_pivo == "p3" else 0.0,
        "hora": float(hora),
        "dia_semana": float(dia_semana),
    }


def _gerar_sugestoes(previsoes: Dict[str, float]) -> List[str]:
    """Delegação para ``ml/suggest.py`` com fallback inline.

    O contrato do projeto coloca a lógica de manejo em ``ml/suggest.py``. Como
    os pacotes irmãos podem ainda não existir no momento do esqueleto, fazemos
    import tardio com degradação graciosa para um heurístico mínimo.
    """
    try:
        from ml.suggest import gerar_sugestoes  # type: ignore

        return list(gerar_sugestoes(previsoes))
    except Exception as exc:  # pragma: no cover - ml/suggest.py ainda não pronto
        logger.info("ml.suggest indisponível (%s); usando fallback inline.", exc)

    # ------- Fallback heurístico mínimo (coerente com as faixas do contrato) -------
    sugestoes: List[str] = []
    vol = previsoes.get("volume_irrigacao")
    fert = previsoes.get("necessidade_fertilizacao")
    umid = previsoes.get("umidade")
    ph = previsoes.get("ph")

    if vol is not None and vol > 5:
        sugestoes.append(f"Irrigar aproximadamente {vol:.1f} mm para repor a umidade do solo.")
    if fert is not None and fert > 50:
        sugestoes.append(
            f"Necessidade de fertilização elevada (índice {fert:.0f}/100): avaliar reposição de NPK."
        )
    if umid is not None and umid < 55:
        sugestoes.append(f"Umidade prevista baixa ({umid:.1f}%); priorizar irrigação.")
    if ph is not None and (ph < 6.0 or ph > 7.0):
        sugestoes.append(f"pH previsto fora da faixa ideal (6.0–7.0): valor {ph:.2f}. Corrigir solo.")
    if not sugestoes:
        sugestoes.append("Condições dentro das faixas ideais; manter o manejo atual.")
    return sugestoes


# --------------------------------------------------------------------------- #
# Fontes de dados de sensores                                                #
# --------------------------------------------------------------------------- #
def _sensores_via_parquet(limit: int) -> List[Dict[str, Any]]:
    """Lê as últimas ``limit`` leituras do Parquet processado (modo cloud)."""
    import pandas as pd  # import tardio

    csv_path = DATA_PATH.with_suffix(".csv")
    if DATA_PATH.exists():
        try:
            df = pd.read_parquet(DATA_PATH)
        except (ImportError, ValueError):
            df = pd.read_csv(csv_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        raise FileNotFoundError(
            f"Dataset processado não encontrado: {DATA_PATH} nem {csv_path}"
        )
    # Ordena pelo timestamp quando disponível, mantendo as leituras mais recentes.
    if "capturado_em" in df.columns:
        df = df.sort_values("capturado_em", ascending=False)
    registros = df.head(limit).to_dict(orient="records")
    # Normaliza chaves/timestamps para JSON.
    return [{k: (str(v) if isinstance(v, datetime) else v) for k, v in r.items()} for r in registros]


def _sensores_via_oracle(limit: int) -> List[Dict[str, Any]]:
    """Consulta as últimas ``limit`` leituras no Oracle (modo local).

    STUB COERENTE: a obtenção de conexão é delegada ao pacote ``db`` (reuso do
    Oracle XE do Cap-3). A query abaixo é a forma canônica esperada sobre a
    tabela ``SENSORES_FARMTECH`` (incluindo a coluna virtual ``PERIODO``).
    """
    # Import tardio do pacote irmão `db` (raiz já está no sys.path).
    from db.connection import get_connection  # type: ignore

    query = """
        SELECT ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K,
               ESTADO_BOMBA, CAPTURADO_EM, PERIODO
          FROM SENSORES_FARMTECH
         ORDER BY CAPTURADO_EM DESC
         FETCH FIRST :limit ROWS ONLY
    """
    registros: List[Dict[str, Any]] = []
    with get_connection() as conn:  # context manager esperado do pacote db
        cur = conn.cursor()
        cur.execute(query, {"limit": limit})
        colunas = [c[0].lower() for c in cur.description]
        for linha in cur.fetchall():
            registro = dict(zip(colunas, linha))
            # Timestamps Oracle → string ISO para serialização JSON.
            ce = registro.get("capturado_em")
            if isinstance(ce, datetime):
                registro["capturado_em"] = ce.isoformat()
            registros.append(registro)
    return registros


# --------------------------------------------------------------------------- #
# Rotas                                                                       #
# --------------------------------------------------------------------------- #
@app.get("/health", tags=["infra"])
def health() -> Dict[str, Any]:
    """Liveness/health check. Reporta a fonte de dados e modelos carregados."""
    return {
        "status": "ok",
        "servico": "farmtech-api",
        "data_source": DATA_SOURCE,
        "modelos_disponiveis": sorted(load_models().keys()),
        "modelos_dir": str(MODELS_DIR),
        "data_path": str(DATA_PATH),
    }


@app.get("/api/sensores", response_model=List[SensorReading], tags=["sensores"])
def listar_sensores(
    limit: int = Query(50, ge=1, le=2696, description="Número máximo de leituras a retornar."),
) -> List[Dict[str, Any]]:
    """Retorna as leituras de sensores mais recentes.

    - ``DATA_SOURCE=local`` → consulta o Oracle (SENSORES_FARMTECH) via ``db``.
    - ``DATA_SOURCE=cloud`` → lê ``data/processed/dataset_ml.parquet``.

    Em caso de falha no Oracle (ex.: Cap-3 não está de pé), faz fallback
    automático para o Parquet, mantendo a API utilizável.
    """
    if DATA_SOURCE == "cloud":
        try:
            return _sensores_via_parquet(limit)
        except Exception as exc:
            logger.error("Falha lendo Parquet: %s", exc)
            raise HTTPException(status_code=503, detail=f"Parquet indisponível: {exc}") from exc

    # modo local (Oracle), com fallback para Parquet.
    try:
        return _sensores_via_oracle(limit)
    except Exception as exc:
        logger.warning("Oracle indisponível (%s); tentando Parquet.", exc)
        try:
            return _sensores_via_parquet(limit)
        except Exception as exc2:
            logger.error("Parquet também indisponível: %s", exc2)
            raise HTTPException(
                status_code=503,
                detail="Nenhuma fonte de dados disponível (Oracle e Parquet falharam).",
            ) from exc2


@app.post("/api/predict", response_model=PredictResponse, tags=["ml"])
def prever(req: PredictRequest) -> PredictResponse:
    """Prevê os 5 alvos de regressão e devolve sugestões de manejo.

    Carrega os modelos ``models/*.joblib`` (em cache) e aplica cada um sobre o
    mesmo vetor de features. Se um modelo ainda não foi treinado, aquele alvo é
    omitido das previsões. Quando NENHUM modelo está disponível, devolve uma
    previsão-stub neutra (``fonte_modelo='stub'``) para que o contrato da rota
    permaneça válido durante o desenvolvimento.
    """
    features = _build_feature_row(req)
    modelos = load_models()
    previsoes: Dict[str, float] = {}
    fonte = "joblib"

    if modelos:
        import pandas as pd  # import tardio

        # DataFrame de 1 linha com nomes de coluna na ordem canônica de treino.
        X = pd.DataFrame([[features[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        for alvo, modelo in modelos.items():
            try:
                valor = float(modelo.predict(X)[0])
                previsoes[alvo] = round(valor, 3)
            except Exception as exc:  # pragma: no cover - mismatch de features etc.
                logger.error("Falha ao prever %s: %s", alvo, exc)
    else:
        # Stub coerente: sem modelos treinados ainda, devolve valores neutros.
        fonte = "stub"
        previsoes = {alvo: 0.0 for alvo in TARGET_MODELS}

    sugestoes = _gerar_sugestoes(previsoes)
    return PredictResponse(previsoes=previsoes, sugestoes=sugestoes, fonte_modelo=fonte)


@app.get("/api/metrics", tags=["ml"])
def metricas() -> Dict[str, Any]:
    """Expõe as métricas de avaliação dos modelos (models/metrics.json)."""
    return load_metrics()


# --------------------------------------------------------------------------- #
# Execução direta (desenvolvimento)                                          #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
