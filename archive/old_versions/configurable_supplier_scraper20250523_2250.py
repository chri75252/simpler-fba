"""
ConfigurableSupplierScraper class for the passive extraction workflow.
Provides methods for extracting data from supplier websites with externalized selector configuration.
Integrates AI fallbacks for selector failures, features optimized HTML parsing, and dedicated pagination logic.
Maintains backward compatibility with the orchestrator while using improved configuration approach.
"""

import os
import logging
import aiohttp
import re
import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin

# Import config loader for supplier selector configuration
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.supplier_config_loader import load_supplier_selectors, get_domain_from_url

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Constants
OPENAI_MODEL_NAME_DEFAULT = "gpt-4.1-mini-2025-04-14"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
REQUEST_TIMEOUT = 30  # seconds


class ConfigurableSupplierScraper:
    """
    Configurable web scraper for extracting data from supplier websites.
    Uses externalized selectors and configurations loaded from JSON files.
    Prioritizes selector-based extraction, with AI-powered fallbacks.
    Features include optimized parsing, robust error handling, and flexible selectors.
    """
    
    def __init__(self, ai_client: Optional[Any] = None, openai_model_name: str = OPENAI_MODEL_NAME_DEFAULT):
        """
        Initialize the configurable supplier scraper.
        
        Args:
            ai_client: An initialized OpenAI client (or compatible)
            openai_model_name: The model name to use for AI operations
        """
        self.session: Optional[aiohttp.ClientSession] = None
        self.ai_client = ai_client
        self.openai_model = openai_model_name
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # Default 1 second between requests
        
        # Cache for loaded selector configurations
        self.loaded_selector_configs = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an aiohttp ClientSession with appropriate headers.
        
        Returns:
            aiohttp.ClientSession: The session object
        """
        if self.session is None or self.session.closed:
            # Standard headers to mimic a browser
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def get_page_content(self, url: str, retry_count: int = 3) -> Optional[str]:
        """
        Get the HTML content of a page using aiohttp with rate limiting and retries.
        
        Args:
            url: The URL to fetch
            retry_count: Number of retries on failure
            
        Returns:
            Optional[str]: The HTML content or None on failure
        """
        session = await self._get_session()
        
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request)
        
        self.last_request_time = time.time()
        
        for attempt in range(retry_count):
            try:
                log.info(f"Fetching page content from: {url} (attempt {attempt+1}/{retry_count})")
                async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
                    if response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', 5))
                        log.warning(f"Rate limited (429). Waiting {retry_after}s before retry.")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    response.raise_for_status()
                    html_content = await response.text()
                    
                    if not html_content or len(html_content) < 1000:
                        log.warning(f"Suspicious response size ({len(html_content)} bytes). Checking if valid HTML.")
                        if "<html" not in html_content.lower() or "<body" not in html_content.lower():
                            log.warning(f"Response doesn't appear to be valid HTML. Retrying.")
                            await asyncio.sleep(2)
                            continue
                    
                    log.info(f"Successfully fetched content from {url} (Size: {len(html_content)} bytes)")
                    return html_content
                    
            except aiohttp.ClientError as e:
                log.error(f"AIOHTTP client error fetching {url} (attempt {attempt+1}): {e}")
            except asyncio.TimeoutError:
                log.error(f"Timeout error fetching {url} (attempt {attempt+1})")
            except Exception as e:
                log.error(f"Unexpected error fetching {url} (attempt {attempt+1}): {e}")
            
            # Exponential backoff
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt + 1
                log.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                
        log.error(f"Failed to fetch {url} after {retry_count} attempts.")
        return None

    def _get_selectors_for_domain(self, url: str) -> Dict[str, Any]:
        """
        Get selectors for a specific domain from external configuration files,
        falling back to default if not found.
        
        Args:
            url: The URL to determine domain from
            
        Returns:
            Dict containing appropriate selectors
        """
        try:
            # Extract domain from URL
            domain = get_domain_from_url(url)
            
            # Check if we have already loaded selectors for this domain
            if domain in self.loaded_selector_configs:
                log.debug(f"Using cached selector config for domain: {domain}")
                return self.loaded_selector_configs[domain]
                
            # Load selectors from external configuration file
            domain_selectors = load_supplier_selectors(domain)
            
            if not domain_selectors:
                # Fallback to default selectors if specific domain config not found
                log.warning(f"No selector configuration found for domain: {domain}. Using default configuration.")
                domain_selectors = load_supplier_selectors("default")
                
            # Cache the loaded selectors
            self.loaded_selector_configs[domain] = domain_selectors
            log.info(f"Loaded and cached selector configuration for domain: {domain}")
            
            return domain_selectors
        except Exception as e:
            log.error(f"Error determining selectors for domain ({url}): {e}")
            # Try to load default selectors as a fallback
            try:
                default_selectors = load_supplier_selectors("default")
                return default_selectors
            except Exception as e_default:
                log.error(f"Error loading default selectors: {e_default}")
                # Return empty dict as last resort
                return {}

    def extract_product_elements(self, html: str, url: str) -> List[BeautifulSoup]:
        """
        Extract product elements from HTML using BeautifulSoup and site-specific selectors.
        
        Args:
            html: HTML content to parse
            url: Source URL for context and domain-specific selectors
            
        Returns:
            List of BeautifulSoup product elements
        """
        soup = BeautifulSoup(html, 'html.parser')
        selectors = self._get_selectors_for_domain(url)
        product_selectors = selectors.get("product_item", selectors.get("product", []))
        
        # If the product selector is a string, convert to list for consistent processing
        if isinstance(product_selectors, str):
            product_selectors = [product_selectors]
        
        # Try each selector until we find product elements
        for selector in product_selectors:
            elements = soup.select(selector)
            if elements:
                log.info(f"Found {len(elements)} product elements on {url} using selector: '{selector}'")
                return elements
        
        # If no elements are found with any selector, try a more aggressive approach
        log.warning(f"No product elements found with configured selectors on {url}. Trying generic approaches.")
        
        # Look for common product patterns in the page structure
        potential_containers = soup.select("div.products, div.product-list, ul.products, div.collection, section.products")
        for container in potential_containers:
            # Look for direct children that could be product listings
            child_items = container.find_all(["div", "li", "article"], recursive=False)
            if len(child_items) > 3:  # If we find multiple direct children, they're likely products
                log.info(f"Found {len(child_items)} potential product elements using container approach.")
                return child_items
            
            # If there are few or no direct children, try one level deeper
            deeper_items = container.find_all(["div", "li", "article"], recursive=True, limit=30)
            if len(deeper_items) > 3:
                log.info(f"Found {len(deeper_items)} potential product elements using deeper container scan.")
                return deeper_items
        
        # Last resort: look for common product indicators
        all_product_indicators = soup.find_all(lambda tag: tag.name in ["div", "li", "article"] and 
                                                (tag.has_attr("class") and any(c in str(tag["class"]) for c in ["product", "item", "card"]) or
                                                 tag.has_attr("id") and any(i in str(tag["id"]) for i in ["product", "item", "card"])),
                                       limit=30)
        
        if all_product_indicators:
            log.info(f"Found {len(all_product_indicators)} product elements using indicator approach.")
            return all_product_indicators
            
        log.warning(f"Could not extract any product elements from {url}.")
        return []

    def _extract_with_selector(self, element_soup: BeautifulSoup, selectors: List[str], attribute: Optional[str] = None, extract_text: bool = True) -> Optional[str]:
        """
        Helper to extract data using a list of selectors.
        
        Args:
            element_soup: BeautifulSoup element to search within
            selectors: List of CSS selectors to try
            attribute: Optional attribute to extract instead of text
            extract_text: Whether to extract text content
            
        Returns:
            Extracted value or None if not found
        """
        if not isinstance(selectors, list):
            selectors = [selectors]
            
        for selector in selectors:
            try:
                target = element_soup.select_one(selector)
                if target:
                    if attribute:
                        attr_value = target.get(attribute)
                        if attr_value: 
                            return str(attr_value).strip()
                    elif extract_text:
                        text_content = target.get_text(separator=" ", strip=True)
                        if text_content: 
                            return text_content
            except Exception as e:
                log.debug(f"Error with selector '{selector}': {e}")
                continue
                
        return None

    async def _ai_extract_field_from_html_element(self, element_html: str, field_description: str, context_url: str) -> Optional[str]:
        """
        Call AI model to extract a specific field from a product HTML element.
        
        Args:
            element_html: HTML of the product element
            field_description: Description of the field to extract
            context_url: URL for context
            
        Returns:
            Extracted value or None if not found or AI unavailable
        """
        if not self.ai_client:
            log.warning(f"AI client not available. Cannot extract '{field_description}' from HTML element.")
            return None
        
        try:
            # Limit HTML size to avoid token limits
            max_html_len = 6000
            truncated_html = element_html[:max_html_len]
            if len(element_html) > max_html_len:
                truncated_html += "... [truncated]"
            
            # Provide context about the field and the source URL
            prompt = (
                f"You are an expert web data extractor. From the following HTML snippet of a product item on the webpage {context_url}, "
                f"extract the '{field_description}'. Provide only the extracted value with no explanation or commentary. "
                f"If not found, respond with 'Not found'.\n\n"
                f"HTML Snippet:\n{truncated_html}"
            )
            
            response = await asyncio.to_thread(
                 self.ai_client.chat.completions.create,
                 model=self.openai_model,
                 messages=[{"role": "user", "content": prompt}],
                 temperature=0.0,
                 max_tokens=100
            )
            extracted_value = response.choices[0].message.content.strip()
            
            if extracted_value.lower() in ["not found", "none", "n/a", "no value found", "no data found", ""]:
                return None
                
            log.info(f"AI extracted '{field_description}': '{extracted_value[:50]}...' if len(extracted_value) > 50 else extracted_value")
            return extracted_value
            
        except Exception as e:
            log.error(f"AI HTML element extraction for '{field_description}' failed: {e}")
            return None

    async def extract_title(self, element_soup: BeautifulSoup, element_html: str, context_url: str) -> Optional[str]:
        """
        Extract product title, with AI fallback.
        
        Args:
            element_soup: BeautifulSoup element containing product data
            element_html: HTML string of the element for AI fallback
            context_url: URL for context and domain-specific selectors
            
        Returns:
            Extracted title or None if not found
        """
        selectors = self._get_selectors_for_domain(context_url)
        title_selectors = selectors.get("title", [])
        title = self._extract_with_selector(element_soup, title_selectors)
        
        # If no title found with selectors, try direct attributes
        if not title and element_soup.has_attr("title"):
            title = element_soup["title"]
            
        # If still no title, try to find any link with title attribute
        if not title:
            links = element_soup.find_all("a", title=True)
            if links:
                title = links[0]["title"]
        
        # If we still don't have a title but found an anchor tag, use its text
        if not title:
            anchor = element_soup.find("a")
            if anchor and anchor.get_text(strip=True):
                title = anchor.get_text(strip=True)
                
        if title:
            # Clean up the title
            title = re.sub(r'\s+', ' ', title).strip()
            return title
        
        log.warning(f"Failed to extract title with selectors from element on {context_url}. Attempting AI fallback.")
        return await self._ai_extract_field_from_html_element(element_html, "product title", context_url)

    async def extract_price(self, element_soup: BeautifulSoup, element_html: str, context_url: str) -> Optional[float]:
        """
        Extract product price, with AI fallback and parsing.
        
        Args:
            element_soup: BeautifulSoup element containing product data
            element_html: HTML string of the element for AI fallback
            context_url: URL for context and domain-specific selectors
            
        Returns:
            Parsed price as float or None if not found
        """
        selectors = self._get_selectors_for_domain(context_url)
        price_selectors = selectors.get("price", [])
        price_str = self._extract_with_selector(element_soup, price_selectors)
        
        # If no price found, try data attribute
        if not price_str:
            price_attrs = [elem for elem in element_soup.find_all(attrs={"data-price": True}) if elem.get("data-price")]
            if price_attrs:
                price_str = price_attrs[0]["data-price"]
                
        # Try additional common price patterns
        if not price_str:
            # Look for elements with specific classes or elements with price indicators
            price_indicators = element_soup.find_all(lambda tag: 
                tag.name and (
                    tag.has_attr("class") and any(c in str(tag["class"]).lower() for c in ["price", "amount", "cost", "value"]) or
                    tag.has_attr("itemprop") and "price" in tag["itemprop"].lower() or
                    tag.has_attr("data-price") or
                    tag.has_attr("id") and "price" in tag["id"].lower()
                )
            )
            
            for indicator in price_indicators:
                text = indicator.get_text(strip=True)
                if text and (re.search(r'[£$€]', text) or re.search(r'\d+\.\d+', text)):
                    price_str = text
                    break
        
        if price_str:
            parsed_price = self._parse_price(price_str)
            if parsed_price is not None and parsed_price > 0:
                return parsed_price
        
        log.warning(f"Failed to extract/parse price with selectors from element on {context_url}. Attempting AI fallback.")
        ai_price_str = await self._ai_extract_field_from_html_element(element_html, "product price (numerical value without currency symbols)", context_url)
        
        if ai_price_str:
            return self._parse_price(ai_price_str)
        return None

    async def extract_url(self, element_soup: BeautifulSoup, element_html: str, context_url: str, base_url: str) -> Optional[str]:
        """
        Extract product URL, with AI fallback and ensuring it's absolute.
        
        Args:
            element_soup: BeautifulSoup element containing product data
            element_html: HTML string of the element for AI fallback
            context_url: URL for context and domain-specific selectors
            base_url: Base URL for converting relative URLs to absolute
            
        Returns:
            Absolute URL or None if not found
        """
        selectors = self._get_selectors_for_domain(context_url)
        url_selectors = selectors.get("url", [])
        url_path = self._extract_with_selector(element_soup, url_selectors, attribute='href')
        
        # If no URL found with selector but the element itself is an <a> tag
        if not url_path and element_soup.name == 'a':
            url_path = element_soup.get('href')
            
        # If still no URL, try to find any link in the element
        if not url_path:
            links = element_soup.find_all("a", href=True)
            if links:
                # Prioritize links that look like product links
                for link in links:
                    href = link.get('href', '').strip()
                    if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                        # Skip obvious non-product links
                        href_lower = href.lower()
                        if not any(skip in href_lower for skip in ['cart', 'wishlist', 'compare', 'share', 'facebook', 'twitter']):
                            url_path = href
                            break
                
                # If no good link found, use the first one
                if not url_path and links:
                    url_path = links[0]["href"]
        
        if url_path:
            # Clean up the URL path
            url_path = url_path.strip()
            if url_path and not url_path.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                # Convert to absolute URL if needed
                absolute_url = self._ensure_absolute_url(url_path, base_url)
                
                # Validate the URL looks reasonable
                if absolute_url and ('://' in absolute_url or absolute_url.startswith('/')):
                    return absolute_url

        log.warning(f"Failed to extract URL with selectors from element on {context_url}. Attempting AI fallback.")
        ai_url = await self._ai_extract_field_from_html_element(element_html, "product page URL (href attribute of the main link)", context_url)
        
        if ai_url:
            ai_url = ai_url.strip()
            if ai_url and not ai_url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                return self._ensure_absolute_url(ai_url, base_url)
        return None

    def _ensure_absolute_url(self, url: str, base_url: str) -> str:
        """
        Ensure a URL is absolute by converting relative URLs.
        
        Args:
            url: URL to check and potentially convert
            base_url: Base URL to use for conversion
            
        Returns:
            Absolute URL
        """
        if not url or not isinstance(url, str):
            return url
            
        url = url.strip()
        if not url:
            return url
            
        # Handle protocol-relative URLs
        if url.startswith('//'):
            return 'https:' + url
            
        # Handle data URLs and javascript URLs
        if url.startswith(('data:', 'javascript:', 'mailto:', 'tel:')):
            return url
            
        # Already absolute URL
        if url.startswith(('http://', 'https://')):
            return url
            
        # Parse base URL
        try:
            parsed_base = urlparse(base_url)
            base_scheme = parsed_base.scheme or 'https'
            base_netloc = parsed_base.netloc
            base_path = parsed_base.path
            
            if not base_netloc:
                # If base_url doesn't have a netloc, try to extract it
                if '//' not in base_url and '.' in base_url:
                    # Assume it's a domain without protocol
                    base_netloc = base_url.split('/')[0]
                    base_scheme = 'https'
                else:
                    log.warning(f"Invalid base URL: {base_url}")
                    return url
            
            # Root-relative URL (starts with /)
            if url.startswith('/'):
                return f"{base_scheme}://{base_netloc}{url}"
                
            # Fragment or query only
            if url.startswith(('#', '?')):
                return f"{base_scheme}://{base_netloc}{base_path}{url}"
                
            # Relative URL - use urljoin for proper handling
            base_for_join = f"{base_scheme}://{base_netloc}{base_path}"
            if not base_for_join.endswith('/') and '/' in url:
                base_for_join += '/'
                
            return urljoin(base_for_join, url)
            
        except Exception as e:
            log.warning(f"Error processing URL '{url}' with base '{base_url}': {e}")
            # Fallback: if url looks like a path, prepend base domain
            if url.startswith('/'):
                try:
                    domain = base_url.split('//')[1].split('/')[0] if '//' in base_url else base_url.split('/')[0]
                    return f"https://{domain}{url}"
                except:
                    pass
            return url

    async def extract_image(self, element_soup: BeautifulSoup, element_html: str, context_url: str, base_url: str) -> Optional[str]:
        """
        Extract product image URL, with AI fallback and ensuring it's absolute.
        
        Args:
            element_soup: BeautifulSoup element containing product data
            element_html: HTML string of the element for AI fallback
            context_url: URL for context and domain-specific selectors
            base_url: Base URL for converting relative URLs to absolute
            
        Returns:
            Absolute image URL or None if not found
        """
        selectors = self._get_selectors_for_domain(context_url)
        image_selectors = selectors.get("image", [])
        img_src = self._extract_with_selector(element_soup, image_selectors, attribute='src')
        
        # Check for lazy loading patterns
        if not img_src:
            # Try common data attributes used for lazy loading
            for attr in ['data-src', 'data-original', 'data-lazy', 'data-original-src', 'data-lazy-src']:
                img_src = self._extract_with_selector(element_soup, image_selectors, attribute=attr)
                if img_src:
                    break
        
        # If still no image, try to find any image in the element
        if not img_src:
            images = element_soup.find_all("img")
            for img in images:
                # Check for src or any data-* attribute that might contain the image URL
                img_src = img.get('src') or next((img.get(attr) for attr in [
                    'data-src', 'data-original', 'data-lazy', 'data-original-src', 'data-lazy-src'
                ] if img.has_attr(attr)), None)
                
                if img_src:
                    break
                    
        if img_src:
            # Skip data URLs and placeholder images
            if img_src.startswith('data:'):
                log.debug("Found data: URL, looking for better image...")
                # Continue looking for better images
                better_images = element_soup.find_all("img", src=lambda s: s and not s.startswith('data:'))
                if better_images:
                    img_src = better_images[0]['src']
                else:
                    return img_src  # Return the data URL if no better alternative
            
            # Handle SVG images
            if img_src.endswith('.svg'):
                log.debug("Found SVG image URL")
                
            return self._ensure_absolute_url(img_src, base_url)

        log.warning(f"Failed to extract image URL with selectors from element on {context_url}. Attempting AI fallback.")
        ai_img_src = await self._ai_extract_field_from_html_element(element_html, "product image source URL (src attribute of the main image tag)", context_url)
        
        if ai_img_src:
            return self._ensure_absolute_url(ai_img_src, base_url)
        return None
        
        
    async def extract_identifier(self, element_soup: BeautifulSoup, element_html: str, context_url: str) -> Optional[str]:
        """
        Extract product EAN, UPC, or other primary Barcode using configured selectors.
        This method is typically used on a product detail page's soup.
        """
        config = self._get_selectors_for_domain(context_url)
        
        identifier_selectors = []  
        for key in [
            "identifier_selectors_product_page",
            "ean_selector_product_page",
            "barcode_selector_product_page",
            "upc_selector_product_page",
            "gtin_selector_product_page"
        ]:
            val = config.get(key, [])
            if isinstance(val, str):
                 val = [val]
            if val:
                identifier_selectors.extend(val)


        if isinstance(identifier_selectors, str): # Ensure it's a list
            identifier_selectors = [identifier_selectors]
        
        extracted_code = None
        if identifier_selectors:
            for selector in identifier_selectors:
                log.debug(f"Trying identifier selector: '{selector}' on {context_url}")
                # _extract_with_selector expects a list, so wrap single selector
                candidate_str = self._extract_with_selector(element_soup, [selector])
                if candidate_str:
                    cleaned_val = re.sub(r'[^0-9]', '', candidate_str) # Keep only digits
                    # Common barcode lengths: EAN-8, UPC-E (can be 8 if converted), UPC-A (12), EAN-13, GTIN-14
                    if len(cleaned_val) in [8, 12, 13, 14] and cleaned_val.isdigit():
                        log.info(f"Valid product identifier '{cleaned_val}' extracted using selector '{selector}' from {context_url}.")
                        extracted_code = cleaned_val
                        break # Found a valid one
                    elif cleaned_val: # Found something, but length or content is unusual
                        log.warning(f"Value from selector '{selector}' ('{candidate_str}', cleaned: '{cleaned_val}') is not a standard length barcode for {context_url}. Will keep trying other selectors.")
                # else: (no value found with this selector, try next)
        
        if extracted_code:
            return extracted_code

        # AI Fallback if no selectors yielded a usable result
        log.warning(f"Failed to extract EAN/Barcode with selectors from element on {context_url}. Attempting AI fallback.")
        ai_identifier_str = await self._ai_extract_field_from_html_element(
            element_html,
            "product's 13-digit EAN, 12-digit UPC, or other primary numerical Barcode. Provide only the numeric value.",
            context_url
        )
        
        if ai_identifier_str:
            cleaned_ai_identifier = re.sub(r'[^0-9]', '', ai_identifier_str)
            if len(cleaned_ai_identifier) in [8, 12, 13, 14] and cleaned_ai_identifier.isdigit():
                log.info(f"AI extracted valid product identifier '{cleaned_ai_identifier}' from {context_url}.")
                return cleaned_ai_identifier
            elif cleaned_ai_identifier:
                 log.warning(f"AI extracted identifier ('{ai_identifier_str}', cleaned: '{cleaned_ai_identifier}') has unusual length from {context_url}. Using AI result if it's purely numeric.")
                 return cleaned_ai_identifier if cleaned_ai_identifier.isdigit() else None
            else:
                log.info(f"AI extraction for EAN/Barcode from {context_url} did not yield usable digits.")
        
        return None
        
    def get_next_page_url(self, current_url: str, current_page_soup: BeautifulSoup, current_page_num: int = 1) -> Optional[str]:
        """
        Get the URL for the next page of products based on pagination configuration.
        
        Args:
            current_url: Current URL being processed
            current_page_soup: BeautifulSoup object of the current page
            current_page_num: Current page number (default: 1)
            
        Returns:
            URL for the next page or None if no next page is found
        """
        selectors = self._get_selectors_for_domain(current_url)
        pagination_config = selectors.get("pagination", {})
        
        # Method 1: Try pattern-based pagination if provided
        if pagination_config.get("pattern"):
            pattern = pagination_config["pattern"]
            if "{page_num}" in pattern:
                next_page_num = current_page_num + 1
                # Handle different pattern formats
                if pattern.startswith(("http://", "https://")):
                    # Absolute URL pattern
                    return pattern.replace("{page_num}", str(next_page_num))
                elif pattern.startswith("/"):
                    # Root-relative URL pattern
                    base_url = f"{urlparse(current_url).scheme}://{urlparse(current_url).netloc}"
                    return f"{base_url}{pattern.replace('{page_num}', str(next_page_num))}"
                else:
                    # Relative URL pattern or query parameter
                    if "?" in current_url and "=" in pattern:
                        # Query parameter pattern
                        parsed_url = urlparse(current_url)
                        # Check if the parameter already exists
                        if f"{pattern.split('=')[0]}=" in parsed_url.query:
                            # Replace existing parameter
                            query_params = parsed_url.query.split("&")
                            param_name = pattern.split("=")[0]
                            updated_params = []
                            for param in query_params:
                                if param.startswith(f"{param_name}="):
                                    updated_params.append(f"{param_name}={next_page_num}")
                                else:
                                    updated_params.append(param)
                            updated_query = "&".join(updated_params)
                            return current_url.replace(parsed_url.query, updated_query)
                        else:
                            # Add new parameter
                            separator = "&" if parsed_url.query else "?"
                            return f"{current_url}{separator}{pattern.replace('{page_num}', str(next_page_num))}"
                    else:
                        # Path based
                        return urljoin(current_url, pattern.replace("{page_num}", str(next_page_num)))
        
        # Method 2: Try next button selector if provided
        next_button_selector = pagination_config.get("next_button_selector")
        if next_button_selector:
            next_button = current_page_soup.select_one(next_button_selector)
            if next_button and next_button.has_attr("href"):
                next_url = next_button["href"]
                return self._ensure_absolute_url(next_url, current_url)
        
        # Method 3: Try multiple next button selectors from patterns
        next_button_selectors = pagination_config.get("next_button_selectors", [
            ".next a", "a.next", "a[rel='next']", ".pagination-next a", 
            ".pagination a[aria-label='Next']", "a.action.next", 
            ".pagination a.next", "li.next a", ".pager-next a"
        ])
        
        if not isinstance(next_button_selectors, list):
            next_button_selectors = [next_button_selectors]
            
        for selector in next_button_selectors:
            try:
                next_button = current_page_soup.select_one(selector)
                if next_button and next_button.has_attr("href"):
                    next_url = next_button["href"]
                    return self._ensure_absolute_url(next_url, current_url)
            except Exception as e:
                log.debug(f"Error checking next button with selector '{selector}': {e}")
        
        # Method 4: Try patterns list if available
        pagination_patterns = pagination_config.get("patterns", [])
        if pagination_patterns:
            # Try each pattern
            for pattern in pagination_patterns:
                if "{page_num}" in pattern:
                    next_page_url = self._apply_pagination_pattern(current_url, pattern, current_page_num + 1)
                    if next_page_url:
                        return next_page_url
        
        # Method 5: Infer pagination from URL
        inferred_next_page = self._infer_next_page_url(current_url, current_page_num)
        if inferred_next_page:
            return inferred_next_page
            
        log.warning(f"Could not determine next page URL for {current_url} (current page: {current_page_num})")
        return None
    
    def _apply_pagination_pattern(self, current_url: str, pattern: str, next_page_num: int) -> Optional[str]:
        """
        Apply a pagination pattern to create a next page URL.
        
        Args:
            current_url: Current URL
            pattern: Pagination pattern with {page_num} placeholder
            next_page_num: Next page number
            
        Returns:
            Next page URL or None if pattern cannot be applied
        """
        try:
            if pattern.startswith(("http://", "https://")):
                # Absolute URL pattern
                return pattern.replace("{page_num}", str(next_page_num))
            
            parsed_url = urlparse(current_url)
            
            if "?" in pattern:
                # Query parameter pattern
                param_name = pattern.split("=")[0].strip("?")
                param_value = str(next_page_num)
                
                # Parse existing query parameters
                query_params = {}
                if parsed_url.query:
                    for param in parsed_url.query.split("&"):
                        if "=" in param:
                            k, v = param.split("=", 1)
                            query_params[k] = v
                
                # Update or add the pagination parameter
                query_params[param_name] = param_value
                
                # Rebuild the query string
                new_query = "&".join([f"{k}={v}" for k, v in query_params.items()])
                
                # Rebuild the URL
                path = parsed_url.path
                return f"{parsed_url.scheme}://{parsed_url.netloc}{path}?{new_query}"
            
            elif pattern.startswith("/"):
                # Root-relative path pattern
                return f"{parsed_url.scheme}://{parsed_url.netloc}{pattern.replace('{page_num}', str(next_page_num))}"
            
            else:
                # Relative path pattern
                path_parts = parsed_url.path.rstrip("/").split("/")
                pattern_parts = pattern.strip("/").split("/")
                
                # Handle patterns like "page/{page_num}/"
                if len(pattern_parts) == 2 and "{page_num}" in pattern_parts[1]:
                    # Check if the pagination component is already in the path
                    if pattern_parts[0] in path_parts:
                        # Replace existing pagination
                        new_path_parts = []
                        for part in path_parts:
                            if part == pattern_parts[0]:
                                new_path_parts.append(pattern_parts[0])
                                new_path_parts.append(pattern_parts[1].replace("{page_num}", str(next_page_num)))
                            elif re.match(r'^\d+$', part) and path_parts[path_parts.index(part) - 1] == pattern_parts[0]:
                                # Skip the current page number
                                continue
                            else:
                                new_path_parts.append(part)
                        
                        new_path = "/" + "/".join(new_path_parts) + "/"
                    else:
                        # Add pagination to the end
                        new_path = f"{parsed_url.path.rstrip('/')}/{pattern_parts[0]}/{pattern_parts[1].replace('{page_num}', str(next_page_num))}/"
                    
                    # Rebuild the URL
                    query = f"?{parsed_url.query}" if parsed_url.query else ""
                    return f"{parsed_url.scheme}://{parsed_url.netloc}{new_path}{query}"
                
                # Simpler case: just append or replace
                return urljoin(current_url, pattern.replace("{page_num}", str(next_page_num)))
                
        except Exception as e:
            log.warning(f"Error applying pagination pattern '{pattern}': {e}")
            
        return None
    
    def _infer_next_page_url(self, current_url: str, current_page_num: int) -> Optional[str]:
        """
        Infer the next page URL based on the structure of the current URL.
        This is used as a fallback when no pagination selectors are found.
        
        Args:
            current_url: Current URL
            current_page_num: Current page number
            
        Returns:
            Inferred next page URL or None if not found
        """
        parsed_url = urlparse(current_url)
        path = parsed_url.path
        query = parsed_url.query
        
        # Check for page number in query parameters (e.g., ?page=2, ?p=2, ?pg=2)
        common_page_params = ["page", "p", "pg", "page_num", "pageNumber", "page_id"]
        
        if query:
            query_params = {}
            for param in query.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    query_params[k] = v
            
            # Check if any common page parameter is present
            for param in common_page_params:
                if param in query_params and query_params[param].isdigit():
                    # Found a page parameter, update it
                    query_params[param] = str(current_page_num + 1)
                    new_query = "&".join([f"{k}={v}" for k, v in query_params.items()])
                    return f"{parsed_url.scheme}://{parsed_url.netloc}{path}?{new_query}"
        
        # Check for page number in the URL path (e.g., /page/2/, /category/page/2/)
        common_page_paths = ["page", "p", "pagina", "pg"]
        
        path_parts = path.rstrip("/").split("/")
        for page_indicator in common_page_paths:
            if page_indicator in path_parts:
                idx = path_parts.index(page_indicator)
                if idx + 1 < len(path_parts) and path_parts[idx + 1].isdigit():
                    # Found a page indicator with a number after it
                    path_parts[idx + 1] = str(current_page_num + 1)
                    new_path = "/" + "/".join(path_parts) + "/"
                    query_part = f"?{query}" if query else ""
                    return f"{parsed_url.scheme}://{parsed_url.netloc}{new_path}{query_part}"
        
        # Look for a number at the end of the URL that might be a page number
        if path.endswith("/"):
            path = path[:-1]
        
        match = re.search(r'/(\d+)/?$', path)
        if match and not re.search(r'\d{4}', match.group(1)):  # Avoid matching years
            page_number = match.group(1)
            new_path = path.replace(f"/{page_number}", f"/{current_page_num + 1}")
            query_part = f"?{query}" if query else ""
            return f"{parsed_url.scheme}://{parsed_url.netloc}{new_path}/{query_part}"
        
        # Try appending common pagination patterns
        for pattern in ["?page={0}", "/page/{0}/", "?p={0}", "/p/{0}/", "?pg={0}"]:
            # Only append if it doesn't already exist
            if pattern.format(current_page_num) not in current_url:
                if "?" in pattern and "?" in current_url:
                    next_url = f"{current_url}&{pattern[1:].format(current_page_num + 1)}"
                else:
                    next_url = f"{current_url}{pattern.format(current_page_num + 1)}"
                return next_url
        
        # No pagination pattern could be inferred
        return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse price text to extract numeric value.
        Args:
            price_text: String containing price information
        Returns:
            Parsed price as float or None if parsing fails
        """
        if not price_text:
            return None
        try:
            cleaned_text = re.sub(r'(?:[£$€]|(?:[Ss]ale)|(?:[Ff]rom)|(?:[Nn]ow:?))\s*', '', price_text).strip()
            match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)', cleaned_text)
            if match:
                price_str = match.group(1)
                if ',' in price_str and '.' not in price_str:
                    price_str = price_str.replace(',', '.')
                elif ',' in price_str and '.' in price_str:
                    if price_str.rfind(',') > price_str.rfind('.'):
                        price_str = price_str.replace('.', '').replace(',', '.')
                    else:
                        price_str = price_str.replace(',', '')
                return float(price_str)
            log.warning(f"No numeric price found in: '{price_text}'")
            return None
        except Exception as e:
            log.warning(f"Error parsing price '{price_text}': {e}")
            try:
                numbers = re.findall(r'\d+\.\d+|\d+\,\d+|\d+', price_text)
                if numbers:
                    return float(numbers[0].replace(',', '.'))
            except:
                pass
            return None

    async def close_session(self):
        """
        Close the aiohttp session gracefully.
        """
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None




