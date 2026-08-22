.PHONY: help up down logs ps test e2e seed migrate reset psql env

COMPOSE := docker compose

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

env: ## Crea .env desde .env.example si no existe
	@test -f .env || (cp .env.example .env && echo "Creado .env desde .env.example")

up: env ## Levanta toda la plataforma (migraciones y seeds incluidos)
	$(COMPOSE) up --build -d
	@echo "Esperando a que terminen las migraciones…"
	@$(COMPOSE) wait migrate >/dev/null 2>&1 || true
	@$(COMPOSE) logs migrate --no-log-prefix | tail -n 40

down: ## Detiene los contenedores (conserva los datos)
	$(COMPOSE) down

logs: ## Sigue los logs de todos los servicios
	$(COMPOSE) logs -f

ps: ## Estado de los contenedores
	$(COMPOSE) ps

migrate: ## Reaplica solo las migraciones (son idempotentes)
	$(COMPOSE) run --rm --entrypoint bash migrate /database/apply.sh migrations

seed: ## Carga los seeds (recursos + emergencias demo)
	$(COMPOSE) run --rm --entrypoint bash migrate /database/apply.sh seeds

psql: ## Abre una sesion psql contra la base local
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-emergency} -d $${POSTGRES_DB:-emergency}

test: ## Corre los tests de todos los servicios
	@for svc in intake dispatch geospatial notification; do \
		if [ -n "$$(ls -A services/$$svc/tests 2>/dev/null)" ]; then \
			echo "── tests: $$svc ──"; \
			$(COMPOSE) run --rm --entrypoint pytest $$svc -q || exit 1; \
		else \
			echo "── tests: $$svc (aun no hay) ──"; \
		fi; \
	done

e2e: ## Prueba de aceptacion end-to-end del §11 (reinicia la base antes)
	$(MAKE) reset
	@echo "Esperando a que el gateway responda…"
	@until curl -sf http://localhost:8080/health >/dev/null 2>&1; do sleep 2; done
	docker build -q -t emergency-e2e ./tests/e2e
	docker run --rm --network emergency-platform_default \
		-e GATEWAY_URL=http://gateway:8080 emergency-e2e test_flow.py

reset: ## Borra el volumen de Postgres y recrea todo desde cero
	$(COMPOSE) down -v
	$(MAKE) up
