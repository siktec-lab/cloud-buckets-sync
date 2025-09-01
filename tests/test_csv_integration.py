"""
Integration tests for CSV processing functionality with sync service.
"""
import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from sync_service.services.csv_processor import CSVProcessor
from sync_service.services.database_manager import DatabaseManager
from sync_service.models.data_models import FileRecord


class TestCSVIntegration:
    """Test CSV processing integration with database manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.database_manager = DatabaseManager(self.db_path)
        self.csv_processor = CSVProcessor()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_sample_records(self) -> list[FileRecord]:
        """Create sample file records for testing."""
        return [
            FileRecord(
                file_path="/test/file1.txt",
                permissions="rw-r--r--",
                size=1024,
                file_type="text/plain",
                last_modified=datetime(2024, 1, 1, 12, 0, 0),
                internal_id="id1"
            ),
            FileRecord(
                file_path="/test/file2.jpg",
                permissions="rw-r--r--",
                size=2048,
                file_type="image/jpeg",
                last_modified=datetime(2024, 1, 2, 12, 0, 0),
                internal_id="id2"
            )
        ]
    
    def test_database_csv_export_import_roundtrip(self):
        """Test exporting from database to CSV and importing back."""
        # Insert records into database
        records = self.create_sample_records()
        for record in records:
            self.database_manager.insert_file_record(record)
        
        # Export to CSV
        csv_path = os.path.join(self.temp_dir, "export.csv")
        self.database_manager.export_to_csv(csv_path)
        
        # Verify CSV was created
        assert Path(csv_path).exists()
        
        # Import records from CSV using CSV processor
        imported_records = self.csv_processor.import_records_from_csv(csv_path)
        
        # Verify imported records match original
        assert len(imported_records) == len(records)
        
        for original, imported in zip(records, imported_records):
            assert original.file_path == imported.file_path
            assert original.permissions == imported.permissions
            assert original.size == imported.size
            assert original.file_type == imported.file_type
            assert original.internal_id == imported.internal_id
    
    def test_csv_diff_with_database_changes(self):
        """Test CSV diff functionality with actual database changes."""
        # Initial state
        initial_records = self.create_sample_records()
        for record in initial_records:
            self.database_manager.insert_file_record(record)
        
        # Export initial state
        old_csv = os.path.join(self.temp_dir, "old_state.csv")
        self.database_manager.export_to_csv(old_csv)
        
        # Make changes to database
        # 1. Update existing record
        updated_record = initial_records[0]
        updated_record.size = 2048
        updated_record.permissions = "rwxr--r--"
        self.database_manager.update_file_record(updated_record)
        
        # 2. Add new record
        new_record = FileRecord(
            file_path="/test/file3.pdf",
            permissions="rw-r--r--",
            size=4096,
            file_type="application/pdf",
            last_modified=datetime(2024, 1, 3, 12, 0, 0),
            internal_id="id3"
        )
        self.database_manager.insert_file_record(new_record)
        
        # 3. Delete existing record
        self.database_manager.delete_file_record("/test/file2.jpg")
        
        # Export new state
        new_csv = os.path.join(self.temp_dir, "new_state.csv")
        self.database_manager.export_to_csv(new_csv)
        
        # Process diff
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Verify operations
        operation_types = [op.operation_type for op in operations]
        assert 'update' in operation_types  # file1.txt was updated
        assert 'create' in operation_types  # file3.pdf was created
        assert 'delete' in operation_types  # file2.jpg was deleted
        
        # Verify specific operations
        update_ops = [op for op in operations if op.operation_type == 'update']
        create_ops = [op for op in operations if op.operation_type == 'create']
        delete_ops = [op for op in operations if op.operation_type == 'delete']
        
        assert len(update_ops) == 1
        assert update_ops[0].file_path == "/test/file1.txt"
        assert update_ops[0].metadata['size'] == 2048
        
        assert len(create_ops) == 1
        assert create_ops[0].file_path == "/test/file3.pdf"
        
        assert len(delete_ops) == 1
        assert delete_ops[0].file_path == "/test/file2.jpg"
    
    def test_csv_validation_with_database_export(self):
        """Test CSV validation with database-exported files."""
        # Insert records and export
        records = self.create_sample_records()
        for record in records:
            self.database_manager.insert_file_record(record)
        
        csv_path = os.path.join(self.temp_dir, "validation_test.csv")
        self.database_manager.export_to_csv(csv_path)
        
        # Validate CSV format
        assert self.csv_processor.validate_csv_format(csv_path) is True
        
        # Get CSV summary
        summary = self.csv_processor.get_csv_summary(csv_path)
        
        assert summary['total_records'] == 2
        assert summary['total_size'] == 1024 + 2048
        assert 'file_path' in summary['columns']
        assert summary['has_internal_ids'] == 2
    
    def test_empty_database_csv_operations(self):
        """Test CSV operations with empty database."""
        # Export empty database
        csv_path = os.path.join(self.temp_dir, "empty.csv")
        self.database_manager.export_to_csv(csv_path)
        
        # Verify CSV was created with headers
        assert Path(csv_path).exists()
        
        # Import from empty CSV
        imported_records = self.csv_processor.import_records_from_csv(csv_path)
        assert len(imported_records) == 0
        
        # Validate empty CSV
        assert self.csv_processor.validate_csv_format(csv_path) is True
        
        # Get summary of empty CSV
        summary = self.csv_processor.get_csv_summary(csv_path)
        assert summary['total_records'] == 0
        assert summary['total_size'] == 0