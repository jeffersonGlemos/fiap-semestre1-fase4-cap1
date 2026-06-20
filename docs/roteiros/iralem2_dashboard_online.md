# Roteiro de Vídeo — IR ALÉM 2: Dashboard Analítico Online (Streamlit Cloud)

> **Projeto:** FarmTech Solutions — Fase 4, Capítulo 1 (Assistente Agrícola Inteligente)
> **Autor:** Jefferson Gonçalves Lemos · RM 572399 · Inteligência Artificial — FIAP
> **Entrega:** IR ALÉM 2 — vídeo, **máximo 5 minutos**

---

## Objetivo do vídeo

Demonstrar o **dashboard analítico interativo PUBLICADO ONLINE** no **Streamlit Community Cloud**, exibindo:

1. A **publicação** do app no Streamlit Cloud (repo já pronto; main file `streamlit/app.py`; `DATA_SOURCE=cloud` por default). **O deploy/login é manual** (OAuth GitHub → Streamlit, no navegador — não pode ser automatizado).
2. O **funcionamento completo** do dashboard com **previsões** geradas pelos modelos.
3. As **visualizações**: **correlações**, **resultados de previsão** e **tendências de produtividade**.
4. A **interpretação** dos resultados para o gestor agrícola.

**Por que funciona online sem o banco local.** A fonte de dados é comutável por `DATA_SOURCE`:
- `cloud` (**DEFAULT**) → lê o dataset versionado `data/processed/dataset_ml.csv` e os modelos `models/*.joblib` (ambos **commitados** no repo). Não depende de Oracle nem de SQLite no servidor.
- `local` → consome a API FastAPI e/ou o banco SQL (`db/`), com fallback para os arquivos.

Config do Streamlit em `/.streamlit/config.toml` (raiz, tema agrícola) e `requirements.txt` na raiz. **Nenhum secret é necessário.**

---

## Duração-alvo

| Total | Limite oficial |
|-------|----------------|
| ~4min45s | **5 minutos** |

---

## Roteiro em blocos (com tempo)

### Bloco 0 — Publicar no Streamlit Cloud (deploy manual) (0:00 – 0:55)

**Fala (resumo):**
> "Jefferson Lemos, RM 572399. Neste IR ALÉM 2 publico o dashboard da FarmTech no **Streamlit Community Cloud** e mostro ele rodando online. O repositório já está pronto: o main file é `streamlit/app.py`, o `DATA_SOURCE` já vem como `cloud` por default — lendo o dataset e os modelos versionados — e não precisa de nenhum secret. O deploy em si é manual: exige login do GitHub no Streamlit pelo navegador."

**Tela (passo a passo do deploy — manual):**
1. share.streamlit.io → **Sign in with GitHub** (OAuth — passo manual no navegador).
2. **Create app** / **Deploy a public app from GitHub**.
3. Repository: `jeffersonGlemos/fiap-semestre1-fase4-cap1` · Branch: `main`.
4. **Main file path:** `streamlit/app.py`.
5. (Opcional) Advanced settings → Python 3.11+ · confirmar `DATA_SOURCE=cloud` (já é o default).
6. **Deploy** → aguardar o build (instala `requirements.txt` da raiz).

**Pontos a citar:**
- `DATA_SOURCE=cloud` evita qualquer dependência de banco no servidor.
- Tema agrícola vem do `/.streamlit/config.toml` (raiz).

---

### Bloco 1 — App no ar: visão geral e usabilidade (0:55 – 1:45)

**Fala (resumo):**
> "Com o build pronto, abro a **URL pública**. A interface foi pensada para o gestor: cabeçalho com KPIs, navegação por abas e controles no painel lateral. Não exige conhecimento técnico — basta ajustar os parâmetros dos sensores e ler previsões e recomendações."

**Tela:**
- Abrir a **URL pública** do app (Streamlit Cloud), de preferência em aba anônima.
- Tour pelas **6 abas**: `Visão Geral`, `NPK e pH`, `Irrigação`, `Correlações`, `Previsões`, `Sugestões de Manejo`.
- Apontar o badge de fonte de dados (☁️ Cloud) e os KPIs/cards em português.

---

### Bloco 2 — Correlações (1:45 – 2:35)

**Fala (resumo):**
> "Na aba **Correlações**, o heatmap mostra como as variáveis se relacionam. A umidade tende a se relacionar negativamente com o volume de irrigação previsto — faz sentido agronômico: solo mais seco demanda mais água. NPK se relaciona com a necessidade de fertilização."

