"""
Mock API server for S3 sync service testing.

Provides mock endpoints for:
- updatePermissions: Mock permissions service
- saveToDisk: File manager endpoint that saves files with internal ID
- pubSubFullList: Mock event service that returns sync events
"""

import uuid
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn


# Data models for API responses
class PermissionResponse(BaseModel):
    file_path: str
    permissions: str
    owner: str
    group: str
    last_updated: datetime


class SaveToDiskResponse(BaseModel):
    internal_id: Optional[str] = None
    file_path: str
    operation: str  # 'create', 'update', 'rename', 'move', 'delete', 'get'
    size: Optional[int] = None
    saved_at: datetime
    status: str
    new_path: Optional[str] = None  # For rename/move operations
    metadata: Optional[Dict[str, Any]] = None


class PubSubEvent(BaseModel):
    event_type: str  # 'change_permission', 'delete', 'create', 'rename', 'move'
    file_path: str
    new_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime


class MockDataGenerator:
    """Generates realistic mock data for API responses."""
    
    @staticmethod
    def generate_permissions(file_path: str) -> PermissionResponse:
        """Generate mock permissions for a file."""
        # Simulate different permission patterns based on file type
        if file_path.endswith(('.txt', '.md', '.log')):
            permissions = "rw-r--r--"
            owner = "user"
            group = "users"
        elif file_path.endswith(('.py', '.js', '.sh')):
            permissions = "rwxr-xr-x"
            owner = "developer"
            group = "dev"
        elif file_path.endswith(('.jpg', '.png', '.pdf')):
            permissions = "rw-r-----"
            owner = "content"
            group = "media"
        else:
            permissions = "rw-rw-r--"
            owner = "system"
            group = "system"
        
        return PermissionResponse(
            file_path=file_path,
            permissions=permissions,
            owner=owner,
            group=group,
            last_updated=datetime.now()
        )
    
    @staticmethod
    def generate_pub_sub_events(count: int = 10) -> List[PubSubEvent]:
        """Generate mock pub/sub events for testing."""
        events = []
        base_time = datetime.now() - timedelta(hours=24)
        
        # Sample file paths for events
        sample_files = [
            "/documents/report.pdf",
            "/images/photo1.jpg",
            "/data/export.csv",
            "/scripts/backup.sh",
            "/logs/app.log",
            "/config/settings.json",
            "/uploads/document.docx",
            "/temp/cache.tmp"
        ]
        
        event_types = ['create', 'change_permission', 'delete', 'rename', 'move']
        
        for i in range(count):
            event_type = event_types[i % len(event_types)]
            file_path = sample_files[i % len(sample_files)]
            
            event = PubSubEvent(
                event_type=event_type,
                file_path=file_path,
                timestamp=base_time + timedelta(minutes=i * 30)
            )
            
            # Add specific data based on event type
            if event_type == 'rename' or event_type == 'move':
                event.new_path = f"{file_path}_renamed" if event_type == 'rename' else f"/moved{file_path}"
            
            if event_type == 'change_permission':
                event.metadata = {
                    "old_permissions": "rw-r--r--",
                    "new_permissions": "rwxr-xr-x",
                    "changed_by": "admin"
                }
            elif event_type == 'create':
                event.metadata = {
                    "size": 1024 * (i + 1),
                    "mime_type": "application/octet-stream",
                    "created_by": "system"
                }
            
            events.append(event)
        
        return events


# Initialize FastAPI app
app = FastAPI(
    title="Mock API Server",
    description="Mock API server for S3 sync service testing",
    version="1.0.0"
)

# Storage directory for saved files
STORAGE_DIR = Path("/tmp/mock_api_storage")
STORAGE_DIR.mkdir(exist_ok=True)

# Mock data generator instance
mock_generator = MockDataGenerator()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Mock API Server is running", "timestamp": datetime.now()}


@app.post("/updatePermissions")
async def update_permissions(
    file_path: str = Form(...),
    permissions: Optional[str] = Form(None),
    owner: Optional[str] = Form(None),
    group: Optional[str] = Form(None)
) -> PermissionResponse:
    """
    Endpoint for retrieving or updating file permissions.
    
    If only file_path is provided: Returns current permissions
    If permissions data is provided: Updates permissions and returns new state
    
    Args:
        file_path: Path of the file to get/update permissions for
        permissions: New permissions to set (optional)
        owner: New owner to set (optional)
        group: New group to set (optional)
        
    Returns:
        PermissionResponse with current or updated permission data
    """
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    # If no permission data provided, just return current permissions
    if not any([permissions, owner, group]):
        # Generate mock permissions based on file path
        current_permissions = mock_generator.generate_permissions(file_path)
        return current_permissions
    
    # Update permissions if provided
    if permissions or owner or group:
        # Get current permissions as base
        current_permissions = mock_generator.generate_permissions(file_path)
        
        # Update with provided values
        updated_permissions = PermissionResponse(
            file_path=file_path,
            permissions=permissions or current_permissions.permissions,
            owner=owner or current_permissions.owner,
            group=group or current_permissions.group,
            last_updated=datetime.now()
        )
        
        # In a real implementation, this would persist to database
        print(f"Updated permissions for {file_path}: {updated_permissions.permissions}")
        
        return updated_permissions


