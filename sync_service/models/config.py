"""
Configuration classes for the S3 sync service.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class S3Config:
    """Configuration for S3 service connection."""
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    region: Optional[str] = None
    
    @classmethod
    def from_env(cls, prefix: str) -> 'S3Config':
        """Create S3Config from environment variables with given prefix."""
        return cls(
            endpoint=os.getenv(f'{prefix}_S3_ENDPOINT', ''),
            access_key=os.getenv(f'{prefix}_S3_ACCESS_KEY', ''),
            secret_key=os.getenv(f'{prefix}_S3_SECRET_KEY', ''),
            bucket=os.getenv(f'{prefix}_S3_BUCKET', ''),
            region=os.getenv(f'{prefix}_S3_REGION')
        )


@dataclass
class SyncConfig:
    """Main configuration for the sync service."""
    customer_s3: S3Config
    file_manager_api_url: str
    mock_api_url: str
    sync_interval: int
    database_path: str
    live_reload: bool
    
    @classmethod
    def from_env(cls) -> 'SyncConfig':
        """Create SyncConfig from environment variables."""
        return cls(
            customer_s3=S3Config.from_env('CUSTOMER'),
            file_manager_api_url=os.getenv('FILE_MANAGER_API_URL', 'http://localhost:8000'),
            mock_api_url=os.getenv('MOCK_API_URL', 'http://localhost:8001'),
            sync_interval=int(os.getenv('SYNC_INTERVAL', '300')),  # Default 5 minutes
            database_path=os.getenv('DATABASE_PATH', 'data/sync.db'),
            live_reload=os.getenv('LIVE_RELOAD', 'false').lower() == 'true'
        )