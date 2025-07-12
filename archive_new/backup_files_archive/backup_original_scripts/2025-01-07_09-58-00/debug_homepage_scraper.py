#!/usr/bin/env python3
"""
Debug Homepage Scraper
Shows exactly what URLs are found and why they're being filtered out
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

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config'))

from tools.configurable_supplier_scraper import ConfigurableSupplierScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class DebugHomepageScraper:
    def __init__(self):
        self.output_dir = Path("OUTPUTS/FBA_ANALYSIS/homepage_analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def debug_homepage_scraping(self, supplier_url="https://www.clearance-king.co.uk"):
        """Debug the homepage scraping process step by step"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.output_dir / f"debug_homepage_scraping_{timestamp}.json"
        
        log.info(f"🔍 DEBUG: Analyzing homepage scraping for: {supplier_url}")
        
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
            
            # Test the selectors one by one
            nav_selectors = [
                '.navigation ul li a',  # Primary navigation - most effective for clearance-king
                '.navigation .level0 a',  # Magento-style navigation
                '.nav-sections .level0 a',  # Alternative Magento navigation
                'nav ul li a',  # Generic navigation
                '.navigation a[href]', '.nav a[href]', '.menu a[href]',
                '.main-menu a[href]', '.primary-menu a[href]', 'header a[href]',
                '.header a[href]', '.category-menu a[href]', '.categories a[href]',
                '#mainNav a[href]', '#main-navigation a[href]', 'ul.navbar-nav a[href]',
                'div.sitemap a[href]', 'footer nav a[href]'
            ]
            
            debug_data = {
                "timestamp": datetime.now().isoformat(),
                "supplier_url": supplier_url,
                "homepage_size_bytes": len(content),
                "selector_results": []
            }
            
            all_found_urls = set()
            
            for selector in nav_selectors:
                try:
                    links = soup.select(selector)
                    log.info(f"🔍 Selector '{selector}': Found {len(links)} links")
                    
                    selector_urls = []
                    for link in links:
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        
                        if href:
                            absolute_url = urljoin(supplier_url, href)
                            
                            # Test the _looks_like_category_url logic step by step
                            is_category = await self._debug_looks_like_category_url(absolute_url, supplier_url)
                            
                            link_info = {
                                "text": text,
                                "href": href,
                                "absolute_url": absolute_url,
                                "is_category": is_category
                            }
                            selector_urls.append(link_info)
                            all_found_urls.add(absolute_url)
                            
                            if is_category:
                                log.info(f"  ✅ CATEGORY: {text} -> {absolute_url}")
                            else:
                                log.info(f"  ❌ FILTERED: {text} -> {absolute_url}")
                    
                    debug_data["selector_results"].append({
                        "selector": selector,
                        "links_found": len(links),
                        "category_links": len([l for l in selector_urls if l["is_category"]]),
                        "links": selector_urls[:20]  # Limit for readability
                    })
                    
                except Exception as e:
                    log.error(f"Error with selector '{selector}': {e}")
                    debug_data["selector_results"].append({
                        "selector": selector,
                        "error": str(e)
                    })
            
            # Summary
            category_urls = [url for url in all_found_urls if await self._debug_looks_like_category_url(url, supplier_url)]
            
            debug_data["summary"] = {
                "total_unique_urls_found": len(all_found_urls),
                "category_urls_after_filtering": len(category_urls),
                "category_urls": list(category_urls)
            }
            
            # Save debug data
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"💾 Debug analysis saved to: {log_file}")
            log.info(f"📊 SUMMARY: Found {len(all_found_urls)} total URLs, {len(category_urls)} passed category filter")
            
            return debug_data
            
        except Exception as e:
            log.error(f"❌ Error during debug analysis: {e}")
            return None
    
    async def _debug_looks_like_category_url(self, url: str, base_url: str) -> bool:
        """Debug version of _looks_like_category_url with detailed logging"""
        if not url or not isinstance(url, str): 
            return False

        url_lower = url.lower()
        parsed_url = urlparse(url)
        parsed_base_url = urlparse(base_url)

        # 1. Domain check
        if parsed_url.netloc != parsed_base_url.netloc and not parsed_url.netloc.endswith('.' + parsed_base_url.netloc):
            return False

        # 2. Exclude common file extensions and specific non-category paths
        excluded_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.css', '.js', '.xml', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.svg', '.webp', '.mp4', '.mov']
        if any(url_lower.endswith(ext) for ext in excluded_extensions): 
            return False

        non_category_keywords = [
            '/cart', '/basket', '/checkout', '/payment', '/account', '/login', '/register',
            '/contact', '/about', '/help', '/support', '/faq', '/terms', '/privacy', '/policy',
            '/search', '/wishlist', '/compare', '/blog', '/news', '/article', '/review',
            'mailto:', 'tel:', 'javascript:', '#', 'add_to_cart', 'my_account',
            'customer_service', 'track_order', 'order_status', 'returns_policy', 'shipping_info',
            'sitemap', 'rss_feed', 'brand_list', 'all_brands', 'gift_card', 'voucher_codes',
            'event=', 'attachment_id=', 'replytocom=', 'author/', 'tag/', 'feed/'
        ]
        # Check full URL for non-category keywords
        if any(keyword in url_lower for keyword in non_category_keywords): 
            return False
        # Avoid fragment-only URLs or URLs that are just the base_url again
        if (parsed_url.path in ['', '/'] and not parsed_url.query and parsed_url.fragment) or url == base_url:
            return False

        # 3. Positive category indicators in path or query
        category_keywords = [
            'category', 'categories', 'cat', 'collection', 'dept', 'department', 'section',
            'products', 'items', 'group', 'range', 'shop', 'browse', 'listing', 'gallery',
            'view', 'filter', 'sort', 'type', 'style', 'gender', 'sale', 'offers', 'deals',
            'brand/', 'manufacturer/', 'c/', 'p/', 'pg/', 'page/', 'shopby', 'product-list', 'product_list'
        ]
        path_and_query = (parsed_url.path + '?' + parsed_url.query).lower()
        if any(keyword in path_and_query for keyword in category_keywords): 
            return True

        # 4. Structural checks: Path depth, common patterns
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        # Allow slightly deeper paths if they don't end in a file extension
        if 1 <= len(path_segments) <= 5:
            last_segment = path_segments[-1]
            # Avoid paths ending with numbers that look like product IDs if too long, unless it's a common page pattern
            if not (last_segment.isdigit() and len(last_segment) > 6 and not any(p_ind in last_segment for p_ind in ["page","p"])):
                import re
                if re.match(r'^[a-z0-9][a-z0-9\-_]*[a-z0-9]$', last_segment, re.IGNORECASE) and len(last_segment) > 1:
                    return True
        
        # 5. Check for common pagination parameters
        if parsed_url.query and any(page_param in parsed_url.query.lower() for page_param in ['page=', 'p=', 'pg=', 'startindex=', 'pagenumber=']):
            return True

        return False

async def main():
    """Main function to run the debug analysis"""
    scraper = DebugHomepageScraper()
    
    print("🔍 Debug Homepage Scraper")
    print("=" * 50)
    
    # Debug the scraping process
    result = await scraper.debug_homepage_scraping()
    
    if result:
        print(f"\n✅ Debug analysis complete! Check the output file for detailed results.")
        print(f"📁 Output directory: {scraper.output_dir}")
    else:
        print("\n❌ Debug analysis failed!")

if __name__ == "__main__":
    asyncio.run(main())
