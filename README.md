# S3 Sync Service

A Python service that synchronizes files between S3-compatible storage and file management systems. The service maintains state tracking thrud storage integrations before production deployment.

## Overview

This service synchronizes files between S3-compatible storage and file management systems using two sync modes:
- **Initial Sync**: Full bucket scanning for new integrations
- **Incremental Sync**: Event-based updates for ongoing synchronization

The system includes a complete testing environment with MinIO (S3-compatible storage) and mock APIs to simulate real-world scenarios without external dependencies.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Setup and Run
```bash
# Clone and start
git clone https://github.com/siktec-lab/cloud-buckets-sync.git
cd cloud-buckets-sync
make setup

# Check status
make status

# Test the system
make test-workflow
```

### Access Points
- **MinIO Console**: http://localhost:9011 (minioadmin/minioadmin)
- **Mock API**: http://localhost:8001
- **Service Logs**: `make logs-sync`

## Development Environment

### Core Components
- **sync-service**: Main Python application with live code reloading
- **minio-customer**: S3-compatible storage with test data
- **mock-api**: FastAPI server simulating file manager endpoints
- **test-suite**: Comprehensive testing framework

### Live Development
The service supports live code reloading - modify files in `sync_service/` and the service automatically restarts.

### Testing
```bash
# Run all unit tests
make test

# Run end-to-end workflow test
make test-workflow

# Check service health
make status
```

## Usage

### Make Commands
```bash
# Setup
make setup           # Build and start all services
make clean           # Clean up containers and volumes

# Sync Operations
make initial-sync    # Run initial synchronization
make incremental-sync # Run incremental synchronization
make status          # Show service status

# Development
make logs-sync       # Show sync service logs
make shell           # Open shell in sync container
make test            # Run unit tests
```

### Direct Commands
```bash
# Inside container
docker-compose exec sync-service python -m sync_service.main help
docker-compose exec sync-service python -m sync_service.main status
docker-compose exec sync-service python -m sync_service.main test
```

### CLI Wrappers
Cross-platform scripts are available:
- **Windows**: `sync_cli.ps1 status`
- **Linux/macOS**: `./sync_cli.sh status`

## Architecture

### Sync Workflows

**Initial Sync (New Integration)**
1. Scan entire S3 bucket
2. Process each file: get permissions, save to disk, store in database
3. Export state to CSV

**Incremental Sync (Periodic Updates)**
1. Export current database state to CSV
2. Process pub/sub events to update database
3. Compare old vs new state via CSV diff
4. Execute operations based on differences
5. Report results

**Daemon Mode (Production)**
- Automatically runs initial sync if database is empty
- Performs incremental sync at configured intervals (default: 5 minutes)
- Handles errors gracefully and continues operation

### Project Structure
```
cloud-buckets-sync/
├── sync_service/          # Main application
│   ├── clients/           # S3 and API clients
│   ├── models/            # Data models and configuration
│   ├── services/          # Core business logic
│   └── main.py            # Application entry point
├── mock_api/              # Mock API server
├── tests/                 # Test suite
├── test-data/             # Sample files
├── examples/              # Demo scripts
├── docker-compose.yml     # Service orchestration
├── Makefile              # Build commands
└── README.md             # This file
```

## Configuration

Environment variables in `docker-compose.yml`:
```yaml
# S3 Configuration
CUSTOMER_S3_ENDPOINT=http://minio-customer:9000
CUSTOMER_S3_BUCKET=customer-bucket
CUSTOMER_S3_ACCESS_KEY=minioadmin
CUSTOMER_S3_SECRET_KEY=minioadmin

# Service Configuration
SYNC_INTERVAL=300                    # Sync interval in seconds
DATABASE_PATH=/app/data/sync.db      # SQLite database path
MOCK_API_URL=http://mock-api:8001    # Mock API endpoint
```

## Production Deployment

### Preparing for Production

This development system can be adapted for production deployment with the following considerations:

