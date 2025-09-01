# Test Scenarios for S3 Sync Service

## Overview
This document defines comprehensive test scenarios for the S3 sync service, covering various file types, sizes, and operations.

## File Type Test Scenarios

### Small Files (< 1KB)
- **sample1.txt** - Basic text file (existing)
- **config.json** - JSON configuration file
- **sample_image.png** - Minimal PNG image (base64 encoded)

### Medium Files (1KB - 100KB)
- **readme.md** - Markdown documentation (~2KB)
- **application.log** - Application log file (~3KB)
- **app.py** - Python application code (~4KB)
- **logo.svg** - SVG vector image (~2KB)
- **spreadsheet.csv** - CSV data file (~1KB)

### Large Files (> 100KB)
- **contract.pdf** - PDF document (simulated structure)
- **script.sh** - Shell script with extensive content
- **error.log** - Extended error log file

## File Operation Test Scenarios

### Create Operations
1. **New file creation** - Upload new files to customer bucket
2. **Batch file creation** - Multiple files created simultaneously
3. **Nested directory creation** - Files in subdirectories

### Update Operations
1. **Content modification** - Existing file content changes
2. **Permission changes** - File permission updates
3. **Metadata updates** - File metadata modifications

### Delete Operations
1. **Single file deletion** - Remove individual files
2. **Batch deletion** - Multiple files deleted
3. **Directory deletion** - Remove entire directories

### Rename/Move Operations
1. **File rename** - Change file name in same directory
2. **File move** - Move file to different directory
3. **Directory restructure** - Move multiple files/directories

## Size-based Test Scenarios

### Tiny Files (< 100 bytes)
- Empty configuration files
- Small text snippets
- Minimal JSON responses

### Small Files (100 bytes - 1KB)
- Basic text documents
- Simple configuration files
- Small log entries

### Medium Files (1KB - 1MB)
- Application code files
- Documentation files
- Standard log files
- Small images

### Large Files (1MB - 10MB)
- High-resolution images
- Detailed PDF documents
- Large datasets
- Video files (simulated)

## Special Character Test Scenarios

### File Names with Special Characters
- Files with spaces: "file with spaces.txt"
- Files with unicode: "файл.txt", "文件.txt"
- Files with symbols: "file@#$.txt", "file[1].txt"

### Path Scenarios
- Deep nested paths: "/level1/level2/level3/file.txt"
- Long file names: Files with names > 100 characters
- Mixed case paths: "/CamelCase/snake_case/file.TXT"

## Concurrent Operation Scenarios

### Simultaneous Operations
1. **Multiple creates** - Several files created at once
2. **Mixed operations** - Create, update, delete happening together
3. **Race conditions** - Same file modified by multiple operations

### Event Processing Scenarios
1. **Event ordering** - Process events in chronological order
2. **Event batching** - Handle multiple events in batches
3. **Event deduplication** - Handle duplicate events gracefully

## Error Handling Scenarios

### Network Issues
1. **S3 connection timeout** - Simulate network delays
2. **API endpoint unavailable** - Mock API server down
3. **Partial failures** - Some operations succeed, others fail

### Data Corruption
1. **Corrupted files** - Files with invalid content
2. **Invalid metadata** - Malformed file information
3. **CSV corruption** - Damaged state files

### Permission Issues
1. **Access denied** - Insufficient permissions
2. **Read-only files** - Files that cannot be modified
3. **Directory permissions** - Folder access restrictions

## Performance Test Scenarios

### Volume Testing
- **High file count** - Sync 1000+ files
- **Large file sizes** - Files > 100MB (simulated)
- **Deep directory structures** - 10+ levels deep

### Throughput Testing
- **Batch processing** - Process files in batches of 50, 100, 200
- **Parallel operations** - Multiple sync operations simultaneously
- **Rate limiting** - Respect API rate limits

## Integration Test Scenarios

### End-to-End Workflows
1. **Initial sync** - Complete bucket synchronization
2. **Incremental sync** - Process only changed files
3. **Recovery sync** - Recover from failed operations

### API Integration
1. **updatePermissions** - Test permission API calls
2. **saveToDisk** - Test file storage API calls
3. **pubSubFullList** - Test event retrieval API calls
4. **reportResults** - Test result reporting API calls

## Data Validation Scenarios

### File Integrity
1. **Checksum validation** - Verify file integrity after sync
2. **Size validation** - Confirm file sizes match
3. **Timestamp validation** - Check modification times

### State Management
1. **CSV state tracking** - Verify state file accuracy
2. **Database consistency** - Check database records
3. **Event correlation** - Match events to file changes

## Edge Cases

### Boundary Conditions
- Empty files (0 bytes)
- Maximum file name length
- Maximum path depth
- Special system files

### Unusual Scenarios
- Files created and deleted rapidly
- Circular rename operations
- Files with identical content but different names
- Symbolic links and shortcuts

## Test Data Organization

```
test-data/
├── documents/          # Document files (PDF, MD, CSV)
├── images/            # Image files (JPG, PNG, SVG)
├── code/              # Code files (PY, SH, JSON)
├── logs/              # Log files (application, error)
├── archives/          # Archive files (ZIP, TAR)
├── special-chars/     # Files with special characters
├── large-files/       # Large test files
└── corrupted/         # Intentionally corrupted files
```

## Expected Outcomes

Each test scenario should verify:
1. **Correct operation execution** - Operations complete successfully
2. **Data integrity** - Files are synchronized accurately
3. **State consistency** - System state remains consistent
4. **Error handling** - Failures are handled gracefully
5. **Performance** - Operations complete within acceptable time
6. **Logging** - All operations are properly logged