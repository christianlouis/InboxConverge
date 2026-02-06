.PHONY: help install test lint format security clean run-dev docker-build docker-up migrate shell

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Setup
install: ## Install all dependencies
	pip install -r requirements.txt
	cd backend && pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	cd backend && pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov black ruff mypy pre-commit

setup-pre-commit: ## Setup pre-commit hooks
	pre-commit install

# Code Quality
lint: ## Run linting checks
	@echo "Running ruff..."
	ruff check backend/
	@echo "Running mypy..."
	mypy backend/app --ignore-missing-imports

format: ## Format code with black and ruff
	@echo "Formatting with black..."
	black backend/
	@echo "Fixing with ruff..."
	ruff check backend/ --fix

format-check: ## Check code formatting without changing files
	black backend/ --check
	ruff check backend/

# Testing
test: ## Run all tests
	pytest backend/tests/ -v

test-cov: ## Run tests with coverage report
	pytest backend/tests/ -v --cov=backend/app --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	pytest backend/tests/unit/ -v

test-integration: ## Run integration tests only
	pytest backend/tests/integration/ -v

test-watch: ## Run tests in watch mode
	pytest-watch backend/tests/ -v

# Security
security: ## Run security checks
	@echo "Running bandit..."
	bandit -r backend/app -ll
	@echo "Running safety..."
	safety check --json

security-full: ## Run comprehensive security scan
	@echo "Running bandit..."
	bandit -r backend/app -ll
	@echo "Running safety..."
	safety check
	@echo "Checking for secrets..."
	detect-secrets scan --all-files

# Database
migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

migrate-create: ## Create a new migration (use name=your_migration_name)
	cd backend && alembic revision --autogenerate -m "$(name)"

migrate-history: ## Show migration history
	cd backend && alembic history

migrate-current: ## Show current migration version
	cd backend && alembic current

db-reset: ## Reset database (DANGER: deletes all data!)
	cd backend && alembic downgrade base
	cd backend && alembic upgrade head

# Docker
docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-restart: ## Restart Docker containers
	docker-compose restart

docker-clean: ## Remove all Docker containers, images, and volumes
	docker-compose down -v
	docker system prune -af

# Running
run-dev: ## Run backend in development mode
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-worker: ## Run Celery worker
	cd backend && celery -A app.core.celery_app worker --loglevel=info

run-beat: ## Run Celery beat scheduler
	cd backend && celery -A app.core.celery_app beat --loglevel=info

run-flower: ## Run Flower (Celery monitoring)
	cd backend && celery -A app.core.celery_app flower --port=5555

run-legacy: ## Run legacy pop3_forwarder script
	python pop3_forwarder.py

# Database Shell
shell: ## Open database shell
	docker-compose exec db psql -U postgres -d pop3_forwarder

shell-python: ## Open Python shell with app context
	cd backend && python -c "from app.core.database import SessionLocal; db = SessionLocal(); print('Database session available as db')"

# Cleanup
clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

clean-all: clean docker-clean ## Clean everything including Docker

# CI/CD
ci-test: format-check lint security test-cov ## Run all CI checks

# Documentation
docs-serve: ## Serve documentation locally
	@echo "Documentation available in docs/ directory"
	@echo "Open docs/ARCHITECTURE.md, docs/CODING_PATTERNS.md, etc."

# Environment
env-check: ## Check if required environment variables are set
	@echo "Checking environment variables..."
	@python -c "import os; required=['DATABASE_URL','SECRET_KEY','ENCRYPTION_KEY']; missing=[v for v in required if not os.getenv(v)]; print('✅ All required vars set' if not missing else f'❌ Missing: {missing}')"

# Development helpers
init-dev: install-dev setup-pre-commit docker-up migrate ## Initialize development environment
	@echo "✅ Development environment initialized!"
	@echo "Run 'make run-dev' to start the backend"

quick-test: format lint test ## Quick quality check before commit

# Release
version: ## Show current version
	@echo "Version information:"
	@git describe --tags --always

tag: ## Create a new version tag (use v=1.0.0)
	@echo "Creating tag $(v)..."
	git tag -a $(v) -m "Release $(v)"
	git push origin $(v)
