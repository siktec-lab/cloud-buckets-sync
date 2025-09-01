"""
Tests for the EventProcessor class.
"""
import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from sync_service.models.data_models import PubSubEvent, FileRecord
from sync_service.services.database_manager import DatabaseManager
from sync_service.services.event_processor import EventProcessor


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager instance for testing."""
    return DatabaseManager(temp_db)


@pytest.fixture
def event_processor(db_manager):
    """Create an EventProcessor instance for testing."""
    return EventProcessor(db_manager)


@pytest.fixture
def sample_file_record():
    """Create a sample file record for testing."""
    return FileRecord(
        file_path="/test/file.txt",
        permissions="rw-r--r--",
        size=1024,
        file_type="text/plain",
        last_modified=datetime(2023, 1, 1, 12, 0, 0),
        internal_id="test-id-123"
    )


class TestEventProcessor:
    """Test cases for EventProcessor."""
    
    def test_process_empty_events(self, event_processor):
        """Test processing empty event list."""
        result = event_processor.process_events([])
        assert result == {}
    
    def test_validate_event_valid(self, event_processor):
        """Test event validation with valid event."""
        event = PubSubEvent(
            event_type="create",
            file_path="/test/file.txt",
            timestamp=datetime.now()
        )
        
        # Should not raise exception
        event_processor._validate_event(event)
    
    def test_validate_event_invalid_type(self, event_processor):
        """Test event validation with invalid event type."""
        event = PubSubEvent(
            event_type="invalid_type",
            file_path="/test/file.txt",
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="Invalid event type"):
            event_processor._validate_event(event)
    
    def test_validate_event_missing_file_path(self, event_processor):
        """Test event validation with missing file path."""
        event = PubSubEvent(
            event_type="create",
            file_path="",
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="File path is required"):
            event_processor._validate_event(event)
    
    def test_validate_event_rename_missing_new_path(self, event_processor):
        """Test event validation for rename without new path."""
        event = PubSubEvent(
            event_type="rename",
            file_path="/test/file.txt",
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="New path is required"):
            event_processor._validate_event(event)
    
    def test_handle_change_permission(self, event_processor, db_manager, sample_file_record):
        """Test handling change_permission event."""
        # Insert initial record
        db_manager.insert_file_record(sample_file_record)
        
        # Create change permission event
        event = PubSubEvent(
            event_type="change_permission",
            file_path="/test/file.txt",
            timestamp=datetime(2023, 1, 2, 12, 0, 0),
            metadata={"permissions": "rwxrwxrwx"}
        )
        
        event_processor._handle_change_permission(event)
        
        # Verify permissions were updated
        updated_record = db_manager.get_file_record("/test/file.txt")
        assert updated_record is not None
        assert updated_record.permissions == "rwxrwxrwx"
        assert updated_record.last_modified == event.timestamp
    
    def test_handle_change_permission_file_not_found(self, event_processor):
        """Test handling change_permission event for non-existent file."""
        event = PubSubEvent(
            event_type="change_permission",
            file_path="/nonexistent/file.txt",
            timestamp=datetime.now(),
            metadata={"permissions": "rwxrwxrwx"}
        )
        
        # Should not raise exception, just log warning
        event_processor._handle_change_permission(event)
    
    def test_handle_delete(self, event_processor, db_manager, sample_file_record):
        """Test handling delete event."""
        # Insert initial record
        db_manager.insert_file_record(sample_file_record)
        
        # Verify record exists
        assert db_manager.get_file_record("/test/file.txt") is not None
        
        # Create delete event
        event = PubSubEvent(
            event_type="delete",
            file_path="/test/file.txt",
            timestamp=datetime.now()
        )
        
        event_processor._handle_delete(event)
        
        # Verify record was deleted
        assert db_manager.get_file_record("/test/file.txt") is None
    
    def test_handle_delete_file_not_found(self, event_processor):
        """Test handling delete event for non-existent file."""
        event = PubSubEvent(
            event_type="delete",
            file_path="/nonexistent/file.txt",
            timestamp=datetime.now()
        )
        
        # Should not raise exception, just log warning
        event_processor._handle_delete(event)
    
    def test_handle_create(self, event_processor, db_manager):
        """Test handling create event."""
        event = PubSubEvent(
            event_type="create",
            file_path="/new/file.txt",
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            metadata={
                "permissions": "rw-r--r--",
                "size": 2048,
                "file_type": "text/plain",
                "internal_id": "new-id-456"
            }
        )
        
        event_processor._handle_create(event)
        
        # Verify record was created
        created_record = db_manager.get_file_record("/new/file.txt")
        assert created_record is not None
        assert created_record.permissions == "rw-r--r--"
        assert created_record.size == 2048
        assert created_record.file_type == "text/plain"
        assert created_record.internal_id == "new-id-456"
        assert created_record.last_modified == event.timestamp
    
    def test_handle_create_file_exists(self, event_processor, db_manager, sample_file_record):
        """Test handling create event for existing file."""
        # Insert initial record
        db_manager.insert_file_record(sample_file_record)
        
        event = PubSubEvent(
            event_type="create",
            file_path="/test/file.txt",
            timestamp=datetime.now(),
            metadata={"permissions": "rw-r--r--", "size": 1024, "file_type": "text/plain"}
        )
        
        # Should not raise exception, just log warning
        event_processor._handle_create(event)
    
    def test_handle_create_insufficient_metadata(self, event_processor):
        """Test handling create event with insufficient metadata."""
        event = PubSubEvent(
            event_type="create",
            file_path="/new/file.txt",
            timestamp=datetime.now(),
            metadata=None
        )
        
        # Should not raise exception, just log error
        event_processor._handle_create(event)
    
    def test_handle_rename(self, event_processor, db_manager, sample_file_record):
        """Test handling rename event."""
        # Insert initial record
        db_manager.insert_file_record(sample_file_record)
        
        event = PubSubEvent(
            event_type="rename",
            file_path="/test/file.txt",
            new_path="/test/renamed_file.txt",
            timestamp=datetime(2023, 1, 2, 12, 0, 0)
        )
        
        event_processor._handle_rename(event)
        
        # Verify old record was deleted
        assert db_manager.get_file_record("/test/file.txt") is None
        
        # Verify new record was created
        renamed_record = db_manager.get_file_record("/test/renamed_file.txt")
        assert renamed_record is not None
        assert renamed_record.permissions == sample_file_record.permissions
        assert renamed_record.size == sample_file_record.size
        assert renamed_record.file_type == sample_file_record.file_type
        assert renamed_record.internal_id == sample_file_record.internal_id
        assert renamed_record.last_modified == event.timestamp
    
    def test_handle_rename_file_not_found(self, event_processor):
        """Test handling rename event for non-existent file."""
        event = PubSubEvent(
            event_type="rename",
            file_path="/nonexistent/file.txt",
            new_path="/test/renamed.txt",
            timestamp=datetime.now()
        )
        
        # Should not raise exception, just log warning
        event_processor._handle_rename(event)
    
    def test_handle_move(self, event_processor, db_manager, sample_file_record):
        """Test handling move event."""
        # Insert initial record
        db_manager.insert_file_record(sample_file_record)
        
        event = PubSubEvent(
            event_type="move",
            file_path="/test/file.txt",
            new_path="/moved/file.txt",
            timestamp=datetime(2023, 1, 2, 12, 0, 0),
            metadata={
                "permissions": "rwxrwxrwx",
                "size": 2048,
                "file_type": "application/octet-stream"
            }
        )
        
        event_processor._handle_move(event)
        
        # Verify old record was deleted
        assert db_manager.get_file_record("/test/file.txt") is None
        
        # Verify new record was created with updated metadata
        moved_record = db_manager.get_file_record("/moved/file.txt")
        assert moved_record is not None
        assert moved_record.permissions == "rwxrwxrwx"
        assert moved_record.size == 2048
        assert moved_record.file_type == "application/octet-stream"
        assert moved_record.internal_id == sample_file_record.internal_id
        assert moved_record.last_modified == event.timestamp
    
    def test_handle_move_file_not_found(self, event_processor):
        """Test handling move event for non-existent file."""
        event = PubSubEvent(
            event_type="move",
            file_path="/nonexistent/file.txt",
            new_path="/test/moved.txt",
            timestamp=datetime.now()
        )
        
        # Should not raise exception, just log warning
        event_processor._handle_move(event)
    
    def test_extract_permissions_from_metadata(self, event_processor):
        """Test extracting permissions from metadata."""
        # Test with 'permissions' key
        metadata1 = {"permissions": "rwxrwxrwx"}
        assert event_processor._extract_permissions_from_metadata(metadata1) == "rwxrwxrwx"
        
        # Test with 'permission' key
        metadata2 = {"permission": "rw-r--r--"}
        assert event_processor._extract_permissions_from_metadata(metadata2) == "rw-r--r--"
        
        # Test with 'perms' key
        metadata3 = {"perms": "755"}
        assert event_processor._extract_permissions_from_metadata(metadata3) == "755"
        
        # Test with 'access' key
        metadata4 = {"access": "read-write"}
        assert event_processor._extract_permissions_from_metadata(metadata4) == "read-write"
        
        # Test with no permissions
        metadata5 = {"size": 1024}
        assert event_processor._extract_permissions_from_metadata(metadata5) is None
        
        # Test with None metadata
        assert event_processor._extract_permissions_from_metadata(None) is None
    
    def test_create_file_record_from_event(self, event_processor):
        """Test creating file record from event."""
        event = PubSubEvent(
            event_type="create",
            file_path="/test/file.txt",
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            metadata={
                "permissions": "rw-r--r--",
                "size": "1024",
                "file_type": "text/plain",
                "internal_id": "test-id"
            }
        )
        
        record = event_processor._create_file_record_from_event(event)
        
        assert record is not None
        assert record.file_path == "/test/file.txt"
        assert record.permissions == "rw-r--r--"
        assert record.size == 1024
        assert record.file_type == "text/plain"
        assert record.internal_id == "test-id"
        assert record.last_modified == event.timestamp
    
    def test_create_file_record_from_event_no_metadata(self, event_processor):
        """Test creating file record from event with no metadata."""
        event = PubSubEvent(
            event_type="create",
            file_path="/test/file.txt",
            timestamp=datetime.now(),
            metadata=None
        )
        
        record = event_processor._create_file_record_from_event(event)
        assert record is None
    
    def test_create_file_record_from_event_invalid_size(self, event_processor):
        """Test creating file record from event with invalid size."""
        event = PubSubEvent(
            event_type="create",
            file_path="/test/file.txt",
            timestamp=datetime.now(),
            metadata={
                "permissions": "rw-r--r--",
                "size": "invalid",
                "file_type": "text/plain"
            }
        )
        
        record = event_processor._create_file_record_from_event(event)
        assert record is None
    
    def test_process_events_integration(self, event_processor, db_manager):
        """Test processing multiple events in sequence."""
        # Create events in chronological order
        events = [
            PubSubEvent(
                event_type="create",
                file_path="/test/file1.txt",
                timestamp=datetime(2023, 1, 1, 12, 0, 0),
                metadata={"permissions": "rw-r--r--", "size": 1024, "file_type": "text/plain"}
            ),
            PubSubEvent(
                event_type="create",
                file_path="/test/file2.txt",
                timestamp=datetime(2023, 1, 1, 12, 1, 0),
                metadata={"permissions": "rw-r--r--", "size": 2048, "file_type": "text/plain"}
            ),
            PubSubEvent(
                event_type="change_permission",
                file_path="/test/file1.txt",
                timestamp=datetime(2023, 1, 1, 12, 2, 0),
                metadata={"permissions": "rwxrwxrwx"}
            ),
            PubSubEvent(
                event_type="rename",
                file_path="/test/file2.txt",
                new_path="/test/renamed_file2.txt",
                timestamp=datetime(2023, 1, 1, 12, 3, 0)
            ),
            PubSubEvent(
                event_type="delete",
                file_path="/test/file1.txt",
                timestamp=datetime(2023, 1, 1, 12, 4, 0)
            )
        ]
        
        result = event_processor.process_events(events)
        
        # Verify event counts
        assert result['create'] == 2
        assert result['change_permission'] == 1
        assert result['rename'] == 1
        assert result['delete'] == 1
        assert result['errors'] == 0
        
        # Verify final database state
        all_records = db_manager.get_all_records()
        assert len(all_records) == 1
        
        remaining_record = all_records[0]
        assert remaining_record.file_path == "/test/renamed_file2.txt"
        assert remaining_record.size == 2048
    
    def test_process_events_with_errors(self, event_processor):
        """Test processing events with validation errors."""
        events = [
            PubSubEvent(
                event_type="create",
                file_path="/test/file1.txt",
                timestamp=datetime.now(),
                metadata={"permissions": "rw-r--r--", "size": 1024, "file_type": "text/plain"}
            ),
            PubSubEvent(
                event_type="invalid_type",
                file_path="/test/file2.txt",
                timestamp=datetime.now()
            ),
            PubSubEvent(
                event_type="rename",
                file_path="/test/file3.txt",
                timestamp=datetime.now()
                # Missing new_path
            )
        ]
        
        result = event_processor.process_events(events)
        
        # Should have 1 successful create and 2 errors
        assert result['create'] == 1
        assert result['errors'] == 2