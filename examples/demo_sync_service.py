#!/usr/bin/env python3
"""
Simple demo of the S3 sync service functionality.

This script demonstrates:
- Service initialization
- Initial sync execution
- Database inspection
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sync_service.models.config import SyncConfig
from sync_service.services.sync_service import SyncService
from sync_service.services.database_manager import DatabaseManager
from loguru import logger


def setup_demo_environment():
    """Configure environment for demo."""
    os.environ['CUSTOMER_S3_ENDPOINT'] = 'http://localhost:9001'
    os.environ['CUSTOMER_S3_ACCESS_KEY'] = 'minioadmin'
    os.environ['CUSTOMER_S3_SECRET_KEY'] = 'minioadmin'
    os.environ['CUSTOMER_S3_BUCKET'] = 'customer-bucket'
    os.environ['CUSTOMER_S3_REGION'] = 'us-east-1'
    os.environ['MOCK_API_URL'] = 'http://localhost:8001'
    os.environ['DATABASE_PATH'] = 'data/demo.db'
    os.environ['SYNC_INTERVAL'] = '300'


def main():
    """Run sync service demo."""
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> - <level>{message}</level>", level="INFO")
    
    logger.info("🚀 S3 Sync Service Demo")
    
    try:
        # Setup
        setup_demo_environment()
        config = SyncConfig.from_env()
        
        # Initialize service
        logger.info("Initializing sync service...")
        sync_service = SyncService(config)
        
        # Check status
        status = sync_service.get_sync_status()
        logger.info(f"Service status: {status['service_status']}")
        logger.info(f"Current database records: {status['database_records']}")
        
        # Run initial sync
        logger.info("Running initial sync...")
        results = sync_service.run_initial_sync()
        
        # Show results
        logger.success(f"✅ Sync completed!")
        logger.info(f"Files processed: {results['files_processed']}")
        logger.info(f"Files failed: {results['files_failed']}")
        logger.info(f"Total size: {results['total_size']} bytes")
        logger.info(f"Duration: {results['duration']:.2f} seconds")
        
        # Show database contents
        db_manager = DatabaseManager(config.database_path)
        records = db_manager.get_all_records()
        
        logger.info(f"\n📊 Database contains {len(records)} records:")
        for record in records:
            logger.info(f"  • {record.file_path} ({record.size} bytes, {record.permissions})")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())