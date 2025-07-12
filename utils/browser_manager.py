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
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.chrome_debug_port = DEFAULT_CHROME_DEBUG_PORT
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # LRU cache for pages (OrderedDict maintains insertion order)
        self._page_cache: OrderedDict[str, Page] = OrderedDict()
        self._cache_lock = asyncio.Lock()
        
        # Status tracking
        self._is_connected = False
        self._connection_time = None
        self._total_pages_created = 0
        
        self._initialized = True
        log.info("🔧 BrowserManager singleton initialized")
    
    async def connect(self) -> Browser:
        """
        Connect to Chrome debug port if not already connected.
        Returns shared browser instance.
        """
        async with self._lock:
            if self._is_connected and self.browser:
                log.info(f"♻️ Reusing existing Chrome connection (port {self.chrome_debug_port})")
                return self.browser
            
            try:
                log.info(f"🔌 Connecting to Chrome on debug port {self.chrome_debug_port}")
                
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    f"http://localhost:{self.chrome_debug_port}"
                )
                
                # Use default context or create if needed
                if self.browser.contexts:
                    self.context = self.browser.contexts[0]
                    log.info(f"📄 Using existing context with {len(self.context.pages)} pages")
                else:
                    self.context = await self.browser.new_context()
                    log.info("📄 Created new browser context")
                
                self._is_connected = True
                self._connection_time = datetime.now()
                
                log.info(f"✅ Connected to Chrome successfully")
                return self.browser
                
            except Exception as e:
                log.error(f"❌ Failed to connect to Chrome on port {self.chrome_debug_port}: {e}")
                log.error("Ensure Chrome is running with --remote-debugging-port=9222")
                raise
    
    async def get_page(self, url: str, reuse_existing: bool = True) -> Page:
        """
        Get page for URL with LRU caching.
        
        Args:
            url: Target URL to navigate to
            reuse_existing: Whether to reuse cached page for same domain
            
        Returns:
            Page instance ready for use
        """
        await self.connect()  # Ensure connected
        
        async with self._cache_lock:
            # Extract domain for cache key
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain_key = f"{parsed.scheme}://{parsed.netloc}"
            
            # Check if we have cached page for this domain
            if reuse_existing and domain_key in self._page_cache:
                log.info(f"♻️ Reusing cached page for {domain_key}")
                # Move to end (most recently used)
                page = self._page_cache[domain_key]
                del self._page_cache[domain_key]
                self._page_cache[domain_key] = page
                
                # Navigate to new URL if different
                if page.url != url:
                    try:
                        await page.goto(url, timeout=PAGE_TIMEOUT_MS)
                        await asyncio.sleep(STABILIZE_WAIT_SECONDS)
                    except Exception as e:
                        log.warning(f"Navigation failed, creating new page: {e}")
                        return await self._create_new_page(url, domain_key)
                
                return page
            
            # Need to create new page
            return await self._create_new_page(url, domain_key)
    
    async def _create_new_page(self, url: str, domain_key: str) -> Page:
        """Create new page and manage LRU cache overflow."""
        # Check if we need to evict oldest page
        if len(self._page_cache) >= MAX_CACHED_PAGES:
            oldest_key, oldest_page = self._page_cache.popitem(last=False)
            try:
                await oldest_page.close()
                log.info(f"🗑️ Evicted oldest cached page: {oldest_key}")
            except Exception as e:
                log.warning(f"Error closing evicted page: {e}")
        
        # Create new page
        try:
            page = await self.context.new_page()
            self._total_pages_created += 1
            
            log.info(f"📄 Created new page #{self._total_pages_created} for {domain_key}")
            
            # Navigate to URL with improved timeout handling
            try:
                await page.goto(url, timeout=30000)  # Reduced timeout from 60s to 30s
                await asyncio.sleep(STABILIZE_WAIT_SECONDS)
            except PlaywrightTimeoutError as e:
                log.warning(f"Navigation timeout for {url}: {e}")
                await page.close()
                return None  # Graceful fallback
            except Exception as e:
                log.warning(f"Navigation error for {url}: {e}")
                await page.close()
                return None  # Graceful fallback
            
            # Add to cache
            self._page_cache[domain_key] = page
            
            log.info(f"✅ Page ready for {url}")
            return page
            
        except Exception as e:
            log.error(f"❌ Failed to create page for {url}: {e}")
            raise
    
    async def get_active_user_page(self) -> Optional[Page]:
        """
        Get the currently active/visible page that the user is viewing.
        
        This method identifies which tab/page is currently visible and has focus,
        ensuring automation works on the same page the user is looking at.
        
        Returns:
            Page instance that is currently active, or None if no active page
        """
        await self.connect()  # Ensure connected
        
        if not self.context or not self.context.pages:
            log.warning("No pages available in browser context")
            return None
        
        # Check all pages to find the one that's visible and has focus
        for page in self.context.pages:
            try:
                # Use JavaScript to check if page is visible and has focus
                is_active = await page.evaluate("""() => {
                    return document.visibilityState === 'visible' && document.hasFocus();
                }""")
                
                if is_active:
                    log.info(f"✅ Found active user page: {page.url[:100]}...")
                    return page
                    
            except Exception as e:
                # Page might be in transient state (closing, crashed, etc.)
                log.debug(f"Could not evaluate page {getattr(page, 'url', 'unknown')}: {e}")
                continue
        
        # Fallback: if no page has focus (browser minimized, etc.), use most recent page
        if self.context.pages:
            fallback_page = self.context.pages[-1]  # Last page is usually most recent
            log.warning(f"⚠️ No active page found, using fallback: {fallback_page.url[:100]}...")
            return fallback_page
        
        log.error("❌ No pages available")
        return None
    
    async def close_page(self, url_or_domain: str) -> bool:
        """
        Close and remove specific page from cache.
        
        Args:
            url_or_domain: URL or domain key to close
            
        Returns:
            True if page was found and closed
        """
        async with self._cache_lock:
            # Try both as-is and as domain key
            from urllib.parse import urlparse
            
            keys_to_try = [url_or_domain]
            if url_or_domain.startswith('http'):
                parsed = urlparse(url_or_domain)
                domain_key = f"{parsed.scheme}://{parsed.netloc}"
                keys_to_try.append(domain_key)
            
            for key in keys_to_try:
                if key in self._page_cache:
                    page = self._page_cache[key]
                    try:
                        await page.close()
                        del self._page_cache[key]
                        log.info(f"🗑️ Closed and removed page: {key}")
                        return True
                    except Exception as e:
                        log.warning(f"Error closing page {key}: {e}")
                        del self._page_cache[key]  # Remove from cache anyway
                        return True
            
            log.warning(f"Page not found in cache: {url_or_domain}")
            return False
    
    async def cleanup_all(self) -> None:
        """Close all cached pages and disconnect browser."""
        async with self._cache_lock:
            log.info("🧹 Starting browser cleanup...")
            
            # Close all cached pages
            closed_count = 0
            for domain_key, page in list(self._page_cache.items()):
                try:
                    await page.close()
                    closed_count += 1
                except Exception as e:
                    log.warning(f"Error closing page {domain_key}: {e}")
            
            self._page_cache.clear()
            log.info(f"🗑️ Closed {closed_count} cached pages")
            
            # Disconnect from browser (but don't close Chrome itself)
            try:
                if self.browser:
                    await self.browser.close()
                    log.info("🔌 Disconnected from Chrome")
                
                if self.playwright:
                    await self.playwright.stop()
                    log.info("🎭 Stopped Playwright")
                    
            except Exception as e:
                log.warning(f"Error during browser cleanup: {e}")
            
            # Reset state
            self.browser = None
            self.context = None
            self.playwright = None
            self._is_connected = False
            
            log.info("✅ Browser cleanup completed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current browser manager status."""
        return {
            "connected": self._is_connected,
            "connection_time": self._connection_time.isoformat() if self._connection_time else None,
            "cached_pages_count": len(self._page_cache),
            "cached_domains": list(self._page_cache.keys()),
            "total_pages_created": self._total_pages_created,
            "max_cached_pages": MAX_CACHED_PAGES,
            "chrome_debug_port": self.chrome_debug_port
        }


# Global instance
_browser_manager = None


async def get_browser_manager() -> BrowserManager:
    """Get global browser manager instance."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


async def cleanup_global_browser() -> None:
    """Cleanup global browser manager."""
    global _browser_manager
    if _browser_manager:
        await _browser_manager.cleanup_all()
        log.info("🧹 Global browser cleanup completed")


def _cleanup_on_exit():
    """Synchronous cleanup for atexit registration."""
    global _browser_manager
    if _browser_manager:
        try:
            asyncio.run(cleanup_global_browser())
        except Exception as e:
            print(f"Error during browser cleanup on exit: {e}")


# Register cleanup function to run on exit
atexit.register(_cleanup_on_exit)


# Convenience functions for common operations
async def get_page_for_url(url: str, reuse_existing: bool = True) -> Page:
    """Convenience function to get page for URL."""
    manager = await get_browser_manager()
    return await manager.get_page(url, reuse_existing)


async def close_page_for_url(url: str) -> bool:
    """Convenience function to close page for URL."""
    manager = await get_browser_manager()
    return await manager.close_page(url)


async def get_browser_status() -> Dict[str, Any]:
    """Get current browser manager status."""
    manager = await get_browser_manager()
    return manager.get_status()


if __name__ == "__main__":
    # Inline smoke test to verify LRU eviction
    async def _smoke():
        log.info("🧪 BrowserManager LRU Smoke Test...")
        try:
            bm = await get_browser_manager()
            
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
            
            await cleanup_global_browser()
            log.info("✅ Smoke test passed")
            
        except Exception as e:
            log.error(f"❌ Smoke test failed: {e}")
            raise
    
    asyncio.run(_smoke())