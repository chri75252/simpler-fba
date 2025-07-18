#!/usr/bin/env python3
"""
Find Category URLs with Redirect Handling
Handle HTTP 307 redirects to find the actual category URLs
"""

import requests
import json
from datetime import datetime
import re

class CategoryFinderWithRedirects:
    def __init__(self):
        self.base_url = "https://www.poundwholesale.co.uk"
        
        # Test categories based on examples and analysis
        self.test_categories = [
            "toys",
            "wholesale-garden", 
            "baby-supplies",
            "cleaning",
            "kitchenware", 
            "health",
            "homeware",
            "diy",
            "electrical",
            "pet",
            "stationery",
            "party",
            "clothing",
            "seasonal",
            "ebay-amazon-sellers"
        ]
        
    def test_category_with_redirects(self, category):
        """Test a category URL, following redirects to find the final URL"""
        category_url = f"{self.base_url}/{category}/"
        
        print(f"\n{'='*60}")
        print(f"Testing: {category}")
        print(f"Initial URL: {category_url}")
        
        try:
            # Follow redirects manually to see where they go
            response = requests.get(category_url, timeout=10, allow_redirects=True, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            final_url = response.url
            print(f"Final URL: {final_url}")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                
                # Check for products using multiple indicators
                product_indicators = [
                    'product-item',
                    'class="product',
                    'product-name',
                    'li class="item product product-item"',
                    'data-product-id'
                ]
                
                has_products = any(indicator in content for indicator in product_indicators)
                
                # Check for pagination
                pagination_indicators = [
                    '?p=',
                    'page=',
                    'toolbar-amount',
                    'Next',
                    'pagination',
                    'pages-item-next'
                ]
                
                has_pagination = any(indicator in content for indicator in pagination_indicators)
                
                # Look for product count in toolbar
                toolbar_matches = [
                    re.search(r'(\d+)-(\d+)\s+of\s+(\d+)', content),
                    re.search(r'(\d+)\s+Item', content),
                    re.search(r'(\d+)\s+Product', content)
                ]
                
                product_count = None
                for match in toolbar_matches:
                    if match:
                        if len(match.groups()) >= 3:
                            product_count = int(match.group(3))
                        else:
                            product_count = int(match.group(1))
                        break
                
                # Check if this looks like a category page vs homepage/other
                is_category_page = any([
                    'category' in final_url.lower(),
                    category in final_url.lower(),
                    'catalog/category' in content.lower(),
                    'categoryview' in content.lower()
                ])
                
                print(f"    Products detected: {has_products}")
                print(f"    Pagination detected: {has_pagination}")
                print(f"    Product count: {product_count}")
                print(f"    Appears to be category: {is_category_page}")
                
                if has_products:
                    result = {
                        "name": category.replace("-", " ").title(),
                        "original_url": category_url,
                        "final_url": final_url,
                        "has_products": True,
                        "product_count": product_count,
                        "has_pagination": has_pagination,
                        "is_category_page": is_category_page,
                        "status": "SUCCESS"
                    }
                    print(f"    ✅ SUCCESS: Category found with products")
                    return result
                else:
                    print(f"    ❌ No products found on final page")
                    
            else:
                print(f"    ❌ Final status: {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        return None
    
    def test_specific_known_urls(self):
        """Test URLs we know work from the analysis report"""
        known_working_urls = [
            "https://www.poundwholesale.co.uk/ebay-amazon-sellers",
            "https://www.poundwholesale.co.uk/seasonal/wholesale-summer"
        ]
        
        print(f"\n🧪 Testing known working URLs...")
        
        working_categories = []
        
        for url in known_working_urls:
            print(f"\n{'='*60}")
            print(f"Testing known URL: {url}")
            
            try:
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Check for products
                    has_products = any([
                        'product-item' in content,
                        'class="product' in content,
                        'data-product-id' in content
                    ])
                    
                    # Check for pagination
                    has_pagination = any([
                        '?p=' in content,
                        'toolbar-amount' in content,
                        'Next' in content
                    ])
                    
                    # Get product count
                    toolbar_match = re.search(r'(\d+)-(\d+)\s+of\s+(\d+)', content)
                    product_count = int(toolbar_match.group(3)) if toolbar_match else None
                    
                    if has_products:
                        category_name = url.split("/")[-1].replace("-", " ").title()
                        result = {
                            "name": category_name,
                            "original_url": url,
                            "final_url": response.url,
                            "has_products": True,
                            "product_count": product_count,
                            "has_pagination": has_pagination,
                            "is_category_page": True,
                            "status": "KNOWN_WORKING"
                        }
                        
                        working_categories.append(result)
                        print(f"    ✅ SUCCESS: {product_count} products found")
                    else:
                        print(f"    ❌ No products found")
                else:
                    print(f"    ❌ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        return working_categories
    
    def discover_categories_from_sitemap_sample(self):
        """Sample a few URLs from sitemap to understand the pattern"""
        print(f"\n🔍 Sampling sitemap for pattern analysis...")
        
        try:
            response = requests.get(f"{self.base_url}/sitemap.xml", timeout=30)
            if response.status_code == 200:
                content = response.text
                
                # Find URLs that might be categories (contain multiple path segments)
                category_candidates = []
                
                import xml.etree.ElementTree as ET
                root = ET.fromstring(content)
                namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                
                urls = []
                for url_elem in root.findall('sitemap:url', namespace):
                    loc_elem = url_elem.find('sitemap:loc', namespace)
                    if loc_elem is not None:
                        urls.append(loc_elem.text)
                
                # Look for URLs that look like categories (not products)
                for url in urls[:100]:  # Sample first 100
                    path = url.replace(self.base_url, "").strip("/")
                    
                    # Skip obvious non-categories
                    if any(skip in path.lower() for skip in ['about', 'contact', 'privacy', 'customer']):
                        continue
                    
                    # Look for paths that might be categories
                    if "/" in path and len(path.split("/")) == 2:  # Two-level paths
                        category_candidates.append(url)
                
                print(f"📋 Found {len(category_candidates)} potential category URLs in sample:")
                for url in category_candidates[:10]:  # Show first 10
                    path = url.replace(self.base_url + "/", "")
                    print(f"  • {path}")
                
                if len(category_candidates) > 10:
                    print(f"  ... and {len(category_candidates) - 10} more")
                
                return category_candidates[:5]  # Return first 5 for testing
                
        except Exception as e:
            print(f"❌ Error sampling sitemap: {e}")
        
        return []

    def run_comprehensive_test(self):
        """Run all tests to find working categories"""
        all_results = []
        
        # Test 1: Known working URLs
        print("🚀 STEP 1: Testing known working URLs")
        known_working = self.test_specific_known_urls()
        all_results.extend(known_working)
        
        # Test 2: Test category patterns with redirects
        print(f"\n🚀 STEP 2: Testing category patterns (following redirects)")
        for category in self.test_categories:
            result = self.test_category_with_redirects(category)
            if result:
                all_results.append(result)
        
        # Test 3: Sample from sitemap
        print(f"\n🚀 STEP 3: Sampling from sitemap")
        sitemap_candidates = self.discover_categories_from_sitemap_sample()
        
        for url in sitemap_candidates:
            try:
                response = requests.get(url, timeout=5, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200 and 'product-item' in response.text:
                    path = url.replace(self.base_url + "/", "")
                    result = {
                        "name": path.replace("/", " > ").replace("-", " ").title(),
                        "original_url": url,
                        "final_url": response.url,
                        "has_products": True,
                        "status": "SITEMAP_DISCOVERED"
                    }
                    all_results.append(result)
                    print(f"    ✅ Found working category: {path}")
                    
            except:
                continue
        
        return all_results

def main():
    """Main execution function"""
    finder = CategoryFinderWithRedirects()
    
    print("🚀 Starting comprehensive category discovery...")
    
    # Run all tests
    results = finder.run_comprehensive_test()
    
    if results:
        # Generate report
        report = {
            "extraction_timestamp": datetime.now().isoformat(),
            "base_url": finder.base_url,
            "total_categories_found": len(results),
            "categories": results,
            "pagination_pattern": "?p={page_num}",
            "extraction_requirements": {
                "fields": ["name", "product_url", "price", "ean_barcode", "stock_status"],
                "pagination": "Continue until page returns 0 products",
                "stock_detection": "Look for OUT OF STOCK indicators"
            }
        }
        
        filename = f"discovered_categories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 DISCOVERY COMPLETE!")
        print(f"✅ Found {len(results)} working categories")
        print(f"📁 Report saved: {filename}")
        
        print(f"\n🎯 WORKING CATEGORIES:")
        for result in results:
            print(f"  • {result['name']}: {result['final_url']}")
            if result.get('product_count'):
                print(f"    📊 Products: {result['product_count']}")
        
    else:
        print("\n❌ No working categories discovered")

if __name__ == "__main__":
    main()