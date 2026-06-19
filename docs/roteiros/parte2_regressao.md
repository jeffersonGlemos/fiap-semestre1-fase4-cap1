# Roteiro de Vídeo — PARTE 2: Pipeline de Regressão (treino, validação, métricas)

> **Projeto:** FarmTech Solutions — Fase 4, Capítulo 1 (Assistente Agrícola Inteligente)
> **Autor:** Jefferson Gonçalves Lemos · RM 572399 · Inteligência Artificial — FIAP
> **Entrega:** PARTE 2 — vídeo, **máximo 5 minutos**

---

## Objetivo do vídeo

Apresentar o **pipeline completo de Machine Learning de regressão**, do dado bruto à previsão:

1. **Tratamento de dados** (limpeza, engenharia de features e de alvos).
2. **Treinamento e validação** dos modelos de regressão (linear, regularizado e não-linear).
3. **Avaliação** com **MAE, MSE, RMSE e R²** e a **interpretação** desses resultados.
4. **Demonstração** da aplicação Streamlit e suas principais funcionalidades, conectando previsões a **ações de manejo** (irrigação, fertilização, rendimento).

Foco da PARTE 2: o **rigor metodológico** do ML (a integração visual foi o foco da PARTE 1).

---

## Duração-alvo

| Total | Limite oficial |
|-------|----------------|
| ~4min40s | **5 minutos** |

---

## Roteiro em blocos (com tempo)

### Bloco 0 — Abertura e problema (0:00 – 0:25)

**Fala (resumo):**
> "Jefferson Lemos, RM 572399. Nesta PARTE 2 mostro o pipeline de regressão supervisionada da FarmTech: a partir de dados de sensores IoT, prevejo cinco variáveis agrícolas e sugiro ações de manejo. Vamos do tratamento dos dados às métricas e à interpretação."

**Tela:** título / `data/raw/seed_data.csv` aberto (mostrar as 9 colunas e ~2696 linhas).

---

### Bloco 1 — Os dados e o tratamento (0:25 – 1:25)

**Fala (resumo):**
> "A base tem 2696 leituras dos pivôs p1, p2 e p3, com umidade, temperatura, pH, NPK, estado da bomba e timestamp. No `ml/prepare_dataset.py` eu trato os dados: normalizo `estado_bomba` para 1/0, aplico one-hot em `id_pivo`, e derivo `hora` e `dia_semana` do `capturado_em`. Como o enunciado pede prever rendimento — que não existe nos sensores — eu **engenheiro** três alvos por heurística agronômica, além de usar umidade e pH, que são reais."

**Tela:**
- `data/raw/seed_data.csv` (colunas: `ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM`).
- `ml/prepare_dataset.py`: trecho da função sino `bell(x, opt, sd) = exp(-0.5*((x-opt)/sd)**2)` e das fórmulas dos alvos.
- Mostrar a saída `data/processed/dataset_ml.parquet`.

**Pontos a citar:**
- **Features:** `temperatura, n, p, k, estado_bomba, id_pivo` (one-hot), `hora`, `dia_semana`.
- **Alvos engenheirados:** `rendimento` (0–80), `volume_irrigacao` (0–40 mm), `necessidade_fertilizacao` (0–100).
- **Alvos reais:** `umidade` (%), `ph`.
- **Reprodutibilidade:** `numpy seed 42` (ruído controlado nas heurísticas).

---

### Bloco 2 — Treinamento e validação (1:25 – 2:45)

**Fala (resumo):**
> "No `ml/train.py` faço o split treino/teste 80/20 com `random_state=42`. Para cada alvo comparo três algoritmos: `LinearRegression` como baseline, `Ridge` (regularização L2) e `RandomForestRegressor` para capturar não-linearidades. A seleção de hiperparâmetros é via `GridSearchCV` com validação cruzada de 5 folds, e o melhor modelo de cada alvo é persistido com `joblib`."

**Tela:**
- `ml/train.py`: `train_test_split(..., test_size=0.2, random_state=42)`.
- Dicionário de modelos/param_grid e o `GridSearchCV(cv=5)`.
- Laço que treina os 5 alvos e salva `models/modelo_<alvo>.joblib`.
- Geração do `models/metrics.json`.

