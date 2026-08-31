# SOC Copilot Makefile
# Usage: make <command>

.PHONY: help dev build test lint format clean install docker-dev-up docker-dev-down docker-dev-logs docker-dev-build branch-setup branch-validate branch-list branch-create-feature branch-create-fix branch-create-release branch-create-hotfix branch-cleanup release-plan release-start release-changelog release-bump release-finish release-status release-list release-abort setup-dev setup-dev-check setup-env venv-install hooks-install check-versions dev-env-up dev-env-down dev-env-logs db-create-migration db-seed db-shell redis-cli

# Default target
help:
	@echo "SOC Copilot - Available Commands:"
	@echo ""
	@echo "  Development:"
	@echo "    dev              Start both frontend and backend"
	@echo "    dev-frontend     Start frontend only (port 3003)"
	@echo "    dev-backend      Start backend only (port 8000)"
	@echo ""
	@echo "  Dev Environment (FR-004):"
	@echo "    setup-dev        One-click dev environment setup (full initialization)"
	@echo "    setup-dev-check  Check dev environment prerequisites only"
	@echo "    setup-env        Copy .env.example to .env with generated secrets"
	@echo "    venv-install     Install Python dependencies in venv"
	@echo "    hooks-install    Install pre-commit hooks"
	@echo "    check-versions   Verify Python/Node.js versions match requirements"
	@echo ""
	@echo "  Dev Docker (FR-004):"
	@echo "    dev-env-up       Start dev infrastructure (postgres + redis)"
	@echo "    dev-env-down     Stop dev infrastructure"
	@echo "    dev-env-logs     Show dev infrastructure logs"
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
	@echo "    format-backend   Format backend code (black + isort)"
	@echo "    type-check       Run TypeScript type checking"
	@echo "    type-check-backend Run Python type checking (mypy)"
	@echo ""
	@echo "  Database:"
	@echo "    db-migrate         Run database migrations"
	@echo "    db-rollback        Rollback last migration"
	@echo "    db-reset           Reset database"
	@echo "    db-create-migration Create new migration (usage: make db-create-migration MSG=description)"
	@echo "    db-seed            Seed database with initial data"
	@echo "    db-shell           Open database shell (psql)"
	@echo "    redis-cli          Open Redis CLI"
	@echo ""
	@echo "  Setup & Cleanup:"
	@echo "    install          Install all dependencies"
	@echo "    clean            Clean build artifacts"
	@echo "    reset            Clean and reinstall"
	@echo ""
	@echo "  Branch Management (FR-001):"
	@echo "    branch-setup           Setup GitHub branch protection rules"
	@echo "    branch-validate        Validate current branch name"
	@echo "    branch-list            List branches by type"
	@echo "    branch-create-feature  Create feature branch (usage: make branch-create-feature FR=xxx DESC=desc)"
	@echo "    branch-create-fix      Create fix branch (usage: make branch-create-fix FR=xxx DESC=desc)"
	@echo "    branch-create-release  Create release branch (usage: make branch-create-release VER=x.y.z)"
	@echo "    branch-create-hotfix   Create hotfix branch (usage: make branch-create-hotfix VER=x.y.z DESC=desc)"
	@echo "    branch-cleanup         Delete merged local branches"
	@echo ""
	@echo "  Release Management (FR-003):"
	@echo "    release-plan           Show release planning info (usage: make release-plan VER=x.y.z)"
	@echo "    release-start          Create release branch with version bump + changelog (usage: make release-start VER=x.y.z)"
	@echo "    release-changelog      Generate CHANGELOG for version (usage: make release-changelog VER=x.y.z)"
	@echo "    release-bump           Bump version number only (usage: make release-bump VER=x.y.z)"
	@echo "    release-finish         Merge release back to develop and cleanup (usage: make release-finish VER=x.y.z)"
	@echo "    release-status         Show current release branch status"
	@echo "    release-list           List all release branches and tags"
	@echo "    release-abort          Abort release and delete branch (usage: make release-abort VER=x.y.z)"
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

