# Roteiro de Vídeo — IR ALÉM 1: Ingestão de Dados IoT no Banco SQL

> **Projeto:** FarmTech Solutions — Fase 4, Capítulo 1 (Assistente Agrícola Inteligente)
> **Autor:** Jefferson Gonçalves Lemos · RM 572399 · Inteligência Artificial — FIAP
> **Entrega:** IR ALÉM 1 — vídeo, **máximo 3 minutos**

---

## Objetivo do vídeo

Demonstrar a **ingestão e a população dos dados IoT** dos sensores num **banco SQL**, mostrando:

1. O **funcionamento da ingestão** dos dados no banco — carga única em lote (`--once`).
2. A **atualização automática/contínua** simulando um datalogger IoT em tempo real (`--loop --simular-tempo-real`).
3. O **ciclo fechado IoT → DB → Dashboard**: o dashboard, em `DATA_SOURCE=local`, lê do banco e reflete os dados ingeridos.

**Arquitetura engine-agnóstica.** O módulo `db/` funciona com **dois engines**, escolhidos pela variável `DB_ENGINE`:
- `sqlite` (**DEFAULT**, arquivo `db/farmtech.db`) — roda sem nenhuma dependência externa;
- `oracle` — conecta a um **Oracle XE externo** via variáveis de ambiente `ORACLE_DSN` / `ORACLE_USER` / `ORACLE_PASSWORD` (DSN default `localhost:1521/XEPDB1`, service `XEPDB1`); o módulo `oracledb` só é importado quando `DB_ENGINE=oracle` (import preguiçoso).

A tabela central é `SENSORES_FARMTECH`, com as colunas: `ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM`.

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
> "Jefferson Lemos, RM 572399. Neste IR ALÉM 1 mostro a ingestão de dados de sensores IoT num banco SQL. O módulo `db/` é engine-agnóstico: por padrão usa **SQLite** — arquivo `db/farmtech.db`, sem nenhum serviço externo — e, com `DB_ENGINE=oracle`, conecta a um **Oracle XE externo** (por exemplo, o da disciplina/Cap-3) via variáveis de ambiente. A tabela é a `SENSORES_FARMTECH`."

**Tela:**
- Diagrama rápido: sensores → CSV (`data/raw/seed_data.csv`) → banco SQL (`db/`) → ML → Dashboard.
- Mostrar a estrutura de `db/`: `connection.py` (engines + dialeto SQL) e `ingest.py` (CLI de ingestão).
- Apontar a variável `DB_ENGINE` em `db/connection.py` (default `sqlite`).

---

### Bloco 1 — Modelagem e ingestão em lote `--once` (0:25 – 1:25)

**Fala (resumo):**
> "A modelagem espelha o sensor: `ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA e CAPTURADO_EM`. A criação da tabela é idempotente (`criar_tabela`) e o dialeto SQL muda por engine — SQLite usa `?` e `TEXT/REAL`; Oracle usa `:n` e `TO_TIMESTAMP`. A ingestão lê o `seed_data.csv` (2696 leituras dos pivôs) e insere em lote com `executemany`. Rodo a carga única."

**Tela — rodar a partir da raiz do projeto:**
```bash
python -m db.ingest --once
```
- Mostrar o log confirmando **2696 linhas inseridas**.
- Mostrar a contagem para confirmar a carga:
```bash
python -c "from db.ingest import contar_linhas; print(contar_linhas())"
```

**Pontos a citar:**
- Colunas idênticas ao CSV → ingestão direta, sem transformar esquema.
- `inserir_linhas` usa `executemany` (carga em lote, com commit).
- `criar_tabela` é idempotente nos dois engines.

---

### Bloco 2 — Atualização automática/contínua `--loop` (1:25 – 2:15)

**Fala (resumo):**
> "Para simular o IoT contínuo, uso o modo `--loop --simular-tempo-real`: a cada intervalo o script envia um lote de leituras, recicla o CSV ao chegar ao fim e carimba cada leitura com o `CAPTURADO_EM` do instante atual. É a atualização automática do banco, sem intervenção manual."

**Tela:**
```bash
python -m db.ingest --loop --simular-tempo-real --interval 5 --batch-size 5 --max-ciclos 3
```
- Mostrar os logs `Lote 1/2/3: +5 linhas (acumulado=...)` chegando ao vivo.
- Confirmar que o `contar_linhas()` **cresceu** (carga única + lotes do loop).
- Mencionar que, sem `--max-ciclos`, o loop roda indefinidamente (Ctrl+C para parar) — é o comportamento de um datalogger contínuo.

---

### Bloco 3 — Ciclo fechado IoT → DB → Dashboard (2:15 – 2:40)

**Fala (resumo):**
> "O ciclo fecha aqui: subo o dashboard em `DATA_SOURCE=local`, que lê **do banco SQL** via `ler_dados()`. Os dados que acabei de ingerir aparecem no painel — IoT, banco e dashboard num fluxo só. E, se eu quiser persistir num Oracle XE externo, basta definir `ORACLE_DSN`/`ORACLE_USER`/`ORACLE_PASSWORD` e rodar com `DB_ENGINE=oracle`."

**Tela:**
```bash
DATA_SOURCE=local streamlit run streamlit/app.py
```
- Mostrar o seletor de pivô / dados refletindo as leituras ingeridas (fonte: 🖥️ Local).
- Citar a alternativa Oracle:
```bash
# com o Oracle XE externo no ar; depois:
DB_ENGINE=oracle ORACLE_DSN=localhost:1521/XEPDB1 ORACLE_USER=... ORACLE_PASSWORD=... python -m db.ingest --once
```

**Fala de fecho:**
> "Banco SQL modelado, dados IoT ingeridos em lote e em tempo real, e o dashboard lendo direto do banco. Ciclo IoT → DB → Dashboard fechado. Obrigado!"

---

## Checklist — o que MOSTRAR na tela

- [ ] Identificação: nome, RM 572399, Fase 4 Cap 1.
- [ ] Arquitetura engine-agnóstica: `DB_ENGINE=sqlite` (default, `db/farmtech.db`) ou `oracle` (Oracle XE externo, service `XEPDB1`).
- [ ] Estrutura de `db/`: `connection.py` (engines + dialeto SQL) e `ingest.py` (CLI).
- [ ] Colunas da tabela `SENSORES_FARMTECH` (espelham o CSV).
- [ ] `python -m db.ingest --once` → **2696 linhas** inseridas.
- [ ] `contar_linhas()` confirmando a carga.
- [ ] `python -m db.ingest --loop --simular-tempo-real ...` → lotes chegando ao vivo (atualização automática).
- [ ] Contagem crescendo após o loop.
- [ ] Dashboard em `DATA_SOURCE=local` lendo do banco (ciclo fechado).
- [ ] Menção ao modo Oracle (`DB_ENGINE=oracle`).

---

## Checklist técnico — ANTES de gravar

- [ ] Estar na raiz do repositório.
- [ ] (Opcional) Apagar `db/farmtech.db` antes, para a contagem começar limpa e mostrar exatamente 2696.
- [ ] Ter os comandos prontos: `--once`, `--loop --simular-tempo-real`, `contar_linhas()`.
- [ ] Dashboard testado em `DATA_SOURCE=local` (lendo do SQLite).
- [ ] (Se for demonstrar Oracle) Oracle XE externo no ar e `ORACLE_DSN/ORACLE_USER/ORACLE_PASSWORD` definidos — mas o caminho SQLite default **não** exige `oracledb`.
- [ ] Ensaiar para fechar em ~2min40s (3 min é apertado — ir direto ao ponto).
