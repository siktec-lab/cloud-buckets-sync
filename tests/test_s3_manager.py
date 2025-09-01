"""
Tests for S3Manager class.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from datetime import datetime
from botocore.exceptions import ClientError

from sync_service.clients.s3_manager import S3Manager, S3Object
from sync_service.models.config import S3Config


@pytest.fixture
def customer_config():
    """Create a test customer S3 configuration."""
    return S3Config(
        endpoint='http://localhost:9000',
        access_key='customer_key',
        secret_key='customer_secret',
        bucket='customer-bucket'
    )


@pytest.fixture
def s3_manager(customer_config):
    """Create a test S3Manager instance with mocked client."""
    with patch('sync_service.clients.s3_manager.boto3.client') as mock_boto3:
        mock_customer_client = Mock()
        mock_boto3.return_value = mock_customer_client
        
        manager = S3Manager(customer_config)
        manager.customer_client = mock_customer_client
        
        return manager


class TestS3Manager:
    """Test cases for S3Manager."""
    
    def test_initialization(self, customer_config):
        """Test S3Manager initialization."""
        with patch('sync_service.clients.s3_manager.boto3.client') as mock_boto3:
            mock_boto3.return_value = Mock()
            
            manager = S3Manager(customer_config)
            
            assert manager.customer_config == customer_config
            assert mock_boto3.call_count == 1
    
    def test_list_objects_customer(self, s3_manager):
        """Test listing objects from customer bucket."""
        # Mock paginator response
        mock_paginator = Mock()
        mock_page_iterator = [
            {
                'Contents': [
                    {
                        'Key': 'test-file.txt',
                        'Size': 1024,
                        'LastModified': datetime.now(),
                        'ETag': '"abc123"',
                        'StorageClass': 'STANDARD'
                    }
                ]
            }
        ]
        mock_paginator.paginate.return_value = mock_page_iterator
        s3_manager.customer_client.get_paginator.return_value = mock_paginator
        
        objects = list(s3_manager.list_objects())
        
        assert len(objects) == 1
        assert objects[0].key == 'test-file.txt'
        assert objects[0].size == 1024
        assert objects[0].etag == 'abc123'
    
    def test_get_object_stream(self, s3_manager):
        """Test getting object stream."""
        mock_response = {'Body': BytesIO(b'test content')}
        s3_manager.customer_client.get_object.return_value = mock_response
        
        stream = s3_manager.get_object_stream('test-key')
        
        assert stream == mock_response['Body']
        s3_manager.customer_client.get_object.assert_called_once_with(
            Bucket='customer-bucket', Key='test-key'
        )
    
    def test_get_object_metadata(self, s3_manager):
        """Test getting object metadata."""
        mock_response = {
            'ContentLength': 1024,
            'LastModified': datetime.now(),
            'ETag': '"abc123"',
            'ContentType': 'text/plain',
            'Metadata': {'custom': 'value'},
            'StorageClass': 'STANDARD'
        }
        s3_manager.customer_client.head_object.return_value = mock_response
        
        metadata = s3_manager.get_object_metadata('test-key')
        
        assert metadata['size'] == 1024
        assert metadata['etag'] == 'abc123'
        assert metadata['content_type'] == 'text/plain'
        assert metadata['metadata'] == {'custom': 'value'}
    

    
    def test_object_exists_true(self, s3_manager):
        """Test checking if object exists (exists)."""
        mock_response = {
            'ContentLength': 1024,
            'LastModified': datetime.now(),
            'ETag': '"abc123"'
        }
        s3_manager.customer_client.head_object.return_value = mock_response
        
        exists = s3_manager.object_exists('test-key')
        
        assert exists is True
    
    def test_object_exists_false(self, s3_manager):
        """Test checking if object exists (doesn't exist)."""
        error = ClientError(
            error_response={'Error': {'Code': '404'}},
            operation_name='HeadObject'
        )
        s3_manager.customer_client.head_object.side_effect = error
        
        exists = s3_manager.object_exists('test-key')
        
        assert exists is False
    
    def test_retry_operation_success(self, s3_manager):
        """Test retry operation succeeds on first attempt."""
        operation = Mock(return_value='success')
        
        result = s3_manager._retry_operation(operation)
        
        assert result == 'success'
        assert operation.call_count == 1
    
    def test_retry_operation_eventual_success(self, s3_manager):
        """Test retry operation succeeds after failures."""
        operation = Mock()
        operation.side_effect = [
            ClientError({'Error': {'Code': '500'}}, 'TestOperation'),
            ClientError({'Error': {'Code': '500'}}, 'TestOperation'),
            'success'
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = s3_manager._retry_operation(operation, max_retries=3)
        
        assert result == 'success'
        assert operation.call_count == 3
    
    def test_retry_operation_max_retries_exceeded(self, s3_manager):
        """Test retry operation fails after max retries."""
        operation = Mock()
        operation.side_effect = ClientError({'Error': {'Code': '500'}}, 'TestOperation')
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(ClientError):
                s3_manager._retry_operation(operation, max_retries=2)
        
        assert operation.call_count == 2
    
    def test_test_connection_success(self, s3_manager):
        """Test connection testing when it succeeds."""
        s3_manager.customer_client.head_bucket.return_value = {}
        
        result = s3_manager.test_connection()
        
        assert result is True
    
    def test_test_connection_failure(self, s3_manager):
        """Test connection testing when it fails."""
        s3_manager.customer_client.head_bucket.side_effect = Exception('Connection failed')
        
        result = s3_manager.test_connection()
        
        assert result is False


class TestS3Object:
    """Test cases for S3Object."""
    
    def test_s3_object_creation(self):
        """Test S3Object creation."""
        now = datetime.now()
        obj = S3Object(
            key='test-key',
            size=1024,
            last_modified=now,
            etag='abc123',
            storage_class='STANDARD'
        )
        
        assert obj.key == 'test-key'
        assert obj.size == 1024
        assert obj.last_modified == now
        assert obj.etag == 'abc123'
        assert obj.storage_class == 'STANDARD'
    
    def test_s3_object_default_storage_class(self):
        """Test S3Object with default storage class."""
        obj = S3Object(
            key='test-key',
            size=1024,
            last_modified=datetime.now(),
            etag='abc123'
        )
        
        assert obj.storage_class == 'STANDARD'