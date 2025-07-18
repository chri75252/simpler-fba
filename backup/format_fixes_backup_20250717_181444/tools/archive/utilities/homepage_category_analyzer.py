#!/usr/bin/env python3
"""
Homepage Category Analyzer for Amazon FBA Agent System
Analyzes what categories are actually discovered from the homepage
and logs the AI's decision-making process.
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config'))

from tools.configurable_supplier_scraper import ConfigurableSupplierScraper
from supplier_config_loader import load_supplier_selectors

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class HomepageCategoryAnalyzer:
    def __init__(self):
        self.output_dir = Path("OUTPUTS/FBA_ANALYSIS/homepage_analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def analyze_homepage_categories(self, supplier_url="https://www.clearance-king.co.uk"):
        """Analyze what categories are actually found on the homepage"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.output_dir / f"homepage_analysis_{timestamp}.json"
        
        log.info(f"🔍 Analyzing homepage categories for: {supplier_url}")
        
        # Initialize scraper
        scraper = ConfigurableSupplierScraper()
        
        try:
            # Extract categories from homepage
            log.info(f"📥 Fetching homepage content from: {supplier_url}")
            
            # Get the homepage content
            async with aiohttp.ClientSession() as session:
                async with session.get(supplier_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        log.info(f"✅ Successfully fetched homepage (Size: {len(content)} bytes)")
                    else:
                        log.error(f"❌ Failed to fetch homepage: HTTP {response.status}")
                        return
            
            # Extract categories using the scraper's logic
            categories = await scraper.get_homepage_categories(supplier_url)
            
            # Prepare analysis data
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "supplier_url": supplier_url,
                "homepage_size_bytes": len(content),
                "categories_discovered": {
                    "count": len(categories),
                    "urls": categories
                },
                "category_analysis": []
            }
            
            log.info(f"🎯 Found {len(categories)} potential category URLs:")
            
            # Analyze each category
            for i, category_url in enumerate(categories, 1):
                log.info(f"  {i}. {category_url}")
                
                # Test if category is productive (has products)
                try:
                    product_count = await self._test_category_productivity(category_url)
                    is_productive = product_count >= 2
                    
                    category_info = {
                        "url": category_url,
                        "product_count": product_count,
                        "is_productive": is_productive,
                        "category_type": self._classify_category(category_url)
                    }
                    
                    analysis_data["category_analysis"].append(category_info)
                    
                    status = "✅ PRODUCTIVE" if is_productive else "❌ UNPRODUCTIVE"
                    log.info(f"     → {status} ({product_count} products)")
                    
                except Exception as e:
                    log.error(f"     → ❌ ERROR testing category: {e}")
                    analysis_data["category_analysis"].append({
                        "url": category_url,
                        "product_count": 0,
                        "is_productive": False,
                        "error": str(e),
                        "category_type": self._classify_category(category_url)
                    })
            
            # Save analysis to file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"💾 Analysis saved to: {log_file}")
            
            # Print summary
            productive_count = sum(1 for cat in analysis_data["category_analysis"] if cat.get("is_productive", False))
            log.info(f"📊 SUMMARY: {productive_count}/{len(categories)} categories are productive")
            
            return analysis_data
            
        except Exception as e:
            log.error(f"❌ Error during homepage analysis: {e}")
            return None
        finally:
            await scraper.close_session()
    
    async def _test_category_productivity(self, category_url):
        """Test if a category URL contains products"""
        try:
            scraper = ConfigurableSupplierScraper()
            
            # Fetch the category page
            async with aiohttp.ClientSession() as session:
                async with session.get(category_url) as response:
                    if response.status != 200:
                        return 0
                    
                    content = await response.text()
            
            # Load selectors for the domain
            from urllib.parse import urlparse
            domain = urlparse(category_url).netloc
            selectors = load_supplier_selectors(domain)
            
            if not selectors:
                log.warning(f"No selectors found for domain: {domain}")
                return 0
            
            # Count products using the scraper's logic
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            product_selector = selectors.get('product_container', '')
            if product_selector:
                products = soup.select(product_selector)
                return len(products)
            
            return 0
            
        except Exception as e:
            log.error(f"Error testing category productivity for {category_url}: {e}")
            return 0
    
    def _classify_category(self, url):
        """Classify the category type based on URL patterns"""
        url_lower = url.lower()
        
        if any(term in url_lower for term in ['clearance', 'sale', 'discount', 'pound', '50p']):
            return "clearance"
        elif any(term in url_lower for term in ['baby', 'kids', 'children', 'toy']):
            return "baby_kids"
        elif any(term in url_lower for term in ['health', 'beauty', 'personal']):
            return "health_beauty"
        elif any(term in url_lower for term in ['household', 'home', 'kitchen']):
            return "household"
        elif any(term in url_lower for term in ['pet', 'animal']):
            return "pets"
        elif any(term in url_lower for term in ['smoking', 'tobacco']):
            return "smoking"
        elif any(term in url_lower for term in ['stationery', 'craft', 'office']):
            return "stationery_crafts"
        elif any(term in url_lower for term in ['mailing', 'shipping', 'postal']):
            return "mailing"
        else:
            return "other"

async def main():
    """Main function to run the homepage analysis"""
    analyzer = HomepageCategoryAnalyzer()
    
    print("🔍 Amazon FBA Homepage Category Analyzer")
    print("=" * 50)
    
    # Analyze the homepage
    result = await analyzer.analyze_homepage_categories()
    
    if result:
        print(f"\n✅ Analysis complete! Check the output file for detailed results.")
        print(f"📁 Output directory: {analyzer.output_dir}")
    else:
        print("\n❌ Analysis failed!")

if __name__ == "__main__":
    asyncio.run(main())
