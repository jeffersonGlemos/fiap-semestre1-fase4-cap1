# `db/` — Integração IoT → Banco SQL (IR ALÉM 1)

**FarmTech Solutions — Fase 4, Capítulo 1**
Autor: **Jefferson Gonçalves Lemos** · RM **572399** · Inteligência Artificial — FIAP

Este módulo implementa o **IR ALÉM 1**: o elo entre os sensores de campo (IoT) e
um banco de dados relacional. Os dados ingeridos aqui servem de fonte para os
modelos de Machine Learning (`ml/`) e para o dashboard (`streamlit/app.py`)
quando `DATA_SOURCE=local`, fechando o fluxo **IoT → DB → ML → Dashboard**.

> **Engine-agnóstico.** O `db/` funciona com **dois bancos**, selecionados pela
> variável de ambiente `DB_ENGINE`:
>
> - **`sqlite`** (DEFAULT) — arquivo local `db/farmtech.db`, **zero configuração**
>   e zero dependências extras. Roda em qualquer máquina, sem container.
> - **`oracle`** — reusa o **Oracle XE** provisionado no Cap-3
>   (`1-semestre/Cap-3/fase3_cap1`, service `XEPDB1`). O driver `oracledb` só é
>   importado nesse modo (**import preguiçoso**), então o SQLite roda sem ter
>   `oracledb` instalado.
>
> A camada de dialeto (placeholders, tipos de coluna, sintaxe de `LIMIT`/
> `TO_TIMESTAMP`) é abstraída em `connection.py`, de modo que `ingest.py` se
> comporta igual nos dois engines.

---

## Arquivos

| Arquivo         | Papel                                                                                                             |
| --------------- | ----------------------------------------------------------------------------------------------------------------- |
| `connection.py` | Conexão e dialeto SQL: `get_connection()`, `criar_tabela()`, `wait_for_connection()`, `db_connection()` (context manager), `is_oracle()` e os geradores `create_table_sql()` / `insert_sql()` / `select_sql(limit)` / `count_sql()`. |
| `ingest.py`     | Ingestão CSV → banco (`--once` / `--loop`), simulação de IoT contínuo e leitura `ler_dados()` para o ML.          |
| `farmtech.db`   | Arquivo SQLite criado automaticamente no modo `sqlite` (gerado em runtime).                                       |
| `README.md`     | Este guia.                                                                                                         |

---

## Visão geral do fluxo (IR ALÉM 1)

```
data/raw/seed_data.csv  ──(db/ingest.py)──►  SENSORES_FARMTECH  ──(ler_dados)──►  ml/ + streamlit/app.py
        (sensores IoT)        INSERT em lote     (SQLite ou Oracle)    SELECT          (DATA_SOURCE=local)
```

1. **Escrita (ingestão):** `ingest.py` lê `data/raw/seed_data.csv` e insere as
   leituras na tabela `SENSORES_FARMTECH` via `executemany` (INSERT em lote).
   Pode rodar uma única vez (`--once`) ou em modo contínuo (`--loop`), simulando
   a chegada periódica de novas leituras dos pivôs de irrigação.
2. **Leitura (serviço para o ML):** `ler_dados()` faz o `SELECT` na tabela e
   devolve os registros prontos para alimentar os modelos de regressão.

---

## Tabela `SENSORES_FARMTECH`

O `ingest.py` grava as **9 colunas reais** abaixo (na ordem dos binds do INSERT).
A DDL é gerada por `create_table_sql()` no dialeto do engine ativo — `TEXT/REAL/
INTEGER` no SQLite, `VARCHAR2/NUMBER/TIMESTAMP` no Oracle.

