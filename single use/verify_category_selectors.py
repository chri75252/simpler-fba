#!/usr/bin/env python3
"""
Manual Category Verification Script
Tests each category individually with proper selectors and product counting
"""

import asyncio
import json
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class CategorySelectorVerifier:
    def __init__(self):
        self.base_url = "https://www.poundwholesale.co.uk/"
        self.browser = None
        self.page = None
        
    async def connect_to_browser(self):
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            if self.browser.contexts:
                context = self.browser.contexts[0]
            else:
                context = await self.browser.new_context()
            
            if context.pages:
                self.page = context.pages[0]
            else:
                self.page = await context.new_page()
                
            await self.page.bring_to_front()
            log.info("✅ Connected to Chrome browser")
            return True
            
        except Exception as e:
            log.error(f"❌ Failed to connect to browser: {e}")
            return False
    
    async def extract_actual_category_urls(self):
        """Extract actual category URLs by clicking through submenu items"""
        log.info("🔍 Extracting actual category URLs from navigation...")
        
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state('domcontentloaded')
        await self.page.wait_for_timeout(2000)
        
        categories = []
        
        # Try to find main navigation menu items
        main_nav_items = await self.page.query_selector_all("#pw-menu-list > li")
        log.info(f"Found {len(main_nav_items)} main navigation items")
        
        for i, nav_item in enumerate(main_nav_items[:18]):
            try:
                # Check if this is a direct link first
                direct_link = await nav_item.query_selector("a[href]:not([href^='#'])")
                if direct_link:
                    href = await direct_link.get_attribute("href")
                    text = await direct_link.inner_text()
                    if href and not href.startswith('#'):
                        categories.append({
                            "name": text.strip(),
                            "url": href if href.startswith('http') else f"{self.base_url.rstrip('/')}{href}",
                            "type": "direct_link"
                        })
                        log.info(f"Direct link: {text.strip()} -> {href}")
                        continue
                
                # For submenu items, try to hover and extract submenu links
                submenu_trigger = await nav_item.query_selector("a[href^='#']")
                if submenu_trigger:
                    trigger_text = await submenu_trigger.inner_text()
                    log.info(f"Submenu trigger: {trigger_text}")
                    
                    # Hover over the item to reveal submenu
                    await submenu_trigger.hover()
                    await self.page.wait_for_timeout(500)
                    
                    # Look for submenu items
                    submenu_id = await submenu_trigger.get_attribute("href")
                    if submenu_id and submenu_id.startswith('#'):
                        submenu_selector = f"{submenu_id} a[href]:not([href^='#'])"
                        submenu_links = await self.page.query_selector_all(submenu_selector)
                        
                        if submenu_links:
                            log.info(f"Found {len(submenu_links)} submenu items for {trigger_text}")
                            for sub_link in submenu_links[:5]:  # Limit to first 5 subcategories
                                sub_href = await sub_link.get_attribute("href")
                                sub_text = await sub_link.inner_text()
                                if sub_href and sub_text:
                                    categories.append({
                                        "name": f"{trigger_text} > {sub_text.strip()}",
                                        "url": sub_href if sub_href.startswith('http') else f"{self.base_url.rstrip('/')}{sub_href}",
                                        "type": "submenu_item",
                                        "parent": trigger_text
                                    })
                                    log.info(f"  Submenu item: {sub_text.strip()} -> {sub_href}")
                        else:
                            log.warning(f"No submenu items found for {trigger_text}")
                
            except Exception as e:
                log.error(f"Error processing navigation item {i}: {e}")
                continue
        
        return categories
    
    async def analyze_category_products(self, category):
        """Analyze a single category for product count and pagination"""
        log.info(f"📊 Analyzing category: {category['name']}")
        
        try:
            await self.page.goto(category['url'])
            await self.page.wait_for_load_state('domcontentloaded')
            await self.page.wait_for_timeout(3000)
            
            # Check for products count using your specified selector
            products_info = {
                "category_name": category['name'],
                "category_url": category['url'],
                "total_products": 0,
                "products_per_page": 0,
                "total_pages": 1,
                "has_pagination": False,
                "error": None
            }
            
            # Extract product count from toolbar-amount
            try:
                toolbar_element = await self.page.query_selector("#toolbar-amount")
                if toolbar_element:
                    toolbar_text = await toolbar_element.inner_text()
                    log.info(f"Toolbar text: {toolbar_text}")
                    
                    # Parse "1-20 of 468 Items" format
                    match = re.search(r'(\d+)-(\d+) of (\d+) Items', toolbar_text)
                    if match:
                        start_item = int(match.group(1))
                        end_item = int(match.group(2))
                        total_items = int(match.group(3))
                        
                        products_info["total_products"] = total_items
                        products_info["products_per_page"] = end_item - start_item + 1
                        products_info["total_pages"] = (total_items + products_info["products_per_page"] - 1) // products_info["products_per_page"]
                        
                        log.info(f"✅ Found {total_items} total products, {products_info['products_per_page']} per page, {products_info['total_pages']} pages")
                    else:
                        log.warning(f"Could not parse toolbar format: {toolbar_text}")
                else:
                    log.warning("Toolbar element not found")
            except Exception as e:
                log.warning(f"Error extracting product count: {e}")
            
            # Check for pagination
            try:
                pagination_elements = await self.page.query_selector_all(".pages a, .pagination a")
                if pagination_elements:
                    products_info["has_pagination"] = True
                    log.info(f"✅ Pagination found: {len(pagination_elements)} elements")
                else:
                    log.info("No pagination found")
            except Exception as e:
                log.warning(f"Error checking pagination: {e}")
            
            # Test product selectors
            try:
                product_items = await self.page.query_selector_all(".product-item, li.product-item")
                actual_products_on_page = len(product_items)
                log.info(f"✅ Found {actual_products_on_page} product items on page using .product-item selector")
                
                if actual_products_on_page > 0 and products_info["products_per_page"] == 0:
                    products_info["products_per_page"] = actual_products_on_page
                    log.info(f"Updated products_per_page to {actual_products_on_page} based on selector count")
            except Exception as e:
                log.warning(f"Error testing product selectors: {e}")
            
            return products_info
            
        except Exception as e:
            log.error(f"❌ Failed to analyze {category['name']}: {e}")
            return {
                "category_name": category['name'],
                "category_url": category['url'],
                "error": str(e),
                "total_products": 0,
                "products_per_page": 0,
                "total_pages": 0
            }
    
    async def run_verification(self):
        """Run complete category verification"""
        if not await self.connect_to_browser():
            return
        
        try:
            # Extract actual category URLs
            categories = await self.extract_actual_category_urls()
            log.info(f"✅ Extracted {len(categories)} category URLs")
            
            # Analyze each category
            results = []
            for i, category in enumerate(categories):
                log.info(f"🔄 Processing category {i+1}/{len(categories)}: {category['name']}")
                analysis = await self.analyze_category_products(category)
                results.append(analysis)
                await self.page.wait_for_timeout(1000)  # Respectful delay
            
            # Generate report
            report = {
                "verification_timestamp": datetime.now().isoformat(),
                "total_categories_verified": len(results),
                "categories": results,
                "summary": {
                    "total_products_across_all_categories": sum(r.get('total_products', 0) for r in results),
                    "categories_with_products": len([r for r in results if r.get('total_products', 0) > 0]),
                    "categories_with_pagination": len([r for r in results if r.get('has_pagination', False)])
                }
            }
            
            # Save report
            report_file = f"category_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, indent=2, fp=f)
            
            log.info(f"✅ Verification complete! Report saved to: {report_file}")
            
            # Display summary
            print("\n" + "="*80)
            print("📊 CATEGORY VERIFICATION SUMMARY")
            print("="*80)
            print(f"Total Categories Verified: {len(results)}")
            print(f"Categories with Products: {report['summary']['categories_with_products']}")
            print(f"Total Products Found: {report['summary']['total_products_across_all_categories']}")
            print(f"Categories with Pagination: {report['summary']['categories_with_pagination']}")
            
            print("\n🎯 TOP CATEGORIES BY PRODUCT COUNT:")
            sorted_cats = sorted(results, key=lambda x: x.get('total_products', 0), reverse=True)
            for i, cat in enumerate(sorted_cats[:10]):
                if cat.get('total_products', 0) > 0:
                    print(f"  {i+1}. {cat['category_name']}: {cat.get('total_products', 0)} products ({cat.get('total_pages', 0)} pages)")
            
            return report
            
        except Exception as e:
            log.error(f"❌ Verification failed: {e}")
        finally:
            if self.browser:
                await self.browser.close()

async def main():
    verifier = CategorySelectorVerifier()
    await verifier.run_verification()

if __name__ == "__main__":
    asyncio.run(main())