#!/usr/bin/env python3
"""
Test the 18 Specific Category URLs
Test the exact category URLs provided by the user with ?p=N pagination
"""

import requests
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import re

class CategoryTester:
    def __init__(self):
        self.base_url = "https://www.poundwholesale.co.uk"
        
        # The exact 18 category URLs provided by the user
        self.categories = [
            "https://www.poundwholesale.co.uk/seasonal/wholesale-summer",
            "https://www.poundwholesale.co.uk/wholesale-garden", 
            "https://www.poundwholesale.co.uk/toys",
            "https://www.poundwholesale.co.uk/leisure-hobbies",
            "https://www.poundwholesale.co.uk/baby-supplies",
            "https://www.poundwholesale.co.uk/wholesale-cleaning",
            "https://www.poundwholesale.co.uk/kitchenware",
            "https://www.poundwholesale.co.uk/health-beauty",
            "https://www.poundwholesale.co.uk/homeware",
            "https://www.poundwholesale.co.uk/diy",
            "https://www.poundwholesale.co.uk/electrical",
            "https://www.poundwholesale.co.uk/pet-supplies",
            "https://www.poundwholesale.co.uk/stationery",
            "https://www.poundwholesale.co.uk/party-gift",
            "https://www.poundwholesale.co.uk/seasonal",
            "https://www.poundwholesale.co.uk/ebay-amazon-sellers",
            # Clothing category - keep for last during analysis
            "https://www.poundwholesale.co.uk/clothing"
        ]
        
    async def test_category_with_pagination(self, category_url, max_pages=None):
        """Test a category URL with ?p=N pagination using Playwright - continue until no more products"""
        category_name = category_url.split("/")[-1].replace("-", " ").title()
        print(f"\n{'='*70}")
        print(f"🔍 TESTING: {category_name}")
        print(f"📍 URL: {category_url}")
        
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
            total_products_found = 0
            page_num = 1
            
            # Continue until no more products found
            while True:
                # Use the ?p=N pagination pattern as specified
                test_url = f"{category_url}?p={page_num}"
                print(f"\n  📄 Testing Page {page_num}: {test_url}")
                
                try:
                    await page.goto(test_url, wait_until='domcontentloaded')
                    await page.wait_for_timeout(2000)
                    
                    # Check for products using multiple selectors
                    product_selectors = [
                        ".product-item",
                        "li.product-item", 
                        ".product",
                        "[data-product-id]"
                    ]
                    
                    products_found = 0
                    for selector in product_selectors:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            products_found = len(elements)
                            break
                    
                    # Check for product details (name, price, URL, EAN, stock status)
                    product_details = []
                    if products_found > 0:
                        # Extract sample product details
                        for i in range(min(3, products_found)):  # Sample first 3 products
                            try:
                                product_element = await page.query_selector_all(product_selectors[0])[i]
                                
                                # Extract product name
                                name_element = await product_element.query_selector("a.product-item-link, .product-item-link")
                                name = await name_element.inner_text() if name_element else "N/A"
                                
                                # Extract product URL
                                url_element = await product_element.query_selector("a.product-item-link")
                                product_url = await url_element.get_attribute("href") if url_element else "N/A"
                                if product_url and not product_url.startswith("http"):
                                    product_url = self.base_url + product_url
                                
                                # Extract price (might require login)
                                price_element = await product_element.query_selector(".price, [data-price-amount]")
                                price = await price_element.inner_text() if price_element else "Login Required"
                                
                                # Check for out of stock
                                stock_element = await product_element.query_selector(".stock.unavailable, .out-of-stock")
                                stock_status = "OUT OF STOCK" if stock_element else "In Stock"
                                
                                product_details.append({
                                    "name": name.strip(),
                                    "product_url": product_url,
                                    "price": price.strip(),
                                    "stock_status": stock_status
                                })
                                
                            except Exception as e:
                                print(f"      ⚠️ Error extracting product {i+1}: {e}")
                    
                    # Check for toolbar with product count (e.g., "1-20 of 59 Items")
                    toolbar_text = ""
                    total_products = None
                    try:
                        toolbar_element = await page.query_selector("#toolbar-amount")
                        if toolbar_element:
                            toolbar_text = await toolbar_element.inner_text()
                            # Extract total count
                            toolbar_match = re.search(r'(\d+)-(\d+)\s+of\s+(\d+)', toolbar_text)
                            if toolbar_match:
                                total_products = int(toolbar_match.group(3))
                    except:
                        pass
                    
                    # Check page title for validation
                    page_title = await page.title()
                    is_valid_page = products_found > 0 and "404" not in page_title.lower()
                    
                    result = {
                        "page": page_num,
                        "url": test_url,
                        "products_found": products_found,
                        "toolbar_text": toolbar_text.strip(),
                        "total_products": total_products,
                        "page_title": page_title,
                        "is_valid": is_valid_page,
                        "sample_products": product_details
                    }
                    
                    pagination_results.append(result)
                    total_products_found += products_found
                    
                    if is_valid_page:
                        status = f"    ✅ Page {page_num}: {products_found} products found"
                        if toolbar_text:
                            status += f" | {toolbar_text}"
                        print(status)
                        
                        # Show sample product details
                        if product_details:
                            print(f"    📦 Sample products:")
                            for j, product in enumerate(product_details, 1):
                                print(f"      {j}. {product['name'][:50]}{'...' if len(product['name']) > 50 else ''}")
                                print(f"         💰 {product['price']} | 📦 {product['stock_status']}")
                        
                        # Continue to next page
                        page_num += 1
                    else:
                        print(f"    ❌ Page {page_num}: No products found - END OF PAGINATION")
                        break  # Exit loop when no products found
                    
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
            
            # Summary for this category
            valid_pages = len([r for r in pagination_results if r.get('is_valid')])
            max_products = max([r.get('total_products', 0) for r in pagination_results if r.get('total_products')] or [0])
            
            summary = {
                "name": category_name,
                "url": category_url,
                "valid_pages": valid_pages,
                "total_products_estimate": max_products,
                "products_found_in_test": total_products_found,
                "pagination_results": pagination_results,
                "status": "SUCCESS" if valid_pages > 0 else "FAILED"
            }
            
            print(f"\n  📊 SUMMARY: {category_name}")
            print(f"    ✅ Valid pages: {valid_pages}")
            print(f"    📦 Estimated total products: {max_products}")
            print(f"    🔍 Products found in test: {total_products_found}")
            
            return summary
            
        except Exception as e:
            print(f"❌ Error testing category {category_name}: {e}")
            return {
                "name": category_name,
                "url": category_url,
                "error": str(e),
                "status": "ERROR"
            }
    
    async def test_all_categories(self):
        """Test all 18 categories"""
        print("🚀 Starting test of 18 category URLs with ?p=N pagination")
        print(f"📋 Total categories to test: {len(self.categories)}")
        
        results = []
        
        # Test first 16 categories (excluding clothing which is last)
        for i, category_url in enumerate(self.categories[:-1], 1):
            print(f"\n🔄 PROGRESS: {i}/{len(self.categories)} categories")
            result = await self.test_category_with_pagination(category_url)
            results.append(result)
        
        # Test clothing category last as requested
        print(f"\n🔄 FINAL CATEGORY: Clothing (as requested - kept for last)")
        clothing_result = await self.test_category_with_pagination(self.categories[-1])
        results.append(clothing_result)
        
        return results
    
    def generate_final_report(self, results):
        """Generate comprehensive report"""
        successful_categories = [r for r in results if r.get('status') == 'SUCCESS']
        failed_categories = [r for r in results if r.get('status') != 'SUCCESS']
        
        total_products = sum([r.get('total_products_estimate', 0) for r in successful_categories])
        
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "total_categories_tested": len(results),
            "successful_categories": len(successful_categories),
            "failed_categories": len(failed_categories),
            "total_products_estimate": total_products,
            "pagination_pattern": "?p={page_num}",
            "extraction_fields": {
                "required": ["name", "product_url", "price", "ean_barcode", "stock_status"],
                "notes": "EAN/barcode when applicable (majority), OUT OF STOCK when applicable"
            },
            "categories": results,
            "ready_for_scraping": [
                {
                    "name": r['name'],
                    "url": r['url'],
                    "estimated_products": r.get('total_products_estimate', 0)
                }
                for r in successful_categories
            ]
        }
        
        # Save report
        filename = f"category_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Display results
        print(f"\n{'='*70}")
        print(f"📊 FINAL VALIDATION REPORT")
        print(f"{'='*70}")
        print(f"📋 Categories tested: {len(results)}")
        print(f"✅ Successful: {len(successful_categories)}")
        print(f"❌ Failed: {len(failed_categories)}")
        print(f"📦 Total products estimate: {total_products:,}")
        print(f"📁 Report saved: {filename}")
        
        if successful_categories:
            print(f"\n🎯 READY FOR SCRAPING ({len(successful_categories)} categories):")
            for cat in successful_categories:
                products = cat.get('total_products_estimate', 0)
                print(f"  ✅ {cat['name']}: {cat['url']} ({products:,} products)")
        
        if failed_categories:
            print(f"\n⚠️ CATEGORIES NEEDING ATTENTION ({len(failed_categories)}):")
            for cat in failed_categories:
                print(f"  ❌ {cat['name']}: {cat.get('error', 'No products found')}")
        
        return filename

async def main():
    """Main execution function"""
    tester = CategoryTester()
    
    # Test all categories
    results = await tester.test_all_categories()
    
    # Generate final report
    report_file = tester.generate_final_report(results)
    
    print(f"\n✅ VALIDATION COMPLETE!")
    print(f"📊 Use these validated categories with ?p=N pagination")
    print(f"📋 Extract: name, product_url, price, EAN/barcode (when applicable), stock_status")
    print(f"📄 Continue pagination until page returns 0 products")

if __name__ == "__main__":
    asyncio.run(main())