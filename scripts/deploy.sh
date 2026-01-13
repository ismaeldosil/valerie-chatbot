#!/bin/bash
# Valerie Supplier Chatbot - Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environments: dev, staging, production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
ENVIRONMENT=${1:-dev}
PROJECT_NAME="valerie-supplier-chatbot"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io/valerie}"

log_info "Deploying ${PROJECT_NAME} to ${ENVIRONMENT}..."

# Validate environment
case $ENVIRONMENT in
    dev|development)
        COMPOSE_FILE="docker-compose.dev.yml"
        log_info "Using development configuration"
        ;;
    staging)
        COMPOSE_FILE="docker-compose.yml"
        log_info "Using staging configuration"
        ;;
    production|prod)
        COMPOSE_FILE="docker-compose.yml"
        log_warning "Deploying to PRODUCTION!"
        read -p "Are you sure? (yes/no): " confirm
        if [[ $confirm != "yes" ]]; then
            log_error "Deployment cancelled"
            exit 1
        fi
        ;;
    *)
        log_error "Unknown environment: $ENVIRONMENT"
        echo "Usage: $0 [dev|staging|production]"
        exit 1
        ;;
esac

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose is not installed"
    exit 1
fi

# Check for required environment variables in production
if [[ $ENVIRONMENT == "production" || $ENVIRONMENT == "prod" ]]; then
    if [[ -z "$VALERIE_ANTHROPIC_API_KEY" ]]; then
        log_error "VALERIE_ANTHROPIC_API_KEY is required for production deployment"
        exit 1
    fi
fi

# Build images
log_info "Building Docker images..."
docker compose -f $COMPOSE_FILE build --no-cache

# Run tests (skip in production for faster deployment)
if [[ $ENVIRONMENT != "production" && $ENVIRONMENT != "prod" ]]; then
    log_info "Running tests..."
    docker compose -f $COMPOSE_FILE run --rm api pytest tests/ -v || {
        log_error "Tests failed!"
        exit 1
    }
fi

# Stop existing containers
log_info "Stopping existing containers..."
docker compose -f $COMPOSE_FILE down --remove-orphans || true

# Start new containers
log_info "Starting containers..."
docker compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 10

# Health check
log_info "Running health checks..."

API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [[ $API_HEALTH == "200" ]]; then
    log_success "API is healthy"
else
    log_error "API health check failed (HTTP $API_HEALTH)"
    docker compose -f $COMPOSE_FILE logs api
    exit 1
fi

# Show status
log_info "Deployment complete! Service status:"
docker compose -f $COMPOSE_FILE ps

# Print access information
echo ""
log_success "Deployment successful!"
echo ""
echo "Access points:"
echo "  - API:      http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Demo UI:  http://localhost:8501"
echo "  - Health:   http://localhost:8000/health"
echo ""

# Show logs command
echo "View logs: docker compose -f $COMPOSE_FILE logs -f"
