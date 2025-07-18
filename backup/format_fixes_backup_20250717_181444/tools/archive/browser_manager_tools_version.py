"""
Browser Manager - Persistent browser and page management for Amazon FBA Agent System v3

Implements:
- 2 second headless probe, restart with headless=False if timeout
- get_persistent_page(supplier) returns same Page for all nodes  
- Max 2 Chrome tabs per supplier with LRU close policy
- Proper browser lifecycle management
"""

import asyncio
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from utils.path_manager import path_manager

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser instances and persistent pages for suppliers"""
    
    def __init__(self, max_tabs: int = 2):
        self.max_tabs = max_tabs
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # Track persistent pages per supplier (LRU cache)
        self.supplier_pages: OrderedDict[str, Page] = OrderedDict()
        
        # Track browser lifecycle
        self.browser_started_at: Optional[datetime] = None
        self.headless_mode: Optional[bool] = None
        
        # Configuration from system config
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load browser configuration from system config"""
        import json
        try:
            config_path = path_manager.get_config_path("system_config.json")
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            return {
                'headless_probe_seconds': config.get('system', {}).get('headless_probe_seconds', 2),
                'max_tabs': config.get('system', {}).get('max_tabs', 2),
                'reuse_browser': config.get('system', {}).get('reuse_browser', True),
                'debug_port': config.get('chrome', {}).get('debug_port', 9222),
                'default_headless': config.get('chrome', {}).get('headless', False)
            }
        except Exception as e:
            logger.warning(f"Failed to load browser config: {e}. Using defaults.")
            return {
                'headless_probe_seconds': 2,
                'max_tabs': 2,
                'reuse_browser': True,
                'debug_port': 9222,
                'default_headless': False
            }
    
    async def _probe_headless_capability(self) -> bool:
        """
        Probe if headless mode works within timeout
        Returns True if headless works, False if needs headed mode
        """
        logger.info(f"Probing headless capability with {self.config['headless_probe_seconds']}s timeout...")
        
        try:
            playwright = await async_playwright().start()
            
            # Try headless mode with timeout
            browser = await asyncio.wait_for(
                playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                ),
                timeout=self.config['headless_probe_seconds']
            )
            
            # Quick page test
            context = await browser.new_context()
            page = await context.new_page()
            await asyncio.wait_for(
                page.goto("about:blank"),
                timeout=self.config['headless_probe_seconds']
            )
            
            # Cleanup probe browser
            await browser.close()
            await playwright.stop()
            
            logger.info("✅ Headless mode probe successful")
            return True
            
        except asyncio.TimeoutError:
            logger.warning("⚠️ Headless mode probe timed out - switching to headed mode")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Headless mode probe failed: {e} - switching to headed mode")
            return False
    
    async def _ensure_browser(self) -> Browser:
        """Ensure browser is running with proper headless detection"""
        if self.browser and not self.browser.is_connected():
            logger.warning("Browser disconnected, will restart")
            self.browser = None
            self.context = None
            self.supplier_pages.clear()
        
        if self.browser is None:
            # Probe headless capability if not already determined
            if self.headless_mode is None:
                self.headless_mode = await self._probe_headless_capability()
                if not self.headless_mode:
                    logger.info("Using headed mode due to headless probe failure")
            
            # Start browser with determined headless mode
            playwright = await async_playwright().start()
            
            launch_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
            
            if not self.headless_mode:
                launch_args.extend([
                    '--start-maximized',
                    '--disable-extensions-except',
                    '--load-extension'
                ])
            
            self.browser = await playwright.chromium.launch(
                headless=self.headless_mode,
                args=launch_args,
                slow_mo=50 if not self.headless_mode else 0
            )
            
            # Create persistent context
            context_dir = path_manager.get_cache_path("browser_contexts", create_dirs=True)
            self.context = await self.browser.new_persistent_context(
                user_data_dir=str(context_dir),
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.browser_started_at = datetime.now()
            logger.info(f"✅ Browser started in {'headless' if self.headless_mode else 'headed'} mode")
        
        return self.browser
    
    async def get_persistent_page(self, supplier: str) -> Page:
        """
        Get or create persistent page for supplier
        Returns same Page instance for all calls with same supplier
        
        Args:
            supplier: Supplier domain identifier
            
        Returns:
            Page instance for the supplier
        """
        await self._ensure_browser()
        
        # Check if we already have a page for this supplier
        if supplier in self.supplier_pages:
            page = self.supplier_pages[supplier]
            
            # Move to end (most recently used)
            self.supplier_pages.move_to_end(supplier)
            
            # Verify page is still valid
            try:
                await page.evaluate("1 + 1")  # Simple JS test
                logger.debug(f"Reusing existing page for supplier: {supplier}")
                return page
            except Exception as e:
                logger.warning(f"Existing page for {supplier} is invalid: {e}")
                del self.supplier_pages[supplier]
        
        # Need to create new page - check tab limit
        if len(self.supplier_pages) >= self.max_tabs:
            # Close least recently used page
            oldest_supplier, oldest_page = self.supplier_pages.popitem(last=False)
            try:
                await oldest_page.close()
                logger.info(f"Closed LRU page for supplier: {oldest_supplier}")
            except Exception as e:
                logger.warning(f"Error closing LRU page for {oldest_supplier}: {e}")
        
        # Create new page for supplier
        try:
            page = await self.context.new_page()
            
            # Configure page settings
            await page.set_viewport_size({'width': 1920, 'height': 1080})
            await page.set_extra_http_headers({
                'Accept-Language': 'en-GB,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            # Store in LRU cache
            self.supplier_pages[supplier] = page
            
            logger.info(f"✅ Created new persistent page for supplier: {supplier} "
                       f"(total tabs: {len(self.supplier_pages)})")
            
            return page
            
        except Exception as e:
            logger.error(f"Failed to create page for supplier {supplier}: {e}")
            raise
    
    async def close_supplier_page(self, supplier: str) -> bool:
        """
        Close page for specific supplier
        
        Args:
            supplier: Supplier domain identifier
            
        Returns:
            True if page was closed, False if not found
        """
        if supplier in self.supplier_pages:
            page = self.supplier_pages.pop(supplier)
            try:
                await page.close()
                logger.info(f"Closed page for supplier: {supplier}")
                return True
            except Exception as e:
                logger.warning(f"Error closing page for {supplier}: {e}")
                return False
        return False
    
    async def get_browser_stats(self) -> dict:
        """Get browser usage statistics"""
        return {
            'browser_connected': self.browser is not None and self.browser.is_connected(),
            'headless_mode': self.headless_mode,
            'started_at': self.browser_started_at.isoformat() if self.browser_started_at else None,
            'active_suppliers': list(self.supplier_pages.keys()),
            'total_tabs': len(self.supplier_pages),
            'max_tabs': self.max_tabs,
            'config': self.config
        }
    
    async def cleanup(self):
        """Clean up all browser resources"""
        logger.info("Cleaning up browser manager...")
        
        # Close all supplier pages
        for supplier, page in self.supplier_pages.items():
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"Error closing page for {supplier}: {e}")
        
        self.supplier_pages.clear()
        
        # Close context and browser
        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")
            
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
        
        self.browser = None
        self.context = None
        self.browser_started_at = None
        
        logger.info("✅ Browser cleanup completed")


# Global browser manager instance
_browser_manager: Optional[BrowserManager] = None


async def get_browser_manager(max_tabs: int = None) -> BrowserManager:
    """Get or create global browser manager instance"""
    global _browser_manager
    
    if _browser_manager is None:
        # Load max_tabs from config if not provided
        if max_tabs is None:
            import json
            try:
                config_path = path_manager.get_config_path("system_config.json")
                with open(config_path, 'r') as f:
                    config = json.load(f)
                max_tabs = config.get('system', {}).get('max_tabs', 2)
            except Exception:
                max_tabs = 2
        
        _browser_manager = BrowserManager(max_tabs=max_tabs)
        logger.info(f"Created global browser manager with max_tabs={max_tabs}")
    
    return _browser_manager


async def cleanup_global_browser():
    """Cleanup global browser manager"""
    global _browser_manager
    if _browser_manager:
        await _browser_manager.cleanup()
        _browser_manager = None


# Convenience functions for common operations
async def get_supplier_page(supplier: str) -> Page:
    """Convenience function to get persistent page for supplier"""
    manager = await get_browser_manager()
    return await manager.get_persistent_page(supplier)


async def close_supplier_page(supplier: str) -> bool:
    """Convenience function to close supplier page"""
    manager = await get_browser_manager()
    return await manager.close_supplier_page(supplier)


async def get_browser_stats() -> dict:
    """Convenience function to get browser statistics"""
    global _browser_manager
    if _browser_manager:
        return await _browser_manager.get_browser_stats()
    return {'browser_connected': False, 'message': 'No browser manager initialized'}


# Example usage and testing
if __name__ == "__main__":
    async def test_browser_manager():
        """Test browser manager functionality"""
        logging.basicConfig(level=logging.INFO)
        
        try:
            # Test browser manager creation
            manager = await get_browser_manager(max_tabs=2)
            
            # Test persistent pages
            page1 = await manager.get_persistent_page("clearance-king.co.uk")
            page2 = await manager.get_persistent_page("poundwholesale.co.uk")
            
            # Verify same page returned
            page1_again = await manager.get_persistent_page("clearance-king.co.uk")
            assert page1 == page1_again, "Should return same page instance"
            
            # Test tab limit (should close LRU page)
            page3 = await manager.get_persistent_page("third-supplier.com")
            
            # Get stats
            stats = await manager.get_browser_stats()
            print(f"Browser stats: {stats}")
            
            # Test navigation
            await page1.goto("https://www.clearance-king.co.uk")
            await page2.goto("https://www.poundwholesale.co.uk")
            
            print("✅ All browser manager tests passed")
            
        except Exception as e:
            print(f"❌ Browser manager test failed: {e}")
            raise
        finally:
            await cleanup_global_browser()
    
    # Run test
    asyncio.run(test_browser_manager())