#### 1. Configuration Updates
```yaml
# Update docker-compose.yml for production
environment:
  # Real S3 credentials
  - CUSTOMER_S3_ENDPOINT=https://your-s3-endpoint.com
  - CUSTOMER_S3_ACCESS_KEY=your-real-access-key
  - CUSTOMER_S3_SECRET_KEY=your-real-secret-key
  - CUSTOMER_S3_BUCKET=your-production-bucket
  
  # Real API endpoints
  - MOCK_API_URL=https://your-production-api.com
  
  # Production settings
  - SYNC_INTERVAL=300
  - LIVE_RELOAD=false
```

#### 2. Security Considerations
- Replace default MinIO credentials
- Use environment variables or secrets management for credentials
- Enable HTTPS for all API endpoints
- Implement proper authentication and authorization
- Set up network security groups and firewalls

#### 3. Monitoring and Logging
- Configure centralized logging (ELK stack, CloudWatch, etc.)
- Set up monitoring and alerting (Prometheus, Grafana, etc.)
- Implement health checks and service discovery
- Configure log rotation and retention policies

#### 4. Scalability and Reliability
- Use managed databases instead of SQLite for production
- Implement horizontal scaling with load balancers
- Set up backup and disaster recovery procedures
- Configure auto-scaling based on workload

#### 5. Deployment Pipeline
```bash
# Production deployment example
# 1. Build production images
docker build -t your-registry/sync-service:latest .

# 2. Push to registry
docker push your-registry/sync-service:latest

# 3. Deploy with production compose file
docker-compose -f docker-compose.prod.yml up -d

# 4. Run initial sync (first deployment only)
docker-compose exec sync-service python -m sync_service.main initial-sync

# 5. Monitor deployment
docker-compose logs -f sync-service
```

## Future Cloud Storage Integrations

This system is designed to be extensible for additional cloud storage providers. Here's how to add new integrations:

### Integration Architecture

#### 1. Storage Client Pattern
New storage providers should follow the existing client pattern:

```python
# Example: SharePoint integration
class SharePointManager:
    def __init__(self, config: SharePointConfig):
        self.config = config
        self.client = self._initialize_client()
    
    def list_objects(self) -> Iterator[StorageObject]:
        """List all objects in SharePoint site"""
        pass
    
    def get_object_stream(self, object_key: str) -> BinaryIO:
        """Get file stream from SharePoint"""
        pass
    
    def test_connection(self) -> bool:
        """Test SharePoint connection"""
        pass
```

#### 2. Configuration Extension
Add new configuration classes:

```python
@dataclass
class SharePointConfig:
    site_url: str
    client_id: str
    client_secret: str
    tenant_id: str
    
    @classmethod
    def from_env(cls) -> 'SharePointConfig':
        return cls(
            site_url=os.getenv('SHAREPOINT_SITE_URL'),
            client_id=os.getenv('SHAREPOINT_CLIENT_ID'),
            client_secret=os.getenv('SHAREPOINT_CLIENT_SECRET'),
            tenant_id=os.getenv('SHAREPOINT_TENANT_ID')
        )
```

#### 3. Service Integration
Update the main sync service to support multiple storage types:

```python
class SyncService:
    def __init__(self, config: SyncConfig):
        # Initialize appropriate storage client based on config
        if config.storage_type == 's3':
            self.storage_manager = S3Manager(config.s3_config)
        elif config.storage_type == 'sharepoint':
            self.storage_manager = SharePointManager(config.sharepoint_config)
        # Add more storage types as needed
```

#### 4. Testing Framework
Each new integration should include:
- Unit tests for the storage client
- Integration tests with mock services
- End-to-end workflow tests
- Performance and reliability tests

#### 5. Planned Integrations
Future integrations could include:
- **SharePoint Online**: Microsoft 365 document libraries
- **Google Drive**: Google Workspace file storage
- **Azure Blob Storage**: Microsoft Azure cloud storage
- **Dropbox Business**: Dropbox team folders
- **Box**: Enterprise content management
- **OneDrive**: Microsoft personal and business storage

### Integration Development Process

1. **Create Mock Service**: Develop a mock API that simulates the target storage provider
2. **Implement Client**: Build the storage client following the established patterns
3. **Add Configuration**: Extend configuration classes and environment variables
4. **Write Tests**: Create comprehensive test suite for the new integration
5. **Update Documentation**: Document configuration and usage for the new provider
6. **Integration Testing**: Test with the complete sync workflow

