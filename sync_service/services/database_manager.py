"""
SQLite database manager for the S3 sync service.
"""
import sqlite3
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from ..models.data_models import FileRecord


class DatabaseManager:
    """Manages SQLite database operations for file records."""
    
    def __init__(self, db_path: str):
        """Initialize database manager with database path."""
        self.db_path = db_path
        self._ensure_db_directory()
        self.create_tables()
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()
    
    def create_tables(self) -> None:
        """Create database tables with proper schema and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create file_records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    permissions TEXT,
                    size INTEGER,
                    file_type TEXT,
                    last_modified TIMESTAMP,
                    internal_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_path 
                ON file_records(file_path)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_internal_id 
                ON file_records(internal_id)
            """)
            
            conn.commit()
    
    def insert_file_record(self, record: FileRecord) -> None:
        """Insert a new file record into the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO file_records 
                (file_path, permissions, size, file_type, last_modified, internal_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.file_path,
                record.permissions,
                record.size,
                record.file_type,
                record.last_modified,
                record.internal_id
            ))
            
            conn.commit()
    
    def update_file_record(self, record: FileRecord) -> None:
        """Update an existing file record in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE file_records 
                SET permissions = ?, size = ?, file_type = ?, 
                    last_modified = ?, internal_id = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE file_path = ?
            """, (
                record.permissions,
                record.size,
                record.file_type,
                record.last_modified,
                record.internal_id,
                record.file_path
            ))
            
            conn.commit()
    
    def delete_file_record(self, file_path: str) -> None:
        """Delete a file record from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM file_records WHERE file_path = ?
            """, (file_path,))
            
            conn.commit()
    
    def get_file_record(self, file_path: str) -> Optional[FileRecord]:
        """Get a specific file record by file path."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT file_path, permissions, size, file_type, 
                       last_modified, internal_id
                FROM file_records 
                WHERE file_path = ?
            """, (file_path,))
            
            row = cursor.fetchone()
            if row:
                return FileRecord(
                    file_path=row['file_path'],
                    permissions=row['permissions'],
                    size=row['size'],
                    file_type=row['file_type'],
                    last_modified=datetime.fromisoformat(row['last_modified']),
                    internal_id=row['internal_id']
                )
            return None
    
    def get_all_records(self) -> List[FileRecord]:
        """Get all file records from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT file_path, permissions, size, file_type, 
                       last_modified, internal_id
                FROM file_records 
                ORDER BY file_path
            """)
            
            records = []
            for row in cursor.fetchall():
                records.append(FileRecord(
                    file_path=row['file_path'],
                    permissions=row['permissions'],
                    size=row['size'],
                    file_type=row['file_type'],
                    last_modified=datetime.fromisoformat(row['last_modified']),
                    internal_id=row['internal_id']
                ))
            
            return records
    
    def export_to_csv(self, csv_path: str) -> None:
        """Export all file records to CSV format."""
        records = self.get_all_records()
        
        # Ensure CSV directory exists
        csv_dir = Path(csv_path).parent
        csv_dir.mkdir(parents=True, exist_ok=True)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if records:
                # Use the first record to get field names
                fieldnames = list(records[0].to_dict().keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for record in records:
                    writer.writerow(record.to_dict())
            else:
                # Write empty CSV with headers
                fieldnames = ['file_path', 'permissions', 'size', 'file_type', 
                             'last_modified', 'internal_id']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
    
    def import_from_csv(self, csv_path: str) -> None:
        """Import file records from CSV format."""
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Skip empty rows
                if not any(row.values()):
                    continue
                
                record = FileRecord.from_dict(row)
                
                # Try to insert, if it fails due to unique constraint, update instead
                try:
                    self.insert_file_record(record)
                except sqlite3.IntegrityError:
                    self.update_file_record(record)
    
    def upsert_file_record(self, record: FileRecord) -> None:
        """Insert or update a file record (upsert operation)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO file_records
                (file_path, permissions, size, file_type, last_modified, internal_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                record.file_path,
                record.permissions,
                record.size,
                record.file_type,
                record.last_modified,
                record.internal_id
            ))
            conn.commit()
    
    def get_record_count(self) -> int:
        """Get the total number of records in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM file_records")
            return cursor.fetchone()[0]
    
    def clear_all_records(self) -> None:
        """Clear all records from the database (for testing purposes)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM file_records")
            conn.commit()