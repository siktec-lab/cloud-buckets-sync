#!/usr/bin/env python3
"""
Demo script showing how to use the EventProcessor with Infrastructure API.

This example demonstrates:
1. Getting pubSubFullList events from the infrastructure API
2. Processing events with the EventProcessor
3. Updating the SQLite database based on events
4. Reporting results back to the infrastructure API
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sync_service.models.data_models import PubSubEvent, FileRecord
from sync_service.services.database_manager import DatabaseManager
from sync_service.services.event_processor import EventProcessor
from sync_service.clients.infrastructure_api import InfrastructureAPI


def setup_logging():
    """Configure logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_database(db_manager: DatabaseManager):
    """Create sample data in the database for demonstration."""
    print("Creating sample database records...")
    
    sample_records = [
        FileRecord(
            file_path="/documents/report.pdf",
            permissions="rw-r--r--",
            size=1024000,
            file_type="application/pdf",
            last_modified=datetime(2023, 1, 1, 10, 0, 0),
            internal_id="pdf-001"
        ),
        FileRecord(
            file_path="/images/photo.jpg",
            permissions="rw-r--r--",
            size=2048000,
            file_type="image/jpeg",
            last_modified=datetime(2023, 1, 1, 11, 0, 0),
            internal_id="img-001"
        ),
        FileRecord(
            file_path="/data/config.json",
            permissions="rw-------",
            size=512,
            file_type="application/json",
            last_modified=datetime(2023, 1, 1, 12, 0, 0),
            internal_id="json-001"
        )
    ]
    
    for record in sample_records:
        db_manager.upsert_file_record(record)
    
    print(f"Created {len(sample_records)} sample records")


def create_sample_events():
    """Create sample events for demonstration when API is not available."""
    print("Creating sample events for demonstration...")
    
    return [
        PubSubEvent(
            event_type="change_permission",
            file_path="/documents/report.pdf",
            timestamp=datetime(2023, 1, 2, 10, 0, 0),
            metadata={"permissions": "rwxrwxrwx"}
        ),
        PubSubEvent(
            event_type="create",
            file_path="/documents/new_file.txt",
            timestamp=datetime(2023, 1, 2, 11, 0, 0),
            metadata={
                "permissions": "rw-r--r--",
                "size": 1024,
                "file_type": "text/plain",
                "internal_id": "txt-001"
            }
        ),
        PubSubEvent(
            event_type="rename",
            file_path="/images/photo.jpg",
            new_path="/images/renamed_photo.jpg",
            timestamp=datetime(2023, 1, 2, 12, 0, 0)
        ),
        PubSubEvent(
            event_type="move",
            file_path="/data/config.json",
            new_path="/config/app_config.json",
            timestamp=datetime(2023, 1, 2, 13, 0, 0),
            metadata={
                "permissions": "rw-rw-r--",
                "size": 768,
                "file_type": "application/json"
            }
        ),
        PubSubEvent(
            event_type="delete",
            file_path="/documents/old_report.pdf",
            timestamp=datetime(2023, 1, 2, 14, 0, 0)
        )
    ]


def demonstrate_event_processing_with_api():
    """Demonstrate event processing using the Infrastructure API."""
    print("=== Event Processing with Infrastructure API Demo ===\n")
    
    # Setup
    setup_logging()
    
    # Configuration
    db_path = "data/demo_event_processing.db"
    api_url = os.getenv("MOCK_API_URL", "http://localhost:8001")
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # Initialize components
    print("Initializing components...")
    db_manager = DatabaseManager(db_path)
    event_processor = EventProcessor(db_manager)
    infrastructure_api = InfrastructureAPI(api_url)
    
    # Create sample database
    create_sample_database(db_manager)
    
    # Show initial state
    print("\n--- Initial Database State ---")
    initial_records = db_manager.get_all_records()
    for record in initial_records:
        print(f"  {record.file_path} | {record.permissions} | {record.size} bytes")
    
    # Try to get events from API, fall back to sample events
    print("\n--- Getting Events ---")
    try:
        if infrastructure_api.health_check():
            print("Infrastructure API is available, getting real events...")
            events = infrastructure_api.get_pub_sub_events(count=10)
            print(f"Retrieved {len(events)} events from API")
        else:
            raise Exception("API not available")
    except Exception as e:
        print(f"API not available ({e}), using sample events...")
        events = create_sample_events()
        print(f"Created {len(events)} sample events")
    
    # Display events
    print("\n--- Events to Process ---")
    for i, event in enumerate(events, 1):
        print(f"  {i}. {event.event_type}: {event.file_path}")
        if event.new_path:
            print(f"     -> {event.new_path}")
        if event.metadata:
            print(f"     Metadata: {event.metadata}")
    
    # Process events
    print("\n--- Processing Events ---")
    result_counts = event_processor.process_events(events)
    
    print("Event processing results:")
    for event_type, count in result_counts.items():
        if count > 0:
            print(f"  {event_type}: {count}")
    
    # Show final state
    print("\n--- Final Database State ---")
    final_records = db_manager.get_all_records()
    for record in final_records:
        print(f"  {record.file_path} | {record.permissions} | {record.size} bytes")
    
    # Report results to API
    print("\n--- Reporting Results ---")
    results = {
        "sync_type": "incremental",
        "timestamp": datetime.now().isoformat(),
        "events_processed": sum(result_counts.values()) - result_counts.get('errors', 0),
        "errors": result_counts.get('errors', 0),
        "event_counts": result_counts,
        "final_record_count": len(final_records)
    }
    
    try:
        if infrastructure_api.health_check():
            response = infrastructure_api.report_results(results)
            print(f"Results reported successfully: {response}")
        else:
            print("API not available, skipping result reporting")
            print(f"Would report: {results}")
    except Exception as e:
        print(f"Failed to report results: {e}")
        print(f"Results that would be reported: {results}")
    
    print("\n=== Demo Complete ===")


def demonstrate_event_validation():
    """Demonstrate event validation and error handling."""
    print("\n=== Event Validation Demo ===\n")
    
    setup_logging()
    
    # Initialize components
    db_path = "data/demo_validation.db"
    Path("data").mkdir(exist_ok=True)
    
    db_manager = DatabaseManager(db_path)
    event_processor = EventProcessor(db_manager)
    
    # Create events with various validation issues
    invalid_events = [
        # Valid event
        PubSubEvent(
            event_type="create",
            file_path="/valid/file.txt",
            timestamp=datetime.now(),
            metadata={"permissions": "rw-r--r--", "size": 1024, "file_type": "text/plain"}
        ),
        # Invalid event type
        PubSubEvent(
            event_type="invalid_operation",
            file_path="/test/file.txt",
            timestamp=datetime.now()
        ),
        # Missing file path
        PubSubEvent(
            event_type="create",
            file_path="",
            timestamp=datetime.now()
        ),
        # Rename without new_path
        PubSubEvent(
            event_type="rename",
            file_path="/test/file.txt",
            timestamp=datetime.now()
        ),
        # Valid rename
        PubSubEvent(
            event_type="rename",
            file_path="/test/old.txt",
            new_path="/test/new.txt",
            timestamp=datetime.now()
        )
    ]
    
    print("Processing events with validation issues...")
    result_counts = event_processor.process_events(invalid_events)
    
    print("\nValidation results:")
    for event_type, count in result_counts.items():
        print(f"  {event_type}: {count}")
    
    print(f"\nExpected: 1 valid create, 1 valid rename, 3 errors")
    print("=== Validation Demo Complete ===")


if __name__ == "__main__":
    try:
        demonstrate_event_processing_with_api()
        demonstrate_event_validation()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()