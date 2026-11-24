SPRINT := $(shell cat SPRINT)
export $(shell sed 's/=.*//' .env 2>/dev/null)

.PHONY: up down test lint gate gate-live doctor

up:
	docker compose up -d --wait

down:
	docker compose down

test:
	cd backend && uv run pytest -m "not live"

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app

gate:
	@N=$(N); \
	if [ -z "$$N" ]; then N=$(SPRINT); fi; \
	MARKEXPR=$$(seq 0 $$N | sed 's/^/sprint/' | paste -sd' or '); \
	echo "Running gate for sprints 0..$$N"; \
	cd backend && uv run pytest -m "($$MARKEXPR) and not live" --cov=app --cov-report=term-missing --cov-fail-under=85 \
	&& uv run ruff check . && uv run ruff format --check . && uv run mypy app

gate-live:
	@N=$(N); \
	if [ -z "$$N" ]; then N=$(SPRINT); fi; \
	MARKEXPR=$$(seq 0 $$N | sed 's/^/sprint/' | paste -sd' or '); \
	cd backend && uv run pytest -m "$$MARKEXPR" --cov=app --cov-report=term-missing --cov-fail-under=85 \
	&& uv run ruff check . && uv run ruff format --check . && uv run mypy app

doctor:
	cd backend && uv run python -m app.core.doctor