#!/usr/bin/env python3
"""
Demo script showing CSV processing and diff engine functionality.
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path

from sync_service.services.csv_processor import CSVProcessor
from sync_service.services.database_manager import DatabaseManager
from sync_service.models.data_models import FileRecord


def main():
    """Demonstrate CSV processing functionality."""
    print("=== CSV Processing and Diff Engine Demo ===\n")
    
    # Create temporary directory for demo
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Initialize components
        db_path = os.path.join(temp_dir, "demo.db")
        database_manager = DatabaseManager(db_path)
        csv_processor = CSVProcessor()
        
        print("\n1. Creating sample file records...")
        
        # Create initial records
        initial_records = [
            FileRecord(
                file_path="/documents/report.pdf",
                permissions="rw-r--r--",
                size=1024000,
                file_type="application/pdf",
                last_modified=datetime(2024, 1, 1, 12, 0, 0),
                internal_id="pdf_001"
            ),
            FileRecord(
                file_path="/images/photo.jpg",
                permissions="rw-r--r--",
                size=2048000,
                file_type="image/jpeg",
                last_modified=datetime(2024, 1, 2, 12, 0, 0),
                internal_id="img_001"
            ),
            FileRecord(
                file_path="/data/spreadsheet.xlsx",
                permissions="rw-r--r--",
                size=512000,
                file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                last_modified=datetime(2024, 1, 3, 12, 0, 0),
                internal_id="xls_001"
            )
        ]
        
        # Insert records into database
        for record in initial_records:
            database_manager.insert_file_record(record)
        
        print(f"Inserted {len(initial_records)} records into database")
        
        print("\n2. Exporting initial state to CSV...")
        
        # Export initial state
        old_csv = os.path.join(temp_dir, "old_state.csv")
        database_manager.export_to_csv(old_csv)
        
        print(f"Exported to: {old_csv}")
        
        # Show CSV summary
        summary = csv_processor.get_csv_summary(old_csv)
        print(f"CSV Summary: {summary['total_records']} records, {summary['total_size']} bytes total")
        
        print("\n3. Making changes to simulate incremental sync...")
        
        # Simulate changes:
        # 1. Update existing record (change size and permissions)
        updated_record = initial_records[0]  # report.pdf
        updated_record.size = 1536000  # Increased size
        updated_record.permissions = "rwxr--r--"  # Changed permissions
        database_manager.update_file_record(updated_record)
        print("  - Updated report.pdf (size and permissions changed)")
        
        # 2. Add new record
        new_record = FileRecord(
            file_path="/videos/presentation.mp4",
            permissions="rw-r--r--",
            size=10240000,
            file_type="video/mp4",
            last_modified=datetime(2024, 1, 4, 12, 0, 0),
            internal_id="vid_001"
        )
        database_manager.insert_file_record(new_record)
        print("  - Added presentation.mp4")
        
        # 3. Delete existing record
        database_manager.delete_file_record("/data/spreadsheet.xlsx")
        print("  - Deleted spreadsheet.xlsx")
        
        print("\n4. Exporting new state to CSV...")
        
        # Export new state
        new_csv = os.path.join(temp_dir, "new_state.csv")
        database_manager.export_to_csv(new_csv)
        
        print(f"Exported to: {new_csv}")
        
        print("\n5. Processing CSV diff to identify changes...")
        
        # Process diff
        operations = csv_processor.compare_csv_files(old_csv, new_csv)
        
        print(f"Found {len(operations)} operations:")
        
        # Group operations by type
        operation_counts = {}
        for op in operations:
            operation_counts[op.operation_type] = operation_counts.get(op.operation_type, 0) + 1
        
        for op_type, count in operation_counts.items():
            print(f"  - {op_type}: {count} operations")
        
        print("\n6. Detailed operation analysis:")
        
        for i, operation in enumerate(operations, 1):
            print(f"\nOperation {i}:")
            print(f"  Type: {operation.operation_type}")
            print(f"  File: {operation.file_path}")
            
            if operation.new_path:
                print(f"  New Path: {operation.new_path}")
            
            if operation.metadata:
                print("  Metadata:")
                for key, value in operation.metadata.items():
                    if key in ['size', 'permissions', 'file_type']:
                        print(f"    {key}: {value}")
        
        print("\n7. Demonstrating in-memory record comparison...")
        
        # Alternative approach: compare records directly without CSV files
        old_records = [
            FileRecord(
                file_path="/test/file1.txt",
                permissions="rw-r--r--",
                size=1000,
                file_type="text/plain",
                last_modified=datetime(2024, 1, 1),
                internal_id="test1"
            ),
            FileRecord(
                file_path="/test/file2.txt",
                permissions="rw-r--r--",
                size=2000,
                file_type="text/plain",
                last_modified=datetime(2024, 1, 2),
                internal_id="test2"
            )
        ]
        
        new_records = [
            FileRecord(
                file_path="/test/file1.txt",
                permissions="rwxr--r--",  # Changed permissions
                size=1500,  # Changed size
                file_type="text/plain",
                last_modified=datetime(2024, 1, 1),
                internal_id="test1"
            ),
            FileRecord(
                file_path="/test/file3.txt",  # New file
                permissions="rw-r--r--",
                size=3000,
                file_type="text/plain",
                last_modified=datetime(2024, 1, 3),
                internal_id="test3"
            )
            # file2.txt is deleted (not in new_records)
        ]
        
        memory_operations = csv_processor.generate_operations_from_records(old_records, new_records)
        
        print(f"In-memory comparison found {len(memory_operations)} operations:")
        for op in memory_operations:
            print(f"  - {op.operation_type}: {op.file_path}")
        
        print("\n8. CSV validation and utilities...")
        
        # Validate CSV format
        is_valid = csv_processor.validate_csv_format(new_csv)
        print(f"CSV format validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Get detailed summary
        detailed_summary = csv_processor.get_csv_summary(new_csv)
        print(f"Detailed CSV summary:")
        print(f"  Total records: {detailed_summary['total_records']}")
        print(f"  Total size: {detailed_summary['total_size']} bytes")
        print(f"  File types: {detailed_summary['file_types']}")
        print(f"  Records with internal IDs: {detailed_summary['has_internal_ids']}")
        
        print(f"\n=== Demo completed successfully! ===")
        print(f"Temporary files created in: {temp_dir}")
        print("You can examine the CSV files to see the exported data.")
        
    except Exception as e:
        print(f"Demo failed with error: {str(e)}")
        raise
    
    finally:
        # Clean up (optional - comment out to keep files for inspection)
        # import shutil
        # shutil.rmtree(temp_dir, ignore_errors=True)
        pass


if __name__ == "__main__":
    main()