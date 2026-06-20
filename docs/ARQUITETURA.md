# Arquitetura — FarmTech Solutions · Fase 4, Capítulo 1

**Assistente Agrícola Inteligente**

- Autor: **Jefferson Gonçalves Lemos** · RM **572399**
- Disciplina: **Inteligência Artificial — FIAP**

Este documento descreve em detalhe a **arquitetura híbrida** do projeto: seus
componentes, o fluxo de dados ponta a ponta (IoT → Banco → ML → Dashboard), as
decisões de design que sustentam essas escolhas e como cada parte mapeia para o
enunciado da Fase 4.

---

## 1. Visão geral

O projeto transforma dados agrícolas de sensores IoT em **previsões e sugestões
de manejo** entregues a um gestor agrícola por meio de um dashboard interativo.

A solução é **híbrida** em dois sentidos complementares:

1. **Reúso de infraestrutura de fases anteriores.** Os sensores simulados e o
   esquema relacional (`SENSORES_FARMTECH`) já construídos em **fases anteriores
   da disciplina** são reaproveitados em vez de recriados. O banco IoT (`db/`) é
   **engine-agnóstico**: roda em **SQLite por padrão** (sem dependências externas)
   ou em um **Oracle XE externo** via `DB_ENGINE=oracle`. A Fase 4 acrescenta a
   camada de Inteligência Artificial sobre essa base existente.
2. **Fonte de dados comutável.** O dashboard funciona em dois modos
   (`DATA_SOURCE=local` e `DATA_SOURCE=cloud`), permitindo rodar localmente
   lendo do **banco SQL** (SQLite/Oracle via `db/`)/API — fechando o loop
   **IoT → DB → ML → Dashboard** — ou publicado online lendo artefatos
   versionados no repositório (CSV + modelos `.joblib`).

```
            ┌──────────────────────────────────────────────────────────────┐
            │                  FarmTech — Fase 4, Cap 1                      │
            │                  (este projeto: fase4cap1)                     │
            └──────────────────────────────────────────────────────────────┘

   BANCO SQL (db/)                   NOVO NA FASE 4 (camada de IA)
 ┌───────────────────┐      ┌───────────────────────────────────────────────┐
 │  SQLite / Oracle  │      │  prepare_dataset → train → models → api/streamlit│
 │  SENSORES_FARMTECH│      └───────────────────────────────────────────────┘
 └───────────────────┘
```

---

## 2. Componentes

### 2.1 Banco SQL engine-agnóstico (`db/`) — SQLite padrão · Oracle XE externo

- O módulo `db/` é **engine-agnóstico**, selecionado pela variável `DB_ENGINE`:
  - **`sqlite` (DEFAULT)** — arquivo local `db/farmtech.db`, **sem dependências
    externas** (não requer Docker nem o `oracledb`); ideal para rodar o loop
    IoT→DB→ML→Dashboard em qualquer máquina.
  - **`oracle` (opcional)** — conecta a um **Oracle XE externo** (importação
    preguiçosa do `oracledb`, só carregado quando `DB_ENGINE=oracle`).
- Em ambos os engines os dados de sensores IoT moram na tabela
  **`SENSORES_FARMTECH`**, com as mesmas colunas do CSV
  (`ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM`).
  No Oracle, há ainda a **coluna virtual `PERIODO`** (derivada de `CAPTURADO_EM`).
- O modo `oracle` conecta a um **Oracle XE externo** (DSN default
  `localhost:1521/XEPDB1`, serviço **`XEPDB1`**). Este projeto **não** sobe Oracle
  próprio: ele consome um Oracle XE externo como dependência apenas no modo
  `oracle`.
- Conexão por variáveis de ambiente: `DB_ENGINE`, `SQLITE_PATH` (sqlite) e
  `ORACLE_DSN` / `ORACLE_USER` / `ORACLE_PASSWORD` (oracle).

