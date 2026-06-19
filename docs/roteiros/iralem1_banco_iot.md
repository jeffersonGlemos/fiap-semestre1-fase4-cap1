# Roteiro de Vídeo — IR ALÉM 1: Ingestão de Dados IoT no Banco (Oracle)

> **Projeto:** FarmTech Solutions — Fase 4, Capítulo 1 (Assistente Agrícola Inteligente)
> **Autor:** Jefferson Gonçalves Lemos · RM 572399 · Inteligência Artificial — FIAP
> **Entrega:** IR ALÉM 1 — vídeo, **máximo 3 minutos**

---

## Objetivo do vídeo

Demonstrar a **modelagem do banco SQL** e a **ingestão/população dos dados IoT** dos sensores, mostrando:

1. O **funcionamento da ingestão/população** dos dados no banco (Oracle, SQL).
2. O **processo de ingestão e atualização automática** dos dados.

Arquitetura híbrida: o **Oracle XE é reutilizado do Cap-3** (`1-semestre/Cap-3/fase3_cap1`), externo a este projeto. A tabela central é `SENSORES_FARMTECH`, com as mesmas colunas do CSV mais a coluna virtual `PERIODO`.

---

## Duração-alvo

| Total | Limite oficial |
|-------|----------------|
| ~2min40s | **3 minutos** |

Vídeo curto: ser direto, sem blocos longos de explicação.

---

## Roteiro em blocos (com tempo)

### Bloco 0 — Abertura e arquitetura (0:00 – 0:25)

**Fala (resumo):**
> "Jefferson Lemos, RM 572399. Neste IR ALÉM 1 mostro a ingestão dos dados de sensores IoT num banco SQL. Reutilizo o Oracle XE da Fase 3 — sobe via docker-compose em `localhost:1521`, serviço `XEPDB1` — e nele populo a tabela `SENSORES_FARMTECH` com as leituras dos pivôs."

**Tela:**
- Diagrama/explicação rápida: sensores → CSV → Oracle → API/Streamlit.
- `docker-compose` do Cap-3 (mostrar o serviço Oracle).

---

### Bloco 1 — Subir o Oracle e a modelagem da tabela (0:25 – 1:15)

**Fala (resumo):**
> "Subo o Oracle do Cap-3 com `docker compose up`. A modelagem segue Cognitive Data Science: a tabela `SENSORES_FARMTECH` espelha o sensor — ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA e CAPTURADO_EM — e ainda tem a coluna virtual `PERIODO`, derivada do horário, para análise por turno sem ocupar espaço físico."

**Tela:**
- Subir o Oracle (`docker compose up -d` na pasta do Cap-3) e mostrar o container `healthy`.
- Mostrar o **DDL** da tabela `SENSORES_FARMTECH` (colunas + coluna virtual `PERIODO`).
- Conectar (sqlplus / SQL client) no serviço `XEPDB1`.

**Pontos a citar:**
- Colunas idênticas ao CSV → ingestão direta, sem transformação de esquema.
- `PERIODO` como **coluna virtual** (calculada, não armazenada).

---

### Bloco 2 — Ingestão/população dos dados (1:15 – 2:10)

**Fala (resumo):**
> "A ingestão lê o `data/raw/seed_data.csv` — 2696 leituras dos pivôs p1, p2 e p3 — e insere em lote na `SENSORES_FARMTECH`. Uso o script de ingestão em `db/`, que converte ESTADO_BOMBA ON/OFF e o timestamp, e faz commit. Rodo o script e confirmo a carga com um `COUNT(*)`."

**Tela:**
- Mostrar o script de ingestão em `db/` (leitura do CSV + `INSERT`/bulk em batch).
- Executar a ingestão.
- `SELECT COUNT(*) FROM SENSORES_FARMTECH;` → confirmar ~2696 linhas.
- `SELECT * FROM SENSORES_FARMTECH FETCH FIRST 5 ROWS ONLY;` → mostrar dados + coluna `PERIODO` preenchida.

---

### Bloco 3 — Atualização automática (2:10 – 2:40)

**Fala (resumo):**
> "Para a atualização automática, a ingestão é idempotente e pode rodar de forma recorrente — agendada por job — incorporando novas leituras dos sensores. Assim o banco se mantém atualizado e serve a API FastAPI e o dashboard sem intervenção manual."

**Tela:**
- Mostrar o mecanismo de atualização (job/scheduler ou execução recorrente do script de ingestão).
- Rodar a ingestão uma 2ª vez e mostrar que não duplica (ou que incorpora novas linhas).
- Encerrar mostrando o `COUNT(*)` consistente.

**Fala de fecho:**
> "Banco SQL modelado, dados IoT ingeridos e atualização automática funcionando. Obrigado!"

---

## Checklist — o que MOSTRAR na tela

- [ ] Identificação: nome, RM 572399, Fase 4 Cap 1.
- [ ] Arquitetura híbrida: Oracle do Cap-3 reutilizado (`localhost:1521`, `XEPDB1`).
- [ ] `docker compose up` do Cap-3 + container Oracle saudável.
- [ ] DDL da tabela `SENSORES_FARMTECH` (colunas do CSV + coluna virtual `PERIODO`).
- [ ] Conexão ao banco (sqlplus / SQL client).
- [ ] Script de ingestão em `db/` (lê `seed_data.csv`, insere em lote).
- [ ] Execução da ingestão.
- [ ] `SELECT COUNT(*)` confirmando ~2696 linhas.
- [ ] `SELECT` de amostra com `PERIODO` calculado.
- [ ] Mecanismo de atualização automática (job/scheduler ou rerun idempotente).

---

## Checklist técnico — ANTES de gravar

- [ ] Oracle XE do Cap-3 no ar (`docker compose up -d`, esperar ficar `healthy`).
- [ ] Variáveis `ORACLE_DSN`, `ORACLE_USER`, `ORACLE_PASSWORD` configuradas.
- [ ] Tabela `SENSORES_FARMTECH` criada (DDL aplicado) antes de gravar.
- [ ] Script de ingestão em `db/` testado e idempotente.
- [ ] Ter pronto o comando de `COUNT(*)`/`SELECT` para confirmar a carga ao vivo.
- [ ] Ensaiar para fechar em ~2min40s (vídeo de 3 min é apertado — ir direto ao ponto).
