"""
Infrastructure API client for communicating with file manager and mock server endpoints.

Handles HTTP communication with retry logic and error handling for:
- updatePermissions: Get file permissions from mock service
- saveToDisk: Upload files to file manager with metadata
- pubSubFullList: Get change events for incremental sync
- reportResults: Report sync operation results
"""

import time
import json
from typing import Dict, Any, List, BinaryIO, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

from ..models.data_models import PubSubEvent


class InfrastructureAPIError(Exception):
    """Custom exception for Infrastructure API errors."""
    pass


class InfrastructureAPI:
    """
    HTTP client for communicating with file manager and infrastructure service endpoints.
    
    Provides methods for all required infrastructure API endpoints with error handling,
    retry logic, and proper file streaming support.
    """
    
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        """
        Initialize Infrastructure API client with base URL and configuration.
        
        Args:
            base_url: Base URL for the infrastructure API server
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # Configure session with retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with error handling and logging.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            InfrastructureAPIError: If request fails after retries
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            # Log response details
            self.logger.debug(f"Response status: {response.status_code}")
            
            # Raise exception for HTTP errors
            response.raise_for_status()
            
            return response
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Infrastructure API request failed: {method} {url} - {str(e)}"
            self.logger.error(error_msg)
            raise InfrastructureAPIError(error_msg) from e
    
    def update_permissions(self, file_path: str, permissions: Optional[str] = None, 
                          owner: Optional[str] = None, group: Optional[str] = None) -> Dict[str, Any]:
        """
        Get or update file permissions from the infrastructure permissions service.
        
        If only file_path is provided: Returns current permissions
        If permission data is provided: Updates permissions and returns new state
        
        Args:
            file_path: Path of the file to get/update permissions for
            permissions: New permissions to set (optional)
            owner: New owner to set (optional)
            group: New group to set (optional)
            
        Returns:
            Dictionary containing permission information
            
        Raises:
            InfrastructureAPIError: If the API call fails
        """
        if not file_path:
            raise ValueError("file_path cannot be empty")
        
        try:
            if any([permissions, owner, group]):
                self.logger.info(f"Updating permissions for file: {file_path}")
            else:
                self.logger.info(f"Getting permissions for file: {file_path}")
            
            # Prepare form data
            form_data = {"file_path": file_path}
            if permissions:
                form_data["permissions"] = permissions
            if owner:
                form_data["owner"] = owner
            if group:
                form_data["group"] = group
            
            response = self._make_request(
                method="POST",
                endpoint="/updatePermissions",
                data=form_data
            )
            
            permissions_data = response.json()
            self.logger.debug(f"Received permissions: {permissions_data}")
            
            return permissions_data
            
        except Exception as e:
            error_msg = f"Failed to get/update permissions for {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise InfrastructureAPIError(error_msg) from e
    
    def save_to_disk(self, operation: str, file_path: str, file_stream: Optional[BinaryIO] = None,
                     new_path: Optional[str] = None, size: Optional[int] = None, 
                     file_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform file operations on infrastructure storage.
        
        Operations supported:
        - create: Create new file (requires file_stream)
        - update: Update existing file (requires file_stream)
        - rename: Rename file (requires new_path)
        - move: Move file (requires new_path)
        - delete: Delete file
        - get: Get file metadata
        
        Args:
            operation: Type of operation ('create', 'update', 'rename', 'move', 'delete', 'get')
            file_path: Original file path
            file_stream: File stream (required for create/update operations)
            new_path: New path (required for rename/move operations)
            size: File size in bytes (optional)
            file_type: MIME type of the file (optional)
            metadata: Additional metadata dictionary (optional)
            
        Returns:
            Dictionary containing operation response
            
        Raises:
            InfrastructureAPIError: If the operation fails
        """
        if not file_path:
            raise ValueError("file_path cannot be empty")
        
        if operation not in ['create', 'update', 'rename', 'move', 'delete', 'get']:
            raise ValueError("Invalid operation")
        
        if operation in ['create', 'update'] and not file_stream:
            raise ValueError(f"{operation} operation requires file_stream")
        
        if operation in ['rename', 'move'] and not new_path:
            raise ValueError(f"{operation} operation requires new_path")
        
        try:
            self.logger.info(f"Performing {operation} operation on file: {file_path}")
            
            # Prepare form data
            form_data = {
                "operation": operation,
                "file_path": file_path
            }
            
            if new_path:
                form_data["new_path"] = new_path
            if size is not None:
                form_data["size"] = str(size)
            if file_type:
                form_data["file_type"] = file_type
            if metadata:
                form_data["metadata"] = json.dumps(metadata)
            
            # Prepare files for upload operations
            files = None
            if operation in ['create', 'update'] and file_stream:
                # Reset stream position to beginning
                if hasattr(file_stream, 'seek'):
                    file_stream.seek(0)
                files = {"file": (file_path, file_stream, file_type or "application/octet-stream")}
            
            response = self._make_request(
                method="POST",
                endpoint="/saveToDisk",
                data=form_data,
                files=files
            )
            
            operation_response = response.json()
            self.logger.info(f"Operation {operation} completed successfully for {file_path}")
            
            return operation_response
            
        except Exception as e:
            error_msg = f"Failed to perform {operation} on {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise InfrastructureAPIError(error_msg) from e
    
    def get_pub_sub_events(self, count: int = 10) -> List[PubSubEvent]:
        """
        Get pub/sub events from infrastructure event service for incremental sync processing.
        
        Args:
            count: Number of events to retrieve (default: 10)
            
        Returns:
            List of PubSubEvent objects
            
        Raises:
            InfrastructureAPIError: If the API call fails
        """
        if count < 1 or count > 100:
            raise ValueError("count must be between 1 and 100")
        
        try:
            self.logger.info(f"Getting {count} pub/sub events from infrastructure")
            
            response = self._make_request(
                method="GET",
                endpoint="/pubSubFullList",
                params={"count": count}
            )
            
            events_data = response.json()
            events_list = events_data.get("events", [])
            
            # Convert to PubSubEvent objects
            events = []
            for event_data in events_list:
                try:
                    # Parse timestamp
                    timestamp_str = event_data.get("timestamp")
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')) if timestamp_str else datetime.now()
                    
                    event = PubSubEvent(
                        event_type=event_data.get("event_type", ""),
                        file_path=event_data.get("file_path", ""),
                        new_path=event_data.get("new_path"),
                        metadata=event_data.get("metadata"),
                        timestamp=timestamp
                    )
                    events.append(event)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse event: {event_data} - {str(e)}")
                    continue
            
            self.logger.info(f"Retrieved {len(events)} pub/sub events from infrastructure")
            return events
            
        except Exception as e:
            error_msg = f"Failed to get pub/sub events: {str(e)}"
            self.logger.error(error_msg)
            raise InfrastructureAPIError(error_msg) from e
    
    def report_results(self, results: Dict[str, Any]) -> Dict[str, str]:
        """
        Report sync operation results to the infrastructure monitoring endpoint.
        
        Args:
            results: Dictionary containing sync results
            
        Returns:
            Dictionary containing acknowledgment response
            
        Raises:
            InfrastructureAPIError: If the API call fails
        """
        if not results:
            raise ValueError("results cannot be empty")
        
        try:
            self.logger.info("Reporting sync results to infrastructure")
            self.logger.debug(f"Results data: {json.dumps(results, indent=2)}")
            
            response = self._make_request(
                method="POST",
                endpoint="/reportResults",
                json=results,
                headers={"Content-Type": "application/json"}
            )
            
            report_response = response.json()
            self.logger.info("Sync results reported successfully to infrastructure")
            
            return report_response
            
        except Exception as e:
            error_msg = f"Failed to report results: {str(e)}"
            self.logger.error(error_msg)
            raise InfrastructureAPIError(error_msg) from e
    
    def health_check(self) -> bool:
        """
        Check if the infrastructure API server is healthy and reachable.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self._make_request(method="GET", endpoint="/")
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Infrastructure API health check failed: {str(e)}")
            return False