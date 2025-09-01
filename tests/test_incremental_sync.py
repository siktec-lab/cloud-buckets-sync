"""
Tests for incremental sync workflow functionality.
"""
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from io import BytesIO

from sync_service.services.sync_service import SyncService
from sync_service.models.config import SyncConfig, S3Config
from sync_service.models.data_models import PubSubEvent, FileRecord, FileOperation


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sync_config(temp_db):
    """Create a test sync configuration."""
    return SyncConfig(
        customer_s3=S3Config(
            endpoint="http://localhost:9000",
            access_key="test_key",
            secret_key="test_secret",
            bucket="test-bucket"
        ),
        mock_api_url="http://localhost:8000",
        file_manager_api_url="http://localhost:8001",
        database_path=temp_db,
        sync_interval=300,
        live_reload=False
    )


@pytest.fixture
def mock_sync_service(sync_config):
    """Create a sync service with mocked dependencies."""
    with patch('sync_service.services.sync_service.S3Manager'), \
         patch('sync_service.services.sync_service.InfrastructureAPI'), \
         patch('sync_service.services.sync_service.DatabaseManager'), \
         patch('sync_service.services.sync_service.CSVProcessor'), \
         patch('sync_service.services.sync_service.EventProcessor'):
        
        service = SyncService(sync_config)
        
        # Mock the components
        service.s3_manager = Mock()
        service.infrastructure_api = Mock()
        service.database_manager = Mock()
        service.csv_processor = Mock()
        service.event_processor = Mock()
        
        return service


