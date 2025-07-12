"""
Test Schema Validation - Validates JSON outputs against strict schemas
====================================================================

Tests the three critical JSON files:
- cached_products.json
- ai_category_cache.json  
- linking_maps/linking_map.json

Uses JSONSchema validation with draft-2020-12 standard.
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from tools.output_verification_node import OutputVerificationNode, NeedsInterventionError
from utils.path_manager import path_manager


class TestSchemaValidation:
    """Test schema validation for FBA system outputs"""
    
    def setup_method(self):
        """Setup test environment"""
        self.verifier = OutputVerificationNode()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, filename: str, data: dict) -> Path:
        """Create test file with data"""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return file_path
    
    def test_cached_products_valid_schema(self):
        """Test valid cached_products.json schema"""
        valid_data = {
            "supplier_name": "test-supplier-com",
            "cached_at": "2025-06-28T10:00:00.000Z",
            "total_products": 2,
            "products": {
                "SKU123": {
                    "title": "Test Product 1",
                    "price": 9.99,
                    "url": "https://test.com/product1",
                    "image_url": "https://test.com/image1.jpg",
                    "ean": "1234567890123",
                    "upc": None,
                    "sku": "SKU123",
                    "source_category_url": "https://test.com/category",
                    "extraction_timestamp": "2025-06-28T10:00:00.000Z"
                },
                "EAN_5055453430411": {
                    "title": "Test Product 2", 
                    "price": 4.50,
                    "url": "https://test.com/product2",
                    "image_url": None,
                    "ean": "5055453430411",
                    "upc": "123456789012",
                    "sku": None,
                    "source_category_url": "https://test.com/category2",
                    "extraction_timestamp": "2025-06-28T10:05:00.000Z"
                }
            }
        }
        
        file_path = self.create_test_file("cached_products.json", valid_data)
        result = self.verifier._verify_single_file("cached_products", file_path)
        
        assert result["valid"] is True
        assert result["record_count"] == 2
        assert "errors" not in result
    
    def test_cached_products_invalid_schema(self):
        """Test invalid cached_products.json schema"""
        invalid_data = {
            "supplier_name": "",  # Empty string invalid
            "cached_at": "invalid-date",  # Invalid date format
            "total_products": "not-a-number",  # Should be integer
            "products": {
                "INVALID": {
                    "title": "",  # Empty title invalid
                    "price": -1,  # Negative price invalid
                    "url": "not-a-url",  # Invalid URL
                    # Missing required extraction_timestamp
                }
            }
        }
        
        file_path = self.create_test_file("cached_products_invalid.json", invalid_data)
        result = self.verifier._verify_single_file("cached_products", file_path)
        
        assert result["valid"] is False
        assert "error" in result
        assert result["critical"] is True
    
    def test_ai_category_cache_valid_schema(self):
        """Test valid ai_category_cache.json schema"""
        valid_data = {
            "supplier": "test-supplier-com",
            "url": "https://www.test-supplier.com",
            "created": "2025-06-28T10:00:00.000Z",
            "last_updated": "2025-06-28T11:00:00.000Z",
            "total_ai_calls": 2,
            "ai_suggestion_history": [
                {
                    "timestamp": "2025-06-28T10:00:00.000Z",
                    "session_context": {
                        "categories_discovered": 5,
                        "total_products_processed": 25,
                        "previous_categories_count": 0
                    },
                    "ai_suggestions": {
                        "top_3_urls": [
                            "https://test.com/category1",
                            "https://test.com/category2"
                        ],
                        "secondary_urls": [
                            "https://test.com/category3"
                        ],
                        "skip_urls": [],
                        "detailed_reasoning": {
                            "category_analysis": "Test reasoning",
                            "selection_criteria": "Test criteria"
                        },
                        "validation_results": {
                            "category1": {
                                "total_products": 10,
                                "success_rate": 0.9
                            }
                        }
                    }
                }
            ]
        }
        
        file_path = self.create_test_file("ai_category_cache.json", valid_data)
        result = self.verifier._verify_single_file("ai_category_cache", file_path)
        
        assert result["valid"] is True
        assert result["record_count"] == 1
    
    def test_ai_category_cache_invalid_schema(self):
        """Test invalid ai_category_cache.json schema"""
        invalid_data = {
            "supplier": 123,  # Should be string
            "url": "not-a-url",  # Invalid URL
            "created": "invalid-date",  # Invalid date
            "total_ai_calls": -1,  # Should be >= 0
            "ai_suggestion_history": [
                {
                    # Missing required timestamp
                    "session_context": {
                        "categories_discovered": -1,  # Should be >= 0
                        # Missing required total_products_processed
                    },
                    "ai_suggestions": {
                        "top_3_urls": ["not-a-url"],  # Invalid URL
                        # Missing required secondary_urls and skip_urls
                    }
                }
            ]
        }
        
        file_path = self.create_test_file("ai_category_cache_invalid.json", invalid_data)
        result = self.verifier._verify_single_file("ai_category_cache", file_path)
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_linking_map_valid_schema(self):
        """Test valid linking_map.json schema (array format)"""
        valid_data = [
            {
                "supplier_product_identifier": "EAN_1234567890123",
                "supplier_title_snippet": "Test Product 1 Description",
                "chosen_amazon_asin": "B0123456789",
                "amazon_title_snippet": "Amazon Product 1 Title",
                "amazon_ean_on_page": "1234567890123",
                "match_method": "EAN_search"
            },
            {
                "supplier_product_identifier": "SKU_TEST123",
                "supplier_title_snippet": "Test Product 2",
                "chosen_amazon_asin": "B0987654321",
                "amazon_title_snippet": "Amazon Product 2",
                "amazon_ean_on_page": None,
                "match_method": "title_search"
            }
        ]
        
        file_path = self.create_test_file("linking_map.json", valid_data)
        result = self.verifier._verify_single_file("linking_map", file_path)
        
        assert result["valid"] is True
        assert result["record_count"] == 2
    
    def test_linking_map_invalid_schema(self):
        """Test invalid linking_map.json schema"""
        invalid_data = [
            {
                "supplier_product_identifier": "",  # Empty string invalid
                "supplier_title_snippet": "Test",
                "chosen_amazon_asin": "INVALID_ASIN",  # Invalid ASIN format
                "amazon_title_snippet": "Test",
                "match_method": "invalid_method"  # Invalid method
                # Missing required fields
            },
            "not_an_object"  # Array should contain objects only
        ]
        
        file_path = self.create_test_file("linking_map_invalid.json", invalid_data)
        result = self.verifier._verify_single_file("linking_map", file_path)
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_linking_map_dict_format_invalid(self):
        """Test that dict format is rejected for linking map"""
        # Old dict format should be invalid
        invalid_dict_data = {
            "supplier": "test",
            "products": {
                "product1": {
                    "asin": "B0123456789"
                }
            }
        }
        
        file_path = self.create_test_file("linking_map_dict.json", invalid_dict_data)
        result = self.verifier._verify_single_file("linking_map", file_path)
        
        assert result["valid"] is False
        assert "array" in result["error"].lower()
    
    def test_content_quality_validation(self):
        """Test content quality validation beyond schema"""
        # Test low product count warning
        low_product_data = {
            "supplier_name": "test-supplier",
            "cached_at": "2025-06-28T10:00:00.000Z",
            "total_products": 2,  # Below minimum of 5
            "products": {
                "P1": {
                    "title": "Product 1",
                    "price": 1.0,
                    "url": "https://test.com/p1",
                    "extraction_timestamp": "2025-06-28T10:00:00.000Z"
                },
                "P2": {
                    "title": "Product 2",
                    "price": 2.0,
                    "url": "https://test.com/p2",
                    "extraction_timestamp": "2025-06-28T10:00:00.000Z"
                }
            }
        }
        
        file_path = self.create_test_file("low_products.json", low_product_data)
        result = self.verifier._verify_single_file("cached_products", file_path)
        
        assert result["valid"] is True  # Schema valid
        assert "content_warnings" in result
        assert any("Low product count" in warning for warning in result["content_warnings"])
        assert result["quality_score"] < 1.0
    
    def test_file_not_exists(self):
        """Test validation of non-existent file"""
        non_existent_path = self.temp_dir / "does_not_exist.json"
        result = self.verifier._verify_single_file("cached_products", non_existent_path)
        
        assert result["valid"] is False
        assert "does not exist" in result["error"]
        assert result["critical"] is True
    
    def test_empty_file(self):
        """Test validation of empty file"""
        empty_file = self.temp_dir / "empty.json"
        empty_file.touch()
        
        result = self.verifier._verify_single_file("cached_products", empty_file)
        
        assert result["valid"] is False
        assert "empty" in result["error"]
        assert result["critical"] is True
    
    def test_invalid_json(self):
        """Test validation of invalid JSON"""
        invalid_file = self.temp_dir / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
        
        result = self.verifier._verify_single_file("cached_products", invalid_file)
        
        assert result["valid"] is False
        assert "Invalid JSON" in result["error"]
        assert result["critical"] is True
    
    def test_full_supplier_verification_success(self):
        """Test full supplier verification with all valid files"""
        # Create run output directory structure
        run_dir = self.temp_dir / "test-supplier" / "20250628_100000_run"
        run_dir.mkdir(parents=True)
        
        # Create linking maps subdirectory
        linking_maps_dir = run_dir / "linking_maps"
        linking_maps_dir.mkdir()
        
        # Create valid cached_products.json
        cached_products = {
            "supplier_name": "test-supplier",
            "cached_at": "2025-06-28T10:00:00.000Z",
            "total_products": 5,  # Meets minimum
            "products": {
                f"P{i}": {
                    "title": f"Product {i}",
                    "price": i * 1.5,
                    "url": f"https://test.com/p{i}",
                    "ean": f"123456789012{i}",
                    "extraction_timestamp": "2025-06-28T10:00:00.000Z"
                }
                for i in range(1, 6)
            }
        }
        
        with open(run_dir / "cached_products.json", 'w') as f:
            json.dump(cached_products, f)
        
        # Create valid ai_category_cache.json
        ai_cache = {
            "supplier": "test-supplier",
            "url": "https://www.test-supplier.com",
            "created": "2025-06-28T10:00:00.000Z",
            "last_updated": "2025-06-28T10:00:00.000Z",
            "total_ai_calls": 1,
            "ai_suggestion_history": [
                {
                    "timestamp": "2025-06-28T10:00:00.000Z",
                    "session_context": {
                        "categories_discovered": 5,
                        "total_products_processed": 5
                    },
                    "ai_suggestions": {
                        "top_3_urls": [
                            "https://test.com/cat1",
                            "https://test.com/cat2",
                            "https://test.com/cat3"
                        ],
                        "secondary_urls": [],
                        "skip_urls": []
                    }
                }
            ]
        }
        
        with open(run_dir / "ai_category_cache.json", 'w') as f:
            json.dump(ai_cache, f)
        
        # Create valid linking_map.json
        linking_map = [
            {
                "supplier_product_identifier": "EAN_1234567890123",
                "supplier_title_snippet": "Test Product",
                "chosen_amazon_asin": "B0123456789",
                "amazon_title_snippet": "Amazon Product",
                "amazon_ean_on_page": "1234567890123",
                "match_method": "EAN_search"
            }
        ]
        
        with open(linking_maps_dir / "linking_map.json", 'w') as f:
            json.dump(linking_map, f)
        
        # Run full verification
        result = self.verifier.verify_output_files("test-supplier", run_dir)
        
        assert result["overall_status"] == "passed"
        assert len(result["files_verified"]) == 3
        assert all(file_result["valid"] for file_result in result["files_verified"].values())
    
    def test_full_supplier_verification_failure(self):
        """Test full supplier verification with intervention needed"""
        # Create run output directory with invalid files
        run_dir = self.temp_dir / "test-supplier" / "20250628_100000_run"
        run_dir.mkdir(parents=True)
        
        # Create invalid cached_products.json (missing required fields)
        invalid_products = {
            "supplier_name": "",  # Invalid empty name
            "total_products": 0
            # Missing required fields
        }
        
        with open(run_dir / "cached_products.json", 'w') as f:
            json.dump(invalid_products, f)
        
        # Test that NeedsInterventionError is raised
        with pytest.raises(NeedsInterventionError):
            self.verifier.verify_output_files("test-supplier", run_dir)


def test_yaml_diff_generation():
    """Test YAML diff generation for human review"""
    verifier = OutputVerificationNode()
    
    # This is more of an integration test to ensure diff generation works
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create file with schema violation
        invalid_data = {
            "supplier_name": 123,  # Should be string
            "cached_at": "2025-06-28T10:00:00.000Z",
            "total_products": 1,
            "products": {}
        }
        
        file_path = temp_dir / "invalid.json"
        with open(file_path, 'w') as f:
            json.dump(invalid_data, f)
        
        result = verifier._verify_single_file("cached_products", file_path)
        
        assert result["valid"] is False
        # Diff generation is optional, but if present should be string
        if "yaml_diff" in result:
            assert isinstance(result["yaml_diff"], str)
            assert len(result["yaml_diff"]) > 0
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])