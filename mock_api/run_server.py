#!/usr/bin/env python3
"""
Startup script for the mock API server.
"""

import uvicorn
from mock_api.server import app

if __name__ == "__main__":
    print("Starting Mock API Server...")
    print("Available endpoints:")
    print("  - GET  /                 : Health check")
    print("  - POST /updatePermissions : Get file permissions")
    print("  - POST /saveToDisk       : Save file with internal ID")
    print("  - GET  /pubSubFullList   : Get mock events")
    print("  - POST /reportResults    : Report sync results")
    print("\nServer will be available at: http://localhost:8001")
    print("API docs available at: http://localhost:8001/docs")
    
    uvicorn.run(
        "mock_api.server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Disable reload in container
        log_level="info"
    )