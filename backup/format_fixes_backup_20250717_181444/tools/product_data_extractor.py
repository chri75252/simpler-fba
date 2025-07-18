#!/usr/bin/env python3
"""
Product Data Extractor for PoundWholesale
Extracts title, price, EAN/barcode via selectors only (no Vision)
Handles post-login price extraction and selector config management
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from bs4 import BeautifulSoup

# Add project paths
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.path_manager import path_manager

log = logging.getLogger(__name__)

class ProductDataExtractor:
    """Extract product data using selector-based approach"""
    
    # Selector patterns for product data extraction
    TITLE_SELECTORS = [
        'h1.product-title',
        'h1.entry-title',
        '.product-title',
        'h1.product-name',
        '.product-name',
        'h1',
        '.page-title'
    ]
    
    PRICE_SELECTORS = [
        '.price .amount',
        '.price-current',
        '.product-price .amount',
        '.woocommerce-Price-amount',
        '.price',
        '.product-price',
        '.current-price',
        '.sale-price',
        'span[class*="price"]'
    ]
    
    EAN_PATTERNS = [
        r'EAN[:\s]*([0-9]{8,14})',
        r'Barcode[:\s]*([0-9]{8,14})',
        r'UPC[:\s]*([0-9]{8,14})',
        r'GTIN[:\s]*([0-9]{8,14})',
        r'Product Code[:\s]*([0-9]{8,14})',
        r'SKU[:\s]*([A-Z0-9]{8,})',
        r'Item Code[:\s]*([0-9]{8,14})'
    ]
    
    META_SELECTORS = [
        'meta[name*="product"]',
        'meta[property*="product"]',
        'meta[name*="sku"]',
        'meta[name*="ean"]',
        'meta[name*="gtin"]'
    ]
    
    def __init__(self):
        """Initialize extractor"""
        self.extracted_data = {}
        self.selector_config = {
            "domain": "poundwholesale.co.uk",
            "name": "PoundWholesale",
            "extraction_timestamp": datetime.now().isoformat(),
            "selectors": {
                "product_title": [],
                "product_price": [],
                "product_ean": {
                    "meta_patterns": [],
                    "text_patterns": [],
                    "element_selectors": []
                }
            },
            "successful_extractions": []
        }
    
    async def extract_product_data(self, page, product_url: str) -> Dict[str, Any]:
        """Extract all product data from current page"""
        try:
            log.info(f"🔍 Extracting product data from: {product_url}")
            
            # Get page content
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Initialize result
            product_data = {
                'url': product_url,
                'title': '',
                'price': '',
                'ean': '',
                'barcode': '',
                'extraction_timestamp': datetime.now().isoformat(),
                'extraction_method': 'selectors_only',
                'successful_selectors': {}
            }
            
            # Extract title
            title_result = await self._extract_title(soup, page)
            product_data.update(title_result)
            
            # Extract price (post-login)
            price_result = await self._extract_price(soup, page)
            product_data.update(price_result)
            
            # Extract EAN/barcode
            ean_result = await self._extract_ean(soup, html_content)
            product_data.update(ean_result)
            
            # Update selector config with successful selectors
            self._update_selector_config(product_data)
            
            log.info("✅ Product data extraction completed")
            log.info(f"   - Title: {product_data['title']}")
            log.info(f"   - Price: {product_data['price']}")
            log.info(f"   - EAN: {product_data['ean']}")
            
            return product_data
            
        except Exception as e:
            log.error(f"❌ Product data extraction failed: {e}")
            return {
                'url': product_url,
                'error': str(e),
                'extraction_timestamp': datetime.now().isoformat()
            }
    
    async def _extract_title(self, soup: BeautifulSoup, page) -> Dict[str, Any]:
        """Extract product title using multiple selector strategies"""
        title_data = {'title': '', 'title_selector': ''}
        
        try:
            # Try each title selector
            for selector in self.TITLE_SELECTORS:
                try:
                    # Try BeautifulSoup first
                    element = soup.select_one(selector)
                    if element and element.get_text(strip=True):
                        title = element.get_text(strip=True)
                        # Validate title (avoid navigation elements, etc.)
                        if len(title) > 10 and not any(nav_word in title.lower() for nav_word in ['home', 'login', 'cart', 'menu']):
                            title_data['title'] = title
                            title_data['title_selector'] = selector
                            log.info(f"✅ Title found via selector '{selector}': {title[:50]}...")
                            break
                except Exception as e:
                    log.debug(f"Title selector '{selector}' failed: {e}")
            
            # If BeautifulSoup failed, try Playwright
            if not title_data['title']:
                for selector in self.TITLE_SELECTORS:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            title = await element.text_content()
                            if title and len(title.strip()) > 10:
                                title_data['title'] = title.strip()
                                title_data['title_selector'] = selector
                                log.info(f"✅ Title found via Playwright selector '{selector}': {title[:50]}...")
                                break
                    except Exception as e:
                        log.debug(f"Playwright title selector '{selector}' failed: {e}")
            
            if not title_data['title']:
                log.warning("❌ No title found with any selector")
            
        except Exception as e:
            log.error(f"Title extraction error: {e}")
        
        return title_data
    
    async def _extract_price(self, soup: BeautifulSoup, page) -> Dict[str, Any]:
        """Extract product price (should work post-login)"""
        price_data = {'price': '', 'price_selector': ''}
        
        try:
            # Try each price selector
            for selector in self.PRICE_SELECTORS:
                try:
                    # Try BeautifulSoup first
                    element = soup.select_one(selector)
                    if element:
                        price_text = element.get_text(strip=True)
                        # Look for price patterns (£, $, numbers)
                        if price_text and any(char in price_text for char in ['£', '$', '€']) and any(char.isdigit() for char in price_text):
                            # Clean up price text
                            price_clean = re.sub(r'[^\d.,£$€]', '', price_text)
                            if price_clean:
                                price_data['price'] = price_text
                                price_data['price_selector'] = selector
                                log.info(f"✅ Price found via selector '{selector}': {price_text}")
                                break
                except Exception as e:
                    log.debug(f"Price selector '{selector}' failed: {e}")
            
            # If BeautifulSoup failed, try Playwright
            if not price_data['price']:
                for selector in self.PRICE_SELECTORS:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            price_text = await element.text_content()
                            if price_text and any(char in price_text for char in ['£', '$', '€']) and any(char.isdigit() for char in price_text):
                                price_data['price'] = price_text.strip()
                                price_data['price_selector'] = selector
                                log.info(f"✅ Price found via Playwright selector '{selector}': {price_text}")
                                break
                    except Exception as e:
                        log.debug(f"Playwright price selector '{selector}' failed: {e}")
            
            # If no price found, might need login
            if not price_data['price']:
                # Look for "login to view price" text
                login_indicators = ['login to view', 'sign in to see', 'member price', 'wholesale price']
                page_text = soup.get_text().lower()
                
                if any(indicator in page_text for indicator in login_indicators):
                    price_data['price'] = 'Login required to view price'
                    log.warning("⚠️ Price requires login - user may need to complete login process")
                else:
                    price_data['price'] = 'Price not found'
                    log.warning("❌ No price found with any selector")
            
        except Exception as e:
            log.error(f"Price extraction error: {e}")
        
        return price_data
    
    async def _extract_ean(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Extract EAN/barcode using multiple strategies"""
        ean_data = {'ean': '', 'barcode': '', 'ean_method': ''}
        
        try:
            # Strategy 1: Search in meta tags
            for meta_element in soup.select('meta'):
                content = meta_element.get('content', '')
                name = meta_element.get('name', '')
                property_attr = meta_element.get('property', '')
                
                # Check meta content for EAN patterns
                for pattern in self.EAN_PATTERNS:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        ean_code = match.group(1)
                        if len(ean_code) >= 8:  # Valid EAN length
                            ean_data['ean'] = ean_code
                            ean_data['barcode'] = ean_code
                            ean_data['ean_method'] = f'meta_content_pattern_{pattern}'
                            log.info(f"✅ EAN found in meta content: {ean_code}")
                            return ean_data
                
                # Check meta name/property for EAN indicators
                if any(ean_term in (name + property_attr).lower() for ean_term in ['ean', 'gtin', 'upc', 'barcode']):
                    if content and content.isdigit() and len(content) >= 8:
                        ean_data['ean'] = content
                        ean_data['barcode'] = content
                        ean_data['ean_method'] = f'meta_attribute_{name or property_attr}'
                        log.info(f"✅ EAN found in meta attribute: {content}")
                        return ean_data
            
            # Strategy 2: Search in visible text
            page_text = soup.get_text()
            for pattern in self.EAN_PATTERNS:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    ean_code = match.group(1)
                    if len(ean_code) >= 8:
                        ean_data['ean'] = ean_code
                        ean_data['barcode'] = ean_code
                        ean_data['ean_method'] = f'text_pattern_{pattern}'
                        log.info(f"✅ EAN found in page text: {ean_code}")
                        return ean_data
            
            # Strategy 3: Search in HTML comments and data attributes
            html_lower = html_content.lower()
            for pattern in self.EAN_PATTERNS:
                match = re.search(pattern, html_lower, re.IGNORECASE)
                if match:
                    ean_code = match.group(1)
                    if len(ean_code) >= 8:
                        ean_data['ean'] = ean_code
                        ean_data['barcode'] = ean_code
                        ean_data['ean_method'] = f'html_source_pattern_{pattern}'
                        log.info(f"✅ EAN found in HTML source: {ean_code}")
                        return ean_data
            
            # Strategy 4: Look for structured data (JSON-LD)
            json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
            for script in json_ld_scripts:
                try:
                    json_data = json.loads(script.string)
                    # Look for product schema with identifiers
                    if isinstance(json_data, dict):
                        identifiers = json_data.get('identifier', [])
                        if not isinstance(identifiers, list):
                            identifiers = [identifiers]
                        
                        for identifier in identifiers:
                            if isinstance(identifier, dict):
                                value = identifier.get('value', '')
                                if value and value.isdigit() and len(value) >= 8:
                                    ean_data['ean'] = value
                                    ean_data['barcode'] = value
                                    ean_data['ean_method'] = 'json_ld_structured_data'
                                    log.info(f"✅ EAN found in JSON-LD: {value}")
                                    return ean_data
                except json.JSONDecodeError:
                    continue
            
            log.warning("❌ No EAN/barcode found with any method")
            
        except Exception as e:
            log.error(f"EAN extraction error: {e}")
        
        return ean_data
    
    def _update_selector_config(self, product_data: Dict[str, Any]):
        """Update selector configuration with successful selectors"""
        try:
            # Update title selectors
            if product_data.get('title_selector'):
                if product_data['title_selector'] not in self.selector_config['selectors']['product_title']:
                    self.selector_config['selectors']['product_title'].append(product_data['title_selector'])
            
            # Update price selectors
            if product_data.get('price_selector'):
                if product_data['price_selector'] not in self.selector_config['selectors']['product_price']:
                    self.selector_config['selectors']['product_price'].append(product_data['price_selector'])
            
            # Update EAN patterns
            if product_data.get('ean_method'):
                method = product_data['ean_method']
                if 'meta' in method:
                    if method not in self.selector_config['selectors']['product_ean']['meta_patterns']:
                        self.selector_config['selectors']['product_ean']['meta_patterns'].append(method)
                elif 'text' in method:
                    if method not in self.selector_config['selectors']['product_ean']['text_patterns']:
                        self.selector_config['selectors']['product_ean']['text_patterns'].append(method)
            
            # Record successful extraction
            extraction_record = {
                'url': product_data['url'],
                'timestamp': product_data['extraction_timestamp'],
                'title_found': bool(product_data.get('title')),
                'price_found': bool(product_data.get('price')) and 'not found' not in product_data.get('price', '').lower(),
                'ean_found': bool(product_data.get('ean'))
            }
            self.selector_config['successful_extractions'].append(extraction_record)
            
        except Exception as e:
            log.error(f"Failed to update selector config: {e}")
    
    def save_selector_config(self, config_path: Optional[Path] = None) -> str:
        """Save selector configuration to specified path"""
        try:
            if config_path is None:
                config_dir = Path("/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/config/supplier_configs")
                config_dir.mkdir(parents=True, exist_ok=True)
                config_path = config_dir / "poundwholesale-co-uk_selectors.json"
            
            # Load existing config if it exists
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                    
                    # Merge with existing config
                    for selector_type, selectors in self.selector_config['selectors'].items():
                        if selector_type in existing_config.get('selectors', {}):
                            if isinstance(selectors, list):
                                existing_selectors = existing_config['selectors'][selector_type]
                                if isinstance(existing_selectors, list):
                                    # Merge lists, avoiding duplicates
                                    combined = list(set(existing_selectors + selectors))
                                    existing_config['selectors'][selector_type] = combined
                            elif isinstance(selectors, dict):
                                existing_selectors = existing_config['selectors'][selector_type]
                                if isinstance(existing_selectors, dict):
                                    for key, values in selectors.items():
                                        if key in existing_selectors and isinstance(values, list):
                                            combined = list(set(existing_selectors[key] + values))
                                            existing_selectors[key] = combined
                                        else:
                                            existing_selectors[key] = values
                        else:
                            existing_config['selectors'][selector_type] = selectors
                    
                    # Update extraction records
                    existing_extractions = existing_config.get('successful_extractions', [])
                    existing_extractions.extend(self.selector_config['successful_extractions'])
                    existing_config['successful_extractions'] = existing_extractions
                    
                    # Update timestamp
                    existing_config['last_updated'] = datetime.now().isoformat()
                    
                    self.selector_config = existing_config
                    
                except Exception as e:
                    log.warning(f"Failed to load existing config, creating new one: {e}")
            
            # Save updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.selector_config, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ Selector config saved to: {config_path}")
            return str(config_path)
            
        except Exception as e:
            log.error(f"❌ Failed to save selector config: {e}")
            return ""

# Example usage
async def extract_product_example(page, product_url: str):
    """Example of product data extraction"""
    extractor = ProductDataExtractor()
    product_data = await extractor.extract_product_data(page, product_url)
    config_path = extractor.save_selector_config()
    
    return product_data, config_path