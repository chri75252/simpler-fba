"""
Playwright Helpers module.
Provides standardized functions for launching and managing Playwright browser instances.
Useful for auxiliary tasks that require browser automation separate from the main Amazon extraction.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Default user agent
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"

# Constants
DEFAULT_VIEWPORT_SIZE = {"width": 1280, "height": 800}
DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds
POST_NAVIGATION_STABILIZE_WAIT = 5  # 5 seconds


@dataclass
class BrowserOptions:
    """Options for browser configuration."""
    headless: bool = False  # Default to visible browser for debugging
    user_agent: str = DEFAULT_USER_AGENT
    viewport_width: int = DEFAULT_VIEWPORT_SIZE["width"]
    viewport_height: int = DEFAULT_VIEWPORT_SIZE["height"]
    locale: str = "en-GB"
    timezone_id: str = "Europe/London"
    navigation_timeout: int = DEFAULT_NAVIGATION_TIMEOUT
    use_persistent_context: bool = False
    user_data_dir: Optional[str] = None
    proxy: Optional[Dict[str, str]] = None


async def get_async_context(
    options: Optional[BrowserOptions] = None,
    browser_type: str = "chromium"
) -> Tuple[Browser, BrowserContext]:
    """
    Launch a browser and get a BrowserContext using Playwright's async API.
    
    Args:
        options: Browser configuration options
        browser_type: The type of browser to launch ('chromium', 'firefox', or 'webkit')
        
    Returns:
        Tuple of (Browser, BrowserContext)
    """
    if options is None:
        options = BrowserOptions()
    
    log.info(f"Launching {browser_type} browser (headless: {options.headless})")
    
    try:
        playwright = await async_playwright().start()
        browser_module = getattr(playwright, browser_type)
        
        if options.use_persistent_context and options.user_data_dir:
            log.info(f"Using persistent context with user data dir: {options.user_data_dir}")
            context = await browser_module.launch_persistent_context(
                user_data_dir=options.user_data_dir,
                headless=options.headless,
                viewport={"width": options.viewport_width, "height": options.viewport_height},
                user_agent=options.user_agent,
                locale=options.locale,
                timezone_id=options.timezone_id,
                proxy=options.proxy,
                accept_downloads=True
            )
            browser = None  # No separate browser object when using persistent context
        else:
            log.info("Launching non-persistent browser context")
            browser = await browser_module.launch(headless=options.headless, proxy=options.proxy)
            context = await browser.new_context(
                viewport={"width": options.viewport_width, "height": options.viewport_height},
                user_agent=options.user_agent,
                locale=options.locale,
                timezone_id=options.timezone_id,
                accept_downloads=True
            )
        
        # Set default timeout
        context.set_default_navigation_timeout(options.navigation_timeout)
        
        return browser, context
    
    except Exception as e:
        log.error(f"Error launching browser: {e}")
        raise


async def close_context_and_browser(browser: Optional[Browser], context: BrowserContext) -> None:
    """
    Close a browser context and browser safely.
    
    Args:
        browser: Browser instance to close (can be None if using persistent context)
        context: BrowserContext to close
    """
    try:
        if context:
            log.info("Closing browser context")
            await context.close()
        
        if browser:
            log.info("Closing browser")
            await browser.close()
    
    except Exception as e:
        log.error(f"Error closing browser/context: {e}")


async def get_async_page(
    options: Optional[BrowserOptions] = None,
    browser_type: str = "chromium",
    start_url: str = "about:blank"
) -> Tuple[Browser, BrowserContext, Page]:
    """
    Get a complete setup with Browser, Context and Page for quick automation tasks.
    
    Args:
        options: Browser configuration options
        browser_type: The type of browser to launch
        start_url: Initial URL to navigate to
        
    Returns:
        Tuple of (Browser, BrowserContext, Page)
    """
    browser, context = await get_async_context(options, browser_type)
    
    try:
        log.info(f"Creating new page and navigating to {start_url}")
        page = await context.new_page()
        
        if start_url != "about:blank":
            await page.goto(start_url, wait_until="domcontentloaded")
            # Optional: allow page to stabilize
            await asyncio.sleep(POST_NAVIGATION_STABILIZE_WAIT)
        
        return browser, context, page
    
    except Exception as e:
        log.error(f"Error creating page or navigating: {e}")
        await close_context_and_browser(browser, context)
        raise


async def connect_to_chrome_debug_port(port: int = 9222) -> Tuple[Browser, BrowserContext]:
    """
    Connect to an existing Chrome instance running with --remote-debugging-port.
    
    Args:
        port: The debug port Chrome was launched with
        
    Returns:
        Tuple of (Browser, BrowserContext)
    """
    try:
        log.info(f"Connecting to Chrome debug port {port}")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{port}")
        
        if not browser.contexts:
            log.warning("No existing browser contexts found")
            return browser, None
        
        context = browser.contexts[0]  # Use the first available context
        log.info(f"Successfully connected to Chrome debug port {port}")
        return browser, context
    
    except Exception as e:
        log.error(f"Error connecting to Chrome debug port {port}: {e}")
        raise


if __name__ == "__main__":
    async def test_browser():
        """Simple test to verify browser functionality."""
        browser, context, page = await get_async_page(
            options=BrowserOptions(headless=False), 
            start_url="https://example.com"
        )
        
        try:
            # Take a screenshot as proof of execution
            await page.screenshot(path="playwright_test.png")
            print(f"Page title: {await page.title()}")
            
            # Test page operations
            h1_text = await page.inner_text("h1")
            print(f"H1 text: {h1_text}")
            
            return True
        finally:
            await close_context_and_browser(browser, context)
    
    # Run the test
    print("Testing Playwright Helpers")
    asyncio.run(test_browser())