| Coluna         | Tipo (SQLite) | Tipo (Oracle)  | Descrição                                              |
| -------------- | ------------- | -------------- | ------------------------------------------------------ |
| `ID_PIVO`      | `TEXT`        | `VARCHAR2(30)` | Identificador do pivô de irrigação (`p1`, `p2`, `p3`). |
| `UMIDADE`      | `REAL`        | `NUMBER(5,2)`  | Umidade do solo (%).                                   |
| `TEMPERATURA`  | `REAL`        | `NUMBER(5,2)`  | Temperatura (°C).                                      |
| `PH`           | `REAL`        | `NUMBER(5,2)`  | pH do solo.                                            |
| `N`            | `INTEGER`     | `NUMBER(3)`    | Nitrogênio.                                            |
| `P`            | `INTEGER`     | `NUMBER(3)`    | Fósforo.                                               |
| `K`            | `INTEGER`     | `NUMBER(3)`    | Potássio.                                              |
| `ESTADO_BOMBA` | `TEXT`        | `VARCHAR2(3)`  | Estado da bomba: `ON` ou `OFF`.                        |
| `CAPTURADO_EM` | `TEXT`        | `TIMESTAMP`    | Momento da leitura (no Oracle via `TO_TIMESTAMP`).     |

> No modo `sqlite`, `criar_tabela()` cria a tabela automaticamente
> (`CREATE TABLE IF NOT EXISTS`). No modo `oracle`, a tabela já vem do schema do
> Cap-3; `criar_tabela()` é idempotente e ignora o erro `ORA-00955` (objeto já
> existe). O schema do Cap-3 pode ainda expor colunas extras (ex.: a coluna
> virtual `PERIODO`), mas o `INSERT` desta fase grava apenas as 9 colunas acima.

---

## Variáveis de ambiente

| Variável          | Default                   | Quando se aplica | Descrição                                       |
| ----------------- | ------------------------- | ---------------- | ----------------------------------------------- |
| `DB_ENGINE`       | `sqlite`                  | sempre           | Seleciona o engine: `sqlite` ou `oracle`.       |
| `SQLITE_PATH`     | `db/farmtech.db`          | `sqlite`         | Caminho do arquivo SQLite (criado se não existe).|
| `ORACLE_DSN`      | `localhost:1521/XEPDB1`   | `oracle`         | DSN `host:porta/service`.                        |
| `ORACLE_USER`     | `system`                  | `oracle`         | Usuário do banco.                                |
| `ORACLE_PASSWORD` | `farmtech123`             | `oracle`         | Senha do banco.                                  |
| `DATA_PATH`       | `data/raw/seed_data.csv`  | ingestão         | CSV bruto a ingerir (sobrescreve com `--path`).  |

Com os defaults, basta rodar — o SQLite não exige nenhuma configuração.

---

## 1. Ingestão única (`--once`)

Execute a partir da **raiz do projeto** (`fase4cap1/`) para que o import
`from db.connection import ...` resolva.

```bash
# SQLite (default) — insere TODO o seed_data.csv de uma vez:
python -m db.ingest --once

# Equivalente, deixando o engine explícito:
DB_ENGINE=sqlite python -m db.ingest --once

# Reescrevendo o timestamp para o instante atual ("leituras ao vivo"):
python -m db.ingest --once --simular-tempo-real

# CSV alternativo:
python -m db.ingest --once --path /caminho/para/outro.csv
```

> Verificado: `python -m db.ingest --once` inseriu **2696 linhas** no SQLite.

---

## 2. Ingestão contínua (`--loop`) — simulação de IoT

O modo `--loop` envia o CSV em **lotes**, num intervalo fixo, reciclando o
arquivo do início ao chegar ao fim (ciclo) — simulando um datalogger IoT que
publica leituras periodicamente. Interrompa com `Ctrl+C`.

```bash
# 3 leituras a cada 5s, com timestamp "ao vivo" (infinito; Ctrl+C para parar):
python -m db.ingest --loop --interval 5 --batch-size 3 --simular-tempo-real

# Loop limitado (útil para teste): 3 lotes de 5 leituras e encerra:
python -m db.ingest --loop --interval 2 --batch-size 5 --max-ciclos 3 --simular-tempo-real

# Loop mais lento: 1 lote a cada 10s:
python -m db.ingest --loop --interval 10 --batch-size 5
```

> Verificado: `--loop --max-ciclos 3 --batch-size 5 --simular-tempo-real`
> adicionou **15 linhas** com `CAPTURADO_EM` no horário corrente.

