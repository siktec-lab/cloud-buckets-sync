"""
CSV processing and diff engine for the S3 sync service.
"""
import csv
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime

from ..models.data_models import FileRecord, FileOperation


class CSVProcessor:
    """Handles CSV processing, diff operations, and FileOperation generation."""
    
    def __init__(self):
        """Initialize CSV processor."""
        pass
    
    def export_records_to_csv(self, records: List[FileRecord], csv_path: str) -> None:
        """Export file records to CSV format."""
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
    
    def import_records_from_csv(self, csv_path: str) -> List[FileRecord]:
        """Import file records from CSV format."""
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        records = []
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Skip empty rows
                if not any(row.values()):
                    continue
                
                record = FileRecord.from_dict(row)
                records.append(record)
        
        return records
    
    def compare_csv_files(self, old_csv_path: str, new_csv_path: str) -> List[FileOperation]:
        """
        Compare two CSV files and generate FileOperation objects for differences.
        Uses pandas for efficient outer join operations.
        """
        if not Path(old_csv_path).exists():
            raise FileNotFoundError(f"Old CSV file not found: {old_csv_path}")
        
        if not Path(new_csv_path).exists():
            raise FileNotFoundError(f"New CSV file not found: {new_csv_path}")
        
        # Read CSV files into pandas DataFrames
        old_df = pd.read_csv(old_csv_path)
        new_df = pd.read_csv(new_csv_path)
        
        # Handle empty DataFrames
        if old_df.empty and new_df.empty:
            return []
        
        if old_df.empty:
            # All records in new_df are creates
            return self._generate_create_operations(new_df)
        
        if new_df.empty:
            # All records in old_df are deletes
            return self._generate_delete_operations(old_df)
        
        # Perform outer join to identify differences
        operations = []
        
        # Find deleted files (in old but not in new)
        deleted_files = self._find_deleted_files(old_df, new_df)
        operations.extend(self._generate_delete_operations(deleted_files))
        
        # Find created files (in new but not in old)
        created_files = self._find_created_files(old_df, new_df)
        operations.extend(self._generate_create_operations(created_files))
        
        # Find updated files (in both but with different content)
        updated_files = self._find_updated_files(old_df, new_df)
        operations.extend(self._generate_update_operations(updated_files))
        
        return operations
    
    def _find_deleted_files(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """Find files that exist in old but not in new (deleted files)."""
        if old_df.empty:
            return pd.DataFrame()
        
        # Files in old but not in new
        deleted_mask = ~old_df['file_path'].isin(new_df['file_path'])
        return old_df[deleted_mask]
    
    def _find_created_files(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """Find files that exist in new but not in old (created files)."""
        if new_df.empty:
            return pd.DataFrame()
        
        # Files in new but not in old
        created_mask = ~new_df['file_path'].isin(old_df['file_path'])
        return new_df[created_mask]
    
    def _find_updated_files(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """Find files that exist in both but have different content (updated files)."""
        if old_df.empty or new_df.empty:
            return pd.DataFrame()
        
        # Merge on file_path to compare records
        merged = pd.merge(old_df, new_df, on='file_path', how='inner', suffixes=('_old', '_new'))
        
        # Find rows where any field (except file_path) has changed
        comparison_fields = ['permissions', 'size', 'file_type', 'last_modified', 'internal_id']
        
        changed_mask = pd.Series([False] * len(merged))
        for field in comparison_fields:
            old_col = f"{field}_old"
            new_col = f"{field}_new"
            if old_col in merged.columns and new_col in merged.columns:
                # Handle NaN values in comparison
                field_changed = (merged[old_col] != merged[new_col]) & ~(
                    merged[old_col].isna() & merged[new_col].isna()
                )
                changed_mask |= field_changed
        
        updated_merged = merged[changed_mask]
        
        # Return only the new version of updated files
        if not updated_merged.empty:
            new_columns = ['file_path'] + [f"{field}_new" for field in comparison_fields]
            updated_files = updated_merged[new_columns].copy()
            
            # Rename columns back to original names
            column_mapping = {f"{field}_new": field for field in comparison_fields}
            updated_files = updated_files.rename(columns=column_mapping)
            
            return updated_files
        
        return pd.DataFrame()
    
    def _generate_delete_operations(self, deleted_df: pd.DataFrame) -> List[FileOperation]:
        """Generate delete operations from deleted files DataFrame."""
        operations = []
        
        for _, row in deleted_df.iterrows():
            operation = FileOperation(
                operation_type='delete',
                file_path=row['file_path'],
                metadata={
                    'permissions': row.get('permissions'),
                    'size': row.get('size'),
                    'file_type': row.get('file_type'),
                    'last_modified': row.get('last_modified'),
                    'internal_id': row.get('internal_id')
                }
            )
            operations.append(operation)
        
        return operations
    
    def _generate_create_operations(self, created_df: pd.DataFrame) -> List[FileOperation]:
        """Generate create operations from created files DataFrame."""
        operations = []
        
        for _, row in created_df.iterrows():
            operation = FileOperation(
                operation_type='create',
                file_path=row['file_path'],
                metadata={
                    'permissions': row.get('permissions'),
                    'size': row.get('size'),
                    'file_type': row.get('file_type'),
                    'last_modified': row.get('last_modified'),
                    'internal_id': row.get('internal_id')
                }
            )
            operations.append(operation)
        
        return operations
    
    def _generate_update_operations(self, updated_df: pd.DataFrame) -> List[FileOperation]:
        """Generate update operations from updated files DataFrame."""
        operations = []
        
        for _, row in updated_df.iterrows():
            operation = FileOperation(
                operation_type='update',
                file_path=row['file_path'],
                metadata={
                    'permissions': row.get('permissions'),
                    'size': row.get('size'),
                    'file_type': row.get('file_type'),
                    'last_modified': row.get('last_modified'),
                    'internal_id': row.get('internal_id')
                }
            )
            operations.append(operation)
        
        return operations
    
    def generate_operations_from_records(
        self, 
        old_records: List[FileRecord], 
        new_records: List[FileRecord]
    ) -> List[FileOperation]:
        """
        Generate FileOperation objects by comparing two lists of FileRecord objects.
        This is an alternative to CSV file comparison for in-memory operations.
        """
        # Convert records to dictionaries for easier comparison
        old_dict = {record.file_path: record for record in old_records}
        new_dict = {record.file_path: record for record in new_records}
        
        operations = []
        
        # Find deleted files (in old but not in new)
        for file_path in old_dict:
            if file_path not in new_dict:
                record = old_dict[file_path]
                operation = FileOperation(
                    operation_type='delete',
                    file_path=file_path,
                    metadata={
                        'permissions': record.permissions,
                        'size': record.size,
                        'file_type': record.file_type,
                        'last_modified': record.last_modified.isoformat(),
                        'internal_id': record.internal_id
                    }
                )
                operations.append(operation)
        
        # Find created and updated files
        for file_path in new_dict:
            new_record = new_dict[file_path]
            
            if file_path not in old_dict:
                # Created file
                operation = FileOperation(
                    operation_type='create',
                    file_path=file_path,
                    metadata={
                        'permissions': new_record.permissions,
                        'size': new_record.size,
                        'file_type': new_record.file_type,
                        'last_modified': new_record.last_modified.isoformat(),
                        'internal_id': new_record.internal_id
                    }
                )
                operations.append(operation)
            else:
                # Check if file was updated
                old_record = old_dict[file_path]
                if self._records_differ(old_record, new_record):
                    operation = FileOperation(
                        operation_type='update',
                        file_path=file_path,
                        metadata={
                            'permissions': new_record.permissions,
                            'size': new_record.size,
                            'file_type': new_record.file_type,
                            'last_modified': new_record.last_modified.isoformat(),
                            'internal_id': new_record.internal_id
                        }
                    )
                    operations.append(operation)
        
        return operations
    
    def _records_differ(self, old_record: FileRecord, new_record: FileRecord) -> bool:
        """Check if two FileRecord objects differ in any field except file_path."""
        return (
            old_record.permissions != new_record.permissions or
            old_record.size != new_record.size or
            old_record.file_type != new_record.file_type or
            old_record.last_modified != new_record.last_modified or
            old_record.internal_id != new_record.internal_id
        )
    
    def validate_csv_format(self, csv_path: str) -> bool:
        """
        Validate that a CSV file has the expected format for FileRecord data.
        """
        if not Path(csv_path).exists():
            return False
        
        expected_columns = {'file_path', 'permissions', 'size', 'file_type', 
                           'last_modified', 'internal_id'}
        
        try:
            df = pd.read_csv(csv_path)
            actual_columns = set(df.columns)
            return expected_columns.issubset(actual_columns)
        except Exception:
            return False
    
    def get_csv_summary(self, csv_path: str) -> Dict[str, Any]:
        """
        Get summary information about a CSV file.
        """
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        
        return {
            'total_records': len(df),
            'file_types': df['file_type'].value_counts().to_dict() if 'file_type' in df.columns else {},
            'total_size': df['size'].sum() if 'size' in df.columns else 0,
            'columns': list(df.columns),
            'has_internal_ids': df['internal_id'].notna().sum() if 'internal_id' in df.columns else 0
        }