"""
Browser Automation Package
Provides Playwright-compatible API using Selenium backend
"""

from .playwright_adapter import (
    async_playwright,
    chromium_launch,
    PlaywrightBrowser,
    PlaywrightPage,
    PlaywrightLocator
)

__all__ = [
    'async_playwright',
    'chromium_launch', 
    'PlaywrightBrowser',
    'PlaywrightPage',
    'PlaywrightLocator'
]
