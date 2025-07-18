"""
Updated web scraper implementation that integrates Oxylabs API.
"""

import os
import logging
import requests
import urllib.parse
import tldextract
from typing import Dict, Any, List, Optional, Union, Callable
from bs4 import BeautifulSoup

# Import specific provider implementations
from tools.firecrawl import FirecrawlScraper
from tools.hyperbrowser import HyperbrowserScraper
from tools.browserbase import BrowserbaseScraper
from tools.oxylabs import OxylabsScraper
from tools.scraperapi import ScraperAPIScraper

# Import utility for loading domain-specific CSS selectors
from config.suppliers_loader import get_selectors_for_domain

log = logging.getLogger(__name__)

class WebScraperImpl:
    """
    Web scraper that uses API-based tools instead of direct browser automation.
    
    This implementation attempts to use the available API-based tools in order
    of preference with fallbacks between them.
    """
    
    def __init__(self):
        """Initialize the web scraper with available API clients."""
        # Initialize available scrapers based on configuration
        self.scrapers = {}
        
        # Oxylabs - prioritize for Amazon-specific scraping
        if os.getenv("OXYLABS_USERNAME") and os.getenv("OXYLABS_PASSWORD"):
            self.scrapers["oxylabs"] = OxylabsScraper()
        
        # Firecrawl
        if os.getenv("FIRECRAWL_API_KEY"):
            self.scrapers["firecrawl"] = FirecrawlScraper()
        
        # Hyperbrowser
        if os.getenv("HYPERBROWSER_API_KEY"):
            self.scrapers["hyperbrowser"] = HyperbrowserScraper()
        
        # Browserbase
        if os.getenv("BROWSERBASE_API_KEY") and os.getenv("BROWSERBASE_PROJECT_ID"):
            self.scrapers["browserbase"] = BrowserbaseScraper()
        
        # ScraperAPI - Third tier fallback
        if os.getenv("SCRAPERAPI_API_KEY"):
            self.scrapers["scraperapi"] = ScraperAPIScraper()
        
        if not self.scrapers:
            log.warning("No API-based scrapers configured. Will use requests/BeautifulSoup as fallback.")
    
    def extract_product_listings(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract product listings from a category page.
        
        Parameters
        ----------
        url : str
            URL of the category page to scrape
            
        Returns
        -------
        List[Dict[str, Any]]
            List of product listings with title, price, url, image_url
        """
        # Get domain-specific selectors
        domain = tldextract.extract(url).registered_domain
        selectors = get_selectors_for_domain(domain)
        
        if not selectors:
            log.warning(f"No selectors found for domain: {domain}")
            return []
        
        log.info(f"Extracting product listings from {url}")
        
        # Check if it's an Amazon URL and prioritize Oxylabs for Amazon
        is_amazon = "amazon" in domain.lower()
        
        # Try each available scraper in order, with Oxylabs first for Amazon
        result = None
        html_content = None
        scraper_used = None
        
        # Define scraper order based on the domain
        scraper_order = list(self.scrapers.items())
        
        # Prioritize Oxylabs for Amazon
        if is_amazon and "oxylabs" in self.scrapers:
            # Move Oxylabs to the beginning of the list
            scraper_order = [("oxylabs", self.scrapers["oxylabs"])] + [
                (name, scraper) for name, scraper in scraper_order 
                if name != "oxylabs"
            ]
        
        for name, scraper in scraper_order:
            log.info(f"Trying to extract product listings using {name}")
            
            try:
                if name == "oxylabs":
                    # Use Oxylabs with different approach for Amazon vs non-Amazon
                    if is_amazon:
                        # Extract Amazon ASIN from URL if possible
                        asin = self._extract_asin_from_url(url)
                        if asin:
                            # Use Amazon product endpoint
                            result = scraper.get_amazon_product(asin)
                            if result and not result.get("error") and "product_data" in result:
                                # For Amazon product detail pages, return as a single-item list
                                return [result["product_data"]]
                    
                    # Fallback to universal scraper
                    result = scraper.scrape_page(url, render="html")
                    if result and not result.get("error") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
                elif name == "firecrawl":
                    # Use Firecrawl
                    result = scraper.scrape_page(
                        url,
                        formats=["html"],
                        waitFor=5000
                    )
                    if result and not result.get("error") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
                elif name == "hyperbrowser":
                    # Use Hyperbrowser
                    result = scraper.scrape_page(
                        url,
                        output_format="html"
                    )
                    if result and not result.get("error") and "content" in result:
                        html_content = result["content"]
                        scraper_used = name
                        break
                
                elif name == "browserbase":
                    # Use Browserbase
                    result = scraper.scrape_page(url)
                    if result and not result.get("error") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
                elif name == "scraperapi":
                    # Use ScraperAPI
                    result = scraper.scrape_page(url, render=True)
                    if result and result.get("success") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
            except Exception as exc:
                log.error(f"Error extracting product listings with {name}: {exc}")
        
        # Fallback to requests/BeautifulSoup if no API-based scraper succeeded
        if not html_content:
            log.warning("All API-based scrapers failed, trying fallback with requests/BeautifulSoup")
            try:
                response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code == 200:
                    html_content = response.text
                    scraper_used = "requests_fallback"
                else:
                    log.error(f"Failed to fetch URL with requests: {response.status_code}")
                    return []
            except Exception as exc:
                log.error(f"Failed to fetch URL with requests: {exc}")
                return []
        
        # Parse the HTML to extract product listings
        log.info(f"Successfully retrieved HTML with {scraper_used}, parsing product listings")
        return self._parse_product_listings(html_content, url, selectors)
    
    def extract_product_details(self, url: str) -> Dict[str, Any]:
        """
        Extract detailed product information from a product page.
        
        Parameters
        ----------
        url : str
            URL of the product page to scrape
            
        Returns
        -------
        Dict[str, Any]
            Detailed product information
        """
        # Get domain-specific selectors
        domain = tldextract.extract(url).registered_domain
        selectors = get_selectors_for_domain(domain)
        
        if not selectors:
            log.warning(f"No selectors found for domain: {domain}")
            return {}
        
        log.info(f"Extracting product details from {url}")
        
        # Check if it's an Amazon URL and prioritize Oxylabs for Amazon
        is_amazon = "amazon" in domain.lower()
        
        # Try each available scraper in order, with Oxylabs first for Amazon
        result = None
        html_content = None
        scraper_used = None
        
        # Define scraper order based on the domain
        scraper_order = list(self.scrapers.items())
        
        # Prioritize Oxylabs for Amazon
        if is_amazon and "oxylabs" in self.scrapers:
            # Move Oxylabs to the beginning of the list
            scraper_order = [("oxylabs", self.scrapers["oxylabs"])] + [
                (name, scraper) for name, scraper in scraper_order 
                if name != "oxylabs"
            ]
        
        for name, scraper in scraper_order:
            log.info(f"Trying to extract product details using {name}")
            
            try:
                if name == "oxylabs":
                    # Use Oxylabs with different approach for Amazon vs non-Amazon
                    if is_amazon:
                        # Extract Amazon ASIN from URL if possible
                        asin = self._extract_asin_from_url(url)
                        if asin:
                            # Use Amazon product endpoint
                            result = scraper.get_amazon_product(asin)
                            if result and not result.get("error") and "product_data" in result:
                                return result["product_data"]
                    
                    # Fallback to universal scraper
                    result = scraper.scrape_page(url, render="html")
                    if result and not result.get("error") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
                elif name == "firecrawl":
                    # Use Firecrawl
                    result = scraper.scrape_page(
                        url,
                        formats=["html"],
                        waitFor=5000
                    )
                    if result and not result.get("error") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
                elif name == "hyperbrowser":
                    # Use Hyperbrowser
                    result = scraper.scrape_page(
                        url,
                        output_format="html"
                    )
                    if result and not result.get("error") and "content" in result:
                        html_content = result["content"]
                        scraper_used = name
                        break
                
                elif name == "browserbase":
                    # Use Browserbase
                    result = scraper.scrape_page(url)
                    if result and not result.get("error") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
                elif name == "scraperapi":
                    # Use ScraperAPI
                    result = scraper.scrape_page(url, render=True)
                    if result and result.get("success") and "html" in result:
                        html_content = result["html"]
                        scraper_used = name
                        break
                
            except Exception as exc:
                log.error(f"Error extracting product details with {name}: {exc}")
        
        # Fallback to requests/BeautifulSoup if no API-based scraper succeeded
        if not html_content:
            log.warning("All API-based scrapers failed, trying fallback with requests/BeautifulSoup")
            try:
                response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code == 200:
                    html_content = response.text
                    scraper_used = "requests_fallback"
                else:
                    log.error(f"Failed to fetch URL with requests: {response.status_code}")
                    return {}
            except Exception as exc:
                log.error(f"Failed to fetch URL with requests: {exc}")
                return {}
        
        # Parse the HTML to extract product details
        log.info(f"Successfully retrieved HTML with {scraper_used}, parsing product details")
        return self._parse_product_details(html_content, url, selectors)
    
    def navigate_pagination(self, url: str, page_num: int) -> str:
        """
        Generate URL for a paginated page.
        
        Parameters
        ----------
        url : str
            Base URL of the category page
        page_num : int
            Page number to navigate to
            
        Returns
        -------
        str
            URL for the paginated page
        """
        domain = tldextract.extract(url).registered_domain
        selectors = get_selectors_for_domain(domain)
        
        if selectors and "pagination_pattern" in selectors:
            # Use domain-specific pagination pattern if available
            pattern = selectors["pagination_pattern"]
            return pattern.replace("{page}", str(page_num))
        
        # Generic pagination handling - try to infer from URL structure
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Common pagination parameter names
        pagination_params = ["page", "p", "pg", "paged", "pn"]
        
        for param in pagination_params:
            if param in query_params:
                # Update the existing parameter
                query_params[param] = [str(page_num)]
                updated_query = urllib.parse.urlencode(query_params, doseq=True)
                return urllib.parse.urlunparse(
                    (parsed_url.scheme, parsed_url.netloc, parsed_url.path, 
                     parsed_url.params, updated_query, parsed_url.fragment)
                )
        
        # If no pagination parameter found, try appending to path
        if parsed_url.path.endswith("/"):
            new_path = f"{parsed_url.path}page/{page_num}/"
        else:
            new_path = f"{parsed_url.path}/page/{page_num}/"
        
        return urllib.parse.urlunparse(
            (parsed_url.scheme, parsed_url.netloc, new_path, 
             parsed_url.params, parsed_url.query, parsed_url.fragment)
        )
    
    def search_amazon_products(self, query: str, marketplace: str = "UK") -> List[Dict[str, Any]]:
        """
        Search for products on Amazon.
        
        Parameters
        ----------
        query : str
            Search query
        marketplace : str
            Amazon marketplace to search (UK or US)
            
        Returns
        -------
        List[Dict[str, Any]]
            List of product search results
        """
        # Determine search URL based on marketplace
        if marketplace.upper() == "US":
            search_url = f"https://www.amazon.com/s?k={urllib.parse.quote(query)}"
        else:
            search_url = f"https://www.amazon.co.uk/s?k={urllib.parse.quote(query)}"
        
        # If Oxylabs is available, use it directly for search
        if "oxylabs" in self.scrapers:
            try:
                log.info(f"Searching Amazon for '{query}' using Oxylabs")
                oxylabs = self.scrapers["oxylabs"]
                
                # Use Google search with site:amazon.com/co.uk to get product links
                site = "amazon.com" if marketplace.upper() == "US" else "amazon.co.uk"
                google_query = f"site:{site} {query}"
                
                result = oxylabs.search_google(google_query)
                
                if result and not result.get("error") and "results" in result:
                    products = []
                    
                    # Process Google search results to find Amazon product links
                    for item in result["results"][0].get("organic", [])[:5]:  # Limit to first 5 results
                        if "url" in item and site in item["url"]:
                            # Extract ASIN from URL if possible
                            asin = self._extract_asin_from_url(item["url"])
                            if asin:
                                # Get detailed product info using the Amazon product endpoint
                                product_result = oxylabs.get_amazon_product(asin)
                                if product_result and not product_result.get("error") and "product_data" in product_result:
                                    products.append(product_result["product_data"])
                    
                    if products:
                        return products
            
            except Exception as exc:
                log.error(f"Error searching Amazon with Oxylabs: {exc}")
        
        # Fallback to regular web scraping
        return self.extract_product_listings(search_url)
    
    def _parse_product_listings(self, html: str, base_url: str, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Parse HTML to extract product listings using the provided selectors.
        
        Parameters
        ----------
        html : str
            HTML content of the page
        base_url : str
            Base URL for resolving relative URLs
        selectors : Dict[str, str]
            CSS selectors for product listings
            
        Returns
        -------
        List[Dict[str, Any]]
            List of product listings
        """
        parsed_url = urllib.parse.urlparse(base_url)
        base_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            product_items = []
            
            # Select product listing items
            item_selector = selectors.get("listing_item", ".product")
            title_selector = selectors.get("listing_title", ".product-title")
            price_selector = selectors.get("listing_price", ".product-price")
            url_selector = selectors.get("listing_url", ".product-link")
            image_selector = selectors.get("listing_image", ".product-image img")
            
            items = soup.select(item_selector)
            log.info(f"Found {len(items)} product items using selector: {item_selector}")
            
            for item in items:
                product = {}
                
                # Extract title
                title_elem = item.select_one(title_selector)
                if title_elem:
                    product["title"] = title_elem.get_text().strip()
                
                # Extract price
                price_elem = item.select_one(price_selector)
                if price_elem:
                    price_text = price_elem.get_text().strip()
                    # Extract numeric price
                    product["price"] = self._extract_price(price_text)
                
                # Extract URL
                url_elem = item.select_one(url_selector) or title_elem
                if url_elem and url_elem.has_attr("href"):
                    href = url_elem["href"]
                    # Handle relative URLs
                    if href.startswith("/"):
                        href = f"{base_host}{href}"
                    elif not href.startswith(("http://", "https://")):
                        href = urllib.parse.urljoin(base_url, href)
                    product["url"] = href
                    
                    # If it's an Amazon URL, try to extract ASIN
                    if "amazon" in parsed_url.netloc:
                        asin = self._extract_asin_from_url(href)
                        if asin:
                            product["asin"] = asin
                
                # Extract image
                image_elem = item.select_one(image_selector)
                if image_elem and image_elem.has_attr("src"):
                    src = image_elem["src"]
                    # Handle relative URLs
                    if src.startswith("/"):
                        src = f"{base_host}{src}"
                    elif not src.startswith(("http://", "https://")):
                        src = urllib.parse.urljoin(base_url, src)
                    product["image_url"] = src
                
                # Only add product if we have at least title and URL
                if product.get("title") and product.get("url"):
                    product_items.append(product)
            
            return product_items
            
        except Exception as exc:
            log.error(f"Error parsing product listings: {exc}")
            return []
    
    def _parse_product_details(self, html: str, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse HTML to extract detailed product information using the provided selectors.
        
        Parameters
        ----------
        html : str
            HTML content of the page
        url : str
            URL of the product page
        selectors : Dict[str, str]
            CSS selectors for product details
            
        Returns
        -------
        Dict[str, Any]
            Detailed product information
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            product = {"url": url}
            
            # If it's an Amazon URL, try to extract ASIN
            if "amazon" in url:
                asin = self._extract_asin_from_url(url)
                if asin:
                    product["asin"] = asin
            
            # Extract product details using selectors
            title_selector = selectors.get("product_title", ".product-title")
            price_selector = selectors.get("product_price", ".product-price")
            description_selector = selectors.get("product_description", ".product-description")
            sku_selector = selectors.get("product_sku", ".product-sku")
            brand_selector = selectors.get("product_brand", ".product-brand")
            upc_selector = selectors.get("product_upc", ".product-upc")
            features_selector = selectors.get("product_features", ".product-features li")
            specs_selector = selectors.get("product_specs", ".product-specs tr")
            image_selector = selectors.get("product_image", ".product-image img")
            
            # Extract title
            title_elem = soup.select_one(title_selector)
            if title_elem:
                product["title"] = title_elem.get_text().strip()
            
            # Extract price
            price_elem = soup.select_one(price_selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                product["price"] = self._extract_price(price_text)
            
            # Extract description
            description_elem = soup.select_one(description_selector)
            if description_elem:
                product["description"] = description_elem.get_text().strip()
            
            # Extract SKU
            sku_elem = soup.select_one(sku_selector)
            if sku_elem:
                product["sku"] = sku_elem.get_text().strip()
            
            # Extract brand
            brand_elem = soup.select_one(brand_selector)
            if brand_elem:
                product["brand"] = brand_elem.get_text().strip()
            
            # Extract UPC/EAN
            upc_elem = soup.select_one(upc_selector)
            if upc_elem:
                product["upc"] = upc_elem.get_text().strip()
            
            # Extract features
            features_elems = soup.select(features_selector)
            if features_elems:
                product["features"] = [elem.get_text().strip() for elem in features_elems]
            
            # Extract specifications
            specs_elems = soup.select(specs_selector)
            if specs_elems:
                specs = {}
                for elem in specs_elems:
                    key_elem = elem.select_one("th") or elem.select_one("td:first-child")
                    value_elem = elem.select_one("td:last-child")
                    if key_elem and value_elem:
                        key = key_elem.get_text().strip()
                        value = value_elem.get_text().strip()
                        specs[key] = value
                if specs:
                    product["specifications"] = specs
            
            # Extract main image
            image_elem = soup.select_one(image_selector)
            if image_elem and image_elem.has_attr("src"):
                parsed_url = urllib.parse.urlparse(url)
                base_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                src = image_elem["src"]
                # Handle relative URLs
                if src.startswith("/"):
                    src = f"{base_host}{src}"
                elif not src.startswith(("http://", "https://")):
                    src = urllib.parse.urljoin(url, src)
                product["image_url"] = src
            
            return product
            
        except Exception as exc:
            log.error(f"Error parsing product details: {exc}")
            return {"url": url, "error": str(exc)}
    
    def _extract_price(self, price_text: str) -> float:
        """
        Extract numeric price from price text.
        
        Parameters
        ----------
        price_text : str
            Price text to parse
            
        Returns
        -------
        float
            Extracted price as float, or 0.0 if parsing fails
        """
        import re
        
        # Remove currency symbols and non-numeric characters except decimal point
        price_text = re.sub(r'[^\d.]', '', price_text.replace(',', '.'))
        
        try:
            # Find and extract the first valid number
            match = re.search(r'\d+(\.\d+)?', price_text)
            if match:
                return float(match.group(0))
        except (ValueError, AttributeError):
            pass
        
        return 0.0
    
    def _extract_asin_from_url(self, url: str) -> str:
        """
        Extract Amazon ASIN from product URL.
        
        Parameters
        ----------
        url : str
            Amazon product URL
            
        Returns
        -------
        str
            Extracted ASIN or empty string if not found
        """
        import re
        
        # Try different patterns for ASIN extraction
        asin_patterns = [
            r'/dp/([A-Z0-9]{10})(?:/|$|\?)',  # /dp/ASIN pattern
            r'/gp/product/([A-Z0-9]{10})(?:/|$|\?)',  # /gp/product/ASIN pattern
            r'/([A-Z0-9]{10})(?:/|$|\?)',  # Direct ASIN in URL
            r'(?:ASIN=|asin=|asin%3D|asin-|asin_)([A-Z0-9]{10})(?:/|$|\?|&)'  # ASIN in query params
        ]
        
        for pattern in asin_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return ""
