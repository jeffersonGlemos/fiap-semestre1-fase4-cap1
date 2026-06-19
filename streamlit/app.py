"""
FarmTech Solutions — Fase 4, Cap. 1
Dashboard do Assistente Agricola Inteligente (Streamlit + Plotly).

Autor: Jefferson Goncalves Lemos · RM 572399
Disciplina: Inteligencia Artificial — FIAP

Este modulo e o ESQUELETO FUNCIONAL do dashboard. Ele:
  - Comuta a fonte de dados pela variavel de ambiente DATA_SOURCE:
        * "local" -> consome a API FastAPI (API_URL) e/ou o Oracle do Cap-3;
        * "cloud" -> le o parquet versionado (data/processed/dataset_ml.parquet)
                     e os modelos *.joblib de models/ (deploy no Streamlit Cloud,
                     que NAO enxerga o Oracle local).
  - Carrega os 5 modelos de regressao treinados (.joblib) sob demanda;
  - Le as metricas (MAE/MSE/RMSE/R2) de models/metrics.json;
  - Reaproveita o conceito do dashboard do Cap-3 nas abas analiticas;
  - Gera previsoes a partir de entradas do usuario e sugestoes de manejo
    (delegando para ml/suggest.py quando disponivel).

Roda com:  streamlit run streamlit/app.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Plotly e usado nas abas analiticas e de previsoes.
import plotly.express as px
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# 1. CAMINHOS E CONFIGURACAO GLOBAL
# ---------------------------------------------------------------------------

# Diretorio deste arquivo (.../streamlit) e a raiz do projeto (um nivel acima).
APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent

# Permite importar o pacote ml/ (ex.: ml/suggest.py) ao rodar o app.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Variaveis de ambiente (com defaults seguros para rodar localmente).
DATA_SOURCE = os.getenv("DATA_SOURCE", "cloud").strip().lower()
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(BASE_DIR / "models")))
DATA_PATH = Path(os.getenv("DATA_PATH", str(BASE_DIR / "data" / "processed" / "dataset_ml.parquet")))
RAW_CSV = BASE_DIR / "data" / "raw" / "seed_data.csv"

# Mapa alvo -> arquivo do modelo treinado.
MODELOS = {
    "rendimento": "modelo_rendimento.joblib",
    "volume_irrigacao": "modelo_volume_irrigacao.joblib",
    "necessidade_fertilizacao": "modelo_necessidade_fertilizacao.joblib",
    "umidade": "modelo_umidade.joblib",
    "ph": "modelo_ph.joblib",
}

# Rotulos amigaveis e unidades para exibicao das previsoes.
ALVOS_INFO = {
    "rendimento": ("Rendimento", "sacas/ha", "🌾"),
    "volume_irrigacao": ("Volume de irrigacao", "mm", "💧"),
    "necessidade_fertilizacao": ("Necessidade de fertilizacao", "indice 0-100", "🧪"),
    "umidade": ("Umidade prevista", "%", "💦"),
    "ph": ("pH previsto", "", "⚗️"),
}

# Paleta agricola (verdes/terra) reutilizada nos graficos.
CORES = {
    "verde": "#2e7d32",
    "verde_claro": "#81c784",
    "terra": "#8d6e63",
    "agua": "#0288d1",
    "alerta": "#f9a825",
}


# ---------------------------------------------------------------------------
# 2. PAGE CONFIG (deve ser a primeira chamada Streamlit)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="FarmTech — Assistente Agricola Inteligente",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# 3. CARGA DE DADOS (comutavel por DATA_SOURCE) — com cache
# ---------------------------------------------------------------------------

def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza os nomes de colunas para minusculo (id_pivo, umidade, ...)."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    # Garante datetime na coluna de captura, se existir.
    if "capturado_em" in df.columns:
        df["capturado_em"] = pd.to_datetime(df["capturado_em"], errors="coerce")
    return df


@st.cache_data(show_spinner="Carregando dados...")
def load_data(data_source: str) -> pd.DataFrame:
    """
    Carrega o dataset conforme a fonte configurada.

    - "local": tenta a API FastAPI (API_URL); se indisponivel, tenta o Oracle
      do Cap-3 via oracledb; por fim cai no parquet/CSV local.
    - "cloud": le o parquet versionado; se ausente, usa o CSV bruto.

    Retorna sempre um DataFrame com colunas em minusculo (pode estar vazio).
    """
    # ---- Modo LOCAL: API -> Oracle -> arquivo ----
    if data_source == "local":
        # 1) API REST (FastAPI)
        try:
            import requests  # import tardio: so necessario no modo local

            resp = requests.get(f"{API_URL}/leituras", timeout=5)
            if resp.ok:
                dados = resp.json()
                registros = dados.get("data", dados) if isinstance(dados, dict) else dados
                df = pd.DataFrame(registros)
                if not df.empty:
                    return _normalizar_colunas(df)
        except Exception:  # pragma: no cover - fallback silencioso
            pass

        # 2) Oracle XE do Cap-3 (leitura direta da tabela SENSORES_FARMTECH)
        try:
            import oracledb  # import tardio

            dsn = os.getenv("ORACLE_DSN")
            user = os.getenv("ORACLE_USER")
            pwd = os.getenv("ORACLE_PASSWORD")
            if dsn and user and pwd:
                with oracledb.connect(user=user, password=pwd, dsn=dsn) as conn:
                    df = pd.read_sql("SELECT * FROM SENSORES_FARMTECH", conn)
                    if not df.empty:
                        return _normalizar_colunas(df)
        except Exception:  # pragma: no cover - fallback silencioso
            pass

    # ---- Modo CLOUD (e fallback geral): parquet versionado ----
    if DATA_PATH.exists():
        try:
            return _normalizar_colunas(pd.read_parquet(DATA_PATH))
        except Exception:  # pragma: no cover - pyarrow ausente, tenta CSV processado
            pass

    # ---- Fallback: CSV processado irmao (preserva alvos engenheirados) ----
    csv_proc = DATA_PATH.with_suffix(".csv")
    if csv_proc.exists():
        try:
            return _normalizar_colunas(pd.read_csv(csv_proc))
        except Exception:  # pragma: no cover
            pass

    # ---- Ultimo recurso: CSV bruto ----
    if RAW_CSV.exists():
        return _normalizar_colunas(pd.read_csv(RAW_CSV))

    # Nada encontrado: DataFrame vazio (a UI avisa o usuario).
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_metrics() -> dict:
    """Le models/metrics.json (metricas dos modelos). Retorna {} se ausente."""
    path = MODELS_DIR / "metrics.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # pragma: no cover
            return {}
    return {}


@st.cache_resource(show_spinner=False)
def load_model(alvo: str):
    """Carrega (e mantem em cache de recurso) um modelo .joblib pelo nome do alvo."""
    nome = MODELOS.get(alvo)
    if not nome:
        return None
    path = MODELS_DIR / nome
    if not path.exists():
        return None
    try:
        import joblib

        # Seguranca: carregamos apenas modelos PROPRIOS, gerados por ml/train.py
        # neste mesmo repositorio (artefatos confiaveis e versionados). Nao ha
        # desserializacao de fontes externas/nao confiaveis.
        return joblib.load(path)
    except Exception:  # pragma: no cover
        return None


# ---------------------------------------------------------------------------
# 4. ENGENHARIA DE FEATURES PARA PREVISAO
# ---------------------------------------------------------------------------

def montar_features(temperatura, n, p, k, estado_bomba, id_pivo, hora, dia_semana) -> pd.DataFrame:
    """
    Constroi a linha de features esperada pelos modelos.

    Features do contrato: temperatura, n, p, k, estado_bomba (1=ON/0=OFF),
    id_pivo one-hot (p1/p2/p3), hora e dia_semana.
    """
    linha = {
        "temperatura": float(temperatura),
        "n": float(n),
        "p": float(p),
        "k": float(k),
        "estado_bomba_bin": int(estado_bomba),
        "hora": int(hora),
        "dia_semana": int(dia_semana),
        # one-hot do pivo
        "id_pivo_p1": 1 if id_pivo == "p1" else 0,
        "id_pivo_p2": 1 if id_pivo == "p2" else 0,
        "id_pivo_p3": 1 if id_pivo == "p3" else 0,
    }
    return pd.DataFrame([linha])


def prever(alvo: str, X: pd.DataFrame):
    """Aplica o modelo do alvo, alinhando as colunas ao que ele espera."""
    modelo = load_model(alvo)
    if modelo is None:
        return None
    Xm = X
    # Alinha as colunas a feature_names_in_ do modelo (preenche faltantes com 0).
    nomes = getattr(modelo, "feature_names_in_", None)
    if nomes is not None:
        Xm = X.reindex(columns=list(nomes), fill_value=0)
    try:
        return float(modelo.predict(Xm)[0])
    except Exception:  # pragma: no cover
        return None


# ---------------------------------------------------------------------------
# 5. SIDEBAR (titulo FarmTech + seletor de pivo + status da fonte)
# ---------------------------------------------------------------------------

def render_sidebar(df: pd.DataFrame) -> str:
    """Desenha a barra lateral e retorna o pivo selecionado."""
    st.sidebar.title("🌱 FarmTech Solutions")
    st.sidebar.caption("Assistente Agricola Inteligente · Fase 4 / Cap. 1")
    st.sidebar.markdown("---")

    # Lista de pivos disponiveis (com opcao "Todos").
    if not df.empty and "id_pivo" in df.columns:
        pivos = sorted(df["id_pivo"].dropna().astype(str).unique().tolist())
    else:
        pivos = ["p1", "p2", "p3"]
    opcoes = ["Todos"] + pivos
    pivo = st.sidebar.selectbox("Pivo de irrigacao", opcoes, index=0)

    st.sidebar.markdown("---")
    # Status da fonte de dados (transparencia para o avaliador).
    fonte_label = "☁️ Cloud (parquet/joblib)" if DATA_SOURCE == "cloud" else "🖥️ Local (API/Oracle)"
    st.sidebar.write(f"**Fonte de dados:** {fonte_label}")
    st.sidebar.write(f"**Registros:** {len(df)}")
    st.sidebar.caption(f"RM 572399 · Jefferson G. Lemos")
    return pivo


def filtrar_por_pivo(df: pd.DataFrame, pivo: str) -> pd.DataFrame:
    """Aplica o filtro de pivo escolhido na sidebar."""
    if pivo and pivo != "Todos" and "id_pivo" in df.columns:
        return df[df["id_pivo"].astype(str) == pivo]
    return df


# ---------------------------------------------------------------------------
# 6. ABAS ANALITICAS (conceito reaproveitado do dashboard do Cap-3)
# ---------------------------------------------------------------------------

def aba_visao_geral(df: pd.DataFrame) -> None:
    """KPIs e series temporais das variaveis-chave."""
    st.subheader("📈 Visao Geral")
    if df.empty:
        st.info("Sem dados disponiveis. Gere o dataset processado ou ajuste DATA_SOURCE.")
        return

    # KPIs principais.
    c1, c2, c3, c4 = st.columns(4)
    if "umidade" in df.columns:
        c1.metric("Umidade media (%)", f"{df['umidade'].mean():.1f}")
    if "temperatura" in df.columns:
        c2.metric("Temperatura media (C)", f"{df['temperatura'].mean():.1f}")
    if "ph" in df.columns:
        c3.metric("pH medio", f"{df['ph'].mean():.2f}")
    if "estado_bomba" in df.columns:
        ligadas = (df["estado_bomba"].astype(str).str.upper().eq("ON") | df["estado_bomba"].eq(1)).mean()
        c4.metric("Bomba ligada (%)", f"{ligadas * 100:.0f}")

    # Serie temporal de umidade e temperatura.
    if "capturado_em" in df.columns and not df["capturado_em"].isna().all():
        d = df.sort_values("capturado_em")
        cols = [c for c in ("umidade", "temperatura") if c in d.columns]
        if cols:
            fig = px.line(
                d, x="capturado_em", y=cols,
                labels={"value": "Valor", "capturado_em": "Captura", "variable": "Variavel"},
                color_discrete_sequence=[CORES["agua"], CORES["alerta"]],
            )
            fig.update_layout(legend_title_text="", margin=dict(t=10))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Sem coluna temporal (capturado_em) para a serie.")


def aba_npk_ph(df: pd.DataFrame) -> None:
    """Distribuicao de nutrientes (N, P, K) e pH."""
    st.subheader("🧪 NPK e pH")
    if df.empty:
        st.info("Sem dados para nutrientes.")
        return

    col1, col2 = st.columns(2)
    npk = [c for c in ("n", "p", "k") if c in df.columns]
    if npk:
        medias = df[npk].mean().reset_index()
        medias.columns = ["nutriente", "valor"]
        fig = px.bar(
            medias, x="nutriente", y="valor", text_auto=".1f",
            color="nutriente",
            color_discrete_sequence=[CORES["verde"], CORES["verde_claro"], CORES["terra"]],
        )
        fig.update_layout(showlegend=False, margin=dict(t=10), title="Media de NPK")
        col1.plotly_chart(fig, use_container_width=True)

    if "ph" in df.columns:
        fig2 = px.histogram(df, x="ph", nbins=30, color_discrete_sequence=[CORES["verde"]])
        # Faixa boa de pH (6.0-7.0) destacada.
        fig2.add_vrect(x0=6.0, x1=7.0, fillcolor=CORES["verde_claro"], opacity=0.25, line_width=0)
        fig2.update_layout(margin=dict(t=10), title="Distribuicao de pH (faixa boa 6.0-7.0)")
        col2.plotly_chart(fig2, use_container_width=True)


def aba_irrigacao(df: pd.DataFrame) -> None:
    """Relacao umidade x bomba e estado de irrigacao."""
    st.subheader("💧 Irrigacao")
    if df.empty:
        st.info("Sem dados de irrigacao.")
        return

    col1, col2 = st.columns(2)
    if "estado_bomba" in df.columns:
        serie = df["estado_bomba"].astype(str).str.upper().replace({"1": "ON", "0": "OFF"})
        cont = serie.value_counts().reset_index()
        cont.columns = ["estado", "contagem"]
        fig = px.pie(
            cont, names="estado", values="contagem", hole=0.45,
            color_discrete_sequence=[CORES["agua"], CORES["terra"]],
        )
        fig.update_layout(margin=dict(t=10), title="Estado da bomba")
        col1.plotly_chart(fig, use_container_width=True)

    if {"umidade", "temperatura"}.issubset(df.columns):
        cor = "estado_bomba" if "estado_bomba" in df.columns else None
        fig2 = px.scatter(
            df, x="umidade", y="temperatura", color=cor, opacity=0.6,
            labels={"umidade": "Umidade (%)", "temperatura": "Temperatura (C)"},
        )
        fig2.update_layout(margin=dict(t=10), title="Umidade x Temperatura")
        col2.plotly_chart(fig2, use_container_width=True)

    # Se o alvo engenheirado de volume existir no dataset, mostra sua distribuicao.
    if "volume_irrigacao" in df.columns:
        fig3 = px.histogram(df, x="volume_irrigacao", nbins=30, color_discrete_sequence=[CORES["agua"]])
        fig3.update_layout(margin=dict(t=10), title="Distribuicao do volume de irrigacao (mm)")
        st.plotly_chart(fig3, use_container_width=True)


def aba_correlacoes(df: pd.DataFrame) -> None:
    """Mapa de calor de correlacao entre variaveis numericas."""
    st.subheader("🔗 Correlacoes")
    if df.empty:
        st.info("Sem dados para correlacao.")
        return

    num = df.select_dtypes(include="number")
    if num.shape[1] < 2:
        st.caption("Variaveis numericas insuficientes para correlacao.")
        return

    corr = num.corr(numeric_only=True)
    fig = px.imshow(
        corr, text_auto=".2f", aspect="auto",
        color_continuous_scale="RdYlGn", zmin=-1, zmax=1,
    )
    fig.update_layout(margin=dict(t=10), title="Matriz de correlacao")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# 7. ABA DE PREVISOES (inputs do usuario -> modelos -> 5 alvos + metricas)
# ---------------------------------------------------------------------------

def aba_previsoes(id_pivo: str) -> dict:
    """
    Coleta entradas via sliders, aplica os 5 modelos e exibe previsoes + metricas.

    Retorna o dicionario {alvo: valor_previsto} (usado pela aba de Sugestoes).
    """
    st.subheader("🔮 Previsoes")
    st.caption("Ajuste as condicoes do pivo e veja a previsao dos 5 alvos agronomicos.")

    # --- Entradas do usuario ---
    c1, c2, c3 = st.columns(3)
    with c1:
        temperatura = st.slider("Temperatura (C)", 0.0, 50.0, 25.0, 0.1)
        hora = st.slider("Hora do dia", 0, 23, 12)
    with c2:
        n = st.slider("Nitrogenio (N)", 0, 140, 70)
        p = st.slider("Fosforo (P)", 0, 140, 60)
    with c3:
        k = st.slider("Potassio (K)", 0, 200, 60)
        dia_semana = st.selectbox(
            "Dia da semana",
            options=list(range(7)),
            format_func=lambda d: ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"][d],
            index=0,
        )

    bomba_label = st.radio("Estado da bomba", ["ON", "OFF"], horizontal=True, index=0)
    estado_bomba = 1 if bomba_label == "ON" else 0

    # Pivo: usa o da sidebar, salvo "Todos" (entao default p1).
    pivo_modelo = id_pivo if id_pivo in ("p1", "p2", "p3") else "p1"
    st.caption(f"Pivo considerado na previsao: **{pivo_modelo}**")

    # --- Previsoes ---
    X = montar_features(temperatura, n, p, k, estado_bomba, pivo_modelo, hora, dia_semana)
    metrics = load_metrics()
    previsoes: dict = {}

    cols = st.columns(len(ALVOS_INFO))
    algum_modelo = False
    for (alvo, (rotulo, unidade, emoji)), col in zip(ALVOS_INFO.items(), cols):
        valor = prever(alvo, X)
        if valor is None:
            col.metric(f"{emoji} {rotulo}", "—")
            col.caption("modelo ausente")
            continue
        algum_modelo = True
        previsoes[alvo] = valor
        texto = f"{valor:.2f} {unidade}".strip()
        col.metric(f"{emoji} {rotulo}", texto)

        # Metricas do modelo (toleranre a chaves em maiusculo/minusculo).
        m = metrics.get(alvo, {}) if isinstance(metrics, dict) else {}
        def _get(k1):
            for kk in (k1, k1.upper(), k1.lower()):
                if kk in m:
                    return m[kk]
            return None
        r2, mae, rmse = _get("r2"), _get("mae"), _get("rmse")
        partes = []
        if r2 is not None:
            partes.append(f"R2 {float(r2):.3f}")
        if mae is not None:
            partes.append(f"MAE {float(mae):.2f}")
        if rmse is not None:
            partes.append(f"RMSE {float(rmse):.2f}")
        if partes:
            col.caption(" · ".join(partes))

    if not algum_modelo:
        st.warning(
            "Nenhum modelo .joblib encontrado em "
            f"`{MODELS_DIR}`. Treine os modelos (ml/train.py) para habilitar as previsoes."
        )

    return previsoes


# ---------------------------------------------------------------------------
# 8. ABA DE SUGESTOES DE MANEJO (delegada a ml/suggest.py)
# ---------------------------------------------------------------------------

def _sugestoes_fallback(previsoes: dict) -> list[str]:
    """Heuristica simples caso ml/suggest.py nao esteja disponivel."""
    msgs: list[str] = []
    vol = previsoes.get("volume_irrigacao")
    if vol is not None:
        if vol > 5:
            msgs.append(f"Irrigar: aplicar ~{vol:.1f} mm para repor a umidade do solo.")
        else:
            msgs.append("Umidade adequada: irrigacao nao prioritaria no momento.")
    fert = previsoes.get("necessidade_fertilizacao")
    if fert is not None:
        if fert > 50:
            msgs.append(f"Fertilizacao alta (indice {fert:.0f}): reforcar NPK conforme analise de solo.")
        elif fert > 20:
            msgs.append(f"Fertilizacao moderada (indice {fert:.0f}): ajuste pontual de nutrientes.")
        else:
            msgs.append("Nutricao equilibrada: manter o plano de adubacao atual.")
    rend = previsoes.get("rendimento")
    if rend is not None:
        msgs.append(f"Rendimento estimado: {rend:.1f} sacas/ha.")
    if not msgs:
        msgs.append("Gere previsoes na aba anterior para receber sugestoes de manejo.")
    return msgs


def aba_sugestoes(previsoes: dict) -> None:
    """Mostra recomendacoes acionaveis a partir das previsoes."""
    st.subheader("🌱 Sugestoes de Manejo")
    st.caption("Acoes recomendadas com base nas previsoes dos modelos.")

    if not previsoes:
        st.info("Ajuste os parametros na aba '🔮 Previsoes' para gerar sugestoes.")
        return

    # Tenta usar o modulo ml/suggest.py (varios nomes de funcao aceitos).
    sugestoes = None
    try:
        import ml.suggest as suggest_mod  # type: ignore

        for fn_nome in ("gerar_sugestoes", "sugerir_manejo", "suggest", "recomendar"):
            fn = getattr(suggest_mod, fn_nome, None)
            if callable(fn):
                try:
                    sugestoes = fn(previsoes)
                except TypeError:
                    # Algumas assinaturas podem nao receber argumentos.
                    sugestoes = fn()
                break
    except Exception:  # pragma: no cover - usa fallback
        sugestoes = None

    if not sugestoes:
        sugestoes = _sugestoes_fallback(previsoes)

    # Normaliza para uma lista de strings exibiveis.
    if isinstance(sugestoes, dict):
        itens = [f"**{k}:** {v}" for k, v in sugestoes.items()]
    elif isinstance(sugestoes, (list, tuple)):
        itens = [str(s) for s in sugestoes]
    else:
        itens = [str(sugestoes)]

    for item in itens:
        st.success(item)


# ---------------------------------------------------------------------------
# 9. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("🌱 FarmTech — Assistente Agricola Inteligente")
    st.caption("Previsoes de ML para irrigacao e manejo · Fase 4 / Cap. 1 · RM 572399")

    # Carrega os dados conforme a fonte e desenha a sidebar.
    df = load_data(DATA_SOURCE)
    pivo = render_sidebar(df)
    df_filtrado = filtrar_por_pivo(df, pivo)

    # Abas do dashboard.
    abas = st.tabs(
        ["📈 Visao Geral", "🧪 NPK e pH", "💧 Irrigacao", "🔗 Correlacoes",
         "🔮 Previsoes", "🌱 Sugestoes de Manejo"]
    )

    with abas[0]:
        aba_visao_geral(df_filtrado)
    with abas[1]:
        aba_npk_ph(df_filtrado)
    with abas[2]:
        aba_irrigacao(df_filtrado)
    with abas[3]:
        aba_correlacoes(df_filtrado)

    # As previsoes alimentam a aba de sugestoes (estado compartilhado na sessao).
    with abas[4]:
        previsoes = aba_previsoes(pivo)
        st.session_state["previsoes"] = previsoes
    with abas[5]:
        aba_sugestoes(st.session_state.get("previsoes", {}))


if __name__ == "__main__":
    main()
