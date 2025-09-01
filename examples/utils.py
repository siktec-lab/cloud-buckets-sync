#!/usr/bin/env python3
"""
Utility scripts for S3 sync service management.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sync_service.services.database_manager import DatabaseManager
from loguru import logger


def setup_environment():
    """Set up standard environment variables."""
    os.environ['CUSTOMER_S3_ENDPOINT'] = 'http://localhost:9001'
    os.environ['CUSTOMER_S3_ACCESS_KEY'] = 'minioadmin'
    os.environ['CUSTOMER_S3_SECRET_KEY'] = 'minioadmin'
    os.environ['CUSTOMER_S3_BUCKET'] = 'customer-bucket'
    os.environ['CUSTOMER_S3_REGION'] = 'us-east-1'
    os.environ['MOCK_API_URL'] = 'http://localhost:8001'
    os.environ['DATABASE_PATH'] = 'data/demo.db'


def check_database():
    """Check database contents and export to CSV."""
    logger.info("📊 Checking database contents...")
    
    db_manager = DatabaseManager('data/demo.db')
    records = db_manager.get_all_records()
    
    logger.info(f"Total records: {len(records)}")
    
    for i, record in enumerate(records, 1):
        logger.info(f"{i}. {record.file_path}")
        logger.info(f"   Size: {record.size} bytes")
        logger.info(f"   Permissions: {record.permissions}")
        logger.info(f"   Type: {record.file_type}")
        logger.info(f"   ID: {record.internal_id}")
    
    # Export to CSV
    csv_path = 'data/database_export.csv'
    db_manager.export_to_csv(csv_path)
    logger.info(f"📄 Exported to: {csv_path}")


def check_docker_status():
    """Check Docker container status."""
    logger.info("🐳 Checking Docker containers...")
    
    try:
        result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if any(service in line for service in ['s3-sync-service', 'minio', 'mock-api']):
                    logger.info(f"  {line}")
        else:
            logger.error("Failed to get container status")
    except Exception as e:
        logger.error(f"Error checking Docker: {str(e)}")


def clear_database():
    """Clear all records from database."""
    logger.warning("⚠️  Clearing database...")
    
    db_manager = DatabaseManager('data/demo.db')
    initial_count = db_manager.get_record_count()
    
    db_manager.clear_all_records()
    
    final_count = db_manager.get_record_count()
    logger.info(f"Cleared {initial_count - final_count} records")


def main():
    """Run utility based on command line argument."""
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> - <level>{message}</level>", level="INFO")
    
    if len(sys.argv) < 2:
        logger.info("🛠️  Available utilities:")
        logger.info("  python examples/utils.py check-db     - Check database contents")
        logger.info("  python examples/utils.py check-docker - Check Docker status")
        logger.info("  python examples/utils.py clear-db     - Clear database")
        return 1
    
    command = sys.argv[1]
    setup_environment()
    
    if command == "check-db":
        check_database()
    elif command == "check-docker":
        check_docker_status()
    elif command == "clear-db":
        clear_database()
    else:
        logger.error(f"Unknown command: {command}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())