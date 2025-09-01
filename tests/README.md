# S3 Sync Service Tests

This directory contains test suites for the S3 sync service components.

## Test Files

### `test_initial_sync.py`
Comprehensive test suite for initial sync functionality (Task 7).

Tests:
- S3 bucket scanning logic
- File processing workflow
- SQLite record creation  
- Permissions retrieval
- Complete sync integration

```bash
python tests/test_initial_sync.py
```

### `test_api_integration.py`
Integration tests for Infrastructure API endpoints.

Tests:
- updatePermissions endpoint
- saveToDisk operations (create, update, delete, etc.)
- pubSubFullList event retrieval

```bash
python tests/test_api_integration.py
```

## Running Tests

### Prerequisites
1. Start Docker services: `docker-compose up -d`
2. Verify services are healthy: `python examples/utils.py check-docker`

### Run Individual Tests
```bash
# Test initial sync functionality
python tests/test_initial_sync.py

# Test API integration
python tests/test_api_integration.py
```

### Run All Tests
```bash
python tests/run_all_tests.py
```

## Test Environment

Tests use isolated test databases and connect to:
- **MinIO S3**: localhost:9001 (customer-bucket)
- **Mock API**: localhost:8001
- **Test Database**: data/test_sync.db

## Expected Results

All tests should pass with output like:
```
=== Test Results: 5/5 tests passed ===
🎉 All tests passed!
```

## Troubleshooting

If tests fail:
1. Ensure Docker services are running and healthy
2. Check MinIO buckets contain test data
3. Verify mock API is responding
4. Clear test database: `python examples/utils.py clear-db`