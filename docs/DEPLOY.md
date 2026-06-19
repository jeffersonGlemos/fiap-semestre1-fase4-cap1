# Deploy — Dashboard online (IR ALÉM 2)

**FarmTech Solutions · Fase 4, Capítulo 1 — Assistente Agrícola Inteligente**

- Autor: **Jefferson Gonçalves Lemos** · RM **572399**
- Disciplina: **Inteligência Artificial — FIAP**
- Diretório base: `/projetos/fiap/1-semestre/fase4cap1`

Este guia descreve, passo a passo, como publicar o dashboard no **Streamlit
Community Cloud** (entregável do **IR ALÉM 2 — Dashboard Analítico com Previsões
Interativa e Online**). Ao final há a **alternativa de execução local** com
`docker compose`.

---

## 1. Como funciona o deploy (resumo)

O Streamlit Community Cloud roda em servidores públicos e **não consegue acessar**
um Oracle em `localhost`. Por isso o dashboard usa uma **fonte de dados
comutável** controlada pela variável `DATA_SOURCE`:

| Modo | `DATA_SOURCE` | Fonte dos dados | Uso |
|---|---|---|---|
| Local | `local` | API FastAPI + Oracle XE (Cap-3) | desenvolvimento, demo com banco |
| Online | `cloud` | `data/processed/dataset_ml.parquet` + `models/*.joblib` versionados | Streamlit Cloud |

No modo **cloud**, o app **não** precisa de banco nem de re-treino: ele lê o
dataset processado e os modelos serializados diretamente do repositório.

---

## 2. Pré-requisitos

### 2.1 Conta e repositório

