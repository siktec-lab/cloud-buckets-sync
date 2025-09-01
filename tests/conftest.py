"""
Pytest configuration and fixtures for the S3 sync service tests.
"""
import os
import pytest
import tempfile
from pathlib import Path

from sync_service.clients.infrastructure_api import InfrastructureAPI
from sync_service.services.database_manager import DatabaseManager


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables for all tests."""
    # Set up environment variables for testing
    test_env = {
        'CUSTOMER_S3_ENDPOINT': 'http://localhost:9001',
        'CUSTOMER_S3_ACCESS_KEY': 'minioadmin',
        'CUSTOMER_S3_SECRET_KEY': 'minioadmin',
        'CUSTOMER_S3_BUCKET': 'customer-bucket',
        'CUSTOMER_S3_REGION': 'us-east-1',
        'MOCK_API_URL': 'http://localhost:8001',
        'FILE_MANAGER_API_URL': 'http://localhost:8000',
        'DATABASE_PATH': 'data/test_sync.db',
        'SYNC_INTERVAL': '300'
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup is handled automatically when the session ends


@pytest.fixture
def api_client():
    """Pytest fixture for Infrastructure API client."""
    return InfrastructureAPI("http://localhost:8001")


@pytest.fixture
def temp_database():
    """Pytest fixture for temporary database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    db_manager = DatabaseManager(db_path)
    yield db_manager
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def sample_file_content():
    """Sample file content for testing."""
    return b"This is test file content for integration testing."


@pytest.fixture(scope="session")
def check_services():
    """Check that required services are running before tests."""
    import requests
    
    services = [
        ("MinIO", "http://localhost:9001/minio/health/live"),
        ("Mock API", "http://localhost:8001/")
    ]
    
    for service_name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code not in [200, 404]:  # 404 is ok for some endpoints
                pytest.skip(f"{service_name} is not responding correctly (status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"{service_name} is not accessible: {e}")
    
    return True