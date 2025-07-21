"""
Browser Automation Package
Provides Playwright-compatible API using Selenium backend
"""

from .playwright_adapter import (
    async_playwright,
    chromium_launch,
    PlaywrightBrowser,
    PlaywrightPage,
    PlaywrightLocator,
)
from .selenium_browser_manager import SeleniumBrowserManager
from .playwright_to_selenium_migrator import PlaywrightToSeleniumMigrator

__all__ = [
    'async_playwright',
    'chromium_launch', 
    'PlaywrightBrowser',
    'PlaywrightPage',
    'PlaywrightLocator',
    'SeleniumBrowserManager',
    'PlaywrightToSeleniumMigrator'
]
