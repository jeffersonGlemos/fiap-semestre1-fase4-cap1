# FarmTech Solutions — Fase 4, Capítulo 1

## Assistente Agrícola Inteligente

**Autor:** Jefferson Gonçalves Lemos · **RM:** 572399
**Disciplina:** Inteligência Artificial — FIAP
**Data:** 2026

---

## Objetivo

Construir um protótipo de **Assistente Agrícola Inteligente** que transforma dados de
sensores IoT (umidade, temperatura, pH, NPK e estado da bomba) em **conhecimento acionável**,
fechando o ciclo da *Agricultura Cognitiva*:

1. **Coleta** — sensores reais/simulados (ESP32/Wokwi) alimentam um histórico de leituras.
2. **Armazenamento** — os dados são persistidos em banco relacional (Oracle XE reaproveitado
   do Cap-3, tabela `SENSORES_FARMTECH`).
3. **Aprendizado** — modelos de **regressão supervisionada** (Scikit-Learn) preveem variáveis
   críticas do campo: rendimento, volume de irrigação, necessidade de fertilização, umidade e pH.
4. **Decisão** — o dashboard **Streamlit** apresenta métricas, correlações e previsões em tempo
   real, sugerindo ações futuras de irrigação e manejo para o gestor agrícola.

A solução é **híbrida**: roda localmente integrada ao Oracle/API, mas também publica um dashboard
**online** (Streamlit Cloud) que opera de forma autônoma a partir de artefatos versionados no
repositório.

---

## Arquitetura híbrida

```
                          ┌──────────────────────────────────────────────────────────┐
                          │                     ORIGEM DOS DADOS                     │
                          │  Sensores IoT (ESP32 / Wokwi)  ·  seed_data.csv (2696)   │
                          │  colunas: ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K,    │
                          │           ESTADO_BOMBA, CAPTURADO_EM                     │
                          └───────────────────────────┬──────────────────────────────┘
                                                      │ ingestão
                                                      ▼
                          ┌──────────────────────────────────────────────────────────┐
                          │        ORACLE XE  (REUSADO do Cap-3 — EXTERNO)           │
                          │  Cap-3/fase3_cap1 · localhost:1521 · service XEPDB1      │
                          │  Tabela SENSORES_FARMTECH (+ coluna virtual PERIODO)     │
                          └───────────────────────────┬──────────────────────────────┘
                                                      │ ORACLE_DSN / USER / PASSWORD
                                                      ▼
        ┌─────────────────────────────────────────────────────────────────────────────────────┐
        │                            PIPELINE DE MACHINE LEARNING                              │
        │                                                                                     │
        │   ml/prepare_dataset.py  ──►  data/processed/dataset_ml.parquet                     │
        │       (limpeza + engenharia de features e dos alvos simulados)                      │
        │                                       │                                             │
        │                                       ▼                                             │
        │   ml/train.py  ──►  GridSearchCV (cv=5) sobre                                       │
        │       LinearRegression · Ridge · RandomForestRegressor                              │
        │                                       │                                             │
        │                                       ▼                                             │
        │   models/*.joblib  (5 modelos)  +  models/metrics.json  (MAE/MSE/RMSE/R²)           │
        └───────────────────────────────────────┬─────────────────────────────────────────────┘
                                                │
                  ┌─────────────────────────────┴─────────────────────────────┐
                  ▼                                                            ▼
   ┌───────────────────────────────┐                        ┌────────────────────────────────────┐
   │  api/  — FastAPI  (:8000)     │                        │  streamlit/app.py  (:8501)         │
   │  expõe dados Oracle + preds   │◄──────  API_URL ──────►│  dashboard interativo do gestor    │
   └───────────────────────────────┘                        └────────────────┬───────────────────┘
                                                                             │ DATA_SOURCE
                                          ┌──────────────────────────────────┴──────────────────────────────┐
                                          │  local  →  consome API / Oracle (Cap-3)                          │
                                          │  cloud  →  lê data/processed/dataset_ml.parquet + models/*.joblib │
                                          └───────────────────────────────────────────────────────────────────┘
                                                                             │
                                                                             ▼
                                                       ☁  DEPLOY ONLINE (Streamlit Cloud)
                                                       Não alcança o Oracle local: opera 100%
                                                       a partir dos artefatos versionados no repo
                                                       (DATA_SOURCE=cloud).  Ver docs/DEPLOY.md
```

