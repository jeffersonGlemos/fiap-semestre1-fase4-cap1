# Arquitetura — FarmTech Solutions · Fase 4, Capítulo 1

**Assistente Agrícola Inteligente**

- Autor: **Jefferson Gonçalves Lemos** · RM **572399**
- Disciplina: **Inteligência Artificial — FIAP**
- Diretório base: `/projetos/fiap/1-semestre/fase4cap1`

Este documento descreve em detalhe a **arquitetura híbrida** do projeto: seus
componentes, o fluxo de dados ponta a ponta (IoT → Banco → ML → Dashboard), as
decisões de design que sustentam essas escolhas e como cada parte mapeia para o
enunciado da Fase 4.

---

## 1. Visão geral

O projeto transforma dados agrícolas de sensores IoT em **previsões e sugestões
de manejo** entregues a um gestor agrícola por meio de um dashboard interativo.

A solução é **híbrida** em dois sentidos complementares:

1. **Reúso de infraestrutura de fases anteriores.** O banco de dados Oracle XE,
   os sensores simulados e o esquema relacional já construídos no **Cap-3** são
   reaproveitados em vez de recriados. A Fase 4 acrescenta a camada de
   Inteligência Artificial sobre essa base existente.
2. **Fonte de dados comutável.** O dashboard funciona em dois modos
   (`DATA_SOURCE=local` e `DATA_SOURCE=cloud`), permitindo rodar localmente
   conectado ao Oracle/API ou publicado online lendo artefatos versionados no
   repositório (Parquet + modelos `.joblib`).

```
            ┌──────────────────────────────────────────────────────────────┐
            │                  FarmTech — Fase 4, Cap 1                      │
            │                  (este projeto: fase4cap1)                     │
            └──────────────────────────────────────────────────────────────┘

   REUSADO DO CAP-3                  NOVO NA FASE 4 (camada de IA)
 ┌───────────────────┐      ┌───────────────────────────────────────────────┐
 │  Oracle XE        │      │  prepare_dataset → train → models → api/streamlit│
 │  SENSORES_FARMTECH│      └───────────────────────────────────────────────┘
 └───────────────────┘
```

---

## 2. Componentes

### 2.1 Oracle XE (reusado do Cap-3) — `1-semestre/Cap-3/fase3_cap1`

- Banco **Oracle XE** que armazena os dados de sensores IoT na tabela
  **`SENSORES_FARMTECH`**, com as mesmas colunas do CSV
  (`ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM`)
  acrescidas de uma **coluna virtual `PERIODO`** (derivada de `CAPTURADO_EM`).
- O **`docker-compose` do Cap-3** sobe o Oracle em `localhost:1521`, serviço
  **`XEPDB1`**. Este projeto **não** sobe Oracle próprio: ele consome o Oracle do
  Cap-3 como dependência externa.
- Conexão por variáveis de ambiente: `ORACLE_DSN`, `ORACLE_USER`,
  `ORACLE_PASSWORD`.

> Por ser uma dependência externa, o Oracle só está disponível no modo **local**.
> No deploy online (Streamlit Cloud) ele é substituído pelos artefatos
> versionados — ver seção 4.3.

### 2.2 `data/raw/seed_data.csv`

- Dataset bruto de sensores: **2696 linhas de dados + header**.
- Colunas: `ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM`.
- Domínios: `ESTADO_BOMBA ∈ {ON, OFF}`, `ID_PIVO ∈ {p1, p2, p3}`,
  `CAPTURADO_EM` é timestamp.
- É a **fonte de verdade** dos dados de entrada, podendo ser ingerido no Oracle
  (Cap-3) ou lido diretamente pelo `prepare_dataset.py`.

### 2.3 `ml/prepare_dataset.py` — preparação e engenharia de atributos

Responsável por transformar o CSV bruto no dataset de ML:

- **Limpeza e tipagem** das colunas.
- **Derivação temporal:** extrai `hora` e `dia_semana` de `capturado_em`.
- **Codificação:** `estado_bomba` → `{ON:1, OFF:0}`; `id_pivo` → one-hot
  (`p1`/`p2`/`p3`).
