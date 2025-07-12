"""
Fake Data Generators for Testing - Safe test data creation
========================================================

Provides fake data generators for testing FBA system components.
Uses safety guards to prevent accidental use in production.
"""

import sys
import json
import random
from datetime import datetime, timezone
from typing import Dict, List, Any
from pathlib import Path


def check_test_safety():
    """Safety guard to prevent production use"""
    if "I_UNDERSTAND_THIS_IS_FAKE" not in sys.argv:
        raise RuntimeError(
            "Fake data generators require 'I_UNDERSTAND_THIS_IS_FAKE' in sys.argv. "
            "This prevents accidental use in production code."
        )


def generate_fake_cached_products(
    supplier_name: str = "test-supplier-com",
    product_count: int = 5
) -> Dict[str, Any]:
    """Generate fake cached products data for testing"""
    check_test_safety()
    
    products = {}
    for i in range(1, product_count + 1):
        sku = f"TEST_SKU_{i:03d}"
        products[sku] = {
            "title": f"Test Product {i} - Sample Item for Testing",
            "price": round(random.uniform(1.0, 50.0), 2),
            "url": f"https://test-supplier.com/product-{i}",
            "image_url": f"https://test-supplier.com/images/product-{i}.jpg" if i % 2 == 0 else None,
            "ean": f"500000000{i:04d}" if i % 3 == 0 else None,
            "upc": f"12345678{i:04d}" if i % 4 == 0 else None,
            "sku": sku,
            "source_category_url": f"https://test-supplier.com/category-{(i-1)//3 + 1}",
            "extraction_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    return {
        "supplier_name": supplier_name,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "total_products": product_count,
        "products": products
    }


def generate_fake_ai_category_cache(
    supplier_name: str = "test-supplier-com",
    suggestion_count: int = 1
) -> Dict[str, Any]:
    """Generate fake AI category cache data for testing"""
    check_test_safety()
    
    suggestions = []
    for i in range(suggestion_count):
        suggestions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_context": {
                "categories_discovered": random.randint(3, 10),
                "total_products_processed": random.randint(10, 100),
                "previous_categories_count": i
            },
            "ai_suggestions": {
                "top_3_urls": [
                    f"https://test-supplier.com/category-{j}"
                    for j in range(1, min(4, random.randint(1, 6)))
                ],
                "secondary_urls": [
                    f"https://test-supplier.com/secondary-{j}"
                    for j in range(1, random.randint(0, 4))
                ],
                "skip_urls": [],
                "detailed_reasoning": {
                    "category_analysis": f"Test reasoning for suggestion {i+1}",
                    "selection_criteria": "Test selection criteria",
                    "arbitrage_potential": "Medium"
                },
                "validation_results": {
                    f"category-{j}": {
                        "total_products": random.randint(5, 25),
                        "success_rate": round(random.uniform(0.6, 1.0), 2),
                        "urls_tested": random.randint(1, 3)
                    }
                    for j in range(1, 4)
                }
            }
        })
    
    return {
        "supplier": supplier_name,
        "url": f"https://www.{supplier_name.replace('-', '.')}",
        "created": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_ai_calls": suggestion_count,
        "ai_suggestion_history": suggestions
    }


def generate_fake_linking_map(entry_count: int = 3) -> List[Dict[str, Any]]:
    """Generate fake linking map data in array format for testing"""
    check_test_safety()
    
    linking_map = []
    
    match_methods = ["EAN_search", "title_search", "hybrid_search", "manual_match"]
    
    for i in range(1, entry_count + 1):
        has_ean = i % 2 == 0
        entry = {
            "supplier_product_identifier": f"EAN_500000000{i:04d}" if has_ean else f"SKU_TEST_{i:03d}",
            "supplier_title_snippet": f"Test Product {i} - Sample Item",
            "chosen_amazon_asin": f"B{random.randint(100000000, 999999999)}",
            "amazon_title_snippet": f"Amazon Test Product {i} - Similar Item",
            "amazon_ean_on_page": f"500000000{i:04d}" if has_ean else None,
            "match_method": random.choice(match_methods)
        }
        
        linking_map.append(entry)
    
    return linking_map


def generate_fake_supplier_config(supplier_domain: str = "test-supplier.com") -> Dict[str, Any]:
    """Generate fake supplier configuration for testing"""
    check_test_safety()
    
    return {
        "supplier_name": supplier_domain,
        "base_url": f"https://www.{supplier_domain}",
        "login_required": True,
        "category_paths": ["/category1", "/category2", "/category3"],
        "product_selectors": {
            "product_links": "a.product-link",
            "title": "h1.product-title",
            "price": ".price",
            "ean": ".ean-code"
        },
        "pagination": {
            "next_page_selector": ".next-page",
            "max_pages": 5
        },
        "test_metadata": {
            "created_for_testing": True,
            "safe_to_use": True
        }
    }


