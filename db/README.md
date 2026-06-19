# `db/` — Integração IoT → Oracle (IR ALÉM 1)

**FarmTech Solutions — Fase 4, Capítulo 1**
Autor: **Jefferson Gonçalves Lemos** · RM **572399** · Inteligência Artificial — FIAP

Este módulo implementa o **IR ALÉM 1**: o elo entre os sensores de campo (IoT) e
o banco de dados, **reusando o Oracle XE provisionado no Cap-3**
(`1-semestre/Cap-3/fase3_cap1`). Os dados ingeridos aqui servem de fonte para os
modelos de Machine Learning (`ml/`) e para o dashboard (`streamlit/app.py`)
quando `DATA_SOURCE=local`.

> **Arquitetura híbrida.** O `docker-compose.yml` *deste* projeto sobe apenas a
> **API (FastAPI :8000)** e o **Streamlit (:8501)**. O banco **não** é recriado:
> ele vem do Cap-3, exposto em `localhost:1521` (service `XEPDB1`). No deploy
> online (IR ALÉM 2) o Oracle local não é alcançável — por isso o Streamlit
> comuta a fonte de dados via `DATA_SOURCE` (`local` = API/Oracle; `cloud` =
> parquet + modelos versionados no repositório).

---

## Arquivos

| Arquivo          | Papel                                                                            |
| ---------------- | -------------------------------------------------------------------------------- |
| `connection.py`  | `get_connection()` (oracledb *thin mode*) + context manager `oracle_connection`. |
| `ingest.py`      | Ingestão do CSV → Oracle (`--once` / `--loop`) e `ler_dados_oracle()` (SELECT).  |
| `README.md`      | Este guia.                                                                       |

---

## Tabela `SENSORES_FARMTECH`

A tabela é a **mesma** criada no Cap-3 (DDL em
`1-semestre/Cap-3/fase3_cap1/oracle/init/01_create_table.sql`). Colunas:

| Coluna         | Tipo Oracle    | Descrição                                                              |
| -------------- | -------------- | --------------------------------------------------------------------- |
| `ID_PIVO`      | `VARCHAR2(30)` | Identificador do pivô de irrigação (`p1`, `p2`, `p3`).                 |
| `UMIDADE`      | `NUMBER(5,2)`  | Umidade do solo (%).                                                   |
| `TEMPERATURA`  | `NUMBER(5,2)`  | Temperatura (°C).                                                      |
| `PH`           | `NUMBER(5,2)`  | pH do solo.                                                            |
| `N`            | `NUMBER(3)`    | Nitrogênio.                                                            |
| `P`            | `NUMBER(3)`    | Fósforo.                                                               |
| `K`            | `NUMBER(3)`    | Potássio.                                                              |
| `ESTADO_BOMBA` | `VARCHAR2(3)`  | Estado da bomba: `ON` ou `OFF`.                                        |
| `CAPTURADO_EM` | `TIMESTAMP`    | Momento da leitura.                                                    |
| `PERIODO`      | `NUMBER(6)`    | **Coluna virtual** = `ano*100 + mês` (`EXTRACT` de `CAPTURADO_EM`); usada para particionamento temporal simulado. Gerada automaticamente — **não** é inserida. |

> O `INSERT` do `ingest.py` grava apenas as 9 colunas reais; `PERIODO` é
> calculada pelo Oracle (`GENERATED ALWAYS AS ... VIRTUAL`).

---

## 1. Subir o Oracle do Cap-3

O container do banco vive no projeto do Cap-3. A partir da raiz do repositório:

```bash
cd 1-semestre/Cap-3/fase3_cap1

# Sobe SOMENTE o Oracle (e cria a tabela + materialized views via init/):
docker compose up -d oracle

# Acompanhe o startup até aparecer "DATABASE IS READY TO USE" (~2 min):
docker compose logs -f oracle
```

Detalhes do serviço (de `1-semestre/Cap-3/fase3_cap1/docker-compose.yml`):

