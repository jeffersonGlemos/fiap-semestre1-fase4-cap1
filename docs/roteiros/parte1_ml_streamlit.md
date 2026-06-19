# Roteiro de Vídeo — PARTE 1: Integração ML (Scikit-Learn) + Dashboard Streamlit

> **Projeto:** FarmTech Solutions — Fase 4, Capítulo 1 (Assistente Agrícola Inteligente)
> **Autor:** Jefferson Gonçalves Lemos · RM 572399 · Inteligência Artificial — FIAP
> **Entrega:** PARTE 1 — vídeo curto, **máximo 5 minutos**

---

## Objetivo do vídeo

Demonstrar a **integração do modelo de regressão treinado com o dashboard interativo em Streamlit**, explicando:

1. As **bibliotecas** utilizadas e o **pipeline de Machine Learning** implementado.
2. Como o modelo persistido (`models/*.joblib`) é **carregado e consumido** pelo dashboard.
3. O **dashboard em funcionamento**: métricas de desempenho, previsões em tempo real e gráficos.

Foco da PARTE 1: a **ponte** entre o ML e a interface do gestor agrícola (não o detalhe do treino — isso é a PARTE 2).

---

## Duração-alvo

| Total | Limite oficial |
|-------|----------------|
| ~4min30s | **5 minutos** |

Deixe ~30s de margem para não estourar o limite.

---

## Roteiro em blocos (com tempo)

### Bloco 0 — Abertura e contexto (0:00 – 0:30)

**Fala (resumo):**
> "Olá, sou o Jefferson Lemos, RM 572399. Este é o projeto FarmTech Solutions, Fase 4 Capítulo 1: um Assistente Agrícola Inteligente que aplica aprendizado supervisionado de regressão sobre dados de sensores IoT para prever variáveis do campo e sugerir ações de manejo. Nesta PARTE 1 mostro como o modelo de regressão se integra ao dashboard Streamlit."

**Tela:** título do projeto / README aberto / estrutura de pastas (`ml/`, `streamlit/`, `models/`, `data/`).

---

### Bloco 1 — Bibliotecas e visão do pipeline (0:30 – 1:30)

**Fala (resumo):**
> "O pipeline usa **pandas** e **numpy** para tratamento de dados; **scikit-learn** para os modelos de regressão e métricas; **joblib** para persistir os modelos; **pyarrow** para o dataset em Parquet; e **Streamlit** com **Plotly** para o dashboard. O fluxo é: `seed_data.csv` → `ml/prepare_dataset.py` gera o `data/processed/dataset_ml.parquet` com os alvos engenheirados → `ml/train.py` treina e salva `models/*.joblib` e `models/metrics.json` → o `streamlit/app.py` carrega esses artefatos."

**Tela:**
- Abrir `ml/prepare_dataset.py` rapidamente (mostrar imports e a engenharia dos 5 alvos).
- Abrir `ml/train.py` (mostrar `GridSearchCV`, `LinearRegression`, `Ridge`, `RandomForestRegressor`).
- Mostrar a pasta `models/` com os 5 `.joblib` + `metrics.json`.

**Pontos a citar (rápido):**
- Features de entrada: `temperatura, n, p, k, estado_bomba, id_pivo` (one-hot p1/p2/p3), `hora` e `dia_semana`.
- 5 alvos: `rendimento`, `volume_irrigacao`, `necessidade_fertilizacao`, `umidade`, `ph`.

---

### Bloco 2 — A integração: como o Streamlit consome o modelo (1:30 – 2:30)

**Fala (resumo):**
> "A integração acontece no `streamlit/app.py`. Os modelos são carregados uma única vez com `joblib.load`, em cache via `@st.cache_resource`, e as métricas vêm do `metrics.json`. O gestor ajusta os sensores nos controles laterais; o app monta o vetor de features na mesma ordem do treino e chama `model.predict` para cada alvo, devolvendo a previsão em tempo real."

