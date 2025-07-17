"""
Product Data Validator for Amazon FBA Agent System
Validates extracted product data against expected formats and business rules.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

log = logging.getLogger(__name__)


class ProductValidator:
    """Validates product data for quality and completeness."""
    
    def __init__(self):
        """Initialize validator with validation rules."""
        self.required_fields = {
            'supplier': ['title', 'price', 'url'],
            'amazon': ['title', 'asin', 'current_price'],
            'combined': ['supplier_product_info', 'amazon_product_info']
        }
        
        self.price_limits = {
            'min': 0.01,
            'max': 100000.00
        }
        
        self.weight_limits = {
            'min_pounds': 0.01,
            'max_pounds': 150.0  # FBA limit
        }
        
        self.dimension_limits = {
            'min_inches': 0.1,
            'max_length_inches': 108.0,  # FBA oversize limit
            'max_girth_inches': 165.0  # Length + 2*(Width + Height)
        }
        
        # Restricted keywords for FBA
        self.restricted_keywords = [
            # Hazmat
            'battery', 'batteries', 'lithium', 'flammable', 'explosive',
            'chemical', 'hazardous', 'toxic', 'corrosive', 'radioactive',
            
            # Restricted categories
            'weapon', 'knife', 'gun', 'ammunition', 'tobacco', 'vape',
            'e-cigarette', 'alcohol', 'drug', 'pharmaceutical', 'prescription',
            
            # Adult content
            'adult', 'sex', 'erotic', 'pornographic',
            
            # Counterfeit risks
            'replica', 'fake', 'copy', 'knockoff', 'imitation'
        ]

    def validate_supplier_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate supplier product data.
        
        Args:
            product_data: Supplier product data dict
            
        Returns:
            Validation result with status and issues
        """
        validation_result = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'data_quality_score': 100.0
        }
        
        # Check required fields
        for field in self.required_fields['supplier']:
            if field not in product_data or not product_data[field]:
                validation_result['valid'] = False
                validation_result['issues'].append(f"Missing required field: {field}")
                validation_result['data_quality_score'] -= 20
        
        # Validate title
        title_validation = self._validate_text_field(product_data.get('title'), "Supplier Title", min_length=5, max_length=500, restricted_keywords_check=True)
        if not title_validation['valid']:
            validation_result['valid'] = False
            validation_result['issues'].extend(title_validation['issues'])
        validation_result['warnings'].extend(title_validation.get('warnings', []))
        
        # Validate price
        if 'price' in product_data:
            price_validation = self._validate_price(product_data['price'])
            if not price_validation['valid']:
                validation_result['valid'] = False
                validation_result['issues'].extend(price_validation['issues'])
            validation_result['warnings'].extend(price_validation.get('warnings', []))
        
        # Validate URL
        if 'url' in product_data:
            url_validation = self._validate_url(product_data['url'])
            if not url_validation['valid']:
                validation_result['valid'] = False
                validation_result['issues'].extend(url_validation['issues'])
        
        # Validate identifiers if present
        if product_data.get('ean'):
            ean_validation = self._validate_ean(product_data['ean'])
            if not ean_validation['valid']:
                validation_result['warnings'].append(f"Invalid Supplier EAN: {ean_validation['issue']}")
                validation_result['data_quality_score'] -= 5
        
        # Validate description
        desc_validation = self._validate_text_field(product_data.get('description'), "Supplier Description", min_length=10, max_length=3000, allow_empty=True, restricted_keywords_check=True)
        if not desc_validation['valid']: # Not a hard fail for description
            validation_result['warnings'].extend(desc_validation['issues'])
            validation_result['data_quality_score'] -= 5
        validation_result['warnings'].extend(desc_validation.get('warnings', []))

        # Validate images
        img_validation = self._validate_image_urls(product_data.get('images'), "Supplier Images")
        if not img_validation['valid']: # Not a hard fail for images
            validation_result['warnings'].extend(img_validation['issues'])
            validation_result['data_quality_score'] -= 5
        validation_result['warnings'].extend(img_validation.get('warnings', []))
        
        # Validate brand
        brand_validation = self._validate_text_field(product_data.get('brand'), "Supplier Brand", min_length=1, max_length=100, allow_empty=True)
        if not brand_validation['valid']:
             validation_result['warnings'].extend(brand_validation['issues']) # Not a hard fail
        validation_result['warnings'].extend(brand_validation.get('warnings', []))

        # Validate model number
        model_validation = self._validate_text_field(product_data.get('model_number'), "Supplier Model Number", min_length=1, max_length=50, allow_empty=True)
        if not model_validation['valid']:
             validation_result['warnings'].extend(model_validation['issues']) # Not a hard fail
        validation_result['warnings'].extend(model_validation.get('warnings', []))

        # Validate extracted weight and dimensions
        weight_val = self._validate_extracted_weight(product_data.get('weight'))
        if not weight_val['valid']:
            validation_result['issues'].extend([f"Supplier Weight: {issue}" for issue in weight_val['issues']])
        validation_result['warnings'].extend([f"Supplier Weight: {warn}" for warn in weight_val['warnings']])

        dim_val = self._validate_extracted_dimensions(product_data.get('dimensions'))
        if not dim_val['valid']:
            validation_result['issues'].extend([f"Supplier Dimensions: {issue}" for issue in dim_val['issues']])
        validation_result['warnings'].extend([f"Supplier Dimensions: {warn}" for warn in dim_val['warnings']])

        # Check for restricted products (based on title and description)
        # This uses the internal restricted_keywords list
        if self._is_text_restricted(product_data.get('title',"") + " " + product_data.get('description',"")):
            validation_result['valid'] = False
            validation_result['issues'].append(f"Restricted product based on title/description keywords.")
            validation_result['data_quality_score'] -= 30

        # Calculate final quality score
        validation_result['data_quality_score'] = max(0, validation_result['data_quality_score'])
        
        return validation_result

    def validate_amazon_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Amazon product data.
        
        Args:
            product_data: Amazon product data dict
            
        Returns:
            Validation result with status and issues
        """
        validation_result = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'data_quality_score': 100.0
        }
        
        # Check required fields
        for field in self.required_fields['amazon']:
            if field not in product_data or not product_data[field]:
                validation_result['valid'] = False
                validation_result['issues'].append(f"Missing required Amazon field: {field}")
                validation_result['data_quality_score'] -= 15
        
        # Validate ASIN
        if 'asin' in product_data:
            asin_validation = self._validate_asin(product_data['asin'])
            if not asin_validation['valid']:
                validation_result['valid'] = False
                validation_result['issues'].append(asin_validation['issue'])
        
        # Validate price
        if 'current_price' in product_data:
            price_validation = self._validate_price(product_data['current_price'])
            if not price_validation['valid']:
                validation_result['valid'] = False
                validation_result['issues'].extend(price_validation['issues'])
        
        # Validate sales rank
        if 'sales_rank' in product_data:
            rank_validation = self._validate_sales_rank(product_data['sales_rank'])
            if not rank_validation['valid']:
                validation_result['warnings'].append(rank_validation['issue'])
                validation_result['data_quality_score'] -= 5
        
        # Validate ratings
        if 'rating' in product_data:
            rating_validation = self._validate_rating(product_data['rating'])
            if not rating_validation['valid']:
                validation_result['warnings'].append(rating_validation['issue'])
                validation_result['data_quality_score'] -= 5
        
        # Validate title
        title_validation = self._validate_text_field(product_data.get('title'), "Amazon Title", min_length=5, max_length=500, restricted_keywords_check=True)
        if not title_validation['valid']:
            validation_result['valid'] = False
            validation_result['issues'].extend(title_validation['issues'])
        validation_result['warnings'].extend(title_validation.get('warnings', []))

        # Validate description
        desc_validation = self._validate_text_field(product_data.get('description'), "Amazon Description", min_length=10, max_length=3000, allow_empty=True, restricted_keywords_check=True)
        if not desc_validation['valid']:
            validation_result['warnings'].extend(desc_validation['issues'])
        validation_result['warnings'].extend(desc_validation.get('warnings', []))

        # Validate images
        img_validation = self._validate_image_urls(product_data.get('images'), "Amazon Images")
        if not img_validation['valid']:
            validation_result['warnings'].extend(img_validation['issues'])
        validation_result['warnings'].extend(img_validation.get('warnings', []))

        # Validate brand
        brand_validation = self._validate_text_field(product_data.get('brand'), "Amazon Brand", min_length=1, max_length=100, allow_empty=True)
        if not brand_validation['valid']:
             validation_result['warnings'].extend(brand_validation['issues'])
        validation_result['warnings'].extend(brand_validation.get('warnings', []))

        # Validate model number
        model_validation = self._validate_text_field(product_data.get('model_number'), "Amazon Model Number", min_length=1, max_length=50, allow_empty=True)
        if not model_validation['valid']:
             validation_result['warnings'].extend(model_validation['issues'])
        validation_result['warnings'].extend(model_validation.get('warnings', []))

        # Validate extracted weight and dimensions (using fields like 'weight_from_details')
        weight_val = self._validate_extracted_weight(product_data.get('weight')) # Assuming 'weight' is the dict from DataExtractor
        if not weight_val['valid']:
            validation_result['issues'].extend([f"Amazon Weight: {issue}" for issue in weight_val['issues']])
        validation_result['warnings'].extend([f"Amazon Weight: {warn}" for warn in weight_val['warnings']])

        dim_val = self._validate_extracted_dimensions(product_data.get('dimensions')) # Assuming 'dimensions' is the dict
        if not dim_val['valid']:
            validation_result['issues'].extend([f"Amazon Dimensions: {issue}" for issue in dim_val['issues']])
        validation_result['warnings'].extend([f"Amazon Dimensions: {warn}" for warn in dim_val['warnings']])

        # Check data completeness for other optional fields
        optional_fields_to_check = ['category', 'features'] # 'weight_from_details', 'dimensions_from_details' are now covered by dicts
        missing_optional = sum(1 for field in optional_fields_to_check if field not in product_data or not product_data[field])
        if missing_optional > 0:
            validation_result['warnings'].append(f"Missing {missing_optional} other optional Amazon fields (e.g., category, features)")
            validation_result['data_quality_score'] -= (missing_optional * 2)
        
        # Calculate final quality score
        validation_result['data_quality_score'] = max(0, validation_result['data_quality_score'])
        
        return validation_result

    def validate_combined_data(self, combined_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate combined supplier and Amazon data.
        
        Args:
            combined_data: Combined data dict with supplier and Amazon info
            
        Returns:
            Validation result with status and issues
        """
        validation_result = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'data_quality_score': 100.0,
            'match_confidence': 0.0
        }
        
        # Check required structure
        for field in self.required_fields['combined']:
            if field not in combined_data or not combined_data[field]:
                validation_result['valid'] = False
                validation_result['issues'].append(f"Missing required field in combined data: {field}")
                return validation_result # Early exit if basic structure is wrong
        
        # Validate supplier data
        supplier_validation = self.validate_supplier_product(combined_data['supplier_product_info'])
        if not supplier_validation['valid']:
            validation_result['valid'] = False # If supplier data is invalid, combined is invalid
            validation_result['issues'].extend([f"Supplier: {issue}" for issue in supplier_validation['issues']])
        validation_result['warnings'].extend([f"Supplier: {warning}" for warning in supplier_validation['warnings']])
        
        # Validate Amazon data
        amazon_validation = self.validate_amazon_product(combined_data['amazon_product_info'])
        if not amazon_validation['valid']:
            validation_result['valid'] = False # If Amazon data is invalid, combined is invalid
            validation_result['issues'].extend([f"Amazon: {issue}" for issue in amazon_validation['issues']])
        validation_result['warnings'].extend([f"Amazon: {warning}" for warning in amazon_validation['warnings']])
        
        # Validate match quality
        if 'match_validation' in combined_data:
            match_validation = combined_data['match_validation']
            validation_result['match_confidence'] = match_validation.get('confidence_score', 0.0)
            
            if match_validation.get('match_quality') == 'low':
                validation_result['warnings'].append("Low confidence product match")
                # Don't mark as invalid, but it's a strong warning
        else:
            validation_result['warnings'].append("Match validation data missing from combined_data")

        # Validate financial metrics
        if all(key in combined_data for key in ['roi_percent_calculated', 'estimated_profit_per_unit']):
            financial_validation = self._validate_financial_metrics(combined_data)
            if not financial_validation['valid']: # This might not set 'valid' to False, just adds warnings
                validation_result['warnings'].extend(financial_validation['warnings'])
        else:
            validation_result['warnings'].append("Financial metrics (ROI, profit) missing for validation")
        
        # Calculate combined quality score
        supplier_score = supplier_validation.get('data_quality_score', 50.0) # Default to 50 if not present
        amazon_score = amazon_validation.get('data_quality_score', 50.0)
        match_conf = validation_result.get('match_confidence', 0.0)

        # Weighted average, giving more weight to Amazon data and match confidence
        validation_result['data_quality_score'] = (supplier_score * 0.25 + 
                                                   amazon_score * 0.45 + 
                                                   match_conf * 30) # Match confidence scaled to 30 points
        validation_result['data_quality_score'] = max(0, min(100, validation_result['data_quality_score']))
        
        # Final validity check: if any core component was invalid, combined is invalid
        if not supplier_validation['valid'] or not amazon_validation['valid']:
            validation_result['valid'] = False
            
        return validation_result

    def _validate_title(self, title: str) -> Dict[str, Any]:
        """Validate product title."""
        # This method is now largely covered by _validate_text_field
        # Kept for backward compatibility if directly called, but prefer _validate_text_field
        return self._validate_text_field(title, "Title", min_length=5, max_length=500, restricted_keywords_check=True)

    def _validate_price(self, price: Any) -> Dict[str, Any]:
        """Validate price value."""
        result = {'valid': True, 'issues': [], 'warnings': []}
        
        if price is None:
            result['valid'] = False
            result['issues'].append("Price cannot be None")
            return result
        
        try:
            price_float = float(price)
        except (ValueError, TypeError):
            result['valid'] = False
            result['issues'].append(f"Price must be numeric, got: {type(price).__name__}")
            return result
        
        if price_float < self.price_limits['min']:
            result['valid'] = False
            result['issues'].append(f"Price too low: £{price_float:.2f} (minimum £{self.price_limits['min']})")
        elif price_float > self.price_limits['max']:
            result['valid'] = False
            result['issues'].append(f"Price too high: £{price_float:.2f} (maximum £{self.price_limits['max']})")
        
        # Warning for suspiciously round prices
        if price_float > 10 and price_float == int(price_float):
            result['warnings'].append(f"Suspiciously round price: £{price_float:.2f}")
        
        return result

    def _validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL format."""
        result = {'valid': True, 'issues': []}
        
        if not url or not isinstance(url, str):
            result['valid'] = False
            result['issues'].append("URL must be a non-empty string")
            return result
        
        # Basic URL pattern
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            result['valid'] = False
            result['issues'].append("Invalid URL format")
        
        return result

    def _validate_ean(self, ean: str) -> Dict[str, Any]:
        """Validate EAN-13 format and checksum."""
        result = {'valid': True, 'issue': ''}
        
        if not ean or not isinstance(ean, str):
            result['valid'] = False
            result['issue'] = "EAN must be a non-empty string"
            return result
        
        # Remove any spaces or dashes
        ean = re.sub(r'[\s-]', '', ean)
        
        if not ean.isdigit():
            result['valid'] = False
            result['issue'] = "EAN must contain only digits"
            return result
        
        if len(ean) != 13:
            result['valid'] = False
            result['issue'] = f"EAN must be 13 digits, got {len(ean)}"
            return result
        
        # Validate checksum
        try:
            total = sum(int(ean[i]) * (3 if i % 2 else 1) for i in range(12))
            check_digit = (10 - (total % 10)) % 10
            if check_digit != int(ean[12]):
                result['valid'] = False
                result['issue'] = "Invalid EAN checksum"
        except:
            result['valid'] = False
            result['issue'] = "Error validating EAN checksum"
        
        return result

    def _validate_asin(self, asin: str) -> Dict[str, Any]:
        """Validate Amazon ASIN format."""
        result = {'valid': True, 'issue': ''}
        
        if not asin or not isinstance(asin, str):
            result['valid'] = False
            result['issue'] = "ASIN must be a non-empty string"
            return result
        
        if not re.match(r'^[A-Z0-9]{10}$', asin):
            result['valid'] = False
            result['issue'] = f"Invalid ASIN format: {asin}"
        
        return result

    def _validate_sales_rank(self, rank: Any) -> Dict[str, Any]:
        """Validate sales rank value."""
        result = {'valid': True, 'issue': ''}
        
        if rank is None:
            return result  # Sales rank is optional
        
        try:
            rank_int = int(rank)
            if rank_int < 0: # Rank 0 is possible for new/unranked items, but negative is invalid
                result['valid'] = False
                result['issue'] = "Sales rank cannot be negative"
            elif rank_int > 20000000: # Arbitrary upper limit for sanity
                result['warnings'].append(f"Sales rank seems unrealistically high: {rank_int}")
        except (ValueError, TypeError):
            result['valid'] = False
            result['issue'] = f"Sales rank must be numeric, got: {type(rank).__name__}"
        
        return result

    def _validate_rating(self, rating: Any) -> Dict[str, Any]:
        """Validate product rating."""
        result = {'valid': True, 'issue': ''}
        
        if rating is None:
            return result  # Rating is optional
        
        try:
            rating_float = float(rating)
            if rating_float < 0 or rating_float > 5:
                result['valid'] = False
                result['issue'] = f"Rating must be between 0 and 5, got: {rating_float}"
        except (ValueError, TypeError):
            result['valid'] = False
            result['issue'] = f"Rating must be numeric, got: {type(rating).__name__}"
        
        return result

    def _is_text_restricted(self, text: str) -> bool:
        """Helper to check if a combined text contains restricted keywords."""
        if not text: return False
        text_lower = text.lower()
        for keyword in self.restricted_keywords:
            if keyword in text_lower:
                return True
        return False

    def _check_restricted_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if product contains restricted keywords in title or description."""
        # This method is now largely covered by _is_text_restricted and individual field validations
        # Kept for conceptual clarity if needed, but logic is integrated elsewhere.
        result = {'restricted': False, 'reason': ''}
        combined_text = str(product_data.get('title', '')) + " " + str(product_data.get('description', ''))
        if self._is_text_restricted(combined_text):
            result['restricted'] = True
            # Find first keyword for reason
            for keyword in self.restricted_keywords:
                if keyword in combined_text.lower():
                    result['reason'] = f"Product data contains restricted keyword: {keyword}"
                    break
        return result
        
    def _validate_financial_metrics(self, combined_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate financial calculations."""
        result = {'valid': True, 'warnings': []} # valid is always true, only warnings
        
        roi = combined_data.get('roi_percent_calculated', 0)
        profit = combined_data.get('estimated_profit_per_unit', 0)
        supplier_price = combined_data.get('supplier_product_info', {}).get('price', 0)
        amazon_price = combined_data.get('amazon_product_info', {}).get('current_price', 0)
        
        if not isinstance(supplier_price, (int, float)) or supplier_price <=0:
             result['warnings'].append(f"Supplier price is invalid for financial validation: {supplier_price}")
             return result # Cant do much more if supplier price is bad
        if not isinstance(amazon_price, (int, float)) or amazon_price <=0:
             result['warnings'].append(f"Amazon price is invalid for financial validation: {amazon_price}")
             # Can still check some things

        if roi > 1000 and profit > 0: # Only if profitable
            result['warnings'].append(f"Unusually high ROI: {roi}%")
        
        if profit > amazon_price * 0.8 and amazon_price > 0: # Avoid division by zero
            result['warnings'].append(f"Profit margin (£{profit:.2f}) seems very high compared to Amazon price (£{amazon_price:.2f})")
        
        if supplier_price > amazon_price and amazon_price > 0 : # Only if amazon price is valid
            result['warnings'].append(f"Supplier price (£{supplier_price:.2f}) higher than Amazon price (£{amazon_price:.2f})")
        
        if profit < 0 and roi > 0:
            result['warnings'].append(f"Contradictory financials: Negative profit (£{profit:.2f}) but positive ROI ({roi}%)")

        return result

    def _validate_text_field(self, text: Optional[str], field_name: str, min_length: int = 1, max_length: int = 5000, allow_empty: bool = False, restricted_keywords_check: bool = False) -> Dict[str, Any]:
        """Generic validation for a text field."""
        result = {'valid': True, 'issues': [], 'warnings': []}
        
        if text is None:
            if not allow_empty:
                result['valid'] = False
                result['issues'].append(f"{field_name} cannot be None")
            return result

        if not isinstance(text, str):
            result['valid'] = False
            result['issues'].append(f"{field_name} must be a string, got {type(text).__name__}")
            return result

        if not allow_empty and not text.strip():
            result['valid'] = False
            result['issues'].append(f"{field_name} cannot be empty or just whitespace")
            return result
        
        text_len = len(text)
        if not allow_empty and text_len < min_length:
            result['valid'] = False
            result['issues'].append(f"{field_name} too short (minimum {min_length} characters), got {text_len}")
        
        if text_len > max_length:
            result['warnings'].append(f"{field_name} very long (over {max_length} characters), got {text_len}")

        if restricted_keywords_check:
            if self._is_text_restricted(text): # Use helper
                 result['warnings'].append(f"{field_name} contains restricted keyword(s).")
        
        return result

    def _validate_image_urls(self, image_urls: Optional[List[str]], field_name: str = "images") -> Dict[str, Any]:
        """Validate a list of image URLs."""
        result = {'valid': True, 'issues': [], 'warnings': []}
        
        if image_urls is None:
            result['warnings'].append(f"{field_name} list is None (optional field)")
            return result 

        if not isinstance(image_urls, list):
            result['valid'] = False
            result['issues'].append(f"{field_name} must be a list, got {type(image_urls).__name__}")
            return result

        if not image_urls: 
            result['warnings'].append(f"No {field_name} provided (optional field).")
            return result

        for i, url in enumerate(image_urls):
            url_validation = self._validate_url(url)
            if not url_validation['valid']:
                result['valid'] = False 
                result['issues'].append(f"Invalid URL for {field_name}[{i}]: {url_validation['issues'][0]}")
            
            if not re.search(r'\.(jpeg|jpg|gif|png|webp)(\?.*)?$', str(url), re.IGNORECASE): # Ensure url is str
                result['warnings'].append(f"Image URL for {field_name}[{i}] ('{str(url)[:50]}...') does not have a common image extension.")
        
        return result

    def _validate_extracted_weight(self, weight_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the structure and values of extracted weight data."""
        result = {'valid': True, 'issues': [], 'warnings': []}
        if weight_data is None:
            result['warnings'].append("Weight data is missing (optional field)")
            return result

        if not isinstance(weight_data, dict):
            result['valid'] = False
            result['issues'].append(f"Weight data must be a dict, got {type(weight_data).__name__}")
            return result

        required_keys = ['value', 'unit', 'pounds']
        missing_keys = [key for key in required_keys if key not in weight_data]
        if missing_keys:
            result['valid'] = False
            result['issues'].append(f"Weight data missing key(s): {', '.join(missing_keys)}")
        
        if not result['valid']: return result

        value = weight_data.get('value')
        unit = weight_data.get('unit')
        pounds = weight_data.get('pounds')

        if not isinstance(value, (int, float)) or value <= 0:
            result['valid'] = False
            result['issues'].append(f"Weight value must be a positive number, got {value}")
        if not isinstance(unit, str) or not unit.strip():
            result['valid'] = False
            result['issues'].append(f"Weight unit must be a non-empty string, got {unit}")
        if not isinstance(pounds, (int, float)) or pounds <= 0:
            result['valid'] = False
            result['issues'].append(f"Weight in pounds must be a positive number, got {pounds}")
        
        if pounds < self.weight_limits['min_pounds']:
            result['warnings'].append(f"Weight {pounds:.2f} lbs is below minimum {self.weight_limits['min_pounds']} lbs")
        if pounds > self.weight_limits['max_pounds']:
            result['valid'] = False 
            result['issues'].append(f"Weight {pounds:.2f} lbs exceeds maximum {self.weight_limits['max_pounds']} lbs (FBA limit)")
            
        return result

    def _validate_extracted_dimensions(self, dimension_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the structure and values of extracted dimension data."""
        result = {'valid': True, 'issues': [], 'warnings': []}
        if dimension_data is None:
            result['warnings'].append("Dimension data is missing (optional field)")
            return result

        if not isinstance(dimension_data, dict):
            result['valid'] = False
            result['issues'].append(f"Dimension data must be a dict, got {type(dimension_data).__name__}")
            return result

        required_keys = ['length', 'width', 'height', 'unit', 'inches']
        missing_keys = [key for key in required_keys if key not in dimension_data]
        if missing_keys:
            result['valid'] = False
            result['issues'].append(f"Dimension data missing key(s): {', '.join(missing_keys)}")

        if not result['valid']: return result

        length = dimension_data.get('length')
        width = dimension_data.get('width')
        height = dimension_data.get('height')
        unit = dimension_data.get('unit')
        inches_tuple = dimension_data.get('inches')

        dim_values = {'length': length, 'width': width, 'height': height}
        for name, val in dim_values.items():
            if not isinstance(val, (int, float)) or val <= 0:
                result['valid'] = False
                result['issues'].append(f"Dimension {name} must be a positive number, got {val}")
        
        if not isinstance(unit, str) or not unit.strip():
            result['valid'] = False
            result['issues'].append(f"Dimension unit must be a non-empty string, got {unit}")

        if not isinstance(inches_tuple, tuple) or len(inches_tuple) != 3 or not all(isinstance(d, (int, float)) and d > 0 for d in inches_tuple):
            result['valid'] = False
            result['issues'].append(f"Dimensions in inches must be a tuple of 3 positive numbers, got {inches_tuple}")
        else:
            l_in, w_in, h_in = inches_tuple
            dims_sorted = sorted([l_in, w_in, h_in])
            longest_side = dims_sorted[2]
            median_side = dims_sorted[1]
            shortest_side = dims_sorted[0]

            if longest_side > self.dimension_limits['max_length_inches']:
                result['valid'] = False 
                result['issues'].append(f"Longest dimension {longest_side:.2f} inches exceeds FBA max length {self.dimension_limits['max_length_inches']} inches")
            
            girth = longest_side + 2 * (median_side + shortest_side)
            if girth > self.dimension_limits['max_girth_inches']:
                result['valid'] = False 
                result['issues'].append(f"Girth {girth:.2f} inches (L + 2*(W+H)) exceeds FBA max girth {self.dimension_limits['max_girth_inches']} inches")

            for d_val, d_name_suffix in zip(inches_tuple, ["length", "width", "height"]):
                 dim_name = f"{d_name_suffix}_inches"
                 if d_val < self.dimension_limits['min_inches']:
                     result['warnings'].append(f"Dimension {dim_name} {d_val:.2f} inches is below minimum {self.dimension_limits['min_inches']} inches")
        return result

    def generate_validation_report(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary report from multiple validation results.
        
        Args:
            validation_results: List of validation results
            
        Returns:
            Summary report
        """
        total = len(validation_results)
        valid_count = sum(1 for r in validation_results if r.get('valid', False)) # Use .get for safety
        
        all_issues: List[str] = []
        all_warnings: List[str] = []
        quality_scores: List[float] = []
        
        for res in validation_results:
            all_issues.extend(res.get('issues', []))
            all_warnings.extend(res.get('warnings', []))
            quality_scores.append(res.get('data_quality_score', 0.0)) # Default to 0.0
        
        issue_counts: Dict[str, int] = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        warning_counts: Dict[str, int] = {}
        for warning in all_warnings:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_products_validated': total,
            'valid_products_count': valid_count,
            'invalid_products_count': total - valid_count,
            'overall_validation_rate_percent': (valid_count / total * 100) if total > 0 else 0,
            'average_data_quality_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'common_issues_top_10': sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'common_warnings_top_10': sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'data_quality_score_distribution': {
                'excellent_90_plus': sum(1 for s in quality_scores if s >= 90),
                'good_70_89': sum(1 for s in quality_scores if 70 <= s < 90),
                'fair_50_69': sum(1 for s in quality_scores if 50 <= s < 70),
                'poor_below_50': sum(1 for s in quality_scores if s < 50)
            }
        }
        
        return report