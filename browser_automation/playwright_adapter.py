"""
Playwright-to-Selenium Adapter
Provides Playwright-like API using Selenium backend
"""

import time
import json
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc

class PlaywrightPage:
    """Selenium-based implementation of Playwright Page API"""
    
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
    
    def goto(self, url: str, wait_until: str = "load", timeout: int = 30):
        """Navigate to URL"""
        self.driver.get(url)
        if wait_until == "networkidle":
            time.sleep(2)  # Simple network idle simulation
        return self
    
    def locator(self, selector: str):
        """Return a locator object"""
        return PlaywrightLocator(self.driver, selector)

    def query_selector_all(self, selector: str) -> List[Any]:
        """Return all elements matching selector"""
        return self.driver.find_elements(By.CSS_SELECTOR, selector)

    def set_content(self, html: str):
        """Set page content to provided HTML"""
        self.driver.execute_script(
            "document.open(); document.write(arguments[0]); document.close();",
            html,
        )
        return self

    def wait_for_load_state(self, state: str = "load", timeout: int = 30):
        """Simplified load state wait"""
        time.sleep(2 if state == "networkidle" else 1)
        return self
    
    def fill(self, selector: str, value: str):
        """Fill input field"""
        element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        element.clear()
        element.send_keys(value)
        return self
    
    def click(self, selector: str):
        """Click element"""
        element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        element.click()
        return self
    
    def wait_for_selector(self, selector: str, timeout: int = 30):
        """Wait for element to appear"""
        self.wait = WebDriverWait(self.driver, timeout)
        return self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    
    def content(self) -> str:
        """Get page content"""
        return self.driver.page_source
    
    def title(self) -> str:
        """Get page title"""
        return self.driver.title
    
    def url(self) -> str:
        """Get current URL"""
        return self.driver.current_url
    
    def screenshot(self, path: str = None) -> bytes:
        """Take screenshot"""
        if path:
            self.driver.save_screenshot(path)
        return self.driver.get_screenshot_as_png()
    
    def evaluate(self, script: str) -> Any:
        """Execute JavaScript"""
        return self.driver.execute_script(script)
    
    def close(self):
        """Close page"""
        self.driver.quit()

class PlaywrightLocator:
    """Selenium-based implementation of Playwright Locator API"""
    
    def __init__(self, driver, selector: str):
        self.driver = driver
        self.selector = selector
        self.wait = WebDriverWait(driver, 10)
    
    def click(self, timeout: int = 30):
        """Click the element"""
        element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.selector)))
        element.click()
        return self
    
    def fill(self, value: str):
        """Fill the element"""
        element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selector)))
        element.clear()
        element.send_keys(value)
        return self
    
    def text_content(self) -> str:
        """Get text content"""
        element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selector)))
        return element.text
    
    def inner_text(self) -> str:
        """Get inner text"""
        return self.text_content()
    
    def get_attribute(self, name: str) -> str:
        """Get attribute value"""
        element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selector)))
        return element.get_attribute(name)
    
    def is_visible(self) -> bool:
        """Check if element is visible"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, self.selector)
            return element.is_displayed()
        except NoSuchElementException:
            return False
    
    def wait_for(self, timeout: int = 30):
        """Wait for element"""
        self.wait = WebDriverWait(self.driver, timeout)
        return self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selector)))

class PlaywrightContext:
    """Simplified browser context"""

    def __init__(self, browser: "PlaywrightBrowser"):
        self.browser = browser

    def new_page(self) -> PlaywrightPage:
        return self.browser.new_page()

    def close(self):
        pass

class PlaywrightBrowser:
    """Selenium-based implementation of Playwright Browser API"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

    def new_context(self, user_agent: Optional[str] = None):
        """Create a new browser context"""
        if not self.driver:
            self.new_page()
        if user_agent:
            try:
                self.driver.execute_cdp_cmd(
                    "Network.setUserAgentOverride", {"userAgent": user_agent}
                )
            except Exception:
                pass
        return PlaywrightContext(self)
    
    def new_page(self) -> PlaywrightPage:
        """Create new page"""
        if not self.driver:
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Use undetected-chromedriver for better stealth
            self.driver = uc.Chrome(options=options)
        
        return PlaywrightPage(self.driver)
    
    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()

# Main API functions to mimic Playwright
def chromium_launch(headless: bool = True, **kwargs) -> PlaywrightBrowser:
    """Launch Chromium browser"""
    return PlaywrightBrowser(headless=headless)

# Context manager for easy usage
class async_playwright:
    """Context manager for Playwright-like usage"""
    
    def __init__(self):
        self.browser = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
    
    @property
    def chromium(self):
        """Chromium browser launcher"""
        class ChromiumLauncher:
            def __init__(self, outer):
                self.outer = outer

            def launch(self, headless: bool = True, **kwargs):
                browser = PlaywrightBrowser(headless=headless)
                self.outer.browser = browser
                return browser

        return ChromiumLauncher(self)

