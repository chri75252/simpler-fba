#!/usr/bin/env python3
"""
Extract Main Categories Script
Extracts the 18 main category URLs from poundwholesale.co.uk sitemap based on URL patterns
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
        
        # Define the 18 main category keywords based on the analysis report
        self.main_category_keywords = [
            "wholesale-garden", "toys", "leisure", "baby", "cleaning", 
            "kitchenware", "health", "homeware", "diy", "electrical", 
            "pet", "stationery", "party", "wholesale-clothing", "seasonal",
            "wholesale-pound", "ebay-amazon-sellers"  # These are the actual working categories
        ]
        
    def extract_main_categories_from_sitemap(self):
        """Extract main category URLs from sitemap.xml using URL pattern analysis"""
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
            
            # Extract main category URLs using pattern analysis
            main_categories = set()
            
            for url in all_urls:
                # Parse the URL path
                parsed = urlparse(url)
                path = parsed.path.strip('/')
                
                if not path:  # Skip homepage
                    continue
                    
                # Split path to get the first segment
                path_parts = path.split('/')
                first_segment = path_parts[0]
                
                # Check if this looks like a main category
                # Main categories are single-level paths that match our keywords
                if len(path_parts) >= 1:
                    # Look for exact matches or variations of our category keywords
                    for keyword in self.main_category_keywords:
                        if (first_segment == keyword or 
                            first_segment.startswith(keyword) or 
                            keyword in first_segment):
                            
                            # Construct the main category URL
                            category_url = f"{self.base_url}/{first_segment}/"
                            main_categories.add(category_url)
                            break
            
            # Convert to sorted list
            main_categories_list = sorted(list(main_categories))
            
            print(f"✅ Extracted {len(main_categories_list)} main category URLs")
            
            # Display the categories
            print(f"\n📋 MAIN CATEGORIES ({len(main_categories_list)}):")
            for i, cat_url in enumerate(main_categories_list, 1):
                category_name = cat_url.replace(f"{self.base_url}/", "").replace("/", "").replace("-", " ").title()
                print(f"  {i:2d}. {category_name}: {cat_url}")
            
            return main_categories_list
            
        except Exception as e:
            print(f"❌ Error extracting categories: {e}")
            return []
    
    def test_category_pagination(self, category_url, max_pages=5):
        """Test pagination for a category to find actual page count"""
        print(f"\n🔍 Testing pagination for: {category_url}")
        
        # Simple test without browser - just check if URLs exist
        valid_pages = []
        
        for page_num in range(1, max_pages + 1):
            test_url = f"{category_url}?p={page_num}"
            
            try:
                response = requests.get(test_url, timeout=10)
                if response.status_code == 200:
                    # Basic check for product content
                    content_length = len(response.content)
                    has_products = "product-item" in response.text
                    
                    if has_products and content_length > 10000:  # Reasonable content size
                        valid_pages.append({
                            "page": page_num,
                            "url": test_url,
                            "content_size": content_length,
                            "status": "valid"
                        })
                        print(f"    ✅ Page {page_num}: Valid ({content_length} bytes)")
                    else:
                        print(f"    ❌ Page {page_num}: No products or empty")
                        break
                else:
                    print(f"    ❌ Page {page_num}: HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"    ❌ Page {page_num}: Error - {e}")
                break
        
        return valid_pages
    
    def generate_category_config(self, categories):
        """Generate configuration for the main workflow"""
        config = {
            "extraction_timestamp": datetime.now().isoformat(),
            "sitemap_url": self.sitemap_url,
            "total_main_categories": len(categories),
            "categories": [],
            "pagination_pattern": "?p={page_num}",
            "extraction_requirements": {
                "required_fields": ["name", "product_url", "price", "ean_barcode", "stock_status"],
                "stock_detection": "OUT OF STOCK when applicable",
                "ean_extraction": "when applicable (majority of products)"
            }
        }
        
        # Test a few categories for pagination
        print(f"\n🧪 Testing pagination for 3 sample categories...")
        
        for i, category_url in enumerate(categories[:3]):  # Test first 3
            category_name = category_url.replace(f"{self.base_url}/", "").replace("/", "").replace("-", " ").title()
            
            print(f"\n{'='*60}")
            print(f"Testing: {category_name}")
            print(f"URL: {category_url}")
            
            pagination_results = self.test_category_pagination(category_url, max_pages=3)
            
            config["categories"].append({
                "name": category_name,
                "url": category_url,
                "pagination_tested": True,
                "valid_pages": len(pagination_results),
                "pagination_results": pagination_results
            })
        
        # Add remaining categories without testing
        for category_url in categories[3:]:
            category_name = category_url.replace(f"{self.base_url}/", "").replace("/", "").replace("-", " ").title()
            config["categories"].append({
                "name": category_name,
                "url": category_url,
                "pagination_tested": False
            })
        
        return config
    
    def save_config(self, config):
        """Save the configuration to a file"""
        filename = f"main_categories_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n📁 Configuration saved to: {filename}")
        
        # Display summary
        print(f"\n📊 SUMMARY:")
        print(f"📋 Main Categories: {config['total_main_categories']}")
        print(f"🧪 Tested Categories: {len([c for c in config['categories'] if c.get('pagination_tested')])}")
        print(f"📄 Pagination Pattern: {config['pagination_pattern']}")
        print(f"📋 Required Fields: {', '.join(config['extraction_requirements']['required_fields'])}")
        
        return filename

def main():
    """Main execution function"""
    extractor = MainCategoryExtractor()
    
    # Step 1: Extract main categories from sitemap
    print("🚀 Starting main category extraction...")
    categories = extractor.extract_main_categories_from_sitemap()
    
    if not categories:
        print("❌ No categories extracted. Exiting.")
        return
    
    # Step 2: Generate configuration with pagination testing
    config = extractor.generate_category_config(categories)
    
    # Step 3: Save configuration
    config_file = extractor.save_config(config)
    
    print("\n✅ Main category extraction complete!")
    print(f"📋 Found {len(categories)} main categories ready for scraping")
    print(f"📄 Use pagination pattern ?p=N where N is page number")
    print(f"📊 Required extraction: name, URL, price, EAN/barcode, stock status")
    print(f"📁 Configuration saved to: {config_file}")

if __name__ == "__main__":
    main()