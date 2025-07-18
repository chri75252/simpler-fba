#!/usr/bin/env python3
"""
Extract Main Categories Script - FIXED VERSION
Extracts actual category directory URLs from poundwholesale.co.uk sitemap
Focus on main category directories like /toys/, /wholesale-garden/, etc.
"""

import requests
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
from urllib.parse import urlparse

class MainCategoryExtractor:
    def __init__(self):
        self.base_url = "https://www.poundwholesale.co.uk"
        self.sitemap_url = "https://www.poundwholesale.co.uk/sitemap.xml"
        
    def extract_main_categories_from_sitemap(self):
        """Extract main category URLs from sitemap.xml using directory analysis"""
        print("🔍 Fetching sitemap.xml...")
        
        try:
            response = requests.get(self.sitemap_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Extract all URLs
            all_urls = []
            for url_elem in root.findall('sitemap:url', namespace):
                loc_elem = url_elem.find('sitemap:loc', namespace)
                if loc_elem is not None:
                    all_urls.append(loc_elem.text)
            
            print(f"📋 Found {len(all_urls)} total URLs in sitemap")
            
            # Extract unique directory patterns
            category_patterns = set()
            
            for url in all_urls:
                parsed = urlparse(url)
                path = parsed.path.strip('/')
                
                if not path:  # Skip homepage
                    continue
                
                # Split path and get the first segment
                path_parts = path.split('/')
                first_segment = path_parts[0]
                
                # Only consider first-level directories that look like categories
                # Exclude obvious non-categories
                exclude_patterns = [
                    'about', 'contact', 'privacy', 'terms', 'customer', 'checkout',
                    'search', 'cms', 'media', 'catalog', 'catalogsearch'
                ]
                
                if first_segment and not any(excl in first_segment.lower() for excl in exclude_patterns):
                    # Add the directory pattern
                    category_patterns.add(first_segment)
            
            # Convert to category URLs and filter for reasonable categories
            main_categories = []
            for pattern in sorted(category_patterns):
                category_url = f"{self.base_url}/{pattern}/"
                
                # Skip single character or very short patterns that are likely not categories
                if len(pattern) >= 3:
                    main_categories.append(category_url)
            
            print(f"✅ Extracted {len(main_categories)} main category patterns")
            
            # Display the first 25 categories
            print(f"\n📋 MAIN CATEGORY PATTERNS (First 25 of {len(main_categories)}):")
            for i, cat_url in enumerate(main_categories[:25], 1):
                category_name = cat_url.replace(f"{self.base_url}/", "").replace("/", "").replace("-", " ").title()
                print(f"  {i:2d}. {category_name}: {cat_url}")
            
            if len(main_categories) > 25:
                print(f"  ... and {len(main_categories) - 25} more categories")
            
            # Now let's identify the most likely main categories based on common e-commerce patterns
            likely_main_categories = []
            priority_keywords = [
                'toys', 'baby', 'garden', 'wholesale-garden', 'cleaning', 'kitchen', 
                'health', 'beauty', 'home', 'homeware', 'diy', 'electrical', 
                'pet', 'stationery', 'party', 'clothing', 'seasonal', 'ebay-amazon-sellers'
            ]
            
            for cat_url in main_categories:
                pattern = cat_url.replace(f"{self.base_url}/", "").replace("/", "")
                
                # Check if this matches our priority keywords
                for keyword in priority_keywords:
                    if keyword in pattern.lower() or pattern.lower().startswith(keyword[:4]):
                        likely_main_categories.append(cat_url)
                        break
            
            print(f"\n🎯 LIKELY MAIN CATEGORIES ({len(likely_main_categories)}):")
            for i, cat_url in enumerate(likely_main_categories, 1):
                category_name = cat_url.replace(f"{self.base_url}/", "").replace("/", "").replace("-", " ").title()
                print(f"  {i:2d}. {category_name}: {cat_url}")
            
            return likely_main_categories if likely_main_categories else main_categories[:18]
            
        except Exception as e:
            print(f"❌ Error extracting categories: {e}")
            return []
    
    def test_category_with_pagination(self, category_url, max_pages=3):
        """Test a category URL to see if it has products and pagination"""
        print(f"\n🔍 Testing: {category_url}")
        
        valid_pages = []
        
        for page_num in range(1, max_pages + 1):
            test_url = f"{category_url}?p={page_num}"
            
            try:
                response = requests.get(test_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Check for products using multiple indicators
                    has_products = any([
                        'product-item' in content,
                        'class="product' in content,
                        'product-name' in content,
                        'price' in content.lower()
                    ])
                    
                    # Check for pagination indicators
                    has_pagination = any([
                        '?p=' in content,
                        'page=' in content,
                        'Next' in content,
                        'pagination' in content.lower()
                    ])
                    
                    # Check for product count in toolbar
                    toolbar_match = re.search(r'(\d+)-(\d+)\s+of\s+(\d+)', content)
                    product_count = None
                    if toolbar_match:
                        product_count = int(toolbar_match.group(3))
                    
                    if has_products:
                        result = {
                            "page": page_num,
                            "url": test_url,
                            "has_products": True,
                            "has_pagination": has_pagination,
                            "product_count": product_count,
                            "content_size": len(content)
                        }
                        valid_pages.append(result)
                        
                        status = f"✅ Page {page_num}: Products found"
                        if product_count:
                            status += f" (Total: {product_count})"
                        print(f"    {status}")
                    else:
                        print(f"    ❌ Page {page_num}: No products found")
                        break
                else:
                    print(f"    ❌ Page {page_num}: HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"    ❌ Page {page_num}: Error - {e}")
                break
        
        return valid_pages

def main():
    """Main execution function"""
    extractor = MainCategoryExtractor()
    
    # Extract main categories
    print("🚀 Starting main category extraction...")
    categories = extractor.extract_main_categories_from_sitemap()
    
    if not categories:
        print("❌ No categories extracted. Exiting.")
        return
    
    # Test the first few categories
    print(f"\n🧪 Testing first 5 categories for products and pagination...")
    
    valid_categories = []
    for i, category_url in enumerate(categories[:5]):
        print(f"\n{'='*60}")
        pagination_results = extractor.test_category_with_pagination(category_url)
        
        if pagination_results:
            valid_categories.append({
                "name": category_url.replace(f"{extractor.base_url}/", "").replace("/", "").replace("-", " ").title(),
                "url": category_url,
                "pages_tested": len(pagination_results),
                "has_products": True
            })
        else:
            print(f"    ⚠️ No products found - might not be a valid category")
    
    # Generate final report
    report = {
        "extraction_timestamp": datetime.now().isoformat(),
        "sitemap_url": extractor.sitemap_url,
        "total_patterns_found": len(categories),
        "tested_categories": len(valid_categories),
        "valid_categories": valid_categories,
        "all_category_urls": categories,
        "pagination_pattern": "?p={page_num}",
        "next_steps": [
            "Use the valid_categories for actual scraping",
            "Each category supports ?p=N pagination",
            "Extract: name, product_url, price, ean/barcode, stock_status"
        ]
    }
    
    # Save report
    filename = f"main_categories_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"📋 Total Category Patterns: {len(categories)}")
    print(f"✅ Valid Categories (with products): {len(valid_categories)}")
    print(f"📄 Pagination Pattern: ?p={{page_num}}")
    print(f"📁 Report saved to: {filename}")
    
    if valid_categories:
        print(f"\n🎯 READY FOR SCRAPING:")
        for cat in valid_categories:
            print(f"  • {cat['name']}: {cat['url']}")

if __name__ == "__main__":
    main()