- Conta no **GitHub** com o projeto versionado em um repositório.
- Conta no **Streamlit Community Cloud** (https://share.streamlit.io),
  conectada ao GitHub.

### 2.2 Artefatos versionados no repositório (obrigatório)

Para o modo `cloud` funcionar, **estes arquivos precisam estar commitados** (não
podem estar no `.gitignore`):

```
data/processed/dataset_ml.parquet          ← dataset processado
models/modelo_rendimento.joblib
models/modelo_volume_irrigacao.joblib
models/modelo_necessidade_fertilizacao.joblib
models/modelo_umidade.joblib
models/modelo_ph.joblib
models/metrics.json
```

Verifique antes do push:

```bash
git ls-files data/processed/dataset_ml.parquet models/
```

A saída deve listar o Parquet e os cinco `.joblib` + `metrics.json`. Se algum não
aparecer, confira o `.gitignore` (pode haver regra `*.parquet`, `models/` ou
`*.joblib` bloqueando — adicione exceções com `!`).

> Arquivos grandes: se o `.parquet` ou os modelos ultrapassarem ~100 MB, use
> **Git LFS**. Para este projeto (2696 linhas) os artefatos são pequenos e o LFS
> não é necessário.

### 2.3 App principal e dependências

- App principal: **`streamlit/app.py`**.
- Arquivo de dependências na raiz: **`requirements.txt`** (o Streamlit Cloud o
  detecta automaticamente). Deve conter ao menos:

```
streamlit
scikit-learn
pandas
numpy
plotly
joblib
pyarrow
```

> Importante: a **versão do `scikit-learn`** usada no deploy deve ser **a mesma**
> que treinou os modelos, para evitar avisos/erros de incompatibilidade ao
> carregar os `.joblib`. Fixe a versão (ex. `scikit-learn==1.5.2`) se necessário.

---

## 3. Passo a passo — publicar no Streamlit Community Cloud

### Passo 1 — Garantir os artefatos no GitHub

```bash
git add data/processed/dataset_ml.parquet models/ requirements.txt streamlit/
git commit -m "deploy: artefatos versionados para Streamlit Cloud"
git push origin main
```

### Passo 2 — Criar o app no Streamlit Cloud

1. Acesse https://share.streamlit.io e faça login com o GitHub.
2. Clique em **"New app"** (ou **"Create app" → "Deploy a public app from GitHub"**).
3. Preencha:
   - **Repository:** seu repositório (ex. `jeffersonGlemos/...`).
   - **Branch:** `main`.
   - **Main file path:** `streamlit/app.py`.
4. **Não** clique em Deploy ainda — primeiro configure os secrets (Passo 3).

### Passo 3 — Configurar `DATA_SOURCE=cloud` via Secrets

Em **"Advanced settings" → "Secrets"** (no formato TOML), informe:

```toml
DATA_SOURCE = "cloud"
DATA_PATH = "data/processed/dataset_ml.parquet"
MODELS_DIR = "models"
```

No modo `cloud` **não** informe `ORACLE_*` nem `API_URL` — o app não acessa banco
nesse modo. O `app.py` lê `DATA_SOURCE` (via `st.secrets`/ambiente) e seleciona
automaticamente a leitura por Parquet + `joblib`.

> Os secrets também podem ser ajustados depois em
> **Manage app → Settings → Secrets**, sem precisar refazer o deploy.

### Passo 4 — Deploy

1. Clique em **"Deploy"**.
2. Acompanhe os logs de build (instalação do `requirements.txt`).
3. Ao terminar, o app fica disponível em uma URL pública do tipo
   `https://<seu-app>.streamlit.app`.

### Passo 5 — Atualizações

Todo `git push` na branch publicada dispara **redeploy automático**. Para forçar,
use **Manage app → Reboot**.

---

## 4. Checklist de validação

Após o deploy, valide na URL pública:

- [ ] O app **carrega sem erro** (sem traceback na tela).
- [ ] Nos logs **não** há tentativa de conexão a Oracle/`localhost`
      (confirma que `DATA_SOURCE=cloud` está ativo).
- [ ] As **métricas** dos modelos aparecem (MAE, MSE, RMSE, R² — de
      `models/metrics.json`).
- [ ] Os **gráficos de correlação** renderizam a partir do `dataset_ml.parquet`.
- [ ] A **previsão interativa** responde: ao ajustar os inputs
      (temperatura, N, P, K, estado da bomba, id do pivô, hora, dia da semana),
      os alvos previstos (`rendimento`, `volume_irrigacao`,
      `necessidade_fertilizacao`, `umidade`, `ph`) são atualizados.
- [ ] As **sugestões de manejo** (irrigação/fertilização) coerentes com as
      previsões são exibidas.
- [ ] Não há **warning de versão** do scikit-learn ao carregar os `.joblib`
      (se houver, alinhe a versão no `requirements.txt`).

---

## 5. Solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| `FileNotFoundError` para `.parquet`/`.joblib` | artefatos não commitados ou `DATA_PATH/MODELS_DIR` errados | conferir `git ls-files` (2.2) e os secrets (Passo 3) |
| App tenta conectar no Oracle e falha | `DATA_SOURCE` não está `cloud` | corrigir secret `DATA_SOURCE = "cloud"` |
| `InconsistentVersionWarning` / erro ao `joblib.load` | versão do scikit-learn diferente da do treino | fixar a mesma versão no `requirements.txt` |
| `ModuleNotFoundError` | dependência ausente | adicionar ao `requirements.txt` e push |
| Build falha por arquivo grande | artefato > limite do GitHub | usar **Git LFS** |

---

## 6. Alternativa — execução local com `docker compose`

Para rodar localmente com o fluxo IoT→DB→ML completo (modo `local`, conectado ao
Oracle do Cap-3):

### 6.1 Subir o Oracle (Cap-3)

```bash
docker compose -f 1-semestre/Cap-3/fase3_cap1/docker-compose.yml up -d
```

Isso disponibiliza o Oracle XE em `localhost:1521`, serviço **`XEPDB1`**.

### 6.2 Subir api + streamlit (este projeto)

O `docker-compose` deste projeto sobe **apenas** `api` (FastAPI `:8000`) e
`streamlit` (`:8501`) — o Oracle vem do Cap-3 (externo). Configure as variáveis:

```bash
export DATA_SOURCE=local
export ORACLE_DSN="localhost:1521/XEPDB1"
export ORACLE_USER="<usuario>"
export ORACLE_PASSWORD="<senha>"
export API_URL="http://api:8000"
export MODELS_DIR="models"
export DATA_PATH="data/processed/dataset_ml.parquet"

docker compose up -d
```

Acesse o dashboard em **http://localhost:8501** e a API em
**http://localhost:8000**.

### 6.3 Rodar o Streamlit local em modo `cloud` (sem banco)

Para validar o comportamento online **sem** subir Oracle/API (útil para conferir
o que será publicado):

```bash
DATA_SOURCE=cloud \
DATA_PATH=data/processed/dataset_ml.parquet \
MODELS_DIR=models \
streamlit run streamlit/app.py
```

---

## 7. Resumo

1. Versione `data/processed/dataset_ml.parquet` e `models/*.joblib` no GitHub.
2. Crie o app no Streamlit Cloud apontando para `streamlit/app.py`.
3. Defina `DATA_SOURCE=cloud` (+ `DATA_PATH`, `MODELS_DIR`) nos **Secrets**.
4. Deploy, valide pelo checklist e compartilhe a URL pública.

Para a demonstração com banco ao vivo, use a **alternativa local** com
`docker compose` (Oracle do Cap-3 + api + streamlit em modo `local`).
