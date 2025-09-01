"""
Event processor for handling pubSubFullList events and updating SQLite database.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..models.data_models import PubSubEvent, FileRecord
from .database_manager import DatabaseManager


class EventProcessor:
    """Processes pubSubFullList events and updates the SQLite database accordingly."""
    
    def __init__(self, database_manager: DatabaseManager):
        """Initialize event processor with database manager."""
        self.db_manager = database_manager
        self.logger = logging.getLogger(__name__)
    
    def process_events(self, events: List[PubSubEvent]) -> Dict[str, int]:
        """
        Process a list of pubSubFullList events and update the database.
        
        Args:
            events: List of PubSubEvent objects to process
            
        Returns:
            Dictionary with counts of processed events by type
        """
        if not events:
            self.logger.info("No events to process")
            return {}
        
        # Sort events by timestamp to ensure proper order
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        event_counts = {
            'change_permission': 0,
            'delete': 0,
            'create': 0,
            'rename': 0,
            'move': 0,
            'errors': 0
        }
        
        self.logger.info(f"Processing {len(sorted_events)} events")
        
        for event in sorted_events:
            try:
                self._validate_event(event)
                self._process_single_event(event)
                event_counts[event.event_type] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing event {event}: {e}")
                event_counts['errors'] += 1
        
        self.logger.info(f"Event processing complete: {event_counts}")
        return event_counts
    
    def _validate_event(self, event: PubSubEvent) -> None:
        """
        Validate event data before processing.
        
        Args:
            event: PubSubEvent to validate
            
        Raises:
            ValueError: If event data is invalid
        """
        if not event.event_type:
            raise ValueError("Event type is required")
        
        if event.event_type not in ['change_permission', 'delete', 'create', 'rename', 'move']:
            raise ValueError(f"Invalid event type: {event.event_type}")
        
        if not event.file_path:
            raise ValueError("File path is required")
        
        if event.event_type in ['rename', 'move'] and not event.new_path:
            raise ValueError(f"New path is required for {event.event_type} events")
        
        if not isinstance(event.timestamp, datetime):
            raise ValueError("Event timestamp must be a datetime object")
    
    def _process_single_event(self, event: PubSubEvent) -> None:
        """
        Process a single event based on its type.
        
        Args:
            event: PubSubEvent to process
        """
        handler_map = {
            'change_permission': self._handle_change_permission,
            'delete': self._handle_delete,
            'create': self._handle_create,
            'rename': self._handle_rename,
            'move': self._handle_move
        }
        
        handler = handler_map.get(event.event_type)
        if handler:
            handler(event)
        else:
            raise ValueError(f"No handler for event type: {event.event_type}")
    
    def _handle_change_permission(self, event: PubSubEvent) -> None:
        """
        Handle change_permission event by updating file permissions.
        
        Args:
            event: PubSubEvent with change_permission type
        """
        self.logger.debug(f"Handling change_permission for {event.file_path}")
        
        # Get existing record
        existing_record = self.db_manager.get_file_record(event.file_path)
        if not existing_record:
            self.logger.warning(f"File not found for permission change: {event.file_path}")
            return
        
        # Extract new permissions from metadata
        new_permissions = self._extract_permissions_from_metadata(event.metadata)
        if new_permissions is None:
            self.logger.warning(f"No permissions found in metadata for {event.file_path}")
            return
        
        # Update permissions and last_modified
        existing_record.permissions = new_permissions
        existing_record.last_modified = event.timestamp
        
        self.db_manager.update_file_record(existing_record)
        self.logger.debug(f"Updated permissions for {event.file_path} to {new_permissions}")
    
    def _handle_delete(self, event: PubSubEvent) -> None:
        """
        Handle delete event by removing file record from database.
        
        Args:
            event: PubSubEvent with delete type
        """
        self.logger.debug(f"Handling delete for {event.file_path}")
        
        # Check if record exists before deleting
        existing_record = self.db_manager.get_file_record(event.file_path)
        if not existing_record:
            self.logger.warning(f"File not found for deletion: {event.file_path}")
            return
        
        self.db_manager.delete_file_record(event.file_path)
        self.logger.debug(f"Deleted record for {event.file_path}")
    
    def _handle_create(self, event: PubSubEvent) -> None:
        """
        Handle create event by adding new file record to database.
        
        Args:
            event: PubSubEvent with create type
        """
        self.logger.debug(f"Handling create for {event.file_path}")
        
        # Check if record already exists
        existing_record = self.db_manager.get_file_record(event.file_path)
        if existing_record:
            self.logger.warning(f"File already exists for creation: {event.file_path}")
            return
        
        # Create new file record from event metadata
        file_record = self._create_file_record_from_event(event)
        if not file_record:
            self.logger.error(f"Could not create file record from event: {event}")
            return
        
        self.db_manager.insert_file_record(file_record)
        self.logger.debug(f"Created record for {event.file_path}")
    
    def _handle_rename(self, event: PubSubEvent) -> None:
        """
        Handle rename event by updating file path in database.
        
        Args:
            event: PubSubEvent with rename type
        """
        self.logger.debug(f"Handling rename from {event.file_path} to {event.new_path}")
        
        # Get existing record
        existing_record = self.db_manager.get_file_record(event.file_path)
        if not existing_record:
            self.logger.warning(f"File not found for rename: {event.file_path}")
            return
        
        # Delete old record and create new one with updated path
        self.db_manager.delete_file_record(event.file_path)
        
        # Update the file path and last_modified
        existing_record.file_path = event.new_path
        existing_record.last_modified = event.timestamp
        
        self.db_manager.insert_file_record(existing_record)
        self.logger.debug(f"Renamed {event.file_path} to {event.new_path}")
    
    def _handle_move(self, event: PubSubEvent) -> None:
        """
        Handle move event by updating file path in database.
        Move is similar to rename but may have different metadata.
        
        Args:
            event: PubSubEvent with move type
        """
        self.logger.debug(f"Handling move from {event.file_path} to {event.new_path}")
        
        # Get existing record
        existing_record = self.db_manager.get_file_record(event.file_path)
        if not existing_record:
            self.logger.warning(f"File not found for move: {event.file_path}")
            return
        
        # Delete old record and create new one with updated path
        self.db_manager.delete_file_record(event.file_path)
        
        # Update the file path, last_modified, and potentially other metadata
        existing_record.file_path = event.new_path
        existing_record.last_modified = event.timestamp
        
        # Update other metadata if provided
        if event.metadata:
            permissions = self._extract_permissions_from_metadata(event.metadata)
            if permissions:
                existing_record.permissions = permissions
            
            size = event.metadata.get('size')
            if size is not None:
                existing_record.size = int(size)
            
            file_type = event.metadata.get('file_type')
            if file_type:
                existing_record.file_type = file_type
        
        self.db_manager.insert_file_record(existing_record)
        self.logger.debug(f"Moved {event.file_path} to {event.new_path}")
    
    def _extract_permissions_from_metadata(self, metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Extract permissions from event metadata.
        
        Args:
            metadata: Event metadata dictionary
            
        Returns:
            Permissions string or None if not found
        """
        if not metadata:
            return None
        
        # Try different possible keys for permissions
        permission_keys = ['permissions', 'permission', 'perms', 'access']
        for key in permission_keys:
            if key in metadata:
                return str(metadata[key])
        
        return None
    
    def _create_file_record_from_event(self, event: PubSubEvent) -> Optional[FileRecord]:
        """
        Create a FileRecord from a create event.
        
        Args:
            event: PubSubEvent with create type
            
        Returns:
            FileRecord object or None if metadata is insufficient
        """
        if not event.metadata:
            self.logger.error(f"No metadata provided for create event: {event.file_path}")
            return None
        
        try:
            # Extract required fields from metadata
            permissions = self._extract_permissions_from_metadata(event.metadata) or "unknown"
            size = int(event.metadata.get('size', 0))
            file_type = event.metadata.get('file_type', 'unknown')
            internal_id = event.metadata.get('internal_id')
            
            return FileRecord(
                file_path=event.file_path,
                permissions=permissions,
                size=size,
                file_type=file_type,
                last_modified=event.timestamp,
                internal_id=internal_id
            )
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error creating file record from event metadata: {e}")
            return None