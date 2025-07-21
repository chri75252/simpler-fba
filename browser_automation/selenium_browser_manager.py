# selenium_browser_manager.py
# Replacement for Playwright functionality

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

class SeleniumBrowserManager:
    """Enhanced Selenium browser manager for Codex environment"""

    def __init__(self, headless: bool = True, stealth_mode: bool = True):
        self.driver = None
        self.headless = headless
        self.stealth_mode = stealth_mode

    def launch_browser(self) -> bool:
        """Launch Chrome browser with optimal settings for Codex"""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--remote-debugging-port=9222')

            # Anti-detection measures
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            if self.stealth_mode:
                # Use undetected-chromedriver for better stealth
                self.driver = uc.Chrome(options=chrome_options)
            else:
                service = Service('/usr/local/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Execute stealth scripts
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            return True

        except Exception as e:
            print(f"🚨 Browser launch failed: {e}")
            return False

    async def get_page(self, url: str, timeout: int = 30) -> bool:
        """Navigate to page with error handling"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return True
        except TimeoutException:
            print(f"⏰ Page load timeout for: {url}")
            return False
        except Exception as e:
            print(f"🚨 Navigation error: {e}")
            return False

    def close(self) -> None:
        """Clean shutdown"""
        if self.driver:
            self.driver.quit()
