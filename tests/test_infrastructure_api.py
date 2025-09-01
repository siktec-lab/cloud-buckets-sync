"""
Tests for InfrastructureAPI client.

Tests HTTP communication with mock server endpoints including
error handling, retry logic, and file streaming.
"""

import pytest
import json
import io
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sync_service.clients.infrastructure_api import InfrastructureAPI, InfrastructureAPIError
from sync_service.models.data_models import PubSubEvent


class TestInfrastructureAPI:
    """Test cases for InfrastructureAPI client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:8001"
        self.api_client = InfrastructureAPI(self.base_url)
    
    def test_init(self):
        """Test InfrastructureAPI initialization."""
        assert self.api_client.base_url == self.base_url
        assert self.api_client.timeout == 30
        assert self.api_client.max_retries == 3
        assert self.api_client.session is not None
    
    def test_init_with_custom_params(self):
        """Test InfrastructureAPI initialization with custom parameters."""
        api_client = InfrastructureAPI(
            base_url="http://example.com/",
            timeout=60,
            max_retries=5
        )
        assert api_client.base_url == "http://example.com"
        assert api_client.timeout == 60
        assert api_client.max_retries == 5
    
    @patch('sync_service.clients.infrastructure_api.requests.Session.request')
    def test_update_permissions_success(self, mock_request):
        """Test successful permissions update."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "file_path": "/test/file.txt",
            "permissions": "rw-r--r--",
            "owner": "user",
            "group": "users",
            "last_updated": "2023-01-01T12:00:00"
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        # Test the method
        result = self.api_client.update_permissions("/test/file.txt")
        
        # Verify the call
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert call_args[1]['url'] == f"{self.base_url}/updatePermissions"
        assert call_args[1]['data'] == {"file_path": "/test/file.txt"}
        
        # Verify the result
        assert result["file_path"] == "/test/file.txt"
        assert result["permissions"] == "rw-r--r--"
    
    def test_update_permissions_empty_path(self):
        """Test update_permissions with empty file path."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            self.api_client.update_permissions("")
    
    @patch('sync_service.clients.infrastructure_api.requests.Session.request')
    def test_save_to_disk_success(self, mock_request):
        """Test successful file save to disk."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "internal_id": "12345-abcde",
            "file_path": "/test/file.txt",
            "operation": "create",
            "size": 1024,
            "saved_at": "2023-01-01T12:00:00",
            "status": "success"
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        # Create test file stream
        file_content = b"test file content"
        file_stream = io.BytesIO(file_content)
        
        # Test the method
        result = self.api_client.save_to_disk(
            operation="create",
            file_path="/test/file.txt",
            file_stream=file_stream,
            size=len(file_content),
            file_type="text/plain"
        )
        
        # Verify the call
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert call_args[1]['url'] == f"{self.base_url}/saveToDisk"
        assert call_args[1]['data']['operation'] == "create"
        assert call_args[1]['data']['file_path'] == "/test/file.txt"
        assert call_args[1]['data']['size'] == str(len(file_content))
        assert call_args[1]['data']['file_type'] == "text/plain"
        assert 'files' in call_args[1]
        
        # Verify the result
        assert result["internal_id"] == "12345-abcde"
        assert result["status"] == "success"
    
    def test_save_to_disk_empty_path(self):
        """Test save_to_disk with empty file path."""
        file_stream = io.BytesIO(b"test")
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            self.api_client.save_to_disk("create", "", file_stream)
    
    def test_save_to_disk_none_stream(self):
        """Test save_to_disk with None file stream for create operation."""
        with pytest.raises(ValueError, match="create operation requires file_stream"):
            self.api_client.save_to_disk("create", "/test/file.txt", None)
    
    @patch('sync_service.clients.infrastructure_api.requests.Session.request')
    def test_get_pub_sub_events_success(self, mock_request):
        """Test successful pub/sub events retrieval."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {
                    "event_type": "create",
                    "file_path": "/test/file1.txt",
                    "new_path": None,
                    "metadata": {"size": 1024},
                    "timestamp": "2023-01-01T12:00:00"
                },
                {
                    "event_type": "rename",
                    "file_path": "/test/file2.txt",
                    "new_path": "/test/file2_renamed.txt",
                    "metadata": None,
                    "timestamp": "2023-01-01T12:30:00"
                }
            ],
            "total_count": 2
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        # Test the method
        result = self.api_client.get_pub_sub_events(count=5)
        
        # Verify the call
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'GET'
        assert call_args[1]['url'] == f"{self.base_url}/pubSubFullList"
        assert call_args[1]['params'] == {"count": 5}
        
        # Verify the result
        assert len(result) == 2
        assert isinstance(result[0], PubSubEvent)
        assert result[0].event_type == "create"
        assert result[0].file_path == "/test/file1.txt"
        assert result[1].event_type == "rename"
        assert result[1].new_path == "/test/file2_renamed.txt"
    
    def test_get_pub_sub_events_invalid_count(self):
        """Test get_pub_sub_events with invalid count."""
        with pytest.raises(ValueError, match="count must be between 1 and 100"):
            self.api_client.get_pub_sub_events(count=0)
        
        with pytest.raises(ValueError, match="count must be between 1 and 100"):
            self.api_client.get_pub_sub_events(count=101)
    
    @patch('sync_service.clients.infrastructure_api.requests.Session.request')
    def test_report_results_success(self, mock_request):
        """Test successful results reporting."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "received",
            "message": "Sync results recorded successfully",
            "timestamp": "2023-01-01T12:00:00"
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        # Test data
        results = {
            "sync_type": "incremental",
            "files_processed": 10,
            "files_created": 3,
            "files_updated": 5,
            "files_deleted": 2,
            "duration": 120.5
        }
        
        # Test the method
        result = self.api_client.report_results(results)
        
        # Verify the call
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert call_args[1]['url'] == f"{self.base_url}/reportResults"
        assert call_args[1]['json'] == results
        assert call_args[1]['headers']['Content-Type'] == "application/json"
        
        # Verify the result
        assert result["status"] == "received"
    
    def test_report_results_empty_results(self):
        """Test report_results with empty results."""
        with pytest.raises(ValueError, match="results cannot be empty"):
            self.api_client.report_results({})
    
    @patch('sync_service.clients.infrastructure_api.requests.Session.request')
    def test_health_check_success(self, mock_request):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        result = self.api_client.health_check()
        
        assert result is True
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'GET'
        assert call_args[1]['url'] == f"{self.base_url}/"
    
    @patch('sync_service.clients.infrastructure_api.requests.Session.request')
    def test_health_check_failure(self, mock_request):
        """Test health check failure."""
        mock_request.side_effect = Exception("Connection failed")
        
        result = self.api_client.health_check()
        
        assert result is False
    
    @patch('sync_service.clients.infrastructure_api.requests.Session.request')
    def test_request_failure_raises_error(self, mock_request):
        """Test that request failures raise InfrastructureAPIError."""
        mock_request.side_effect = Exception("Network error")
        
        with pytest.raises(InfrastructureAPIError, match="Failed to get/update permissions"):
            self.api_client.update_permissions("/test/file.txt")