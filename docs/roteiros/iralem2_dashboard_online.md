# Roteiro de Vídeo — IR ALÉM 2: Dashboard Analítico Online com Previsões

> **Projeto:** FarmTech Solutions — Fase 4, Capítulo 1 (Assistente Agrícola Inteligente)
> **Autor:** Jefferson Gonçalves Lemos · RM 572399 · Inteligência Artificial — FIAP
> **Entrega:** IR ALÉM 2 — vídeo, **máximo 5 minutos**

---

## Objetivo do vídeo

Demonstrar o **dashboard analítico interativo e ONLINE** (Streamlit Cloud), exibindo:

1. O **funcionamento completo** do dashboard com **previsões** geradas pelo modelo.
2. As **visualizações**: gráficos de **correlação**, **resultados de previsão** e **tendências de produtividade**.
3. A **interpretação dos resultados** e a **usabilidade** da interface para o gestor agrícola.

Diferencial do IR ALÉM 2: o dashboard está **publicado online** e funciona **sem o Oracle local**, graças à fonte de dados comutável por `DATA_SOURCE`.

---

## Duração-alvo

| Total | Limite oficial |
|-------|----------------|
| ~4min40s | **5 minutos** |

---

## Roteiro em blocos (com tempo)

### Bloco 0 — Abertura e o "online" (0:00 – 0:35)

**Fala (resumo):**
> "Jefferson Lemos, RM 572399. Neste IR ALÉM 2 mostro o dashboard analítico da FarmTech publicado online no Streamlit Cloud. Como o deploy não alcança o Oracle local, a aplicação tem uma fonte de dados comutável: a variável `DATA_SOURCE`. Em `cloud`, ela lê o `dataset_ml.parquet` e os `models/*.joblib` versionados no repositório; em `local`, consome a API FastAPI e o Oracle."

**Tela:**
- Abrir a **URL pública** do dashboard (Streamlit Cloud).
- Mostrar rápido em `streamlit/app.py` o trecho que comuta por `DATA_SOURCE` (local vs. cloud).

---

### Bloco 1 — Visão geral e usabilidade (0:35 – 1:25)

**Fala (resumo):**
> "A interface foi pensada para o gestor: visão geral no topo, navegação por abas, controles à esquerda e resultados à direita. Nenhum conhecimento de código é necessário — basta ajustar os parâmetros dos sensores e ler as previsões e recomendações."

**Tela:**
- Tour pela interface: cabeçalho, abas/seções, painel lateral de controles.
- Mostrar responsividade/clareza (cards de KPI, rótulos em português).

**Pontos a citar (usabilidade):**
- Layout limpo, métricas como KPIs, gráficos interativos (Plotly: zoom/hover).
- Mensagens de recomendação em linguagem do agronegócio.

---

### Bloco 2 — Correlações (1:25 – 2:15)

**Fala (resumo):**
> "Na seção de correlações, o heatmap mostra como as variáveis se relacionam. Veja que umidade tem correlação negativa com o volume de irrigação previsto — faz sentido agronômico: solo mais seco demanda mais água. NPK se relaciona com a necessidade de fertilização."

**Tela:**
- Abrir o **heatmap de correlações** (Plotly).
- Passar o mouse para mostrar valores; apontar 2–3 relações relevantes.

**Interpretação a verbalizar:**
- Correlação ≠ causalidade, mas orienta hipóteses de manejo.
- Destacar pares com forte relação (umidade↔irrigação, NPK↔fertilização).

---

### Bloco 3 — Previsões e tendências de produtividade (2:15 – 3:35)

**Fala (resumo):**
> "Aqui o coração do dashboard: as previsões. Informando os sensores, o modelo prevê rendimento, volume de irrigação, necessidade de fertilização, umidade e pH. O gráfico de previsto vs. real mostra a aderência do modelo, e a aba de tendências mostra a produtividade ao longo do tempo e por pivô."

**Tela:**
1. Ajustar os **controles de entrada** → ver as **5 previsões** atualizando.
2. Mostrar a seção de **sugestões de manejo** (irrigar X mm, fertilizar índice Y, rendimento esperado em sacas/ha).
3. Mostrar gráfico **previsto vs. real** (aderência) e/ou **importância de variáveis**.
4. Mostrar **tendência de produtividade** (linha temporal / comparação entre pivôs p1/p2/p3).

**Interpretação a verbalizar:**
- "Previsto vs. real próximo da diagonal" = modelo confiável.
- Tendência ajuda o gestor a antecipar safra e planejar insumos.

---

### Bloco 4 — Interpretação para o gestor (3:35 – 4:20)

**Fala (resumo):**
> "Traduzindo para a decisão: com estes sensores, o modelo prevê rendimento de N sacas por hectare e recomenda M milímetros de irrigação. Se a necessidade de fertilização sobe, há déficit de NPK a corrigir. O gestor decide com dados, não no 'achismo'."

**Tela:**
- Simular um cenário de **déficit** (umidade baixa, NPK baixo) → ver previsões e recomendações reagindo.
- Comparar com um cenário **ótimo** → mostrar contraste nas sugestões.

---

### Bloco 5 — Fechamento (4:20 – 4:45)

**Fala (resumo):**
> "Recapitulando: dashboard publicado online, com correlações, previsões e tendências, interpretáveis e fáceis de usar pelo gestor — e funcionando sem depender do banco local graças ao `DATA_SOURCE`. Esse é o ciclo completo: do sensor à decisão. Obrigado!"

**Tela:** visão geral do dashboard online + URL pública. Encerrar.

---

## Checklist — o que MOSTRAR na tela

- [ ] Identificação: nome, RM 572399, Fase 4 Cap 1.
- [ ] **URL pública** do dashboard (Streamlit Cloud) funcionando.
- [ ] Comutação de fonte por `DATA_SOURCE` (`cloud` = Parquet + joblib; `local` = API/Oracle).
- [ ] Tour de usabilidade: layout, abas, controles, KPIs em português.
- [ ] **Heatmap de correlações** (com interpretação de 2–3 relações).
- [ ] **Previsões** dos 5 alvos atualizando ao mover os controles.
- [ ] **Sugestões de manejo** (irrigação / fertilização / rendimento).
- [ ] Gráfico **previsto vs. real** e/ou importância de variáveis.
- [ ] **Tendência de produtividade** (temporal / por pivô p1/p2/p3).
- [ ] Cenário de déficit vs. cenário ótimo (contraste das recomendações).

---

## Checklist técnico — ANTES de gravar

- [ ] `data/processed/dataset_ml.parquet` e `models/*.joblib` **commitados** no repositório (necessário para o modo `cloud`).
- [ ] App publicado no Streamlit Cloud, com `DATA_SOURCE=cloud` nas secrets/variáveis.
- [ ] Testar a URL pública em aba anônima (garantir que carrega sem dependência local).
- [ ] Confirmar que todos os gráficos (correlação, previsto vs. real, tendência) renderizam online.
- [ ] Preparar 2 cenários de entrada (déficit e ótimo) para a comparação ao vivo.
- [ ] Conexão de internet estável durante a gravação.
- [ ] Ensaiar para fechar em ~4min40s.
