# Deploy — Dashboard online (IR ALÉM 2)

**FarmTech Solutions · Fase 4, Capítulo 1 — Assistente Agrícola Inteligente**

- Autor: **Jefferson Gonçalves Lemos** · RM **572399**
- Disciplina: **Inteligência Artificial — FIAP**
- Repositório: **https://github.com/jeffersonGlemos/fiap-semestre1-fase4-cap1** (branch `main`)

Este guia descreve, passo a passo, como publicar o dashboard no **Streamlit
Community Cloud** (entregável do **IR ALÉM 2 — Dashboard Analítico com Previsões
Interativas e Online**). Ao final há a **alternativa de execução local** com
`docker compose`.

> **Resumo do caminho verificado:** o app sobe em modo `cloud` **por padrão**,
> lendo um dataset e modelos **já versionados** no repositório. Não há banco,
> não há re-treino e **não é preciso configurar nenhum secret**. A configuração
> do Streamlit fica na **raiz** do repositório (`.streamlit/config.toml`). O
> único passo que **você** precisa fazer manualmente no navegador é o login
> **GitHub → Streamlit (OAuth)** — ele não pode ser automatizado.

---

## 1. Como funciona o deploy (resumo)

O Streamlit Community Cloud roda em servidores públicos e **não consegue acessar**
um Oracle em `localhost`. Por isso o dashboard usa uma **fonte de dados
comutável**, controlada pela variável `DATA_SOURCE`:

| Modo | `DATA_SOURCE` | Fonte dos dados | Uso |
|---|---|---|---|
| **Online (default)** | `cloud` | `data/processed/dataset_ml.csv` + `models/*.joblib` (versionados no repo) | **Streamlit Cloud** |
| Local | `local` | API FastAPI + banco SQL (Oracle XE externo ou SQLite da ingestão IoT) | desenvolvimento, demo com banco |

Pontos-chave do modo `cloud` (o que o Streamlit Cloud usa):

- **É o padrão.** No `streamlit/app.py`, `DATA_SOURCE` tem default `"cloud"`
  (`os.getenv("DATA_SOURCE", "cloud")`). Ou seja, **sem configurar nada**, o app
  já abre em modo online.
- **Lê arquivos versionados, não banco.** Carrega o dataset processado
  `data/processed/dataset_ml.csv` e os modelos `models/*.joblib` diretamente do
  repositório. O app prefere um `dataset_ml.parquet` se existir, mas **cai
  automaticamente** para o `dataset_ml.csv` irmão — e é o **CSV** que está
  versionado neste projeto.
- **Nenhum secret é necessário.** O `.gitignore` exclui
  `.streamlit/secrets.toml` justamente porque o deploy não depende dele.

---

## 2. Pré-requisitos

### 2.1 Conta e repositório

- Conta no **GitHub** com o projeto versionado (repo
  `jeffersonGlemos/fiap-semestre1-fase4-cap1`).
