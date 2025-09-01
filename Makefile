.PHONY: help build up down logs clean test format lint setup initial-sync incremental-sync daemon

help: ## Show this help message
	@echo 'S3 Sync Service - Make Commands'
	@echo ''
	@echo 'Setup Commands:'
	@echo '  setup           Build and start all services'
	@echo '  build           Build Docker images'
	@echo '  up              Start all services'
	@echo '  down            Stop all services'
	@echo '  clean           Clean up containers and volumes'
	@echo ''
	@echo 'Sync Commands:'
	@echo '  initial-sync    Run initial synchronization (first time setup)'
	@echo '  incremental-sync Run incremental synchronization'
	@echo '  daemon          Run in daemon mode (periodic sync)'
	@echo '  status          Show service status'
	@echo '  test-workflow   Run end-to-end test workflow'
	@echo ''
	@echo 'Development Commands:'
	@echo '  logs            Show logs for all services'
	@echo '  logs-sync       Show sync service logs only'
	@echo '  logs-api        Show mock API logs only'
	@echo '  shell           Open shell in sync service container'
	@echo '  test            Run unit tests'
	@echo '  format          Format code with black'
	@echo '  lint            Lint code with flake8'

setup: build up ## Build and start all services
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services are ready!"

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

initial-sync: ## Run initial synchronization (for new deployments)
	docker-compose exec sync-service python -m sync_service.main initial-sync

incremental-sync: ## Run incremental synchronization
	docker-compose exec sync-service python -m sync_service.main incremental-sync

daemon: ## Run in daemon mode (periodic sync)
	docker-compose exec sync-service python -m sync_service.main daemon

status: ## Show service status and statistics
	docker-compose exec sync-service python -m sync_service.main status

test-workflow: ## Run end-to-end test workflow
	docker-compose exec sync-service python -m sync_service.main test

logs: ## Show logs for all services
	docker-compose logs -f

logs-sync: ## Show logs for sync service only
	docker-compose logs -f sync-service

logs-api: ## Show logs for mock API only
	docker-compose logs -f mock-api

restart: ## Restart all services
	docker-compose restart

restart-sync: ## Restart sync service only
	docker-compose restart sync-service

test: ## Run unit tests
	docker-compose exec sync-service python -m pytest tests/ -v

format: ## Format code with black
	docker-compose exec sync-service black sync_service/ tests/

lint: ## Lint code with flake8
	docker-compose exec sync-service flake8 sync_service/ tests/

shell: ## Open shell in sync service container
	docker-compose exec sync-service /bin/bash

api-shell: ## Open shell in mock API container
	docker-compose exec mock-api /bin/bash

ps: ## Show running containers
	docker-compose ps