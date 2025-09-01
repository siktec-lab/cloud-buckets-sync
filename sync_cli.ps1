# S3 Sync Service CLI Wrapper for PowerShell
# This script provides an easy way to interact with the sync service running in Docker

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Service = "sync-service"
)

# Function to print colored output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check if Docker Compose services are running
function Test-Services {
    Write-Info "Checking Docker Compose services..."
    
    try {
        $services = docker-compose ps --format json | ConvertFrom-Json
        $runningServices = $services | Where-Object { $_.State -eq "running" }
        
        if ($runningServices.Count -eq 0) {
            Write-Error "Docker Compose services are not running"
            Write-Info "Starting services with: docker-compose up -d"
            docker-compose up -d
            
            Write-Info "Waiting for services to be ready..."
            Start-Sleep -Seconds 10
        } else {
            Write-Success "Docker Compose services are running"
        }
        return $true
    } catch {
        Write-Error "Failed to check Docker Compose services: $_"
        return $false
    }
}

# Function to run sync service commands
function Invoke-SyncCommand {
    param([string]$SyncCommand)
    
    Write-Info "Running sync service command: $SyncCommand"
    
    try {
        $result = docker-compose exec sync-service python -m sync_service.main $SyncCommand
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Command '$SyncCommand' completed successfully"
        } else {
            Write-Error "Command '$SyncCommand' failed with exit code $LASTEXITCODE"
            return $false
        }
        return $true
    } catch {
        Write-Error "Failed to execute command '$SyncCommand': $_"
        return $false
    }
}

# Function to show service logs
function Show-Logs {
    param([string]$ServiceName = "sync-service")
    
    Write-Info "Showing logs for service: $ServiceName"
    docker-compose logs -f $ServiceName
}

# Function to show help
function Show-Help {
    Write-Host @"
S3 Sync Service CLI Wrapper for PowerShell

USAGE:
    .\sync_cli.ps1 [COMMAND] [OPTIONS]

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
    .\sync_cli.ps1 start
    
    # Check service status
    .\sync_cli.ps1 status
    
    # Run initial sync
    .\sync_cli.ps1 initial-sync
    
    # Run incremental sync
    .\sync_cli.ps1 incremental-sync
    
    # Test end-to-end workflow
    .\sync_cli.ps1 test
    
    # Show sync service logs
    .\sync_cli.ps1 logs
    
    # Show mock API logs
    .\sync_cli.ps1 logs mock-api
    
    # Open shell in sync service container
    .\sync_cli.ps1 shell

SERVICES:
    sync-service      Main S3 sync service
    minio-customer    Customer S3 service (MinIO)
    minio-target      Target S3 service (MinIO)
    mock-api          Mock API server

"@
}

# Main command handling
switch ($Command.ToLower()) {
    "start" {
        Write-Info "Starting Docker Compose services..."
        docker-compose up -d
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Services started successfully"
        } else {
            Write-Error "Failed to start services"
            exit 1
        }
    }
    
    "stop" {
        Write-Info "Stopping Docker Compose services..."
        docker-compose down
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Services stopped successfully"
        } else {
            Write-Error "Failed to stop services"
            exit 1
        }
    }
    
    "restart" {
        Write-Info "Restarting Docker Compose services..."
        docker-compose restart
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Services restarted successfully"
        } else {
            Write-Error "Failed to restart services"
            exit 1
        }
    }
    
    "status" {
        if (Test-Services) {
            Invoke-SyncCommand "status"
        }
    }
    
    "initial-sync" {
        if (Test-Services) {
            Invoke-SyncCommand "initial-sync"
        }
    }
    
    "incremental-sync" {
        if (Test-Services) {
            Invoke-SyncCommand "incremental-sync"
        }
    }
    
    "test" {
        if (Test-Services) {
            Invoke-SyncCommand "test"
        }
    }
    
    "logs" {
        Show-Logs $Service
    }
    
    "shell" {
        if (Test-Services) {
            Write-Info "Opening shell in sync-service container..."
            docker-compose exec sync-service /bin/bash
        }
    }
    
    { $_ -in @("help", "--help", "-h") } {
        Show-Help
    }
    
    default {
        Write-Error "Unknown command: $Command"
        Show-Help
        exit 1
    }
}