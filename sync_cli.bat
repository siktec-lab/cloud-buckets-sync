@echo off
REM S3 Sync Service CLI Wrapper for Windows
REM This script provides an easy way to interact with the sync service running in Docker

setlocal enabledelayedexpansion

REM Function to print colored output (basic version for Windows)
set "INFO_PREFIX=[INFO]"
set "SUCCESS_PREFIX=[SUCCESS]"
set "WARNING_PREFIX=[WARNING]"
set "ERROR_PREFIX=[ERROR]"

REM Function to check if Docker Compose services are running
:check_services
echo %INFO_PREFIX% Checking Docker Compose services...

docker-compose ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo %ERROR_PREFIX% Docker Compose services are not running
    echo %INFO_PREFIX% Starting services with: docker-compose up -d
    docker-compose up -d
    
    echo %INFO_PREFIX% Waiting for services to be ready...
    timeout /t 10 /nobreak >nul
) else (
    echo %SUCCESS_PREFIX% Docker Compose services are running
)
exit /b 0

REM Function to run sync service commands
:run_sync_command
set "command=%~1"
echo %INFO_PREFIX% Running sync service command: %command%

docker-compose exec sync-service python -m sync_service.main "%command%"
if errorlevel 1 (
    echo %ERROR_PREFIX% Command '%command%' failed
    exit /b 1
) else (
    echo %SUCCESS_PREFIX% Command '%command%' completed successfully
)
goto :eof

REM Function to show service logs
:show_logs
set "service=%~1"
if "%service%"=="" set "service=sync-service"
echo %INFO_PREFIX% Showing logs for service: %service%
docker-compose logs -f "%service%"
goto :eof

REM Function to show help
:show_help
echo S3 Sync Service CLI Wrapper for Windows
echo.
echo USAGE:
echo     sync_cli.bat [COMMAND] [OPTIONS]
echo.
echo COMMANDS:
echo     start             Start all Docker Compose services
echo     stop              Stop all Docker Compose services
echo     restart           Restart all Docker Compose services
echo     status            Show service status and statistics
echo     initial-sync      Run initial synchronization
echo     incremental-sync  Run incremental synchronization
echo     test              Run end-to-end test workflow
echo     logs [service]    Show logs (default: sync-service)
echo     shell             Open shell in sync-service container
echo     help              Show this help message
echo.
echo EXAMPLES:
echo     # Start all services
echo     sync_cli.bat start
echo.
echo     # Check service status
echo     sync_cli.bat status
echo.
echo     # Run initial sync
echo     sync_cli.bat initial-sync
echo.
echo     # Run incremental sync
echo     sync_cli.bat incremental-sync
echo.
echo     # Test end-to-end workflow
echo     sync_cli.bat test
echo.
echo     # Show sync service logs
echo     sync_cli.bat logs
echo.
echo     # Show mock API logs
echo     sync_cli.bat logs mock-api
echo.
echo     # Open shell in sync service container
echo     sync_cli.bat shell
echo.
echo SERVICES:
echo     sync-service      Main S3 sync service
echo     minio-customer    Customer S3 service (MinIO)
echo     minio-target      Target S3 service (MinIO)
echo     mock-api          Mock API server
echo.
goto :eof

REM Main command handling
set "cmd=%~1"
if "%cmd%"=="" set "cmd=help"

if /i "%cmd%"=="start" (
    echo %INFO_PREFIX% Starting Docker Compose services...
    docker-compose up -d
    if errorlevel 1 (
        echo %ERROR_PREFIX% Failed to start services
        exit /b 1
    )
    echo %SUCCESS_PREFIX% Services started successfully
    
) else if /i "%cmd%"=="stop" (
    echo %INFO_PREFIX% Stopping Docker Compose services...
    docker-compose down
    if errorlevel 1 (
        echo %ERROR_PREFIX% Failed to stop services
        exit /b 1
    )
    echo %SUCCESS_PREFIX% Services stopped successfully
    
) else if /i "%cmd%"=="restart" (
    echo %INFO_PREFIX% Restarting Docker Compose services...
    docker-compose restart
    if errorlevel 1 (
        echo %ERROR_PREFIX% Failed to restart services
        exit /b 1
    )
    echo %SUCCESS_PREFIX% Services restarted successfully
    
) else if /i "%cmd%"=="status" (
    call :check_services
    if errorlevel 1 exit /b 1
    call :run_sync_command "status"
    
) else if /i "%cmd%"=="initial-sync" (
    call :check_services
    call :run_sync_command "initial-sync"
    
) else if /i "%cmd%"=="incremental-sync" (
    call :check_services
    call :run_sync_command "incremental-sync"
    
) else if /i "%cmd%"=="test" (
    call :check_services
    call :run_sync_command "test"
    
) else if /i "%cmd%"=="logs" (
    call :show_logs "%~2"
    
) else if /i "%cmd%"=="shell" (
    call :check_services
    echo %INFO_PREFIX% Opening shell in sync-service container...
    docker-compose exec sync-service /bin/bash
    
) else if /i "%cmd%"=="help" (
    call :show_help
    
) else if /i "%cmd%"=="--help" (
    call :show_help
    
) else if /i "%cmd%"=="-h" (
    call :show_help
    
) else (
    echo %ERROR_PREFIX% Unknown command: %cmd%
    call :show_help
    exit /b 1
)