**Pontos a citar:**
- Por que 3 modelos: comparar baseline linear vs. não-linear, evitar overfitting com Ridge.
- `cv=5`: estima generalização antes do teste final.

---

### Bloco 3 — Métricas e interpretação (2:45 – 3:55)

**Fala (resumo):**
> "Agora as métricas no conjunto de teste. **MAE** é o erro médio absoluto, na unidade do alvo — fácil de explicar ao gestor. **MSE** penaliza erros grandes; **RMSE** é a raiz, voltando à unidade original. **R²** mede quanto da variância o modelo explica: quanto mais perto de 1, melhor. Tipicamente o RandomForest vence nos alvos não-lineares como rendimento, enquanto Ridge é competitivo em umidade e pH."

**Tela:**
- Abrir `models/metrics.json` (ou a tabela de métricas no dashboard).
- Apontar, por alvo: **MAE / MSE / RMSE / R²** e qual modelo foi escolhido.
- Comentar 1 caso bom (R² alto) e a leitura prática do RMSE ("erramos em média ± X mm de irrigação").

**Interpretação a verbalizar:**
- **R² alto + RMSE baixo** → previsão confiável para decidir manejo.
- **MAE** é a métrica que comunica ao gestor o erro esperado na unidade real.
- Comparar baseline (Linear) vs. escolhido para justificar a escolha do não-linear.

---

### Bloco 4 — Demo Streamlit e ações de manejo (3:55 – 4:35)

**Fala (resumo):**
> "Por fim, as previsões viram decisão. No dashboard, ao informar os sensores, o modelo prevê rendimento, volume de irrigação e necessidade de fertilização, e o app converte isso em sugestões: quanto irrigar, se há déficit de NPK e o rendimento esperado em sacas por hectare."

**Tela:**
- Dashboard ao vivo: mover entradas → previsões e sugestões mudando.
- Mostrar gráfico que justifica a decisão (previsto vs. real ou importância de variáveis).

---

### Bloco 5 — Fechamento (4:35 – 4:50)

**Fala (resumo):**
> "Resumindo: tratamento reprodutível, três modelos comparados com validação cruzada, avaliação por MAE, MSE, RMSE e R², e previsões traduzidas em ações de manejo no Streamlit. Obrigado!"

**Tela:** `metrics.json` + dashboard lado a lado. Encerrar.

---

## Checklist — o que MOSTRAR na tela

- [ ] Identificação: nome, RM 572399, Fase 4 Cap 1.
- [ ] `data/raw/seed_data.csv` (9 colunas, ~2696 linhas, pivôs p1/p2/p3).
- [ ] `ml/prepare_dataset.py`: limpeza, one-hot `id_pivo`, derivação `hora`/`dia_semana`.
- [ ] Engenharia dos alvos: função `bell`, fórmulas de rendimento/volume/fertilização, `numpy seed 42`.
- [ ] `data/processed/dataset_ml.parquet` gerado.
- [ ] `ml/train.py`: `train_test_split` 80/20, `random_state=42`.
- [ ] Três modelos: `LinearRegression`, `Ridge`, `RandomForestRegressor`.
- [ ] `GridSearchCV(cv=5)` (validação cruzada).
- [ ] Persistência: `models/modelo_<alvo>.joblib` (5 arquivos).
- [ ] `models/metrics.json` com MAE/MSE/RMSE/R² por alvo.
- [ ] Interpretação verbal das métricas (R², RMSE, MAE).
- [ ] Demo do dashboard com previsões + sugestões de manejo.
- [ ] Gráfico de justificativa (previsto vs. real / importância de variáveis).

---

## Checklist técnico — ANTES de gravar

- [ ] Rodar `ml/prepare_dataset.py` → confirma `dataset_ml.parquet`.
- [ ] Rodar `ml/train.py` → confirma 5 `.joblib` + `metrics.json` atualizados.
- [ ] Conferir que os valores em `metrics.json` "fecham" com o que vai narrar.
- [ ] `streamlit run streamlit/app.py` sobe sem erro.
- [ ] Ter um exemplo de entrada que gere previsões "boas" e outro com déficit (para contraste).
- [ ] Ensaiar para fechar em ~4min40s.
