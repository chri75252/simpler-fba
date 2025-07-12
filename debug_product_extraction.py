#!/usr/bin/env python3
"""
Debug script to test product extraction from poundwholesale.co.uk
"""

import asyncio
import sys
import os
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse

# Add tools directory to path
sys.path.append('tools')
from configurable_supplier_scraper import ConfigurableSupplierScraper

async def debug_product_extraction():
    """Debug the product extraction process step by step"""
    
    url = "https://www.poundwholesale.co.uk/"
    scraper = ConfigurableSupplierScraper()
    
    print(f"🔍 Testing product extraction from: {url}")
    print("=" * 60)
    
    # Step 1: Fetch HTML
    print("Step 1: Fetching HTML...")
    html_content = await scraper.fetch_html(url)
    if not html_content:
        print("❌ Failed to fetch HTML content")
        return
    
    print(f"✅ HTML fetched, length: {len(html_content)} characters")
    
    # Step 2: Extract product elements 
    print("\nStep 2: Extracting product elements...")
    product_elements = scraper.extract_product_elements(html_content, url)
    print(f"Found {len(product_elements)} product elements")
    
    if not product_elements:
        print("❌ No product elements found!")
        
        # Debug: Let's check what selectors are being used
        parsed_url = urlparse(url)
        selectors = scraper._get_selectors_for_domain(parsed_url.netloc)
        print(f"Selectors config: {selectors}")
        
        # Debug: Let's see if we can find ANY products manually
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try common product selectors
        test_selectors = ['.product-item', '.product', 'article', '.item', '[class*="product"]']
        for selector in test_selectors:
            elements = soup.select(selector)
            print(f"  Manual test '{selector}': {len(elements)} elements")
            if elements and len(elements) > 0:
                print(f"    First element: {str(elements[0])[:200]}...")
        
        return
    
    print(f"✅ Found {len(product_elements)} product elements")
    
    # Step 3: Test extraction on first few elements
    print("\nStep 3: Testing field extraction...")
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    for i, element in enumerate(product_elements[:5]):  # Test first 5
        print(f"\n--- Product Element {i+1} ---")
        element_html = str(element)
        print(f"HTML snippet: {element_html[:300]}...")
        
        # Extract each field
        title = await scraper.extract_title(element, element_html, url)
        price = await scraper.extract_price(element, element_html, url)
        product_url = await scraper.extract_url(element, element_html, url, base_url)
        image_url = await scraper.extract_image(element, element_html, url, base_url)
        
        print(f"Title: {title}")
        print(f"Price: {price}")
        print(f"URL: {product_url}")
        print(f"Image: {image_url}")
        
        # Check if it would be included
        if title and price:
            print("✅ Would be INCLUDED (has both title and price)")
        else:
            print("❌ Would be SKIPPED (missing title or price)")
            
    # Step 4: Run the full scrape
    print(f"\nStep 4: Running full scrape (max 10 products)...")
    products = await scraper.scrape_products_from_url(url, max_products=10)
    print(f"Final result: {len(products)} products extracted")
    
    for i, product in enumerate(products):
        print(f"Product {i+1}: {product['title']} - {product['price']}")

if __name__ == "__main__":
    asyncio.run(debug_product_extraction())