#!/usr/bin/env python3
"""
Simple page inspector to examine PoundWholesale homepage for debugging.
"""

import asyncio
from playwright.async_api import async_playwright
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def inspect_page():
    """Inspect the current page content to understand why navigation failed."""
    
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
        
        # Get page title
        title = await page.title()
        log.info(f"Page title: {title}")
        
        # Check if we're on the homepage
        if "poundwholesale.co.uk" not in current_url:
            log.info("Navigating to homepage...")
            await page.goto("https://www.poundwholesale.co.uk/")
            await page.wait_for_load_state('networkidle')
        
        # Get all navigation links
        log.info("\n🔍 Searching for navigation links...")
        nav_selectors = [
            'nav a', '.nav a', '.navigation a', '.menu a', 
            'a[href*="/category/"]', 'a[href*="/products"]', 'a[href*="/shop"]',
            '.main-nav a', '.primary-nav a'
        ]
        
        for selector in nav_selectors:
            try:
                elements = await page.locator(selector).all()
                if elements:
                    log.info(f"Found {len(elements)} elements with selector: {selector}")
                    for i, element in enumerate(elements[:5]):  # Show first 5
                        text = await element.text_content()
                        href = await element.get_attribute('href')
                        is_visible = await element.is_visible()
                        log.info(f"  [{i+1}] Text: '{text}' | Href: '{href}' | Visible: {is_visible}")
            except Exception as e:
                log.debug(f"Selector '{selector}' failed: {e}")
        
        # Look for product-related links
        log.info("\n🛍️ Searching for product links...")
        product_selectors = [
            'a[href*="/product/"]', '.product a', '.product-card a',
            '.product-item a', '.product-link', 'a[href*="/p/"]'
        ]
        
        for selector in product_selectors:
            try:
                elements = await page.locator(selector).all()
                if elements:
                    log.info(f"Found {len(elements)} product elements with selector: {selector}")
                    for i, element in enumerate(elements[:3]):  # Show first 3
                        text = await element.text_content()
                        href = await element.get_attribute('href')
                        is_visible = await element.is_visible()
                        log.info(f"  [{i+1}] Text: '{text}' | Href: '{href}' | Visible: {is_visible}")
            except Exception as e:
                log.debug(f"Selector '{selector}' failed: {e}")
        
        # Get page structure
        log.info("\n📄 Page structure overview...")
        main_content = await page.locator('main, .main, #main, .content, #content').first.inner_html() if await page.locator('main, .main, #main, .content, #content').first.is_visible() else "No main content found"
        log.info(f"Main content length: {len(main_content)} characters")
        
        # Check for specific PoundWholesale elements
        log.info("\n🏪 Checking for PoundWholesale-specific elements...")
        pw_selectors = [
            '.product-grid', '.products', '.category-nav', '.shop-nav',
            'a:has-text("Home")', 'a:has-text("Shop")', 'a:has-text("Products")',
            'a:has-text("Categories")', 'a:has-text("Browse")'
        ]
        
        for selector in pw_selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    log.info(f"Found {count} elements with selector: {selector}")
                    element = page.locator(selector).first
                    if await element.is_visible():
                        text = await element.text_content()
                        log.info(f"  First element text: '{text}'")
            except Exception as e:
                log.debug(f"Selector '{selector}' failed: {e}")
        
        # Save page HTML for analysis
        html_content = await page.content()
        with open("homepage_content.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        log.info("Saved homepage HTML to homepage_content.html")
        
        # Take screenshot
        await page.screenshot(path="homepage_screenshot.png", full_page=True)
        log.info("Saved homepage screenshot to homepage_screenshot.png")
        
    except Exception as e:
        log.error(f"Error during inspection: {e}")
    
    finally:
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(inspect_page())