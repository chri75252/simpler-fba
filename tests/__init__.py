"""
Amazon FBA Agent System v3.5 - Test Package

This package contains all test modules for the Amazon FBA Agent System.
Tests are organized by component and test type for clear structure and maintainability.

Test Organization:
    unit/           - Unit tests for individual components
    integration/    - Integration tests for component interactions  
    e2e/           - End-to-end tests for complete workflows
    fixtures/      - Test data and mock objects
    conftest.py    - Shared pytest configuration and fixtures

Test Categories:
    - Unit Tests: Test individual functions/classes in isolation
    - Integration Tests: Test interactions between components
    - API Tests: Test external API integrations (with mocking)
    - Performance Tests: Test system performance and benchmarks
    - Security Tests: Test security aspects and vulnerability scanning

Running Tests:
    # Run all tests
    pytest
    
    # Run specific test categories
    pytest -m unit
    pytest -m integration  
    pytest -m "not slow"
    
    # Run with coverage
    pytest --cov=tools --cov=config --cov=utils
    
    # Run in parallel
    pytest -n auto
    
    # Run with tox for full environment testing
    tox

Environment Variables for Testing:
    TEST_MODE=true              - Enable test mode
    MOCK_EXTERNAL_APIS=true     - Mock external API calls
    TEST_DATA_DIR=tests/fixtures - Test data location
    LOG_LEVEL=WARNING           - Reduce log noise during tests
"""

import os
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools"))
sys.path.insert(0, str(project_root / "config"))
sys.path.insert(0, str(project_root / "utils"))

# Test configuration constants
TEST_DATA_DIR = project_root / "tests" / "fixtures"
MOCK_API_RESPONSES_DIR = TEST_DATA_DIR / "api_responses"
SAMPLE_CONFIGS_DIR = TEST_DATA_DIR / "configs"

# Ensure test directories exist
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
MOCK_API_RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

# Test environment setup
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("MOCK_EXTERNAL_APIS", "true")
os.environ.setdefault("TEST_DATA_DIR", str(TEST_DATA_DIR))
os.environ.setdefault("LOG_LEVEL", "WARNING")

__version__ = "3.5.0"
__author__ = "Amazon FBA Agent System Team"