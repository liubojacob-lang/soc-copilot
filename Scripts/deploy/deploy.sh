#!/bin/bash
# SOC Copilot Deployment Script
# Usage: ./deploy.sh [environment]
# Environments: local, staging, production

set -e

ENV=${1:-local}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 SOC Copilot Deployment Script"
echo "================================"
echo "Environment: $ENV"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Compose v2 ships as a docker plugin (`docker compose`)
    if docker compose version &> /dev/null; then
        print_status "Docker and Docker Compose are installed"
    elif command -v docker-compose &> /dev/null; then
        print_warning "Legacy docker-compose detected; compose v2 is recommended."
    else
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Load environment variables
load_env() {
    if [ -f ".env.$ENV" ]; then
        print_status "Loading environment from .env.$ENV"
        export $(cat .env.$ENV | grep -v '^#' | xargs)
    elif [ -f ".env" ]; then
        print_status "Loading environment from .env"
        export $(cat .env | grep -v '^#' | xargs)
    else
        print_warning "No .env file found. Using default values."
    fi
}

# Deploy for local development
deploy_local() {
    print_status "Deploying for local development..."
    
    # Build and start services
    docker-compose up --build -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Run database migrations
    print_status "Running database migrations..."
    docker-compose exec -T backend alembic upgrade head || true
    
    print_status "Local deployment complete!"
    print_status "Frontend: http://localhost:3000"
    print_status "Backend API: http://localhost:8000"
    print_status "API Docs: http://localhost:8000/docs"
}

# Deploy for staging
deploy_staging() {
    print_status "Deploying to staging..."
    
    # Pull latest images
    docker compose -f docker-compose.prod.yml pull
    
    # Start services
    docker compose -f docker-compose.prod.yml up -d
    
    # Run migrations
    docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
    
    print_status "Staging deployment complete!"
}

# Deploy for production
deploy_production() {
    print_status "Deploying to production..."
    print_warning "This will deploy to PRODUCTION environment!"
    
    # Confirm deployment
    read -p "Are you sure you want to deploy to production? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        print_status "Deployment cancelled"
        exit 0
    fi
    
    # Create backup
    print_status "Creating database backup..."
    docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U "${DB_USER:-soc_copilot}" "${DB_NAME:-soc_copilot}" > "backups/backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # Deploy
    docker compose -f docker-compose.prod.yml pull
    docker compose -f docker-compose.prod.yml up -d
    
    # Run migrations
    docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
    
    # Health check
    print_status "Running health checks..."
    sleep 5
    
    if curl -f http://localhost/api/health > /dev/null 2>&1; then
        print_status "✓ Health check passed"
    else
        print_error "✗ Health check failed"
        exit 1
    fi
    
    print_status "Production deployment complete!"
}

# Main deployment logic
main() {
    # Run from the repository root: every compose path below is relative to it.
    cd "$SCRIPT_DIR/../.."

    check_docker
    load_env
    
    case $ENV in
        local)
            deploy_local
            ;;
        staging)
            deploy_staging
            ;;
        production)
            deploy_production
            ;;
        *)
            print_error "Unknown environment: $ENV"
            print_status "Usage: ./deploy.sh [local|staging|production]"
            exit 1
            ;;
    esac
    
    echo ""
    print_status "Deployment completed successfully! 🎉"
}

# Run main function
main
