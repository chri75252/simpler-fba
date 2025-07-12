#!/usr/bin/env python3
"""
PlaywrightBrowserManager - Robust browser pool management for LangGraph integration

Provides supplier-specific context isolation, crash recovery, and resource management
for Vision-Enhanced Playwright Tools. Uses pool pattern for resilience and scalability.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Set, AsyncGenerator
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.path_manager import get_log_path
except ImportError:
    # Fallback for testing
    def get_log_path(category: str, filename: str) -> str:
        log_dir = Path(f"logs/{category}")
        log_dir.mkdir(parents=True, exist_ok=True)
        return str(log_dir / filename)

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class BrowserContextInfo:
    """Information about a browser context"""
    context: BrowserContext
    supplier_id: str
    created_at: datetime
    last_used: datetime
    page_count: int = 0
    is_persistent: bool = False
    user_data_dir: Optional[Path] = None

@dataclass 
class BrowserPoolMetrics:
    """Metrics for browser pool monitoring"""
    total_contexts: int = 0
    active_contexts: int = 0
    idle_contexts: int = 0
    crashed_browsers: int = 0
    total_pages_created: int = 0
    context_reuse_count: int = 0
    avg_context_lifetime_seconds: float = 0.0

class PlaywrightBrowserManager:
    """
    Robust browser pool manager with supplier-specific isolation
    
    Features:
    - Browser pool for resilience (multiple browser instances)
    - Supplier-specific BrowserContext isolation
    - Automatic crash detection and recovery
    - Resource cleanup and lifecycle management
    - Performance monitoring and metrics
    """
    
    def __init__(
        self,
        max_browsers: int = 3,
        max_contexts_per_browser: int = 10,
        context_idle_timeout_minutes: int = 30,
        browser_launch_args: Optional[list] = None,
        headless: bool = True,
        enable_persistent_contexts: bool = True
    ):
        self.max_browsers = max_browsers
        self.max_contexts_per_browser = max_contexts_per_browser
        self.context_idle_timeout = timedelta(minutes=context_idle_timeout_minutes)
        self.headless = headless
        self.enable_persistent_contexts = enable_persistent_contexts
        
        # Browser launch arguments
        self.browser_launch_args = browser_launch_args or [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
            '--no-first-run',
            '--disable-default-apps'
        ]
        
        # Pool state
        self.playwright: Optional[Playwright] = None
        self.browsers: list[Browser] = []
        self.contexts: Dict[str, BrowserContextInfo] = {}  # supplier_id -> context_info
        self.browser_contexts: Dict[Browser, Set[str]] = {}  # browser -> supplier_ids
        
        # Metrics and monitoring
        self.metrics = BrowserPoolMetrics()
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_started = False
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup debug logging to standardized path"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = get_log_path("debug", f"browser_manager_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Browser manager debug logging initialized - writing to {debug_log_path}")
            
        except Exception as e:
            log.warning(f"Failed to setup debug logging: {e}")
    
    async def start(self):
        """Initialize the browser pool"""
        if self.is_started:
            log.warning("Browser manager already started")
            return
            
        try:
            log.info("Starting PlaywrightBrowserManager...")
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch initial browser instance
            await self._launch_browser()
            
            # Start background cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.is_started = True
            log.info(f"Browser manager started with {len(self.browsers)} browser(s)")
            
        except Exception as e:
            log.error(f"Failed to start browser manager: {e}")
            await self.cleanup()
            raise
    
    async def _test_headless_navigation(self, url: str) -> bool:
        """Test if headless mode works for navigation with 2-second timeout"""
        try:
            log.debug(f"Testing headless navigation to {url}")
            
            # Launch headless browser for quick test
            test_browser = await self.playwright.chromium.launch(
                headless=True,
                args=self.browser_launch_args
            )
            
            try:
                context = await test_browser.new_context()
                page = await context.new_page()
                
                # 2-second timeout for headless probe
                await page.goto(url, wait_until='domcontentloaded', timeout=2000)
                await page.wait_for_load_state('networkidle', timeout=2000)
                
                log.info("✅ Headless navigation successful")
                return True
                
            except Exception as e:
                log.warning(f"⚠️ Headless navigation failed: {e}")
                return False
                
            finally:
                await test_browser.close()
                
        except Exception as e:
            log.error(f"Headless test failed: {e}")
            return False

    async def _launch_browser(self) -> Browser:
        """Launch a new browser instance with intelligent headless/headed mode selection"""
        try:
            log.debug(f"Launching new browser instance (headless={self.headless})")
            
            browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=self.browser_launch_args
            )
            
            # Setup crash detection
            browser.on("disconnected", lambda: self._handle_browser_crash(browser))
            
            self.browsers.append(browser)
            self.browser_contexts[browser] = set()
            
            log.info(f"Browser launched successfully. Total browsers: {len(self.browsers)}")
            return browser
            
        except Exception as e:
            log.error(f"Failed to launch browser: {e}")
            raise
    
    def _handle_browser_crash(self, browser: Browser):
        """Handle browser crash and cleanup"""
        log.error(f"Browser crashed: {browser}")
        self.metrics.crashed_browsers += 1
        
        try:
            # Remove from browser list
            if browser in self.browsers:
                self.browsers.remove(browser)
            
            # Clean up contexts associated with this browser
            crashed_suppliers = self.browser_contexts.get(browser, set())
            for supplier_id in crashed_suppliers:
                if supplier_id in self.contexts:
                    log.warning(f"Cleaning up crashed context for supplier: {supplier_id}")
                    del self.contexts[supplier_id]
            
            # Remove from context mapping
            if browser in self.browser_contexts:
                del self.browser_contexts[browser]
                
        except Exception as e:
            log.error(f"Error during crash cleanup: {e}")
    
    async def get_context(self, supplier_id: str, persistent: bool = False) -> BrowserContext:
        """
        Get or create a browser context for the specified supplier
        
        Args:
            supplier_id: Unique identifier for the supplier
            persistent: Whether to use persistent context for login state
            
        Returns:
            BrowserContext isolated for this supplier
        """
        if not self.is_started:
            await self.start()
        
        # Check if we already have a context for this supplier
        if supplier_id in self.contexts:
            context_info = self.contexts[supplier_id]
            context_info.last_used = datetime.now()
            self.metrics.context_reuse_count += 1
            log.debug(f"Reusing existing context for supplier: {supplier_id}")
            return context_info.context
        
        # Create new context
        return await self._create_context(supplier_id, persistent)
    
    async def _create_context(self, supplier_id: str, persistent: bool = False) -> BrowserContext:
        """Create a new browser context for a supplier"""
        try:
            # Find browser with available capacity
            browser = await self._get_available_browser()
            
            # Create context
            if persistent and self.enable_persistent_contexts:
                # Create persistent context for login state preservation
                user_data_dir = Path(f"browser_contexts/{supplier_id}")
                user_data_dir.mkdir(parents=True, exist_ok=True)
                
                # Note: Playwright doesn't support user_data_dir parameter in new_context()
                # Persistent state is handled at browser launch level, not context level
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                log.debug(f"Created persistent context for supplier: {supplier_id}")
            else:
                # Create regular context
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                log.debug(f"Created regular context for supplier: {supplier_id}")
            
            # Store context info
            context_info = BrowserContextInfo(
                context=context,
                supplier_id=supplier_id,
                created_at=datetime.now(),
                last_used=datetime.now(),
                is_persistent=persistent,
                user_data_dir=user_data_dir if persistent else None
            )
            
            self.contexts[supplier_id] = context_info
            self.browser_contexts[browser].add(supplier_id)
            
            # Update metrics
            self.metrics.total_contexts += 1
            self.metrics.active_contexts += 1
            
            log.info(f"Created new context for supplier: {supplier_id} (persistent={persistent})")
            return context
            
        except Exception as e:
            log.error(f"Failed to create context for supplier {supplier_id}: {e}")
            raise
    
    async def _get_available_browser(self) -> Browser:
        """Get a browser with available context capacity"""
        # Check existing browsers for capacity
        for browser in self.browsers:
            if browser in self.browser_contexts:
                context_count = len(self.browser_contexts[browser])
                if context_count < self.max_contexts_per_browser:
                    return browser
        
        # Launch new browser if under limit
        if len(self.browsers) < self.max_browsers:
            return await self._launch_browser()
        
        # Use browser with least contexts (load balancing)
        return min(self.browsers, key=lambda b: len(self.browser_contexts.get(b, set())))
    
    async def get_page_with_intelligent_mode(self, supplier_id: str, url: str, persistent: bool = False) -> Optional[Page]:
        """Get a page with intelligent headless/headed mode selection based on URL accessibility"""
        try:
            # First, test if headless mode works for this URL
            if self.headless and url:
                headless_works = await self._test_headless_navigation(url)
                if not headless_works:
                    log.info(f"🔄 Switching to headed mode for {supplier_id} due to headless timeout")
                    # Temporarily switch to headed mode
                    original_headless = self.headless
                    self.headless = False
                    try:
                        page = await self.get_page(supplier_id, persistent)
                        return page
                    finally:
                        # Restore original setting
                        self.headless = original_headless
            
            # Use normal page creation if headless works or no URL provided
            return await self.get_page(supplier_id, persistent)
            
        except Exception as e:
            log.error(f"Failed to get page with intelligent mode for {supplier_id}: {e}")
            return None

    async def get_page(self, supplier_id: str, persistent: bool = False) -> Page:
        """
        Get a new page for the specified supplier
        
        Args:
            supplier_id: Unique identifier for the supplier
            persistent: Whether to use persistent context
            
        Returns:
            New Page instance within supplier's context
        """
        context = await self.get_context(supplier_id, persistent)
        page = await context.new_page()
        
        # Update metrics
        if supplier_id in self.contexts:
            self.contexts[supplier_id].page_count += 1
        self.metrics.total_pages_created += 1
        
        log.debug(f"Created new page for supplier: {supplier_id}")
        return page
    
    @asynccontextmanager
    async def managed_page(self, supplier_id: str, persistent: bool = False) -> AsyncGenerator[Page, None]:
        """
        Context manager for automatic page cleanup
        
        Usage:
            async with browser_manager.managed_page("amazon") as page:
                await page.goto("https://amazon.com")
                # page is automatically closed when exiting context
        """
        page = await self.get_page(supplier_id, persistent)
        try:
            yield page
        finally:
            try:
                await page.close()
                log.debug(f"Closed managed page for supplier: {supplier_id}")
            except Exception as e:
                log.warning(f"Error closing page for {supplier_id}: {e}")
    
    async def release_context(self, supplier_id: str, force: bool = False):
        """
        Release a context for a supplier
        
        Args:
            supplier_id: Supplier to release context for
            force: Force release even if context has open pages
        """
        if supplier_id not in self.contexts:
            log.debug(f"No context to release for supplier: {supplier_id}")
            return
        
        context_info = self.contexts[supplier_id]
        
        try:
            # Check for open pages
            pages = context_info.context.pages
            if pages and not force:
                log.warning(f"Context for {supplier_id} has {len(pages)} open pages - use force=True to close")
                return
            
            # Close all pages
            for page in pages:
                await page.close()
            
            # Close context
            await context_info.context.close()
            
            # Update browser mapping
            for browser, supplier_ids in self.browser_contexts.items():
                if supplier_id in supplier_ids:
                    supplier_ids.remove(supplier_id)
                    break
            
            # Remove from contexts
            del self.contexts[supplier_id]
            
            # Update metrics
            self.metrics.active_contexts -= 1
            
            log.info(f"Released context for supplier: {supplier_id}")
            
        except Exception as e:
            log.error(f"Error releasing context for {supplier_id}: {e}")
    
    async def _cleanup_loop(self):
        """Background task to clean up idle contexts"""
        while self.is_started:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_idle_contexts()
                self._update_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_idle_contexts(self):
        """Clean up contexts that have been idle too long"""
        current_time = datetime.now()
        idle_suppliers = []
        
        for supplier_id, context_info in self.contexts.items():
            if current_time - context_info.last_used > self.context_idle_timeout:
                # Don't cleanup persistent contexts by default
                if not context_info.is_persistent:
                    idle_suppliers.append(supplier_id)
        
        for supplier_id in idle_suppliers:
            log.info(f"Cleaning up idle context for supplier: {supplier_id}")
            await self.release_context(supplier_id, force=True)
    
    def _update_metrics(self):
        """Update performance metrics"""
        self.metrics.total_contexts = len(self.contexts)
        self.metrics.active_contexts = len([c for c in self.contexts.values() if c.context.pages])
        self.metrics.idle_contexts = self.metrics.total_contexts - self.metrics.active_contexts
        
        # Calculate average context lifetime
        if self.contexts:
            total_lifetime = sum(
                (datetime.now() - info.created_at).total_seconds()
                for info in self.contexts.values()
            )
            self.metrics.avg_context_lifetime_seconds = total_lifetime / len(self.contexts)
    
    async def get_metrics(self) -> BrowserPoolMetrics:
        """Get current pool metrics"""
        self._update_metrics()
        return self.metrics
    
    async def health_check(self) -> Dict[str, any]:
        """Perform health check on browser pool"""
        health_info = {
            "status": "healthy",
            "browsers_count": len(self.browsers),
            "active_contexts": len(self.contexts),
            "total_pages": sum(len(browser.contexts) for browser in self.browsers if browser.contexts),
            "crashed_browsers": self.metrics.crashed_browsers,
            "issues": []
        }
        
        # Check for issues
        if len(self.browsers) == 0:
            health_info["status"] = "critical"
            health_info["issues"].append("No browsers available")
        
        if self.metrics.crashed_browsers > 0:
            health_info["status"] = "degraded"
            health_info["issues"].append(f"{self.metrics.crashed_browsers} browser crashes detected")
        
        return health_info
    
    async def cleanup(self):
        """Clean up all resources"""
        log.info("Starting browser manager cleanup...")
        
        try:
            self.is_started = False
            
            # Cancel cleanup task
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Close all contexts
            for supplier_id in list(self.contexts.keys()):
                await self.release_context(supplier_id, force=True)
            
            # Close all browsers
            for browser in self.browsers:
                try:
                    await browser.close()
                except Exception as e:
                    log.warning(f"Error closing browser: {e}")
            
            # Stop Playwright
            if self.playwright:
                await self.playwright.stop()
            
            # Clear state
            self.browsers.clear()
            self.contexts.clear()
            self.browser_contexts.clear()
            
            log.info("Browser manager cleanup completed")
            
        except Exception as e:
            log.error(f"Error during cleanup: {e}")

# Global browser manager instance
_browser_manager: Optional[PlaywrightBrowserManager] = None

async def get_browser_manager() -> PlaywrightBrowserManager:
    """Get the global browser manager instance"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = PlaywrightBrowserManager()
        await _browser_manager.start()
    return _browser_manager

async def cleanup_browser_manager():
    """Cleanup the global browser manager"""
    global _browser_manager
    if _browser_manager:
        await _browser_manager.cleanup()
        _browser_manager = None

# Example usage and testing
async def main():
    """Test the browser manager"""
    manager = PlaywrightBrowserManager(max_browsers=1, headless=True)
    
    try:
        print("Starting browser manager...")
        await manager.start()
        
        print("Testing basic context creation...")
        # Test basic context creation
        context = await manager.get_context("test_supplier")
        print(f"Created context for test_supplier: {type(context)}")
        
        # Test page creation
        page = await manager.get_page("test_supplier")
        print(f"Created page: {type(page)}")
        await page.goto("https://httpbin.org/get")  # Simple test endpoint
        print(f"Page loaded: {page.url}")
        await page.close()
        
        # Check metrics
        metrics = await manager.get_metrics()
        print(f"Metrics: contexts={metrics.total_contexts}, pages={metrics.total_pages_created}")
        
        # Health check
        health = await manager.health_check()
        print(f"Health status: {health['status']}")
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())