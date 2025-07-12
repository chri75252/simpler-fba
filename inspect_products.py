#!/usr/bin/env python3
"""
Simple product inspector to examine available products on PoundWholesale homepage.
"""

import asyncio
from playwright.async_api import async_playwright
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def inspect_products():
    """Inspect the products available on the homepage."""
    
    playwright = await async_playwright().start()
    
    try:
        # Connect to shared Chrome
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        contexts = browser.contexts
        if contexts:
            page = contexts[0].pages[0] if contexts[0].pages else await contexts[0].new_page()
        else:
            context = await browser.new_context()
            page = await context.new_page()
        
        current_url = page.url
        log.info(f"Current URL: {current_url}")
        
        # Navigate to homepage if needed
        if "poundwholesale.co.uk" not in current_url:
            log.info("Navigating to homepage...")
            await page.goto("https://www.poundwholesale.co.uk/")
            await page.wait_for_load_state('networkidle')
        
        # Find all product links that match our criteria
        log.info("\n🔍 Finding actual product links...")
        
        # Get all links on the page - focus on visible product areas
        # First check the product containers we know have products
        product_containers = [
            '.product a[href*="poundwholesale.co.uk/"]',
            '.product-item a[href*="poundwholesale.co.uk/"]',
            '.products a[href*="poundwholesale.co.uk/"]'
        ]
        
        all_links = []
        for selector in product_containers:
            container_links = await page.locator(selector).all()
            log.info(f"Found {len(container_links)} links with selector: {selector}")
            all_links.extend(container_links)
        
        # If no products in containers, check all visible links
        if not all_links:
            all_links = await page.locator('a[href*="poundwholesale.co.uk/"]:visible').all()
        
        log.info(f"Total links found: {len(all_links)}")
        
        # First, let's see ALL the links to understand the pattern
        log.info("\n📄 First 20 links found:")
        for i, link in enumerate(all_links[:20]):
            try:
                href = await link.get_attribute('href')
                text = await link.text_content()
                is_visible = await link.is_visible()
                log.info(f"  [{i+1}] {href} | Text: '{text[:50]}' | Visible: {is_visible}")
            except:
                log.info(f"  [{i+1}] Error reading link")
        
        actual_products = []
        for link in all_links[:50]:  # Check first 50 links
            try:
                href = await link.get_attribute('href')
                text = await link.text_content()
                is_visible = await link.is_visible()
                
                # Much more lenient filtering - just exclude obvious system pages
                if (href and is_visible and 
                    href.startswith('https://www.poundwholesale.co.uk/') and
                    'javascript:' not in href and
                    len(href.split('/')) > 4):  # Must have at least 4 URL parts (deeper than homepage)
                    
                    actual_products.append({
                        'url': href,
                        'text': text.strip()[:100] if text else 'No text',
                        'url_parts': len(href.split('/'))
                    })
            
            except Exception as e:
                log.debug(f"Error checking link: {e}")
        
        # Sort by URL depth (more specific URLs first)
        actual_products.sort(key=lambda x: x['url_parts'], reverse=True)
        
        log.info(f"\n📦 Found {len(actual_products)} potential product links:")
        for i, product in enumerate(actual_products[:10]):  # Show first 10
            log.info(f"  [{i+1}] {product['url']}")
            log.info(f"      Text: '{product['text']}'")
            log.info(f"      Depth: {product['url_parts']} URL parts")
            log.info("")
        
        # Test navigation to first product
        if actual_products:
            test_product = actual_products[0]
            log.info(f"🧪 Testing navigation to: {test_product['url']}")
            
            try:
                await page.goto(test_product['url'])
                await page.wait_for_load_state('networkidle')
                
                final_url = page.url
                title = await page.title()
                
                log.info(f"✅ Navigation successful!")
                log.info(f"   Final URL: {final_url}")
                log.info(f"   Page title: {title}")
                
                # Check for product-specific elements
                log.info("\n🔍 Checking for product elements...")
                
                # Title selectors
                title_selectors = ['h1', '.product-title', '.entry-title', '.page-title']
                for selector in title_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            text = await element.text_content()
                            log.info(f"   Title found via '{selector}': {text[:100]}")
                            break
                    except:
                        pass
                
                # Price selectors
                price_selectors = ['.price', '.product-price', '.woocommerce-Price-amount', 'meta[property="product:price:amount"]']
                for selector in price_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            text = await element.text_content()
                            log.info(f"   Price found via '{selector}': {text}")
                            break
                    except:
                        pass
                
                # EAN/Barcode check
                log.info(f"   Page content contains 'EAN': {'EAN' in await page.content()}")
                log.info(f"   Page content contains 'Barcode': {'Barcode' in await page.content()}")
                log.info(f"   Page content contains 'Code:': {'Code:' in await page.content()}")
                
            except Exception as e:
                log.error(f"❌ Navigation failed: {e}")
    
    except Exception as e:
        log.error(f"Error during inspection: {e}")
    
    finally:
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(inspect_products())