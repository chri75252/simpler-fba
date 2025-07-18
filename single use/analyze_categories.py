#!/usr/bin/env python3
"""
Poundwholesale Category Analysis Script
Analyzes main categories and their page counts for system optimization
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
import re
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class PoundwholesaleCategoryAnalyzer:
    """Analyzes poundwholesale.co.uk categories and pagination"""
    
    def __init__(self):
        self.base_url = "https://www.poundwholesale.co.uk/"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.categories_data = []
        
    async def connect_to_browser(self) -> bool:
        """Connect to existing Chrome debug instance"""
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
    
    async def extract_main_categories(self) -> List[Dict[str, str]]:
        """Extract main categories using multiple selector strategies"""
        log.info("🔍 Extracting main categories...")
        
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state('domcontentloaded')
        
        categories = []
        
        # Strategy 1: Your specific XPath pattern converted to CSS
        primary_selector = "#pw-menu-list > li"
        try:
            elements = await self.page.query_selector_all(primary_selector)
            log.info(f"📋 Found {len(elements)} elements with primary selector: {primary_selector}")
            
            for i, element in enumerate(elements[:18]):  # Limit to 18 as you mentioned
                try:
                    # Extract link
                    link_element = await element.query_selector("a")
                    if link_element:
                        href = await link_element.get_attribute("href")
                        text = await link_element.inner_text()
                        
                        if href and text:
                            # Make absolute URL
                            if href.startswith('/'):
                                href = urljoin(self.base_url, href)
                            
                            categories.append({
                                "name": text.strip(),
                                "url": href,
                                "index": i + 1,
                                "selector_used": primary_selector
                            })
                            log.info(f"  {i+1}. {text.strip()} -> {href}")
                            
                except Exception as e:
                    log.warning(f"⚠️ Failed to extract category {i+1}: {e}")
                    
        except Exception as e:
            log.error(f"❌ Primary selector failed: {e}")
            
        # Strategy 2: Fallback selectors if primary fails
        if len(categories) < 5:  # If we didn't get enough categories
            log.info("🔄 Trying fallback selectors...")
            fallback_selectors = [
                "nav ul li a",
                ".main-nav li a",
                "[class*='menu'] li a",
                ".navigation li a",
                "header nav li a"
            ]
            
            for selector in fallback_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if len(elements) >= 10:  # Likely main categories
                        log.info(f"✅ Fallback selector found {len(elements)} elements: {selector}")
                        
                        for i, element in enumerate(elements[:18]):
                            try:
                                href = await element.get_attribute("href")
                                text = await element.inner_text()
                                
                                if href and text and "poundwholesale.co.uk" in href:
                                    categories.append({
                                        "name": text.strip(),
                                        "url": href,
                                        "index": i + 1,
                                        "selector_used": selector
                                    })
                                    
                            except Exception as e:
                                continue
                        break
                        
                except Exception as e:
                    continue
        
        log.info(f"📊 Total categories extracted: {len(categories)}")
        return categories
    
    async def analyze_category_pagination(self, category: Dict[str, str]) -> Dict[str, Any]:
        """Analyze pagination for a single category"""
        log.info(f"📄 Analyzing pagination for: {category['name']}")
        
        try:
            await self.page.goto(category['url'])
            await self.page.wait_for_load_state('domcontentloaded')
            await self.page.wait_for_timeout(2000)  # Wait for dynamic content
            
            # Look for pagination indicators
            pagination_info = {
                "category_name": category['name'],
                "category_url": category['url'],
                "total_pages": 1,
                "products_per_page": 0,
                "total_products_estimate": 0,
                "pagination_pattern": None,
                "has_pagination": False,
                "pagination_selectors": []
            }
            
            # Count products on current page
            product_selectors = [
                ".product-item",
                "li.product-item",
                ".product-card",
                "[class*='product']"
            ]
            
            products_found = 0
            for selector in product_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if len(elements) > products_found:
                        products_found = len(elements)
                        pagination_info["products_per_page"] = products_found
                except:
                    continue
            
            # Look for pagination elements
            pagination_selectors = [
                ".pagination",
                ".pages",
                ".page-numbers",
                "a[href*='?p=']",
                "a[href*='page=']",
                "a:has-text('Next')",
                "a:has-text('›')",
                "a:has-text('»')"
            ]
            
            max_page = 1
            for selector in pagination_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        pagination_info["has_pagination"] = True
                        pagination_info["pagination_selectors"].append(selector)
                        
                        # Try to find highest page number
                        for element in elements:
                            try:
                                href = await element.get_attribute("href")
                                text = await element.inner_text()
                                
                                if href:
                                    # Extract page number from URL
                                    page_match = re.search(r'[?&]p=(\d+)', href)
                                    if page_match:
                                        page_num = int(page_match.group(1))
                                        max_page = max(max_page, page_num)
                                        pagination_info["pagination_pattern"] = "?p={page_num}"
                                
                                # Extract page number from text
                                if text and text.isdigit():
                                    page_num = int(text)
                                    max_page = max(max_page, page_num)
                                    
                            except:
                                continue
                                
                except Exception as e:
                    continue
            
            pagination_info["total_pages"] = max_page
            pagination_info["total_products_estimate"] = products_found * max_page
            
            # Test pagination pattern by trying to go to page 2
            if pagination_info["has_pagination"] and max_page > 1:
                try:
                    test_url = category['url']
                    if '?' in test_url:
                        test_url += "&p=2"
                    else:
                        test_url += "?p=2"
                    
                    await self.page.goto(test_url)
                    await self.page.wait_for_load_state('domcontentloaded')
                    
                    # Check if we actually got to page 2
                    page_products = 0
                    for selector in product_selectors:
                        try:
                            elements = await self.page.query_selector_all(selector)
                            page_products = max(page_products, len(elements))
                        except:
                            continue
                    
                    if page_products > 0:
                        pagination_info["pagination_pattern"] = "?p={page_num}"
                        log.info(f"✅ Confirmed pagination pattern: ?p={{page_num}}")
                    
                except Exception as e:
                    log.warning(f"⚠️ Failed to test pagination: {e}")
            
            log.info(f"📊 {category['name']}: {pagination_info['total_pages']} pages, ~{pagination_info['total_products_estimate']} products")
            return pagination_info
            
        except Exception as e:
            log.error(f"❌ Failed to analyze {category['name']}: {e}")
            return {
                "category_name": category['name'],
                "category_url": category['url'],
                "error": str(e),
                "total_pages": 1,
                "products_per_page": 0,
                "total_products_estimate": 0
            }
    
    async def analyze_all_categories(self) -> List[Dict[str, Any]]:
        """Analyze all main categories"""
        log.info("🚀 Starting comprehensive category analysis...")
        
        # Extract main categories
        categories = await self.extract_main_categories()
        
        if not categories:
            log.error("❌ No categories found!")
            return []
        
        # Analyze each category
        results = []
        for i, category in enumerate(categories):
            log.info(f"🔄 Processing category {i+1}/{len(categories)}: {category['name']}")
            
            try:
                pagination_info = await self.analyze_category_pagination(category)
                results.append(pagination_info)
                
                # Small delay to be respectful
                await self.page.wait_for_timeout(1000)
                
            except Exception as e:
                log.error(f"❌ Failed to analyze {category['name']}: {e}")
                results.append({
                    "category_name": category['name'],
                    "category_url": category['url'],
                    "error": str(e),
                    "total_pages": 1
                })
        
        return results
    
    async def generate_report(self, results: List[Dict[str, Any]]) -> None:
        """Generate comprehensive analysis report"""
        log.info("📊 Generating analysis report...")
        
        # Calculate statistics
        total_categories = len(results)
        total_pages = sum(r.get('total_pages', 0) for r in results)
        total_products = sum(r.get('total_products_estimate', 0) for r in results)
        categories_with_pagination = sum(1 for r in results if r.get('has_pagination', False))
        
        # Create report
        report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_main_categories": total_categories,
                "total_pages_across_categories": total_pages,
                "estimated_total_products": total_products,
                "categories_with_pagination": categories_with_pagination,
                "average_pages_per_category": total_pages / total_categories if total_categories > 0 else 0
            },
            "category_details": results,
            "recommendations": {
                "suggested_category_limit": min(total_categories, 500),  # Reasonable for AI processing
                "pagination_pattern": "?p={page_num}",
                "max_pages_per_category": max(r.get('total_pages', 0) for r in results),
                "products_per_page_typical": max(r.get('products_per_page', 0) for r in results)
            }
        }
        
        # Save report
        report_file = f"category_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, indent=2, fp=f)
        
        # Display summary
        print("\n" + "="*80)
        print("📊 POUNDWHOLESALE CATEGORY ANALYSIS REPORT")
        print("="*80)
        print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Main Categories Found: {total_categories}")
        print(f"📄 Total Pages: {total_pages}")
        print(f"📦 Estimated Products: {total_products}")
        print(f"🔗 Categories with Pagination: {categories_with_pagination}")
        print(f"📊 Average Pages per Category: {report['summary']['average_pages_per_category']:.1f}")
        print(f"📁 Report saved to: {report_file}")
        
        print("\n🎯 TOP CATEGORIES BY SIZE:")
        sorted_cats = sorted(results, key=lambda x: x.get('total_products_estimate', 0), reverse=True)
        for i, cat in enumerate(sorted_cats[:10]):
            print(f"  {i+1}. {cat['category_name']}: {cat.get('total_pages', 0)} pages, ~{cat.get('total_products_estimate', 0)} products")
        
        print("\n💡 RECOMMENDATIONS:")
        print(f"  • Set category limit to: {report['recommendations']['suggested_category_limit']}")
        print(f"  • Use pagination pattern: {report['recommendations']['pagination_pattern']}")
        print(f"  • Max pages per category: {report['recommendations']['max_pages_per_category']}")
        print(f"  • Typical products per page: {report['recommendations']['products_per_page_typical']}")
        
        return report

async def main():
    """Main execution function"""
    analyzer = PoundwholesaleCategoryAnalyzer()
    
    if not await analyzer.connect_to_browser():
        log.error("❌ Failed to connect to browser. Make sure Chrome is running with --remote-debugging-port=9222")
        return
    
    try:
        # Analyze categories
        results = await analyzer.analyze_all_categories()
        
        if results:
            # Generate report
            report = await analyzer.generate_report(results)
            log.info("✅ Analysis complete!")
        else:
            log.error("❌ No category analysis results")
            
    except Exception as e:
        log.error(f"❌ Analysis failed: {e}")
    
    finally:
        if analyzer.browser:
            await analyzer.browser.close()

if __name__ == "__main__":
    asyncio.run(main())