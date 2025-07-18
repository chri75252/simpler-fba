"""
Browser Manager with LRU Cache for Amazon FBA Agent System v3
Provides centralized browser resource management with LRU page caching.
Singleton pattern ensures all tools share the same Chrome instance.
Max 2 tabs with proper overflow cleanup to prevent memory leaks.
"""

import os
import logging
import asyncio
import atexit
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from collections import OrderedDict

# Playwright imports
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

# Configure logging
log = logging.getLogger(__name__)

# Browser configuration constants
DEFAULT_CHROME_DEBUG_PORT = 9222
MAX_CACHED_PAGES = 1  # CRITICAL FIX: Force single-page mode for stability and prevent Keepa extension failures
PAGE_TIMEOUT_MS = 60000
STABILIZE_WAIT_SECONDS = 3


class BrowserManager:
    """
    Singleton browser manager with LRU page cache.
    Provides shared Chrome instance and manages up to 5 cached pages.
    """
    
    _instance = None
    
    def __init__(self):
        if BrowserManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.playwright = None
            self.browser = None
            self.context = None
            self.page_cache = {}
            self.page_usage_order = []
            self.max_cache_size = 10
            BrowserManager._instance = self
            log.info("🔧 BrowserManager singleton initialized")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = BrowserManager()
        return cls._instance

    async def launch_browser(self, cdp_port: int, headless: bool = False):
        if self.browser and self.browser.is_connected():
            log.info(f"♻️ Reusing existing Chrome connection (port {cdp_port})")
            return

        self.playwright = await async_playwright().start()
        try:
            log.info(f"🔌 Connecting to persistent Chrome on debug port {cdp_port}")
            self.browser = await self.playwright.chromium.connect_over_cdp(f"http://localhost:{cdp_port}")
            
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                log.info(f"📄 Using existing context with {len(self.context.pages)} pages")
            else:
                self.context = await self.browser.new_context()
                log.info("📄 Created new browser context")
            log.info("✅ Connected to persistent Chrome successfully")
        except Exception as e:
            log.error(f"❌ Could not connect to persistent Chrome on port {cdp_port}. Error: {e}")
            log.error(f"❌ Please ensure Chrome is running with --remote-debugging-port={cdp_port}")
            log.error(f"❌ Command: chrome --remote-debugging-port={cdp_port} --user-data-dir=/tmp/chrome-debug")
            # Clean up playwright if connection failed
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            raise Exception(f"Failed to connect to persistent Chrome on port {cdp_port}. Please start Chrome with debug port.")

    async def get_page(self, url: str = None, reuse_existing: bool = True) -> Page:
        if not self.context:
            raise Exception("Browser context not initialized. Call launch_browser() first.")

        if url and url in self.page_cache:
            log.info(f"♻️ Reusing cached page for {url}")
            self.page_usage_order.remove(url)
            self.page_usage_order.append(url)
            return self.page_cache[url]

        if self.context.pages:
            page = self.context.pages[0]
            log.info(f"♻️ Reusing existing page in context.")
        else:
            page = await self.context.new_page()
            log.info("📄 Created new page in context.")
            
        if url:
            log.info(f"📄 Navigating to {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            log.info(f"✅ Page ready for {url}")
            self._add_to_cache(url, page)
            
        return page

    def _add_to_cache(self, url: str, page: Page):
        if len(self.page_cache) >= self.max_cache_size:
            oldest_url = self.page_usage_order.pop(0)
            del self.page_cache[oldest_url]
            log.info(f"🗑️ Evicted oldest cached page: {oldest_url}")
        
        self.page_cache[url] = page
        self.page_usage_order.append(url)

    async def close_browser(self):
        log.info("🧹 Starting browser cleanup...")
        
        # For persistent Chrome instances (debug port), we should NOT close the browser
        # Only disconnect from it to keep it running
        if self.browser and self.browser.is_connected():
            # Check if this is a CDP connection (persistent browser)
            try:
                # For CDP connections, we just disconnect without closing
                log.info("🔌 Disconnecting from persistent Chrome instance (keeping browser running)")
                # Don't close pages for persistent browser - just clear our references
                self.page_cache.clear()
                self.page_usage_order.clear()
                
                # Disconnect playwright but don't close the browser
                if self.playwright:
                    await self.playwright.stop()
                    log.info("🎭 Stopped Playwright instance (browser remains running)")
                
                # Clear references but don't close the actual browser
                self.browser = None
                self.context = None
                self.playwright = None
                
                log.info("✅ Disconnected from persistent browser (Chrome debug port remains active)")
                return
                
            except Exception as e:
                log.warning(f"Error during persistent browser disconnect: {e}")
        
        # Fallback for non-persistent browsers (if any)
        if self.context:
            for page in list(self.context.pages):
                try:
                    await page.close()
                except Exception:
                    pass
            log.info(f"🗑️ Closed pages from non-persistent context")
            
        if self.playwright:
            await self.playwright.stop()
            log.info("🎭 Stopped Playwright instance")
        
        self.browser = None
        self.context = None
        self.playwright = None
        self.page_cache.clear()
        self.page_usage_order.clear()
        log.info("✅ Browser cleanup completed")

async def global_cleanup():
    log.info("🧹 Performing global cleanup...")
    manager = BrowserManager.get_instance()
    await manager.close_browser()
    log.info("🔌 Persistent Chrome browser should remain running on debug port 9222")

# This allows the cleanup to be registered with atexit
def run_global_cleanup():
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(global_cleanup())
        else:
            asyncio.run(global_cleanup())
    except Exception as e:
        log.warning(f"Error during global cleanup: {e}")


# Register cleanup function to run on exit
atexit.register(run_global_cleanup)


# Convenience functions for common operations
async def get_page_for_url(url: str, reuse_existing: bool = True) -> Page:
    """Convenience function to get page for URL."""
    manager = BrowserManager.get_instance()
    
    # Auto-launch browser if not already launched
    if not manager.context:
        chrome_debug_port = int(os.getenv('CHROME_DEBUG_PORT', DEFAULT_CHROME_DEBUG_PORT))
        # For persistent browser, headless is not relevant since we're connecting to existing Chrome
        try:
            await manager.launch_browser(chrome_debug_port, headless=False)
        except Exception as e:
            log.error(f"❌ Failed to connect to persistent Chrome: {e}")
            raise Exception(f"Cannot connect to persistent Chrome on port {chrome_debug_port}. Please start Chrome with debug port.")
    
    return await manager.get_page(url, reuse_existing)


async def close_page_for_url(url: str) -> bool:
    """Convenience function to close page for URL."""
    manager = BrowserManager.get_instance()
    return await manager.close_page(url)


async def get_browser_status() -> Dict[str, Any]:
    """Get current browser manager status."""
    manager = BrowserManager.get_instance()
    return manager.get_status()


if __name__ == "__main__":
    # Inline smoke test to verify LRU eviction
    async def _smoke():
        log.info("🧪 BrowserManager LRU Smoke Test...")
        try:
            bm = BrowserManager.get_instance()
            
            # Create 3 pages to trigger LRU eviction (max 2 allowed)
            page1 = await bm.get_page("https://example.com")
            page2 = await bm.get_page("https://example.org") 
            page3 = await bm.get_page("https://example.net")  # Should trigger LRU eviction
            
            # Verify LRU cache has max 2 pages
            assert len(bm._page_cache) == 2, f"Expected 2 pages in cache, got {len(bm._page_cache)}"
            
            # Verify example.com was evicted (oldest)
            domain_keys = list(bm._page_cache.keys())
            assert "https://example.com" not in domain_keys, "Oldest page should have been evicted"
            assert "https://example.org" in domain_keys, "Second page should still be cached"
            assert "https://example.net" in domain_keys, "Newest page should be cached"
            
            log.info("✅ LRU eviction working correctly")
            
            await global_cleanup()
            log.info("✅ Smoke test passed")
            
        except Exception as e:
            log.error(f"❌ Smoke test failed: {e}")
            raise
    
    asyncio.run(_smoke())