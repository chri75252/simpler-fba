#!/usr/bin/env python3
"""
Find Actual Category URLs
Based on the examples provided: /wholesale-garden/ and /toys/
Find these specific category directories and test them with pagination
"""

import requests
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import re

class ActualCategoryFinder:
    def __init__(self):
        self.base_url = "https://www.poundwholesale.co.uk"
        
        # Based on the examples you provided and the failed analysis report
        self.known_categories = [
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
            "ebay-amazon-sellers"  # This one we know works from the analysis
        ]
        
    def test_category_urls(self):
        """Test each potential category URL to see if it exists and has products"""
        valid_categories = []
        
        print("🔍 Testing known category URLs...")
        
        for category in self.known_categories:
            category_url = f"{self.base_url}/{category}/"
            
            print(f"\n{'='*60}")
            print(f"Testing: {category}")
            print(f"URL: {category_url}")
            
            try:
                response = requests.get(category_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Check for products
                    has_products = any([
                        'product-item' in content,
                        'class="product' in content,
                        'product-name' in content,
                        '<li class="item product product-item"' in content
                    ])
                    
                    # Check for pagination
                    has_pagination = any([
                        '?p=' in content,
                        'page=' in content,
                         'Next' in content and 'Previous' in content,
                        'pagination' in content.lower()
                    ])
                    
                    # Check for product count
                    toolbar_match = re.search(r'(\d+)-(\d+)\s+of\s+(\d+)', content)
                    product_count = None
                    if toolbar_match:
                        product_count = int(toolbar_match.group(3))
                    
                    if has_products:
                        print(f"    ✅ SUCCESS: Found products")
                        if product_count:
                            print(f"    📊 Product count: {product_count}")
                        if has_pagination:
                            print(f"    📄 Pagination available")
                        
                        valid_categories.append({
                            "name": category.replace("-", " ").title(),
                            "url": category_url,
                            "has_products": True,
                            "product_count": product_count,
                            "has_pagination": has_pagination
                        })
                    else:
                        print(f"    ❌ No products found")
                        
                elif response.status_code == 404:
                    print(f"    ❌ 404 - Category does not exist")
                else:
                    print(f"    ❌ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        return valid_categories
    
    async def test_pagination_for_category(self, category_url, max_pages=3):
        """Test pagination using Playwright for a specific category"""
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
                test_url = f"{category_url}?p={page_num}"
                print(f"  📄 Testing page {page_num}: {test_url}")
                
                try:
                    await page.goto(test_url, wait_until='domcontentloaded')
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
                    
                    # Check page title
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
                    break
            
            await browser.close()
            return pagination_results
            
        except Exception as e:
            print(f"❌ Error testing pagination: {e}")
            return []
    
    async def comprehensive_test(self):
        """Run comprehensive test of all valid categories"""
        # First, find valid categories
        valid_categories = self.test_category_urls()
        
        if not valid_categories:
            print("\n❌ No valid categories found!")
            return
        
        print(f"\n✅ Found {len(valid_categories)} valid categories")
        
        # Test pagination for the first 3 valid categories
        enhanced_categories = []
        
        for i, category in enumerate(valid_categories[:3]):
            print(f"\n{'='*60}")
            print(f"PAGINATION TEST {i+1}: {category['name']}")
            
            pagination_results = await self.test_pagination_for_category(category['url'])
            
            enhanced_category = category.copy()
            enhanced_category['pagination_results'] = pagination_results
            enhanced_category['valid_pages'] = len([r for r in pagination_results if r.get('is_valid')])
            enhanced_categories.append(enhanced_category)
        
        # Add remaining categories without pagination testing
        for category in valid_categories[3:]:
            enhanced_categories.append(category)
        
        return enhanced_categories
    
    def generate_final_report(self, categories):
        """Generate final report with all findings"""
        report = {
            "extraction_timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_categories_tested": len(self.known_categories),
            "valid_categories_found": len(categories),
            "categories": categories,
            "pagination_pattern": "?p={page_num}",
            "extraction_fields": [
                "name (product title)",
                "product_url (full URL to product page)", 
                "price (in GBP)",
                "ean/barcode (when applicable - majority of products)",
                "stock_status (OUT OF STOCK when applicable)"
            ],
            "next_steps": [
                "Use these validated category URLs for scraping",
                "Apply ?p=N pagination pattern (N = page number)",
                "Continue until page returns 0 products",
                "Extract all required fields for each product"
            ]
        }
        
        # Save report
        filename = f"valid_categories_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 FINAL REPORT:")
        print(f"📋 Categories Tested: {report['total_categories_tested']}")
        print(f"✅ Valid Categories: {report['valid_categories_found']}")
        print(f"📄 Pagination Pattern: {report['pagination_pattern']}")
        print(f"📁 Report saved: {filename}")
        
        print(f"\n🎯 READY FOR SCRAPING:")
        for cat in categories:
            status = f"✅ {cat['name']}: {cat['url']}"
            if cat.get('product_count'):
                status += f" ({cat['product_count']} products)"
            if cat.get('valid_pages'):
                status += f" [{cat['valid_pages']} pages tested]"
            print(f"  {status}")
        
        return filename

async def main():
    """Main execution function"""
    finder = ActualCategoryFinder()
    
    print("🚀 Starting actual category validation...")
    print("📋 Testing known category patterns based on URL analysis")
    
    # Run comprehensive test
    categories = await finder.comprehensive_test()
    
    if categories:
        # Generate final report
        report_file = finder.generate_final_report(categories)
        
        print("\n✅ Category validation complete!")
        print(f"📊 Found {len(categories)} working categories")
        print(f"📁 Full report: {report_file}")
    else:
        print("\n❌ No working categories found")

if __name__ == "__main__":
    asyncio.run(main())