> Por ser local/externo, o banco só está disponível no modo **`DATA_SOURCE=local`**.
> No deploy online (Streamlit Cloud) ele é substituído pelos artefatos
> versionados — ver seção 4.3.

### 2.2 `data/raw/seed_data.csv`

- Dataset bruto de sensores: **2696 linhas de dados + header**.
- Colunas: `ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM`.
- Domínios: `ESTADO_BOMBA ∈ {ON, OFF}`, `ID_PIVO ∈ {p1, p2, p3}`,
  `CAPTURADO_EM` é timestamp.
- É a **fonte de verdade** dos dados de entrada, podendo ser ingerido no Oracle
  XE externo ou lido diretamente pelo `prepare_dataset.py`.

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
- **Saída:** `data/processed/dataset_ml.csv` (versionado para o deploy `cloud`).

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

- **Features de entrada (por-alvo):**
  - Base (todos): `temperatura, n, p, k, estado_bomba_bin`
    (1=ON / 0=OFF), `id_pivo` (one-hot p1/p2/p3), `hora` e `dia_semana`.
  - Contexto (`umidade`, `ph`): adicionadas **só** aos alvos engenheirados
    (`rendimento`, `volume_irrigacao`, `necessidade_fertilizacao`), que dependem
    delas — sem usar o alvo como feature de si mesmo (sem *data leakage*).
- **Cinco alvos de regressão**, cada um com seu próprio modelo e conjunto de
  features (registrado em `metrics.json → feature_columns`):
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

### 2.6 `db/` — banco IoT engine-agnóstico (IR ALÉM 1)

Materializa a integração dos dados IoT no banco SQL (tabela
`SENSORES_FARMTECH`), com dois módulos:

- **`db/connection.py`** — abstrai o engine (`DB_ENGINE`): `get_connection()`,
  `criar_tabela()` (idempotente), `wait_for_connection()`, `db_connection()`
  (context manager) e o dialeto SQL (`create_table_sql` / `insert_sql` /
  `select_sql` / `count_sql`), cujos placeholders e tipos diferem por engine
  (SQLite `?` + `TEXT/REAL`; Oracle `:n` + `TO_TIMESTAMP` + `FETCH FIRST`).
- **`db/ingest.py`** — CLI de ingestão IoT: `--once` (carrega todo o
  `seed_data.csv` via `executemany`) e `--loop` (simula IoT contínuo, reciclando
  o CSV com timestamp ao vivo; flags `--interval`, `--batch-size`, `--max-ciclos`,
  `--simular-tempo-real`). Expõe ainda `ler_dados(limit, as_dataframe)` — o
  caminho **DB → ML/Dashboard** usado quando `DATA_SOURCE=local`.

Usa o esquema `SENSORES_FARMTECH` no Oracle XE externo quando `DB_ENGINE=oracle`;
no default (`sqlite`) cria/usa o arquivo `db/farmtech.db`.

### 2.7 `api/` — FastAPI (`:8000`)

- Expõe os dados do Oracle e/ou as previsões dos modelos via HTTP.
- Consumida pelo Streamlit no modo **local** (`API_URL`).
- Configurada por `ORACLE_DSN/USER/PASSWORD`, `MODELS_DIR`, `DATA_PATH`.

### 2.8 `streamlit/app.py` — Dashboard (`:8501`)

- Interface do gestor agrícola: métricas de desempenho dos modelos,
  gráficos de correlação, previsões interativas e sugestões de manejo
  (irrigação / fertilização) derivadas das previsões.
- **Fonte de dados comutável** por `DATA_SOURCE`:
  - `local` → lê do **banco SQL** via `db/` (SQLite padrão ou Oracle XE externo),
    com a API como alternativa; fecha o loop IoT→DB→ML→Dashboard;
  - `cloud` (**default**) → lê `data/processed/dataset_ml.csv` + `models/*.joblib`
    versionados no repositório, sem precisar de banco.

---

## 3. Fluxo de dados (IoT → DB → ML → Dashboard)

