# Dockerfile do dashboard Streamlit — FarmTech Solutions (Fase 4 / Cap. 1)
#
# IMPORTANTE: o build deve ser feito a partir da RAIZ do projeto
# (/projetos/fiap/1-semestre/fase4cap1), pois a imagem precisa de:
#   - streamlit/        (app + config)
#   - ml/               (suggest.py usado nas sugestoes de manejo)
#   - models/           (modelos .joblib + metrics.json) — modo "cloud"
#   - data/processed/   (dataset_ml.parquet) — modo "cloud"
#
# Exemplo de build/run:
#   docker build -f streamlit/Dockerfile -t farmtech-streamlit .
#   docker run -p 8501:8501 -e DATA_SOURCE=cloud farmtech-streamlit

FROM python:3.11-slim

# Boas praticas Python em container.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    DATA_SOURCE=cloud

WORKDIR /app

# 1) Dependencias — copia primeiro o requirements para aproveitar o cache.
#    requirements.txt fica na raiz do projeto (contexto de build).
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# 2) Codigo e artefatos necessarios para o app rodar.
COPY .streamlit/ ./.streamlit/
COPY streamlit/ ./streamlit/
COPY ml/ ./ml/
COPY models/ ./models/
COPY data/ ./data/

# 3) Rede.
EXPOSE 8501

# 4) Healthcheck do Streamlit.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# 5) Sobe o dashboard.
CMD ["streamlit", "run", "streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
