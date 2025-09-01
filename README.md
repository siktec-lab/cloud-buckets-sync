# S3 Sync Service

A production-ready Python service that synchronizes files between S3-compatible storage and file management systems. The service maintains state tracking through SQLite and supports both initial full synchronization and incremental event-based updates.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Setup and Start
```bash
# Clone the repository
git clone <repository-url>
cd s3-sync-service

# Build and start all services
make setup
# OR
docker-compose up -d
```

### 2. First Time Setup (Initial Sync)
```bash
# Run initial synchronization (scans entire S3 bucket)
make initial-sync
# OR
docker-compose exec sync-service python -m sync_service.main initial-sync
```

### 3. Check Status
```bash
# Check service status and statistics
make status
# OR
docker-compose exec sync-service python -m sync_service.main status
```

### 4. Test Everything Works
```bash
# Run end-to-end test workflow
make test-workflow
# OR
docker-compose exec sync-service python -m sync_service.main test
```

## 📋 Architecture

### Core Components
- **SyncService**: Main orchestration and workflow management
- **S3Manager**: Customer S3 bucket operations with retry logic
- **DatabaseManager**: SQLite operations and schema management
- **InfrastructureAPI**: Communication with file manager endpoints
- **CSVProcessor**: State export, import, and diff operations
- **EventProcessor**: Pub/sub event replay and processing

### Services
- **sync-service**: Main Python application with live code reloading
- **minio-customer**: Customer S3 service (MinIO) with test data
- **minio-target**: Target S3 service (MinIO) for backup storage
- **mock-api**: FastAPI server with mock endpoints for testing

### Sync Workflows

#### Initial Sync (First Time Setup)
1. **Bucket Scanning**: Scan entire customer S3 bucket
2. **File Processing**: For each file:
   - Retrieve file metadata and stream
   - Call `updatePermissions` endpoint
   - Call `saveToDisk` endpoint with file stream
   - Store file record in SQLite database
3. **State Export**: Export final state to CSV

#### Incremental Sync (Periodic Updates)
1. **State Export**: Export current SQLite state to CSV (old state)
2. **Event Replay**: Process pub/sub events:
   - Handle change_permission, delete, create, rename, move operations
   - Update SQLite database based on events
3. **State Comparison**: Export updated state to CSV (new state)
4. **Diff Processing**: Compare old and new CSV files
5. **Change Application**: Execute operations based on differences
6. **Result Reporting**: Report sync results to configured endpoints

#### Daemon Mode (Production)
- Runs initial sync if no database records exist
- Performs incremental sync at configured intervals (default: 5 minutes)
- Handles errors gracefully and continues operation

## 🛠️ Usage

### Make Commands (Recommended)
```bash
# Setup and management
make setup           # Build and start all services
make up              # Start services
make down            # Stop services
make clean           # Clean up containers and volumes

# Sync operations
make initial-sync    # Run initial synchronization (first time)
make incremental-sync # Run incremental synchronization
make daemon          # Run in daemon mode (periodic sync)
make status          # Show service status
make test-workflow   # Run end-to-end test

# Development
make logs            # Show all service logs
make logs-sync       # Show sync service logs only
make shell           # Open shell in sync container
make test            # Run unit tests
```

### Direct Commands
```bash
# Sync operations
docker-compose exec sync-service python -m sync_service.main initial-sync
docker-compose exec sync-service python -m sync_service.main incremental-sync
docker-compose exec sync-service python -m sync_service.main daemon
docker-compose exec sync-service python -m sync_service.main status
docker-compose exec sync-service python -m sync_service.main test
docker-compose exec sync-service python -m sync_service.main help

# Service management
docker-compose up -d
docker-compose down
docker-compose logs -f sync-service
```

### CLI Wrapper Scripts
Cross-platform wrapper scripts are available:

**Windows PowerShell:**
```powershell
.\sync_cli.ps1 status
.\sync_cli.ps1 initial-sync
.\sync_cli.ps1 test
```

**Linux/macOS:**
```bash
./sync_cli.sh status
./sync_cli.sh initial-sync
./sync_cli.sh test
```

## ⚙️ Configuration

### Environment Variables
Configuration is managed through environment variables in `docker-compose.yml`:

```yaml
# Customer S3 Configuration
CUSTOMER_S3_ENDPOINT=http://minio-customer:9000
CUSTOMER_S3_ACCESS_KEY=minioadmin
CUSTOMER_S3_SECRET_KEY=minioadmin
CUSTOMER_S3_BUCKET=customer-bucket

# API Endpoints
MOCK_API_URL=http://mock-api:8001
FILE_MANAGER_API_URL=http://localhost:8000

# Service Configuration
SYNC_INTERVAL=300                    # Sync interval in seconds (5 minutes)
DATABASE_PATH=/app/data/sync.db      # SQLite database path
LIVE_RELOAD=true                     # Enable live code reloading
```

### Service Ports
- **MinIO Customer**: `9001` (API), `9011` (Console)
- **MinIO Target**: `9002` (API), `9012` (Console)
- **Mock API**: `8001`

Access MinIO consoles:
- Customer: http://localhost:9011 (minioadmin/minioadmin)
- Target: http://localhost:9012 (minioadmin/minioadmin)

## 🏗️ Project Structure

```
s3-sync-service/
├── sync_service/                 # Main Python application
│   ├── clients/                  # S3 and API clients
│   │   ├── s3_manager.py        # S3 operations with retry logic
│   │   └── infrastructure_api.py # API client for file manager
│   ├── models/                   # Data models and configuration
│   │   ├── config.py            # Configuration classes
│   │   └── data_models.py       # FileRecord, FileOperation models
│   ├── services/                 # Core business logic
│   │   ├── sync_service.py      # Main orchestration service
│   │   ├── database_manager.py  # SQLite operations
│   │   ├── csv_processor.py     # CSV export/import/diff
│   │   └── event_processor.py   # Event replay processing
│   ├── utils/                    # Utility functions
│   └── main.py                   # Application entry point
├── mock_api/                     # Mock API server (FastAPI)
├── test-data/                    # Sample test files
├── tests/                        # Comprehensive test suite
├── data/                         # SQLite database and CSV exports
├── logs/                         # Application logs
├── scripts/                      # Initialization scripts
├── docker-compose.yml            # Service orchestration
├── Dockerfile                    # Main service container
├── Dockerfile.mock-api           # Mock API container
├── Makefile                      # Build and run commands
├── requirements.txt              # Python dependencies
├── sync_cli.ps1                  # PowerShell CLI wrapper
├── sync_cli.sh                   # Bash CLI wrapper
└── README.md                     # This file
```

## 🧪 Testing

### End-to-End Test
```bash
# Run comprehensive test workflow
make test-workflow

# This tests:
# 1. Service status and health
# 2. All service connections (S3, API, Database)
# 3. Incremental sync workflow
# 4. CSV export functionality
# 5. Final system state validation
```

### Unit Tests
```bash
# Run all unit tests
make test

# Run specific test files
docker-compose exec sync-service python -m pytest tests/test_sync_service.py -v
```

### Manual Testing
```bash
# Check service logs
make logs-sync

# Check database state
make shell
# Then inside container:
python -c "
from sync_service.services.database_manager import DatabaseManager
db = DatabaseManager('/app/data/sync.db')
print(f'Records: {db.get_record_count()}')
"
```

## 🚀 Deployment

### Production Deployment Flow

1. **Initial Setup**:
   ```bash
   # Deploy services
   docker-compose up -d
   
   # Run initial sync (first time only)
   make initial-sync
   ```

2. **Normal Operation**:
   ```bash
   # Service runs in daemon mode automatically
   # Performs incremental sync every 5 minutes
   # Monitor with:
   make logs-sync
   make status
   ```