- Imagem: `container-registry.oracle.com/database/express:21.3.0-xe`
- Porta publicada: **`1521:1521`**
- Service/PDB: **`XEPDB1`**
- Usuário/senha de admin: **`system` / `farmtech123`** (env `ORACLE_PWD`)

Se a tabela `SENSORES_FARMTECH` ainda não existir (banco recém-criado), os
scripts em `oracle/init/` a criam no primeiro boot. Para checar:

```bash
docker compose exec oracle bash -lc \
  "echo 'SELECT COUNT(*) FROM SENSORES_FARMTECH;' | sqlplus -s system/farmtech123@localhost:1521/XEPDB1"
```

---

## 2. Configurar as variáveis de ambiente

A conexão é lida do ambiente, com defaults já apontando para o Cap-3 em
`localhost`:

| Variável          | Default (Cap-3)         | Descrição                          |
| ----------------- | ----------------------- | ---------------------------------- |
| `ORACLE_DSN`      | `localhost:1521/XEPDB1` | DSN `host:porta/service`.          |
| `ORACLE_USER`     | `system`                | Usuário do banco.                  |
| `ORACLE_PASSWORD` | `farmtech123`           | Senha do banco.                    |
| `DATA_PATH`       | `data/raw/seed_data.csv`| CSV bruto a ingerir (opcional).    |

Rodando na sua máquina (Oracle em `localhost`), os defaults já bastam. Para
sobrescrever:

```bash
export ORACLE_DSN="localhost:1521/XEPDB1"
export ORACLE_USER="system"
export ORACLE_PASSWORD="farmtech123"
```

> Em containers (API/Streamlit deste projeto na mesma rede do Cap-3), use o
> nome do container como host, ex.: `ORACLE_DSN=farmtech-fase3-oracle:1521/XEPDB1`.

Dependência Python (thin mode, sem Instant Client):

```bash
pip install oracledb
```

Teste rápido de conectividade:

```bash
python -m db.connection      # imprime "OK — conexão ... funcionando."
```

---

## 3. Rodar a ingestão

Execute a partir da **raiz do projeto** (`fase4cap1/`) para que o import
`from db.connection import ...` resolva:

```bash
# Ingestão única — insere todo o seed_data.csv de uma vez:
python -m db.ingest --once

# Ingestão contínua — simula IoT: 3 leituras a cada 5s, com timestamp "ao vivo":
python -m db.ingest --loop --interval 5 --batch-size 3 --simular-tempo-real

# Loop limitado (útil para teste): 10 lotes e encerra:
python -m db.ingest --loop --interval 2 --batch-size 5 --max-ciclos 10
```

Flags principais:

| Flag                   | Efeito                                                            |
| ---------------------- | ---------------------------------------------------------------- |
| `--once`               | Insere o CSV inteiro e encerra.                                  |
| `--loop`               | Ingestão contínua em lotes (Ctrl+C para parar).                 |
| `--interval N`         | Segundos entre lotes (modo loop).                               |
| `--batch-size N`       | Leituras por lote (modo loop).                                  |
| `--max-ciclos N`       | Limite de lotes no loop (opcional).                            |
| `--simular-tempo-real` | Reescreve `CAPTURADO_EM` com o instante atual.                 |
| `--path CAMINHO`       | CSV alternativo (default = `DATA_PATH`).                        |

---

## 4. Ler os dados para o ML

A função `ler_dados_oracle()` faz o `SELECT` que serve o pipeline de Machine
Learning:

```python
from db.ingest import ler_dados_oracle

# Lista de dicionários:
registros = ler_dados_oracle(limit=1000)

# Ou direto como DataFrame (pandas), pronto para o pré-processamento:
df = ler_dados_oracle(as_dataframe=True)
```

Esse é o caminho usado por `ml/` e por `streamlit/app.py` quando
`DATA_SOURCE=local`. No modo `cloud`, a leitura cai para
`data/processed/dataset_ml.parquet` (sem Oracle).