> **docker-compose deste projeto** sobe apenas **api** (FastAPI :8000) + **streamlit** (:8501).
> O **Oracle é externo**, fornecido pelo `docker-compose` do **Cap-3** (`1-semestre/Cap-3/fase3_cap1`).

---

## Estrutura de diretórios

```
fase4cap1/
├── README.md                       # este arquivo — visão geral do projeto
├── enunciado.md                    # enunciado oficial da Fase 4 (FIAP)
├── analise_gap.md                  # análise enunciado × já implementado (reuso Cap-2/Cap-3)
├── requirements.txt                # dependências Python (sklearn, pandas, streamlit, fastapi...)
├── docker-compose.yml              # sobe api + streamlit (Oracle vem do Cap-3, externo)
│
├── data/
│   ├── raw/
│   │   └── seed_data.csv           # dataset bruto: 2696 leituras de sensores (header + dados)
│   └── processed/
│       └── dataset_ml.parquet      # dataset pronto p/ ML (gerado por prepare_dataset.py)
│
├── ml/                             # PARTE 1 + PARTE 2 — pipeline de Machine Learning
│   ├── prepare_dataset.py          # limpeza + features + engenharia dos alvos simulados
│   ├── train.py                    # treino, GridSearchCV, métricas e persistência dos modelos
│   └── notebook.ipynb              # exploração, correlações e justificativa das decisões (PARTE 2)
│
├── models/                         # artefatos treinados (versionados p/ deploy cloud)
│   ├── modelo_rendimento.joblib
│   ├── modelo_volume_irrigacao.joblib
│   ├── modelo_necessidade_fertilizacao.joblib
│   ├── modelo_umidade.joblib
│   ├── modelo_ph.joblib
│   └── metrics.json                # MAE, MSE, RMSE, R² de cada alvo/algoritmo
│
├── api/                            # FastAPI (:8000) — expõe dados Oracle e previsões
│
├── streamlit/                      # PARTE 1 + IR ALÉM 2 — dashboard do gestor agrícola
│   ├── app.py                      # fonte de dados comutável via DATA_SOURCE (local|cloud)
│   └── .streamlit/                 # configuração/segredos do Streamlit (deploy)
│
├── db/                             # IR ALÉM 1 — modelagem e ingestão IoT (Oracle Cap-3)
│
└── docs/
    ├── DEPLOY.md                   # guia de publicação do dashboard online (Streamlit Cloud)
    └── roteiros/                   # roteiros dos vídeos de entrega (PARTE 1, 2, IR ALÉM 1 e 2)
```

---

## Mapa enunciado → arquivos

| Item do enunciado | Descrição | Onde está |
|---|---|---|
| **PARTE 1** — ML + Streamlit | Pipeline Scikit-Learn integrado a dashboard interativo (métricas, correlações, previsões em tempo real) | `ml/` + `streamlit/app.py` |
| **PARTE 2** — Algoritmos preditivos | Modelos de regressão (linear, múltipla, não-linear) para volume de irrigação, necessidade de fertilização e rendimento, avaliados por MAE/MSE/RMSE/R² | `ml/train.py` + `ml/notebook.ipynb` |
| **IR ALÉM 1** — Banco de dados IoT | Modelagem e ingestão/atualização dos dados de sensores em banco SQL (Oracle XE reaproveitado do Cap-3) | `db/` (+ Oracle do Cap-3) |
| **IR ALÉM 2** — Dashboard online | Dashboard analítico interativo e **online** com correlações, previsões e tendências de produtividade | `streamlit/` + `docs/DEPLOY.md` |

---

## Como rodar

> Pré-requisitos: Python 3.11+, Docker/Docker Compose e o repositório do **Cap-3** disponível em
> `1-semestre/Cap-3/fase3_cap1` (fornece o Oracle XE).

**1. Subir o Oracle do Cap-3** (fonte de dados externa)

```bash
cd ../Cap-3/fase3_cap1
docker compose up -d        # Oracle XE em localhost:1521 · service XEPDB1
```

**2. Instalar as dependências Python**

```bash
pip install -r requirements.txt
```

**3. Preparar o dataset** (limpeza + features + engenharia dos alvos)

```bash
python ml/prepare_dataset.py        # gera data/processed/dataset_ml.parquet
```

**4. Treinar os modelos de regressão**

```bash
python ml/train.py                  # gera models/*.joblib + models/metrics.json
```

**5. Rodar o dashboard Streamlit**

```bash
streamlit run streamlit/app.py      # dashboard em http://localhost:8501
```

**6. (Opcional) Subir tudo via Docker Compose** (api + streamlit)

