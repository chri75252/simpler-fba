#!/usr/bin/env python3
"""
Test script to debug EAN extraction issue for cleaning products.
This script will directly test the extract_ean function on specific product URLs.
"""

import sys
import os
import asyncio
import re
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.configurable_supplier_scraper import ConfigurableSupplierScraper
from urllib.parse import urlparse

async def test_ean_extraction():
    """Test EAN extraction on specific product URLs"""
    
    # Initialize scraper
    scraper = ConfigurableSupplierScraper(headless=False)
    
    # Test URLs from the cache - one working (toys) and one failing (cleaning)
    test_urls = [
        {
            "url": "https://www.poundwholesale.co.uk/hoot-light-up-teddy-bear-assorted-colours-cdu",
            "expected_ean": "5056170316644",
            "category": "toys"
        },
        {
            "url": "https://www.poundwholesale.co.uk/bettina-multicoloured-sponge-scourers-8-pack", 
            "expected_ean": "5052578016384",  # From screenshot
            "category": "cleaning"
        }
    ]
    
    for test_case in test_urls:
        print(f"\n🧪 Testing {test_case['category']} product: {test_case['url']}")
        print(f"Expected EAN: {test_case['expected_ean']}")
        
        try:
            # Get page content
            html_content = await scraper.get_page_content(test_case['url'])
            
            if not html_content:
                print(f"❌ Failed to fetch page content")
                continue
                
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Test the extract_ean function directly
            extracted_ean = scraper.extract_ean(soup, test_case['url'])
            
            print(f"Extracted EAN: {extracted_ean}")
            
            if extracted_ean == test_case['expected_ean']:
                print(f"✅ SUCCESS: EAN extracted correctly")
            elif extracted_ean:
                print(f"⚠️ WARNING: EAN extracted but different from expected")
            else:
                print(f"❌ FAILURE: No EAN extracted")
                
                # Debug: Check if the expected EAN is in the HTML
                if test_case['expected_ean'] in html_content:
                    print(f"🔍 DEBUG: Expected EAN '{test_case['expected_ean']}' IS present in HTML")
                    
                    # Check the specific pattern used by extract_ean
                    pattern = r'Product Barcode/ASIN/EAN:\s*([0-9]{8,14})'
                    matches = re.finditer(pattern, html_content, re.IGNORECASE)
                    pattern_matches = [match.group(1) for match in matches]
                    
                    if pattern_matches:
                        print(f"🔍 DEBUG: Pattern matches found: {pattern_matches}")
                    else:
                        print(f"🔍 DEBUG: Pattern 'Product Barcode/ASIN/EAN:' NOT found in HTML")
                        
                        # Check for variations
                        if "Product Barcode/ASIN/EAN:" in html_content:
                            print(f"🔍 DEBUG: Text 'Product Barcode/ASIN/EAN:' found in HTML")
                        else:
                            print(f"🔍 DEBUG: Text 'Product Barcode/ASIN/EAN:' NOT found in HTML")
                            
                else:
                    print(f"🔍 DEBUG: Expected EAN '{test_case['expected_ean']}' NOT present in HTML")
                
        except Exception as e:
            print(f"❌ ERROR during extraction: {e}")
    
    # Cleanup
    await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_ean_extraction())