This modular approach ensures that new cloud storage integrations can be added without disrupting existing functionality, and each integration benefits from the robust testing and development environment provided by this system.

## Service Isolation for Production Applications

This sync service can be isolated and integrated into larger applications as a standalone microservice. Here are the recommended approaches:

### 1. Microservice Integration

#### Docker Container Deployment
Package the sync service as a standalone container for integration into existing applications:

```dockerfile
# Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the sync service code
COPY sync_service/ ./sync_service/

# Create non-root user
RUN useradd -m -u 1000 syncuser && chown -R syncuser:syncuser /app
USER syncuser

# Set environment
ENV PYTHONPATH=/app

# Run the service
CMD ["python", "-m", "sync_service.main", "daemon"]
```

#### Kubernetes Deployment
Deploy as a Kubernetes service with proper resource management:

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloud-sync-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloud-sync-service
  template:
    metadata:
      labels:
        app: cloud-sync-service
    spec:
      containers:
      - name: sync-service
        image: your-registry/cloud-sync-service:latest
        env:
        - name: CUSTOMER_S3_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: s3-credentials
              key: endpoint
        - name: CUSTOMER_S3_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: s3-credentials
              key: access-key
        - name: DATABASE_PATH
          value: "/data/sync.db"
        volumeMounts:
        - name: sync-data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: sync-data
        persistentVolumeClaim:
          claimName: sync-data-pvc
```

### 2. API Integration Patterns

#### REST API Wrapper
Create a REST API wrapper around the sync service for external applications:

```python
# api_wrapper.py
from fastapi import FastAPI, BackgroundTasks
from sync_service.services.sync_service import SyncService
from sync_service.models.config import SyncConfig

app = FastAPI(title="Cloud Sync API")

@app.post("/sync/initial")
async def trigger_initial_sync(background_tasks: BackgroundTasks):
    """Trigger initial synchronization"""
    config = SyncConfig.from_env()
    sync_service = SyncService(config)
    background_tasks.add_task(sync_service.run_initial_sync)
    return {"status": "initial_sync_started"}

@app.post("/sync/incremental")
async def trigger_incremental_sync(background_tasks: BackgroundTasks):
    """Trigger incremental synchronization"""
    config = SyncConfig.from_env()
    sync_service = SyncService(config)
    background_tasks.add_task(sync_service.run_incremental_sync)
    return {"status": "incremental_sync_started"}

@app.get("/sync/status")
async def get_sync_status():
    """Get current sync service status"""
    config = SyncConfig.from_env()
    sync_service = SyncService(config)
    return sync_service.get_sync_status()
```

#### Message Queue Integration
Integrate with message queues for event-driven synchronization:

```python
# queue_integration.py
import pika
import json
from sync_service.services.sync_service import SyncService
from sync_service.models.config import SyncConfig

class SyncQueueConsumer:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('rabbitmq-server')
        )
        self.channel = self.connection.channel()
        self.sync_service = SyncService(SyncConfig.from_env())
    
    def setup_queues(self):
        self.channel.queue_declare(queue='sync_requests', durable=True)
        self.channel.basic_consume(
            queue='sync_requests',
            on_message_callback=self.handle_sync_request,
            auto_ack=True
        )
    
    def handle_sync_request(self, ch, method, properties, body):
        request = json.loads(body)
        if request['type'] == 'initial':
            self.sync_service.run_initial_sync()
        elif request['type'] == 'incremental':
            self.sync_service.run_incremental_sync()
```

### 3. Library Integration

#### Python Package
Package the core sync functionality as a Python library:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="cloud-sync-service",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.34.0",
        "pandas>=2.1.4",
        "requests>=2.31.0",
        "loguru>=0.7.2",
    ],
    entry_points={
        'console_scripts': [
            'cloud-sync=sync_service.main:main',
        ],
    },
)
```

#### Usage as Library
```python
# In your application
from sync_service.services.sync_service import SyncService
from sync_service.models.config import SyncConfig

# Initialize and use
config = SyncConfig.from_env()
sync_service = SyncService(config)

# Run synchronization
initial_results = sync_service.run_initial_sync()
incremental_results = sync_service.run_incremental_sync()

# Get status
status = sync_service.get_sync_status()
```

