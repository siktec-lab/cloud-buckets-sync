"""
Main entry point for the S3 sync service.
"""
import os
import sys
import json
from pathlib import Path
from loguru import logger

from .models.config import SyncConfig
from .services.sync_service import SyncService


def setup_logging():
    """Configure logging for the sync service."""
    # Remove default logger
    logger.remove()
    
    # Add console logger with appropriate format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Add file logger for debugging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        "logs/sync_service.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )


def run_initial_sync():
    """Run initial synchronization process."""
    try:
        logger.info("Starting S3 Sync Service - Initial Sync Mode")
        
        # Load configuration from environment
        config = SyncConfig.from_env()
        logger.info(f"Loaded configuration - Customer bucket: {config.customer_s3.bucket}")
        
        # Initialize sync service
        sync_service = SyncService(config)
        
        # Run initial sync
        logger.info("Beginning initial sync process")
        sync_results = sync_service.run_initial_sync()
        
        # Display results
        logger.info("Initial sync completed successfully")
        logger.info(f"Sync Results: {json.dumps(sync_results, indent=2, default=str)}")
        
        return sync_results
        
    except Exception as e:
        logger.error(f"Initial sync failed: {str(e)}")
        raise


def run_incremental_sync():
    """Run incremental synchronization process."""
    try:
        logger.info("Starting S3 Sync Service - Incremental Sync Mode")
        
        # Load configuration from environment
        config = SyncConfig.from_env()
        logger.info(f"Loaded configuration - Customer bucket: {config.customer_s3.bucket}")
        
        # Initialize sync service
        sync_service = SyncService(config)
        
        # Run incremental sync
        logger.info("Beginning incremental sync process")
        sync_results = sync_service.run_incremental_sync()
        
        # Display results
        logger.info("Incremental sync completed successfully")
        logger.info(f"Sync Results: {json.dumps(sync_results, indent=2, default=str)}")
        
        return sync_results
        
    except Exception as e:
        logger.error(f"Incremental sync failed: {str(e)}")
        raise


def run_daemon_mode():
    """Run sync service in daemon mode with periodic syncing."""
    import time
    import threading
    from datetime import datetime, timedelta
    
    try:
        logger.info("Starting S3 Sync Service - Daemon Mode")
        
        # Load configuration from environment
        config = SyncConfig.from_env()
        logger.info(f"Loaded configuration - Customer bucket: {config.customer_s3.bucket}")
        logger.info(f"Sync interval: {config.sync_interval} seconds")
        
        # Initialize sync service
        sync_service = SyncService(config)
        
        # Check if we need to run initial sync
        status = sync_service.get_sync_status()
        if status.get('database_records', 0) == 0:
            logger.info("No existing records found - running initial sync on startup")
            initial_results = sync_service.run_initial_sync()
            logger.info(f"Initial sync completed - Processed: {initial_results['files_processed']}, "
                       f"Failed: {initial_results['files_failed']}")
        else:
            logger.info(f"Found {status['database_records']} existing records - skipping initial sync")
        
        # Set up periodic sync scheduling
        next_sync_time = datetime.now() + timedelta(seconds=config.sync_interval)
        logger.info(f"Next sync scheduled for: {next_sync_time}")
        
        # Enter daemon loop with proper scheduling
        logger.info("Entering daemon mode - will sync periodically using incremental sync")
        while True:
            try:
                current_time = datetime.now()
                
                if current_time >= next_sync_time:
                    logger.info("Running scheduled incremental sync")
                    sync_results = sync_service.run_incremental_sync()
                    logger.info(f"Incremental sync completed - Events: {sync_results['events_processed']}, "
                               f"Operations processed: {sync_results['operations_processed']}, "
                               f"Operations failed: {sync_results['operations_failed']}")
                    
                    # Schedule next sync
                    next_sync_time = datetime.now() + timedelta(seconds=config.sync_interval)
                    logger.info(f"Next sync scheduled for: {next_sync_time}")
                
                # Sleep for a short interval to avoid busy waiting
                time.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down gracefully")
                break
            except Exception as e:
                logger.error(f"Error during periodic sync: {str(e)}")
                # Schedule next sync even if current one failed
                next_sync_time = datetime.now() + timedelta(seconds=config.sync_interval)
                logger.info(f"Next sync scheduled for: {next_sync_time} (after error)")
                continue
                
    except Exception as e:
        logger.error(f"Daemon mode failed: {str(e)}")
        raise


def print_help():
    """Print help information for the CLI."""
    help_text = """
S3 Sync Service - Command Line Interface

USAGE:
    python -m sync_service.main [COMMAND] [OPTIONS]

COMMANDS:
    initial-sync      Run initial synchronization (scan entire S3 bucket)
    incremental-sync  Run incremental synchronization (process events only)
    status           Show service status and statistics
    daemon           Run in daemon mode with periodic syncing (default)
    test             Run end-to-end test workflow
    help             Show this help message

EXAMPLES:
    # Run initial sync once
    python -m sync_service.main initial-sync
    
    # Run incremental sync once
    python -m sync_service.main incremental-sync
    
    # Check service status
    python -m sync_service.main status
    
    # Run in daemon mode (periodic syncing)
    python -m sync_service.main daemon
    
    # Test end-to-end workflow
    python -m sync_service.main test

ENVIRONMENT VARIABLES:
    CUSTOMER_S3_ENDPOINT     Customer S3 service URL
    CUSTOMER_S3_ACCESS_KEY   Customer S3 access key
    CUSTOMER_S3_SECRET_KEY   Customer S3 secret key
    CUSTOMER_S3_BUCKET       Customer S3 bucket name
    MOCK_API_URL            Mock API server URL
    SYNC_INTERVAL           Sync interval in seconds (default: 300)
    DATABASE_PATH           SQLite database path (default: data/sync.db)
    LIVE_RELOAD             Enable live reload (default: false)

For more information, see the README.md file.
"""
    print(help_text)


def run_test_workflow():
    """Run end-to-end test workflow to verify all components."""
    logger.info("Starting end-to-end test workflow")
    
    try:
        # Load configuration
        config = SyncConfig.from_env()
        sync_service = SyncService(config)
        
        # Test 1: Check service status
        logger.info("Test 1: Checking service status")
        status = sync_service.get_sync_status()
        logger.info(f"Service status: {status['service_status']}")
        logger.info(f"Database records: {status['database_records']}")
        
        # Test 2: Test connections
        logger.info("Test 2: Testing service connections")
        if not sync_service._test_connections():
            raise Exception("Connection tests failed")
        logger.info("All service connections successful")
        
        # Test 3: Run incremental sync (safer than initial sync for testing)
        logger.info("Test 3: Running incremental sync test")
        sync_results = sync_service.run_incremental_sync()
        logger.info(f"Incremental sync test completed - Events: {sync_results['events_processed']}")
        
        # Test 4: Export state to CSV
        logger.info("Test 4: Testing CSV export functionality")
        test_csv_path = "data/test_export.csv"
        sync_service.export_state_to_csv(test_csv_path)
        
        # Verify CSV file was created
        if os.path.exists(test_csv_path):
            logger.info(f"CSV export successful - File created: {test_csv_path}")
            # Clean up test file
            os.remove(test_csv_path)
        else:
            raise Exception("CSV export failed - File not created")
        
        # Test 5: Final status check
        logger.info("Test 5: Final status check")
        final_status = sync_service.get_sync_status()
        logger.info(f"Final database records: {final_status['database_records']}")
        
        logger.info("End-to-end test workflow completed successfully!")
        logger.info("All components are working correctly")
        
        return {
            'success': True,
            'tests_passed': 5,
            'final_status': final_status,
            'sync_results': sync_results
        }
        
    except Exception as e:
        logger.error(f"End-to-end test workflow failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Main entry point with enhanced command line argument handling."""
    setup_logging()
    
    # If no arguments provided, run in daemon mode (for Docker)
    if len(sys.argv) < 2:
        logger.info("No command specified - starting in daemon mode")
        run_daemon_mode()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command in ["help", "--help", "-h"]:
            print_help()
        elif command == "initial-sync":
            logger.info("Running initial sync command")
            results = run_initial_sync()
            logger.info("Initial sync command completed successfully")
        elif command == "incremental-sync":
            logger.info("Running incremental sync command")
            results = run_incremental_sync()
            logger.info("Incremental sync command completed successfully")
        elif command == "status":
            logger.info("Running status command")
            config = SyncConfig.from_env()
            sync_service = SyncService(config)
            status = sync_service.get_sync_status()
            logger.info(f"Service Status: {json.dumps(status, indent=2)}")
        elif command == "daemon":
            logger.info("Running daemon command")
            run_daemon_mode()
        elif command == "test":
            logger.info("Running test workflow command")
            test_results = run_test_workflow()
            if test_results['success']:
                logger.info("Test workflow completed successfully")
                logger.info(f"Test Results: {json.dumps(test_results, indent=2, default=str)}")
            else:
                logger.error(f"Test workflow failed: {test_results['error']}")
                sys.exit(1)
        else:
            logger.error(f"Unknown command: {command}")
            logger.error("Use 'help' to see available commands")
            print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down gracefully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()