# Dev Environment Setup (FR-004)
setup-dev:
	@echo "🛠️  Running full development environment setup..."
	@chmod +x scripts/setup-dev.sh
	@./scripts/setup-dev.sh

setup-dev-check:
	@echo "🔍 Checking development environment prerequisites..."
	@chmod +x scripts/setup-dev.sh
	@./scripts/setup-dev.sh --check-only

setup-env:
	@echo "📝 Setting up .env file..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env created from .env.example"; \
		echo "⚠️  Please update .env with your actual values (API keys, passwords, etc.)"; \
	else \
		echo "✅ .env already exists"; \
	fi

venv-install:
	@echo "📦 Installing Python dependencies..."
	@if [ ! -d venv ]; then \
		python3 -m venv venv; \
		echo "✅ Virtual environment created"; \
	fi
	@. venv/bin/activate && pip install --upgrade pip --quiet
	@. venv/bin/activate && cd backend && pip install -r requirements.txt --quiet
	@. venv/bin/activate && cd backend && pip install -r requirements-test.txt --quiet 2>/dev/null || true
	@echo "✅ Python dependencies installed"

hooks-install:
	@echo "🪝 Installing pre-commit hooks..."
	@. venv/bin/activate && pre-commit install
	@. venv/bin/activate && pre-commit install --hook-type pre-push
	@. venv/bin/activate && pre-commit install --hook-type commit-msg 2>/dev/null || true
	@echo "✅ Pre-commit hooks installed"

check-versions:
	@echo "🔍 Checking required versions..."
	@echo "  Python: $(shell python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo 'NOT FOUND')"
	@echo "  Required: 3.12 (see .python-version)"
	@echo "  Node.js: $(shell node -v 2>/dev/null || echo 'NOT FOUND')"
	@echo "  Required: >=20 (see .nvmrc)"

# Dev Infrastructure Docker (FR-004)
dev-env-up:
	@echo "🐳 Starting development infrastructure (postgres + redis)..."
	docker compose up -d postgres redis 2>/dev/null || docker-compose up -d postgres redis 2>/dev/null || (echo "❌ Docker compose failed" && exit 1)
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo "✅ Development infrastructure started"

dev-env-down:
	@echo "🐳 Stopping development infrastructure..."
	docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
	@echo "✅ Development infrastructure stopped"

dev-env-logs:
	@echo "📋 Showing development infrastructure logs..."
	docker compose logs -f postgres redis 2>/dev/null || docker-compose logs -f postgres redis 2>/dev/null || true

# Additional Code Quality
format-backend:
	@echo "✨ Formatting backend code..."
	cd backend && source ../venv/bin/activate && black . && isort .

type-check-backend:
	@echo "📝 Running Python type checking..."
	cd backend && source ../venv/bin/activate && mypy . --ignore-missing-imports --exclude 'tests/|migrations_alembic/'

# Extended Database Operations
db-create-migration:
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Usage: make db-create-migration MSG=description"; \
		echo "   Example: make db-create-migration MSG=add_user_preferences"; \
		exit 1; \
	fi
	@echo "📝 Creating migration: $(MSG)..."
	cd backend && source ../venv/bin/activate && alembic revision --autogenerate -m "$(MSG)"

db-seed:
	@echo "🌱 Seeding database with initial data..."
	cd backend && source ../venv/bin/activate && python init_ai_models.py 2>/dev/null || true
	cd backend && source ../venv/bin/activate && python init_correlation_rules.py 2>/dev/null || true
	@echo "✅ Database seeded"

db-shell:
	@echo "🐚 Opening PostgreSQL shell..."
	docker compose exec postgres psql -U $${DB_USER:-soc_copilot} -d $${DB_NAME:-soc_copilot} 2>/dev/null || \
		docker-compose exec postgres psql -U $${DB_USER:-soc_copilot} -d $${DB_NAME:-soc_copilot} 2>/dev/null || \
		psql -U $${DB_USER:-soc_copilot} -d $${DB_NAME:-soc_copilot} -h localhost

