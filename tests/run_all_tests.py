#!/usr/bin/env python3
"""
Test runner for all S3 sync service tests.
"""
import sys
import subprocess
from pathlib import Path
from loguru import logger


def run_test(test_file):
    """Run a single test file and return success status."""
    logger.info(f"Running {test_file}...")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            logger.success(f"✅ {test_file}: PASSED")
            return True
        else:
            logger.error(f"❌ {test_file}: FAILED")
            logger.error(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ {test_file}: ERROR - {str(e)}")
        return False


def main():
    """Run all tests."""
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> - <level>{message}</level>", level="INFO")
    
    logger.info("🧪 Running All S3 Sync Service Tests")
    
    test_files = [
        "tests/test_initial_sync.py",
        "tests/test_api_integration.py"
    ]
    
    results = []
    for test_file in test_files:
        success = run_test(test_file)
        results.append((test_file, success))
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    for test_file, success in results:
        status = "PASS" if success else "FAIL"
        icon = "✅" if success else "❌"
        logger.info(f"{icon} {Path(test_file).name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        logger.success("🎉 All test suites passed!")
        return 0
    else:
        logger.error(f"❌ {total - passed} test suite(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())