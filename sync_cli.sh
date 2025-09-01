#!/bin/bash

# S3 Sync Service CLI Wrapper
# This script provides an easy way to interact with the sync service running in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker Compose services are running
check_services() {
    print_info "Checking Docker Compose services..."
    
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Docker Compose services are not running"
        print_info "Starting services with: docker-compose up -d"
        docker-compose up -d
        
        print_info "Waiting for services to be ready..."
        sleep 10
    else
        print_success "Docker Compose services are running"
    fi
}

# Function to run sync service commands
run_sync_command() {
    local command=$1
    print_info "Running sync service command: $command"
    
    if docker-compose exec sync-service python -m sync_service.main "$command"; then
        print_success "Command '$command' completed successfully"
    else
        print_error "Command '$command' failed"
        exit 1
    fi
}

# Function to show service logs
show_logs() {
    local service=${1:-sync-service}
    print_info "Showing logs for service: $service"
    docker-compose logs -f "$service"
}

# Function to show help
show_help() {
    cat << EOF
S3 Sync Service CLI Wrapper

USAGE:
    ./sync_cli.sh [COMMAND] [OPTIONS]

COMMANDS:
    start             Start all Docker Compose services
    stop              Stop all Docker Compose services
    restart           Restart all Docker Compose services
    status            Show service status and statistics
    initial-sync      Run initial synchronization
    incremental-sync  Run incremental synchronization
    test              Run end-to-end test workflow
    logs [service]    Show logs (default: sync-service)
    shell             Open shell in sync-service container
    help              Show this help message

EXAMPLES:
    # Start all services
    ./sync_cli.sh start
    
    # Check service status
    ./sync_cli.sh status
    
    # Run initial sync
    ./sync_cli.sh initial-sync
    
    # Run incremental sync
    ./sync_cli.sh incremental-sync
    
    # Test end-to-end workflow
    ./sync_cli.sh test
    
    # Show sync service logs
    ./sync_cli.sh logs
    
    # Show mock API logs
    ./sync_cli.sh logs mock-api
    
    # Open shell in sync service container
    ./sync_cli.sh shell

SERVICES:
    sync-service      Main S3 sync service
    minio-customer    Customer S3 service (MinIO)
    minio-target      Target S3 service (MinIO)
    mock-api          Mock API server

EOF
}

# Main command handling
case "${1:-help}" in
    start)
        print_info "Starting Docker Compose services..."
        docker-compose up -d
        print_success "Services started successfully"
        ;;
    
    stop)
        print_info "Stopping Docker Compose services..."
        docker-compose down
        print_success "Services stopped successfully"
        ;;
    
    restart)
        print_info "Restarting Docker Compose services..."
        docker-compose restart
        print_success "Services restarted successfully"
        ;;
    
    status)
        check_services
        run_sync_command "status"
        ;;
    
    initial-sync)
        check_services
        run_sync_command "initial-sync"
        ;;
    
    incremental-sync)
        check_services
        run_sync_command "incremental-sync"
        ;;
    
    test)
        check_services
        run_sync_command "test"
        ;;
    
    logs)
        service=${2:-sync-service}
        show_logs "$service"
        ;;
    
    shell)
        check_services
        print_info "Opening shell in sync-service container..."
        docker-compose exec sync-service /bin/bash
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac