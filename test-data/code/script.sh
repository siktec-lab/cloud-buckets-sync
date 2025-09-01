#!/bin/bash

# Sample shell script for testing S3 sync service
# This script demonstrates various file operations that might be synchronized

set -e

echo "Starting sample script execution..."

# Configuration
APP_NAME="S3 Sync Test Script"
VERSION="1.0.0"
LOG_FILE="/tmp/script_execution.log"

# Function to log messages
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Function to create test files
create_test_files() {
    log_message "Creating test files..."
    
    # Create temporary directory
    TEST_DIR="/tmp/sync_test_$$"
    mkdir -p "$TEST_DIR"
    
    # Generate various file types
    echo "Small text file content" > "$TEST_DIR/small.txt"
    
    # Generate larger text file
    for i in {1..100}; do
        echo "Line $i: This is a test line with some content to make the file larger" >> "$TEST_DIR/large.txt"
    done
    
    # Create JSON data file
    cat > "$TEST_DIR/data.json" << EOF
{
  "test_data": {
    "files_created": $(ls "$TEST_DIR" | wc -l),
    "timestamp": "$(date -Iseconds)",
    "script_version": "$VERSION"
  }
}
EOF
    
    log_message "Created test files in $TEST_DIR"
    ls -la "$TEST_DIR"
}

# Function to simulate file operations
simulate_operations() {
    log_message "Simulating file operations..."
    
    # Copy operations
    cp "$TEST_DIR/small.txt" "$TEST_DIR/small_copy.txt"
    
    # Move operations
    mv "$TEST_DIR/small_copy.txt" "$TEST_DIR/renamed_file.txt"
    
    # Modify file permissions
    chmod 755 "$TEST_DIR/data.json"
    chmod 644 "$TEST_DIR/large.txt"
    
    log_message "File operations completed"
}

# Function to cleanup
cleanup() {
    log_message "Cleaning up temporary files..."
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
        log_message "Cleanup completed"
    fi
}

# Main execution
main() {
    log_message "Starting $APP_NAME v$VERSION"
    
    create_test_files
    simulate_operations
    
    log_message "Script execution completed successfully"
    
    # Cleanup on exit
    trap cleanup EXIT
}

# Execute main function
main "$@"