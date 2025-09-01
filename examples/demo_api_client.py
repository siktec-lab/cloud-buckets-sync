#!/usr/bin/env python3
"""
Simple demo of the Infrastructure API client.

Shows basic usage of all API endpoints.
"""
import io
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sync_service.clients.infrastructure_api import InfrastructureAPI
from loguru import logger


def main():
    """Demo API client functionality."""
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> - <level>{message}</level>", level="INFO")
    
    logger.info("🔌 Infrastructure API Demo")
    
    try:
        # Initialize API client
        api = InfrastructureAPI("http://localhost:8001")
        
        # Health check
        if not api.health_check():
            logger.error("❌ API server not responding")
            return 1
        
        logger.success("✅ API server is healthy")
        
        # Demo permissions
        logger.info("📋 Getting file permissions...")
        permissions = api.update_permissions("/demo/test.txt")
        logger.info(f"Permissions: {permissions.get('permissions')}")
        
        # Demo file operations
        logger.info("💾 Creating a file...")
        content = b"Hello from API demo!"
        file_stream = io.BytesIO(content)
        
        result = api.save_to_disk(
            operation="create",
            file_path="/demo/api_test.txt",
            file_stream=file_stream,
            size=len(content),
            file_type="text/plain"
        )
        logger.info(f"Created file with ID: {result.get('internal_id')}")
        
        # Demo events
        logger.info("📡 Getting recent events...")
        events = api.get_pub_sub_events(count=3)
        logger.info(f"Retrieved {len(events)} events")
        
        for event in events:
            logger.info(f"  • {event.event_type}: {event.file_path}")
        
        logger.success("🎉 API demo completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())