```bash
docker compose up                   # api :8000 + streamlit :8501 (Oracle vem do Cap-3)
```

### Variáveis de ambiente

| Variável | Componente | Descrição |
|---|---|---|
| `ORACLE_DSN`, `ORACLE_USER`, `ORACLE_PASSWORD` | api / db | Conexão com o Oracle XE do Cap-3 |
| `DATA_SOURCE` | streamlit | `local` (API/Oracle) ou `cloud` (parquet + joblib do repo) |
| `API_URL` | streamlit | URL da API FastAPI (modo local) |
| `MODELS_DIR`, `DATA_PATH` | ml / streamlit / api | Caminhos dos modelos e do dataset processado |

---

## Alvos de regressão e features

### Alvos previstos pelos modelos

| Alvo | Unidade / faixa | Natureza |
|---|---|---|
| `rendimento` | sacas/ha (0–80) | **Engenheirado** (heurística agronômica) |
| `volume_irrigacao` | mm (0–40) | **Engenheirado** |
| `necessidade_fertilizacao` | índice (0–100) | **Engenheirado** |
| `umidade` | % | **Real** (medido pelos sensores) |
| `ph` | — | **Real** (medido pelos sensores) |

### Features de entrada (por-alvo)

Cada alvo é treinado com o conjunto de features adequado, evitando *data leakage*
(um alvo nunca é feature de si mesmo):

- **Features base** (todos os modelos): `temperatura`, `n`, `p`, `k`,
  `estado_bomba_bin` (1=ON, 0=OFF), `id_pivo` (one-hot p1/p2/p3),
  `hora` e `dia_semana` (derivadas de `capturado_em`).
- **Features de contexto** (`umidade`, `ph`): adicionadas **apenas** aos alvos
  **engenheirados** (`rendimento`, `volume_irrigacao`, `necessidade_fertilizacao`),
  que dependem delas por construção. Os alvos **reais** (`umidade`, `ph`) usam
  somente as features base.

> **Por que isso importa:** o `rendimento` é função de umidade+pH. Sem essas duas
> como features, o modelo previa mal (R² ≈ 0,10). Com features por-alvo, o R² do
> rendimento sobe para **≈ 0,88** (e o de `volume_irrigacao` para **≈ 0,94**),
> sem vazamento. O conjunto efetivo de cada modelo fica registrado em
> `models/metrics.json` (campo `feature_columns`).

### Modelos e métricas

- **Algoritmos (Scikit-Learn):** `LinearRegression` (baseline), `Ridge` e
  `RandomForestRegressor` (não-linear), selecionados via **GridSearchCV (cv=5)**.
- **Split:** treino/teste **80/20**, `random_state=42`.
- **Métricas:** **MAE, MSE, RMSE e R²**, registradas em `models/metrics.json`.

---

## Nota de transparência — alvos simulados

Três dos cinco alvos (`rendimento`, `volume_irrigacao` e `necessidade_fertilizacao`) **não existem
nos dados brutos dos sensores**. Eles são **engenheirados por heurísticas agronômicas** em
`ml/prepare_dataset.py`, usando funções-sino (`bell(x, ótimo, desvio) = exp(-0.5·((x-ótimo)/desvio)²)`)
sobre as faixas ideais de umidade (~62,5%), pH (~6,5), temperatura (~25 °C) e NPK (N≈70, P≈60, K≈60),
com ruído gaussiano controlado e `numpy seed 42` para reprodutibilidade.

Isso significa que o desempenho desses três modelos reflete a **consistência da heurística**, e não
uma verdade de campo. Os alvos `umidade` e `ph`, em contraste, são **medições reais** dos sensores.
Essa distinção é assumida explicitamente: o objetivo é demonstrar o **pipeline completo de regressão**
(preparação → treino → avaliação → integração ao dashboard), e os alvos simulados servem de
*proxy* didático até que rótulos reais de produtividade estejam disponíveis.

---

## Documentação e roteiros

- **`docs/DEPLOY.md`** — guia de publicação do dashboard online (Streamlit Cloud, modo `DATA_SOURCE=cloud`).
- **`docs/roteiros/`** — roteiros dos vídeos de entrega (PARTE 1, PARTE 2, IR ALÉM 1 e IR ALÉM 2).
- **`enunciado.md`** — enunciado oficial da atividade da Fase 4.
- **`analise_gap.md`** — análise do que o enunciado pede × o que já existe nos capítulos anteriores
  (reaproveitamento de dados, banco e dashboard dos Cap-2 e Cap-3).