**Tela:**
- Mostrar no `streamlit/app.py` o trecho de carregamento dos modelos (`joblib.load`, `@st.cache_resource`).
- Mostrar o trecho que monta o DataFrame de entrada e chama `.predict()`.
- Destacar o alinhamento de colunas (mesma ordem/one-hot do treino) — ponto crítico da integração.

**Mensagem-chave:** "o modelo treinado offline é reutilizado online sem re-treinar — só carregamento e inferência."

---

### Bloco 3 — Demo do dashboard em funcionamento (2:30 – 4:15)

**Fala (resumo):**
> "Vou subir o dashboard. No topo temos as métricas de desempenho de cada modelo. Ao mover os controles de umidade, temperatura, NPK e estado da bomba, as cinco previsões — rendimento, volume de irrigação, necessidade de fertilização, umidade e pH — se atualizam na hora, junto com as sugestões de manejo."

**Passos na tela:**
1. Subir o app: `streamlit run streamlit/app.py` (ou abrir `http://localhost:8501`).
2. Mostrar o painel de **métricas** (cards com R², RMSE, MAE por alvo).
3. Ajustar os **controles de entrada** (sliders/inputs dos sensores) e mostrar as **previsões atualizando**.
4. Mostrar pelo menos **um gráfico**: correlações (heatmap) e/ou previsto vs. real / importância de variáveis.
5. Mostrar a seção de **sugestões de ação** (ex.: "irrigar X mm", "fertilização: índice Y").

**Tela:** dashboard ao vivo, interação com os controles, gráficos Plotly renderizando.

---

### Bloco 4 — Fechamento (4:15 – 4:45)

**Fala (resumo):**
> "Recapitulando: pipeline scikit-learn → modelos persistidos em joblib → carregados e consumidos pelo Streamlit, entregando previsões e sugestões em tempo real ao gestor. Na PARTE 2 detalho o tratamento de dados, o treino e as métricas. Obrigado!"

**Tela:** voltar ao dashboard completo / estrutura do projeto. Encerrar.

---

## Checklist — o que MOSTRAR na tela

- [ ] Identificação: nome, RM 572399, Fase 4 Cap 1.
- [ ] Estrutura de pastas: `ml/`, `streamlit/`, `models/`, `data/`.
- [ ] Imports/bibliotecas: pandas, numpy, scikit-learn, joblib, pyarrow, streamlit, plotly.
- [ ] `ml/prepare_dataset.py` (geração do Parquet + alvos engenheirados).
- [ ] `ml/train.py` (GridSearchCV; LinearRegression, Ridge, RandomForestRegressor).
- [ ] Artefatos em `models/`: os 5 `.joblib` + `metrics.json`.
- [ ] `streamlit/app.py`: carregamento com `joblib.load` + `@st.cache_resource`.
- [ ] `streamlit/app.py`: montagem das features e chamada `.predict()`.
- [ ] Dashboard ao vivo (`localhost:8501`).
- [ ] Cards de métricas (R², RMSE, MAE).
- [ ] Previsões atualizando ao mover os controles dos sensores.
- [ ] Pelo menos 1 gráfico (correlação / previsto vs. real / importância).
- [ ] Seção de sugestões de manejo (irrigação / fertilização).

---

## Checklist técnico — ANTES de gravar

- [ ] `data/processed/dataset_ml.parquet` gerado (rodar `ml/prepare_dataset.py`).
- [ ] `models/*.joblib` e `models/metrics.json` presentes (rodar `ml/train.py`).
- [ ] `streamlit run streamlit/app.py` sobe sem erro em `localhost:8501`.
- [ ] `DATA_SOURCE` definido (use `cloud`/Parquet local para a demo ficar autossuficiente, sem depender do Oracle).
- [ ] Zoom/fonte do editor e do navegador legíveis na gravação.
- [ ] Cronômetro: ensaiar para fechar em ~4min30s.
