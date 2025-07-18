
"""
WebScraper class for the passive extraction workflow.
Provides methods for extracting data from supplier websites like clearance-king.co.uk.
Integrates AI fallbacks for selector failures and features optimized HTML parsing.
MODIFIED: Enhanced EAN extraction and added JSON output to test_scraper.
FIXED: Malformed image selector.
"""

import os
import logging
import aiohttp
import re
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple
from bs4 import BeautifulSoup, Tag

# ADDED for test_scraper output
import json
from urllib.parse import urlparse # For deriving supplier name in test_scraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Constants
OPENAI_MODEL_NAME_DEFAULT = "gpt-4.1-mini-2025-04-14"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
REQUEST_TIMEOUT = 30  # seconds


class WebScraper:
    """
    Web scraper for extracting data from supplier websites.
    Prioritizes selector-based extraction, with AI-powered fallbacks.
    Features include optimized parsing, robust error handling, and flexible selectors.
    """
    
    def __init__(self, ai_client: Optional[Any] = None, openai_model_name: str = OPENAI_MODEL_NAME_DEFAULT):
        """
        Initialize the web scraper.
        
        Args:
            ai_client: An initialized OpenAI client (or compatible)
            openai_model_name: The model name to use for AI operations
        """
        self.session: Optional[aiohttp.ClientSession] = None
        self.ai_client = ai_client
        self.openai_model = openai_model_name
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # Default 1 second between requests

        # Selectors dictionary with site-specific configurations
        self.selector_config = {
            # clearance-king.co.uk specific selectors
            "clearance-king.co.uk": {
                "product": "li.item.product.product-item",
                "title": "a.product-item-link",
                "price": "span.price",
                "url": "a.product-item-link",
                "image": "img.product-image-photo", # This is an <img> tag selector
                "ean_detail_page": [
                    "div.product-info-main div.value[itemprop='gtin13']", 
                    "div.product-info-main div.product.attribute.sku div.value[itemprop='sku']", 
                    "span.ck-b-code-value", 
                    "table.additional-attributes-table td[data-th='EAN']",
                    "table.additional-attributes-table td[data-th='Barcode']",
                    ".product-info-main *:contains('EAN:') + *",
                    ".product-info-main *:contains('Barcode:') + *",
                    ".product-info-main *:contains('EAN:')", 
                    ".product-info-main *:contains('Barcode:')",
                ]
            },
            # Default selectors for any site
            "default": {
                "product": [
                    ".products .product", ".product-grid .product", ".product-list .product-item",
                    ".product-container", ".category-products .item", ".item-grid .item-box",
                    ".product-layout", "article.product", "[data-test='product-grid'] > div",
                    ".grid__item--collection-template", ".product-card", ".ProductItem"
                ],
                "title": [
                    ".product-title", ".product-name", "h2", "h3", "h4", ".card-title", 
                    "[class*='title']", "[class*='name']", "a[title]", ".product-info a"
                ],
                "price": [
                    ".price", ".product-price", ".price-box", "[class*='price']", 
                    ".card-text", ".amount", "[data-price]", "[itemprop='price']"
                ],
                "url": ["a[href]"],
                # FIXED: Image selectors should target <img> tags or <source> tags within <picture>
                "image": [
                    "img",  # General img tag
                    "img[data-src]", # Img tag with data-src
                    "[class*='image'] img", # Img tag within an element with class containing 'image'
                    "[class*='thumb'] img", # Img tag within an element with class containing 'thumb'
                    "picture > source", # Source tag directly under a picture tag (will get srcset)
                    "picture img" # Fallback img tag within a picture element
                ],
                "ean_detail_page": [ 
                    "[itemprop='gtin13']", "[itemprop='gtin12']", "[itemprop='sku']",
                    "*:contains('EAN:') + *", "*:contains('Barcode:') + *",
                    "*:contains('GTIN:') + *", "*:contains('UPC:') + *",
                    "*:contains('EAN:')", "*:contains('Barcode:')",
                    "*:contains('GTIN:')", "*:contains('UPC:')",
                    ".product-ean", ".product-barcode", ".product-gtin"
                ]
            }
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
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
        session = await self._get_session()
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request)
        self.last_request_time = time.time()
        
        for attempt in range(retry_count):
            try:
                log.info(f"Fetching page content from: {url} (attempt {attempt+1}/{retry_count})")
                async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 5))
                        log.warning(f"Rate limited (429). Waiting {retry_after}s before retry.")
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    html_content = await response.text()
                    if not html_content or len(html_content) < 1000:
                        soup_check = BeautifulSoup(html_content, 'html.parser')
                        if not soup_check.find('html') or not soup_check.find('body'):
                            log.warning(f"Response from {url} doesn't appear to be valid HTML (Size: {len(html_content)} bytes). Retrying.")
                            await asyncio.sleep(2 * (attempt + 1))
                            continue
                    log.info(f"Successfully fetched content from {url} (Size: {len(html_content)} bytes)")
                    return html_content
            except aiohttp.ClientError as e:
                log.error(f"AIOHTTP client error fetching {url} (attempt {attempt+1}): {e}")
            except asyncio.TimeoutError:
                log.error(f"Timeout error fetching {url} (attempt {attempt+1})")
            except Exception as e:
                log.error(f"Unexpected error fetching {url} (attempt {attempt+1}): {e}")
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt + 1
                log.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        log.error(f"Failed to fetch {url} after {retry_count} attempts.")
        return None

    def _get_selectors_for_domain(self, url: str) -> Dict[str, Any]:
        try:
            domain = urlparse(url).netloc.lower().replace("www.", "")
            for known_domain_key, config_value in self.selector_config.items():
                if known_domain_key != "default" and (domain == known_domain_key or known_domain_key in domain):
                    merged_config = self.selector_config["default"].copy()
                    merged_config.update(config_value)
                    return merged_config
            return self.selector_config["default"]
        except Exception as e:
            log.error(f"Error determining selectors for domain from URL '{url}': {e}")
            return self.selector_config["default"]

    def extract_product_elements(self, html: str, url: str) -> List[BeautifulSoup]:
        soup = BeautifulSoup(html, 'html.parser')
        selectors_config = self._get_selectors_for_domain(url)
        product_selectors = selectors_config.get("product", [])
        if isinstance(product_selectors, str):
            product_selectors = [product_selectors]
        
        for selector in product_selectors:
            try:
                # Ensure selector is not empty or just whitespace
                if selector and selector.strip():
                    elements = soup.select(selector)
                    if elements:
                        log.info(f"Found {len(elements)} product elements on {url} using selector: '{selector}'")
                        return elements
                else:
                    log.warning(f"Skipping empty or invalid product selector for {url}")
            except Exception as e:
                log.error(f"Error with product selector '{selector}' on {url}: {e}")
                continue
        
        log.warning(f"No product elements found with configured selectors on {url}. Trying generic approaches.")
        potential_containers = soup.select("div.products, div.product-list, ul.products, div.collection, section.products")
        for container in potential_containers:
            child_items = container.find_all(["div", "li", "article"], recursive=False)
            if len(child_items) > 3:
                log.info(f"Found {len(child_items)} potential product elements using container approach.")
                return child_items
            deeper_items = container.find_all(["div", "li", "article"], recursive=True, limit=30)
            if len(deeper_items) > 3:
                log.info(f"Found {len(deeper_items)} potential product elements using deeper container scan.")
                return deeper_items
        
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
        if not isinstance(selectors, list):
            selectors = [str(selectors)] if selectors else []
            
        for selector in selectors:
            try:
                # Ensure selector is not empty or just whitespace before passing to select_one
                if not selector or not selector.strip():
                    log.debug(f"Skipping empty selector.")
                    continue

                target = element_soup.select_one(selector)
                if target:
                    if attribute:
                        attr_value = target.get(attribute)
                        if attr_value is not None:
                            return str(attr_value).strip()
                    elif extract_text:
                        texts = [t.strip() for t in target.find_all(string=True, recursive=True) if t.strip()]
                        text_content = " ".join(texts)
                        if text_content: 
                            return re.sub(r'\s+', ' ', text_content).strip()
            except Exception as e: # Catch soupsieve errors here too
                log.debug(f"Error with selector '{selector}': {e}")
                continue
        return None

    async def _ai_extract_field_from_html_element(self, element_html: str, field_description: str, context_url: str) -> Optional[str]:
        if not self.ai_client:
            log.warning(f"AI client not available. Cannot extract '{field_description}' from HTML element on {context_url}.")
            return None
        try:
            max_html_len = 8000
            truncated_html = element_html[:max_html_len]
            if len(element_html) > max_html_len:
                truncated_html += "... [HTML truncated]"
            prompt = (
                f"You are an expert web data extractor. From the following HTML snippet of a product item on the webpage {context_url}, "
                f"extract the '{field_description}'. Provide only the extracted value itself with no additional explanation, labels, or commentary. "
                f"If the value is not found, respond with 'NOT_FOUND'.\n\n"
                f"HTML Snippet:\n{truncated_html}"
            )
            response = await asyncio.to_thread(
                 self.ai_client.chat.completions.create,
                 model=self.openai_model,
                 messages=[{"role": "user", "content": prompt}],
                 temperature=0.0,
                 max_tokens=150
            )
            extracted_value = response.choices[0].message.content.strip()
            if extracted_value.upper() in ["NOT_FOUND", "NOT FOUND", "NONE", "N/A", "NO VALUE FOUND", "NO DATA FOUND", ""]:
                log.info(f"AI indicated '{field_description}' was not found on {context_url}.")
                return None
            log.info(f"AI extracted '{field_description}' on {context_url}: '{extracted_value[:60]}...'")
            return extracted_value
        except Exception as e:
            log.error(f"AI HTML element extraction for '{field_description}' on {context_url} failed: {e}")
            return None

    async def extract_title(self, element_soup: BeautifulSoup, element_html: str, context_url: str) -> Optional[str]:
        selectors_config = self._get_selectors_for_domain(context_url)
        title_selectors = selectors_config.get("title", [])
        title = self._extract_with_selector(element_soup, title_selectors)
        if not title:
            for attr_name in ['title', 'alt']:
                if element_soup.has_attr(attr_name):
                    title = element_soup[attr_name]
                    if title: break
            if not title:
                for tag_name in ['h1', 'h2', 'h3', 'a']:
                    found_tag = element_soup.find(tag_name)
                    if found_tag:
                        title_text = found_tag.get_text(strip=True)
                        if title_text:
                            title = title_text
                            break
        if title:
            title = re.sub(r'\s+', ' ', title).strip()
            if len(title) < 5 and not any(char.isdigit() for char in title): 
                title = None 
        if title: return title
        log.warning(f"Failed to extract title with selectors/heuristics from element on {context_url}. Attempting AI fallback.")
        return await self._ai_extract_field_from_html_element(element_html, "product title", context_url)

    async def extract_price(self, element_soup: BeautifulSoup, element_html: str, context_url: str) -> Optional[float]:
        selectors_config = self._get_selectors_for_domain(context_url)
        price_selectors = selectors_config.get("price", [])
        price_str = self._extract_with_selector(element_soup, price_selectors)
        if not price_str:
            price_meta = element_soup.select_one('[itemprop="price"], [data-price]')
            if price_meta:
                price_str = price_meta.get('content') or price_meta.get('data-price') or price_meta.get_text(strip=True)
        if price_str:
            parsed_price = self._parse_price(price_str)
            if parsed_price is not None and parsed_price > 0:
                return parsed_price
        log.warning(f"Failed to extract/parse price with selectors/heuristics from element on {context_url}. Attempting AI fallback.")
        ai_price_str = await self._ai_extract_field_from_html_element(element_html, "product price (numerical value only, e.g., 10.99)", context_url)
        if ai_price_str:
            return self._parse_price(ai_price_str)
        return None

    async def extract_url(self, element_soup: BeautifulSoup, element_html: str, context_url: str, base_url: str) -> Optional[str]:
        selectors_config = self._get_selectors_for_domain(context_url)
        url_selectors = selectors_config.get("url", [])
        url_path = self._extract_with_selector(element_soup, url_selectors, attribute='href')
        if not url_path:
            anchor_tag = element_soup.find("a", href=True)
            if anchor_tag:
                url_path = anchor_tag.get('href')
            elif element_soup.name == 'a' and element_soup.has_attr('href'):
                url_path = element_soup.get('href')
        if url_path:
            return self._ensure_absolute_url(url_path, base_url)
        log.warning(f"Failed to extract URL with selectors/heuristics from element on {context_url}. Attempting AI fallback.")
        ai_url = await self._ai_extract_field_from_html_element(element_html, "product page URL (the 'href' attribute of the main link to the product)", context_url)
        if ai_url:
            return self._ensure_absolute_url(ai_url, base_url)
        return None

    def _ensure_absolute_url(self, url: str, base_url: str) -> str:
        from urllib.parse import urljoin
        url = url.strip()
        if not base_url:
            log.warning("Base URL is empty, cannot ensure absolute URL properly.")
            return url
        return urljoin(base_url, url)

    async def extract_image(self, element_soup: BeautifulSoup, element_html: str, context_url: str, base_url: str) -> Optional[str]:
        selectors_config = self._get_selectors_for_domain(context_url)
        image_selectors = selectors_config.get("image", []) # This is a list of selectors
        
        img_src = None
        preferred_attrs = ['data-src', 'src', 'data-lazy', 'data-original', 'data-srcset', 'srcset']

        for selector_str in image_selectors:
            # Ensure selector_str is a valid, non-empty string
            if not selector_str or not selector_str.strip():
                log.debug(f"Skipping empty or invalid image selector: '{selector_str}'")
                continue
            try:
                target_tag = element_soup.select_one(selector_str)
                if target_tag:
                    # If the selector targets a <source> tag, prefer srcset
                    if target_tag.name == 'source':
                        src_candidate = target_tag.get('srcset') or target_tag.get('data-srcset')
                        if src_candidate:
                            # Take the first URL from srcset
                            img_src = src_candidate.split(',')[0].strip().split(' ')[0]
                            if img_src and not img_src.startswith('data:'): break 
                    else: # For <img> tags or other elements
                        for attr in preferred_attrs:
                            if target_tag.has_attr(attr):
                                src_candidate = target_tag[attr]
                                if attr in ['data-srcset', 'srcset'] and src_candidate:
                                    src_candidate = src_candidate.split(',')[0].strip().split(' ')[0]
                                if src_candidate and not src_candidate.startswith('data:'):
                                    img_src = src_candidate
                                    break # Found a good src from this tag
                        if img_src: break # Found a good src, no need to check other selectors
            except Exception as e:
                log.debug(f"Error applying image selector '{selector_str}': {e}")
                continue
        
        # Fallback: if selectors didn't yield, find any img tag directly
        if not img_src:
            images = element_soup.find_all("img")
            for img_tag_fallback in images:
                for attr in preferred_attrs:
                    if img_tag_fallback.has_attr(attr):
                        src_candidate = img_tag_fallback[attr]
                        if attr in ['data-srcset', 'srcset'] and src_candidate:
                             src_candidate = src_candidate.split(',')[0].strip().split(' ')[0]
                        if src_candidate and not src_candidate.startswith('data:'):
                            img_src = src_candidate
                            break
                if img_src: break
        
        if img_src:
            if img_src.startswith('data:'):
                log.debug(f"Found data: image URL on {context_url}, skipping.")
                return None
            return self._ensure_absolute_url(img_src, base_url)

        log.warning(f"Failed to extract image URL with selectors/heuristics from element on {context_url}. Attempting AI fallback.")
        ai_img_src = await self._ai_extract_field_from_html_element(element_html, "product image source URL (src, data-src, or srcset attribute of the main product image tag or picture source tag)", context_url)
        
        if ai_img_src and not ai_img_src.startswith('data:'):
            return self._ensure_absolute_url(ai_img_src, base_url)
        return None

    def _validate_ean(self, ean_text: Optional[str]) -> bool:
        if not ean_text: return False
        cleaned_ean = re.sub(r'[^\d]', '', str(ean_text).strip())
        if len(cleaned_ean) in [8, 12, 13, 14]:
            if len(set(cleaned_ean)) > 1 and not cleaned_ean.startswith("000000"): 
                return True
        return False

    def _find_ean_in_text_content(self, soup: BeautifulSoup, product_url: str) -> Optional[str]:
        log.debug(f"Attempting text-based EAN search for {product_url}")
        ean_patterns = [
            re.compile(r'(?:EAN|Barcode|GTIN|UPC)\s*[:\-]?\s*(\d{8,14})\b', re.IGNORECASE),
            re.compile(r'\b(?:Barcode|EAN|GTIN|UPC)\s+(\d{8,14})\b', re.IGNORECASE),
        ]
        for prop in ['gtin13', 'gtin12', 'gtin8', 'sku', 'productID']:
            elements = soup.select(f'[itemprop="{prop}"]')
            for el in elements:
                val = el.get('content') or el.get_text(strip=True)
                if self._validate_ean(val):
                    log.info(f"EAN found via itemprop='{prop}': {re.sub(r'[^\d]', '', val)} on {product_url}")
                    return re.sub(r'[^\d]', '', val)
        all_text_nodes_content = " ".join(t.strip() for t in soup.find_all(string=True, recursive=True) if t.strip() and t.parent.name not in ['script', 'style', 'noscript', 'a', 'button'])
        for pattern in ean_patterns:
            matches = pattern.findall(all_text_nodes_content)
            for match_group in matches:
                ean_candidate = match_group if isinstance(match_group, str) else (match_group[0] if isinstance(match_group, tuple) and len(match_group) > 0 else None)
                if ean_candidate and self._validate_ean(ean_candidate):
                    numeric_ean = re.sub(r'[^\d]', '', ean_candidate)
                    log.info(f"EAN found via text pattern '{pattern.pattern}': {numeric_ean} on {product_url}")
                    return numeric_ean
        candidate_tags = soup.find_all(['dd', 'span', 'div', 'td', 'p', 'li'])
        for tag in candidate_tags:
            if len(tag.find_all(recursive=False)) < 2 and len(tag.get_text(strip=True)) < 30:
                text_val = tag.get_text(strip=True)
                cleaned_text_val = re.sub(r'^(barcode|ean|gtin|upc)\s*[:\-]?\s*', '', text_val, flags=re.IGNORECASE).strip()
                if self._validate_ean(cleaned_text_val):
                    numeric_ean = re.sub(r'[^\d]', '', cleaned_text_val)
                    log.info(f"EAN found via standalone number in tag <{tag.name}>: {numeric_ean} on {product_url}")
                    return numeric_ean
        log.debug(f"No EAN found via advanced text search on {product_url}")
        return None

    async def extract_ean_from_product_page(self, product_url: str, context_url: str) -> Optional[str]:
        html = await self.get_page_content(product_url)
        if not html:
            log.warning(f"Could not fetch product page for EAN extraction: {product_url}")
            return None
        soup = BeautifulSoup(html, 'html.parser')
        selectors_config = self._get_selectors_for_domain(context_url)
        ean_selectors = selectors_config.get("ean_detail_page", [])
        if isinstance(ean_selectors, str): ean_selectors = [ean_selectors]

        for selector in ean_selectors:
            # Ensure selector is not empty or just whitespace
            if not selector or not selector.strip():
                log.debug(f"Skipping empty EAN selector: '{selector}'")
                continue
            try:
                ean_text = self._extract_with_selector(soup, [selector])
                if ean_text and self._validate_ean(ean_text):
                    numeric_ean = re.sub(r'[^\d]', '', ean_text.strip())
                    log.info(f"EAN found: {numeric_ean} using selector: '{selector}' on {product_url}")
                    return numeric_ean
            except Exception as e:
                 log.debug(f"Error with EAN selector '{selector}': {e}")
        
        log.debug(f"EAN not found with specific selectors on {product_url}. Attempting generic text search.")
        ean_from_text_search = self._find_ean_in_text_content(soup, product_url)
        if ean_from_text_search:
            log.info(f"EAN found via generic text search: {ean_from_text_search} on {product_url}")
            return ean_from_text_search

        if self.ai_client:
            log.warning(f"EAN not found with selectors or text search on {product_url}. Attempting AI fallback.")
            ai_ean_text = await self._ai_extract_field_from_html_element(
                html[:15000],
                "the product's EAN, Barcode, GTIN, or UPC number (typically 8, 12, 13, or 14 digits). Look for labels like 'EAN:', 'Barcode:'. Only return the numeric value.",
                product_url
            )
            if ai_ean_text and self._validate_ean(ai_ean_text):
                numeric_ean = re.sub(r'[^\d]', '', ai_ean_text.strip())
                log.info(f"EAN found via AI: {numeric_ean} on {product_url}")
                return numeric_ean
        
        log.warning(f"No valid EAN found on product page: {product_url} after all methods.")
        return None

    def _get_domain_specific_ean_selectors(self, url: str) -> List[str]: # Keep for now if anything relies on it
        log.warning("_get_domain_specific_ean_selectors is deprecated. Use 'ean_detail_page' in config.")
        selectors_config = self._get_selectors_for_domain(url)
        return selectors_config.get("ean_detail_page", [])

    def _parse_price(self, price_text: Optional[str]) -> Optional[float]:
        if not price_text: return None
        cleaned_price_text = str(price_text)
        cleaned_price_text = re.sub(r'(?:[£$€]|(?:[Ss]ale)|(?:[Ff]rom)|(?:[Nn]ow:?))\s*', '', cleaned_price_text).strip()
        match = re.search(r'(\d{1,3}(?:[,.]\d{3})*[.,]\d{2}|\d+[.,]\d{2}|\d+)', cleaned_price_text) # Simpler, allow . or , as decimal
        if match:
            price_str = match.group(1)
            # Normalize: remove thousands separators, ensure . is decimal
            price_str_no_thousands = price_str.replace(',', '') if '.' in price_str else price_str.replace('.', '')
            if ',' in price_str and '.' not in price_str : # Handles "12,34" as "12.34"
                 price_str_final = price_str.replace(',', '.')
            elif '.' in price_str and ',' in price_str : # Handles "1.234,56" and "1,234.56"
                if price_str.rfind(',') > price_str.rfind('.'): # 1.234,56 -> 1234.56
                    price_str_final = price_str.replace('.', '').replace(',', '.')
                else: # 1,234.56 -> 1234.56
                    price_str_final = price_str.replace(',', '')
            else: # Handles "1234.56" or "1234"
                price_str_final = price_str

            try:
                return float(price_str_final)
            except ValueError:
                log.warning(f"Could not parse price string: '{price_str_final}' from original '{price_text}'")
                return None
        return None

    async def extract_complete_product_data(self, product_urls: List[str], base_url: str, include_ean: bool = True) -> List[Dict[str, Any]]:
        complete_products = []
        for i, product_url in enumerate(product_urls):
            log.info(f"Processing product {i+1}/{len(product_urls)}: {product_url}")
            try:
                html = await self.get_page_content(product_url)
                if not html:
                    log.warning(f"Could not fetch product page: {product_url}, skipping.")
                    continue
                soup = BeautifulSoup(html, 'html.parser')
                context_url_for_detail = product_url 
                product_data: Dict[str, Any] = {
                    "url": product_url, "extraction_timestamp": datetime.now().isoformat(),
                    "title": None, "price": None, "image_url": None, "ean": None,
                    "brand": None, "description": None, "features": None,
                    "upc": None, "sku": None
                }
                product_data["title"] = await self.extract_title(soup, html, context_url_for_detail)
                product_data["price"] = await self.extract_price(soup, html, context_url_for_detail)
                product_data["image_url"] = await self.extract_image(soup, html, context_url_for_detail, base_url) # This was the error line
                if include_ean:
                    product_data["ean"] = await self.extract_ean_from_product_page(product_url, context_url_for_detail)
                
                domain_config = self._get_selectors_for_domain(product_url)
                if "clearance-king.co.uk" in urlparse(product_url).netloc.lower():
                    brand_selectors = domain_config.get("brand_selector_detail_page", domain_config.get("brand_selector", [".product.attribute.brand .value", ".product-brand a"]))
                    product_data["brand"] = self._extract_with_selector(soup, brand_selectors)
                    desc_selectors = domain_config.get("description_selector_detail_page", domain_config.get("description_selector", [".product.attribute.description .value", "#description .std"]))
                    product_data["description"] = self._extract_with_selector(soup, desc_selectors)
                    features_list_selector = domain_config.get("features_list_selector_detail_page", ".product.attributes .additional-attributes li")
                    features_elements = soup.select(features_list_selector)
                    if features_elements:
                        product_data["features"] = [elem.get_text(strip=True) for elem in features_elements if elem.get_text(strip=True)]
                
                if product_data.get("title") or product_data.get("ean"):
                    complete_products.append(product_data)
                    log.info(f"Successfully extracted data for: {product_data.get('title', 'N/A')[:50]}... (EAN: {product_data.get('ean', 'N/A')})")
                else:
                    log.warning(f"No meaningful data (title or EAN) extracted from: {product_url}")
                await asyncio.sleep(self.rate_limit_delay)
            except Exception as e:
                log.error(f"Error processing product {product_url}: {e}", exc_info=True)
                continue
        log.info(f"Successfully processed {len(complete_products)} out of {len(product_urls)} products for detailed extraction.")
        return complete_products

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
            log.info("AIOHTTP session closed.")
            self.session = None

