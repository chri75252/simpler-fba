"""
Amazon Tools for matching and validation.
"""

import os
import logging
import re
from typing import Dict, Any, List, Optional, Union, Tuple

# Import the necessary scraping tools for different providers
from tools.firecrawl import FirecrawlScraper
from tools.hyperbrowser import HyperbrowserScraper
from tools.browserbase import BrowserbaseScraper

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger(__name__)

# Default Amazon marketplace
DEFAULT_MARKETPLACE = os.getenv("AMAZON_MARKETPLACE_ID", "2")  # UK=2, US=1

class AmazonTools:
    """
    Tools for interacting with Amazon, including product search, detail extraction,
    and validation.
    """
    
    def __init__(self):
        """Initialize Amazon tools with available API clients."""
        # Initialize available scrapers based on configuration
        self.scrapers = {}
        
        # Firecrawl
        if os.getenv("FIRECRAWL_API_KEY"):
            self.scrapers["firecrawl"] = FirecrawlScraper()
        
        # Hyperbrowser
        if os.getenv("HYPERBROWSER_API_KEY"):
            self.scrapers["hyperbrowser"] = HyperbrowserScraper()
        
        # Browserbase
        if os.getenv("BROWSERBASE_API_KEY") and os.getenv("BROWSERBASE_PROJECT_ID"):
            self.scrapers["browserbase"] = BrowserbaseScraper()
        
        if not self.scrapers:
            log.warning("No scraper APIs configured. Amazon tools will have limited functionality.")
    
    def search_by_upc(self, upc: str, marketplace: str = DEFAULT_MARKETPLACE) -> Dict[str, Any]:
        """
        Search for a product on Amazon by UPC/EAN.
        
        Parameters
        ----------
        upc : str
            UPC or EAN code to search for
        marketplace : str
            Amazon marketplace ID (UK=2, US=1)
            
        Returns
        -------
        Dict[str, Any]
            Search results with product details
        """
        search_url = f"https://www.amazon.co.uk/s?k={upc}"
        
        # Try each available scraper in order
        for name, scraper in self.scrapers.items():
            log.info(f"Searching Amazon for UPC {upc} using {name}")
            
            try:
                if name == "firecrawl":
                    # Use Firecrawl's search capability
                    result = scraper.scrape_page(
                        search_url,
                        formats=["html"],
                        waitFor=5000
                    )
                elif name == "hyperbrowser":
                    # Use Hyperbrowser
                    result = scraper.scrape_page(
                        search_url,
                        output_format="html"
                    )
                elif name == "browserbase":
                    # Use Browserbase
                    result = scraper.scrape_page(
                        search_url,
                        waitForSelector=".s-result-item"
                    )
                
                # Check for success and extract product details
                if result and not result.get("error"):
                    # Extract product info from HTML - implementation varies by scraper
                    if name == "firecrawl" and "html" in result:
                        html = result["html"]
                        product_data = self._extract_product_data_from_html(html)
                        if product_data:
                            product_data["source"] = f"{name}_search"
                            return product_data
                    
                    elif name == "hyperbrowser" and "content" in result:
                        html = result["content"]
                        product_data = self._extract_product_data_from_html(html)
                        if product_data:
                            product_data["source"] = f"{name}_search"
                            return product_data
                    
                    elif name == "browserbase" and "html" in result:
                        html = result["html"]
                        product_data = self._extract_product_data_from_html(html)
                        if product_data:
                            product_data["source"] = f"{name}_search"
                            return product_data
                
                log.warning(f"{name} search returned invalid or empty result")
                
            except Exception as exc:
                log.error(f"Error searching Amazon with {name}: {exc}")
        
        # If all scrapers fail
        return {"error": "Failed to search Amazon with all available methods", "upc": upc}
    
    def get_product_details(self, asin: str, marketplace: str = DEFAULT_MARKETPLACE) -> Dict[str, Any]:
        """
        Get detailed product information for an Amazon ASIN.
        
        Parameters
        ----------
        asin : str
            Amazon ASIN to look up
        marketplace : str
            Amazon marketplace ID (UK=2, US=1)
            
        Returns
        -------
        Dict[str, Any]
            Detailed product information
        """
        product_url = f"https://www.amazon.co.uk/dp/{asin}"
        
        # Try each available scraper in order
        for name, scraper in self.scrapers.items():
            log.info(f"Getting product details for ASIN {asin} using {name}")
            
            try:
                if name == "firecrawl":
                    # Use Firecrawl
                    result = scraper.scrape_page(
                        product_url,
                        formats=["html"],
                        waitFor=5000
                    )
                elif name == "hyperbrowser":
                    # Use Hyperbrowser
                    result = scraper.scrape_page(
                        product_url,
                        output_format="html"
                    )
                elif name == "browserbase":
                    # Use Browserbase
                    result = scraper.scrape_page(
                        product_url,
                        waitForSelector="#productTitle"
                    )
                
                # Check for success and extract product details
                if result and not result.get("error"):
                    # Extract detailed product info from HTML
                    if name == "firecrawl" and "html" in result:
                        html = result["html"]
                        product_data = self._extract_detailed_product_data(html, asin)
                        if product_data:
                            product_data["source"] = f"{name}_details"
                            return product_data
                    
                    elif name == "hyperbrowser" and "content" in result:
                        html = result["content"]
                        product_data = self._extract_detailed_product_data(html, asin)
                        if product_data:
                            product_data["source"] = f"{name}_details"
                            return product_data
                    
                    elif name == "browserbase" and "html" in result:
                        html = result["html"]
                        product_data = self._extract_detailed_product_data(html, asin)
                        if product_data:
                            product_data["source"] = f"{name}_details"
                            return product_data
                
                log.warning(f"{name} product details returned invalid or empty result")
                
            except Exception as exc:
                log.error(f"Error getting product details with {name}: {exc}")
        
        # If all scrapers fail
        return {"error": "Failed to get product details with all available methods", "asin": asin}
    
    def validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and score the match between a supplier product and Amazon product.
        
        Parameters
        ----------
        supplier_product : Dict[str, Any]
            Supplier product data
        amazon_product : Dict[str, Any]
            Amazon product data
            
        Returns
        -------
        Dict[str, Any]
            Validation results with match score and details
        """
        validation = {"match_score": 0.0, "warnings": [], "matches": []}
        
        # 1. Check UPC/EAN match if available
        if supplier_product.get("upc") and amazon_product.get("upc"):
            if supplier_product["upc"] == amazon_product["upc"]:
                validation["match_score"] += 0.5
                validation["matches"].append("UPC code match")
            else:
                validation["warnings"].append("UPC code mismatch")
        
        # 2. Check brand match if available
        if supplier_product.get("brand") and amazon_product.get("brand"):
            if supplier_product["brand"].lower() == amazon_product["brand"].lower():
                validation["match_score"] += 0.2
                validation["matches"].append("Brand match")
            else:
                validation["warnings"].append("Brand mismatch")
        
        # 3. Check title similarity
        if supplier_product.get("title") and amazon_product.get("title"):
            title_similarity = self._calculate_title_similarity(
                supplier_product["title"],
                amazon_product["title"]
            )
            validation["title_similarity"] = title_similarity
            
            if title_similarity > 0.8:
                validation["match_score"] += 0.3
                validation["matches"].append("Strong title match")
            elif title_similarity > 0.5:
                validation["match_score"] += 0.15
                validation["matches"].append("Partial title match")
            else:
                validation["warnings"].append("Low title similarity")
        
        # 4. Finalize the validation
        if validation["match_score"] > 0.7:
            validation["match_quality"] = "high"
        elif validation["match_score"] > 0.4:
            validation["match_quality"] = "medium"
        else:
            validation["match_quality"] = "low"
            
        return validation
    
    def _extract_product_data_from_html(self, html: str) -> Dict[str, Any]:
        """
        Extract basic product data from Amazon search results HTML.
        
        Parameters
        ----------
        html : str
            HTML content of Amazon search results page
            
        Returns
        -------
        Dict[str, Any]
            Extracted product data including ASIN, title, price, and image URL
        """
        # Basic extraction pattern - would need more robust parsing in production
        asin_pattern = r'data-asin="([A-Z0-9]{10})"'
        title_pattern = r'<span class="a-size-medium a-color-base a-text-normal">(.*?)</span>'
        price_pattern = r'<span class="a-price-whole">(\d+)</span><span class="a-price-fraction">(\d+)</span>'
        image_pattern = r'<img.*?src="(https://[^"]+)".*?>'
        
        # Extract data using regex patterns
        asin_match = re.search(asin_pattern, html)
        title_match = re.search(title_pattern, html)
        price_match = re.search(price_pattern, html)
        image_match = re.search(image_pattern, html)
        
        # Build product data dictionary
        product_data = {}
        
        if asin_match:
            product_data["asin"] = asin_match.group(1)
        
        if title_match:
            product_data["title"] = title_match.group(1)
        
        if price_match:
            product_data["price"] = float(f"{price_match.group(1)}.{price_match.group(2)}")
        
        if image_match:
            product_data["image_url"] = image_match.group(1)
        
        # Only return if we have at least an ASIN
        if "asin" in product_data:
            product_data["url"] = f"https://www.amazon.co.uk/dp/{product_data['asin']}"
            return product_data
        
        return {}
    
    def _extract_detailed_product_data(self, html: str, asin: str) -> Dict[str, Any]:
        """
        Extract detailed product data from Amazon product page HTML.
        
        Parameters
        ----------
        html : str
            HTML content of Amazon product page
        asin : str
            Amazon ASIN
            
        Returns
        -------
        Dict[str, Any]
            Detailed product data
        """
        # More comprehensive extraction patterns for product details
        title_pattern = r'<span id="productTitle".*?>(.*?)</span>'
        price_pattern = r'<span class="a-price-whole">(\d+)</span><span class="a-price-fraction">(\d+)</span>'
        brand_pattern = r'<a id="bylineInfo".*?>(.*?)</a>'
        upc_pattern = r'<th.*?>UPC</th>\s*<td.*?>(.*?)</td>'
        ean_pattern = r'<th.*?>EAN</th>\s*<td.*?>(.*?)</td>'
        features_pattern = r'<div id="feature-bullets".*?<ul.*?>(.*?)</ul>'
        rating_pattern = r'<span class="a-icon-alt">(\d+\.\d+) out of 5 stars</span>'
        
        # Extract data using regex patterns
        title_match = re.search(title_pattern, html, re.DOTALL)
        price_match = re.search(price_pattern, html)
        brand_match = re.search(brand_pattern, html)
        upc_match = re.search(upc_pattern, html)
        ean_match = re.search(ean_pattern, html)
        features_match = re.search(features_pattern, html, re.DOTALL)
        rating_match = re.search(rating_pattern, html)
        
        # Build detailed product data
        product_data = {"asin": asin}
        
        if title_match:
            product_data["title"] = title_match.group(1).strip()
        
        if price_match:
            product_data["price"] = float(f"{price_match.group(1)}.{price_match.group(2)}")
        
        if brand_match:
            product_data["brand"] = brand_match.group(1).strip()
        
        if upc_match:
            product_data["upc"] = upc_match.group(1).strip()
        
        if ean_match:
            product_data["ean"] = ean_match.group(1).strip()
            # If no UPC found, use EAN as UPC (they're often interchangeable)
            if "upc" not in product_data:
                product_data["upc"] = product_data["ean"]
        
        if features_match:
            # Extract features from bullet points
            features_html = features_match.group(1)
            feature_items = re.findall(r'<li.*?><span.*?>(.*?)</span></li>', features_html, re.DOTALL)
            if feature_items:
                product_data["features"] = [item.strip() for item in feature_items]
        
        if rating_match:
            product_data["rating"] = float(rating_match.group(1))
        
        # Add product URL
        product_data["url"] = f"https://www.amazon.co.uk/dp/{asin}"
        
        return product_data
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity score between two product titles.
        
        Parameters
        ----------
        title1 : str
            First product title
        title2 : str
            Second product title
            
        Returns
        -------
        float
            Similarity score between 0.0 and 1.0
        """
        # Normalize titles
        title1 = title1.lower()
        title2 = title2.lower()
        
        # Remove common words and punctuation
        for word in ["the", "a", "an", "and", "or", "for", "with", "in", "of", "at", "by", "from"]:
            title1 = title1.replace(f" {word} ", " ")
            title2 = title2.replace(f" {word} ", " ")
        
        for char in ",.;:!?\"'()[]{}-":
            title1 = title1.replace(char, "")
            title2 = title2.replace(char, "")
        
        # Split into words
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
