# SOC Copilot Makefile
# Usage: make <command>

.PHONY: help dev build test lint format clean install

# Default target
help:
	@echo "SOC Copilot - Available Commands:"
	@echo ""
	@echo "  Development:"
	@echo "    dev              Start both frontend and backend"
	@echo "    dev-frontend     Start frontend only (port 3003)"
	@echo "    dev-backend      Start backend only (port 8000)"
	@echo ""
	@echo "  Building:"
	@echo "    build            Build frontend for production"
	@echo "    build-analyze    Build with bundle analyzer"
	@echo ""
	@echo "  Testing:"
	@echo "    test             Run all tests"
	@echo "    test-frontend    Run frontend tests"
	@echo "    test-backend     Run backend tests"
	@echo "    test-e2e         Run E2E tests"
	@echo "    test-coverage    Run tests with coverage"
	@echo ""
	@echo "  Code Quality:"
	@echo "    lint             Run all linters"
	@echo "    lint-frontend    Run frontend linter"
	@echo "    lint-backend     Run backend linter"
	@echo "    format           Format all code"
	@echo "    type-check       Run TypeScript type checking"
	@echo ""
	@echo "  Database:"
	@echo "    db-migrate       Run database migrations"
	@echo "    db-rollback      Rollback last migration"
	@echo "    db-reset         Reset database"
	@echo ""
	@echo "  Setup & Cleanup:"
	@echo "    install          Install all dependencies"
	@echo "    clean            Clean build artifacts"
	@echo "    reset            Clean and reinstall"
	@echo ""

# Development
dev:
	@echo "🚀 Starting development servers..."
	npm run dev

dev-frontend:
	@echo "🎨 Starting frontend server..."
	cd frontend && npm run dev

dev-backend:
	@echo "⚙️  Starting backend server..."
	cd backend && source ../venv/bin/activate && uvicorn main:app --reload --port 8000

# Building
build:
	@echo "🏗️  Building frontend..."
	cd frontend && npm run build

build-analyze:
	@echo "📊 Building with bundle analyzer..."
	cd frontend && ANALYZE=true npm run build

# Testing
test:
	@echo "🧪 Running all tests..."
	npm run test

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm run test

test-backend:
	@echo "🧪 Running backend tests..."
	cd backend && source ../venv/bin/activate && pytest

test-e2e:
	@echo "🎭 Running E2E tests..."
	cd frontend && npm run test:e2e

test-coverage:
	@echo "📈 Running tests with coverage..."
	npm run test-coverage

# Code Quality
lint:
	@echo "🔍 Running linters..."
	npm run lint

lint-frontend:
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint

lint-backend:
	@echo "🔍 Linting backend..."
	cd backend && source ../venv/bin/activate && ruff check .

format:
	@echo "✨ Formatting code..."
	npm run format

type-check:
	@echo "📝 Running TypeScript type checking..."
	cd frontend && npm run type-check

# Database
db-migrate:
	@echo "📦 Running database migrations..."
	cd backend && source ../venv/bin/activate && alembic upgrade head

db-rollback:
	@echo "⏪ Rolling back migration..."
	cd backend && source ../venv/bin/activate && alembic downgrade -1

db-reset:
	@echo "🔄 Resetting database..."
	cd backend && source ../venv/bin/activate && alembic downgrade base && alembic upgrade head

# Setup & Cleanup
install:
	@echo "📦 Installing dependencies..."
	npm install
	cd frontend && npm install
	cd backend && source ../venv/bin/activate && pip install -r requirements.txt

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf frontend/.next frontend/out frontend/node_modules/.cache
	rm -rf backend/__pycache__ backend/**/__pycache__
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

reset: clean install
	@echo "✅ Reset complete!"

# Docker
docker-up:
	@echo "🐳 Starting Docker containers..."
	docker-compose up -d

docker-down:
	@echo "🐳 Stopping Docker containers..."
	docker-compose down

docker-logs:
	@echo "📋 Showing Docker logs..."
	docker-compose logs -f

docker-reset:
	@echo "🔄 Resetting Docker containers..."
	docker-compose down -v
	docker-compose up -d --build

# Production
prod-build:
	@echo "🏗️  Building for production..."
	npm run build

prod-start:
	@echo "🚀 Starting production servers..."
	cd frontend && npm run start
