"""
Tests for CSV processor functionality.
"""
import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from sync_service.services.csv_processor import CSVProcessor
from sync_service.models.data_models import FileRecord, FileOperation


class TestCSVProcessor:
    """Test cases for CSV processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.csv_processor = CSVProcessor()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp directory
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
            ),
            FileRecord(
                file_path="/test/file3.pdf",
                permissions="rw-r--r--",
                size=4096,
                file_type="application/pdf",
                last_modified=datetime(2024, 1, 3, 12, 0, 0),
                internal_id="id3"
            )
        ]
    
    def test_export_records_to_csv(self):
        """Test exporting records to CSV."""
        records = self.create_sample_records()
        csv_path = os.path.join(self.temp_dir, "test_export.csv")
        
        self.csv_processor.export_records_to_csv(records, csv_path)
        
        # Verify file was created
        assert Path(csv_path).exists()
        
        # Verify content
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "/test/file1.txt" in content
            assert "/test/file2.jpg" in content
            assert "/test/file3.pdf" in content
            assert "rw-r--r--" in content
    
    def test_export_empty_records_to_csv(self):
        """Test exporting empty records list to CSV."""
        csv_path = os.path.join(self.temp_dir, "test_empty.csv")
        
        self.csv_processor.export_records_to_csv([], csv_path)
        
        # Verify file was created with headers
        assert Path(csv_path).exists()
        
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "file_path" in content
            assert "permissions" in content
    
    def test_import_records_from_csv(self):
        """Test importing records from CSV."""
        # First export some records
        records = self.create_sample_records()
        csv_path = os.path.join(self.temp_dir, "test_import.csv")
        self.csv_processor.export_records_to_csv(records, csv_path)
        
        # Then import them back
        imported_records = self.csv_processor.import_records_from_csv(csv_path)
        
        # Verify imported records match original
        assert len(imported_records) == len(records)
        
        for original, imported in zip(records, imported_records):
            assert original.file_path == imported.file_path
            assert original.permissions == imported.permissions
            assert original.size == imported.size
            assert original.file_type == imported.file_type
            assert original.internal_id == imported.internal_id
    
    def test_import_nonexistent_csv(self):
        """Test importing from non-existent CSV file."""
        csv_path = os.path.join(self.temp_dir, "nonexistent.csv")
        
        with pytest.raises(FileNotFoundError):
            self.csv_processor.import_records_from_csv(csv_path)
    
    def test_compare_csv_files_no_changes(self):
        """Test comparing identical CSV files."""
        records = self.create_sample_records()
        
        old_csv = os.path.join(self.temp_dir, "old.csv")
        new_csv = os.path.join(self.temp_dir, "new.csv")
        
        self.csv_processor.export_records_to_csv(records, old_csv)
        self.csv_processor.export_records_to_csv(records, new_csv)
        
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Should be no operations for identical files
        assert len(operations) == 0
    
    def test_compare_csv_files_with_deletions(self):
        """Test comparing CSV files with deleted records."""
        old_records = self.create_sample_records()
        new_records = old_records[:-1]  # Remove last record
        
        old_csv = os.path.join(self.temp_dir, "old.csv")
        new_csv = os.path.join(self.temp_dir, "new.csv")
        
        self.csv_processor.export_records_to_csv(old_records, old_csv)
        self.csv_processor.export_records_to_csv(new_records, new_csv)
        
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Should have one delete operation
        assert len(operations) == 1
        assert operations[0].operation_type == 'delete'
        assert operations[0].file_path == "/test/file3.pdf"
    
    def test_compare_csv_files_with_additions(self):
        """Test comparing CSV files with added records."""
        old_records = self.create_sample_records()[:-1]  # Remove last record
        new_records = self.create_sample_records()
        
        old_csv = os.path.join(self.temp_dir, "old.csv")
        new_csv = os.path.join(self.temp_dir, "new.csv")
        
        self.csv_processor.export_records_to_csv(old_records, old_csv)
        self.csv_processor.export_records_to_csv(new_records, new_csv)
        
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Should have one create operation
        assert len(operations) == 1
        assert operations[0].operation_type == 'create'
        assert operations[0].file_path == "/test/file3.pdf"
    
    def test_compare_csv_files_with_updates(self):
        """Test comparing CSV files with updated records."""
        old_records = self.create_sample_records()
        new_records = self.create_sample_records()
        
        # Modify one record
        new_records[1].size = 3072  # Change size
        new_records[1].permissions = "rwxr--r--"  # Change permissions
        
        old_csv = os.path.join(self.temp_dir, "old.csv")
        new_csv = os.path.join(self.temp_dir, "new.csv")
        
        self.csv_processor.export_records_to_csv(old_records, old_csv)
        self.csv_processor.export_records_to_csv(new_records, new_csv)
        
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Should have one update operation
        assert len(operations) == 1
        assert operations[0].operation_type == 'update'
        assert operations[0].file_path == "/test/file2.jpg"
        assert operations[0].metadata['size'] == 3072
        assert operations[0].metadata['permissions'] == "rwxr--r--"
    
    def test_compare_empty_csv_files(self):
        """Test comparing empty CSV files."""
        old_csv = os.path.join(self.temp_dir, "old_empty.csv")
        new_csv = os.path.join(self.temp_dir, "new_empty.csv")
        
        self.csv_processor.export_records_to_csv([], old_csv)
        self.csv_processor.export_records_to_csv([], new_csv)
        
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Should be no operations for empty files
        assert len(operations) == 0
    
    def test_compare_csv_old_empty_new_has_records(self):
        """Test comparing empty old CSV with new CSV that has records."""
        records = self.create_sample_records()
        
        old_csv = os.path.join(self.temp_dir, "old_empty.csv")
        new_csv = os.path.join(self.temp_dir, "new_full.csv")
        
        self.csv_processor.export_records_to_csv([], old_csv)
        self.csv_processor.export_records_to_csv(records, new_csv)
        
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Should have create operations for all records
        assert len(operations) == len(records)
        for operation in operations:
            assert operation.operation_type == 'create'
    
    def test_compare_csv_old_has_records_new_empty(self):
        """Test comparing old CSV with records to empty new CSV."""
        records = self.create_sample_records()
        
        old_csv = os.path.join(self.temp_dir, "old_full.csv")
        new_csv = os.path.join(self.temp_dir, "new_empty.csv")
        
        self.csv_processor.export_records_to_csv(records, old_csv)
        self.csv_processor.export_records_to_csv([], new_csv)
        
        operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
        
        # Should have delete operations for all records
        assert len(operations) == len(records)
        for operation in operations:
            assert operation.operation_type == 'delete'
    
    def test_generate_operations_from_records(self):
        """Test generating operations from FileRecord lists."""
        old_records = self.create_sample_records()
        new_records = self.create_sample_records()
        
        # Modify records to test different operation types
        new_records = new_records[:-1]  # Delete last record
        new_records[0].size = 2048  # Update first record
        new_records.append(FileRecord(  # Add new record
            file_path="/test/file4.doc",
            permissions="rw-r--r--",
            size=8192,
            file_type="application/msword",
            last_modified=datetime(2024, 1, 4, 12, 0, 0),
            internal_id="id4"
        ))
        
        operations = self.csv_processor.generate_operations_from_records(old_records, new_records)
        
        # Should have delete, update, and create operations
        operation_types = [op.operation_type for op in operations]
        assert 'delete' in operation_types
        assert 'update' in operation_types
        assert 'create' in operation_types
    
    def test_validate_csv_format_valid(self):
        """Test validating a properly formatted CSV file."""
        records = self.create_sample_records()
        csv_path = os.path.join(self.temp_dir, "valid.csv")
        
        self.csv_processor.export_records_to_csv(records, csv_path)
        
        assert self.csv_processor.validate_csv_format(csv_path) is True
    
    def test_validate_csv_format_nonexistent(self):
        """Test validating a non-existent CSV file."""
        csv_path = os.path.join(self.temp_dir, "nonexistent.csv")
        
        assert self.csv_processor.validate_csv_format(csv_path) is False
    
    def test_get_csv_summary(self):
        """Test getting summary information about a CSV file."""
        records = self.create_sample_records()
        csv_path = os.path.join(self.temp_dir, "summary_test.csv")
        
        self.csv_processor.export_records_to_csv(records, csv_path)
        
        summary = self.csv_processor.get_csv_summary(csv_path)
        
        assert summary['total_records'] == 3
        assert summary['total_size'] == 1024 + 2048 + 4096
        assert 'file_path' in summary['columns']
        assert summary['has_internal_ids'] == 3
    
    def test_get_csv_summary_nonexistent(self):
        """Test getting summary for non-existent CSV file."""
        csv_path = os.path.join(self.temp_dir, "nonexistent.csv")
        
        with pytest.raises(FileNotFoundError):
            self.csv_processor.get_csv_summary(csv_path)