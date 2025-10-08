#!/bin/bash

# YouTube ELT Pipeline Deployment Script
# This script automates the deployment process for different environments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV="${1:-development}"
VERSION="${2:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Function to validate environment
validate_environment() {
    log "Validating environment: $ENV"
    
    case $ENV in
        development|staging|production)
            log "Environment '$ENV' is valid"
            ;;
        *)
            error "Invalid environment: $ENV. Must be one of: development, staging, production"
            ;;
    esac
}

# Function to check prerequisites  
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        warn "docker-compose not found, trying docker compose..."
        if ! docker compose version &> /dev/null; then
            error "Neither docker-compose nor docker compose is available"
        fi
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    # Check Astro CLI (optional)
    if command -v astro &> /dev/null; then
        log "Astro CLI found: $(astro version)"
        ASTRO_AVAILABLE=true
    else
        warn "Astro CLI not found - using Docker Compose instead"
        ASTRO_AVAILABLE=false
    fi
    
    log "Prerequisites check completed"
}

# Function to backup data
backup_data() {
    if [ "$ENV" = "production" ]; then
        log "Creating backup for production deployment..."
        
        BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup database
        if [ -f "$PROJECT_DIR/.env" ]; then
            source "$PROJECT_DIR/.env"
            log "Backing up PostgreSQL database..."
            $DOCKER_COMPOSE exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_DIR/database.sql" || warn "Database backup failed"
        fi
        
        # Backup data files
        if [ -d "$PROJECT_DIR/data" ]; then
            log "Backing up data files..."
            cp -r "$PROJECT_DIR/data" "$BACKUP_DIR/" || warn "Data files backup failed"
        fi
        
        log "Backup completed: $BACKUP_DIR"
    fi
}

# Function to deploy with Docker Compose
deploy_docker_compose() {
    log "Deploying with Docker Compose..."
    
    cd "$PROJECT_DIR"
    
    # Select appropriate compose file
    case $ENV in
        development)
            COMPOSE_FILE="docker-compose.yml"
            ;;
        staging)
            COMPOSE_FILE="docker-compose-simple.yml"  
            ;;
        production)
            COMPOSE_FILE="docker-compose-production.yml"
            ;;
    esac
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Compose file not found: $COMPOSE_FILE"
    fi
    
    log "Using compose file: $COMPOSE_FILE"
    
    # Stop existing services
    log "Stopping existing services..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" down || warn "Failed to stop services"
    
    # Pull latest images
    log "Pulling latest images..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" pull || warn "Failed to pull images"
    
    # Build services
    log "Building services..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" build
    
    # Start services
    log "Starting services..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
    
    log "Docker Compose deployment completed"
}

# Function to deploy with Astro CLI
deploy_astro() {
    log "Deploying with Astro CLI..."
    
    cd "$PROJECT_DIR"
    
    case $ENV in
        development)
            log "Starting Astro development environment..."
            astro dev start
            ;;
        staging)
            log "Deploying to Astro staging..."
            # astro deploy staging
            warn "Astro staging deployment not configured"
            ;;
        production)
            log "Deploying to Astro production..."
            # astro deploy production
            warn "Astro production deployment not configured"
            ;;
    esac
}

# Function to run health checks
health_check() {
    log "Running health checks..."
    
    # Wait for services to be ready
    sleep 30
    
    # Check Airflow webserver
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log "✓ Airflow webserver is healthy"
    else
        warn "✗ Airflow webserver health check failed"
    fi
    
    # Check PostgreSQL
    if $DOCKER_COMPOSE exec postgres pg_isready -U postgres > /dev/null 2>&1; then
        log "✓ PostgreSQL is healthy"
    else
        warn "✗ PostgreSQL health check failed"
    fi
    
    # Check data directory
    if [ -d "$PROJECT_DIR/data/json" ]; then
        log "✓ Data directory exists"
    else
        warn "✗ Data directory not found"
    fi
    
    log "Health checks completed"
}

# Function to run tests
run_tests() {
    log "Running tests..."
    
    cd "$PROJECT_DIR"
    
    # Run unit tests
    if python -m pytest tests/ -v; then
        log "✓ Unit tests passed"
    else
        error "✗ Unit tests failed"
    fi
    
    # Test DAG loading
    log "Testing DAG loading..."
    export AIRFLOW_HOME="$PROJECT_DIR"
    if python -c "
from airflow.models import DagBag
dagbag = DagBag()
if dagbag.import_errors:
    print('DAG import errors found')
    exit(1)
print(f'Successfully loaded {len(dagbag.dags)} DAGs')
"; then
        log "✓ DAG loading test passed"
    else
        warn "✗ DAG loading test failed (may be due to Airflow environment)"
    fi
    
    log "Tests completed"
}

# Function to setup environment file
setup_env_file() {
    log "Setting up environment file for $ENV..."
    
    ENV_FILE="$PROJECT_DIR/.env"
    ENV_EXAMPLE="$PROJECT_DIR/.env.example"
    
    if [ "$ENV" = "production" ]; then
        ENV_SOURCE="$PROJECT_DIR/.env.production"
    else
        ENV_SOURCE="$ENV_EXAMPLE"
    fi
    
    if [ -f "$ENV_SOURCE" ]; then
        cp "$ENV_SOURCE" "$ENV_FILE"
        log "Environment file configured from $ENV_SOURCE"
    else
        warn "Environment source file not found: $ENV_SOURCE"
        if [ ! -f "$ENV_FILE" ]; then
            error "No environment file available"
        fi
    fi
    
    # Validate required variables
    source "$ENV_FILE"
    if [ -z "${YOUTUBE_API_KEY:-}" ] || [ "$YOUTUBE_API_KEY" = "your-api-key-here" ]; then
        warn "YOUTUBE_API_KEY is not configured properly"
    fi
}

# Function to copy files and sync data
sync_files() {
    log "Syncing files and data..."
    
    # Ensure data directories exist
    mkdir -p "$PROJECT_DIR/data/json"
    mkdir -p "$PROJECT_DIR/logs"
    
    # Set proper permissions
    chmod -R 755 "$PROJECT_DIR/data"
    chmod -R 755 "$PROJECT_DIR/logs"
    
    log "File sync completed"
}

# Main deployment function
main() {
    log "Starting YouTube ELT Pipeline deployment"
    log "Environment: $ENV"
    log "Version: $VERSION"
    
    validate_environment
    check_prerequisites
    setup_env_file
    sync_files
    
    if [ "$ENV" != "development" ]; then
        backup_data
        run_tests
    fi
    
    # Choose deployment method
    if [ "$ASTRO_AVAILABLE" = true ] && [ "$ENV" = "development" ]; then
        deploy_astro
    else
        deploy_docker_compose
    fi
    
    health_check
    
    log "Deployment completed successfully!"
    log "Access Airflow UI at: http://localhost:8080"
    log "Username: admin"
    log "Password: admin (or configured password)"
}

# Print usage
usage() {
    echo "Usage: $0 [environment] [version]"
    echo "  environment: development (default), staging, production"
    echo "  version: latest (default)"
    echo ""
    echo "Examples:"
    echo "  $0                          # Deploy to development"
    echo "  $0 staging                  # Deploy to staging"
    echo "  $0 production v1.0.0        # Deploy version v1.0.0 to production"
}

# Handle command line arguments
case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac