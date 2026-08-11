# THE EYE — comandos descobríveis.
#
# `make` sozinho lista tudo. Nenhum comando aqui publica nada: os que expõem
# conteúdo passam pela trava (scripts/publish_lock.py) e não moram num alvo.

PY      := .venv/bin/python
PIP     := .venv/bin/pip
RUFF    := .venv/bin/ruff
EXTRAS  := .[telemetry,dashboard,dev]
LEDGER  ?= https://the-eye-audit-staging.mateusmenezesfigueiredo6.workers.dev

.DEFAULT_GOAL := help
.PHONY: help setup check test lint fmt fmt-check types cov chart adjudicate run-comercial run-dash \
        source-graph leak gates package clean

help:  ## lista os comandos
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	 | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- ambiente

setup:  ## cria o ambiente e instala tudo (usa uv se existir, senão pip)
	@command -v uv >/dev/null 2>&1 \
	 && { uv venv --allow-existing && uv pip install -e '$(EXTRAS)'; } \
	 || { python3 -m venv .venv && $(PIP) install -q -e '$(EXTRAS)'; }
	@echo "pronto — rode 'make check'"

clean:  ## remove artefatos de build e cache
	rm -rf build dist src/*.egg-info .pytest_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

# ------------------------------------------------------------------ qualidade

check: lint fmt-check types test  ## tudo que o CI roda

lint:  ## ruff (lint + import order)
	$(RUFF) check .

fmt-check:  ## formatação, do mesmo jeito que o CI cobra (não corrige)
	$(RUFF) format --check .

fmt:  ## corrige o que o ruff sabe corrigir
	$(RUFF) check . --fix
	$(RUFF) format .

types:  ## checagem de tipos (não falha o build ainda — ver ADR-012)
	@if $(PY) -c "import mypy" 2>/dev/null; then $(PY) -m mypy src/ || true; else echo "  mypy não instalado: pip install mypy"; fi

test:  ## suíte completa
	$(PY) -m pytest tests/ -q

cov:  ## testes com cobertura e relatório HTML
	$(PY) -m pytest tests/ -q --cov=asus_theye --cov-report=term-missing --cov-report=html
	@echo "relatório: htmlcov/index.html"

# --------------------------------------------------------------- operação

chart:  ## Mistress Chart (pipeline, nichos, grafo de fontes)
	$(PY) -m asus_theye.cli chart

source-graph:  ## cobertura do grafo de fontes + relatórios da Fase C
	$(PY) -m asus_theye.cli source-graph --reports

# O único alvo que manda conteúdo para fora: confere as pré-condições e avisa
# antes de enviar. PROPOSER/CHALLENGER sobrescrevem os padrões chatgpt/claude.
adjudicate:  ## adjudicação real com dois modelos: make adjudicate Q="sua pergunta"
	@bash scripts/adjudicate_real.sh "$(Q)"

run-comercial:  ## app do diretor comercial em localhost:8713
	$(PY) -m uvicorn apps.comercial.api:create_app --factory --port 8713

run-dash:  ## painel de benchmark em localhost:8712
	$(PY) -m uvicorn asus_theye.dashboard.app:create_dashboard_app --factory --port 8712

# ------------------------------------------------------------- verificação

leak:  ## tripla checagem de vazamento (estranho, provedor, matemática)
	$(PY) scripts/leak_check.py

gates:  ## portões de lançamento da classe L2
	$(PY) scripts/release_check.py L2

package:  ## zip completo para disco externo, sem segredos
	@bash scripts/empacotar.sh