async def test_scraper():
    """Test the scraper on a sample URL and save results to OUTPUTS directory."""
    # Setup output directory
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "OUTPUTS", "supplier_data")
    os.makedirs(outputs_dir, exist_ok=True)
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    ai_client = None
    
    try:
        from openai import OpenAI
        ai_client = OpenAI(api_key=openai_api_key)
        print("OpenAI client initialized")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
    
    scraper = ConfigurableSupplierScraper(ai_client=ai_client)
    test_url = "https://www.clearance-king.co.uk/pound-lines.html"
    base_url = "https://www.clearance-king.co.uk"
    
    html = await scraper.get_page_content(test_url)
    if html:
        print(f"Successfully fetched page content ({len(html)} bytes)")
        product_elements = scraper.extract_product_elements(html, test_url)
        print(f"Found {len(product_elements)} product elements")
        
        products_data = []
        
        if product_elements:
            # Test with the first 5 products
            for i, p_soup in enumerate(product_elements[:5]):
                if i >= 5:
                    break
                    
                p_html = str(p_soup)
                title = await scraper.extract_title(p_soup, p_html, test_url)
                price = await scraper.extract_price(p_soup, p_html, test_url)
                url = await scraper.extract_url(p_soup, p_html, test_url, base_url)
                image = await scraper.extract_image(p_soup, p_html, test_url, base_url)
                
                product_data = {
                    "id": i + 1,
                    "title": title,
                    "price": price,
                    "url": url,
                    "image": image,
                    "source_url": test_url,
                    "timestamp": datetime.now().isoformat()
                }
                
                products_data.append(product_data)
                
                print(f"\nProduct {i+1}:")
                print(f"Title: {title}")
                print(f"Price: {price}")
                print(f"URL: {url}")
                print(f"Image: {image}")
            
            # Save to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(outputs_dir, f"clearance_king_test_{timestamp}.json")
            
            output_data = {
                "source": "clearance-king.co.uk",
                "url": test_url,
                "extraction_time": datetime.now().isoformat(),
                "total_products": len(products_data),
                "products": products_data
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Saved {len(products_data)} products to: {output_file}")
            
            # Test pagination
            soup = BeautifulSoup(html, 'html.parser')
            next_page_url = scraper.get_next_page_url(test_url, soup, 1)
            print(f"\nNext page URL: {next_page_url}")
            
            if next_page_url:
                # Verify the next page exists
                next_page_html = await scraper.get_page_content(next_page_url)
                if next_page_html:
                    print(f"✅ Successfully verified next page content ({len(next_page_html)} bytes)")
                    next_page_soup = BeautifulSoup(next_page_html, 'html.parser')
                    next_next_page_url = scraper.get_next_page_url(next_page_url, next_page_soup, 2)
                    print(f"Next next page URL: {next_next_page_url}")
                else:
                    print("❌ Failed to fetch next page content")
            else:
                print("⚠️ No next page URL found")
        else:
            print("❌ No products found.")
    else:
        print("❌ Failed to fetch page content.")
    
    await scraper.close_session()
    return len(products_data) if 'products_data' in locals() else 0


if __name__ == "__main__":
    print("="*80)
    print("ConfigurableSupplierScraper Test")
    print("="*80)
    asyncio.run(test_scraper())