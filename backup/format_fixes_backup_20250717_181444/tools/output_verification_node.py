"""
Output Verification Node - JSONSchema validation for FBA system outputs
======================================================================

Implements:
- Build JSONSchema objects (draft-2020-12) for the three JSON files
- Use jsonschema.validate; raise NeedsInterventionError on failure
- Log YAML diff for human review using difflib.unified_diff
- Comprehensive validation of cached_products.json, ai_category_cache.json, linking_map.json
"""

import json
import logging
import difflib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import jsonschema
import yaml

try:
    from utils.path_manager import get_run_output_dir
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.path_manager import get_run_output_dir

logger = logging.getLogger(__name__)


class NeedsInterventionError(Exception):
    """Raised when output validation fails and requires human intervention"""
    pass


class OutputVerificationNode:
    """Validates FBA system outputs against strict schemas"""
    
    def __init__(self):
        self.schemas = self._build_schemas()
        logger.info("🔍 Output Verification Node initialized with JSONSchema validation")
    
    def _build_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Build JSONSchema objects for all three output files"""
        
        # Schema for cached_products.json
        cached_products_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://fba-system.internal/schemas/cached_products.json",
            "title": "Cached Products Schema",
            "type": "object",
            "required": ["supplier_name", "cached_at", "total_products", "products"],
            "properties": {
                "supplier_name": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9.-]+$",
                    "description": "Supplier domain identifier"
                },
                "cached_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO 8601 timestamp when cached"
                },
                "total_products": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Total number of products"
                },
                "products": {
                    "type": "object",
                    "patternProperties": {
                        "^[A-Z0-9_-]+$": {
                            "type": "object",
                            "required": ["title", "price", "url", "extraction_timestamp"],
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 500
                                },
                                "price": {
                                    "type": "number",
                                    "minimum": 0
                                },
                                "url": {
                                    "type": "string",
                                    "format": "uri"
                                },
                                "image_url": {
                                    "type": ["string", "null"],
                                    "format": "uri"
                                },
                                "ean": {
                                    "type": ["string", "null"],
                                    "pattern": "^[0-9]{8,14}$"
                                },
                                "upc": {
                                    "type": ["string", "null"],
                                    "pattern": "^[0-9]{12}$"
                                },
                                "sku": {
                                    "type": ["string", "null"]
                                },
                                "source_category_url": {
                                    "type": ["string", "null"],
                                    "format": "uri"
                                },
                                "extraction_timestamp": {
                                    "type": "string",
                                    "format": "date-time"
                                }
                            },
                            "additionalProperties": True
                        }
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": True
        }
        
        # Schema for ai_category_cache.json (clearance-king style)
        ai_category_cache_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://fba-system.internal/schemas/ai_category_cache.json",
            "title": "AI Category Cache Schema",
            "type": "object",
            "required": ["supplier", "url", "created", "last_updated", "total_ai_calls", "ai_suggestion_history"],
            "properties": {
                "supplier": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9.-]+$"
                },
                "url": {
                    "type": "string",
                    "format": "uri"
                },
                "created": {
                    "type": "string",
                    "format": "date-time"
                },
                "last_updated": {
                    "type": "string",
                    "format": "date-time"
                },
                "total_ai_calls": {
                    "type": "integer",
                    "minimum": 0
                },
                "ai_suggestion_history": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["timestamp", "session_context", "ai_suggestions"],
                        "properties": {
                            "timestamp": {
                                "type": "string",
                                "format": "date-time"
                            },
                            "session_context": {
                                "type": "object",
                                "required": ["categories_discovered", "total_products_processed"],
                                "properties": {
                                    "categories_discovered": {
                                        "type": "integer",
                                        "minimum": 0
                                    },
                                    "total_products_processed": {
                                        "type": "integer",
                                        "minimum": 0
                                    },
                                    "previous_categories_count": {
                                        "type": "integer",
                                        "minimum": 0
                                    }
                                },
                                "additionalProperties": True
                            },
                            "ai_suggestions": {
                                "type": "object",
                                "required": ["top_3_urls", "secondary_urls", "skip_urls"],
                                "properties": {
                                    "top_3_urls": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "format": "uri"
                                        }
                                    },
                                    "secondary_urls": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "format": "uri"
                                        }
                                    },
                                    "skip_urls": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "format": "uri"
                                        }
                                    },
                                    "detailed_reasoning": {
                                        "type": "object"
                                    },
                                    "validation_results": {
                                        "type": "object"
                                    }
                                },
                                "additionalProperties": True
                            }
                        },
                        "additionalProperties": True
                    }
                }
            },
            "additionalProperties": True
        }
        
        # Schema for linking_maps/linking_map.json (ARRAY format)
        linking_map_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://fba-system.internal/schemas/linking_map.json",
            "title": "Linking Map Schema",
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "supplier_product_identifier",
                    "supplier_title_snippet", 
                    "chosen_amazon_asin",
                    "amazon_title_snippet",
                    "match_method"
                ],
                "properties": {
                    "supplier_product_identifier": {
                        "type": "string",
                        "minLength": 1
                    },
                    "supplier_title_snippet": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200
                    },
                    "chosen_amazon_asin": {
                        "type": "string",
                        "pattern": "^B[0-9A-Z]{9}$"
                    },
                    "amazon_title_snippet": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200
                    },
                    "amazon_ean_on_page": {
                        "type": ["string", "null"],
                        "pattern": "^[0-9]{8,14}$"
                    },
                    "match_method": {
                        "type": "string",
                        "enum": ["EAN_search", "title_search", "hybrid_search", "manual_match", "ai_match"]
                    }
                },
                "additionalProperties": True
            },
            "minItems": 0
        }
        
        return {
            "cached_products": cached_products_schema,
            "ai_category_cache": ai_category_cache_schema,
            "linking_map": linking_map_schema
        }
    
    def verify_output_files(
        self, 
        supplier_name: str, 
        run_output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Verify all output files for a supplier against schemas
        
        Args:
            supplier_name: Supplier domain identifier
            run_output_dir: Optional specific run directory to verify
            
        Returns:
            Dictionary with verification results
            
        Raises:
            NeedsInterventionError: If any critical validation fails
        """
        try:
            if run_output_dir is None:
                run_output_dir = get_run_output_dir(supplier_name)
            
            logger.info(f"🔍 Verifying output files for {supplier_name} in {run_output_dir}")
            
            verification_results = {
                "supplier_name": supplier_name,
                "run_output_dir": str(run_output_dir),
                "verification_timestamp": datetime.utcnow().isoformat(),
                "files_verified": {},
                "overall_status": "pending",
                "errors": [],
                "warnings": []
            }
            
            # Define expected file locations
            expected_files = {
                "cached_products": run_output_dir / "cached_products.json",
                "ai_category_cache": run_output_dir / "ai_category_cache.json", 
                "linking_map": run_output_dir / "linking_maps" / "linking_map.json"
            }
            
            # Verify each file
            all_passed = True
            critical_errors = []
            
            for file_type, file_path in expected_files.items():
                try:
                    result = self._verify_single_file(file_type, file_path)
                    verification_results["files_verified"][file_type] = result
                    
                    if not result["valid"]:
                        all_passed = False
                        if result.get("critical", False):
                            critical_errors.append(f"{file_type}: {result.get('error', 'Validation failed')}")
                        else:
                            verification_results["warnings"].append(f"{file_type}: {result.get('error', 'Warning')}")
                    
                except Exception as e:
                    all_passed = False
                    error_msg = f"{file_type}: Verification error: {e}"
                    critical_errors.append(error_msg)
                    verification_results["files_verified"][file_type] = {
                        "valid": False,
                        "error": str(e),
                        "critical": True
                    }
            
            # Set overall status
            if critical_errors:
                verification_results["overall_status"] = "failed"
                verification_results["errors"] = critical_errors
            elif all_passed:
                verification_results["overall_status"] = "passed"
            else:
                verification_results["overall_status"] = "passed_with_warnings"
            
            # Log results
            if verification_results["overall_status"] == "passed":
                logger.info(f"✅ All output files verified successfully for {supplier_name}")
            elif verification_results["overall_status"] == "passed_with_warnings":
                logger.warning(f"⚠️ Output files verified with warnings for {supplier_name}")
            else:
                logger.error(f"❌ Output file verification failed for {supplier_name}")
            
            # Raise intervention error if critical failures
            if critical_errors:
                error_summary = "; ".join(critical_errors)
                raise NeedsInterventionError(
                    f"Output verification failed for {supplier_name}: {error_summary}"
                )
            
            return verification_results
            
        except NeedsInterventionError:
            raise
        except Exception as e:
            logger.error(f"Output verification error for {supplier_name}: {e}")
            raise NeedsInterventionError(f"Verification system error: {e}")
    
    def _verify_single_file(self, file_type: str, file_path: Path) -> Dict[str, Any]:
        """
        Verify a single output file against its schema
        
        Args:
            file_type: Type of file (cached_products, ai_category_cache, linking_map)
            file_path: Path to the file
            
        Returns:
            Dictionary with verification results for this file
        """
        result = {
            "file_type": file_type,
            "file_path": str(file_path),
            "valid": False,
            "schema_version": "draft-2020-12",
            "validation_timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check file exists
            if not file_path.exists():
                result.update({
                    "error": "File does not exist",
                    "critical": True
                })
                return result
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                result.update({
                    "error": "File is empty",
                    "critical": True
                })
                return result
            
            # Load and parse JSON
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                result.update({
                    "error": f"Invalid JSON: {e}",
                    "critical": True
                })
                return result
            
            # Get schema for this file type
            schema = self.schemas.get(file_type)
            if not schema:
                result.update({
                    "error": f"No schema defined for file type: {file_type}",
                    "critical": True
                })
                return result
            
            # Validate against schema
            try:
                jsonschema.validate(instance=data, schema=schema)
                result.update({
                    "valid": True,
                    "file_size_bytes": file_size,
                    "record_count": self._get_record_count(file_type, data)
                })
                
                # Additional content validation
                content_validation = self._validate_content_quality(file_type, data)
                result.update(content_validation)
                
            except jsonschema.ValidationError as e:
                # Create detailed validation error with diff
                error_details = self._create_validation_error_details(e, data, schema)
                result.update({
                    "error": f"Schema validation failed: {e.message}",
                    "validation_path": list(e.absolute_path),
                    "schema_path": list(e.schema_path),
                    "error_details": error_details,
                    "critical": True
                })
                
                # Generate YAML diff for human review
                diff_output = self._generate_yaml_diff(file_type, data, e)
                if diff_output:
                    result["yaml_diff"] = diff_output
                    logger.error(f"Validation diff for {file_type}:\n{diff_output}")
            
            except jsonschema.SchemaError as e:
                result.update({
                    "error": f"Schema error: {e.message}",
                    "critical": True
                })
            
            return result
            
        except Exception as e:
            result.update({
                "error": f"Verification error: {e}",
                "critical": True
            })
            return result
    
    def _get_record_count(self, file_type: str, data: Any) -> int:
        """Get record count for different file types"""
        try:
            if file_type == "cached_products":
                return len(data.get("products", {}))
            elif file_type == "ai_category_cache":
                return len(data.get("ai_suggestion_history", []))
            elif file_type == "linking_map":
                return len(data) if isinstance(data, list) else 0
            return 0
        except:
            return 0
    
    def _validate_content_quality(self, file_type: str, data: Any) -> Dict[str, Any]:
        """Validate content quality beyond schema compliance"""
        quality_result = {
            "content_warnings": [],
            "quality_score": 1.0
        }
        
        try:
            if file_type == "cached_products":
                # Check for minimum products
                products = data.get("products", {})
                if len(products) < 5:
                    quality_result["content_warnings"].append(f"Low product count: {len(products)} (expected ≥5)")
                    quality_result["quality_score"] *= 0.8
                
                # Check for missing EANs
                products_with_ean = sum(1 for p in products.values() if p.get("ean"))
                ean_ratio = products_with_ean / len(products) if products else 0
                if ean_ratio < 0.3:
                    quality_result["content_warnings"].append(f"Low EAN coverage: {ean_ratio:.1%}")
                    quality_result["quality_score"] *= 0.9
                    
            elif file_type == "ai_category_cache":
                # Check for AI suggestions
                history = data.get("ai_suggestion_history", [])
                if not history:
                    quality_result["content_warnings"].append("No AI suggestion history")
                    quality_result["quality_score"] *= 0.5
                else:
                    latest = history[-1]
                    top_urls = latest.get("ai_suggestions", {}).get("top_3_urls", [])
                    if len(top_urls) < 3:
                        quality_result["content_warnings"].append(f"Insufficient top URLs: {len(top_urls)}")
                        quality_result["quality_score"] *= 0.8
                        
            elif file_type == "linking_map":
                # Check for minimum linking results
                if isinstance(data, list) and len(data) < 1:
                    quality_result["content_warnings"].append("No linking map entries")
                    quality_result["quality_score"] *= 0.5
                    
        except Exception as e:
            quality_result["content_warnings"].append(f"Quality validation error: {e}")
            quality_result["quality_score"] *= 0.7
        
        return quality_result
    
    def _create_validation_error_details(
        self, 
        error: jsonschema.ValidationError, 
        data: Any, 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create detailed validation error information"""
        return {
            "failed_value": error.instance,
            "validator": error.validator,
            "validator_value": error.validator_value,
            "schema_context": error.schema,
            "absolute_path": list(error.absolute_path),
            "relative_path": list(error.path)
        }
    
    def _generate_yaml_diff(
        self, 
        file_type: str, 
        actual_data: Any, 
        error: jsonschema.ValidationError
    ) -> Optional[str]:
        """Generate YAML diff for human review"""
        try:
            # Create expected structure based on schema and error
            expected_structure = self._create_expected_structure(file_type, error)
            
            # Convert to YAML for readable diff
            actual_yaml = yaml.dump(actual_data, default_flow_style=False, sort_keys=True)
            expected_yaml = yaml.dump(expected_structure, default_flow_style=False, sort_keys=True)
            
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                actual_yaml.splitlines(keepends=True),
                expected_yaml.splitlines(keepends=True),
                fromfile=f"actual_{file_type}.yaml",
                tofile=f"expected_{file_type}.yaml",
                lineterm=""
            ))
            
            if diff_lines:
                return ''.join(diff_lines)
            
        except Exception as e:
            logger.debug(f"Failed to generate YAML diff: {e}")
        
        return None
    
    def _create_expected_structure(self, file_type: str, error: jsonschema.ValidationError) -> Dict[str, Any]:
        """Create expected structure example for diff generation"""
        # Create minimal valid examples based on file type
        if file_type == "cached_products":
            return {
                "supplier_name": "example-supplier.com",
                "cached_at": "2025-06-28T10:00:00.000Z",
                "total_products": 1,
                "products": {
                    "SKU123": {
                        "title": "Example Product",
                        "price": 1.99,
                        "url": "https://example.com/product",
                        "image_url": "https://example.com/image.jpg",
                        "ean": "1234567890123",
                        "upc": None,
                        "sku": None,
                        "source_category_url": "https://example.com/category",
                        "extraction_timestamp": "2025-06-28T10:00:00.000Z"
                    }
                }
            }
        elif file_type == "ai_category_cache":
            return {
                "supplier": "example-supplier.com",
                "url": "https://www.example-supplier.com",
                "created": "2025-06-28T10:00:00.000Z",
                "last_updated": "2025-06-28T10:00:00.000Z",
                "total_ai_calls": 1,
                "ai_suggestion_history": [
                    {
                        "timestamp": "2025-06-28T10:00:00.000Z",
                        "session_context": {
                            "categories_discovered": 5,
                            "total_products_processed": 10,
                            "previous_categories_count": 0
                        },
                        "ai_suggestions": {
                            "top_3_urls": ["https://example.com/category1"],
                            "secondary_urls": [],
                            "skip_urls": [],
                            "detailed_reasoning": {},
                            "validation_results": {}
                        }
                    }
                ]
            }
        elif file_type == "linking_map":
            return [
                {
                    "supplier_product_identifier": "EAN_1234567890123",
                    "supplier_title_snippet": "Example Product Title",
                    "chosen_amazon_asin": "B0123456789",
                    "amazon_title_snippet": "Amazon Product Title",
                    "amazon_ean_on_page": "1234567890123",
                    "match_method": "EAN_search"
                }
            ]
        
        return {}


# Convenience functions
def verify_supplier_outputs(supplier_name: str, run_output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Verify all output files for a supplier"""
    verifier = OutputVerificationNode()
    return verifier.verify_output_files(supplier_name, run_output_dir)


if __name__ == "__main__":
    # Test output verification
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Output Verification Node...")
    
    # Create test verifier
    verifier = OutputVerificationNode()
    
    # Test schema building
    print(f"Built {len(verifier.schemas)} schemas")
    for schema_name in verifier.schemas.keys():
        print(f"  - {schema_name}")
    
    # Test with non-existent supplier (should fail gracefully)
    try:
        result = verify_supplier_outputs("non-existent-supplier")
        print("Should have failed for non-existent supplier")
    except NeedsInterventionError as e:
        print(f"✅ Correctly failed for non-existent supplier: {e}")
    
    print("✅ Output Verification Node tests completed")