- **Engenharia dos alvos** (numpy `seed=42`), simulando por heurística
  agronômica três alvos que **não existem nos dados brutos** — `rendimento`,
  `volume_irrigacao`, `necessidade_fertilizacao` — além de manter os alvos
  **reais** `umidade` e `ph`.
- **Saída:** `data/processed/dataset_ml.parquet`.

Função-base usada na engenharia (sino gaussiano):

```
bell(x, opt, sd) = exp(-0.5 * ((x - opt) / sd) ** 2)   # 0..1
```

Constantes agronômicas (centro ótimo / desvio): umidade `62.5 / 12`,
pH `6.5 / 0.6`, temperatura `25 / 7`; ideais de nutrientes `N=70`, `P=60`,
`K=60`; umidade-alvo de irrigação `65`.

Fórmulas dos alvos engenheirados:

```
f_npk = média( bell(N,70,25), bell(P,60,25), bell(K,60,25) )

rendimento = clip( 80 * bell(umidade,62.5,12) * bell(ph,6.5,0.6)
                      * f_npk * bell(temperatura,25,7)
                      + ruído_normal(0,3), 0, 80 )

volume_irrigacao = clip( max(0, 65 - umidade)*0.8
                         + 0.15*max(0, temperatura-20)
                         + ruído_normal(0,1.5), 0, 40 )

necessidade_fertilizacao = clip(
    (relu(70-N) + relu(60-P) + relu(60-K)) / (70+60+60) * 100
    + ruído_normal(0,3), 0, 100 )     # relu(x) = max(0, x)
```

### 2.4 `ml/train.py` — treinamento e seleção de modelos

- **Features de entrada:** `temperatura, n, p, k, estado_bomba`
  (1=ON / 0=OFF), `id_pivo` (one-hot p1/p2/p3), `hora` e `dia_semana`.
- **Cinco alvos de regressão**, cada um com seu próprio modelo:
  `rendimento`, `volume_irrigacao`, `necessidade_fertilizacao`, `umidade`, `ph`.
- **Algoritmos (Scikit-Learn):** `LinearRegression` (baseline), `Ridge`
  e `RandomForestRegressor` (não-linear).
- **Seleção:** `GridSearchCV` com `cv=5`; melhor estimador por alvo.
- **Split:** treino/teste **80/20**, `random_state=42`.
- **Métricas:** **MAE, MSE, RMSE, R²** — gravadas em `models/metrics.json`.
- **Saída:** modelos serializados em `models/` (`joblib`).

### 2.5 `models/` — artefatos versionados

```
models/
├── modelo_rendimento.joblib
├── modelo_volume_irrigacao.joblib
├── modelo_necessidade_fertilizacao.joblib
├── modelo_umidade.joblib
├── modelo_ph.joblib
└── metrics.json
```

Versionados no repositório para que o deploy online (modo `cloud`) os carregue
sem precisar treinar.

### 2.6 `db/` — banco IoT (IR ALÉM 1)

Scripts e DDL que materializam a integração dos dados IoT no banco SQL
(tabela `SENSORES_FARMTECH` + coluna virtual `PERIODO`), incluindo o processo
de ingestão/atualização dos dados de sensores. Reaproveita o esquema do Cap-3.

### 2.7 `api/` — FastAPI (`:8000`)

- Expõe os dados do Oracle e/ou as previsões dos modelos via HTTP.
- Consumida pelo Streamlit no modo **local** (`API_URL`).
- Configurada por `ORACLE_DSN/USER/PASSWORD`, `MODELS_DIR`, `DATA_PATH`.

### 2.8 `streamlit/app.py` — Dashboard (`:8501`)

- Interface do gestor agrícola: métricas de desempenho dos modelos,
  gráficos de correlação, previsões interativas e sugestões de manejo
  (irrigação / fertilização) derivadas das previsões.
- **Fonte de dados comutável** por `DATA_SOURCE`:
  - `local` → consome **API/Oracle**;
  - `cloud` → lê `data/processed/dataset_ml.parquet` + `models/*.joblib`
    versionados no repositório.

---

## 3. Fluxo de dados (IoT → DB → ML → Dashboard)

