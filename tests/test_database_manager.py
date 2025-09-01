"""
Tests for the DatabaseManager class.
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path

from sync_service.models.data_models import FileRecord
from sync_service.services.database_manager import DatabaseManager


def test_database_manager_basic_operations():
    """Test basic CRUD operations of DatabaseManager."""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(db_path)
        
        # Create a test file record
        test_record = FileRecord(
            file_path="/test/file.txt",
            permissions="rw-r--r--",
            size=1024,
            file_type="text/plain",
            last_modified=datetime.now(),
            internal_id="test-id-123"
        )
        
        # Test insert
        db_manager.insert_file_record(test_record)
        
        # Test get
        retrieved_record = db_manager.get_file_record("/test/file.txt")
        assert retrieved_record is not None
        assert retrieved_record.file_path == test_record.file_path
        assert retrieved_record.permissions == test_record.permissions
        assert retrieved_record.size == test_record.size
        assert retrieved_record.file_type == test_record.file_type
        assert retrieved_record.internal_id == test_record.internal_id
        
        # Test get all records
        all_records = db_manager.get_all_records()
        assert len(all_records) == 1
        assert all_records[0].file_path == test_record.file_path
        
        # Test update
        test_record.permissions = "rwxr-xr-x"
        test_record.size = 2048
        db_manager.update_file_record(test_record)
        
        updated_record = db_manager.get_file_record("/test/file.txt")
        assert updated_record.permissions == "rwxr-xr-x"
        assert updated_record.size == 2048
        
        # Test record count
        assert db_manager.get_record_count() == 1
        
        # Test delete
        db_manager.delete_file_record("/test/file.txt")
        deleted_record = db_manager.get_file_record("/test/file.txt")
        assert deleted_record is None
        assert db_manager.get_record_count() == 0
        
        print("✓ All basic database operations work correctly")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_csv_export_import():
    """Test CSV export and import functionality."""
    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_csv:
        csv_path = tmp_csv.name
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(db_path)
        
        # Create test records
        records = [
            FileRecord(
                file_path="/test/file1.txt",
                permissions="rw-r--r--",
                size=1024,
                file_type="text/plain",
                last_modified=datetime(2023, 1, 1, 12, 0, 0),
                internal_id="id-1"
            ),
            FileRecord(
                file_path="/test/file2.jpg",
                permissions="rw-r--r--",
                size=2048,
                file_type="image/jpeg",
                last_modified=datetime(2023, 1, 2, 12, 0, 0),
                internal_id="id-2"
            )
        ]
        
        # Insert records
        for record in records:
            db_manager.insert_file_record(record)
        
        # Export to CSV
        db_manager.export_to_csv(csv_path)
        
        # Verify CSV file exists and has content
        assert os.path.exists(csv_path)
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "/test/file1.txt" in content
            assert "/test/file2.jpg" in content
            assert "text/plain" in content
            assert "image/jpeg" in content
        
        # Clear database and import from CSV
        db_manager.clear_all_records()
        assert db_manager.get_record_count() == 0
        
        db_manager.import_from_csv(csv_path)
        
        # Verify import worked
        imported_records = db_manager.get_all_records()
        assert len(imported_records) == 2
        
        # Check specific records
        file1_record = db_manager.get_file_record("/test/file1.txt")
        assert file1_record is not None
        assert file1_record.size == 1024
        assert file1_record.file_type == "text/plain"
        assert file1_record.internal_id == "id-1"
        
        file2_record = db_manager.get_file_record("/test/file2.jpg")
        assert file2_record is not None
        assert file2_record.size == 2048
        assert file2_record.file_type == "image/jpeg"
        assert file2_record.internal_id == "id-2"
        
        print("✓ CSV export and import work correctly")
        
    finally:
        # Clean up
        for path in [db_path, csv_path]:
            if os.path.exists(path):
                os.unlink(path)


def test_upsert_functionality():
    """Test upsert (insert or update) functionality."""
    import uuid
    db_path = f"/tmp/test_upsert_{uuid.uuid4().hex}.db"
    
    try:
        db_manager = DatabaseManager(db_path)
        
        # Create a test record
        test_record = FileRecord(
            file_path="/test/upsert.txt",
            permissions="rw-r--r--",
            size=1024,
            file_type="text/plain",
            last_modified=datetime.now(),
            internal_id="upsert-id"
        )
        
        # First upsert should insert
        db_manager.upsert_file_record(test_record)
        assert db_manager.get_record_count() == 1
        
        # Second upsert should update
        test_record.size = 2048
        test_record.permissions = "rwxr-xr-x"
        db_manager.upsert_file_record(test_record)
        assert db_manager.get_record_count() == 1  # Still only one record
        
        # Verify the update worked
        updated_record = db_manager.get_file_record("/test/upsert.txt")
        assert updated_record.size == 2048
        assert updated_record.permissions == "rwxr-xr-x"
        
        print("✓ Upsert functionality works correctly")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    test_database_manager_basic_operations()
    test_csv_export_import()
    test_upsert_functionality()
    print("\n✅ All DatabaseManager tests passed!")