# Enunciado de Atividade — Fase 4

Essa fase do projeto FarmTech Solutions marca a consolidação do conhecimento técnico e analítico adquirido ao longo das fases anteriores e o fechamento de um semestre do seu curso. Nesta etapa, a Inteligência Artificial começa a ser aplicada diretamente sobre os dados agrícolas já coletados, estruturados e armazenados.

O foco agora é transformar dados em conhecimento, utilizando aprendizado de máquina supervisionado (regressão) para gerar previsões e insights relevantes sobre o campo, como a relação entre umidade, pH e produtividade, e o impacto das ações de irrigação e fertilização no rendimento final das culturas.

Com base na estrutura lógica e relacional construída nas fases anteriores, vocês deverão compreender como os dados agrícolas podem alimentar modelos de IA permitindo a tomada de decisão automatizada e o suporte inteligente à produção agrícola. Essa integração entre sensores IoT, banco de dados e modelos de Machine Learning representa o início da Agricultura Cognitiva, um campo em que a tecnologia aprende com os dados do campo para otimizar os resultados.

---

## Objetivo Geral

Construir um protótipo de **Assistente Agrícola Inteligente** que:

- Modele um banco de dados simples capaz de armazenar os dados coletados pelos sensores reais ou dados simulados de sensores virtuais do Wokwi.
- Implemente modelos simples de aprendizado supervisionado de regressão (Scikit-Learn) para prever variáveis críticas do campo, como umidade do solo, pH e rendimento esperado.
- Sugira ações futuras de irrigação e manejo agrícola em C++ ou Python, baseadas nas previsões geradas pelos modelos.
- Apresente os resultados de forma acessível e interativa, por meio de um dashboard desenvolvido com Streamlit, facilitando a interpretação dos dados por gestores agrícolas.
- Demonstre domínio técnico e pensamento analítico, aplicando conceitos de IA, ciência de dados e automação em um contexto prático e sustentável do agronegócio.

---

## Atividade Detalhada

### PARTE 1 — Integração de ML com Scikit-Learn e Streamlit em dashboard estática e online para gestores agrícolas

Desenvolver um pipeline completo de Machine Learning usando Scikit-Learn, conectando o modelo de regressão treinado a uma interface interativa desenvolvida com Streamlit.

O dashboard deverá permitir que gestores agrícolas visualizem métricas de desempenho, gráficos de correlação e previsões geradas em tempo real.

#### Entregáveis

O aluno deverá entregar um vídeo curto (máximo 5 minutos) apresentando todas as etapas da solução PARTE 1, incluindo:

- A integração do modelo de regressão com o dashboard em Streamlit.
- A explicação das bibliotecas utilizadas e do pipeline de Machine Learning implementado.
- A demonstração do dashboard em funcionamento, exibindo métricas, previsões e gráficos gerados.

---

### PARTE 2 — Implementação de algoritmos preditivos para sugerir ações futuras de irrigação e manejo agrícola

- Criar e treinar modelos de regressão (linear, múltipla ou não linear) com base nos dados nesta fase ou nas anteriores.
- Implementar previsões sobre parâmetros agrícolas, como volume de irrigação, necessidade de fertilização e estimativa de rendimento.
- Avaliar o desempenho do modelo com métricas como MAE, MSE, RMSE e R², e apresentar recomendações baseadas nos resultados.
- Documentar o processo e apresentar visualizações que justifiquem as decisões tomadas e as previsões obtidas.

#### Entregáveis

O aluno deverá entregar um vídeo de no máximo 5 minutos apresentando toda a solução desenvolvida, incluindo:

- O pipeline de Machine Learning com tratamento de dados, treinamento e validação do modelo de regressão.
- A demonstração da aplicação Streamlit e suas principais funcionalidades.
- As métricas e previsões obtidas pelo modelo e sua interpretação.

---

## Critérios de Avaliação (10 pontos totais)

| Critério | Pontos |
|---|---|
| Qualidade da integração entre o modelo de regressão e o dashboard interativo desenvolvido em Streamlit. | 3 |
| Correta aplicação dos modelos de regressão para prever variáveis agrícolas e sugerir ações de manejo. | 3 |
| Clareza e eficiência na apresentação dos resultados, métricas e previsões no dashboard. | 2 |
| Clareza, objetividade e domínio técnico na apresentação da solução em vídeo, demonstrando o funcionamento completo do projeto. | 2 |

---

## IR ALÉM 1 — Integração dos Dados Reais ou Simulados IoT com o Banco de Dados

Modele um banco de dados simples de acordo com os capítulos de Cognitive Data Science capaz de armazenar os dados de seus sensores.

### Entregáveis

O aluno deverá entregar um vídeo de até 3 minutos demonstrando:

- O funcionamento da ingestão/população de dados IoT no seu banco de dados, de preferência SQL.
- O processo de ingestão e atualização automática dos dados.

---

## IR ALÉM 2 — Dashboard Analítico com Previsões Interativa e Online

Criar um dashboard visual interativo (usando Streamlit, Power BI ou ferramenta similar) exibindo:

- Gráficos de correlação.
- Resultados de previsão.
- Tendências de produtividade.

### Entregáveis

O aluno deverá entregar um vídeo de até 5 minutos demonstrando:

- O funcionamento completo do dashboard analítico com previsões.
- As visualizações criadas (gráficos, correlações e tendências).
- A interpretação dos resultados e a usabilidade da interface para o gestor agrícola.

---

## Critérios de Avaliação (Ir Além)

- Interface funcional em React Native.
- Grau de funcionalidade e coerência da integração entre sensores, base de dados e modelo de IA.
- Criatividade e relevância das soluções apresentadas para o contexto agrícola.
- Clareza, estética e navegabilidade das interfaces criadas (Streamlit, Power BI ou similares).
- Clareza, domínio técnico e capacidade de demonstrar o funcionamento completo da solução em vídeo.

---

## Mensagem Final

Na Fase 4, o aluno consolida ainda mais funcionalidades usando Inteligência Artificial aplicada ao Agronegócio. Da coleta à predição, a FarmTech Solutions evolui para um ecossistema inteligente, onde sensores e algoritmos trabalham juntos para tornar o campo mais eficiente, sustentável e produtivo. O objetivo não é apenas programar, mas compreender o impacto real da IA em um setor essencial para o futuro da humanidade.
