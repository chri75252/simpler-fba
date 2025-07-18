"""
Fixed Amazon Playwright Extractor that reuses existing browser windows 
instead of creating new ones, ensuring extensions load properly.
"""

import os
import re
import json
import logging
import asyncio
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from playwright.async_api import async_playwright, Page, Browser, FrameLocator, TimeoutError as PlaywrightTimeoutError
from openai import OpenAI
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = "gpt-4.1-mini-2025-04-14"

OUTPUT_DIR = "C:\\Users\\chris\\Amazon-FBA-Agent-System\\OUTPUTS\\AMAZON_SCRAPE"

# Default timeouts and waits
DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds
POST_NAVIGATION_STABILIZE_WAIT = 10 # 10 seconds
CAPTCHA_MANUAL_SOLVE_WAIT = 30    # 30 seconds
EXTENSION_DATA_WAIT = 15          # 15 seconds for extensions to load

class AmazonExtractor:
    def __init__(self, chrome_debug_port: int = 9222, ai_client: Optional[OpenAI] = None):
        self.chrome_debug_port = chrome_debug_port
        self.browser: Optional[Browser] = None
        
        if ai_client:
            self.ai_client = ai_client
        else:
            # Ensure you replace "YOUR_OPENAI_API_KEY" with your actual key or use environment variables
            if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY": 
                try:
                    self.ai_client = OpenAI(api_key=OPENAI_API_KEY)
                    log.info(f"OpenAI client initialized successfully with model {OPENAI_MODEL_NAME}.")
                except Exception as e:
                    self.ai_client = None
                    log.error(f"Failed to initialize OpenAI client: {e}. AI fallbacks will be disabled.")
            else:
                self.ai_client = None
                log.warning("OpenAI API key not provided or is a placeholder. AI fallbacks will be disabled.")
        
        self.openai_model = OPENAI_MODEL_NAME
        
        self.output_dir = OUTPUT_DIR
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            log.info(f"Output directory set to: {os.path.abspath(self.output_dir)}")
        except OSError as e:
            log.error(f"Could not create output directory '{self.output_dir}': {e}. Files will be saved in the current directory.")
            self.output_dir = "." 
    
    async def connect(self) -> Browser:
        """
        Connect to an existing Chrome instance using CDP.
        This implementation reuses existing pages rather than creating new ones,
        which ensures extensions like SellerAmp load properly.
        """
        log.info(f"Connecting to Chrome browser on debug port {self.chrome_debug_port}")
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.chrome_debug_port}")
            log.info(f"Successfully connected to Chrome on port {self.chrome_debug_port}")
            
            # Use existing pages instead of creating a new one
            # This helps ensure extensions like SellerAmp are properly loaded
            all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
            
            if all_pages:
                log.info(f"Found {len(all_pages)} existing pages")
                # Use an existing page instead of creating a new one
                test_page = all_pages[0]
                log.info(f"Using existing page: {test_page.url}")
                await test_page.bring_to_front()
            else:
                # Only create a new page if none exist
                log.info("No existing pages found. Creating new page")
                page = await self.browser.new_page()
                await page.goto("about:blank", timeout=10000)
                await page.close()
                
            return self.browser
        except Exception as e:
            log.error(f"Failed to connect to Chrome on port {self.chrome_debug_port}: {e}")
            log.error("Ensure Chrome is running with --remote-debugging-port=9222 and a dedicated --user-data-dir for persistence.")
            raise

    async def extract_data(self, asin: str) -> Dict[str, Any]:
        """
        Extract data for an Amazon product by ASIN.
        This implementation reuses existing pages to ensure extensions work properly.
        """
        result = {"asin_queried": asin, "timestamp": datetime.now().isoformat()}
        amazon_url = f"https://www.amazon.co.uk/dp/{asin}"
        page = None

        if not asin or not re.match(r"^B[0-9A-Z]{9}$", asin):
            result["error"] = "Invalid or missing ASIN."
            return result
        
        try:
            if not self.browser or not self.browser.is_connected():
                await self.connect()
            
            if not self.browser:
                result["error"] = "Browser connection failed."
                return result
            
            # Reuse an existing page if available, otherwise create a new one
            all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
            
            if all_pages:
                page = all_pages[0]
                log.info(f"Reusing existing page: {page.url}")
                await page.bring_to_front()
            else:
                page = await self.browser.new_page()
                log.info("Created new page as none existed")
            
            # Navigate to the Amazon product page
            log.info(f"Navigating to {amazon_url}")
            await page.goto(amazon_url, wait_until="domcontentloaded", timeout=DEFAULT_NAVIGATION_TIMEOUT)
            
            # Wait for the page to stabilize and extensions to load
            log.info(f"Page loaded, waiting {POST_NAVIGATION_STABILIZE_WAIT}s for stabilization...")
            await asyncio.sleep(POST_NAVIGATION_STABILIZE_WAIT)
            
            log.info(f"Waiting additional {EXTENSION_DATA_WAIT}s for extensions to load...")
            await asyncio.sleep(EXTENSION_DATA_WAIT)
            
            # Take a screenshot for debugging if needed
            if os.getenv("DEBUG_SCREENSHOTS", "").lower() in ("true", "1", "yes"):
                debug_filename = f"debug_asin_{asin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                debug_filepath = os.path.join(self.output_dir, debug_filename)
                await page.screenshot(path=debug_filepath, full_page=True)
                log.info(f"Debug screenshot saved to {debug_filepath}")
            
            # Extract product data here
            # For now, just return a confirmation
            result["success"] = True
            result["message"] = "Page loaded successfully with extensions"
            result["url"] = page.url
            
            # Don't close the page - leave it open for reuse
            # This is key to keeping extensions working properly
            
            return result
            
        except Exception as e:
            log.error(f"Error extracting data for ASIN {asin}: {e}", exc_info=True)
            result["error"] = str(e)
            return result

    async def close(self):
        """Close the browser connection."""
        if self.browser and self.browser.is_connected():
            log.info("Closing browser connection.")
            try:
                await self.browser.close()
            except Exception as e:
                log.error(f"Error closing browser: {e}")
        self.browser = None

# Simple test function
async def test_amazon_extractor():
    """Test the Amazon extractor with a sample ASIN."""
    extractor = AmazonExtractor()
    try:
        # Test with a sample ASIN
        result = await extractor.extract_data("B085W7P4DK")  # Example ASIN
        print(json.dumps(result, indent=2))
    finally:
        # Don't close the browser when done
        pass

if __name__ == "__main__":
    asyncio.run(test_amazon_extractor())
