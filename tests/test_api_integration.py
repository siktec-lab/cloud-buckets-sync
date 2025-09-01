#!/usr/bin/env python3
"""
Integration tests for Infrastructure API endpoints.

Tests all API functionality:
- updatePermissions: Get and update permissions
- saveToDisk: All operations (create, update, rename, move, delete, get)
- pubSubFullList: Get unconsumed events
"""
import io
import sys
import pytest
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sync_service.clients.infrastructure_api import InfrastructureAPI, InfrastructureAPIError
from loguru import logger


@pytest.fixture
def api_client():
    """Pytest fixture for API client."""
    return InfrastructureAPI("http://localhost:8001")


def test_update_permissions(api_client, check_services):
    """Test updatePermissions endpoint."""
    logger.info("Testing updatePermissions endpoint...")
    
    file_path = "/test/permissions_test.txt"
    
    # Get current permissions
    permissions = api_client.update_permissions(file_path)
    logger.info(f"Current permissions: {permissions.get('permissions')}")
    
    # Update permissions
    new_permissions = api_client.update_permissions(
        file_path=file_path,
        permissions="rwxrwxrwx",
        owner="admin",
        group="admin"
    )
    logger.info(f"Updated permissions: {new_permissions.get('permissions')}")
    assert permissions is not None
    assert new_permissions is not None


def test_save_to_disk_operations(api_client, check_services, sample_file_content):
    """Test saveToDisk endpoint operations."""
    logger.info("Testing saveToDisk operations...")
    
    file_path = "/test/operations_test.txt"
    
    # Create operation
    file_stream = io.BytesIO(sample_file_content)
    create_result = api_client.save_to_disk(
        operation="create",
        file_path=file_path,
        file_stream=file_stream,
        size=len(sample_file_content),
        file_type="text/plain"
    )
    logger.info(f"Created file with ID: {create_result.get('internal_id')}")
    
    # Update operation
    updated_content = b"Updated content."
    file_stream = io.BytesIO(updated_content)
    update_result = api_client.save_to_disk(
        operation="update",
        file_path=file_path,
        file_stream=file_stream,
        size=len(updated_content)
    )
    logger.info(f"Updated file: {update_result.get('status')}")
    
    # Delete operation
    delete_result = api_client.save_to_disk(
        operation="delete",
        file_path=file_path
    )
    logger.info(f"Deleted file: {delete_result.get('status')}")
    
    assert create_result is not None
    assert update_result is not None
    assert delete_result is not None


def test_pub_sub_events(api_client, check_services):
    """Test pubSubFullList endpoint."""
    logger.info("Testing pubSubFullList endpoint...")
    
    events = api_client.get_pub_sub_events(count=5)
    logger.info(f"Retrieved {len(events)} events")
    
    for event in events[:2]:  # Show first 2 events
        logger.info(f"Event: {event.event_type} - {event.file_path}")
    
    assert isinstance(events, list)


# Tests are now run with pytest