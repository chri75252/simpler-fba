"""
Amazon FBA Agent System v3.5 - Pytest Configuration and Shared Fixtures

This module provides shared pytest fixtures and configuration for all tests.
It includes common test utilities, mock objects, and test data setup.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

import pytest
import asyncio
try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    Faker = None


# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically set up test environment for all tests."""
    # Set test environment variables
    os.environ["TEST_MODE"] = "true"
    os.environ["MOCK_EXTERNAL_APIS"] = "true"
    os.environ["LOG_LEVEL"] = "WARNING"
    
    # Disable actual API calls
    os.environ["OPENAI_API_KEY"] = "test-key-12345"
    os.environ["KEEPA_API_KEY"] = "test-keepa-key"
    
    yield
    
    # Cleanup after test
    # Reset any global state if needed


@pytest.fixture
def fake():
    """Provide a Faker instance for generating test data."""
    return Faker()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_data_dir():
    """Provide the test data directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_product_data(fake):
    """Generate sample product data for testing."""
    return {
        "title": fake.catch_phrase(),
        "price": round(fake.random.uniform(5.0, 50.0), 2),
        "ean": fake.ean13(),
        "category": fake.word(),
        "supplier_url": fake.url(),
        "image_url": fake.image_url(),
        "description": fake.text(max_nb_chars=200),
        "in_stock": fake.boolean(),
        "rating": round(fake.random.uniform(3.0, 5.0), 1),
        "review_count": fake.random_int(min=0, max=1000),
    }


@pytest.fixture
def sample_amazon_data(fake):
    """Generate sample Amazon product data for testing."""
    return {
        "asin": fake.uuid4()[:10].upper(),
        "title": fake.catch_phrase(),
        "price": round(fake.random.uniform(10.0, 100.0), 2),
        "category": fake.word(),
        "rank": fake.random_int(min=1, max=100000),
        "fba_fees": round(fake.random.uniform(2.0, 10.0), 2),
        "dimensions": {
            "length": fake.random.uniform(5.0, 50.0),
            "width": fake.random.uniform(5.0, 50.0), 
            "height": fake.random.uniform(5.0, 50.0),
            "weight": fake.random.uniform(0.1, 5.0),
        },
        "keepa_data": {
            "avg_30d_price": round(fake.random.uniform(15.0, 80.0), 2),
            "sales_rank_drops": fake.random_int(min=0, max=50),
            "price_history": [
                round(fake.random.uniform(10.0, 100.0), 2) 
                for _ in range(30)
            ],
        },
    }


@pytest.fixture
def sample_config_data():
    """Provide sample configuration data for testing."""
    return {
        "system": {
            "max_products_per_category": 0,
            "max_analyzed_products": 0,
            "max_products_per_cycle": 0,
            "request_timeout": 30,
            "browser_timeout": 60,
        },
        "ai_features": {
            "category_selection": {
                "mode": "v2",
                "enabled": True,
                "temperature": 0.1,
            },
            "product_matching": {
                "enabled": True,
                "confidence_threshold": 0.8,
            },
        },
        "cache": {
            "type": "file",
            "ttl_hours": 24,
            "max_size_mb": 100,
        },
    }


@pytest.fixture  
def mock_openai_client():
    """Provide a mocked OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Mocked AI response"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_browser():
    """Provide a mocked browser instance for testing."""
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.new_page.return_value = mock_page
    
    # Mock common page methods
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])
    mock_page.evaluate = AsyncMock()
    mock_page.close = AsyncMock()
    
    return mock_browser


@pytest.fixture
def mock_cache_manager():
    """Provide a mocked cache manager for testing."""
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.exists.return_value = False
    mock_cache.clear.return_value = True
    return mock_cache


@pytest.fixture
def mock_requests_session():
    """Provide a mocked requests session for testing."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_response.text = "<html><body>Test content</body></html>"
    mock_session.get.return_value = mock_response
    mock_session.post.return_value = mock_response
    return mock_session


@pytest.fixture
def event_loop():
    """Provide an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Async mock helper for Python 3.8+ compatibility
class AsyncMock(MagicMock):
    """Async version of MagicMock for mocking async functions."""
    
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


# Test data generation helpers
def generate_test_products(count: int = 10, fake_instance: Faker = None) -> list:
    """Generate a list of test product data."""
    if fake_instance is None:
        fake_instance = Faker()
    
    products = []
    for _ in range(count):
        products.append({
            "title": fake_instance.catch_phrase(),
            "price": round(fake_instance.random.uniform(5.0, 50.0), 2),
            "ean": fake_instance.ean13(),
            "category": fake_instance.word(),
            "url": fake_instance.url(),
        })
    
    return products


def generate_test_categories(count: int = 5, fake_instance: Faker = None) -> list:
    """Generate a list of test category data."""
    if fake_instance is None:
        fake_instance = Faker()
    
    categories = []
    for _ in range(count):
        categories.append({
            "name": fake_instance.word().title(),
            "url": fake_instance.url(),
            "product_count": fake_instance.random_int(min=10, max=1000),
            "ai_score": round(fake_instance.random.uniform(0.5, 1.0), 2),
        })
    
    return categories


# Pytest hooks for custom behavior
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "api: mark test as requiring API access")
    config.addinivalue_line("markers", "browser: mark test as requiring browser")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            
        # Add browser marker if test uses browser fixtures
        if "browser" in str(item.function):
            item.add_marker(pytest.mark.browser)