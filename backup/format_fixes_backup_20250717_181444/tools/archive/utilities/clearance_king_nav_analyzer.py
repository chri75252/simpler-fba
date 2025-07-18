#!/usr/bin/env python3
"""
Clearance King Navigation Analyzer
Specifically analyzes the main navigation categories visible in the screenshot
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class ClearanceKingNavAnalyzer:
    def __init__(self):
        self.output_dir = Path("OUTPUTS/FBA_ANALYSIS/homepage_analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def analyze_main_navigation(self, supplier_url="https://www.clearance-king.co.uk"):
        """Analyze the main navigation categories specifically"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.output_dir / f"clearance_king_nav_analysis_{timestamp}.json"
        
        log.info(f"🔍 Analyzing main navigation for: {supplier_url}")
        
        try:
            # Get the homepage content
            async with aiohttp.ClientSession() as session:
                async with session.get(supplier_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        log.info(f"✅ Successfully fetched homepage (Size: {len(content)} bytes)")
                    else:
                        log.error(f"❌ Failed to fetch homepage: HTTP {response.status}")
                        return
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for the main navigation categories from the screenshot
            # Based on the screenshot, these should be in the main navigation bar
            expected_categories = [
                "CLEARANCE", "50P & UNDER", "POUND LINES", "BABY & KIDS", 
                "GIFTS & TOYS", "HEALTH & BEAUTY", "HOUSEHOLD", "PETS", 
                "SMOKING", "STATIONERY & CRAFTS", "MAILING SUPPLIES", "OTHERS"
            ]
            
            # Try multiple navigation selectors
            nav_selectors = [
                # Main navigation bar
                '.navigation ul li a',
                '.nav-primary ul li a', 
                '.main-nav ul li a',
                '.navbar ul li a',
                'nav ul li a',
                'header nav ul li a',
                '.menu ul li a',
                '.top-menu ul li a',
                
                # Specific to Magento/common e-commerce platforms
                '.navigation .level0 a',
                '.nav-sections .level0 a',
                '.categories-menu a',
                
                # Generic link patterns
                'a[href*="catalog/category"]',
                'a[href*="/category/"]',
                'a[href*="/cat/"]',
                'a[href*="/c/"]',
            ]
            
            found_categories = []
            all_nav_links = []
            
            log.info("🔍 Searching for navigation links...")
            
            for selector in nav_selectors:
                try:
                    links = soup.select(selector)
                    log.info(f"  Selector '{selector}': Found {len(links)} links")
                    
                    for link in links:
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        
                        if href and text:
                            absolute_url = urljoin(supplier_url, href)
                            
                            link_info = {
                                "text": text,
                                "href": href,
                                "absolute_url": absolute_url,
                                "selector": selector
                            }
                            all_nav_links.append(link_info)
                            
                            # Check if this matches expected categories
                            text_upper = text.upper()
                            if any(expected_cat in text_upper for expected_cat in expected_categories):
                                found_categories.append(link_info)
                                log.info(f"    ✅ FOUND EXPECTED: {text} -> {absolute_url}")
                            else:
                                log.info(f"    📝 Other link: {text} -> {absolute_url}")
                                
                except Exception as e:
                    log.debug(f"Error with selector '{selector}': {e}")
            
            # Remove duplicates
            unique_nav_links = []
            seen_urls = set()
            for link in all_nav_links:
                if link['absolute_url'] not in seen_urls:
                    unique_nav_links.append(link)
                    seen_urls.add(link['absolute_url'])
            
            unique_found_categories = []
            seen_cat_urls = set()
            for cat in found_categories:
                if cat['absolute_url'] not in seen_cat_urls:
                    unique_found_categories.append(cat)
                    seen_cat_urls.add(cat['absolute_url'])
            
            # Test productivity of found categories
            log.info(f"\n🧪 Testing productivity of {len(unique_found_categories)} expected categories...")
            
            productive_categories = []
            for cat in unique_found_categories:
                try:
                    product_count = await self._test_category_productivity(cat['absolute_url'])
                    cat['product_count'] = product_count
                    cat['is_productive'] = product_count >= 2
                    
                    if cat['is_productive']:
                        productive_categories.append(cat)
                        log.info(f"  ✅ {cat['text']}: {product_count} products - PRODUCTIVE")
                    else:
                        log.info(f"  ❌ {cat['text']}: {product_count} products - UNPRODUCTIVE")
                        
                except Exception as e:
                    log.error(f"  ❌ Error testing {cat['text']}: {e}")
                    cat['product_count'] = 0
                    cat['is_productive'] = False
                    cat['error'] = str(e)
            
            # Prepare analysis data
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "supplier_url": supplier_url,
                "homepage_size_bytes": len(content),
                "expected_categories": expected_categories,
                "analysis_results": {
                    "total_nav_links_found": len(unique_nav_links),
                    "expected_categories_found": len(unique_found_categories),
                    "productive_categories_found": len(productive_categories),
                    "expected_categories_missing": [
                        cat for cat in expected_categories 
                        if not any(cat in found['text'].upper() for found in unique_found_categories)
                    ]
                },
                "found_expected_categories": unique_found_categories,
                "productive_categories": productive_categories,
                "all_navigation_links": unique_nav_links[:50]  # Limit for readability
            }
            
            # Save analysis to file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"💾 Analysis saved to: {log_file}")
            
            # Print summary
            log.info(f"\n📊 SUMMARY:")
            log.info(f"  Expected categories: {len(expected_categories)}")
            log.info(f"  Found expected categories: {len(unique_found_categories)}")
            log.info(f"  Productive categories: {len(productive_categories)}")
            log.info(f"  Missing categories: {len(analysis_data['analysis_results']['expected_categories_missing'])}")
            
            if analysis_data['analysis_results']['expected_categories_missing']:
                log.info(f"  Missing: {', '.join(analysis_data['analysis_results']['expected_categories_missing'])}")
            
            return analysis_data
            
        except Exception as e:
            log.error(f"❌ Error during navigation analysis: {e}")
            return None
    
    async def _test_category_productivity(self, category_url):
        """Test if a category URL contains products"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(category_url) as response:
                    if response.status != 200:
                        return 0
                    
                    content = await response.text()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Use the same selectors as the main system
            product_selectors = [
                'li.item.product.product-item',  # Main selector from config
                '.product-item',
                '.product',
                '.item',
                '[data-product-id]',
                '.product-container'
            ]
            
            max_products = 0
            for selector in product_selectors:
                try:
                    products = soup.select(selector)
                    max_products = max(max_products, len(products))
                except:
                    continue
            
            return max_products
            
        except Exception as e:
            log.error(f"Error testing category productivity for {category_url}: {e}")
            return 0

async def main():
    """Main function to run the navigation analysis"""
    analyzer = ClearanceKingNavAnalyzer()
    
    print("🔍 Clearance King Navigation Analyzer")
    print("=" * 50)
    
    # Analyze the navigation
    result = await analyzer.analyze_main_navigation()
    
    if result:
        print(f"\n✅ Analysis complete! Check the output file for detailed results.")
        print(f"📁 Output directory: {analyzer.output_dir}")
        
        # Print key findings
        if result['productive_categories']:
            print(f"\n🎯 PRODUCTIVE CATEGORIES FOUND:")
            for cat in result['productive_categories']:
                print(f"  • {cat['text']}: {cat['product_count']} products")
                print(f"    URL: {cat['absolute_url']}")
        else:
            print(f"\n❌ NO PRODUCTIVE CATEGORIES FOUND!")
            print("This explains why the AI system isn't finding good categories to suggest.")
    else:
        print("\n❌ Analysis failed!")

if __name__ == "__main__":
    asyncio.run(main())