### Flags da CLI

| Flag                   | Aplica a   | Efeito                                                            |
| ---------------------- | ---------- | ---------------------------------------------------------------- |
| `--once`               | —          | Insere o CSV inteiro e encerra. *(mutuamente exclusivo com `--loop`)* |
| `--loop`               | —          | Ingestão contínua em lotes (Ctrl+C para parar).                  |
| `--interval N`         | `--loop`   | Segundos entre lotes (default `5.0`).                            |
| `--batch-size N`       | `--loop`   | Leituras por lote (default `3`).                                 |
| `--max-ciclos N`       | `--loop`   | Limite de lotes; sem ela, roda indefinidamente.                  |
| `--simular-tempo-real` | ambos      | Reescreve `CAPTURADO_EM` com o instante atual.                   |
| `--path CAMINHO`       | ambos      | CSV alternativo (default = `DATA_PATH`).                         |

---

## 3. Ler os dados para o ML / Dashboard

A função `ler_dados()` faz o `SELECT` (ordenado por `CAPTURADO_EM`) que serve o
pipeline de Machine Learning e o dashboard:

```python
from db.ingest import ler_dados

# Lista de dicionários {coluna: valor}:
registros = ler_dados(limit=1000)

# Ou direto como DataFrame (pandas), pronto para o pré-processamento:
df = ler_dados(as_dataframe=True)

# Contagem rápida de linhas na tabela:
from db.ingest import contar_linhas
print(contar_linhas())
```

> `ler_dados_oracle` permanece como **alias retrocompatível** de `ler_dados`.

Esse é o caminho usado pelo `streamlit/app.py` quando **`DATA_SOURCE=local`**: o
dashboard tenta a API FastAPI; se indisponível, importa `db.ingest.ler_dados` e
lê **direto de `SENSORES_FARMTECH`** (SQLite por padrão, ou o Oracle do Cap-3 se
`DB_ENGINE=oracle`); por fim, cai no arquivo versionado. No modo `cloud`
(default do deploy), a leitura usa `data/processed/dataset_ml.csv` + os modelos
em `models/*.joblib`, sem tocar no banco.

```bash
# Rodar o dashboard lendo do banco SQL local (a partir da raiz do projeto):
DATA_SOURCE=local streamlit run streamlit/app.py
```

---

## 4. Apontar para o Oracle do Cap-3 (opcional)

Para reusar o Oracle XE do Cap-3 em vez do SQLite:

**a)** Suba o container do banco (ele vive no projeto do Cap-3):

```bash
cd 1-semestre/Cap-3/fase3_cap1
docker compose up -d oracle
docker compose logs -f oracle   # aguarde "DATABASE IS READY TO USE" (~2 min)
```

Detalhes do serviço (de `1-semestre/Cap-3/fase3_cap1/docker-compose.yml`):
imagem `container-registry.oracle.com/database/express:21.3.0-xe`, porta
**`1521:1521`**, service/PDB **`XEPDB1`**, admin **`system` / `farmtech123`**.

**b)** Instale o driver (thin mode, sem Instant Client) e configure o engine:

```bash
pip install oracledb

export DB_ENGINE=oracle
export ORACLE_DSN="localhost:1521/XEPDB1"
export ORACLE_USER="system"
export ORACLE_PASSWORD="farmtech123"
```

**c)** Teste a conectividade e ingira:

```bash
# Smoke test (conecta + garante a tabela):
python -m db.connection      # imprime "OK — engine=oracle ... pronta."

# Ingestão apontando para o Oracle:
DB_ENGINE=oracle ORACLE_DSN=localhost:1521/XEPDB1 python -m db.ingest --once
```

> Em containers na mesma rede do Cap-3, use o nome do container como host, ex.:
> `ORACLE_DSN=farmtech-fase3-oracle:1521/XEPDB1`. O `wait_for_connection()` faz
> várias tentativas com espera (o Oracle pode levar minutos para subir); no
> SQLite a conexão é imediata.
</content>
</invoke>