3. **Monitoring**:
   ```bash
   # Check service health
   make status
   
   # View recent activity
   make logs-sync
   
   # Check database records
   docker-compose exec sync-service python -c "
   from sync_service.services.database_manager import DatabaseManager
   db = DatabaseManager('/app/data/sync.db')
   print(f'Total records: {db.get_record_count()}')
   "
   ```

### Production Configuration

For production deployment, update the environment variables in `docker-compose.yml`:

```yaml
environment:
  # Update with real S3 credentials
  - CUSTOMER_S3_ENDPOINT=https://your-s3-endpoint.com
  - CUSTOMER_S3_ACCESS_KEY=your-access-key
  - CUSTOMER_S3_SECRET_KEY=your-secret-key
  - CUSTOMER_S3_BUCKET=your-bucket-name
  
  # Update with real API endpoints
  - MOCK_API_URL=https://your-api-endpoint.com
  - FILE_MANAGER_API_URL=https://your-file-manager.com
  
  # Adjust sync interval as needed (seconds)
  - SYNC_INTERVAL=300
  
  # Disable live reload in production
  - LIVE_RELOAD=false
```

## 🔧 Development

### Live Code Reloading
The service supports live code reloading for efficient development:
- Source code is mounted into containers
- Service automatically restarts when Python files change
- No container rebuilds needed for code changes

### Adding Features
1. Modify code in `sync_service/` directory
2. Changes are automatically detected and applied
3. Test with `make test-workflow`
4. Run unit tests with `make test`

### Debugging
```bash
# View detailed logs
make logs-sync

# Open shell for debugging
make shell

# Run specific components
docker-compose exec sync-service python -c "
from sync_service.services.sync_service import SyncService
from sync_service.models.config import SyncConfig
config = SyncConfig.from_env()
service = SyncService(config)
status = service.get_sync_status()
print(status)
"
```

## 📊 Monitoring and Troubleshooting

### Health Checks
```bash
# Service status
make status

# Container status
docker-compose ps

# Service logs
make logs-sync
```

### Common Issues

**Services not starting:**
```bash
# Check Docker status
docker --version
docker-compose --version

# Restart services
make down && make up
```

**Sync failures:**
```bash
# Check logs for errors
make logs-sync

# Test connections
make test-workflow

# Reset database if needed
make clean && make setup
```

**Database issues:**
```bash
# Check database file
ls -la data/

# Export current state
docker-compose exec sync-service python -m sync_service.main status
```

### Performance Monitoring

The service provides detailed metrics:
- **Events processed**: Number of pub/sub events handled
- **Operations executed**: File operations performed
- **Sync duration**: Time taken for each sync cycle
- **Database records**: Total files tracked
- **Error counts**: Failed operations and reasons

Access metrics through:
```bash
make status                    # Current status
make logs-sync                # Detailed operation logs
```

## 🔐 Security Considerations

- **Credentials**: Default MinIO credentials for development only
- **Network**: Services communicate within Docker network
- **Data**: SQLite database and files stored in mounted volumes
- **API**: Mock endpoints for testing only - replace in production
- **Logs**: Sensitive data is not logged

## 📈 Performance Features

- **Incremental Sync**: Only processes changed files
- **Event Replay**: Efficient change detection through pub/sub events
- **CSV Diff**: Fast state comparison using pandas
- **Connection Pooling**: Reused S3 and API connections
- **Retry Logic**: Automatic retry with exponential backoff
- **Streaming**: Large files streamed to avoid memory issues

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes (live reload helps with testing)
4. Run tests: `make test`
5. Run end-to-end test: `make test-workflow`
6. Submit a pull request

## 📄 License

[Add your license information here]

---

**Ready to use!** This is a complete, production-ready S3 synchronization service with comprehensive testing, monitoring, and development tools.