### 4. Configuration Management

#### Environment-Based Configuration
Isolate configuration for different environments:

```bash
# Production environment variables
export CUSTOMER_S3_ENDPOINT="https://production-s3.company.com"
export CUSTOMER_S3_BUCKET="production-bucket"
export SYNC_INTERVAL="600"  # 10 minutes for production
export DATABASE_PATH="/var/lib/sync/production.db"
export LOG_LEVEL="INFO"

# Staging environment
export CUSTOMER_S3_ENDPOINT="https://staging-s3.company.com"
export CUSTOMER_S3_BUCKET="staging-bucket"
export SYNC_INTERVAL="300"  # 5 minutes for staging
export DATABASE_PATH="/var/lib/sync/staging.db"
export LOG_LEVEL="DEBUG"
```

#### Configuration Files
Support configuration files for complex deployments:

```yaml
# config/production.yaml
storage:
  type: "s3"
  endpoint: "https://production-s3.company.com"
  bucket: "production-bucket"
  credentials:
    access_key: "${S3_ACCESS_KEY}"
    secret_key: "${S3_SECRET_KEY}"

sync:
  interval: 600
  initial_sync_on_startup: true
  
database:
  path: "/var/lib/sync/production.db"
  backup_enabled: true
  backup_interval: 3600

logging:
  level: "INFO"
  file: "/var/log/sync/service.log"
  rotation: "10MB"
  retention: "30 days"

api:
  endpoints:
    file_manager: "https://api.company.com/files"
    reporting: "https://api.company.com/sync-reports"
  timeout: 30
  retry_attempts: 3
```

### 5. Monitoring and Observability

#### Health Check Endpoint
Provide health checks for container orchestration:

```python
# health_check.py
@app.get("/health")
async def health_check():
    config = SyncConfig.from_env()
    sync_service = SyncService(config)
    
    # Test all connections
    s3_healthy = sync_service.s3_manager.test_connection()
    api_healthy = sync_service.infrastructure_api.health_check()
    db_healthy = sync_service.database_manager.get_record_count() >= 0
    
    status = "healthy" if all([s3_healthy, api_healthy, db_healthy]) else "unhealthy"
    
    return {
        "status": status,
        "components": {
            "s3": "healthy" if s3_healthy else "unhealthy",
            "api": "healthy" if api_healthy else "unhealthy",
            "database": "healthy" if db_healthy else "unhealthy"
        },
        "timestamp": datetime.now().isoformat()
    }
```

#### Metrics Export
Export metrics for monitoring systems:

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
sync_operations_total = Counter('sync_operations_total', 'Total sync operations', ['type', 'status'])
sync_duration_seconds = Histogram('sync_duration_seconds', 'Sync operation duration')
sync_files_processed = Counter('sync_files_processed_total', 'Total files processed')
database_records_total = Gauge('database_records_total', 'Total records in database')

class MetricsCollector:
    def record_sync_operation(self, sync_type: str, status: str, duration: float):
        sync_operations_total.labels(type=sync_type, status=status).inc()
        sync_duration_seconds.observe(duration)
    
    def record_files_processed(self, count: int):
        sync_files_processed.inc(count)
    
    def update_database_records(self, count: int):
        database_records_total.set(count)
```

### 6. Security Considerations

#### Secrets Management
Use proper secrets management for production:

```python
# secrets_manager.py
import boto3
from botocore.exceptions import ClientError

class SecretsManager:
    def __init__(self, region_name="us-east-1"):
        self.client = boto3.client('secretsmanager', region_name=region_name)
    
    def get_secret(self, secret_name: str) -> dict:
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except ClientError as e:
            raise Exception(f"Failed to retrieve secret {secret_name}: {e}")

# Usage in configuration
secrets = SecretsManager()
s3_credentials = secrets.get_secret("production/s3-credentials")
```

#### Network Security
Configure network policies for isolated deployment:

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cloud-sync-service-policy
spec:
  podSelector:
    matchLabels:
      app: cloud-sync-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS to S3 and APIs
    - protocol: TCP
      port: 5432  # PostgreSQL if using external DB
```

This isolation approach allows the sync service to be deployed as a standalone component in larger applications while maintaining proper separation of concerns, security, and scalability.