```
 ┌─────────────────┐
 │  Sensores IoT   │  ESP32 / Wokwi (simulado) — Cap-3
 │  (p1, p2, p3)   │
 └────────┬────────┘
          │  leituras (umidade, temp, pH, N, P, K, bomba, timestamp)
          ▼
 ┌─────────────────────────────┐        ┌──────────────────────────┐
 │  data/raw/seed_data.csv     │───────▶│  Oracle XE (Cap-3)       │
 │  2696 linhas                │ ingest │  SENSORES_FARMTECH       │
 └────────────┬────────────────┘        │  + coluna virtual PERIODO│
              │                          └────────────┬─────────────┘
              │  (modo local: dados vêm do Oracle via API)
              ▼                                        │
 ┌─────────────────────────────┐                       │
 │  ml/prepare_dataset.py      │◀──────────────────────┘
 │  • limpeza / tipagem        │
 │  • hora, dia_semana         │
 │  • one-hot id_pivo          │
 │  • alvos engenheirados      │  numpy seed 42
 └────────────┬────────────────┘
              ▼
 ┌─────────────────────────────┐
 │ data/processed/             │
 │   dataset_ml.parquet        │
 └────────────┬────────────────┘
              ▼
 ┌─────────────────────────────┐
 │  ml/train.py                │  LinearRegression / Ridge / RandomForest
 │  • split 80/20 (rs=42)      │  GridSearchCV cv=5
 │  • 5 modelos (1 por alvo)   │  MAE · MSE · RMSE · R²
 └────────────┬────────────────┘
              ▼
 ┌─────────────────────────────┐
 │  models/*.joblib            │
 │  models/metrics.json        │
 └────────────┬────────────────┘
              ▼
 ┌──────────────────────────────────────────────────────────────┐
 │              streamlit/app.py  (Dashboard :8501)              │
 │                                                              │
 │   DATA_SOURCE=local  ──▶  api/ (FastAPI :8000) ──▶ Oracle XE  │
 │   DATA_SOURCE=cloud  ──▶  dataset_ml.parquet + models/*.joblib│
 │                                                              │
 │   • métricas de desempenho   • gráficos de correlação        │
 │   • previsões interativas    • sugestões de irrigação/manejo │
 └──────────────────────────────────────────────────────────────┘
                              ▲
                              │
                      Gestor agrícola
```

### Orquestração de contêineres

- **`docker-compose` deste projeto:** sobe apenas **`api`** (FastAPI `:8000`) e
  **`streamlit`** (`:8501`).
- **Oracle:** vem do **`docker-compose` do Cap-3** (externo), em
  `localhost:1521`, serviço `XEPDB1`.

---

## 4. Decisões de design

### 4.1 Por que arquitetura híbrida (reúso do Cap-3)

O enunciado pede explicitamente partir "da estrutura lógica e relacional
construída nas fases anteriores". Recriar um banco do zero seria redundante e
contrariaria o objetivo de **consolidação**. Reusar o Oracle XE do Cap-3:

- Evita duplicação de esquema e de geração de dados.
- Mantém uma **única fonte de verdade** para os sensores
  (`SENSORES_FARMTECH` / `seed_data.csv`).
- Concentra o esforço da Fase 4 onde está o gap real: a **camada de IA**
  (regressão, previsões, sugestões e dashboard online).

Por isso o `docker-compose` local sobe só `api` + `streamlit`, tratando o Oracle
como serviço externo já provido pelo Cap-3.

### 4.2 Por que alvos simulados (engenharia agronômica)

A variável **`rendimento`** — alvo central pedido pelo enunciado — **não existe**
em nenhum dataset coletado, assim como `volume_irrigacao` e
`necessidade_fertilizacao`. Em vez de abandonar esses alvos, eles são
**engenheirados por heurística agronômica** a partir das variáveis reais:

- Cada alvo é uma função interpretável das condições do campo (sinos gaussianos
  centrados nos ótimos agronômicos de umidade, pH, temperatura e NPK), somada a
  um **ruído normal controlado** para evitar relação determinística trivial.
- O uso de **numpy `seed=42`** garante **reprodutibilidade** completa do dataset.
- Os alvos **`umidade`** e **`ph`** permanecem **reais**, ancorando o pipeline em
  dados de fato medidos pelos sensores.