@app.post("/saveToDisk")
async def save_to_disk(
    operation: str = Form(...),  # 'create', 'update', 'rename', 'move', 'delete', 'get'
    file_path: str = Form(...),
    file: Optional[UploadFile] = File(None),
    new_path: Optional[str] = Form(None),  # For rename/move operations
    size: Optional[int] = Form(None),
    file_type: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)  # JSON string of additional metadata
) -> SaveToDiskResponse:
    """
    File manager endpoint that handles all file operations.
    
    Operations supported:
    - create: Create new file (requires file upload)
    - update: Update existing file (requires file upload)
    - rename: Rename file (requires new_path)
    - move: Move file (requires new_path)
    - delete: Delete file
    - get: Get file metadata
    
    Args:
        operation: Type of operation to perform
        file_path: Original file path
        file: File stream (required for create/update)
        new_path: New path (required for rename/move)
        size: File size in bytes
        file_type: MIME type of the file
        metadata: Additional metadata as JSON string
        
    Returns:
        SaveToDiskResponse with operation details
    """
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    if operation not in ['create', 'update', 'rename', 'move', 'delete', 'get']:
        raise HTTPException(status_code=400, detail="Invalid operation")
    
    # Parse metadata if provided
    parsed_metadata = None
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    try:
        if operation in ['create', 'update']:
            if not file:
                raise HTTPException(status_code=400, detail=f"{operation} operation requires file upload")
            
            # Generate internal ID for the file
            internal_id = str(uuid.uuid4())
            
            # Save file with internal ID as filename
            save_path = STORAGE_DIR / internal_id
            
            # Read and save file content
            content = await file.read()
            with open(save_path, "wb") as f:
                f.write(content)
            
            # Get actual file size if not provided
            actual_size = len(content) if size is None else size
            
            response = SaveToDiskResponse(
                internal_id=internal_id,
                file_path=file_path,
                operation=operation,
                size=actual_size,
                saved_at=datetime.now(),
                status="success",
                metadata=parsed_metadata
            )
            
        elif operation in ['rename', 'move']:
            if not new_path:
                raise HTTPException(status_code=400, detail=f"{operation} operation requires new_path")
            
            # Simulate rename/move operation
            # In real implementation, this would update file system and database
            response = SaveToDiskResponse(
                internal_id=str(uuid.uuid4()),  # Would be existing ID in real implementation
                file_path=file_path,
                operation=operation,
                new_path=new_path,
                saved_at=datetime.now(),
                status="success",
                metadata=parsed_metadata
            )
            
        elif operation == 'delete':
            # Simulate delete operation
            # In real implementation, this would remove file and update database
            response = SaveToDiskResponse(
                file_path=file_path,
                operation=operation,
                saved_at=datetime.now(),
                status="success",
                metadata=parsed_metadata
            )
            
        elif operation == 'get':
            # Simulate get metadata operation
            # In real implementation, this would query database for file info
            response = SaveToDiskResponse(
                internal_id=str(uuid.uuid4()),  # Would be actual ID in real implementation
                file_path=file_path,
                operation=operation,
                size=size or 1024,  # Mock size
                saved_at=datetime.now(),
                status="success",
                metadata=parsed_metadata or {"last_accessed": datetime.now().isoformat()}
            )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform {operation} operation: {str(e)}")


@app.get("/pubSubFullList")
async def pub_sub_full_list(count: int = 10) -> Dict[str, Any]:
    """
    Mock endpoint that returns pub/sub events for sync processing.
    
    Args:
        count: Number of events to return (default: 10)
        
    Returns:
        Dictionary containing list of mock events
    """
    if count < 1 or count > 100:
        raise HTTPException(status_code=400, detail="count must be between 1 and 100")
    
    # Generate mock events
    events = mock_generator.generate_pub_sub_events(count)
    
    # Convert to dict format for JSON response
    events_data = [
        {
            "event_type": event.event_type,
            "file_path": event.file_path,
            "new_path": event.new_path,
            "metadata": event.metadata,
            "timestamp": event.timestamp.isoformat()
        }
        for event in events
    ]
    
    return {
        "events": events_data,
        "total_count": len(events_data),
        "generated_at": datetime.now().isoformat()
    }


@app.post("/reportResults")
async def report_results(results: Dict[str, Any]) -> Dict[str, str]:
    """
    Mock endpoint for receiving sync operation results.
    
    Args:
        results: Dictionary containing sync results
        
    Returns:
        Acknowledgment response
    """
    # Log the results (in a real implementation, this might go to a database)
    print(f"Received sync results: {json.dumps(results, indent=2)}")
    
    return {
        "status": "received",
        "message": "Sync results recorded successfully",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "mock_api.server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )