# S3 Sync Service Examples

This directory contains demo scripts and utilities for the S3 sync service.

## Demo Scripts

### `demo_sync_service.py`
Complete demonstration of the sync service functionality.
```bash
python examples/demo_sync_service.py
```
Shows:
- Service initialization
- Initial sync execution  
- Database inspection
- Results summary

### `demo_api_client.py`
Demonstrates Infrastructure API client usage.
```bash
python examples/demo_api_client.py
```
Shows:
- API health checks
- File operations (create, update, delete)
- Permissions management
- Event retrieval

## Utilities

### `utils.py`
Collection of utility functions for service management.

```bash
# Check database contents
python examples/utils.py check-db

# Check Docker container status  
python examples/utils.py check-docker

# Clear database records
python examples/utils.py clear-db
```

## Prerequisites

Before running examples:

1. **Start Docker services:**
   ```bash
   docker-compose up -d
   ```

2. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

3. **Check service health:**
   ```bash
   python examples/utils.py check-docker
   ```

## Expected Output

Successful demo runs should show:
- ✅ Service initialization
- ✅ S3 connection established
- ✅ Files processed and synced
- ✅ Database records created
- ✅ API operations completed

## Troubleshooting

If demos fail:
1. Check Docker services are running
2. Verify MinIO buckets are initialized
3. Ensure mock API is responding
4. Check logs: `docker-compose logs sync-service`

See `../docs/docker_troubleshooting.md` for detailed troubleshooting.