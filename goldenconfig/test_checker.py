#!/usr/bin/env python3
"""
Test script for the Splunk Configuration Checker

This script performs basic tests to verify the functionality of the
configuration checker without requiring a full Splunk installation.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from splunk_config_checker import SplunkConfigChecker, SplunkRole, ConfigCheck


def create_test_config():
    """Create a test configuration file"""
    test_config = """
###BEGIN SEARCH HEADS###

###server.conf###
[httpServer]
busyKeepAliveIdleTimeout = 120
streamInWriteTimeout = 30

[sslConfig]
useClientSSLCompression = false

###limits.conf###
[search]
remote_timeline_connection_timeout = 30

###END SEARCH HEADS###

###BEGIN INDEXERS###

###server.conf###
[clustering]
heartbeat_period = 10
cxn_timeout = 300

###END INDEXERS###
"""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(test_config.strip())
        return f.name


def test_config_parsing():
    """Test configuration file parsing"""
    print("Testing configuration file parsing...")
    
    # Create a mock checker (won't validate Splunk installation for testing)
    class MockChecker(SplunkConfigChecker):
        def __init__(self):
            self.splunk_home = "/fake/splunk"
            self.btool_path = "/fake/splunk/bin/splunk"
            self.config_checks = []
        
        def validate_splunk_installation(self):
            return True
    
    checker = MockChecker()
    config_file = create_test_config()
    
    try:
        # Test parsing
        checker.parse_config_file(config_file)
        
        print(f"✓ Parsed {len(checker.config_checks)} configuration checks")
        
        # Verify we got expected results
        search_head_checks = [c for c in checker.config_checks if c.role == SplunkRole.SEARCH_HEAD]
        indexer_checks = [c for c in checker.config_checks if c.role == SplunkRole.INDEXER]
        
        print(f"✓ Found {len(search_head_checks)} search head checks")
        print(f"✓ Found {len(indexer_checks)} indexer checks")
        
        # Test specific configurations
        http_server_checks = [c for c in search_head_checks if c.stanza == "httpServer"]
        print(f"✓ Found {len(http_server_checks)} httpServer checks")
        
        # Test role filtering
        original_count = len(checker.config_checks)
        checker.config_checks = [c for c in checker.config_checks if c.role == SplunkRole.SEARCH_HEAD]
        print(f"✓ Role filtering: {original_count} -> {len(checker.config_checks)} checks")
        
        return True
        
    except Exception as e:
        print(f"✗ Parsing test failed: {e}")
        return False
    
    finally:
        # Clean up
        os.unlink(config_file)


def test_value_comparison():
    """Test value comparison logic"""
    print("\nTesting value comparison...")
    
    class MockChecker(SplunkConfigChecker):
        def __init__(self):
            pass
    
    checker = MockChecker()
    
    # Test cases
    test_cases = [
        ("120", "120", True, "Exact match"),
        ("true", "True", True, "Case insensitive boolean"),
        ("false", "FALSE", True, "Case insensitive boolean"),
        ("auto", "AUTO", True, "Case insensitive auto"),
        ("30", "30.0", True, "Numeric conversion"),
        ("100", "200", False, "Numeric mismatch"),
        ("test", "different", False, "String mismatch"),
    ]
    
    all_passed = True
    for actual, expected, should_match, description in test_cases:
        result = checker._compare_values(actual, expected)
        if result == should_match:
            print(f"✓ {description}")
        else:
            print(f"✗ {description}: expected {should_match}, got {result}")
            all_passed = False
    
    return all_passed


def test_dry_run():
    """Test dry run functionality"""
    print("\nTesting dry run mode...")
    
    config_file = create_test_config()
    
    try:
        # Run the actual script in dry-run mode
        cmd = [
            sys.executable, 
            "splunk_config_checker.py",
            "--config-file", config_file,
            "--dry-run",
            "--verbose"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✓ Dry run completed successfully")
            if "Dry run mode" in result.stdout:
                print("✓ Dry run mode detected correctly")
            if "configuration checks" in result.stdout:
                print("✓ Configuration parsing completed")
            return True
        else:
            print(f"✗ Dry run failed with return code {result.returncode}")
            print(f"Error output: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"✗ Dry run test failed: {e}")
        return False
    
    finally:
        os.unlink(config_file)


def main():
    """Run all tests"""
    print("Splunk Configuration Checker - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Configuration Parsing", test_config_parsing),
        ("Value Comparison", test_value_comparison),
        ("Dry Run Mode", test_dry_run),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()