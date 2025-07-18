"""
Enhanced Supplier Parser with flexible configuration support
"""
import re
import json
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from pathlib import Path

log = logging.getLogger(__name__)

class SupplierDataParser:
    """
    Parser for supplier-specific data extraction with configuration support.
    """
    
    def __init__(self, config_dir: str = "config/supplier_configs"):
        self.config_dir = Path(config_dir)
        self.parser_configs = {}
        self._load_all_configs()
        
    def _load_all_configs(self):
        """Load all supplier configurations from JSON files."""
        if not self.config_dir.exists():
            log.warning(f"Config directory {self.config_dir} does not exist")
            return
            
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    supplier_id = config_file.stem
                    self.parser_configs[supplier_id] = config
                    log.info(f"Loaded configuration for supplier: {supplier_id}")
            except Exception as e:
                log.error(f"Error loading config {config_file}: {e}")
    
    def parse_supplier_data(self, supplier_id: str, html_content: str, url: str) -> Dict[str, Any]:
        """
        Parse supplier data using supplier-specific configuration.
        
        Args:
            supplier_id: Identifier for the supplier
            html_content: HTML content to parse
            url: URL of the page (for context)
            
        Returns:
            Parsed product data
        """
        config = self.parser_configs.get(supplier_id)
        if not config:
            log.error(f"No parser configuration found for supplier: {supplier_id}")
            return {}
            
        # If html_content is already a BeautifulSoup element, use it directly
        if isinstance(html_content, BeautifulSoup):
            soup = html_content
        else:
            soup = BeautifulSoup(html_content, 'html.parser')
            
        parsed_data = {'supplier_id': supplier_id, 'url': url}
        
        # Parse each configured field
        field_mappings = config.get('field_mappings', {})
        for field_name, field_config in field_mappings.items():
            try:
                log.debug(f"Extracting field: {field_name} with config: {field_config}")
                value = self._extract_field(soup, field_config)
                log.debug(f"Extracted value for {field_name}: {value}")
                if value is not None:
                    parsed_data[field_name] = value
            except Exception as e:
                log.error(f"Error extracting {field_name}: {e}")
        
        # Apply post-processing rules
        if 'post_processing' in config:
            parsed_data = self._apply_post_processing(parsed_data, config['post_processing'])
        
        # Validate required fields
        required_fields = config.get('required_fields', ['title', 'price', 'url'])
        missing_fields = [f for f in required_fields if f not in parsed_data or not parsed_data[f]]
        if missing_fields:
            log.warning(f"Missing required fields for {supplier_id}: {missing_fields}")
            parsed_data['_validation_errors'] = missing_fields
        
        return parsed_data
    
    def _extract_field(self, soup: BeautifulSoup, field_config: Any) -> Optional[Any]:
        """Extract a field using its configuration with comprehensive debug logging."""
        log.debug(f"Starting field extraction with config: {field_config}")
        
        # Handle list format (multiple selector configurations)
        if isinstance(field_config, list):
            log.debug(f"Processing list of {len(field_config)} field configurations")
            for i, config_item in enumerate(field_config):
                log.debug(f"Trying configuration {i+1}/{len(field_config)}: {config_item}")
                result = self._extract_single_field_config(soup, config_item)
                if result is not None:
                    log.debug(f"Successfully extracted with config {i+1}: {result}")
                    return result
            log.debug("No successful extraction from any configuration in list")
            return None
        
        # Handle single configuration
        elif isinstance(field_config, dict):
            return self._extract_single_field_config(soup, field_config)
        
        else:
            log.error(f"Invalid field_config type: {type(field_config)}, expected dict or list")
            return None
    
    def _extract_single_field_config(self, soup: BeautifulSoup, field_config: Dict[str, Any]) -> Optional[Any]:
        """Extract a field using a single configuration dictionary."""
        extraction_type = field_config.get('type', 'text')
        log.debug(f"Processing single config - Type: {extraction_type}, Config: {field_config}")
        
        # Validate field_config structure
        if not isinstance(field_config, dict):
            log.error(f"Invalid field_config type: {type(field_config)}, expected dict")
            return None
            
        try:
            if extraction_type == 'text':
                result = self._extract_text_field(soup, field_config)
                log.debug(f"Text extraction result: {result}")
                return result
            elif extraction_type == 'price':
                result = self._extract_price_field(soup, field_config)
                log.debug(f"Price extraction result: {result}")
                return result
            elif extraction_type == 'image':
                result = self._extract_image_field(soup, field_config)
                log.debug(f"Image extraction result: {result}")
                return result
            elif extraction_type == 'list':
                result = self._extract_list_field(soup, field_config)
                log.debug(f"List extraction result: {result}")
                return result
            elif extraction_type == 'structured':
                result = self._extract_structured_field(soup, field_config)
                log.debug(f"Structured extraction result: {result}")
                return result
            elif extraction_type == 'attribute':
                result = self._extract_attribute_field(soup, field_config)
                log.debug(f"Attribute extraction result: {result}")
                return result
            elif extraction_type == 'element':
                # Handle element type - extract elements for further processing
                result = self._extract_element_field(soup, field_config)
                log.debug(f"Element extraction result: {result}")
                return result
            else:
                log.warning(f"Unknown extraction type: {extraction_type}")
                return None
        except Exception as e:
            log.error(f"Error in field extraction for type {extraction_type}: {e}", exc_info=True)
            return None
    
    def _extract_text_field(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[str]:
        """Extract text field with multiple selector attempts, including attribute extraction if specified."""
        # Handle direct selector in config (for clearance-king format)
        selector = config.get('selector')
        attribute = config.get('attribute')
        
        if selector:
            log.debug(f"Using direct selector for text: '{selector}'")
            try:
                elements = soup.select(selector)
                if elements:
                    element = elements[0]
                    log.debug(f"Found {len(elements)} elements, using first one")
                    
                    if element:
                        if attribute:
                            value = element.get(attribute)
                            if value:
                                log.debug(f"Extracted attribute text: {value}")
                                return self._apply_text_processing(value, config)
                        else:
                            value = element.get_text(strip=True)
                            if value:
                                log.debug(f"Extracted element text: {value}")
                                return self._apply_text_processing(value, config)
                else:
                    log.debug(f"No elements found for direct selector: {selector}")
            except Exception as e:
                log.error(f"Error processing direct text selector {selector}: {e}", exc_info=True)
        
        # Handle selectors list format (legacy format)
        selectors = config.get('selectors', [])
        if isinstance(selectors, str):
            selectors = [selectors]
        
        for selector in selectors:
            try:
                if isinstance(selector, dict):
                    css_selector = selector.get('selector')
                    attr = selector.get('attribute', attribute)
                    elements = soup.select(css_selector)
                    if elements:
                        element = elements[0]
                        if element:
                            if attr:
                                value = element.get(attr)
                                if value:
                                    return self._apply_text_processing(value, config)
                            else:
                                value = element.get_text(strip=True)
                                if value:
                                    return self._apply_text_processing(value, config)
                else:
                    elements = soup.select(selector)
                    if elements:
                        element = elements[0]
                        if element:
                            if attribute:
                                value = element.get(attribute)
                                if value:
                                    return self._apply_text_processing(value, config)
                            else:
                                value = element.get_text(strip=True)
                                if value:
                                    return self._apply_text_processing(value, config)
            except Exception as e:
                log.debug(f"Selector {selector} failed: {e}")
        return None
    
    def _apply_text_processing(self, text: str, config: Dict[str, Any]) -> str:
        """Apply text processing rules."""
        # Apply regex if specified
        if 'regex' in config:
            match = re.search(config['regex'], text)
            if match:
                group = config.get('regex_group', 1)
                text = match.group(group)
        
        # Apply replacements
        if 'replacements' in config:
            for old, new in config['replacements'].items():
                text = text.replace(old, new)
        
        # Apply transformations
        if 'transform' in config:
            transform = config['transform']
            if transform == 'uppercase':
                text = text.upper()
            elif transform == 'lowercase':
                text = text.lower()
            elif transform == 'title':
                text = text.title()
        
        return text.strip()
    
    def _extract_price_field(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[float]:
        """Extract and parse price field."""
        text_value = self._extract_text_field(soup, config)
        if not text_value:
            return None
            
        # Parse price from text
        price_pattern = r'[\d,]+\.?\d*'
        match = re.search(price_pattern, text_value.replace(',', ''))
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return None
    
    def _extract_image_field(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[str]:
        """Extract image URL."""
        selectors = config.get('selectors', [])
        if isinstance(selectors, str):
            selectors = [selectors]
            
        for selector in selectors:
            try:
                if isinstance(selector, dict):
                    css_selector = selector.get('selector')
                    attribute = selector.get('attribute', 'src')
                    element = soup.select_one(css_selector)
                    if element:
                        value = element.get(attribute)
                        if value:
                            return value
                else:
                    element = soup.select_one(selector)
                    if element:
                        value = element.get('src') or element.get('data-src')
                        if value:
                            return value
            except Exception as e:
                log.debug(f"Image selector {selector} failed: {e}")
                
        return None
    
    def _extract_list_field(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[List[str]]:
        """Extract list of values."""
        selectors = config.get('selectors', [])
        if isinstance(selectors, str):
            selectors = [selectors]
            
        for selector in selectors:
            try:
                if isinstance(selector, dict):
                    css_selector = selector.get('selector')
                    attribute = selector.get('attribute')
                    elements = soup.select(css_selector)
                    if elements:
                        values = []
                        for element in elements:
                            if attribute:
                                value = element.get(attribute)
                            else:
                                value = element.get_text(strip=True)
                            if value:
                                values.append(value)
                        if values:
                            return values[:config.get('max_items', 10)]
                else:
                    elements = soup.select(selector)
                    if elements:
                        values = [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
                        if values:
                            return values[:config.get('max_items', 10)]
            except Exception as e:
                log.debug(f"List selector {selector} failed: {e}")
                
        return None
    
    def _extract_structured_field(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[str]:
        """Extract structured data like breadcrumbs."""
        extract_as = config.get('extract_as', 'text')
        
        if extract_as == 'breadcrumb':
            selectors = config.get('selectors', [])
            separator = config.get('separator', ' > ')
            skip_first = config.get('skip_first', 0)
            skip_last = config.get('skip_last', 0)
            
            for selector in selectors:
                try:
                    if isinstance(selector, dict):
                        css_selector = selector.get('selector')
                        elements = soup.select(css_selector)
                    else:
                        elements = soup.select(selector)
                    
                    if elements:
                        texts = [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
                        if skip_first:
                            texts = texts[skip_first:]
                        if skip_last:
                            texts = texts[:-skip_last]
                        if texts:
                            return separator.join(texts)
                except Exception as e:
                    log.debug(f"Structured selector {selector} failed: {e}")
        
        return None
    
    def _extract_attribute_field(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[str]:
        """Extract attribute field with comprehensive error handling and debug logging."""
        # Handle direct selector in config (for clearance-king format)
        selector = config.get('selector')
        attribute = config.get('attribute')
        
        if selector and attribute:
            log.debug(f"Using direct selector: '{selector}', attribute: '{attribute}'")
            try:
                elements = soup.select(selector)
                if elements:
                    element = elements[0]
                    log.debug(f"Found {len(elements)} elements, using first one")
                    
                    if element and hasattr(element, 'get'):
                        value = element.get(attribute)
                        log.debug(f"Extracted attribute value: {value}")
                        
                        if value and value.strip():
                            log.debug(f"Successfully extracted attribute '{attribute}': {value}")
                            return value.strip()
                        else:
                            log.debug(f"Attribute '{attribute}' was empty or None")
                    else:
                        log.warning(f"Element does not support attribute extraction: {type(element)}")
                else:
                    log.debug(f"No elements found for selector: {selector}")
            except Exception as e:
                log.error(f"Error processing direct selector {selector}: {e}", exc_info=True)
        
        # Handle selectors list format (legacy format)
        selectors = config.get('selectors', [])
        if isinstance(selectors, str):
            selectors = [selectors]
        
        # Get attribute from config - support both 'attribute' and nested selector configs
        default_attribute = config.get('attribute')
        log.debug(f"Extracting attribute field with {len(selectors)} selectors, default attribute: {default_attribute}")
        
        for i, selector in enumerate(selectors):
            try:
                log.debug(f"Trying selector {i+1}/{len(selectors)}: {selector}")
                
                if isinstance(selector, dict):
                    # Selector is a dictionary with 'selector' and 'attribute' keys
                    css_selector = selector.get('selector')
                    attribute = selector.get('attribute', default_attribute)
                    
                    if not css_selector:
                        log.warning(f"Selector dict missing 'selector' key: {selector}")
                        continue
                    if not attribute:
                        log.warning(f"No attribute specified for selector: {css_selector}")
                        continue
                        
                    log.debug(f"Using CSS selector: '{css_selector}', attribute: '{attribute}'")
                    elements = soup.select(css_selector)
                    
                    if elements:
                        element = elements[0]
                        log.debug(f"Found {len(elements)} elements, using first one")
                        
                        if element and hasattr(element, 'get'):
                            value = element.get(attribute)
                            log.debug(f"Extracted attribute value: {value}")
                            
                            if value and value.strip():
                                log.debug(f"Successfully extracted attribute '{attribute}': {value}")
                                return value.strip()
                            else:
                                log.debug(f"Attribute '{attribute}' was empty or None")
                        else:
                            log.warning(f"Element does not support attribute extraction: {type(element)}")
                    else:
                        log.debug(f"No elements found for CSS selector: {css_selector}")
                        
                else:
                    # Selector is a string - use default attribute
                    if not default_attribute:
                        log.warning(f"String selector '{selector}' provided but no default attribute specified")
                        continue
                        
                    log.debug(f"Using string selector: '{selector}', attribute: '{default_attribute}'")
                    elements = soup.select(selector)
                    
                    if elements:
                        element = elements[0]
                        log.debug(f"Found {len(elements)} elements, using first one")
                        
                        if element and hasattr(element, 'get'):
                            value = element.get(default_attribute)
                            log.debug(f"Extracted attribute value: {value}")
                            
                            if value and value.strip():
                                log.debug(f"Successfully extracted attribute '{default_attribute}': {value}")
                                return value.strip()
                            else:
                                log.debug(f"Attribute '{default_attribute}' was empty or None")
                        else:
                            log.warning(f"Element does not support attribute extraction: {type(element)}")
                    else:
                        log.debug(f"No elements found for selector: {selector}")
                        
            except Exception as e:
                log.error(f"Error processing attribute selector {selector}: {e}", exc_info=True)
                continue
        
        log.debug("No attribute value found with any selector")
        return None
    
    def _extract_element_field(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[List]:
        """Extract elements for further processing (used for product items)."""
        selector = config.get('selector')
        
        if not selector:
            log.warning("Element extraction requires a 'selector' field")
            return None
            
        log.debug(f"Extracting elements with selector: {selector}")
        
        try:
            elements = soup.select(selector)
            log.debug(f"Found {len(elements)} elements")
            
            if elements:
                # Return the elements for further processing
                return elements
            else:
                log.debug(f"No elements found for selector: {selector}")
                return None
                
        except Exception as e:
            log.error(f"Error extracting elements with selector {selector}: {e}", exc_info=True)
            return None
    
    def _apply_post_processing(self, data: Dict[str, Any], post_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply post-processing rules to extracted data."""
        # Price adjustments
        if 'price_adjustments' in post_config and 'price' in data:
            price_adj = post_config['price_adjustments']
            if price_adj.get('vat_included') and 'vat_rate' in price_adj:
                vat_rate = price_adj['vat_rate']
                data['price_ex_vat'] = data['price'] / (1 + vat_rate)
        
        # Title cleanup
        if 'title_cleanup' in post_config and 'title' in data:
            title_config = post_config['title_cleanup']
            title = data['title']
            
            # Remove patterns
            for pattern in title_config.get('remove_patterns', []):
                title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
            
            # Limit length
            max_length = title_config.get('max_length', 200)
            if len(title) > max_length:
                title = title[:max_length].strip()
            
            data['title'] = title
        
        return data