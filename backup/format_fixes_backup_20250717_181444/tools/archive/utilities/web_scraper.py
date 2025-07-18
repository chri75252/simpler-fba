"""
Web scraper tools for the FBA-Agent System.
This module provides compatibility with the old BaseTool interface
by wrapping the new functional API.
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Any, Type, TypeVar, Union

from langchain.tools import BaseTool
from pydantic import Field

from tools.web_scraper_impl import extract_product_listings, extract_product_details

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class WebScraperTool(BaseTool):
    """Base class for web-scraping tools."""
    # Pydantic v2: type-annotate *all* fields that override parents
    name: str = Field(default="web_scraper", description="Tool name")
    description: str = Field(
        default="Scrapes information from a web page",
        description="What the tool does",
    )
    
    def _run(self, *args: Any, **kwargs: Any) -> Dict:
        """Implementation should be provided by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")
    
    async def _arun(self, *args: Any, **kwargs: Any) -> Dict:
        """Default async implementation just calls the sync version."""
        return self._run(*args, **kwargs)


class ProductListingScraper(WebScraperTool):
    """Scrapes product listings from a category page."""
    name: str = Field(default="product_listing_scraper")
    description: str = Field(default="Scrapes product listings from a category page")
    
    def _run(self, url: str, pagination: bool = True, max_pages: int = 5) -> List[Dict]:
        """Scrape product listings from a supplier category page."""
        return extract_product_listings(url, pagination, max_pages)


class ProductDetailScraper(WebScraperTool):
    """Scrapes detailed product information from a product page."""
    name: str = Field(default="product_detail_scraper")
    description: str = Field(default="Scrapes detailed product information from a product page")
    
    def _run(self, url: str) -> Dict:
        """Scrape detailed product information from a product page."""
        return extract_product_details(url)