**Tela:**
- Abrir o **heatmap de correlações** (Plotly): hover para mostrar os valores.
- Apontar 2–3 relações relevantes (umidade ↔ irrigação, NPK ↔ fertilização).

**Interpretação a verbalizar:**
- Correlação ≠ causalidade, mas orienta hipóteses de manejo.

---

### Bloco 3 — Previsões e tendências de produtividade (2:35 – 3:45)

**Fala (resumo):**
> "Aqui o coração do dashboard. Informando os sensores, os modelos preveem **rendimento**, **volume de irrigação**, **necessidade de fertilização**, **umidade** e **pH** — cinco alvos. As abas de Visão Geral e Irrigação mostram as tendências de produtividade ao longo do tempo e por pivô."

**Tela:**
1. Aba **Previsões**: ajustar os **controles de entrada** → ver as **5 previsões** atualizando.
2. Citar os **R²** dos modelos (lidos de `models/metrics.json`): rendimento **0.88**, volume de irrigação **0.94**, necessidade de fertilização **0.97**, umidade **0.77**, pH **0.09**.
3. Aba **Visão Geral / Irrigação**: mostrar a **tendência de produtividade** (linha temporal e comparação entre pivôs p1/p2/p3).

**Interpretação a verbalizar:**
- R² alto (irrigação, fertilização, rendimento) = previsões confiáveis para decisão.
- R² do pH é baixo (0.09) — sinalizo a limitação com honestidade.
- Tendência ajuda o gestor a antecipar safra e planejar insumos.

---

### Bloco 4 — Sugestões de manejo: interpretação para o gestor (3:45 – 4:30)

**Fala (resumo):**
> "Traduzindo para a decisão: na aba **Sugestões de Manejo**, as previsões viram recomendações — quantos milímetros irrigar, o índice de fertilização e o rendimento esperado. O gestor decide com dados, não no 'achismo'."

**Tela:**
- Simular um cenário de **déficit** (umidade baixa, NPK baixo) → ver previsões e sugestões reagindo.
- Comparar com um cenário **ótimo** → mostrar o contraste nas recomendações (`ml/suggest.py`).

---

### Bloco 5 — Fechamento (4:30 – 4:45)

**Fala (resumo):**
> "Recapitulando: dashboard **publicado online** no Streamlit Cloud, com correlações, previsões e tendências, interpretáveis e fáceis de usar — e funcionando sem banco local graças ao `DATA_SOURCE=cloud`, lendo o dataset e os modelos versionados no repo. Do sensor à decisão. Obrigado!"

**Tela:** visão geral do dashboard online + URL pública. Encerrar.

---

## Checklist — o que MOSTRAR na tela

- [ ] Identificação: nome, RM 572399, Fase 4 Cap 1.
- [ ] **Deploy manual** no Streamlit Cloud: login GitHub (OAuth), repo `jeffersonGlemos/fiap-semestre1-fase4-cap1`, main file `streamlit/app.py`.
- [ ] **URL pública** do dashboard funcionando (aba anônima).
- [ ] Fonte comutável por `DATA_SOURCE` (`cloud` = `dataset_ml.csv` + `*.joblib` versionados; `local` = API/banco).
- [ ] Tour das **6 abas** e dos KPIs em português.
- [ ] **Heatmap de correlações** (com interpretação de 2–3 relações).
- [ ] **Previsões** dos 5 alvos atualizando ao mover os controles.
- [ ] **R²** dos modelos (0.88 / 0.94 / 0.97 / 0.77 / 0.09), com honestidade sobre o pH.
- [ ] **Tendência de produtividade** (temporal / por pivô p1/p2/p3).
- [ ] **Sugestões de manejo**: cenário de déficit vs. cenário ótimo (contraste).

---

## Checklist técnico — ANTES de gravar

- [ ] `data/processed/dataset_ml.csv` e `models/*.joblib` **commitados** no repo (essenciais para o modo `cloud`).
- [ ] `requirements.txt` e `/.streamlit/config.toml` na **raiz** do repo.
- [ ] App publicado e buildado no Streamlit Cloud (`DATA_SOURCE=cloud` já é o default — sem secrets).
- [ ] Testar a URL pública em **aba anônima** (garantir que carrega sem dependência local).
- [ ] Confirmar que todos os gráficos (correlação, previsões, tendência) renderizam online.
- [ ] Preparar 2 cenários de entrada (déficit e ótimo) para a comparação ao vivo.
- [ ] Conexão de internet estável durante a gravação.
- [ ] Ensaiar para fechar em ~4min45s.
