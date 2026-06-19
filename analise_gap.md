# Análise: Enunciado vs. Já Feito — Fase 4 Cap 1

> **Revisão verificada (2026-06-19):** afirmações conferidas contra o código real.
> Correções aplicadas e gaps adicionais incluídos (ver seção "Histórico de correções").

## Status Geral

| Componente | Status | Onde já existe |
|------------|--------|----------------|
| **Banco de dados para sensores IoT** | ✅ Pronto | **Cap-2** (Postgres + PostGIS via Drizzle, 3 tabelas: `farm_config`, `pivots`, `geo_features`), **Cap-3** (Oracle XE: `SENSORES_FARMTECH` + 6 materialized views) |
| **Dados de sensores simulados** | ✅ Pronto | Cap-2 (ESP32/Wokwi + MQTT: `backend/src/mqtt/`), Cap-3 (gerador Faker + CSV com 2696 linhas) |
| **Dashboard Streamlit** | ⚠️ Parcial | Cap-3 tem Streamlit (4 tabs: Visão Geral, NPK e pH, Irrigação, Correlações; Plotly), mas **sem ML de regressão integrado** e **sem deploy online** |
| **Modelo de regressão (Scikit-Learn)** | ❌ Não feito | Cap-3 tem classificação (RandomForest), fase4_cap4 tem CRISP-DM, mas **nenhum modelo de regressão em todo o projeto** (verificado) |
| **Previsão de umidade, pH, rendimento** | ❌ Não feito | — |
| **Sugestão de irrigação/manejo baseada em ML** | ⚠️ Parcial | Cap-2 tem lógica de irrigação por regras (`backend/src/irrigation/logic.ts`), mas **não preditiva** |
| **Métricas MAE, MSE, RMSE, R²** | ❌ Não feito | — |
| **Gráficos de correlação no Streamlit** | ✅ Pronto | Cap-3 já tem (tab "🔗 Correlações") |

---

## O que JÁ TEMOS e pode ser reutilizado

1. **Dados de sensores** — `Cap-3/fase3_cap1/data/seed_data.csv` (2696 linhas de dados + header = 2697 linhas; 9 colunas: `ID_PIVO, UMIDADE, TEMPERATURA, PH, N, P, K, ESTADO_BOMBA, CAPTURADO_EM`)
2. **Oracle schema** — `Cap-3/fase3_cap1/oracle/farmtech_completo.sql` (tabela `SENSORES_FARMTECH` + 6 materialized views + scheduler de refresh)
3. **Streamlit base** — `Cap-3/fase3_cap1/api/streamlit_app.py` (4 tabs, Plotly, consome API FastAPI, pronto para estender)
4. **Geração de dados** — **dois geradores** (ver ⚠️ ponto de atenção abaixo):
   - `Cap-3/fase3_cap1/api/src/faker_generator.py` (correlações realistas — fonte provável do CSV de 2696 linhas)
   - `Cap-3/fase3_cap1/oracle/generate_sensor_data.py` (`N_ROWS = 200`, numpy seed 42)
5. **Lógica de irrigação** — `Cap-2/backend/src/irrigation/logic.ts` (regras; pode inspirar as sugestões de manejo)
6. **Pipeline ML como referência** — `fase4_cap4/` (CRISP-DM completo) e `tarefa4_seeds_crispdm.md` (esqueleto CRISP-DM), **ambos de classificação** — reaproveitar a estrutura, não os modelos/métricas

---

## O que FALTA construir (GAP)

| # | Item | Prioridade | Notas |
|---|------|-----------|-------|
| 1 | **Dataset de regressão** com target (umidade, pH e/ou rendimento) | 🔴 Alta | Ver ⚠️: a coluna `rendimento` **não existe** em nenhum dataset — precisa ser engenheirada/simulada |
| 2 | **Modelos de regressão** (Linear, Múltipla, Não-linear) | 🔴 Alta | Scikit-Learn: `LinearRegression`, `Ridge`, `RandomForestRegressor` |
| 3 | **Pipeline de ML** (split, train, predict) | 🔴 Alta | `train_test_split`, `fit`, `predict` |
| 4 | **Métricas** (MAE, MSE, RMSE, R²) | 🔴 Alta | `sklearn.metrics` |
| 5 | **Persistir o modelo treinado** (`joblib`/`pickle`) | 🔴 Alta | Pré-requisito para carregar no Streamlit |
| 6 | **Integrar modelo no Streamlit** | 🔴 Alta | Carregar modelo, inputs do usuário, mostrar previsões |
| 7 | **Sugestões de ações** (irrigação, fertilização) | 🟡 Média | Baseado nas previsões do modelo |
| 8 | **Gráficos de previsão** no dashboard | 🟡 Média | Scatter predito vs. real, tendências |
| 9 | **Deploy online do Streamlit** | 🟡 Média | Enunciado pede dashboard "estática e **online**" / "Interativa e **Online**"; não há `.streamlit/`/Streamlit Cloud configurado |
| 10 | **Vídeos** (3× 5min + 1× 3min = 4 vídeos) | 🟡 Depois | PARTE 1 (5min), PARTE 2 (5min), IR ALÉM 1 (3min), IR ALÉM 2 (5min) |

