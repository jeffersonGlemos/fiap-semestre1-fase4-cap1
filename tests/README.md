# Testes — FarmTech Solutions (Fase 4, Cap 1)

Suíte `pytest` cobrindo o pipeline de ML, o banco IoT, a API, o dashboard e a
consistência entre os módulos.

## Rodar os testes

```bash
pip install -r ../requirements.txt   # (a partir da raiz: pip install -r requirements.txt)
pytest                               # usa ../pytest.ini → testpaths=tests
```

Os testes que dependem de bibliotecas opcionais **pulam automaticamente** se elas
não estiverem instaladas: `test_api.py` (FastAPI) e `test_dashboard.py` (Streamlit).

## Cobertura

A medição simples mede o processo principal (db / ml / api):

```bash
pytest --cov --cov-report=term-missing
```

> **Atenção:** `tests/test_dashboard.py` roda o `AppTest` do Streamlit num
> **subprocesso** (para não sombrear o pacote `streamlit` com o diretório local
> `streamlit/`). Por isso, no comando acima, `streamlit/app.py` aparece com
> cobertura baixa/zero mesmo sendo exercitado.

Para incluir o subprocesso e obter a cobertura **real** (~70% no total), use o
modo paralelo do coverage com `process_startup` (capta o subprocesso):

```bash
# a partir da raiz do projeto
mkdir -p /tmp/covstart
echo 'import coverage; coverage.process_startup()' > /tmp/covstart/sitecustomize.py
COVERAGE_PROCESS_START=$(pwd)/.coveragerc PYTHONPATH=/tmp/covstart \
  coverage run -m pytest -q
coverage combine
coverage report -m
```

## Organização

| Arquivo | Cobre |
|---|---|
| `test_prepare_dataset.py` | engenharia de features + alvos simulados |
| `test_train_features.py`  | features por-alvo, ausência de data leakage |
| `test_train_pipeline.py`  | laço de treino (train_target, save_model/metrics) |
| `test_suggest.py`         | montagem de features, previsão, regras de manejo |
| `test_db_ingest.py`       | ingestão SQLite (idempotência, loop), ler_dados, dialeto |
| `test_api.py`             | FastAPI (health, predict, sensores) |
| `test_dashboard.py`       | dashboard Streamlit (AppTest, modo cloud) |
| `test_consistency.py`     | metrics.json, nomes de feature, arquivos referenciados |
