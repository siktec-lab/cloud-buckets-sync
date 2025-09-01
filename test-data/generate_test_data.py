#!/usr/bin/env python3
"""
Test data generator for S3 sync service.

This script generates various types of test files with different sizes,
formats, and characteristics for comprehensive testing.
"""

import os
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


class TestDataGenerator:
    """Generates test data files for S3 sync service testing."""
    
    def __init__(self, base_dir: str = "test-data"):
        """Initialize the test data generator."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
    def generate_text_file(self, path: str, size_bytes: int) -> None:
        """Generate a text file with specified size."""
        content_lines = []
        current_size = 0
        line_number = 1
        
        while current_size < size_bytes:
            line = f"Line {line_number}: This is test content for the S3 sync service. " \
                   f"Generated at {datetime.now().isoformat()}. Random data: {self._random_string(20)}\n"
            
            if current_size + len(line.encode()) > size_bytes:
                # Truncate the last line to fit exact size
                remaining = size_bytes - current_size
                line = line[:remaining]
                if not line.endswith('\n'):
                    line = line[:-1] + '\n'
            
            content_lines.append(line)
            current_size += len(line.encode())
            line_number += 1
        
        file_path = self.base_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(content_lines)
    
    def generate_json_file(self, path: str, complexity: str = "medium") -> None:
        """Generate a JSON file with varying complexity."""
        if complexity == "simple":
            data = {
                "id": random.randint(1, 1000),
                "name": f"test_item_{self._random_string(5)}",
                "timestamp": datetime.now().isoformat(),
                "active": random.choice([True, False])
            }
        elif complexity == "medium":
            data = {
                "metadata": {
                    "id": str(random.randint(1000, 9999)),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": (datetime.now() + timedelta(hours=1)).isoformat(),
                    "version": "1.0.0"
                },
                "config": {
                    "settings": {
                        "debug": True,
                        "timeout": random.randint(30, 300),
                        "retries": random.randint(1, 5)
                    },
                    "features": [
                        "sync", "backup", "restore", "monitor"
                    ]
                },
                "data": [
                    {
                        "type": "file",
                        "path": f"/test/path/{i}.txt",
                        "size": random.randint(100, 10000)
                    }
                    for i in range(random.randint(5, 15))
                ]
            }
        else:  # complex
            data = {
                "schema_version": "2.1.0",
                "generated_at": datetime.now().isoformat(),
                "test_suite": {
                    "name": "S3 Sync Service Test Suite",
                    "scenarios": [
                        {
                            "id": f"scenario_{i}",
                            "name": f"Test Scenario {i}",
                            "description": f"Complex test scenario {i} for sync service validation",
                            "parameters": {
                                "file_count": random.randint(10, 100),
                                "size_range": {
                                    "min": random.randint(100, 1000),
                                    "max": random.randint(10000, 100000)
                                },
                                "operations": random.sample(
                                    ["create", "update", "delete", "rename", "move"], 
                                    random.randint(2, 5)
                                )
                            },
                            "expected_results": {
                                "success_rate": random.uniform(0.95, 1.0),
                                "max_duration_seconds": random.randint(60, 300),
                                "error_tolerance": random.uniform(0.0, 0.05)
                            }
                        }
                        for i in range(random.randint(3, 8))
                    ]
                },
                "environment": {
                    "s3_buckets": ["customer-bucket", "target-bucket"],
                    "api_endpoints": [
                        "http://mock-api:8001/updatePermissions",
                        "http://mock-api:8001/saveToDisk",
                        "http://mock-api:8001/pubSubFullList"
                    ],
                    "database": "sqlite:///test_sync.db"
                }
            }
        
        file_path = self.base_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def generate_csv_file(self, path: str, rows: int = 100) -> None:
        """Generate a CSV file with test data."""
        headers = ["id", "filename", "size_bytes", "mime_type", "created_at", "permissions", "owner"]
        
        file_path = self.base_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(','.join(headers) + '\n')
            
            # Write data rows
            for i in range(1, rows + 1):
                row_data = [
                    str(i),
                    f"test_file_{i}.{random.choice(['txt', 'pdf', 'jpg', 'docx', 'json'])}",
                    str(random.randint(100, 1000000)),
                    random.choice(['text/plain', 'application/pdf', 'image/jpeg', 
                                 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                 'application/json']),
                    (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                    random.choice(['rw-r--r--', 'rwxr-xr-x', 'rw-rw-r--', 'rw-------']),
                    random.choice(['user', 'admin', 'system', 'service'])
                ]
                f.write(','.join(row_data) + '\n')
    
    def generate_log_file(self, path: str, entries: int = 50) -> None:
        """Generate a log file with realistic log entries."""
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        components = ['sync_service', 's3_manager', 'database', 'api_client', 'event_processor']
        
        file_path = self.base_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            base_time = datetime.now() - timedelta(hours=24)
            
            for i in range(entries):
                timestamp = base_time + timedelta(minutes=random.randint(0, 1440))
                level = random.choice(log_levels)
                component = random.choice(components)
                
                if level == 'ERROR':
                    messages = [
                        "Failed to connect to S3 bucket",
                        "Database operation timeout",
                        "API endpoint returned 500 error",
                        "File processing failed",
                        "Invalid event format received"
                    ]
                elif level == 'WARNING':
                    messages = [
                        "Retrying failed operation",
                        "High memory usage detected",
                        "Slow API response time",
                        "Large file detected",
                        "Rate limit approaching"
                    ]
                else:
                    messages = [
                        "Operation completed successfully",
                        "File synchronized",
                        "Event processed",
                        "Database updated",
                        "API call successful"
                    ]
                
                message = random.choice(messages)
                log_entry = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} - {level} - {component} - {message}\n"
                f.write(log_entry)
    
    def generate_binary_file(self, path: str, size_bytes: int) -> None:
        """Generate a binary file with random data."""
        file_path = self.base_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            # Generate random binary data
            data = bytes([random.randint(0, 255) for _ in range(size_bytes)])
            f.write(data)
    
    def generate_special_chars_files(self) -> None:
        """Generate files with special characters in names."""
        special_dir = self.base_dir / "special-chars"
        special_dir.mkdir(exist_ok=True)
        
        special_names = [
            "file with spaces.txt",
            "file@#$%.txt",
            "file[1].txt",
            "file(copy).txt",
            "файл.txt",  # Cyrillic
            "文件.txt",   # Chinese
            "ファイル.txt", # Japanese
            "très_spécial.txt",  # French accents
            "file&more.txt",
            "file+plus.txt"
        ]
        
        for name in special_names:
            try:
                content = f"This is a test file with special characters in the name: {name}\n"
                content += f"Generated at: {datetime.now().isoformat()}\n"
                
                file_path = special_dir / name
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except (OSError, UnicodeError) as e:
                print(f"Could not create file {name}: {e}")
    
    def _random_string(self, length: int) -> str:
        """Generate a random string of specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def generate_test_suite(self) -> None:
        """Generate a complete test suite with various file types and sizes."""
        print("Generating comprehensive test data suite...")
        
        # Small files (< 1KB)
        self.generate_text_file("small/tiny.txt", 50)
        self.generate_text_file("small/small.txt", 500)
        self.generate_json_file("small/config.json", "simple")
        
        # Medium files (1KB - 100KB)
        self.generate_text_file("medium/medium.txt", 5000)
        self.generate_json_file("medium/data.json", "medium")
        self.generate_csv_file("medium/records.csv", 200)
        self.generate_log_file("medium/app.log", 100)
        
        # Large files (> 100KB)
        self.generate_text_file("large/large.txt", 150000)
        self.generate_json_file("large/complex.json", "complex")
        self.generate_csv_file("large/dataset.csv", 2000)
        self.generate_log_file("large/system.log", 1000)
        self.generate_binary_file("large/binary.dat", 200000)
        
        # Special character files
        self.generate_special_chars_files()
        
        # Nested directory structure
        nested_files = [
            "level1/file1.txt",
            "level1/level2/file2.txt",
            "level1/level2/level3/file3.txt",
            "level1/level2/level3/level4/deep_file.txt"
        ]
        
        for nested_file in nested_files:
            self.generate_text_file(nested_file, random.randint(100, 5000))
        
        print("Test data generation completed!")
        print(f"Files generated in: {self.base_dir.absolute()}")


if __name__ == "__main__":
    generator = TestDataGenerator()
    generator.generate_test_suite()