class TestIncrementalSyncWorkflow:
    """Test cases for incremental sync workflow."""
    
    def test_incremental_sync_complete_workflow(self, mock_sync_service):
        """Test complete incremental sync workflow with events and operations."""
        # Setup mocks
        mock_sync_service._test_connections = Mock(return_value=True)
        mock_sync_service.export_state_to_csv = Mock()
        mock_sync_service._cleanup_temp_files = Mock()
        
        # Mock events from infrastructure API
        test_events = [
            PubSubEvent(
                event_type="create",
                file_path="new_file.txt",
                metadata={"size": 100, "file_type": "text/plain"},
                timestamp=datetime.now()
            ),
            PubSubEvent(
                event_type="delete",
                file_path="old_file.txt",
                timestamp=datetime.now()
            )
        ]
        mock_sync_service.infrastructure_api.get_pub_sub_events.return_value = test_events
        
        # Mock event processing
        event_counts = {"create": 1, "delete": 1, "errors": 0}
        mock_sync_service.event_processor.process_events.return_value = event_counts
        
        # Mock CSV diff operations
        test_operations = [
            FileOperation(
                operation_type="create",
                file_path="new_file.txt",
                metadata={"size": 100, "file_type": "text/plain"}
            ),
            FileOperation(
                operation_type="delete",
                file_path="old_file.txt"
            )
        ]
        mock_sync_service.process_csv_diff = Mock(return_value=test_operations)
        
        # Mock operation execution
        mock_sync_service._execute_operation = Mock(return_value=True)
        
        # Mock result reporting
        mock_sync_service._report_sync_results = Mock()
        
        # Execute incremental sync
        result = mock_sync_service.run_incremental_sync()
        
        # Verify workflow steps
        assert mock_sync_service._test_connections.called
        assert mock_sync_service.export_state_to_csv.call_count == 2  # old and new state
        assert mock_sync_service.infrastructure_api.get_pub_sub_events.called
        mock_sync_service.event_processor.process_events.assert_called_with(test_events)
        assert mock_sync_service.process_csv_diff.called
        assert mock_sync_service._execute_operation.call_count == 2  # two operations
        assert mock_sync_service._report_sync_results.called
        assert mock_sync_service._cleanup_temp_files.called
        
        # Verify result structure
        assert result['success'] is True
        assert result['events_processed'] == 2
        assert result['operations_processed'] == 2
        assert result['operations_failed'] == 0
        assert result['event_counts'] == event_counts
        assert 'duration' in result
        assert 'start_time' in result
        assert 'end_time' in result
    
    def test_incremental_sync_no_events(self, mock_sync_service):
        """Test incremental sync when no events are available."""
        # Setup mocks
        mock_sync_service._test_connections = Mock(return_value=True)
        mock_sync_service.export_state_to_csv = Mock()
        mock_sync_service._cleanup_temp_files = Mock()
        
        # No events from infrastructure API
        mock_sync_service.infrastructure_api.get_pub_sub_events.return_value = []
        
        # No operations from CSV diff
        mock_sync_service.process_csv_diff = Mock(return_value=[])
        
        # Mock result reporting
        mock_sync_service._report_sync_results = Mock()
        
        # Execute incremental sync
        result = mock_sync_service.run_incremental_sync()
        
        # Verify workflow
        assert result['success'] is True
        assert result['events_processed'] == 0
        assert result['operations_processed'] == 0
        assert result['operations_failed'] == 0
        assert result['event_counts'] == {}
        
        # Verify CSV export still happens
        assert mock_sync_service.export_state_to_csv.call_count == 2
    
    def test_incremental_sync_operation_failures(self, mock_sync_service):
        """Test incremental sync with some operation failures."""
        # Setup mocks
        mock_sync_service._test_connections = Mock(return_value=True)
        mock_sync_service.export_state_to_csv = Mock()
        mock_sync_service._cleanup_temp_files = Mock()
        
        # Mock events
        test_events = [
            PubSubEvent(
                event_type="create",
                file_path="file1.txt",
                timestamp=datetime.now()
            )
        ]
        mock_sync_service.infrastructure_api.get_pub_sub_events.return_value = test_events
        mock_sync_service.event_processor.process_events.return_value = {"create": 1}
        
        # Mock operations
        test_operations = [
            FileOperation(operation_type="create", file_path="file1.txt"),
            FileOperation(operation_type="update", file_path="file2.txt")
        ]
        mock_sync_service.process_csv_diff = Mock(return_value=test_operations)
        
        # Mock operation execution with one failure
        def mock_execute_operation(operation):
            if operation.file_path == "file1.txt":
                return True
            else:
                raise Exception("Operation failed")
        
        mock_sync_service._execute_operation = Mock(side_effect=mock_execute_operation)
        mock_sync_service._report_sync_results = Mock()
        
        # Execute incremental sync
        result = mock_sync_service.run_incremental_sync()
        
        # Verify results
        assert result['success'] is True  # Overall sync succeeds even with operation failures
        assert result['operations_processed'] == 1
        assert result['operations_failed'] == 1
        assert len(result['errors']) == 1
    
    def test_incremental_sync_connection_failure(self, mock_sync_service):
        """Test incremental sync when connection tests fail."""
        # Mock connection test failure
        mock_sync_service._test_connections = Mock(return_value=False)
        mock_sync_service._cleanup_temp_files = Mock()
        mock_sync_service._report_sync_results = Mock()
        
        # Execute incremental sync and expect exception
        with pytest.raises(Exception, match="Connection tests failed"):
            mock_sync_service.run_incremental_sync()
        
        # Verify failure reporting
        assert mock_sync_service._report_sync_results.called
    
    def test_incremental_sync_event_processing_failure(self, mock_sync_service):
        """Test incremental sync when event processing fails."""
        # Setup mocks
        mock_sync_service._test_connections = Mock(return_value=True)
        mock_sync_service.export_state_to_csv = Mock()
        mock_sync_service._cleanup_temp_files = Mock()
        
        # Mock infrastructure API failure
        mock_sync_service.infrastructure_api.get_pub_sub_events.side_effect = Exception("API failure")
        mock_sync_service._report_sync_results = Mock()
        
        # Execute incremental sync and expect exception
        with pytest.raises(Exception, match="API failure"):
            mock_sync_service.run_incremental_sync()
        
        # Verify failure reporting
        assert mock_sync_service._report_sync_results.called
    
    def test_report_sync_results(self, mock_sync_service):
        """Test sync results reporting functionality."""
        # Mock database manager
        mock_sync_service.database_manager.get_record_count.return_value = 42
        
        # Test sync stats
        sync_stats = {
            'success': True,
            'duration': 123.45,
            'events_processed': 5,
            'operations_processed': 3,
            'operations_failed': 1,
            'event_counts': {'create': 2, 'delete': 1},
            'errors': ['Some error']
        }
        
        # Execute reporting
        mock_sync_service._report_sync_results(sync_stats, 'incremental')
        
        # Verify API call
        assert mock_sync_service.infrastructure_api.report_results.called
        
        # Get the reported data
        call_args = mock_sync_service.infrastructure_api.report_results.call_args[0][0]
        
        # Verify report structure
        assert call_args['sync_type'] == 'incremental'
        assert call_args['success'] is True
        assert call_args['duration_seconds'] == 123.45
        assert call_args['statistics']['events_processed'] == 5
        assert call_args['statistics']['operations_processed'] == 3
        assert call_args['statistics']['operations_failed'] == 1
        assert call_args['event_counts'] == {'create': 2, 'delete': 1}
        assert call_args['errors'] == ['Some error']
        assert call_args['service_info']['record_count'] == 42
    
    def test_cleanup_temp_files(self, mock_sync_service):
        """Test temporary file cleanup functionality."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as f1, \
             tempfile.NamedTemporaryFile(delete=False) as f2:
            file1_path = f1.name
            file2_path = f2.name
        
        # Verify files exist
        assert os.path.exists(file1_path)
        assert os.path.exists(file2_path)
        
        # Test cleanup
        mock_sync_service._cleanup_temp_files([file1_path, file2_path, None])
        
        # Verify files are deleted
        assert not os.path.exists(file1_path)
        assert not os.path.exists(file2_path)
    
    def test_cleanup_temp_files_nonexistent(self, mock_sync_service):
        """Test cleanup with non-existent files doesn't raise errors."""
        # Test cleanup with non-existent files
        mock_sync_service._cleanup_temp_files([
            "/nonexistent/file1.csv",
            "/nonexistent/file2.csv",
            None
        ])
        
        # Should not raise any exceptions