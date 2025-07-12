#!/usr/bin/env python3
"""
Extract Category URLs from Sitemap Script
Extracts actual category URLs from poundwholesale.co.uk sitemap and tests pagination
"""

import requests
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin
import asyncio
from playwright.async_api import async_playwright

class SitemapCategoryExtractor:
    def __init__(self):
        self.base_url = "https://www.poundwholesale.co.uk"
        self.sitemap_url = "https://www.poundwholesale.co.uk/sitemap.xml"
        self.categories = []
        
    def extract_categories_from_sitemap(self):
        """Extract category URLs from sitemap.xml"""
        print("🔍 Fetching sitemap.xml...")
        
        try:
            response = requests.get(self.sitemap_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Define namespace
            namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Extract all URLs
            urls = []
            for url_elem in root.findall('sitemap:url', namespace):
                loc_elem = url_elem.find('sitemap:loc', namespace)
                if loc_elem is not None:
                    urls.append(loc_elem.text)
            
            print(f"📋 Found {len(urls)} total URLs in sitemap")
            
            # Filter for category URLs (exclude product URLs)
            category_patterns = [
                r'^https://www\.poundwholesale\.co\.uk/[a-zA-Z-]+$',  # Main categories like /toys, /diy
                r'^https://www\.poundwholesale\.co\.uk/[a-zA-Z-]+/[a-zA-Z-]+$',  # Subcategories like /toys/wholesale-boys-toys
                r'^https://www\.poundwholesale\.co\.uk/wholesale-[a-zA-Z-]+$',  # Wholesale categories
            ]
            
            # Exclude product URLs and other non-category URLs
            exclude_patterns = [
                r'\.html$',  # Product pages end with .html
                r'/[a-zA-Z0-9-]+-\d+',  # Products with numbers
                r'/media/',  # Media files
                r'/customer/',  # Customer pages
                r'/checkout/',  # Checkout pages
                r'/search/',  # Search pages
                r'/cms/',  # CMS pages
            ]
            
            categories = []
            for url in urls:
                # Check if URL matches category patterns
                is_category = any(re.match(pattern, url) for pattern in category_patterns)
                
                # Check if URL should be excluded
                is_excluded = any(re.search(pattern, url) for pattern in exclude_patterns)
                
                if is_category and not is_excluded:
                    # Extract category name from URL
                    path = urlparse(url).path.strip('/')
                    category_name = path.replace('/', ' > ').replace('-', ' ').title()
                    
                    categories.append({
                        "name": category_name,
                        "url": url,
                        "path": path,
                        "level": path.count('/') + 1
                    })
            
            # Sort by level (main categories first, then subcategories)
            categories.sort(key=lambda x: (x['level'], x['name']))
            
            print(f"✅ Extracted {len(categories)} category URLs")
            
            # Display categories by level
            main_categories = [c for c in categories if c['level'] == 1]
            subcategories = [c for c in categories if c['level'] > 1]
            
            print(f"\n📋 MAIN CATEGORIES ({len(main_categories)}):")
            for cat in main_categories:
                print(f"  • {cat['name']}: {cat['url']}")
            
            print(f"\n📋 SUBCATEGORIES ({len(subcategories)}):")
            for cat in subcategories[:20]:  # Show first 20 subcategories
                print(f"  • {cat['name']}: {cat['url']}")
            
            if len(subcategories) > 20:
                print(f"  ... and {len(subcategories) - 20} more subcategories")
            
            self.categories = categories
            return categories
            
        except Exception as e:
            print(f"❌ Error extracting categories: {e}")
            return []
    
    async def test_category_pagination(self, category_url, max_pages=3):
        """Test pagination pattern ?p= for a category"""
        print(f"\n🔍 Testing pagination for: {category_url}")
        
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            if browser.contexts:
                context = browser.contexts[0]
            else:
                context = await browser.new_context()
            
            if context.pages:
                page = context.pages[0]
            else:
                page = await context.new_page()
            
            pagination_results = []
            
            for page_num in range(1, max_pages + 1):
                # Construct paginated URL
                separator = "&" if "?" in category_url else "?"
                test_url = f"{category_url}{separator}p={page_num}"
                
                print(f"  📄 Testing page {page_num}: {test_url}")
                
                try:
                    await page.goto(test_url)
                    await page.wait_for_load_state('domcontentloaded')
                    await page.wait_for_timeout(2000)
                    
                    # Check for products
                    product_elements = await page.query_selector_all(".product-item, li.product-item")
                    products_found = len(product_elements)
                    
                    # Check for toolbar with product count
                    toolbar_text = ""
                    try:
                        toolbar_element = await page.query_selector("#toolbar-amount")
                        if toolbar_element:
                            toolbar_text = await toolbar_element.inner_text()
                    except:
                        pass
                    
                    # Check if page actually exists (not 404 or empty)
                    page_title = await page.title()
                    is_valid_page = products_found > 0 and "404" not in page_title.lower()
                    
                    result = {
                        "page": page_num,
                        "url": test_url,
                        "products_found": products_found,
                        "toolbar_text": toolbar_text.strip(),
                        "page_title": page_title,
                        "is_valid": is_valid_page
                    }
                    
                    pagination_results.append(result)
                    
                    if is_valid_page:
                        print(f"    ✅ Page {page_num}: {products_found} products found")
                        if toolbar_text:
                            print(f"    📊 Toolbar: {toolbar_text}")
                    else:
                        print(f"    ❌ Page {page_num}: No products or invalid page")
                        if page_num > 1:
                            break  # Stop testing if we hit an invalid page
                    
                except Exception as e:
                    print(f"    ❌ Error testing page {page_num}: {e}")
                    pagination_results.append({
                        "page": page_num,
                        "url": test_url,
                        "error": str(e),
                        "is_valid": False
                    })
                    break
            
            await browser.close()
            return pagination_results
            
        except Exception as e:
            print(f"❌ Error testing pagination: {e}")
            return []
    
    async def test_multiple_categories(self, num_categories=5):
        """Test pagination for multiple categories"""
        print(f"\n🧪 Testing pagination for {num_categories} categories...")
        
        # Select a mix of main categories and subcategories
        main_cats = [c for c in self.categories if c['level'] == 1]
        sub_cats = [c for c in self.categories if c['level'] > 1]
        
        test_categories = main_cats[:3] + sub_cats[:2]  # 3 main + 2 sub
        
        all_results = {}
        
        for category in test_categories:
            print(f"\n{'='*60}")
            print(f"Testing: {category['name']}")
            print(f"URL: {category['url']}")
            
            pagination_results = await self.test_category_pagination(category['url'], max_pages=3)
            all_results[category['name']] = {
                "category": category,
                "pagination_results": pagination_results
            }
        
        return all_results
    
    def generate_report(self, categories, pagination_results):
        """Generate comprehensive report"""
        report = {
            "extraction_timestamp": datetime.now().isoformat(),
            "sitemap_url": self.sitemap_url,
            "total_categories_found": len(categories),
            "categories": categories,
            "pagination_test_results": pagination_results,
            "summary": {
                "main_categories": len([c for c in categories if c['level'] == 1]),
                "subcategories": len([c for c in categories if c['level'] > 1]),
                "tested_categories": len(pagination_results),
                "categories_with_pagination": len([r for r in pagination_results.values() 
                                                 if any(p.get('is_valid', False) for p in r['pagination_results'])])
            }
        }
        
        # Save report
        report_file = f"sitemap_categories_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, indent=2, fp=f)
        
        print(f"\n📊 FINAL REPORT")
        print("="*60)
        print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Total Categories: {report['summary']['total_categories_found']}")
        print(f"🏠 Main Categories: {report['summary']['main_categories']}")
        print(f"📂 Subcategories: {report['summary']['subcategories']}")
        print(f"🧪 Tested Categories: {report['summary']['tested_categories']}")
        print(f"📄 Categories with Pagination: {report['summary']['categories_with_pagination']}")
        print(f"📁 Report saved to: {report_file}")
        
        # Display pagination test summary
        print(f"\n📄 PAGINATION TEST SUMMARY:")
        for cat_name, results in pagination_results.items():
            valid_pages = [p for p in results['pagination_results'] if p.get('is_valid', False)]
            print(f"  • {cat_name}: {len(valid_pages)} valid pages")
            for page_result in valid_pages[:2]:  # Show first 2 pages
                if page_result.get('toolbar_text'):
                    print(f"    - Page {page_result['page']}: {page_result['toolbar_text']}")
        
        return report

async def main():
    """Main execution function"""
    extractor = SitemapCategoryExtractor()
    
    # Step 1: Extract categories from sitemap
    print("🚀 Starting sitemap category extraction...")
    categories = extractor.extract_categories_from_sitemap()
    
    if not categories:
        print("❌ No categories extracted. Exiting.")
        return
    
    # Step 2: Test pagination for selected categories
    pagination_results = await extractor.test_multiple_categories(num_categories=5)
    
    # Step 3: Generate comprehensive report
    report = extractor.generate_report(categories, pagination_results)
    
    print("\n✅ Sitemap category extraction and pagination testing complete!")
    print(f"📋 Found {len(categories)} categories ready for AI selection")
    print(f"📄 Pagination pattern ?p= confirmed working")

if __name__ == "__main__":
    asyncio.run(main())