redis-cli:
	@echo "🔴 Opening Redis CLI..."
	docker compose exec redis redis-cli -a "$${REDIS_PASSWORD}" 2>/dev/null || \
		docker-compose exec redis redis-cli -a "$${REDIS_PASSWORD}" 2>/dev/null || \
		redis-cli -a "$${REDIS_PASSWORD}"

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

# Docker Development (Frontend with Volume Mount & HMR)
docker-dev-up:
	@echo "🐳 Starting frontend development container with hot reload..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d frontend

docker-dev-down:
	@echo "🐳 Stopping frontend development container..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

docker-dev-logs:
	@echo "📋 Showing frontend development logs..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend

docker-dev-build:
	@echo "🏗️  Rebuilding frontend development image..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend

# Production
prod-build:
	@echo "🏗️  Building for production..."
	npm run build

prod-start:
	@echo "🚀 Starting production servers..."
	cd frontend && npm run start

# Branch Management (FR-001)
branch-setup:
	@echo "🔒 Setting up GitHub branch protection rules..."
	./scripts/setup-branch-protection.sh

branch-setup-dry-run:
	@echo "🔍 Dry-run: Previewing branch protection rules..."
	./scripts/setup-branch-protection.sh --dry-run

branch-validate:
	@echo "✅ Validating branch name..."
	./scripts/validate-branch-name.sh

branch-list:
	@echo "📋 Branch listing:"
	@echo ""
	@echo "  Permanent branches:"
	@git branch -a | grep -E '(main|develop)' || echo "    (none found)"
	@echo ""
	@echo "  Feature branches:"
	@git branch -a | grep 'feature/' || echo "    (none)"
	@echo ""
	@echo "  Fix branches:"
	@git branch -a | grep 'fix/' || echo "    (none)"
	@echo ""
	@echo "  Release branches:"
	@git branch -a | grep 'release/' || echo "    (none)"
	@echo ""
	@echo "  Hotfix branches:"
	@git branch -a | grep 'hotfix/' || echo "    (none)"

branch-create-feature:
	@if [ -z "$(FR)" ] || [ -z "$(DESC)" ]; then \
		echo "❌ Usage: make branch-create-feature FR=xxx DESC=short-description"; \
		echo "   Example: make branch-create-feature FR=001 DESC=alert-dedup"; \
		exit 1; \
	fi
	@echo "🌿 Creating feature branch: feature/FR-$(FR)-$(DESC)"
	git checkout develop && git pull origin develop
	git checkout -b feature/FR-$(FR)-$(DESC)

branch-create-fix:
	@if [ -z "$(FR)" ] || [ -z "$(DESC)" ]; then \
		echo "❌ Usage: make branch-create-fix FR=xxx DESC=short-description"; \
		echo "   Example: make branch-create-fix FR=002 DESC=login-timeout"; \
		exit 1; \
	fi
	@echo "🔧 Creating fix branch: fix/FR-$(FR)-$(DESC)"
	git checkout develop && git pull origin develop
	git checkout -b fix/FR-$(FR)-$(DESC)

branch-create-release:
	@if [ -z "$(VER)" ]; then \
		echo "❌ Usage: make branch-create-release VER=x.y.z"; \
		echo "   Example: make branch-create-release VER=0.10.0"; \
		exit 1; \
	fi
	@echo "📦 Creating release branch: release/v$(VER)"
	git checkout develop && git pull origin develop
	git checkout -b release/v$(VER)

branch-create-hotfix:
	@if [ -z "$(VER)" ] || [ -z "$(DESC)" ]; then \
		echo "❌ Usage: make branch-create-hotfix VER=x.y.z DESC=short-description"; \
		echo "   Example: make branch-create-hotfix VER=0.10.1 DESC=xss-fix"; \
		exit 1; \
	fi
	@echo "🚨 Creating hotfix branch: hotfix/v$(VER)-$(DESC)"
	git checkout main && git pull origin main
	git checkout -b hotfix/v$(VER)-$(DESC)

