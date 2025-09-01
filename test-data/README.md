# Test Data for S3 Sync Service

This directory contains comprehensive test data for the S3 sync service, including various file types, sizes, and test scenarios.

## Directory Structure

```
test-data/
├── README.md                    # This file
├── test_scenarios.md           # Comprehensive test scenarios documentation
├── sample_pubsub_events.json   # Sample pub/sub events for testing
├── generate_test_data.py       # Script to generate additional test data
├── sample1.txt                 # Basic text file (existing)
├── documents/                  # Document files
│   ├── contract.pdf           # Sample PDF document
│   ├── readme.md              # Markdown documentation
│   ├── report.pdf             # Existing PDF (from init setup)
│   └── spreadsheet.csv        # CSV data file
├── images/                     # Image files
│   ├── logo.svg               # SVG vector image
│   ├── photo.jpg              # Existing photo (from init setup)
│   └── sample_image.png       # Minimal PNG image
├── code/                       # Code files
│   ├── app.py                 # Python application
│   ├── config.json            # JSON configuration
│   └── script.sh              # Shell script
└── logs/                       # Log files
    ├── application.log         # Application log entries
    └── error.log               # Error log entries
```

## File Categories

### Small Files (< 1KB)
- `sample1.txt` - Basic text content (existing)
- `sample_image.png` - Minimal PNG image
- `code/config.json` - JSON configuration file

### Medium Files (1KB - 100KB)
- `documents/readme.md` - Markdown documentation (~2KB)
- `documents/spreadsheet.csv` - CSV data file (~1KB)
- `code/app.py` - Python application code (~4KB)
- `images/logo.svg` - SVG vector image (~2KB)
- `logs/application.log` - Application log file (~3KB)
- `logs/error.log` - Error log file (~1KB)

### Large Files (> 100KB)
- `documents/contract.pdf` - PDF document (simulated structure)
- `code/script.sh` - Shell script with extensive content

## Test Data Types

### Documents
- **PDF files**: Simulated PDF structure for testing document handling
- **Markdown files**: Documentation with various formatting
- **CSV files**: Structured data with headers and multiple rows

### Images
- **SVG files**: Vector graphics with embedded styling
- **PNG files**: Raster images (base64 encoded for testing)
- **JPG files**: Existing photo files from initial setup

### Code Files
- **Python files**: Complete application code with classes and functions
- **Shell scripts**: Executable scripts with various operations
- **JSON files**: Configuration and data files with nested structures

### Log Files
- **Application logs**: Realistic log entries with timestamps and levels
- **Error logs**: Error-specific log entries for testing error handling

## Test Scenarios

The `test_scenarios.md` file contains comprehensive test scenarios covering:

- **File Operations**: Create, update, delete, rename, move
- **Size Categories**: Tiny, small, medium, large files
- **Special Cases**: Unicode filenames, special characters, nested paths
- **Error Conditions**: Corrupted files, network issues, permission problems
- **Performance Tests**: High volume, concurrent operations, throughput

## Sample Events

The `sample_pubsub_events.json` file contains realistic pub/sub events for testing:

- **Event Types**: create, delete, rename, move, change_permission
- **Metadata**: File sizes, MIME types, permissions, timestamps
- **Realistic Timing**: Events spread over several hours
- **Various File Types**: Documents, images, code, logs, archives

## Usage

### Manual Testing
Copy files to MinIO customer bucket for manual testing:
```bash
# Using MinIO client
mc cp --recursive test-data/ customer/customer-bucket/
```

### Automated Testing
Use the test data in automated test suites:
```python
# In test files
TEST_DATA_DIR = "test-data"
sample_files = [
    "documents/readme.md",
    "images/logo.svg",
    "code/app.py"
]
```

### Generate Additional Data
Run the test data generator for more files:
```bash
python test-data/generate_test_data.py
```

## Integration with Docker

The test data is automatically copied to the MinIO customer bucket during Docker initialization via the `scripts/init-buckets.sh` script.

## API Testing

### Mock API Endpoints
The test data works with these mock API endpoints:

- **updatePermissions**: Test with various file paths from test data
- **saveToDisk**: Upload test files and verify storage
- **pubSubFullList**: Use sample events from `sample_pubsub_events.json`

### Example API Calls
```bash
# Test updatePermissions
curl -X POST http://localhost:8001/updatePermissions \
  -F "file_path=/documents/readme.md"

# Test saveToDisk with file upload
curl -X POST http://localhost:8001/saveToDisk \
  -F "operation=create" \
  -F "file_path=/test/upload.txt" \
  -F "file=@test-data/sample1.txt"

# Test pubSubFullList
curl http://localhost:8001/pubSubFullList?count=5
```

## File Characteristics

### Realistic Content
- All files contain realistic content appropriate to their type
- Timestamps and metadata reflect actual usage patterns
- File sizes vary to test different scenarios

### Special Features
- **Unicode support**: Files with international characters
- **Nested structures**: Multi-level directory hierarchies  
- **Various formats**: Text, binary, structured data
- **Metadata rich**: Files include relevant metadata for testing

## Maintenance

### Adding New Test Data
1. Create files in appropriate subdirectories
2. Update this README with new file descriptions
3. Add corresponding test scenarios to `test_scenarios.md`
4. Include new file types in `generate_test_data.py` if needed

### File Naming Conventions
- Use descriptive names that indicate file purpose
- Include file extensions appropriate to content type
- Use lowercase with underscores for consistency
- Avoid spaces in automated test files (use special-chars/ for testing spaces)

## Requirements Coverage

This test data addresses the following requirements:

- **Requirement 5.3**: Various file types and sizes for comprehensive testing
- **Requirement 5.4**: Realistic mock data for API endpoint testing
- **Integration testing**: End-to-end workflow validation
- **Performance testing**: Files of different sizes for load testing
- **Error handling**: Corrupted and edge-case files for robustness testing