- Conta no **Streamlit Community Cloud** (https://share.streamlit.io),
  que será conectada ao GitHub via OAuth **no navegador** (passo manual — ver §3).

### 2.2 Artefatos versionados no repositório (obrigatório)

Para o modo `cloud` funcionar, **estes arquivos precisam estar commitados** (não
podem cair em alguma regra do `.gitignore`):

```
data/processed/dataset_ml.csv                      ← dataset processado (lido em modo cloud)
models/modelo_rendimento.joblib
models/modelo_volume_irrigacao.joblib
models/modelo_necessidade_fertilizacao.joblib
models/modelo_umidade.joblib
models/modelo_ph.joblib
models/metrics.json                                ← métricas (MAE/MSE/RMSE/R²) dos 5 modelos
```

Verifique antes do push (a partir da raiz do projeto):

```bash
git ls-files data/processed/dataset_ml.csv models/
```

A saída deve listar o **CSV** e os **cinco `.joblib`** + `metrics.json`. Se algum
não aparecer, confira o `.gitignore` (não há regra bloqueando esses caminhos;
o `.gitignore` só ignora `__pycache__/`, `*.pyc`, `.venv/`,
`.streamlit/secrets.toml` e o SQLite local `db/*.db`/`*.sqlite*`).

> **Arquivos grandes:** os modelos somam ~36 MB e o CSV ~280 KB — tudo abaixo do
> limite do GitHub, então **Git LFS não é necessário**.

### 2.3 Configuração do Streamlit (na RAIZ do repo)

A configuração de tema/servidor fica em **`.streamlit/config.toml`** na **raiz do
repositório** — é **desse local** que tanto o **Streamlit Cloud** quanto o
**Docker** (`WORKDIR /app`, `streamlit run streamlit/app.py`) leem o config.

Características relevantes do arquivo:

- **Tema agrícola** (`base = "light"`, verde-folha `#2e7d32`, fundos esverdeados).
- **`headless = true`** (não tenta abrir navegador — ideal para containers/cloud).
- **Sem `server.port` fixado.** A porta é gerenciada pelo Streamlit Cloud (e, no
  Docker, vem do `CMD`). Fixar `port` aqui causaria conflito.

> Não é preciso editar esse arquivo para o deploy: ele já está pronto e
> versionado na raiz.

### 2.4 App principal e dependências

- **Main file path:** `streamlit/app.py`.
- **Dependências na raiz:** `requirements.txt` (o Streamlit Cloud o detecta
  automaticamente). Já inclui `streamlit`, `scikit-learn`, `pandas`, `numpy`,
  `plotly`, `joblib`, `pyarrow`, etc.
- **Python 3.11+** recomendado (selecionável em *Advanced settings* no Cloud).

> A **versão do `scikit-learn`** do deploy deve ser compatível com a que treinou
> os modelos, para evitar avisos ao carregar os `.joblib`. O `requirements.txt`
> usa `scikit-learn>=1.4`; se aparecer aviso de versão, fixe a versão exata
> usada no treino.

---

## 3. Passo a passo — publicar no Streamlit Community Cloud

### Passo 1 — Garantir os artefatos no GitHub

```bash
git add data/processed/dataset_ml.csv models/ requirements.txt streamlit/ .streamlit/
git commit -m "deploy: artefatos versionados para Streamlit Cloud"
git push origin main
```

Confira com o `git ls-files` da §2.2 antes de seguir.

### Passo 2 — (MANUAL, no navegador) Login GitHub → Streamlit

1. Acesse **https://share.streamlit.io**.
2. Faça **login com o GitHub** e **autorize** o Streamlit a acessar seus repos.

> ⚠️ **Este é o único passo que não pode ser automatizado.** É um fluxo
> **OAuth no navegador** (GitHub → Streamlit) e exige a sua interação manual.
> Nenhum script/CLI substitui esta etapa.

### Passo 3 — Criar o app

1. Clique em **"New app"** (ou **"Create app" → "Deploy a public app from GitHub"**).
2. Preencha:
   - **Repository:** `jeffersonGlemos/fiap-semestre1-fase4-cap1`.
   - **Branch:** `main`.
   - **Main file path:** `streamlit/app.py`.
   - **Python version:** `3.11` (ou superior), em *Advanced settings*.

### Passo 4 — Secrets? Não precisa.

**Deixe os Secrets vazios.** Como `DATA_SOURCE` já tem default `"cloud"` no
`app.py`, o modo online é assumido automaticamente. **Não** informe `ORACLE_*`,
`API_URL` nem `DATA_PATH` — o app não acessa banco nesse modo.

> *(Opcional)* Se quiser deixar explícito, você pode abrir
> **Advanced settings → Secrets** e adicionar `DATA_SOURCE = "cloud"`. É apenas
> redundante; **não é obrigatório**.

### Passo 5 — Deploy

1. Clique em **"Deploy"**.
2. Acompanhe os logs de build (instalação do `requirements.txt`).
3. Ao terminar, o app fica disponível em uma URL pública do tipo
   `https://<seu-app>.streamlit.app`.

### Passo 6 — Atualizações

Todo `git push` na branch publicada dispara **redeploy automático**. Para forçar,
use **Manage app → Reboot**.

---

## 4. Checklist de validação

Após o deploy, valide na URL pública (estes itens foram verificados localmente
via `streamlit.testing` AppTest em modo `cloud`, com **0 exceções e 0 erros**):

- [ ] O app **carrega sem erro** (sem traceback na tela).
- [ ] O indicador de fonte mostra **☁️ Cloud** (e **não** Local/Oracle),
      confirmando `DATA_SOURCE=cloud`.
- [ ] Nos logs **não** há tentativa de conexão a Oracle/`localhost`.
- [ ] As **6 abas** do dashboard renderizam.
- [ ] As **métricas** dos modelos aparecem (MAE, MSE, RMSE, **R²** — de
      `models/metrics.json`): foram contabilizadas **9 métricas** e o **R² dos 5
      modelos** (rendimento ≈ 0,88; volume_irrigacao ≈ 0,94;
      necessidade_fertilizacao ≈ 0,97; umidade ≈ 0,77; ph ≈ 0,09).
- [ ] Os **gráficos** renderizam a partir do `dataset_ml.csv`.
- [ ] A **previsão interativa** responde: ao ajustar os inputs (temperatura,
      N, P, K, estado da bomba, id do pivô, hora, dia da semana), os alvos
      previstos (`rendimento`, `volume_irrigacao`, `necessidade_fertilizacao`,
      `umidade`, `ph`) são atualizados.
- [ ] As **sugestões de manejo** (irrigação/fertilização via `ml/suggest.py`),
      coerentes com as previsões, são exibidas.
- [ ] Não há **warning de versão** do scikit-learn ao carregar os `.joblib`
      (se houver, alinhe a versão no `requirements.txt`).

---

## 5. Solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| `FileNotFoundError` / "Sem dados disponíveis" | `dataset_ml.csv` ou `.joblib` não commitados | conferir `git ls-files` (§2.2) e dar push |
| App tenta conectar no Oracle e falha | algum secret forçou `DATA_SOURCE=local` | remover o secret (o default já é `cloud`) |
| `InconsistentVersionWarning` ao `joblib.load` | scikit-learn diferente do treino | fixar a mesma versão no `requirements.txt` |
| `ModuleNotFoundError` | dependência ausente | adicionar ao `requirements.txt` e push |
| Tema/cores não aplicam | `config.toml` fora da raiz | manter `.streamlit/config.toml` na **raiz** do repo |
| Build falha por arquivo grande | artefato > limite do GitHub | usar **Git LFS** (não esperado aqui) |

---

## 6. Alternativa — execução local com `docker compose`

Para rodar localmente — seja em modo `cloud` (idêntico ao que vai pro ar) ou em
modo `local` com o fluxo IoT→DB→ML completo conectado ao banco.

O `docker-compose.yml` deste projeto sobe **apenas dois serviços**: `api`
(FastAPI `:8000`) e `streamlit` (`:8501`). O Oracle XE **não** é definido aqui —
ele é **reusado de um Oracle XE externo** (service `XEPDB1`, em `localhost:1521`),
acessado via `ORACLE_DSN` / `ORACLE_USER` / `ORACLE_PASSWORD`.

### 6.1 Modo `cloud` local (rápido, sem banco)

Reproduz exatamente o deploy online, lendo o CSV + modelos versionados:

```bash
# a partir da raiz do projeto
DATA_SOURCE=cloud docker compose up -d streamlit
```

Ou sem Docker, direto na máquina:

```bash
DATA_SOURCE=cloud streamlit run streamlit/app.py
```

Acesse **http://localhost:8501**.

### 6.2 Modo `local` com banco (demo com Oracle XE externo)

1. Tenha um **Oracle XE externo** disponível (fonte da tabela
   `SENSORES_FARMTECH`) escutando em `localhost:1521`, serviço **`XEPDB1`** — pode
   ser, por exemplo, o Oracle da disciplina (Cap-3). A conexão é feita apenas via
   as variáveis `ORACLE_DSN` / `ORACLE_USER` / `ORACLE_PASSWORD`.

2. Suba `api` + `streamlit` deste projeto em modo `local`:

   ```bash
   # a partir da raiz do projeto
   export DATA_SOURCE=local
   export ORACLE_DSN="host.docker.internal:1521/XEPDB1"
   export ORACLE_USER="system"
   export ORACLE_PASSWORD="oracle"
   export API_URL="http://api:8000"

   docker compose up -d
   ```

   O compose já resolve o host da máquina (Oracle XE externo) via
   `extra_hosts: host.docker.internal:host-gateway`.

3. Acesse o dashboard em **http://localhost:8501** e a API em
   **http://localhost:8000**.

> **Sobre os defaults:** no `docker-compose.yml`, `DATA_SOURCE` tem default
> `local` (ideal para a demo com banco). Já o `streamlit/app.py` tem default
> `cloud` (ideal para o Streamlit Cloud). Por isso, ao subir o compose para a
> demo com banco, **exporte `DATA_SOURCE=local`** como acima.

---

## 7. Resumo

1. Versione `data/processed/dataset_ml.csv`, `models/*.joblib` + `metrics.json`,
   `requirements.txt`, `streamlit/app.py` e `.streamlit/config.toml`.
2. **(Manual, no navegador)** faça login **GitHub → Streamlit (OAuth)** em
   https://share.streamlit.io.
3. Crie o app: repo `jeffersonGlemos/fiap-semestre1-fase4-cap1`, branch `main`,
   **Main file path = `streamlit/app.py`**, Python 3.11+.
4. **Sem secrets** — `DATA_SOURCE=cloud` já é o padrão do app.
5. Deploy, valide pelo checklist (§4) e compartilhe a URL pública.

Para a demonstração com banco ao vivo, use a **alternativa local** com
`docker compose` (Oracle XE externo + api + streamlit em modo `local`).
