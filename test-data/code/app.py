#!/usr/bin/env python3
"""
Sample Python application for testing S3 sync service.

This file represents a typical Python application that might be
synchronized between S3 buckets.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional


class SampleApplication:
    """Sample application class for testing purposes."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the application with configuration."""
        self.config_path = config_path
        self.config = self.load_config()
        self.logger = self.setup_logging()
        
    def load_config(self) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "app_name": "Sample App",
                "version": "1.0.0",
                "debug": True,
                "database_url": "sqlite:///sample.db"
            }
    
    def setup_logging(self) -> logging.Logger:
        """Set up application logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def process_data(self, data: List[Dict]) -> List[Dict]:
        """Process input data and return results."""
        self.logger.info(f"Processing {len(data)} records")
        
        processed = []
        for item in data:
            processed_item = {
                **item,
                "processed_at": datetime.now().isoformat(),
                "status": "processed"
            }
            processed.append(processed_item)
        
        self.logger.info(f"Processed {len(processed)} records successfully")
        return processed
    
    def run(self):
        """Main application entry point."""
        self.logger.info("Starting Sample Application")
        
        # Sample data processing
        sample_data = [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300}
        ]
        
        results = self.process_data(sample_data)
        
        self.logger.info("Application completed successfully")
        return results


if __name__ == "__main__":
    app = SampleApplication()
    results = app.run()
    print(json.dumps(results, indent=2))