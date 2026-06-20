# FarmTech Solutions — Fase 4, Capítulo 1 · Assistente Agrícola Inteligente
# Imagem da API FastAPI (camada fina da arquitetura híbrida).
# Autor: Jefferson Gonçalves Lemos · RM 572399 — FIAP
#
# IMPORTANTE — contexto de build:
#   Esta imagem deve ser construída a partir da RAIZ do projeto
#   (e não de dentro de api/), porque a
#   aplicação importa os pacotes irmãos `db` e `ml` e usa `models/` e
#   `data/processed/`. No docker-compose declare:
#
#       services:
#         api:
#           build:
#             context: .
#             dockerfile: api/Dockerfile
#           ports:
#             - "8000:8000"
#
# Build manual equivalente (a partir da raiz):
#       docker build -f api/Dockerfile -t farmtech-api .

FROM python:3.11-slim

# Boas práticas de runtime Python em container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Garante que `db`, `ml`, `api` sejam importáveis como pacotes de topo.
    PYTHONPATH=/app

WORKDIR /app

# 1) Dependências primeiro (camada cacheável): requirements.txt da raiz do projeto.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 2) Código da aplicação e pacotes/artefatos necessários em runtime.
#    Copia o projeto inteiro (contexto = raiz) para que api/ + db/ + ml/ +
#    models/ + data/processed convivam sob /app.
COPY . .

# API FastAPI escuta na porta 8000 (uvicorn).
EXPOSE 8000

# Sobe o servidor ASGI servindo o objeto `app` de api/main.py.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