---

## ⚠️ Pontos de atenção / riscos

1. **Variável `rendimento` não existe** em nenhum dataset atual. É o alvo central que o enunciado pede prever. Opções: (a) engenheirar a coluna no gerador como função de umidade+pH+NPK; ou (b) focar a regressão em prever umidade/pH a partir das demais variáveis (já viável com os dados atuais).
2. **Dois geradores de dados divergentes.** `generate_sensor_data.py` usa `N_ROWS = 200`, mas o CSV real tem 2696 linhas → o CSV foi gerado pelo `faker_generator.py`. Definir qual é a fonte de verdade antes de estender para incluir o target.
3. **CRISP-DM existente é de classificação.** `tarefa4_seeds_crispdm.md` e `fase4_cap4` precisam ser adaptados de classificação → regressão (modelos e métricas mudam: acurácia/F1 → MAE/MSE/RMSE/R²).
4. **React Native (ambiguidade do enunciado).** Os "Critérios de Avaliação (Ir Além)" citam "Interface funcional em React Native", mas o corpo do enunciado pede Streamlit/Power BI. Aparenta ser boilerplate do template FIAP. **Não há React Native implementado** no projeto. Confirmar com o professor se é exigência real ou apenas Streamlit basta.

---

## Resumo Visual

```
ENUNCIADO PEDE                    STATUS
─────────────────────────────────────────────
Banco de dados sensor IoT         ✅ Existe (Cap-2 Postgres, Cap-3 Oracle)
Scikit-Learn regressão            ❌ FALTA (só tem classificação)
Prever umidade/pH/rendimento      ❌ FALTA (rendimento nem existe nos dados)
Dashboard Streamlit               ⚠️  Existe mas sem ML e sem deploy online
Métricas MAE/MSE/RMSE/R²          ❌ FALTA
Sugestões irrigação/manejo        ⚠️  Só por regras, não preditivo
Gráficos correlação               ✅ Existe (Cap-3, tab Correlações)
Integração IoT→DB→ML              ⚠️  IoT+DB sim, ML não
Dashboard online (deploy)         ❌ FALTA
```

---

## Conclusão

A infraestrutura (dados, DB, Streamlit, IoT) já existe. O gap principal é **criar os modelos de regressão, integrá-los ao Streamlit e gerar previsões/sugestões** — além de **simular a variável `rendimento`** e **publicar o dashboard online**.

### Caminho sugerido

1. Definir a fonte de dados (faker vs. CSV) e **engenheirar a coluna `rendimento`** como target
2. Treinar modelos de regressão (`LinearRegression`, `Ridge`, `RandomForestRegressor`)
3. Avaliar com MAE, MSE, RMSE, R²
4. Persistir o melhor modelo (`joblib`)
5. Integrar o modelo no Streamlit existente (nova tab de previsões + sugestões de irrigação/fertilização)
6. Publicar o dashboard online (Streamlit Cloud)
7. Gravar os 4 vídeos de entrega

---

## Histórico de correções (2026-06-19)

Correções aplicadas após verificação contra o código:

- **Cap-2 NÃO usa Oracle.** Usa **Postgres + PostGIS via Drizzle ORM** com **3 tabelas** (`farm_config`, `pivots`, `geo_features`) — não "Oracle, 5 tabelas". O Oracle está no **Cap-3**.
- **Contagem de linhas:** `seed_data.csv` tem **2696 linhas de dados** (2697 com header) — corrigido o "2496" que aparecia inconsistente na tabela de status.
- **Colunas do CSV listadas por extenso** (eram "9 cols ... etc.").
- **Gaps adicionais incluídos:** persistência do modelo (joblib), deploy online do Streamlit.
- **Pontos de atenção novos:** variável `rendimento` inexistente, dois geradores divergentes, CRISP-DM existente ser de classificação, ambiguidade do React Native no enunciado.