```
 ┌─────────────────┐
 │  Sensores IoT   │  ESP32 / Wokwi (simulado)
 │  (p1, p2, p3)   │
 └────────┬────────┘
          │  leituras (umidade, temp, pH, N, P, K, bomba, timestamp)
          ▼
 ┌─────────────────────────────┐        ┌──────────────────────────┐
 │  data/raw/seed_data.csv     │───────▶│  Banco SQL (db/)         │
 │  2696 linhas                │ ingest │  sqlite padrão / oracle  │
 └────────────┬────────────────┘        │  SENSORES_FARMTECH       │
              │   python -m db.ingest    └────────────┬─────────────┘
              │  (modo local: dados vêm do banco via db/ — ler_dados)
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
 │   dataset_ml.csv            │
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
 │   DATA_SOURCE=local  ──▶  banco SQL via db/ (SQLite/Oracle)   │
 │   DATA_SOURCE=cloud  ──▶  dataset_ml.csv + models/*.joblib    │
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
- **Oracle:** opcional, fornecido por um **Oracle XE externo** (DSN default
  `localhost:1521/XEPDB1`, serviço `XEPDB1`), configurado via
  `ORACLE_DSN` / `ORACLE_USER` / `ORACLE_PASSWORD`.

---

## 4. Decisões de design

### 4.1 Por que arquitetura híbrida (reúso de fases anteriores)

O enunciado pede explicitamente partir "da estrutura lógica e relacional
construída nas fases anteriores". Recriar um banco do zero seria redundante e
contrariaria o objetivo de **consolidação**. Reusar um Oracle XE externo (por
exemplo, o da disciplina no Cap-3):

- Evita duplicação de esquema e de geração de dados.
- Mantém uma **única fonte de verdade** para os sensores
  (`SENSORES_FARMTECH` / `seed_data.csv`).
- Concentra o esforço da Fase 4 onde está o gap real: a **camada de IA**
  (regressão, previsões, sugestões e dashboard online).

Por isso o `docker-compose` local sobe só `api` + `streamlit`, tratando o Oracle
como serviço externo.

Para não amarrar a demonstração ao Docker, o banco IoT (`db/`) é
**engine-agnóstico**: por padrão usa **SQLite** (`db/farmtech.db`, sem
dependências), fechando o loop IoT→DB→ML→Dashboard em qualquer máquina; quando se
quer fidelidade ao ambiente relacional, basta `DB_ENGINE=oracle` para conectar ao
Oracle XE externo. A **única fonte de verdade** (`seed_data.csv` /
`SENSORES_FARMTECH`) permanece a mesma nos dois engines.

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

O deploy online no **Streamlit Community Cloud** **não alcança** um banco rodando
em `localhost` (nem SQLite local nem o Oracle XE externo). Para que o mesmo `app.py`
rode tanto localmente quanto na nuvem, a fonte de dados é comutável:

- **`DATA_SOURCE=local`** → lê do **banco SQL** via `db/` (SQLite por padrão ou
  Oracle XE externo), com a API como alternativa — dados ao vivo, **fluxo IoT
  completo**. Usado em desenvolvimento e na demonstração com banco.
- **`DATA_SOURCE=cloud`** (**default**) → lê os **artefatos versionados** no
  repositório (`data/processed/dataset_ml.csv` + `models/*.joblib`). Usado no
  Streamlit Cloud, sem necessidade de banco nem de re-treino.

O deploy online já está **pronto**: o default é `cloud`, a configuração do
Streamlit fica em **`.streamlit/config.toml` na raiz** do repositório (lida pelo
Streamlit Cloud e pelo Docker, `WORKDIR /app`) e os artefatos estão versionados —
nenhum *secret* é necessário. Essa comutação é a peça que viabiliza o
**IR ALÉM 2** (dashboard online) sem sacrificar o fluxo IoT→DB→ML completo do
ambiente local.

---

## 5. Mapa enunciado → componentes

| Item do enunciado | O que entrega | Onde mora |
|---|---|---|
| **PARTE 1** — ML + Streamlit (dashboard estático e online) | Pipeline ML integrado ao dashboard interativo | `ml/` + `streamlit/app.py` |
| **PARTE 2** — Regressão (linear/múltipla/não-linear) + métricas | Treino, seleção e avaliação (MAE/MSE/RMSE/R²) | `ml/train.py` + notebook |
| **IR ALÉM 1** — Banco de dados IoT | Ingestão/atualização em SQL (`SENSORES_FARMTECH`) | `db/` (SQLite padrão · Oracle XE externo) |
| **IR ALÉM 2** — Dashboard analítico online | Publicação no Streamlit Cloud (`DATA_SOURCE=cloud`) | `streamlit/` + `docs/DEPLOY.md` |

### Detalhamento

- **PARTE 1** — O `prepare_dataset.py` e o `train.py` produzem modelos que o
  `streamlit/app.py` carrega para exibir métricas, correlações e previsões em
  tempo real, atendendo ao critério de integração modelo↔dashboard.
- **PARTE 2** — `train.py` cobre os três tipos de regressão exigidos
  (`LinearRegression` baseline, `Ridge` e `RandomForestRegressor` não-linear),
  prevê `volume_irrigacao`, `necessidade_fertilizacao` e `rendimento`, e avalia
  com as quatro métricas. O notebook acompanha as visualizações justificativas.
- **IR ALÉM 1** — A camada `db/` materializa a ingestão IoT no banco SQL
  **engine-agnóstico** (`SENSORES_FARMTECH`; SQLite por padrão ou Oracle XE
  externo com coluna virtual `PERIODO`), via CLI `python -m db.ingest`
  (`--once`/`--loop`), demonstrando população e atualização contínua dos dados
  de sensores e a leitura DB→ML (`ler_dados`).
- **IR ALÉM 2** — `docs/DEPLOY.md` (este conjunto de docs) guia a publicação do
  dashboard online, usando os artefatos versionados via `DATA_SOURCE=cloud`.

---

## 6. Variáveis de ambiente

| Variável | Componente | Função |
|---|---|---|
| `DB_ENGINE` | db | `sqlite` (**default**, `db/farmtech.db`) ou `oracle` (Oracle XE externo) |
| `SQLITE_PATH` | db | caminho do arquivo SQLite (default `db/farmtech.db`) |
| `ORACLE_DSN` | api / db | DSN do Oracle XE externo, ex. `localhost:1521/XEPDB1` (service `XEPDB1`) — só com `DB_ENGINE=oracle` |
| `ORACLE_USER` | api / db | usuário do banco (engine `oracle`) |
| `ORACLE_PASSWORD` | api / db | senha do banco (engine `oracle`) |
| `DATA_SOURCE` | streamlit | `cloud` (**default**, CSV + joblib) ou `local` (banco SQL via `db/`/API) |
| `API_URL` | streamlit | URL da FastAPI no modo local |
| `MODELS_DIR` | api / streamlit | diretório dos modelos `.joblib` |
| `DATA_PATH` | api / streamlit | caminho do `dataset_ml.csv` processado |

---

## 7. Resumo

O **esquema relacional e os sensores** vêm de fases anteriores da disciplina; a Fase 4 adiciona a
**inteligência** e um banco IoT **engine-agnóstico** (SQLite por padrão, Oracle
opcional): engenharia de alvos reprodutível, modelos de regressão avaliados por
MAE/MSE/RMSE/R² e um dashboard que **comuta entre o banco SQL ao vivo
(SQLite/Oracle) e os artefatos versionados**, permitindo tanto a demonstração
local completa (IoT→DB→ML→Dashboard) quanto a publicação online já pronta
(`DATA_SOURCE=cloud`) — fechando o ciclo da **Agricultura Cognitiva** proposto
pelo enunciado.
