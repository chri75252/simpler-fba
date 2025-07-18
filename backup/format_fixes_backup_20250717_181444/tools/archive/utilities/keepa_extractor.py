"""
Enhanced Amazon data extraction using Playwright connected to Chrome with debug port.
Extracts data from Amazon product pages, including extension data if available.
"""

from __future__ import annotations
import os
import logging
import time
import datetime
import re
import json
import asyncio
from typing import Dict, Any, List, Optional
from tools.amazon_playwright_extractor import AmazonExtractor

log = logging.getLogger(__name__)

class KeepaExtractor:
    """
    Extract data from Amazon product pages using Playwright connected to Chrome browser.
    Uses a Chrome instance with debug port 9222 and extracts data from both the page and extensions.
    """
    
    def __init__(self, chrome_debug_port: int = 9222):
        self.chrome_debug_port = chrome_debug_port
        self.extractor = AmazonExtractor(chrome_debug_port=chrome_debug_port)
        
    async def extract_data(self, asin: str) -> Dict[str, Any]:
        """
        Extract data from Amazon product page including extension data.
        
        Parameters
        ----------
        asin : str
            Amazon ASIN to analyze
            
        Returns
        -------
        Dict[str, Any]
            Extracted data including price, sales rank, extension data etc.
        """
        try:
            # Use the Playwright extractor
            log.info(f"Extracting data for ASIN {asin} using Playwright with debug port {self.chrome_debug_port}")
            data = await self.extractor.extract_data(asin)
            
            # If there's an error in the extraction, log it
            if "error" in data:
                log.error(f"Error extracting data for ASIN {asin}: {data['error']}")
            
            # Return the extracted data
            return data
            
        except Exception as exc:
            log.error(f"Failed to extract data for ASIN {asin}: {exc}")
            return {
                "asin": asin,
                "error": str(exc),
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    async def close(self):
        """Close the extractor connection."""
        try:
            await self.extractor.close()
        except Exception as e:
            log.error(f"Error closing extractor: {e}")
