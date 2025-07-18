"""
Enhanced Data Extractor for Amazon FBA Agent System
Provides robust extraction methods for product data with improved accuracy and error handling.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup, Tag
import json

log = logging.getLogger(__name__)


class DataExtractor:
    """Enhanced data extraction utilities for product information."""
    
    def __init__(self):
        """Initialize the data extractor with common patterns."""
        # Price patterns for various formats
        self.price_patterns = [
            r'(?:£|$|€)\s*(\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{1,2})?)',
            r'(\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{1,2})?)\s*(?:£|$|€)',
            r'(?:GBP|USD|EUR)\s*(\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{1,2})?)',
            r'(\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{1,2})?)\s*(?:GBP|USD|EUR)',
        ]
        
        # Weight patterns
        self.weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*(kg|kilogram|kilo)',
            r'(\d+(?:\.\d+)?)\s*(g|gram)',
            r'(\d+(?:\.\d+)?)\s*(lb|lbs|pound)',
            r'(\d+(?:\.\d+)?)\s*(oz|ounce)',
        ]
        
        # Dimension patterns
        self.dimension_patterns = [
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(cm|mm|in|inch|inches)?',
            r'(\d+(?:\.\d+)?)\s*×\s*(\d+(?:\.\d+)?)\s*×\s*(\d+(?:\.\d+)?)\s*(cm|mm|in|inch|inches)?',
            r'L:\s*(\d+(?:\.\d+)?)\s*W:\s*(\d+(?:\.\d+)?)\s*H:\s*(\d+(?:\.\d+)?)\s*(cm|mm|in|inch|inches)?',
        ]
        
        # EAN/UPC/GTIN patterns
        self.identifier_patterns = [
            r'(?:EAN|ean)[\s:-]*(\d{13})',
            r'(?:UPC|upc)[\s:-]*(\d{12})',
            r'(?:GTIN|gtin)[\s:-]*(\d{8,14})',
            r'(?:Barcode|barcode)[\s:-]*(\d{8,14})',
            r'(?:ISBN|isbn)[\s:-]*(\d{10,13})',
            r'(?:ASIN|asin)[\s:-]*([A-Z0-9]{10})',
        ]

    def extract_price(self, text: str) -> Optional[float]:
        """
        Extract price from text with improved accuracy.
        
        Args:
            text: Text containing price information
            
        Returns:
            Extracted price as float or None
        """
        if not text:
            return None
            
        text = str(text).strip()
        
        # Look for "Now" price first (for "Was X Now Y" patterns)
        now_match = re.search(r'(?:Now|now)[\s:]*(?:£|$|€)?\s*(\d+(?:[.,]\d+)?)', text)
        if now_match:
            try:
                price_str = now_match.group(1).replace(',', '.')
                price = float(price_str)
                if 0.01 <= price <= 1000000:
                    return price
            except ValueError:
                pass
        
        # Try each price pattern
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    try:
                        # Clean the price string
                        price_str = match if isinstance(match, str) else match[0]
                        # Remove spaces used as thousand separators
                        price_str = price_str.replace(' ', '')
                        # Handle European vs US number formats
                        if ',' in price_str and '.' in price_str:
                            # Determine which is the decimal separator
                            if price_str.rfind(',') > price_str.rfind('.'):
                                # European format: 1.234,56
                                price_str = price_str.replace('.', '').replace(',', '.')
                            else:
                                # US format: 1,234.56
                                price_str = price_str.replace(',', '')
                        elif ',' in price_str:
                            # Could be either format
                            parts = price_str.split(',')
                            if len(parts) == 2 and len(parts[1]) <= 2:
                                # Likely European decimal: 123,45
                                price_str = price_str.replace(',', '.')
                            else:
                                # Likely thousand separator: 1,234
                                price_str = price_str.replace(',', '')
                        
                        price = float(price_str)
                        # Sanity check
                        if 0.01 <= price <= 1000000:
                            return price
                    except (ValueError, AttributeError):
                        continue
        
        # Fallback: try to extract any number
        numbers = re.findall(r'\d+(?:[.,]\d+)?', text)
        for num_str in numbers:
            try:
                price = float(num_str.replace(',', '.'))
                if 0.01 <= price <= 1000000:
                    return price
            except ValueError:
                continue
                
        return None

    def extract_weight(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract weight information from text.
        
        Args:
            text: Text containing weight information
            
        Returns:
            Dict with 'value' and 'unit' or None
        """
        if not text:
            return None
            
        text = str(text).lower().strip()
        
        for pattern in self.weight_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    unit = match.group(2)
                    return {
                        'value': value,
                        'unit': unit,
                        'pounds': self._convert_to_pounds(value, unit)
                    }
                except (ValueError, AttributeError):
                    continue
                    
        return None

    def extract_dimensions(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract dimension information from text.
        
        Args:
            text: Text containing dimension information
            
        Returns:
            Dict with length, width, height and unit or None
        """
        if not text:
            return None
            
        text = str(text).strip()
        
        for pattern in self.dimension_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    length = float(match.group(1))
                    width = float(match.group(2))
                    height = float(match.group(3))
                    unit = match.group(4) if len(match.groups()) >= 4 else 'cm'
                    
                    # Normalize unit name
                    if unit:
                        unit = unit.lower()
                        if unit == 'in':
                            unit = 'inches'
                    
                    return {
                        'length': length,
                        'width': width,
                        'height': height,
                        'unit': unit or 'cm',
                        'inches': self._convert_to_inches(length, width, height, unit)
                    }
                except (ValueError, AttributeError):
                    continue
                    
        return None

    def extract_identifiers(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract product identifiers (EAN, UPC, GTIN, etc.) from text.
        
        Args:
            text: Text containing identifier information
            
        Returns:
            Dict with found identifiers
        """
        identifiers = {
            'ean': None,
            'upc': None,
            'gtin': None,
            'isbn': None,
            'asin': None,
            'barcode': None
        }
        
        if not text:
            return identifiers
            
        text = str(text).strip()
        
        # Extract EAN
        ean_match = re.search(r'(?:EAN|ean)[\s:-]*(\d{13})', text)
        if ean_match and self._validate_ean(ean_match.group(1)):
            identifiers['ean'] = ean_match.group(1)
        
        # Extract UPC
        upc_match = re.search(r'(?:UPC|upc)[\s:-]*(\d{12})', text)
        if upc_match and self._validate_upc(upc_match.group(1)):
            identifiers['upc'] = upc_match.group(1)
        
        # Extract GTIN
        gtin_match = re.search(r'(?:GTIN|gtin)[\s:-]*(\d{8,14})', text)
        if gtin_match:
            identifiers['gtin'] = gtin_match.group(1)
        
        # Extract ISBN
        isbn_match = re.search(r'(?:ISBN|isbn)[\s:-]*(\d{10,13})', text)
        if isbn_match:
            identifiers['isbn'] = isbn_match.group(1)
        
        # Extract ASIN
        asin_match = re.search(r'(?:ASIN|asin)[\s:-]*([A-Z0-9]{10})', text, re.IGNORECASE)
        if asin_match:
            identifiers['asin'] = asin_match.group(1).upper()
        
        # Generic barcode
        if not any(identifiers.values()):
            barcode_match = re.search(r'(?:Barcode|barcode)[\s:-]*(\d{8,14})', text)
            if barcode_match:
                identifiers['barcode'] = barcode_match.group(1)
        
        return identifiers

    def extract_title(self, element: Any, fallback_text: str = "") -> str:
        """
        Extract and clean product title.
        
        Args:
            element: BeautifulSoup element or string
            fallback_text: Text to use if extraction fails
            
        Returns:
            Cleaned title string
        """
        title = ""
        
        if isinstance(element, Tag):
            # Try common title selectors, more specific first
            title_selectors = [
                'h1.product-title', 'h1[itemprop="name"]', 'h1.pdp-title', 'h1.product-name',
                'h1', 
                'h2.product-title', 'h2[itemprop="name"]',
                'h2',
                '.product-title', '.pdp-title', '.product-name', '.title', 
                '[itemprop="name"]',
                '[data-cy="product-title"]'
            ]
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title: # Found a non-empty title
                        break 
            
            if not title: # Fallback if no specific selector worked
                # Try to get text from the most prominent heading if no title found yet
                for heading_tag in ['h1', 'h2', 'h3']:
                    heading_elem = element.find(heading_tag)
                    if heading_elem:
                        title = heading_elem.get_text(strip=True)
                        if title:
                            break
                if not title:
                    title = element.get_text(strip=True) # Last resort for the element itself
        else:
            title = str(element).strip()
        
        if not title and fallback_text:
            title = fallback_text
        
        # Clean the title
        title = re.sub(r'\s+', ' ', title).strip() # Normalize whitespace
        
        # Remove common noise patterns more intelligently
        # Example: "Brand Name | Product Title Here" -> "Product Title Here"
        # Example: "Product Title Here - Site Name" -> "Product Title Here"
        # Example: "Product Title Here | Site Name" -> "Product Title Here"

        # Split by common separators and take the most likely part
        separators = ['|', ' - ', ' – ', ' :: ']
        best_part = title
        for sep in separators:
            if sep in title:
                parts = title.split(sep)
                # Heuristic: often the longest part is the title, or the first/last part if it's not a brand/site name
                # This can be made more sophisticated, e.g. by checking against known site names or brand lists
                
                # If "Brand | Title" or "Title | Brand/Site"
                if len(parts) == 2:
                    # Prefer part that doesn't look like a short brand/site name or a generic term
                    # This is a simple heuristic, could be improved
                    if len(parts[0]) > len(parts[1]) and len(parts[1]) < 15:
                        best_part = parts[0].strip()
                    elif len(parts[1]) > len(parts[0]) and len(parts[0]) < 15:
                        best_part = parts[1].strip()
                    else: # If lengths are similar or both parts are long, prefer the first
                        best_part = parts[0].strip() 
                    title = best_part # Update title with the best part found so far
                    break # Processed one separator type

        # Further noise removal
        noise_patterns = [
            r'(?i)^(buy|shop|purchase|get|new|genuine|official)\s+',  # Shopping prefixes
            r'(?i)\s+(online|store|shop|official site|website)$', # Shopping suffixes
            r'^\s*\d+\s*$',  # Just numbers
            r'^(Product Detail|Details|Overview|Features|Specs|Specifications)$' # Generic section headers
        ]
        
        for pattern in noise_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
        
        return title[:500]  # Limit length

    def extract_description(self, element: Any) -> str:
        """
        Extract and clean product description.
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            Cleaned description string
        """
        description = ""
        
        if isinstance(element, Tag):
            # Try common description selectors, more specific first
            desc_selectors = [
                '[itemprop="description"]',
                '#productDescription',  # Common ID
                'div[class*="product--description"]',
                'div[class*="product-description-container"]',
                'div.product-description',
                'div.description',
                'div.product-details-content',
                'div.pdp-description-content',
                'div[data-cy="product-description"]',
                'section[aria-labelledby*="description"]'
            ]
            
            for selector in desc_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem:
                    # Extract text, preserving some structure like paragraphs
                    parts = []
                    for child in desc_elem.find_all(['p', 'li', 'br'], recursive=False):
                        if child.name == 'br':
                            parts.append('\n')
                        else:
                            parts.append(child.get_text(strip=True))
                    if parts:
                        description = '\n'.join(part for part in parts if part.strip())
                    else:
                        description = desc_elem.get_text(separator='\n', strip=True)
                    
                    if description.strip(): # Found a non-empty description
                        break 
            
            if not description.strip():
                # Fallback: Look for paragraphs or divs that seem like descriptions
                # This is a heuristic and might grab unwanted text
                candidates = []
                for p_or_div in element.find_all(['p', 'div']):
                    # Avoid very short texts or texts that are clearly navigation/links
                    if len(p_or_div.find_all(['a', 'button', 'nav'])) > 2: # Too many links/buttons
                        continue
                    
                    text_content = p_or_div.get_text(strip=True)
                    if 50 < len(text_content) < 3000: # Reasonable length for a description paragraph
                        # Avoid if it's mostly just a few words repeated or looks like a menu
                        words = text_content.split()
                        if len(words) > 5 and len(set(words)) > len(words) / 3: # Basic check for variety
                             candidates.append(text_content)
                
                if candidates:
                    # Join the longest few candidates, prioritizing those not nested deep
                    candidates.sort(key=len, reverse=True)
                    description = "\n\n".join(candidates[:3]) # Take top 3 longest candidates

        # Clean the description
        description = re.sub(r'\s*\n\s*', '\n', description) # Normalize newlines
        description = re.sub(r'(\n){3,}', '\n\n', description) # Max 2 consecutive newlines
        description = re.sub(r'\s+', ' ', description.replace('\n', ' ')).strip() # Normalize spaces after newline processing for final cleanup
        
        # Remove common boilerplate
        boilerplate_patterns = [
            r'(?i)^description\s*[:\-]*\s*',
            r'(?i)^product details\s*[:\-]*\s*',
            r'(?i)^features\s*[:\-]*\s*',
            r'(?i)^specifications\s*[:\-]*\s*',
            r'(?i)read more\s*$',
            r'(?i)show less\s*$'
        ]
        for pattern in boilerplate_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE).strip()

        return description[:3000]  # Limit length

    def extract_images(self, element: Any, base_url: str = "") -> List[str]:
        """
        Extract product image URLs.
        
        Args:
            element: BeautifulSoup element
            base_url: Base URL for relative URLs
            
        Returns:
            List of image URLs
        """
        images = []
        
        if not isinstance(element, Tag):
            return images
        
        # Common image selectors
        img_selectors = [
            'img.product-image',
            'img[itemprop="image"]',
            '.product-images img',
            '.gallery img',
            'img[data-zoom-image]',
        ]
        
        for selector in img_selectors:
            img_elements = element.select(selector)
            for img in img_elements:
                src = img.get('src') or img.get('data-src') or img.get('data-zoom-image')
                if src:
                    # Make URL absolute
                    if base_url and not src.startswith(('http://', 'https://', '//')):
                        if src.startswith('/'):
                            from urllib.parse import urljoin
                            src = urljoin(base_url, src)
                        else:
                            src = base_url.rstrip('/') + '/' + src
                    elif src.startswith('//'):
                        src = 'https:' + src
                    
                    if src not in images:
                        images.append(src)
        
        # Fallback to any images
        if not images:
            all_images = element.find_all('img')
            for img in all_images[:10]:  # Limit to first 10
                src = img.get('src') or img.get('data-src')
                if src and not any(skip in src.lower() for skip in ['logo', 'icon', 'button', 'banner']):
                    if base_url and not src.startswith(('http://', 'https://', '//')):
                        from urllib.parse import urljoin
                        src = urljoin(base_url, src)
                    elif src.startswith('//'):
                        src = 'https:' + src
                    
                    if src not in images:
                        images.append(src)
        
        return images

    def _convert_to_pounds(self, value: float, unit: str) -> float:
        """Convert weight to pounds."""
        unit = unit.lower()
        if 'kg' in unit or 'kilo' in unit:
            return value * 2.20462
        elif 'g' in unit or 'gram' in unit:
            return value * 0.00220462
        elif 'oz' in unit or 'ounce' in unit:
            return value * 0.0625
        elif 'lb' in unit or 'pound' in unit:
            return value
        else:
            return value  # Assume pounds if unknown

    def _convert_to_inches(self, length: float, width: float, height: float, unit: Optional[str]) -> Tuple[float, float, float]:
        """Convert dimensions to inches."""
        if not unit:
            unit = 'cm'
        
        unit = unit.lower()
        if 'mm' in unit:
            factor = 0.0393701
        elif 'cm' in unit:
            factor = 0.393701
        elif 'in' in unit:
            factor = 1.0
        else:
            factor = 0.393701  # Assume cm if unknown
        
        return (length * factor, width * factor, height * factor)

    def _validate_ean(self, ean: str) -> bool:
        """Validate EAN-13 checksum."""
        if not ean or len(ean) != 13 or not ean.isdigit():
            return False
        
        try:
            # Calculate checksum
            total = sum(int(ean[i]) * (3 if i % 2 else 1) for i in range(12))
            check_digit = (10 - (total % 10)) % 10
            return check_digit == int(ean[12])
        except:
            return False

    def _validate_upc(self, upc: str) -> bool:
        """Validate UPC-A checksum."""
        if not upc or len(upc) != 12 or not upc.isdigit():
            return False
        
        try:
            # Calculate checksum - UPC uses odd positions * 3, even positions * 1
            total = sum(int(upc[i]) * (3 if i % 2 == 0 else 1) for i in range(11))
            check_digit = (10 - (total % 10)) % 10
            return check_digit == int(upc[11])
        except:
            return False

    def extract_brand(self, element: Any, text_content: str = "") -> Optional[str]:
        """Extract product brand."""
        brand = None
        if isinstance(element, Tag):
            brand_selectors = [
                '[itemprop="brand"] meta[content]', '[itemprop="brand"] span', '[itemprop="brand"]',
                '.product-brand a', '.product-brand', '.brand-name', '[data-brand]',
                'a[href*="/brand/"]', 'a[href*="/brands/"]',
                'img[alt*="brand logo"]', 'img[title*="brand logo"]' # Less reliable
            ]
            for selector in brand_selectors:
                brand_elem = element.select_one(selector)
                if brand_elem:
                    if brand_elem.name == 'meta' and brand_elem.has_attr('content'):
                        brand = brand_elem['content']
                    else:
                        brand = brand_elem.get_text(strip=True)
                    if brand: break
        
        if not brand and text_content:
            # Fallback to regex in text if not found via selectors
            # This is more prone to errors and should be used cautiously
            # Example: "Brand: SuperBrand", "Manufacturer: MegaCorp"
            brand_patterns_text = [
                r'(?i)(?:brand|manufacturer|make)\s*[:\-]\s*([A-Za-z0-9\s\-&]{2,50})(?:\n|<)', # Stop at newline or tag
                r'(?i)by\s+([A-Za-z0-9\s\-&]{2,50})(?:\n|<|\s+-)' # "by BrandName"
            ]
            for pattern in brand_patterns_text:
                match = re.search(pattern, text_content)
                if match:
                    brand = match.group(1).strip()
                    # Basic cleanup for common issues
                    if brand.lower() in ["brand", "manufacturer", "n/a", "unknown", "generic"]:
                        brand = None # Invalid brand name
                    else:
                        break
        
        if brand:
            # Further cleanup
            brand = re.sub(r'\s*\(.*?\)\s*$', '', brand) # Remove trailing (details)
            brand = brand.strip()
            if len(brand) > 100: # Unlikely to be a brand if too long
                return None
            return brand
        return None

    def extract_model_number(self, element: Any, text_content: str = "") -> Optional[str]:
        """Extract product model number (MPN, Part Number)."""
        model_no = None
        if isinstance(element, Tag):
            model_selectors = [
                '[itemprop="mpn"]', '[itemprop="model"]', '[itemprop="sku"]', # SKU can sometimes be model
                '.product-mpn', '.model-number', '.part-number',
                'dd.model', 'span.model', 'div[class*="model"]'
            ]
            for selector in model_selectors:
                model_elem = element.select_one(selector)
                if model_elem:
                    model_no = model_elem.get_text(strip=True)
                    if model_no: break
        
        if not model_no and text_content:
            # Fallback to regex in text
            model_patterns_text = [
                r'(?i)(?:model|mpn|part number|item code|sku|product code)\s*[:\-#]?\s*([A-Za-z0-9\-/.]{3,50})(?:\n|<|\s)',
                r'(?i)Item\s+[Mm]odel\s+[Nn]umber\s*[:\-#]?\s*([A-Za-z0-9\-/.]{3,50})'
            ]
            for pattern in model_patterns_text:
                match = re.search(pattern, text_content)
                if match:
                    candidate = match.group(1).strip()
                    # Avoid grabbing overly generic or clearly not model numbers
                    if not candidate.isdigit() or len(candidate) > 4: # Simple check: not purely numeric unless long enough
                        if candidate.lower() not in ["n/a", "unknown", "none", "see description"]:
                            model_no = candidate
                            break
        
        if model_no:
            model_no = model_no.strip()
            # Avoid overly long strings or things that look like descriptions
            if len(model_no) > 50 or len(model_no.split()) > 5:
                return None
            return model_no
        return None

    def extract_all_data(self, html_content: str, base_url: str = "") -> Dict[str, Any]:
        """
        Extract all available data from HTML content.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for relative URLs
            
        Returns:
            Dict with all extracted data
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style", "noscript", "iframe", "link", "meta"]): # Added more tags to remove
            script_or_style.decompose()
        
        # Attempt to find the main product container for more focused extraction
        main_product_area = soup.select_one('div[class*="product-detail"], article[class*="product"], section[class*="product"], div#productMain, div.pdp-main-content')
        extraction_target_soup = main_product_area if main_product_area else soup # Use focused area or whole soup

        text_content = extraction_target_soup.get_text(separator=' ', strip=True) # Text from focused area
        full_text_content = soup.get_text(separator=' ', strip=True) # For broader searches if needed
        
        # Extract all data
        data = {
            'title': self.extract_title(extraction_target_soup, fallback_text=self.extract_title(soup)), # Try focused then whole
            'description': self.extract_description(extraction_target_soup),
            'images': self.extract_images(extraction_target_soup, base_url),
            'identifiers': self.extract_identifiers(text_content), # Identifiers often in text
            'price': self.extract_price(text_content), # Price often in text
            'weight': self.extract_weight(text_content),
            'dimensions': self.extract_dimensions(text_content),
            'brand': self.extract_brand(extraction_target_soup, text_content=text_content),
            'model_number': self.extract_model_number(extraction_target_soup, text_content=text_content),
            'raw_text_snippet': text_content[:1000]  # Keep some raw text for reference
        }

        # If some core fields are missing, try with full soup/text as a fallback
        if not data['description']:
            data['description'] = self.extract_description(soup)
        if not data['images']:
            data['images'] = self.extract_images(soup, base_url)
        if not data['brand']:
            data['brand'] = self.extract_brand(soup, text_content=full_text_content)
        if not data['model_number']:
            data['model_number'] = self.extract_model_number(soup, text_content=full_text_content)
        
        # Try to extract from structured data (JSON-LD, Microdata)
        structured_data = self._extract_structured_data(soup)
        if structured_data:
            data['structured_data'] = structured_data
            # Augment with structured data if fields are missing or better
            if not data.get('title') and structured_data.get('name'):
                data['title'] = str(structured_data['name'])
            if not data.get('description') and structured_data.get('description'):
                data['description'] = str(structured_data['description'])
            if not data.get('price') and structured_data.get('offers'):
                offers = structured_data['offers']
                if isinstance(offers, list): offers = offers[0] # Take first offer
                if isinstance(offers, dict) and offers.get('price'):
                    data['price'] = self.extract_price(str(offers['price']))
            if not data.get('brand') and structured_data.get('brand'):
                brand_data = structured_data['brand']
                if isinstance(brand_data, dict) and brand_data.get('name'):
                    data['brand'] = str(brand_data['name'])
                elif isinstance(brand_data, str):
                    data['brand'] = brand_data
            if not data.get('model_number') and (structured_data.get('mpn') or structured_data.get('model') or structured_data.get('sku')):
                data['model_number'] = str(structured_data.get('mpn') or structured_data.get('model') or structured_data.get('sku'))
            if not data.get('images') and structured_data.get('image'):
                img_data = structured_data['image']
                if isinstance(img_data, list):
                    data['images'] = [str(i) for i in img_data if isinstance(i, str)]
                elif isinstance(img_data, str):
                    data['images'] = [img_data]
                elif isinstance(img_data, dict) and img_data.get('url'):
                     data['images'] = [str(img_data['url'])]


        # Final cleanup for description if it became too messy
        if data.get('description'):
            data['description'] = re.sub(r'\s+', ' ', data['description']).strip()
            data['description'] = data['description'][:3000]

        return data

    def _extract_structured_data(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract JSON-LD or microdata structured data."""
        # Look for JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data_content = script.string
                if data_content: # Ensure script.string is not None
                    loaded_json = json.loads(data_content)
                    if isinstance(loaded_json, dict) and loaded_json.get('@type') in ['Product', 'Offer']:
                        return loaded_json
                    elif isinstance(loaded_json, list):
                        for item in loaded_json:
                            if isinstance(item, dict) and item.get('@type') in ['Product', 'Offer']:
                                return item
            except (json.JSONDecodeError, AttributeError): # Catch AttributeError if script.string is None
                continue
        
        return None