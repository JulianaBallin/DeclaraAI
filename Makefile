.PHONY: help \
	up up-build down down-v build restart \
	restart-backend restart-frontend restart-ollama \
	logs logs-backend logs-frontend logs-ollama ps health \
	shell shell-ollama inspect-backend inspect-frontend inspect-ollama \
	build-no-cache images prune \
	lint format check test test-cov clean \
	modelo ingest status

# ── Variáveis ─────────────────────────────────────────────────────────────────
COMPOSE          = docker compose
CONTAINER_BACK   = declaraai-backend
CONTAINER_FRONT  = declaraai-frontend
CONTAINER_OLLAMA = declaraai-ollama
SRC_DIR          = backend/app
PYTHON           ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PIP              := $(PYTHON) -m pip
FLAKE8           := $(PYTHON) -m flake8
BLACK            := $(PYTHON) -m black
ISORT            := $(PYTHON) -m isort

# ── Ajuda ─────────────────────────────────────────────────────────────────────
help: ## Mostra esta mensagem de ajuda
	@printf "\n\033[1;33mDeclaraAI — Comandos disponíveis\033[0m\n"

	@printf "\n\033[1;36mCiclo da Stack\033[0m\n"
	@printf "  make up                - sobe todos os serviços em background\n"
	@printf "  make up-build          - sobe tudo com rebuild das imagens\n"
	@printf "  make down              - para e remove containers\n"
	@printf "  make down-v            - para containers e remove volumes\n"
	@printf "  make build             - apenas reconstrói as imagens\n"
	@printf "  make restart           - reinicia todos os serviços\n"
	@printf "  make restart-backend   - reinicia apenas o backend\n"
	@printf "  make restart-frontend  - reinicia apenas o frontend\n"
	@printf "  make restart-ollama    - reinicia apenas o Ollama\n"

	@printf "\n\033[1;36mDiagnóstico\033[0m\n"
	@printf "  make ps                - lista containers em execução\n"
	@printf "  make logs              - acompanha logs de todos os serviços\n"
	@printf "  make logs-backend      - acompanha logs do backend\n"
	@printf "  make logs-frontend     - acompanha logs do frontend\n"
	@printf "  make logs-ollama       - acompanha logs do Ollama\n"
	@printf "  make health            - checa o endpoint / da API\n"
	@printf "  make status            - exibe status e métricas do pipeline RAG\n"

	@printf "\n\033[1;36mDepuração\033[0m\n"
	@printf "  make shell             - abre shell no container do backend\n"
	@printf "  make shell-ollama      - abre shell no container do Ollama\n"
	@printf "  make inspect-backend   - inspeciona o container do backend\n"
	@printf "  make inspect-frontend  - inspeciona o container do frontend\n"
	@printf "  make inspect-ollama    - inspeciona o container do Ollama\n"

	@printf "\n\033[1;36mImagens e Build\033[0m\n"
	@printf "  make build-no-cache    - reconstrói imagens sem usar cache\n"
	@printf "  make images            - lista imagens Docker locais\n"
	@printf "  make prune             - remove recursos Docker não usados\n"

	@printf "\n\033[1;36mModelo e Ingestão\033[0m\n"
	@printf "  make modelo            - baixa o modelo Mistral no Ollama\n"
	@printf "  make ingest            - re-indexa a base de conhecimento via API\n"

	@printf "\n\033[1;36mQualidade de Código\033[0m\n"
	@printf "  make lint              - verifica o código com flake8\n"
	@printf "  make format            - formata com black e isort\n"
	@printf "  make check             - verifica formatação sem alterar arquivos\n"
	@printf "  make test              - executa os testes com pytest\n"
	@printf "  make test-cov          - executa testes com cobertura\n"
	@printf "  make clean             - remove arquivos de cache Python\n\n"

# ── Docker Compose / Ciclo da Stack ───────────────────────────────────────────
up: ## Sobe todos os serviços em background
	$(COMPOSE) up -d

up-build: ## Reconstrói as imagens e sobe os serviços
	$(COMPOSE) up -d --build

down: ## Para e remove os containers
	$(COMPOSE) down

down-v: ## Para containers e remove volumes (apaga modelos Ollama)
	$(COMPOSE) down -v

build: ## Apenas reconstrói as imagens
	$(COMPOSE) build

restart: ## Reinicia todos os serviços
	$(COMPOSE) restart

restart-backend: ## Reinicia apenas o backend
	$(COMPOSE) restart backend

restart-frontend: ## Reinicia apenas o frontend
	$(COMPOSE) restart frontend

restart-ollama: ## Reinicia apenas o Ollama
	$(COMPOSE) restart ollama

# ── Logs / Diagnóstico ────────────────────────────────────────────────────────
logs: ## Acompanha logs de todos os serviços
	$(COMPOSE) logs -f

logs-backend: ## Acompanha logs do backend
	$(COMPOSE) logs -f backend

logs-frontend: ## Acompanha logs do frontend
	$(COMPOSE) logs -f frontend

logs-ollama: ## Acompanha logs do Ollama
	$(COMPOSE) logs -f ollama

ps: ## Lista os containers em execução
	$(COMPOSE) ps

health: ## Checa o endpoint raiz da API (health check)
	@curl -s http://localhost:8000/ | $(PYTHON) -m json.tool

status: ## Exibe status e métricas do pipeline RAG
	@curl -s http://localhost:8000/status | $(PYTHON) -m json.tool

# ── Shell / Depuração ─────────────────────────────────────────────────────────
shell: ## Abre shell no container do backend
	$(COMPOSE) exec backend sh

shell-ollama: ## Abre shell no container do Ollama
	$(COMPOSE) exec ollama sh

inspect-backend: ## Mostra detalhes completos do container do backend
	docker inspect $(CONTAINER_BACK)

inspect-frontend: ## Mostra detalhes completos do container do frontend
	docker inspect $(CONTAINER_FRONT)

inspect-ollama: ## Mostra detalhes completos do container do Ollama
	docker inspect $(CONTAINER_OLLAMA)

# ── Imagens e Build ───────────────────────────────────────────────────────────
build-no-cache: ## Reconstrói as imagens sem usar cache
	$(COMPOSE) build --no-cache

images: ## Lista imagens Docker locais
	docker images

prune: ## Remove recursos Docker não utilizados
	docker system prune

# ── Modelo e Ingestão ─────────────────────────────────────────────────────────
modelo: ## Baixa o modelo Mistral 7B no container do Ollama
	docker exec -it $(CONTAINER_OLLAMA) ollama pull mistral

ingest: ## Re-indexa a base de conhecimento via API
	@curl -s -X POST http://localhost:8000/ingest | $(PYTHON) -m json.tool

# ── Qualidade de Código ───────────────────────────────────────────────────────
lint: ## Verifica o código com flake8
	$(FLAKE8) $(SRC_DIR)

format: ## Formata o código com black e isort
	$(ISORT) $(SRC_DIR)
	$(BLACK) $(SRC_DIR)

check: ## Verifica formatação sem modificar arquivos (CI)
	$(ISORT) --check-only $(SRC_DIR)
	$(BLACK) --check $(SRC_DIR)
	$(FLAKE8) $(SRC_DIR)

# ── Testes ────────────────────────────────────────────────────────────────────
test: ## Executa os testes com pytest
	$(PYTHON) -m pytest -v

test-cov: ## Executa testes com relatório de cobertura
	$(PYTHON) -m pytest --cov=$(SRC_DIR) --cov-report=term-missing -v

# ── Utilitários ───────────────────────────────────────────────────────────────
clean: ## Remove arquivos de cache Python
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete
