# selenium_browser_manager.py
# Place in: tools/ directory (replaces BrowserManager functionality)
# Replacement for Playwright functionality

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutError, NoSuchElementException, WebDriverException
import undetected_chromedriver as uc

class SeleniumBrowserManager:
    """Enhanced Selenium browser manager for Codex environment"""
    
    def __init__(self, headless=True, stealth_mode=True):
        self.driver = None
        self.headless = headless
        self.stealth_mode = stealth_mode
        self.log = logging.getLogger(__name__)
        
    def launch_browser(self, cdp_port=None):
        """Launch Chrome browser with optimal settings for Codex"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless=new')  # Use new headless mode
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-plugins')
                chrome_options.add_argument('--disable-images')  # Speed optimization
                
            if cdp_port:
                chrome_options.add_argument(f'--remote-debugging-port={cdp_port}')
            
            # Anti-detection measures
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
            
            # Performance optimizations for Codex
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--max_old_space_size=4096')
            chrome_options.add_argument('--disable-background-timer-throttling')
            
            if self.stealth_mode:
                # Use undetected-chromedriver for better stealth
                self.driver = uc.Chrome(options=chrome_options, version_main=None)
            else:
                try:
                    service = Service('/usr/local/bin/chromedriver')
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except WebDriverException:
                    # Fallback to webdriver-manager
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute stealth scripts
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
            })
            
            self.log.info("✅ Selenium browser launched successfully")
            return True
            
        except Exception as e:
            self.log.error(f"🚨 Browser launch failed: {e}")
            return False
    
    async def get_page(self, url=None, timeout=30):
        """Navigate to page with error handling (async compatible)"""
        if url:
            return self.navigate_to(url, timeout)
        return self  # Return self for chaining like Playwright
    
    def navigate_to(self, url, timeout=30):
        """Navigate to page with error handling"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.log.info(f"✅ Successfully navigated to: {url}")
            return True
        except TimeoutError:
            self.log.warning(f"⏰ Page load timeout for: {url}")
            return False
        except Exception as e:
            self.log.error(f"🚨 Navigation error: {e}")
            return False
    
    def click(self, selector, timeout=10):
        """Click element by CSS selector"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            return True
        except Exception as e:
            self.log.warning(f"Click failed for {selector}: {e}")
            return False
    
    def fill(self, selector, text, timeout=10):
        """Fill input field with text"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            self.log.warning(f"Fill failed for {selector}: {e}")
            return False
    
    def text_content(self, selector, timeout=10):
        """Get text content of element"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element.text
        except Exception as e:
            self.log.warning(f"Text extraction failed for {selector}: {e}")
            return None
    
    def get_attribute(self, selector, attribute, timeout=10):
        """Get attribute value of element"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element.get_attribute(attribute)
        except Exception as e:
            self.log.warning(f"Attribute extraction failed for {selector}: {e}")
            return None
    
    def wait_for_selector(self, selector, timeout=10):
        """Wait for element to be present"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutError:
            return False
    
    def close(self):
        """Clean shutdown"""
        if self.driver:
            try:
                self.driver.quit()
                self.log.info("🔄 Browser closed successfully")
            except Exception as e:
                self.log.warning(f"Browser close error: {e}")

# Singleton pattern like your original BrowserManager
class BrowserManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SeleniumBrowserManager()
        return cls._instance