branch-cleanup:
	@echo "🧹 Cleaning up merged branches..."
	@echo "  Local merged branches:"
	@git branch --merged develop | grep -E 'feature/|fix/|release/|hotfix/' | xargs git branch -d 2>/dev/null || echo "    (no branches to clean)"
	@echo "  Done!"

# Release Management (FR-003)

# 步骤1: 版本规划 - 显示当前版本和变更摘要
release-plan:
	@if [ -z "$(VER)" ]; then \
		echo "❌ Usage: make release-plan VER=x.y.z"; \
		echo "   Example: make release-plan VER=0.10.0"; \
		exit 1; \
	fi
	@echo "📋 Release Planning: v$(VER)"
	@echo ""
	@echo "  Current version:"
	@grep '^version = ' backend/pyproject.toml | head -1 | sed 's/^/    /'
	@echo ""
	@echo "  Target version: v$(VER)"
	@echo ""
	@echo "  Commits since last release:"
	@git log $$(git tag --sort=-version:refname | grep -E '^v[0-9]' | head -1)..HEAD --oneline 2>/dev/null | head -20 || echo "    (unable to determine)"
	@echo ""
	@echo "  Next steps:"
	@echo "    1. make release-start VER=$(VER)"
	@echo "    2. Review and test on release branch"
	@echo "    3. Create PR: release/v$(VER) → main"
	@echo "    4. After merge: make release-finish VER=$(VER)"

# 步骤4: 创建 release 分支（含版本号更新 + CHANGELOG 生成）
release-start:
	@if [ -z "$(VER)" ]; then \
		echo "❌ Usage: make release-start VER=x.y.z"; \
		echo "   Example: make release-start VER=0.10.0"; \
		exit 1; \
	fi
	@echo "🚀 Starting release v$(VER)..."
	@chmod +x scripts/release-branch.sh scripts/bump-version.sh scripts/generate-changelog.sh
	@./scripts/release-branch.sh start $(VER)

# 步骤2: 生成 CHANGELOG
release-changelog:
	@if [ -z "$(VER)" ]; then \
		echo "❌ Usage: make release-changelog VER=x.y.z"; \
		echo "   Example: make release-changelog VER=0.10.0"; \
		exit 1; \
	fi
	@echo "📝 Generating CHANGELOG for v$(VER)..."
	@chmod +x scripts/generate-changelog.sh
	@./scripts/generate-changelog.sh $(VER)

# 版本号更新（仅更新版本号，不创建分支）
release-bump:
	@if [ -z "$(VER)" ]; then \
		echo "❌ Usage: make release-bump VER=x.y.z"; \
		echo "   Example: make release-bump VER=0.10.0"; \
		exit 1; \
	fi
	@echo "🔢 Bumping version to v$(VER)..."
	@chmod +x scripts/bump-version.sh
	@./scripts/bump-version.sh $(VER)

# 步骤8: 完成 release（合并回 develop + 清理分支）
release-finish:
	@if [ -z "$(VER)" ]; then \
		echo "❌ Usage: make release-finish VER=x.y.z"; \
		echo "   Example: make release-finish VER=0.10.0"; \
		exit 1; \
	fi
	@echo "🏁 Finishing release v$(VER)..."
	@chmod +x scripts/release-branch.sh
	@./scripts/release-branch.sh finish $(VER)

# 查看 release 状态
release-status:
	@echo "📊 Release Status"
	@chmod +x scripts/release-branch.sh
	@./scripts/release-branch.sh status

# 列出所有 release 分支
release-list:
	@echo "📋 Release Branches"
	@chmod +x scripts/release-branch.sh
	@./scripts/release-branch.sh list

# 中止发布
release-abort:
	@if [ -z "$(VER)" ]; then \
		echo "❌ Usage: make release-abort VER=x.y.z"; \
		echo "   Example: make release-abort VER=0.10.0"; \
		exit 1; \
	fi
	@echo "🚨 Aborting release v$(VER)..."
	@chmod +x scripts/release-branch.sh
	@./scripts/release-branch.sh abort $(VER)
