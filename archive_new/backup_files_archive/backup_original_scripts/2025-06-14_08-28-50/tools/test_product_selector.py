#!/usr/bin/env python3
"""
Test Product Selector
Tests the product selector on a known category page
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_product_selector():
    """Test the product selector on a known category page"""
    
    # Test on a category page that should have products
    test_url = "https://www.clearance-king.co.uk/clearance-lines.html"
    
    print(f"🔍 Testing product selector on: {test_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url) as response:
                if response.status == 200:
                    content = await response.text()
                    print(f"✅ Successfully fetched page (Size: {len(content)} bytes)")
                else:
                    print(f"❌ Failed to fetch page: HTTP {response.status}")
                    return
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Test different product selectors
        selectors_to_test = [
            'li.item.product.product-item',  # Current selector
            '.product-item',
            '.product',
            '.item',
            'li.item',
            'li.product',
            'li.product-item',
            '[data-product-id]',
            '.product-container',
            'div.product',
            'article.product',
            '.product-card'
        ]
        
        print(f"\n🧪 Testing different product selectors:")
        
        for selector in selectors_to_test:
            try:
                products = soup.select(selector)
                print(f"  {selector}: Found {len(products)} products")
                
                if len(products) > 0 and len(products) < 50:  # Show details for reasonable numbers
                    for i, product in enumerate(products[:3]):  # Show first 3
                        # Try to extract title
                        title_selectors = ['a.product-item-link', 'a', '.title', '.name', 'h2', 'h3']
                        title = "No title found"
                        for title_sel in title_selectors:
                            title_elem = product.select_one(title_sel)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                break
                        
                        print(f"    Product {i+1}: {title[:50]}...")
                        
            except Exception as e:
                print(f"  {selector}: ERROR - {e}")
        
        # Also check the page structure
        print(f"\n📋 Page structure analysis:")
        print(f"  Total <li> elements: {len(soup.select('li'))}")
        print(f"  Total elements with 'product' class: {len(soup.select('.product'))}")
        print(f"  Total elements with 'item' class: {len(soup.select('.item'))}")
        print(f"  Total <a> elements: {len(soup.select('a'))}")
        
        # Look for common e-commerce patterns
        print(f"\n🔍 Looking for common e-commerce patterns:")
        patterns = [
            ('.product-list', 'Product list container'),
            ('.products', 'Products container'),
            ('.catalog', 'Catalog container'),
            ('.grid', 'Grid container'),
            ('.listing', 'Listing container'),
            ('ol.products', 'Ordered list of products'),
            ('ul.products', 'Unordered list of products'),
        ]
        
        for pattern, description in patterns:
            elements = soup.select(pattern)
            if elements:
                print(f"  Found {len(elements)} {description} elements")
                # Look inside the first one
                if elements:
                    children = elements[0].find_all(['li', 'div', 'article'], recursive=False)
                    print(f"    First container has {len(children)} direct children")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_product_selector())