async def test_scraper():
    openai_api_key = os.getenv("OPENAI_API_KEY")
    ai_client = None
    if openai_api_key:
        try:
            from openai import OpenAI
            ai_client = OpenAI(api_key=openai_api_key)
            print("OpenAI client initialized.")
        except ImportError:
            print("OpenAI library not installed. pip install openai.")
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
    else:
        print("OPENAI_API_KEY not set. AI fallbacks will not be available.")
    
    scraper = WebScraper(ai_client=ai_client)
    test_url = "https://www.clearance-king.co.uk/pound-lines.html"
    base_url = "https://www.clearance-king.co.uk"
    parsed_base_url = urlparse(base_url)
    supplier_name = parsed_base_url.netloc.replace("www.", "")
    output_dir_supplier = r"C:\Users\chris\Amazon-FBA-Agent-System\OUTPUTS\supplier_data"
    os.makedirs(output_dir_supplier, exist_ok=True)
    all_products_data_for_json = []

    try:
        html_category_page = await scraper.get_page_content(test_url)
        product_detail_urls = []
        if html_category_page:
            print(f"Successfully fetched category page content ({len(html_category_page)} bytes)") 
            product_elements = scraper.extract_product_elements(html_category_page, test_url)
            print(f"Found {len(product_elements)} product elements on category page.")
            for i, p_soup in enumerate(product_elements[:5]): 
                p_html = str(p_soup)
                item_url = await scraper.extract_url(p_soup, p_html, test_url, base_url)
                if item_url:
                    product_detail_urls.append(item_url)
                else:
                    log.warning(f"Could not extract URL for product element {i+1} on {test_url}")
            print(f"Extracted {len(product_detail_urls)} product detail URLs for testing.")
        else:
            print(f"Failed to fetch category page content from {test_url}.")
            return

        if product_detail_urls:
            extracted_details = await scraper.extract_complete_product_data(product_detail_urls, base_url, include_ean=True)
            for product_data in extracted_details:
                product_data["source_supplier"] = supplier_name
                product_data["source_category_url"] = test_url
                product_data.setdefault("upc", None)
                product_data.setdefault("sku", None)
                all_products_data_for_json.append(product_data)
            
            print(f"\n--- Detailed Extraction Results ({len(all_products_data_for_json)} products) ---")
            for i, data in enumerate(all_products_data_for_json):
                print(f"\nProduct {i+1}:")
                print(f"  Title: {data.get('title')}")
                print(f"  Price: {data.get('price')}")
                print(f"  URL: {data.get('url')}")
                print(f"  Image: {data.get('image_url')}")
                print(f"  EAN: {data.get('ean')}")
                print(f"  Brand: {data.get('brand')}")
        else:
            print("No product detail URLs were extracted to test detailed data extraction.")

        if all_products_data_for_json:
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{supplier_name.replace('.', '_')}_TEST_products_{timestamp_str}.json"
            output_filepath = os.path.join(output_dir_supplier, output_filename)
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_products_data_for_json, f, indent=2, ensure_ascii=False)
            print(f"\nSuccessfully saved {len(all_products_data_for_json)} products to {output_filepath}")
        else:
            print("\nNo product data collected to save.")
    except Exception as e:
        log.error(f"An error occurred during test_scraper: {e}", exc_info=True)
    finally:
        await scraper.close_session()

if __name__ == "__main__":
    print("="*80)
    print("WebScraper Test (with Enhanced EAN Extraction & JSON Output)")
    print("="*80)
    asyncio.run(test_scraper())

