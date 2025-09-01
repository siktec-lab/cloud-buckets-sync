#!/usr/bin/env python3
"""
Demo script for incremental sync workflow functionality.

This script demonstrates the complete incremental sync workflow including:
- Event retrieval and processing
- CSV state comparison
- Operation execution
- Result reporting

Usage:
    python examples/demo_incremental_sync.py
"""

import os
import sys
import tempfile
from datetime import datetime
from io import BytesIO

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sync_service.services.sync_service import SyncService
from sync_service.models.config import SyncConfig, S3Config
from sync_service.models.data_models import PubSubEvent, FileRecord


def create_demo_config():
    """Create a demo configuration for testing."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    return SyncConfig(
        customer_s3=S3Config(
            endpoint="http://localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket="customer-bucket"
        ),
        mock_api_url="http://localhost:8000",
        file_manager_api_url="http://localhost:8001",
        database_path=temp_db.name,
        sync_interval=300,
        live_reload=False
    ), temp_db.name


def setup_initial_data(sync_service):
    """Set up some initial data in the database for demo purposes."""
    print("Setting up initial database records...")
    
    # Create some initial file records
    initial_records = [
        FileRecord(
            file_path="documents/report.pdf",
            permissions="rw-r--r--",
            size=1024000,
            file_type="application/pdf",
            last_modified=datetime(2024, 1, 1, 10, 0, 0),
            internal_id="file_001"
        ),
        FileRecord(
            file_path="images/photo.jpg",
            permissions="rw-r--r--",
            size=2048000,
            file_type="image/jpeg",
            last_modified=datetime(2024, 1, 2, 11, 0, 0),
            internal_id="file_002"
        ),
        FileRecord(
            file_path="data/spreadsheet.xlsx",
            permissions="rw-rw-r--",
            size=512000,
            file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            last_modified=datetime(2024, 1, 3, 12, 0, 0),
            internal_id="file_003"
        )
    ]
    
    for record in initial_records:
        sync_service.database_manager.upsert_file_record(record)
    
    print(f"Created {len(initial_records)} initial records")
    return len(initial_records)


def create_demo_events():
    """Create demo pub/sub events for testing."""
    return [
        PubSubEvent(
            event_type="create",
            file_path="documents/new_report.pdf",
            metadata={
                "size": 1500000,
                "file_type": "application/pdf",
                "permissions": "rw-r--r--",
                "internal_id": "file_004"
            },
            timestamp=datetime.now()
        ),
        PubSubEvent(
            event_type="change_permission",
            file_path="data/spreadsheet.xlsx",
            metadata={
                "permissions": "rw-rw-rw-"
            },
            timestamp=datetime.now()
        ),
        PubSubEvent(
            event_type="delete",
            file_path="images/photo.jpg",
            timestamp=datetime.now()
        ),
        PubSubEvent(
            event_type="rename",
            file_path="documents/report.pdf",
            new_path="documents/annual_report.pdf",
            timestamp=datetime.now()
        )
    ]


def mock_infrastructure_responses(sync_service, demo_events):
    """Mock infrastructure API responses for demo."""
    from unittest.mock import Mock
    
    # Mock get_pub_sub_events to return our demo events
    sync_service.infrastructure_api.get_pub_sub_events = Mock(return_value=demo_events)
    
    # Mock report_results to simulate successful reporting
    sync_service.infrastructure_api.report_results = Mock(return_value={"status": "success"})
    
    # Mock S3 operations for create events
    def mock_get_object_stream(key):
        return BytesIO(b"Mock file content for " + key.encode())
    
    sync_service.s3_manager.get_object_stream = Mock(side_effect=mock_get_object_stream)
    
    # Mock save_to_disk for create operations
    def mock_save_to_disk(**kwargs):
        return {"internal_id": f"file_{hash(kwargs['file_path']) % 1000:03d}"}
    
    sync_service.infrastructure_api.save_to_disk = Mock(side_effect=mock_save_to_disk)
    
    print("Mocked infrastructure API responses")


def demonstrate_incremental_sync():
    """Demonstrate the complete incremental sync workflow."""
    print("=" * 60)
    print("S3 Sync Service - Incremental Sync Workflow Demo")
    print("=" * 60)
    
    # Create configuration and sync service
    config, temp_db_path = create_demo_config()
    
    try:
        # Initialize sync service
        print("\n1. Initializing sync service...")
        sync_service = SyncService(config)
        
        # Set up initial data
        print("\n2. Setting up initial database state...")
        initial_count = setup_initial_data(sync_service)
        
        # Show initial state
        print(f"\nInitial database state: {sync_service.database_manager.get_record_count()} records")
        
        # Create demo events
        print("\n3. Creating demo pub/sub events...")
        demo_events = create_demo_events()
        print(f"Created {len(demo_events)} demo events:")
        for i, event in enumerate(demo_events, 1):
            print(f"  {i}. {event.event_type}: {event.file_path}")
            if event.new_path:
                print(f"     -> {event.new_path}")
        
        # Mock infrastructure responses
        print("\n4. Setting up mock infrastructure responses...")
        mock_infrastructure_responses(sync_service, demo_events)
        
        # Mock connection tests to pass
        from unittest.mock import Mock
        sync_service._test_connections = Mock(return_value=True)
        
        # Run incremental sync
        print("\n5. Running incremental sync workflow...")
        print("-" * 40)
        
        result = sync_service.run_incremental_sync()
        
        print("-" * 40)
        print("Incremental sync completed!")
        
        # Display results
        print("\n6. Sync Results:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Duration: {result.get('duration', 0):.2f} seconds")
        print(f"   Events processed: {result.get('events_processed', 0)}")
        print(f"   Operations processed: {result.get('operations_processed', 0)}")
        print(f"   Operations failed: {result.get('operations_failed', 0)}")
        
        if result.get('event_counts'):
            print(f"   Event breakdown: {result['event_counts']}")
        
        if result.get('errors'):
            print(f"   Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"     - {error}")
        
        # Show final database state
        final_count = sync_service.database_manager.get_record_count()
        print(f"\nFinal database state: {final_count} records")
        print(f"Net change: {final_count - initial_count:+d} records")
        
        print("\n7. Workflow Components Demonstrated:")
        print("   ✓ CSV state export (old and new)")
        print("   ✓ Event retrieval from infrastructure API")
        print("   ✓ Event processing and database updates")
        print("   ✓ CSV diff processing to identify operations")
        print("   ✓ Operation execution (create, update, delete, move)")
        print("   ✓ Result reporting to infrastructure endpoints")
        print("   ✓ Temporary file cleanup")
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nDemo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up temporary database
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
            print(f"\nCleaned up temporary database: {temp_db_path}")


if __name__ == "__main__":
    demonstrate_incremental_sync()