def save_fake_data_to_files(output_dir: Path, supplier_name: str = "test-supplier-com"):
    """Save all fake data types to files for testing"""
    check_test_safety()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save cached products
    cached_products = generate_fake_cached_products(supplier_name, 8)
    with open(output_dir / "cached_products.json", 'w') as f:
        json.dump(cached_products, f, indent=2)
    
    # Save AI category cache
    ai_cache = generate_fake_ai_category_cache(supplier_name, 2)
    with open(output_dir / "ai_category_cache.json", 'w') as f:
        json.dump(ai_cache, f, indent=2)
    
    # Save linking map
    linking_maps_dir = output_dir / "linking_maps"
    linking_maps_dir.mkdir(exist_ok=True)
    linking_map = generate_fake_linking_map(5)
    with open(linking_maps_dir / "linking_map.json", 'w') as f:
        json.dump(linking_map, f, indent=2)
    
    # Save supplier config
    supplier_config = generate_fake_supplier_config(supplier_name.replace('-', '.'))
    with open(output_dir / "supplier_config.json", 'w') as f:
        json.dump(supplier_config, f, indent=2)
    
    print(f"✅ Fake data saved to {output_dir}")
    return output_dir


def create_minimal_valid_outputs(output_dir: Path, supplier_name: str = "test-supplier-com") -> Dict[str, Path]:
    """Create minimal valid outputs that pass schema validation"""
    check_test_safety()
    
    output_dir = Path(output_dir)
    run_dir = output_dir / supplier_name / "20250628_120000_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Minimal cached products (meets 5 product minimum)
    cached_products = {
        "supplier_name": supplier_name,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "total_products": 5,
        "products": {
            f"P{i}": {
                "title": f"Minimal Product {i}",
                "price": i * 2.5,
                "url": f"https://test.com/product-{i}",
                "extraction_timestamp": datetime.now(timezone.utc).isoformat()
            }
            for i in range(1, 6)
        }
    }
    
    cached_products_path = run_dir / "cached_products.json"
    with open(cached_products_path, 'w') as f:
        json.dump(cached_products, f, indent=2)
    
    # Minimal AI category cache
    ai_cache = {
        "supplier": supplier_name,
        "url": f"https://www.{supplier_name.replace('-', '.')}",
        "created": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_ai_calls": 1,
        "ai_suggestion_history": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_context": {
                    "categories_discovered": 5,
                    "total_products_processed": 5
                },
                "ai_suggestions": {
                    "top_3_urls": [
                        "https://test.com/category1",
                        "https://test.com/category2"
                    ],
                    "secondary_urls": [],
                    "skip_urls": []
                }
            }
        ]
    }
    
    ai_cache_path = run_dir / "ai_category_cache.json"
    with open(ai_cache_path, 'w') as f:
        json.dump(ai_cache, f, indent=2)
    
    # Minimal linking map
    linking_map = [
        {
            "supplier_product_identifier": "TEST_P1",
            "supplier_title_snippet": "Minimal Product 1",
            "chosen_amazon_asin": "B012345678",
            "amazon_title_snippet": "Amazon Product Match",
            "amazon_ean_on_page": None,
            "match_method": "title_search"
        }
    ]
    
    linking_maps_dir = run_dir / "linking_maps"
    linking_maps_dir.mkdir(exist_ok=True)
    linking_map_path = linking_maps_dir / "linking_map.json"
    with open(linking_map_path, 'w') as f:
        json.dump(linking_map, f, indent=2)
    
    return {
        "cached_products": cached_products_path,
        "ai_category_cache": ai_cache_path,
        "linking_map": linking_map_path,
        "run_dir": run_dir
    }


if __name__ == "__main__":
    # Test the fake data generators
    if "I_UNDERSTAND_THIS_IS_FAKE" not in sys.argv:
        print("❌ Add 'I_UNDERSTAND_THIS_IS_FAKE' to sys.argv to run fake data generators")
        sys.exit(1)
    
    import tempfile
    
    temp_dir = Path(tempfile.mkdtemp())
    print(f"🧪 Testing fake data generators in {temp_dir}")
    
    try:
        # Test individual generators
        cached_products = generate_fake_cached_products("test-supplier", 3)
        print(f"✅ Generated cached products with {cached_products['total_products']} products")
        
        ai_cache = generate_fake_ai_category_cache("test-supplier", 2)
        print(f"✅ Generated AI cache with {ai_cache['total_ai_calls']} suggestions")
        
        linking_map = generate_fake_linking_map(4)
        print(f"✅ Generated linking map with {len(linking_map)} entries")
        
        # Test file creation
        save_fake_data_to_files(temp_dir / "full_fake_data", "test-supplier")
        
        # Test minimal valid outputs
        minimal_paths = create_minimal_valid_outputs(temp_dir / "minimal_outputs", "test-supplier")
        print(f"✅ Created minimal valid outputs: {list(minimal_paths.keys())}")
        
        print("✅ All fake data generators working correctly")
        
    except Exception as e:
        print(f"❌ Fake data generator test failed: {e}")
        raise
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)