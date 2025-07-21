# playwright_to_selenium_migrator.py
# Automatic migration helper

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class PlaywrightToSeleniumMigrator:
    """Convert Playwright calls to Selenium equivalents"""

    def __init__(self, selenium_driver):
        self.driver = selenium_driver

    def click(self, selector, timeout: int = 10) -> bool:
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            return True
        except Exception as e:
            print(f"Click failed for {selector}: {e}")
            return False

    def fill(self, selector, text: str, timeout: int = 10) -> bool:
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            print(f"Fill failed for {selector}: {e}")
            return False

    def text_content(self, selector, timeout: int = 10):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element.text
        except Exception as e:
            print(f"Text extraction failed for {selector}: {e}")
            return None
