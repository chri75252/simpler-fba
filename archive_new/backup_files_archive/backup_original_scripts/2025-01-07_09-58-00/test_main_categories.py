#!/usr/bin/env python3
"""
Test Main Categories
Tests the main navigation categories from the screenshot
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_main_categories():
    """Test the main navigation categories"""
    
    # Main categories from the screenshot
    main_categories = [
        ("CLEARANCE", "https://www.clearance-king.co.uk/clearance-lines.html"),
        ("50P & UNDER", "https://www.clearance-king.co.uk/50p-under.html"),
        ("POUND LINES", "https://www.clearance-king.co.uk/pound-lines.html"),
        ("BABY & KIDS", "https://www.clearance-king.co.uk/baby-kids.html"),
        ("GIFTS & TOYS", "https://www.clearance-king.co.uk/gifts-toys.html"),
        ("HEALTH & BEAUTY", "https://www.clearance-king.co.uk/health-beauty.html"),
        ("HOUSEHOLD", "https://www.clearance-king.co.uk/household.html"),
        ("PETS", "https://www.clearance-king.co.uk/pets.html"),
        ("SMOKING", "https://www.clearance-king.co.uk/smoking.html"),
        ("STATIONERY & CRAFTS", "https://www.clearance-king.co.uk/stationery-crafts.html"),
        ("MAILING SUPPLIES", "https://www.clearance-king.co.uk/mailing-supplies.html"),
        ("OTHERS", "https://www.clearance-king.co.uk/catalog/category/view/s/others/id/408/")
    ]
    
    print(f"🔍 Testing main navigation categories from screenshot")
    print("=" * 60)
    
    product_selector = 'li.item.product.product-item'
    
    for category_name, url in main_categories:
        try:
            print(f"\n📂 Testing: {category_name}")
            print(f"   URL: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        print(f"   ✅ Fetched successfully (Size: {len(content)} bytes)")
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        continue
            
            soup = BeautifulSoup(content, 'html.parser')
            products = soup.select(product_selector)
            
            if len(products) >= 2:
                print(f"   🎯 PRODUCTIVE: {len(products)} products found")
                
                # Show first few product titles
                for i, product in enumerate(products[:3]):
                    title_elem = product.select_one('a.product-item-link')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        print(f"      {i+1}. {title[:50]}...")
                    
            else:
                print(f"   ❌ UNPRODUCTIVE: {len(products)} products found")
                
                # Debug: check if page has any products at all
                all_products = soup.select('.product')
                print(f"      (Total .product elements: {len(all_products)})")
                
                # Check if it's a category landing page that needs subcategories
                subcategory_links = soup.select('a[href*=".html"]')
                category_links = [link for link in subcategory_links 
                                if any(keyword in link.get('href', '').lower() 
                                      for keyword in ['category', 'cat', category_name.lower().replace(' ', '-')])]
                if category_links:
                    print(f"      Found {len(category_links)} potential subcategory links")
                    
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n📊 SUMMARY:")
    print("This test shows which main categories are productive and should be prioritized by the AI system.")

if __name__ == "__main__":
    asyncio.run(test_main_categories())
