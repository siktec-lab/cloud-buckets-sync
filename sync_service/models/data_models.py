"""
Core data models for the S3 sync service.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class FileRecord:
    """Represents a file record in the sync system."""
    file_path: str
    permissions: str
    size: int
    file_type: str
    last_modified: datetime
    internal_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export."""
        return {
            'file_path': self.file_path,
            'permissions': self.permissions,
            'size': self.size,
            'file_type': self.file_type,
            'last_modified': self.last_modified.isoformat(),
            'internal_id': self.internal_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileRecord':
        """Create from dictionary for CSV import."""
        return cls(
            file_path=data['file_path'],
            permissions=data['permissions'],
            size=int(data['size']),
            file_type=data['file_type'],
            last_modified=datetime.fromisoformat(data['last_modified']),
            internal_id=data.get('internal_id')
        )


@dataclass
class PubSubEvent:
    """Represents a pub/sub event from the mock server."""
    event_type: str  # 'change_permission', 'delete', 'create', 'rename', 'move'
    file_path: str
    timestamp: datetime
    new_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FileOperation:
    """Represents a file operation to be executed."""
    operation_type: str  # 'create', 'update', 'delete', 'move'
    file_path: str
    new_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None