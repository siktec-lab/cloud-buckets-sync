"""
Main sync service orchestrator for S3 to file manager synchronization.
"""
import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from ..clients.s3_manager import S3Manager, S3Object
from ..clients.infrastructure_api import InfrastructureAPI, InfrastructureAPIError
from ..services.database_manager import DatabaseManager
from ..services.csv_processor import CSVProcessor
from ..services.event_processor import EventProcessor
from ..models.config import SyncConfig
from ..models.data_models import FileRecord, FileOperation


class SyncService:
    """
    Main synchronization service that orchestrates S3 scanning, file processing,
    and database operations for initial and incremental sync workflows.
    """
    
    def __init__(self, config: SyncConfig):
        """
        Initialize sync service with configuration.
        
        Args:
            config: SyncConfig containing all service configuration
        """
        self.config = config
        
        # Initialize components
        self.s3_manager = S3Manager(config.customer_s3)
        self.infrastructure_api = InfrastructureAPI(config.mock_api_url)
        self.database_manager = DatabaseManager(config.database_path)
        self.csv_processor = CSVProcessor()
        self.event_processor = EventProcessor(self.database_manager)
        
        logger.info("SyncService initialized successfully")
    
    def run_initial_sync(self) -> Dict[str, Any]:
        """
        Perform initial synchronization by scanning the entire customer S3 bucket
        and processing all discovered files.
        
        This method implements the complete initial sync workflow:
        1. Scan customer S3 bucket for all objects
        2. For each file: get permissions, save to disk, store in database
        3. Return sync statistics
        
        Returns:
            Dictionary containing sync statistics and results
            
        Raises:
            Exception: If sync fails due to S3, API, or database errors
        """
        logger.info("Starting initial sync process")
        
        sync_stats = {
            'start_time': datetime.now(),
            'files_processed': 0,
            'files_failed': 0,
            'total_size': 0,
            'errors': []
        }
        
        try:
            # Test connections before starting
            if not self._test_connections():
                raise Exception("Connection tests failed - cannot proceed with sync")
            
            logger.info("Scanning customer S3 bucket for objects")
            
            # Scan S3 bucket and process each object
            for s3_object in self.s3_manager.list_objects():
                try:
                    logger.debug(f"Processing S3 object: {s3_object.key}")
                    
                    # Process the file and update statistics
                    if self._process_file(s3_object):
                        sync_stats['files_processed'] += 1
                        sync_stats['total_size'] += s3_object.size
                        logger.info(f"Successfully processed file: {s3_object.key}")
                    else:
                        sync_stats['files_failed'] += 1
                        logger.warning(f"Failed to process file: {s3_object.key}")
                        
                except Exception as e:
                    sync_stats['files_failed'] += 1
                    error_msg = f"Error processing {s3_object.key}: {str(e)}"
                    sync_stats['errors'].append(error_msg)
                    logger.error(error_msg)
                    continue
            
            sync_stats['end_time'] = datetime.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            
            sync_stats['success'] = True
            
            logger.info(f"Initial sync completed - Processed: {sync_stats['files_processed']}, "
                       f"Failed: {sync_stats['files_failed']}, "
                       f"Total size: {sync_stats['total_size']} bytes, "
                       f"Duration: {sync_stats['duration']:.2f} seconds")
            
            # Report results to configured endpoints
            try:
                self._report_sync_results(sync_stats, 'initial')
            except Exception as e:
                logger.warning(f"Failed to report sync results: {str(e)}")
                sync_stats['errors'].append(f"Result reporting failed: {str(e)}")
            
            return sync_stats
            
        except Exception as e:
            sync_stats['end_time'] = datetime.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            sync_stats['success'] = False
            error_msg = f"Initial sync failed: {str(e)}"
            sync_stats['errors'].append(error_msg)
            logger.error(error_msg)
            
            # Still try to report the failure
            try:
                self._report_sync_results(sync_stats, 'initial')
            except Exception as report_error:
                logger.warning(f"Failed to report sync failure: {str(report_error)}")
            
            raise
    
    def _process_file(self, s3_object: S3Object) -> bool:
        """
        Process a single file from S3: get permissions, save to disk, store in database.
        
        Args:
            s3_object: S3Object containing file metadata
            
        Returns:
            bool: True if file was processed successfully, False otherwise
        """
        try:
            # Step 1: Get file stream and metadata from S3
            logger.debug(f"Getting file stream for: {s3_object.key}")
            file_stream = self.s3_manager.get_object_stream(s3_object.key)
            
            # Get additional metadata from S3
            s3_metadata = self.s3_manager.get_object_metadata(s3_object.key)
            
            # Step 2: Get file permissions from infrastructure API
            logger.debug(f"Getting permissions for: {s3_object.key}")
            permissions_response = self.infrastructure_api.update_permissions(s3_object.key)
            permissions = permissions_response.get('permissions', 'rw-r--r--')
            
            # Step 3: Read the stream into memory to avoid seek issues
            logger.debug(f"Reading file content for: {s3_object.key}")
            file_content = file_stream.read()
            
            # Create a BytesIO stream from the content
            from io import BytesIO
            content_stream = BytesIO(file_content)
            
            # Step 4: Save file to disk via infrastructure API
            logger.debug(f"Saving file to disk: {s3_object.key}")
            save_response = self.infrastructure_api.save_to_disk(
                operation='create',
                file_path=s3_object.key,
                file_stream=content_stream,
                size=s3_object.size,
                file_type=s3_metadata.get('content_type', 'application/octet-stream'),
                metadata={
                    'etag': s3_object.etag,
                    'storage_class': s3_object.storage_class,
                    'source': 'customer_s3'
                }
            )
            
            # Extract internal ID from save response
            internal_id = save_response.get('internal_id') or str(uuid.uuid4())
            
            # Step 5: Create file record and store in database
            file_record = FileRecord(
                file_path=s3_object.key,
                permissions=permissions,
                size=s3_object.size,
                file_type=s3_metadata.get('content_type', 'application/octet-stream'),
                last_modified=s3_object.last_modified,
                internal_id=internal_id
            )
            
            logger.debug(f"Storing file record in database: {s3_object.key}")
            self.database_manager.upsert_file_record(file_record)
            
            logger.debug(f"Successfully processed file: {s3_object.key} -> {internal_id}")
            return True
            
        except InfrastructureAPIError as e:
            logger.error(f"Infrastructure API error processing {s3_object.key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing {s3_object.key}: {str(e)}")
            return False
    
    def _test_connections(self) -> bool:
        """
        Test connections to all required services before starting sync.
        
        Returns:
            bool: True if all connections are successful, False otherwise
        """
        logger.info("Testing service connections")
        
        # Test S3 connection
        try:
            if not self.s3_manager.test_connection():
                logger.error("Customer S3 connection test failed")
                return False
            logger.info("Customer S3 connection test passed")
        except Exception as e:
            logger.error(f"Customer S3 connection test error: {str(e)}")
            return False
        
        # Test Infrastructure API connection
        try:
            if not self.infrastructure_api.health_check():
                logger.error("Infrastructure API health check failed")
                return False
            logger.info("Infrastructure API health check passed")
        except Exception as e:
            logger.error(f"Infrastructure API health check error: {str(e)}")
            return False
        
        # Test database connection
        try:
            record_count = self.database_manager.get_record_count()
            logger.info(f"Database connection test passed - Current records: {record_count}")
        except Exception as e:
            logger.error(f"Database connection test error: {str(e)}")
            return False
        
        logger.info("All service connections tested successfully")
        return True
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current sync service status and statistics.
        
        Returns:
            Dictionary containing service status information
        """
        try:
            record_count = self.database_manager.get_record_count()
            
            return {
                'service_status': 'healthy',
                'database_records': record_count,
                'database_path': self.config.database_path,
                'customer_bucket': self.config.customer_s3.bucket,
                'api_endpoints': {
                    'mock_api': self.config.mock_api_url,
                    'file_manager': self.config.file_manager_api_url
                }
            }
        except Exception as e:
            return {
                'service_status': 'error',
                'error': str(e)
            }
    
    def export_state_to_csv(self, filename: str) -> None:
        """
        Export current database state to CSV file.
        
        Args:
            filename: Path where CSV file should be saved
        """
        logger.info(f"Exporting database state to CSV: {filename}")
        
        try:
            # Use database manager's existing export functionality
            self.database_manager.export_to_csv(filename)
            logger.info(f"Successfully exported state to CSV: {filename}")
        except Exception as e:
            logger.error(f"Failed to export state to CSV: {str(e)}")
            raise
    
    def process_csv_diff(self, old_csv: str, new_csv: str) -> list[FileOperation]:
        """
        Process differences between two CSV files and generate FileOperation objects.
        
        Args:
            old_csv: Path to the old state CSV file
            new_csv: Path to the new state CSV file
            
        Returns:
            List of FileOperation objects representing the differences
        """
        logger.info(f"Processing CSV diff between {old_csv} and {new_csv}")
        
        try:
            operations = self.csv_processor.compare_csv_files(old_csv, new_csv)
            
            logger.info(f"CSV diff processing completed - Found {len(operations)} operations")
            
            # Log operation summary
            operation_counts = {}
            for op in operations:
                operation_counts[op.operation_type] = operation_counts.get(op.operation_type, 0) + 1
            
            for op_type, count in operation_counts.items():
                logger.info(f"  {op_type}: {count} operations")
            
            return operations
            
        except Exception as e:
            logger.error(f"Failed to process CSV diff: {str(e)}")
            raise
    
    def run_incremental_sync(self) -> Dict[str, Any]:
        """
        Perform incremental synchronization using event replay and CSV diff approach.
        
        This method implements the complete incremental sync workflow:
        1. Export current database state to CSV (old state)
        2. Retrieve and process pub/sub events to update database
        3. Export updated database state to CSV (new state)
        4. Compare CSV files to identify differences
        5. Execute operations based on differences
        6. Report results to configured endpoints
        
        Returns:
            Dictionary containing sync statistics and results
        """
        logger.info("Starting incremental sync process")
        
        sync_stats = {
            'start_time': datetime.now(),
            'events_processed': 0,
            'operations_processed': 0,
            'operations_failed': 0,
            'event_counts': {},
            'errors': []
        }
        
        old_csv_path = None
        new_csv_path = None
        
        try:
            # Test connections before starting
            if not self._test_connections():
                raise Exception("Connection tests failed - cannot proceed with incremental sync")
            
            # Step 1: Export current database state to CSV (old state)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            old_csv_path = f"data/sync_state_old_{timestamp}.csv"
            logger.info(f"Exporting current state to: {old_csv_path}")
            self.export_state_to_csv(old_csv_path)
            
            # Step 2: Retrieve and process pub/sub events
            logger.info("Retrieving pub/sub events from infrastructure API")
            events = self.infrastructure_api.get_pub_sub_events(count=50)
            logger.info(f"Retrieved {len(events)} events for processing")
            
            if events:
                # Process events to update database
                logger.info("Processing events to update database state")
                event_counts = self.event_processor.process_events(events)
                sync_stats['events_processed'] = len(events)
                sync_stats['event_counts'] = event_counts
                logger.info(f"Event processing completed: {event_counts}")
            else:
                logger.info("No events to process - database state unchanged")
                sync_stats['event_counts'] = {}
            
            # Step 3: Export updated database state to CSV (new state)
            new_csv_path = f"data/sync_state_new_{timestamp}.csv"
            logger.info(f"Exporting updated state to: {new_csv_path}")
            self.export_state_to_csv(new_csv_path)
            
            # Step 4: Process CSV diff to identify operations
            logger.info("Comparing old and new states to identify operations")
            operations = self.process_csv_diff(old_csv_path, new_csv_path)
            logger.info(f"Identified {len(operations)} operations to execute")
            
            # Step 5: Execute operations based on differences
            if operations:
                logger.info("Executing operations based on identified differences")
                for operation in operations:
                    try:
                        if self._execute_operation(operation):
                            sync_stats['operations_processed'] += 1
                            logger.info(f"Successfully executed {operation.operation_type} for {operation.file_path}")
                        else:
                            sync_stats['operations_failed'] += 1
                            logger.warning(f"Failed to execute {operation.operation_type} for {operation.file_path}")
                            
                    except Exception as e:
                        sync_stats['operations_failed'] += 1
                        error_msg = f"Error executing {operation.operation_type} for {operation.file_path}: {str(e)}"
                        sync_stats['errors'].append(error_msg)
                        logger.error(error_msg)
                        continue
            else:
                logger.info("No operations to execute - states are identical")
            
            # Calculate final statistics
            sync_stats['end_time'] = datetime.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            sync_stats['success'] = True
            
            logger.info(f"Incremental sync completed successfully - "
                       f"Events: {sync_stats['events_processed']}, "
                       f"Operations processed: {sync_stats['operations_processed']}, "
                       f"Operations failed: {sync_stats['operations_failed']}, "
                       f"Duration: {sync_stats['duration']:.2f} seconds")
            
            # Step 6: Report results to configured endpoints
            try:
                self._report_sync_results(sync_stats, 'incremental')
            except Exception as e:
                logger.warning(f"Failed to report sync results: {str(e)}")
                sync_stats['errors'].append(f"Result reporting failed: {str(e)}")
            
            return sync_stats
            
        except Exception as e:
            sync_stats['end_time'] = datetime.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            sync_stats['success'] = False
            error_msg = f"Incremental sync failed: {str(e)}"
            sync_stats['errors'].append(error_msg)
            logger.error(error_msg)
            
            # Still try to report the failure
            try:
                self._report_sync_results(sync_stats, 'incremental')
            except Exception as report_error:
                logger.warning(f"Failed to report sync failure: {str(report_error)}")
            
            raise
        
        finally:
            # Clean up temporary CSV files if they exist
            self._cleanup_temp_files([old_csv_path, new_csv_path])
    
    def _execute_operation(self, operation: FileOperation) -> bool:
        """
        Execute a single FileOperation.
        
        Args:
            operation: FileOperation to execute
            
        Returns:
            bool: True if operation was executed successfully, False otherwise
        """
        try:
            if operation.operation_type == 'create':
                return self._execute_create_operation(operation)
            elif operation.operation_type == 'update':
                return self._execute_update_operation(operation)
            elif operation.operation_type == 'delete':
                return self._execute_delete_operation(operation)
            elif operation.operation_type == 'move':
                return self._execute_move_operation(operation)
            else:
                logger.error(f"Unknown operation type: {operation.operation_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing operation {operation.operation_type} for {operation.file_path}: {str(e)}")
            return False
    
    def _execute_create_operation(self, operation: FileOperation) -> bool:
        """Execute a create operation."""
        logger.debug(f"Executing create operation for: {operation.file_path}")
        
        # For create operations, we need to get the file from S3 and save it
        try:
            # Get file stream from S3
            file_stream = self.s3_manager.get_object_stream(operation.file_path)
            file_content = file_stream.read()
            
            from io import BytesIO
            content_stream = BytesIO(file_content)
            
            # Save to disk via infrastructure API
            save_response = self.infrastructure_api.save_to_disk(
                operation='create',
                file_path=operation.file_path,
                file_stream=content_stream,
                size=operation.metadata.get('size', 0),
                file_type=operation.metadata.get('file_type', 'application/octet-stream'),
                metadata=operation.metadata
            )
            
            # Update database record
            file_record = FileRecord(
                file_path=operation.file_path,
                permissions=operation.metadata.get('permissions', 'rw-r--r--'),
                size=operation.metadata.get('size', 0),
                file_type=operation.metadata.get('file_type', 'application/octet-stream'),
                last_modified=datetime.fromisoformat(operation.metadata.get('last_modified', datetime.now().isoformat())),
                internal_id=save_response.get('internal_id') or operation.metadata.get('internal_id')
            )
            
            self.database_manager.upsert_file_record(file_record)
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute create operation: {str(e)}")
            return False
    
    def _execute_update_operation(self, operation: FileOperation) -> bool:
        """Execute an update operation."""
        logger.debug(f"Executing update operation for: {operation.file_path}")
        
        # For update operations, we update the database record and potentially re-save the file
        try:
            file_record = FileRecord(
                file_path=operation.file_path,
                permissions=operation.metadata.get('permissions', 'rw-r--r--'),
                size=operation.metadata.get('size', 0),
                file_type=operation.metadata.get('file_type', 'application/octet-stream'),
                last_modified=datetime.fromisoformat(operation.metadata.get('last_modified', datetime.now().isoformat())),
                internal_id=operation.metadata.get('internal_id')
            )
            
            self.database_manager.update_file_record(file_record)
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute update operation: {str(e)}")
            return False
    
    def _execute_delete_operation(self, operation: FileOperation) -> bool:
        """Execute a delete operation."""
        logger.debug(f"Executing delete operation for: {operation.file_path}")
        
        try:
            # Remove from database
            self.database_manager.delete_file_record(operation.file_path)
            
            # Optionally, we could also delete from file manager here
            # but that would require additional API endpoints
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute delete operation: {str(e)}")
            return False
    
    def _execute_move_operation(self, operation: FileOperation) -> bool:
        """Execute a move operation."""
        logger.debug(f"Executing move operation for: {operation.file_path} -> {operation.new_path}")
        
        try:
            # For move operations, we need to update the file_path in the database
            if not operation.new_path:
                logger.error("Move operation requires new_path")
                return False
            
            # Get existing record
            existing_record = self.database_manager.get_file_record(operation.file_path)
            if not existing_record:
                logger.error(f"Cannot move non-existent file: {operation.file_path}")
                return False
            
            # Delete old record
            self.database_manager.delete_file_record(operation.file_path)
            
            # Create new record with updated path
            new_record = FileRecord(
                file_path=operation.new_path,
                permissions=existing_record.permissions,
                size=existing_record.size,
                file_type=existing_record.file_type,
                last_modified=existing_record.last_modified,
                internal_id=existing_record.internal_id
            )
            
            self.database_manager.insert_file_record(new_record)
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute move operation: {str(e)}")
            return False
    
    def _report_sync_results(self, sync_stats: Dict[str, Any], sync_type: str) -> None:
        """
        Report sync results to configured endpoints.
        
        Args:
            sync_stats: Dictionary containing sync statistics
            sync_type: Type of sync ('initial' or 'incremental')
        """
        logger.info(f"Reporting {sync_type} sync results")
        
        # Prepare results for reporting
        results = {
            'sync_type': sync_type,
            'timestamp': datetime.now().isoformat(),
            'success': sync_stats.get('success', False),
            'duration_seconds': sync_stats.get('duration', 0),
            'statistics': {
                'events_processed': sync_stats.get('events_processed', 0),
                'operations_processed': sync_stats.get('operations_processed', 0),
                'operations_failed': sync_stats.get('operations_failed', 0),
                'files_processed': sync_stats.get('files_processed', 0),
                'files_failed': sync_stats.get('files_failed', 0),
                'total_size': sync_stats.get('total_size', 0)
            },
            'event_counts': sync_stats.get('event_counts', {}),
            'errors': sync_stats.get('errors', []),
            'service_info': {
                'database_path': self.config.database_path,
                'customer_bucket': self.config.customer_s3.bucket,
                'record_count': self.database_manager.get_record_count()
            }
        }
        
        try:
            # Report to infrastructure API
            response = self.infrastructure_api.report_results(results)
            logger.info(f"Successfully reported {sync_type} sync results: {response}")
            
        except Exception as e:
            logger.error(f"Failed to report {sync_type} sync results: {str(e)}")
            raise
    
    def start_periodic_sync(self) -> None:
        """
        Start periodic synchronization using a background thread.
        
        This method starts a background thread that runs incremental sync
        at the configured interval. It's designed for use in applications
        that need to continue other operations while syncing periodically.
        """
        import threading
        import time
        from datetime import datetime, timedelta
        
        def sync_worker():
            """Background worker function for periodic sync."""
            logger.info("Starting periodic sync worker thread")
            
            # Check if we need to run initial sync
            status = self.get_sync_status()
            if status.get('database_records', 0) == 0:
                logger.info("No existing records found - running initial sync")
                try:
                    initial_results = self.run_initial_sync()
                    logger.info(f"Initial sync completed - Processed: {initial_results['files_processed']}")
                except Exception as e:
                    logger.error(f"Initial sync failed in worker thread: {str(e)}")
            
            # Set up periodic incremental sync
            next_sync_time = datetime.now() + timedelta(seconds=self.config.sync_interval)
            logger.info(f"Periodic sync worker started - Next sync: {next_sync_time}")
            
            while True:
                try:
                    current_time = datetime.now()
                    
                    if current_time >= next_sync_time:
                        logger.info("Running scheduled incremental sync in worker thread")
                        sync_results = self.run_incremental_sync()
                        logger.info(f"Worker incremental sync completed - "
                                   f"Events: {sync_results['events_processed']}, "
                                   f"Operations: {sync_results['operations_processed']}")
                        
                        # Schedule next sync
                        next_sync_time = datetime.now() + timedelta(seconds=self.config.sync_interval)
                        logger.debug(f"Next sync scheduled for: {next_sync_time}")
                    
                    # Sleep for a short interval to avoid busy waiting
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in periodic sync worker: {str(e)}")
                    # Schedule next sync even if current one failed
                    next_sync_time = datetime.now() + timedelta(seconds=self.config.sync_interval)
                    time.sleep(60)  # Wait a bit longer after an error
                    continue
        
        # Start the worker thread as a daemon thread
        sync_thread = threading.Thread(target=sync_worker, daemon=True)
        sync_thread.start()
        logger.info("Periodic sync thread started successfully")
    
    def _cleanup_temp_files(self, file_paths: List[Optional[str]]) -> None:
        """
        Clean up temporary files created during sync operations.
        
        Args:
            file_paths: List of file paths to clean up (None values are ignored)
        """
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")