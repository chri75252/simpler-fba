"""
Data Normalizer for Amazon FBA Agent System
Normalizes and standardizes product data from various sources.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime
import unicodedata

log = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes product data to consistent formats."""
    
    def __init__(self):
        """Initialize normalizer with conversion rules."""
        # Currency symbols and their codes
        self.currency_symbols = {
            '£': 'GBP',
            '$': 'USD',
            '€': 'EUR',
            '¥': 'JPY',
            '₹': 'INR',
            'kr': 'SEK', # General 'kr', might need context for DKK, NOK
            'zł': 'PLN' 
        }
        
        # Weight unit conversions to pounds
        self.weight_conversions = {
            'kg': 2.20462,
            'kilogram': 2.20462,
            'kilo': 2.20462,
            'g': 0.00220462,
            'gram': 0.00220462,
            'oz': 0.0625,
            'ounce': 0.0625,
            'lb': 1.0,
            'lbs': 1.0,
            'pound': 1.0,
            'pounds': 1.0,
            'mg': 0.00000220462,
            'milligram': 0.00000220462,
            'ton': 2000.0, # US ton
            'tonne': 2204.62 # Metric tonne
        }
        
        # Dimension unit conversions to inches
        self.dimension_conversions = {
            'mm': 0.0393701,
            'millimeter': 0.0393701,
            'cm': 0.393701,
            'centimeter': 0.393701,
            'dm': 3.93701,
            'decimeter': 3.93701,
            'm': 39.3701,
            'meter': 39.3701,
            'in': 1.0,
            'inch': 1.0,
            'inches': 1.0,
            'ft': 12.0,
            'foot': 12.0,
            'feet': 12.0,
            'yd': 36.0,
            'yard': 36.0
        }
        
        # Common brand name variations
        self.brand_normalizations = {
            'hp': 'HP',
            'ibm': 'IBM',
            'lg': 'LG',
            '3m': '3M',
            'p&g': 'Procter & Gamble',
            'j&j': 'Johnson & Johnson',
            'nestle': 'Nestlé',
            'l\'oreal': 'L\'Oréal',
            'coca cola': 'Coca-Cola',
            'mercedes benz': 'Mercedes-Benz'
            # Add more as needed
        }

    def normalize_product_data(self, product_data: Dict[str, Any], source: str = 'unknown') -> Dict[str, Any]:
        """
        Normalize all product data fields.
        
        Args:
            product_data: Raw product data
            source: Source of the data ('supplier' or 'amazon')
            
        Returns:
            Normalized product data
        """
        normalized = product_data.copy() # Create a copy to avoid modifying original
        
        # Normalize text fields
        if 'title' in normalized and normalized['title'] is not None:
            normalized['title'] = self.normalize_title(normalized['title'])
        
        if 'description' in normalized and normalized['description'] is not None:
            normalized['description'] = self.normalize_text(normalized['description'])
        
        if 'brand' in normalized and normalized['brand'] is not None:
            normalized['brand'] = self.normalize_brand(normalized['brand'])
        
        # Normalize price fields
        price_fields = ['price', 'current_price', 'sale_price', 'list_price', 'msrp']
        for field in price_fields:
            if field in normalized and normalized[field] is not None:
                normalized[field] = self.normalize_price(normalized[field]) # Returns dict or None
        
        # Normalize identifiers
        for id_field in ['ean', 'upc', 'isbn', 'asin', 'sku', 'mpn', 'model_number']:
            if id_field in normalized and normalized[id_field] is not None:
                normalized[id_field] = self.normalize_identifier(normalized[id_field], id_field)
        
        # Normalize weight
        if 'weight' in normalized and normalized['weight'] is not None:
            normalized['weight_normalized'] = self.normalize_weight(normalized['weight'])
        elif 'weight_from_details' in normalized and normalized['weight_from_details'] is not None:
            normalized['weight_normalized'] = self.normalize_weight(normalized['weight_from_details'])
        
        # Normalize dimensions
        if 'dimensions' in normalized and normalized['dimensions'] is not None:
            normalized['dimensions_normalized'] = self.normalize_dimensions(normalized['dimensions'])
        elif 'dimensions_from_details' in normalized and normalized['dimensions_from_details'] is not None:
            normalized['dimensions_normalized'] = self.normalize_dimensions(normalized['dimensions_from_details'])
        
        # Normalize boolean fields
        boolean_fields = ['in_stock', 'is_prime', 'sold_by_amazon', 'is_available'] # Added is_available
        for field in boolean_fields:
            if field in normalized and normalized[field] is not None:
                normalized[field] = self.normalize_boolean(normalized[field])

        # Normalize URLs
        if 'url' in normalized and normalized['url'] is not None:
            normalized['url'] = self.normalize_url(normalized['url'])
        
        if 'image_url' in normalized and normalized['image_url'] is not None: # Single image_url
            normalized['image_url'] = self.normalize_url(normalized['image_url'])
        elif 'images' in normalized and isinstance(normalized['images'], list): # List of images
            normalized['images'] = [self.normalize_url(url) for url in normalized['images'] if url] # Ensure url is not None

        # Normalize categories
        if 'category' in normalized and normalized['category'] is not None:
            normalized['category'] = self.normalize_category(normalized['category'])
        if 'categories' in normalized and isinstance(normalized['categories'], list): # List of categories
             normalized['categories'] = [self.normalize_category(cat) for cat in normalized['categories'] if cat]


        # Add metadata
        normalized['_normalized_metadata'] = {
            'normalized_at': datetime.now().isoformat(),
            'original_source': source
        }
        
        return normalized

    def normalize_title(self, title: str) -> str:
        """
        Normalize product title.
        """
        if not title:
            return ""
        
        title = str(title).strip()
        title = unicodedata.normalize('NFKD', title)
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'([!?.])\1+', r'\1', title)
        title = re.sub(r'\s*-\s*-\s*', ' - ', title)
        title = re.sub(r'\s*,\s*,\s*', ', ', title)
        
        # More advanced title casing might be needed for some brands/acronyms
        # Simple title case for now:
        title = title.title() 
        
        # Limit length
        if len(title) > 255: # Standard Amazon title limit is around 200-250
            cut_pos = title.rfind(' ', 0, 250)
            title = title[:cut_pos] + '...' if cut_pos != -1 else title[:250] + '...'
        
        return title

    def normalize_text(self, text: str) -> str:
        """
        Normalize general text content (like descriptions).
        """
        if not text:
            return ""
        
        text = str(text).strip()
        text = unicodedata.normalize('NFKD', text)
        text = re.sub(r'<[^>]+>', ' ', text) # Remove HTML tags
        text = re.sub(r'\s+', ' ', text) # Normalize whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text) # Normalize multiple newlines
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\t\r') # Remove most control chars
        
        return text.strip()

    def normalize_brand(self, brand: str) -> str:
        """
        Normalize brand name.
        """
        if not brand:
            return ""
        
        brand = str(brand).strip()
        brand = re.sub(r'^(by|from|brand:)\s+', '', brand, flags=re.IGNORECASE)
        brand = re.sub(r'\s+(brand|inc\.?|ltd\.?|co\.?|corp\.?|llc|gmbh)$', '', brand, flags=re.IGNORECASE)
        
        brand_lower = brand.lower()
        if brand_lower in self.brand_normalizations:
            return self.brand_normalizations[brand_lower]
        
        # If all caps or all lower (and not a known acronym like HP), title case it
        if (brand.isupper() or brand.islower()) and brand_lower not in [k.lower() for k in self.brand_normalizations.values() if k.isupper()]:
            brand = brand.title()
        
        return brand

    def normalize_price(self, price_input: Union[str, float, int], target_currency: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Normalize price to a dictionary with value and currency.
        Handles various formats and extracts currency if possible.
        """
        if price_input is None:
            return None
        
        if isinstance(price_input, (int, float)):
            return {'value': round(float(price_input), 2), 'currency': target_currency or 'UNKNOWN'}
        
        price_str = str(price_input).strip()
        if not price_str:
            return None

        extracted_currency = None
        
        # Attempt to identify currency symbol/code first
        # Check for currency codes first (USD, GBP) as they are more explicit
        for code_symbol, code_name in self.currency_symbols.items(): # Check symbols first
            if code_symbol in price_str:
                extracted_currency = code_name
                price_str = price_str.replace(code_symbol, '') # Remove symbol for easier parsing
                break 
        
        if not extracted_currency: # If no symbol, check for codes
            for code in ['GBP', 'USD', 'EUR', 'CAD', 'AUD', 'JPY', 'INR', 'SEK', 'PLN']: 
                # Regex to find code as a whole word, possibly at start/end or with space
                match_code = re.search(rf'(?:^|\s)({code})(?:$|\s)', price_str, re.IGNORECASE)
                if match_code:
                    extracted_currency = match_code.group(1).upper()
                    price_str = re.sub(rf'(?:^|\s)({code})(?:$|\s)', ' ', price_str, flags=re.IGNORECASE) # Remove code
                    break
        
        price_str = price_str.strip()
        
        price_words_pattern = r'(?i)\b(price|cost|rrp|msrp|now|was|sale|save|off|only|approx\.?|around|from|total|subtotal|vat)\b[:\s]*'
        price_str = re.sub(price_words_pattern, '', price_str).strip()

        # Regex to find a number, possibly with thousands separators (., or space) and a decimal part
        match = re.search(r'(\d{1,3}(?:([.,\s])\d{3})*(?:([.,])\d{1,2})?|\d+(?:([.,])\d{1,2})?)', price_str)
        
        numeric_part_str = None
        if match:
            numeric_part_str = match.group(0) 

            # Standardize the numeric string
            if ' ' in numeric_part_str: # Remove spaces if used as thousands separator
                 numeric_part_str = numeric_part_str.replace(' ', '')

            if ',' in numeric_part_str and '.' in numeric_part_str:
                if numeric_part_str.rfind(',') > numeric_part_str.rfind('.'):
                    numeric_part_str = numeric_part_str.replace('.', '').replace(',', '.')
                else:
                    numeric_part_str = numeric_part_str.replace(',', '')
            elif ',' in numeric_part_str:
                if re.match(r'^\d+,\d{1,2}$', numeric_part_str) and not re.match(r'^\d{1,3}(,\d{3})+(,\d{1,2})?$', numeric_part_str): # e.g. 12,34 not 1,234,56
                    numeric_part_str = numeric_part_str.replace(',', '.')
                else: # Assume thousand separator
                    numeric_part_str = numeric_part_str.replace(',', '')
        
        if numeric_part_str:
            try:
                price_value = float(numeric_part_str)
                if 0.001 < price_value < 10000000:
                     return {'value': round(price_value, 2), 'currency': extracted_currency or target_currency or 'UNKNOWN'}
            except ValueError:
                log.debug(f"Could not convert '{numeric_part_str}' to float after parsing price string '{price_input}'")
        
        log.warning(f"Could not normalize price from input: '{price_input}'")
        return None

    def normalize_identifier(self, identifier: str, id_type: str) -> str:
        """
        Normalize product identifier.
        """
        if not identifier:
            return ""
        
        identifier = str(identifier).strip()
        identifier = re.sub(rf'^(?i){id_type}[\s:-]*', '', identifier) # Case insensitive prefix
        
        if id_type in ['ean', 'upc', 'isbn', 'gtin']: # GTIN also numeric
            identifier = re.sub(r'[\s-]', '', identifier)
        
        if id_type == 'asin':
            identifier = identifier.upper()
        
        expected_lengths = {
            'ean': 13, 'upc': 12, 'isbn': [10, 13], 'asin': 10, 'gtin': [8,12,13,14]
        }
        
        if id_type in expected_lengths:
            expected = expected_lengths[id_type]
            id_len = len(identifier)
            if isinstance(expected, list):
                if id_len not in expected:
                    log.debug(f"Potential invalid {id_type} length: {id_len} for '{identifier}' (expected one of {expected})")
            elif id_len != expected:
                log.debug(f"Potential invalid {id_type} length: {id_len} for '{identifier}' (expected {expected})")
        
        return identifier

    def normalize_weight(self, weight_input: Union[str, float, int, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Normalize weight to a standard dictionary format (value, unit, pounds).
        """
        if weight_input is None:
            return None

        parsed_value: Optional[float] = None
        parsed_unit: Optional[str] = None
        pounds: Optional[float] = None

        if isinstance(weight_input, dict):
            parsed_value = weight_input.get('value')
            parsed_unit = weight_input.get('unit')
            if 'pounds' in weight_input and isinstance(weight_input['pounds'], (int, float)):
                 pounds = float(weight_input['pounds'])
                 if parsed_value is None and parsed_unit is None and pounds is not None: # Reconstruct if only pounds given
                     parsed_value = pounds 
                     parsed_unit = 'lb'
            elif parsed_value is not None and parsed_unit is not None:
                try:
                    pounds = self.convert_weight_to_pounds(float(parsed_value), str(parsed_unit))
                except ValueError:
                    log.warning(f"Could not convert weight value in dict: {parsed_value}")
                    return None
            else: # Malformed dict
                log.warning(f"Input weight dict missing 'value'/'unit' or 'pounds': {weight_input}")
                return None
        elif isinstance(weight_input, (int, float)):
            pounds = float(weight_input) # Assume pounds if just a number
            parsed_value = pounds
            parsed_unit = 'lb'
        elif isinstance(weight_input, str):
            parsed_data = self.parse_weight_string(weight_input)
            if parsed_data:
                pounds = parsed_data['pounds']
                parsed_value = parsed_data['value']
                parsed_unit = parsed_data['unit']
            else:
                log.debug(f"Could not parse weight string: '{weight_input}'")
                return None
        else:
            log.warning(f"Unsupported weight input type: {type(weight_input)}")
            return None
            
        if pounds is None or pounds <= 0:
            log.debug(f"Normalized weight resulted in non-positive or None pounds: {pounds} from input {weight_input}")
            return None

        return {
            'original_value': parsed_value,
            'original_unit': parsed_unit,
            'pounds': round(pounds, 3),
            'kilograms': round(pounds / self.weight_conversions.get('kg', 2.20462), 3), # Safe get
            'ounces': round(pounds * 16, 2),
            'grams': round(pounds * 453.59237, 1)
        }

    def normalize_dimensions(self, dim_input: Union[str, Dict[str, Any], List[float], Tuple[float, ...]]) -> Optional[Dict[str, Any]]:
        """
        Normalize dimensions to a standard dictionary format.
        """
        if dim_input is None:
            return None

        l_in: Optional[float] = None
        w_in: Optional[float] = None
        h_in: Optional[float] = None
        original_l: Optional[float] = None
        original_w: Optional[float] = None
        original_h: Optional[float] = None
        original_unit: Optional[str] = None

        if isinstance(dim_input, dict):
            inches_data = dim_input.get('inches')
            if isinstance(inches_data, (tuple, list)) and len(inches_data) == 3 and all(isinstance(d, (int,float)) for d in inches_data):
                l_in, w_in, h_in = map(float, inches_data)
                original_l, original_w, original_h = dim_input.get('length'), dim_input.get('width'), dim_input.get('height')
                original_unit = dim_input.get('unit')
            elif all(k in dim_input for k in ['length', 'width', 'height']) and dim_input.get('unit'):
                try:
                    original_l, original_w, original_h = float(dim_input['length']), float(dim_input['width']), float(dim_input['height'])
                    original_unit = str(dim_input['unit'])
                    l_in = self.convert_dimension_to_inches(original_l, original_unit)
                    w_in = self.convert_dimension_to_inches(original_w, original_unit)
                    h_in = self.convert_dimension_to_inches(original_h, original_unit)
                except ValueError:
                    log.warning(f"Could not convert dimension values in dict: {dim_input}")
                    return self._empty_dimensions()
            else:
                log.debug(f"Input dimension dict malformed: {dim_input}")
                return self._empty_dimensions()
        elif isinstance(dim_input, (list, tuple)) and len(dim_input) == 3 and all(isinstance(d, (int, float)) for d in dim_input):
            l_in, w_in, h_in = map(float, dim_input)
            original_l, original_w, original_h = l_in, w_in, h_in
            original_unit = 'in' # Assume inches
        elif isinstance(dim_input, str):
            parsed_data = self.parse_dimension_string(dim_input)
            if parsed_data and isinstance(parsed_data.get('inches'), (tuple, list)) and len(parsed_data['inches']) == 3:
                l_in, w_in, h_in = map(float, parsed_data['inches'])
                original_l, original_w, original_h = parsed_data.get('length'), parsed_data.get('width'), parsed_data.get('height')
                original_unit = parsed_data.get('unit')
            else:
                log.debug(f"Could not parse dimension string: '{dim_input}'")
                return self._empty_dimensions()
        else:
            log.warning(f"Unsupported dimension input type: {type(dim_input)}")
            return self._empty_dimensions()

        if not all(d is not None and d > 0 for d in [l_in, w_in, h_in]):
            log.debug(f"Normalized dimensions resulted in non-positive values: L={l_in}, W={w_in}, H={h_in} from input {dim_input}")
            return self._empty_dimensions()

        cm_conversion_factor = self.dimension_conversions.get('cm', 0.393701) / self.dimension_conversions.get('in', 1.0)

        return {
            'original': {
                'length': original_l, 'width': original_w, 'height': original_h, 'unit': original_unit
            },
            'inches': {
                'length': round(l_in, 2), 'width': round(w_in, 2), 'height': round(h_in, 2)
            },
            'centimeters': {
                'length': round(l_in * cm_conversion_factor, 1),
                'width': round(w_in * cm_conversion_factor, 1),
                'height': round(h_in * cm_conversion_factor, 1)
            },
            'volume_cubic_inches': round(l_in * w_in * h_in, 2),
            'volume_cubic_feet': round((l_in * w_in * h_in) / 1728, 3) # 1728 cubic inches in a cubic foot
        }

    def normalize_boolean(self, value: Any) -> Optional[bool]:
        """Converts various string/int inputs to boolean."""
        if value is None:
            return None # Or False, depending on desired strictness
        if isinstance(value, bool):
            return value
        
        val_str = str(value).lower().strip()
        if val_str in ['true', 'yes', '1', 'on', 'enabled', 'active', 'in stock', 'available']:
            return True
        if val_str in ['false', 'no', '0', 'off', 'disabled', 'inactive', 'out of stock', 'unavailable']:
            return False
        
        log.debug(f"Could not normalize boolean from value: '{value}'")
        return None # Or raise error/return default

    def normalize_url(self, url: str) -> str:
        """
        Normalize URL format.
        """
        if not url or not isinstance(url, str): # Added type check
            return ""
        
        url = url.strip()
        
        if not url.startswith(('http://', 'https://', '//')):
            if url.startswith('www.'):
                url = 'https://' + url
            # Avoid prepending https:// to relative paths like '/path/to/page'
            elif '.' in url.split('/')[0] and not url.startswith('/'): # Check if first part looks like a domain
                url = 'https://' + url
        
        if url.startswith('//'):
            url = 'https:' + url
        
        # More comprehensive tracking parameter removal
        # Common prefixes: utm_, gclid, fbclid, msclkid, ref, source, campaign, kw, term, content, etc.
        # (?i) for case-insensitivity
        tracking_params_regex = r'(?i)[?&](utm_[a-z_]+=.*|gclid=.*|fbclid=.*|msclkid=.*|ref=.*|source=.*|campaign=.*|kw=.*|term=.*|content=.*|cid=.*|mc_[a-z_]+=.*|yclid=.*|zanpid=.*|cjevent=.*|affiliateid=.*|partnerid=.*|clickid=.*|promo[a-z_]*=.*)(&|$)'
        
        # Iteratively remove to handle multiple params
        prev_url = None
        while url != prev_url:
            prev_url = url
            url = re.sub(tracking_params_regex, '', url)
            url = url.rstrip('?&') # Clean trailing ? or &

        # Normalize www (optional: remove or add consistently)
        # url = re.sub(r'https://www\.', 'https://', url) 

        # Remove fragment (optional, depends on use case)
        # url = url.split('#')[0]
        
        return url

    def normalize_category(self, category: str) -> str:
        """
        Normalize category string.
        """
        if not category or not isinstance(category, str): # Added type check
            return ""
        
        category = category.strip()
        
        # Replace common separators with a standard one, e.g., ' > '
        # Order matters if some separators are substrings of others
        separators_map = {
            ' >> ': ' > ',
            ' // ': ' > ', # If // is used
            ' / ': ' > ',
            ' | ': ' > ',
            ' - ': ' > ', # Use with caution, might be part of category name
            '\\': ' > ', # Backslash
            ':': ' > ' # Colon
        }
        for sep, standard_sep in separators_map.items():
            category = category.replace(sep, standard_sep)
        
        # Clean up each part and handle potential empty parts from multiple separators
        parts = [part.strip() for part in category.split(' > ') if part.strip()]
        
        # Title case each part and remove duplicates while preserving order
        cleaned_parts = []
        seen_parts = set()
        for part in parts:
            # Simple title case, could be more sophisticated for acronyms etc.
            # part_title_cased = part.title() 
            # For categories, often keeping original casing or just capitalizing first letter is better
            part_processed = part[0].upper() + part[1:] if len(part) > 1 else part.upper()

            if part_processed not in seen_parts:
                cleaned_parts.append(part_processed)
                seen_parts.add(part_processed)
        
        return ' > '.join(cleaned_parts)

    def parse_weight_string(self, weight_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse weight from string.
        """
        if not weight_str or not isinstance(weight_str, str): # Added type check
            return None
        
        weight_str = weight_str.lower().strip()
        
        # More flexible regex to capture value and unit
        # Allows for optional space between value and unit
        # Prioritize longer unit matches (e.g., 'kilogram' before 'kg' or 'g')
        # Sort keys by length to match longer units first
        sorted_units = sorted(self.weight_conversions.keys(), key=len, reverse=True)

        for unit_key in sorted_units:
            # Regex: (number) possibly_space (unit_key) possibly_plural_s end_of_word_or_string
            # Example: "10.5kg", "10.5 kg", "10.5kgs"
            pattern = rf'(\d+(?:[.,]\d+)?)\s*{re.escape(unit_key)}(?:s)?(?:\b|$)'
            match = re.search(pattern, weight_str)
            if match:
                try:
                    value_str = match.group(1).replace(',', '.') # Handle comma as decimal
                    value = float(value_str)
                    pounds = self.convert_weight_to_pounds(value, unit_key)
                    return {
                        'value': value,
                        'unit': unit_key, # The matched unit from our conversion map
                        'pounds': pounds
                    }
                except ValueError:
                    log.debug(f"ValueError parsing weight value from '{match.group(1)}' with unit '{unit_key}'")
                    continue
        
        # Fallback for just a number, assume it might be a primary unit if context allows (e.g. pounds or kg)
        # This is risky without more context. For now, require unit.
        log.debug(f"Could not parse weight with unit from string: '{weight_str}'")
        return None

    def parse_dimension_string(self, dim_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse dimensions from string.
        """
        if not dim_str or not isinstance(dim_str, str): # Added type check
            return None
        
        dim_str = dim_str.strip()
        
        # Enhanced patterns to be more flexible
        # Pattern 1: 10x20x30 cm OR 10 x 20 x 30cm OR 10x 20 x30 cm etc.
        # Captures three numbers and an optional unit at the end.
        pattern1 = r'(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]{1,10})?'
        
        # Pattern 2: L:10 W:20 H:30 cm OR Length 10cm Width 20cm Height 30cm
        # This is harder to make generic. For now, stick to simpler LWH.
        pattern2 = r'(?:L|Length)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*(?:[a-zA-Z]{1,10})?\s*,?\s*(?:W|Width)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*(?:[a-zA-Z]{1,10})?\s*,?\s*(?:H|Height)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]{1,10})?'

        patterns_to_try = [pattern1, pattern2]
        
        for pattern_regex in patterns_to_try:
            match = re.search(pattern_regex, dim_str, re.IGNORECASE)
            if match:
                try:
                    g = match.groups()
                    length = float(g[0].replace(',', '.'))
                    width = float(g[1].replace(',', '.'))
                    height = float(g[2].replace(',', '.'))
                    
                    # Determine unit: unit might be after each number or at the end.
                    # This simplified regex assumes unit is at the end (g[3]) or implied.
                    unit_str = g[3] if len(g) > 3 and g[3] else 'cm' # Default to cm if no unit found
                    
                    # Find the actual unit from our conversion map
                    found_unit = 'cm' # Default
                    unit_str_lower = unit_str.lower()
                    for dim_unit_key in self.dimension_conversions.keys():
                        if dim_unit_key == unit_str_lower or (dim_unit_key+'s' == unit_str_lower): # Handle plurals like inches
                            found_unit = dim_unit_key
                            break
                    
                    inches_tuple = (
                        self.convert_dimension_to_inches(length, found_unit),
                        self.convert_dimension_to_inches(width, found_unit),
                        self.convert_dimension_to_inches(height, found_unit)
                    )
                    
                    return {
                        'length': length, 'width': width, 'height': height, 'unit': found_unit,
                        'inches': inches_tuple
                    }
                except (ValueError, TypeError, IndexError) as e:
                    log.debug(f"Error parsing dimensions with pattern '{pattern_regex}' on '{dim_str}': {e}")
                    continue
        
        log.debug(f"Could not parse dimensions from string: '{dim_str}'")
        return None

    def convert_weight_to_pounds(self, value: float, unit: str) -> float:
        """Convert weight to pounds."""
        if not isinstance(value, (int,float)): raise ValueError("Weight value must be numeric")
        if not unit or not isinstance(unit, str): raise ValueError("Weight unit must be a string")

        unit_lower = unit.lower().strip()
        # Handle common variations not in map directly
        if unit_lower == "gramme" or unit_lower == "grammes": unit_lower = "g"
        if unit_lower == "kilos" or unit_lower == "kilogrammes": unit_lower = "kg"
        
        conversion = self.weight_conversions.get(unit_lower)
        if conversion is None:
            log.warning(f"Unknown weight unit '{unit}' for conversion. Assuming value is already in pounds.")
            return value # Or raise error
        return value * conversion

    def convert_dimension_to_inches(self, value: float, unit: str) -> float:
        """Convert dimension to inches."""
        if not isinstance(value, (int,float)): raise ValueError("Dimension value must be numeric")
        if not unit or not isinstance(unit, str): raise ValueError("Dimension unit must be a string")

        unit_lower = unit.lower().strip()
        # Handle common variations
        if unit_lower == "centimetre" or unit_lower == "centimetres": unit_lower = "cm"
        if unit_lower == "millimetre" or unit_lower == "millimetres": unit_lower = "mm"
        if unit_lower == "metre" or unit_lower == "metres": unit_lower = "m"


        conversion = self.dimension_conversions.get(unit_lower)
        if conversion is None:
            log.warning(f"Unknown dimension unit '{unit}' for conversion. Assuming value is already in inches.")
            return value # Or raise error
        return value * conversion

    def _empty_dimensions(self) -> Dict[str, Any]:
        """Return empty/default dimensions structure."""
        return {
            'original': {'length': None, 'width': None, 'height': None, 'unit': None},
            'inches': {'length': 0.0, 'width': 0.0, 'height': 0.0}, # Use 0.0 for calculations
            'centimeters': {'length': 0.0, 'width': 0.0, 'height': 0.0},
            'volume_cubic_inches': 0.0,
            'volume_cubic_feet': 0.0
        }

    def merge_normalized_data(self, *data_sources: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple normalized data sources. Prioritizes first source for most fields,
        aggregates lists like images/features.
        """
        if not data_sources:
            return {}
        
        merged_data = data_sources[0].copy() # Start with the first source as base

        for i in range(1, len(data_sources)):
            current_source = data_sources[i]
            for key, value in current_source.items():
                if value is not None: # Only consider non-None values from subsequent sources
                    if key in ['images', 'features', 'categories'] and isinstance(value, list):
                        # Aggregate list type fields, ensuring uniqueness
                        if key not in merged_data or not isinstance(merged_data.get(key), list):
                            merged_data[key] = []
                        
                        existing_values = set(tuple(item.items()) if isinstance(item, dict) else item for item in merged_data[key])
                        for item in value:
                            item_comparable = tuple(item.items()) if isinstance(item, dict) else item
                            if item_comparable not in existing_values:
                                merged_data[key].append(item)
                                existing_values.add(item_comparable)
                    elif key not in merged_data: # If key doesn't exist in merged, add it
                        merged_data[key] = value
                    # For other types (like string, dict, numeric), first source usually wins unless explicitly handled
                    # Example: if 'price' (dict) is better in a later source, specific logic would be needed.
                    # For now, simple overwrite if not list or not present.

        return merged_data