Isso permite demonstrar regressão linear, múltipla e não-linear com métricas
significativas, mantendo coerência agronômica nas sugestões de manejo. As
fórmulas e constantes estão documentadas (seção 2.3) para total transparência.

### 4.3 Por que fonte de dados comutável (`DATA_SOURCE`)

O deploy online no **Streamlit Community Cloud** **não alcança** um Oracle rodando
em `localhost`. Para que o mesmo `app.py` rode tanto localmente quanto na nuvem,
a fonte de dados é comutável:

- **`DATA_SOURCE=local`** → consome a **API/Oracle** (dados ao vivo, fluxo IoT
  completo). Usado em desenvolvimento e na demonstração com banco.
- **`DATA_SOURCE=cloud`** → lê os **artefatos versionados** no repositório
  (`data/processed/dataset_ml.parquet` + `models/*.joblib`). Usado no Streamlit
  Cloud, sem necessidade de banco nem de re-treino.

Essa comutação é a peça que viabiliza o **IR ALÉM 2** (dashboard online) sem
sacrificar o fluxo IoT→DB→ML completo do ambiente local.

---

## 5. Mapa enunciado → componentes

| Item do enunciado | O que entrega | Onde mora |
|---|---|---|
| **PARTE 1** — ML + Streamlit (dashboard estático e online) | Pipeline ML integrado ao dashboard interativo | `ml/` + `streamlit/app.py` |
| **PARTE 2** — Regressão (linear/múltipla/não-linear) + métricas | Treino, seleção e avaliação (MAE/MSE/RMSE/R²) | `ml/train.py` + notebook |
| **IR ALÉM 1** — Banco de dados IoT | Ingestão/atualização em SQL (`SENSORES_FARMTECH`) | `db/` (Oracle XE reusado do Cap-3) |
| **IR ALÉM 2** — Dashboard analítico online | Publicação no Streamlit Cloud (`DATA_SOURCE=cloud`) | `streamlit/` + `docs/DEPLOY.md` |

### Detalhamento

- **PARTE 1** — O `prepare_dataset.py` e o `train.py` produzem modelos que o
  `streamlit/app.py` carrega para exibir métricas, correlações e previsões em
  tempo real, atendendo ao critério de integração modelo↔dashboard.
- **PARTE 2** — `train.py` cobre os três tipos de regressão exigidos
  (`LinearRegression` baseline, `Ridge` e `RandomForestRegressor` não-linear),
  prevê `volume_irrigacao`, `necessidade_fertilizacao` e `rendimento`, e avalia
  com as quatro métricas. O notebook acompanha as visualizações justificativas.
- **IR ALÉM 1** — A camada `db/` materializa a ingestão IoT no Oracle XE
  (tabela com coluna virtual `PERIODO`), demonstrando população e atualização
  dos dados de sensores.
- **IR ALÉM 2** — `docs/DEPLOY.md` (este conjunto de docs) guia a publicação do
  dashboard online, usando os artefatos versionados via `DATA_SOURCE=cloud`.

---

## 6. Variáveis de ambiente

| Variável | Componente | Função |
|---|---|---|
| `ORACLE_DSN` | api / db | DSN do Oracle XE (Cap-3), ex. `localhost:1521/XEPDB1` |
| `ORACLE_USER` | api / db | usuário do banco |
| `ORACLE_PASSWORD` | api / db | senha do banco |
| `DATA_SOURCE` | streamlit | `local` (API/Oracle) ou `cloud` (Parquet + joblib) |
| `API_URL` | streamlit | URL da FastAPI no modo local |
| `MODELS_DIR` | api / streamlit | diretório dos modelos `.joblib` |
| `DATA_PATH` | api / streamlit | caminho do `dataset_ml.parquet` |

---

## 7. Resumo

A infraestrutura de **dados, banco e sensores** vem do Cap-3; a Fase 4 adiciona a
**inteligência**: engenharia de alvos reprodutível, modelos de regressão
avaliados por MAE/MSE/RMSE/R² e um dashboard que **comuta entre Oracle ao vivo e
artefatos versionados**, permitindo tanto a demonstração local completa
(IoT→DB→ML→Dashboard) quanto a publicação online — fechando o ciclo da
**Agricultura Cognitiva** proposto pelo enunciado.
