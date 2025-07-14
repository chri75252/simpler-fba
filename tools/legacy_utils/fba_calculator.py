"""
FBA Calculator for Amazon FBA fee calculations.
Implements fee structures for different product categories and sizes.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FBACalculator:
    """
    Calculate Amazon FBA fees based on product dimensions, weight, and category.
    
    Fee structure based on Amazon's 2024 FBA fee schedule.
    """
    
    def __init__(self):
        """Initialize FBA Calculator with current fee structures."""
        # Standard size tiers (in pounds and inches)
        self.size_tiers = {
            'small_standard': {
                'max_weight': 1.0,  # pounds
                'max_dimensions': (15, 12, 0.75),  # length, width, height in inches
                'fee': 3.22
            },
            'large_standard': {
                'max_weight': 20.0,
                'max_dimensions': (18, 14, 8),
                'fee': 5.42
            },
            'small_oversize': {
                'max_weight': 70.0,
                'max_dimensions': (60, 30, None),  # No height limit
                'fee': 9.73
            },
            'medium_oversize': {
                'max_weight': 150.0,
                'max_dimensions': (108, None, None),
                'fee': 19.05
            },
            'large_oversize': {
                'max_weight': 150.0,
                'max_dimensions': (108, None, None),
                'fee': 89.98
            },
            'special_oversize': {
                'max_weight': float('inf'),
                'max_dimensions': (None, None, None),
                'fee': 158.49
            }
        }
        
        # Referral fees by category (percentage)
        self.referral_fees = {
            'electronics': 0.08,  # 8%
            'computers': 0.08,
            'video_games': 0.08,
            'books': 0.15,  # 15%
            'music': 0.15,
            'dvd': 0.15,
            'video': 0.15,
            'toys': 0.15,
            'games': 0.15,
            'home': 0.15,
            'kitchen': 0.15,
            'sports': 0.15,
            'outdoors': 0.15,
            'tools': 0.15,
            'grocery': 0.08,  # 8% for items under £10, 15% over
            'health': 0.08,
            'beauty': 0.08,
            'clothing': 0.17,  # 17%
            'shoes': 0.15,
            'jewelry': 0.20,  # 20%
            'watches': 0.16,  # 16%
            'default': 0.15  # Default 15%
        }
        
        # Storage fees per cubic foot per month
        self.storage_fees = {
            'standard_size': {
                'jan_sep': 0.75,  # January - September
                'oct_dec': 2.40   # October - December (peak season)
            },
            'oversize': {
                'jan_sep': 0.48,
                'oct_dec': 1.20
            }
        }
        
        # Additional fees
        self.additional_fees = {
            'closing_fee': 1.80,  # Media items only
            'high_volume_listing_fee': 0.005,  # Per item over 2 million
            'removal_order_fee': 0.50,  # Per item
            'disposal_order_fee': 0.30,  # Per item
            'unplanned_service_fee': 0.30  # Per item for prep services
        }
        
        # Restricted categories that may have additional requirements
        self.restricted_categories = [
            'hazardous_materials',
            'batteries',
            'magnets',
            'food_and_beverage',
            'cosmetics',
            'dietary_supplements',
            'medical_devices',
            'pesticides'
        ]

    def calculate_fees(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate all FBA fees for a product.
        
        Args:
            product_data: Dictionary containing:
                - weight: Product weight in pounds
                - dimensions: Tuple of (length, width, height) in inches
                - category: Product category
                - price: Selling price
                - is_media: Boolean indicating if it's a media item
                - monthly_units: Estimated monthly sales volume
                
        Returns:
            Dictionary containing:
                - fulfillment_fee: FBA fulfillment fee
                - referral_fee: Amazon referral fee
                - total_fees: Total of all fees
                - size_tier: Determined size tier
                - monthly_storage_fee: Estimated monthly storage fee
                - is_restricted: Whether category is restricted
                - fee_breakdown: Detailed breakdown of all fees
        """
        try:
            # Extract product data
            weight = product_data.get('weight', 0)
            dimensions = product_data.get('dimensions', (0, 0, 0))
            category = product_data.get('category', 'default').lower()
            price = product_data.get('price', 0)
            is_media = product_data.get('is_media', False)
            monthly_units = product_data.get('monthly_units', 100)
            
            # Validate input data
            if not self._validate_product_data(product_data):
                raise ValueError("Invalid product data provided")
            
            # Determine size tier
            size_tier = self._determine_size_tier(weight, dimensions)
            
            # Calculate fulfillment fee
            fulfillment_fee = self._calculate_fulfillment_fee(size_tier, weight)
            
            # Calculate referral fee
            referral_fee = self._calculate_referral_fee(price, category)
            
            # Calculate storage fee
            monthly_storage_fee = self._calculate_storage_fee(
                dimensions, size_tier, monthly_units
            )
            
            # Check if category is restricted
            is_restricted = self._is_restricted_category(category)
            
            # Calculate additional fees
            additional_fees = 0
            if is_media:
                additional_fees += self.additional_fees['closing_fee']
            
            # Total fees
            total_fees = fulfillment_fee + referral_fee + monthly_storage_fee + additional_fees
            
            # Create fee breakdown
            fee_breakdown = {
                'fulfillment_fee': round(fulfillment_fee, 2),
                'referral_fee': round(referral_fee, 2),
                'monthly_storage_fee': round(monthly_storage_fee, 2),
                'additional_fees': round(additional_fees, 2),
                'total_fees': round(total_fees, 2)
            }
            
            result = {
                'fulfillment_fee': round(fulfillment_fee, 2),
                'referral_fee': round(referral_fee, 2),
                'total_fees': round(total_fees, 2),
                'size_tier': size_tier,
                'monthly_storage_fee': round(monthly_storage_fee, 2),
                'is_restricted': is_restricted,
                'fee_breakdown': fee_breakdown,
                'calculation_date': datetime.now().isoformat()
            }
            
            logger.info(f"Calculated FBA fees for product: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating FBA fees: {str(e)}")
            return {
                'error': str(e),
                'fulfillment_fee': None,
                'referral_fee': None,
                'total_fees': None,
                'size_tier': None,
                'monthly_storage_fee': None,
                'is_restricted': None,
                'fee_breakdown': None
            }

    def _validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """Validate product data for fee calculation."""
        required_fields = ['weight', 'dimensions', 'price']
        
        for field in required_fields:
            if field not in product_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate weight
        if product_data['weight'] <= 0:
            logger.error("Weight must be positive")
            return False
        
        # Validate dimensions
        dimensions = product_data['dimensions']
        if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 3:
            logger.error("Dimensions must be a tuple/list of 3 values")
            return False
        
        if any(d < 0 for d in dimensions if d is not None):
            logger.error("Dimensions must be non-negative")
            return False
        
        # Validate price
        if product_data['price'] < 0:
            logger.error("Price must be non-negative")
            return False
        
        return True

    def _determine_size_tier(self, weight: float, dimensions: Tuple[float, float, float]) -> str:
        """
        Determine the size tier based on weight and dimensions.
        
        Args:
            weight: Weight in pounds
            dimensions: (length, width, height) in inches
            
        Returns:
            Size tier string
        """
        length, width, height = sorted(dimensions, reverse=True)  # Sort to get longest side first
        
        # Check small standard
        if (weight <= self.size_tiers['small_standard']['max_weight'] and
            length <= 15 and width <= 12 and height <= 0.75):
            return 'small_standard'
        
        # Check large standard
        if (weight <= self.size_tiers['large_standard']['max_weight'] and
            length <= 18 and width <= 14 and height <= 8):
            return 'large_standard'
        
        # Calculate dimensional weight
        dimensional_weight = (length * width * height) / 139
        unit_weight = max(weight, dimensional_weight)
        
        # Check oversize tiers
        if unit_weight <= 70 and length + 2 * (width + height) <= 130:
            return 'small_oversize'
        elif unit_weight <= 150 and length + 2 * (width + height) <= 165:
            return 'medium_oversize'
        elif unit_weight <= 150 and length + 2 * (width + height) <= 165:
            return 'large_oversize'
        else:
            return 'special_oversize'

    def _calculate_fulfillment_fee(self, size_tier: str, weight: float) -> float:
        """
        Calculate fulfillment fee based on size tier and weight.
        
        Args:
            size_tier: Product size tier
            weight: Product weight in pounds
            
        Returns:
            Fulfillment fee amount
        """
        base_fee = self.size_tiers[size_tier]['fee']
        
        # Add weight-based fees for heavier items
        if size_tier in ['small_oversize', 'medium_oversize', 'large_oversize']:
            if weight > 90:
                base_fee += (weight - 90) * 0.42  # Additional fee per pound over 90 lbs
        
        return base_fee

    def _calculate_referral_fee(self, price: float, category: str) -> float:
        """
        Calculate referral fee based on price and category.
        
        Args:
            price: Selling price
            category: Product category
            
        Returns:
            Referral fee amount
        """
        # Get category-specific rate or default
        rate = self.referral_fees.get(category, self.referral_fees['default'])
        
        # Special case for grocery items
        if category == 'grocery' and price > 10:
            rate = 0.15
        
        # Minimum referral fee is £0.30
        referral_fee = max(price * rate, 0.30)
        
        return referral_fee

    def _calculate_storage_fee(self, dimensions: Tuple[float, float, float], 
                              size_tier: str, monthly_units: int) -> float:
        """
        Calculate monthly storage fee based on dimensions and sales volume.
        
        Args:
            dimensions: Product dimensions (length, width, height) in inches
            size_tier: Product size tier
            monthly_units: Estimated monthly sales
            
        Returns:
            Monthly storage fee
        """
        # Calculate cubic feet
        length, width, height = dimensions
        cubic_feet = (length * width * height) / 1728  # Convert cubic inches to cubic feet
        
        # Determine if standard or oversize
        is_oversize = 'oversize' in size_tier
        
        # Get current month to determine season
        current_month = datetime.now().month
        is_peak_season = current_month >= 10  # October through December
        
        # Get appropriate rate
        if is_oversize:
            rate = self.storage_fees['oversize']['oct_dec' if is_peak_season else 'jan_sep']
        else:
            rate = self.storage_fees['standard_size']['oct_dec' if is_peak_season else 'jan_sep']
        
        # Calculate average inventory (assuming 2 weeks of inventory)
        average_inventory = monthly_units / 2
        
        # Calculate total storage fee
        storage_fee = cubic_feet * rate * average_inventory / monthly_units
        
        return storage_fee

    def _is_restricted_category(self, category: str) -> bool:
        """
        Check if the category is restricted and may require additional approval.
        
        Args:
            category: Product category
            
        Returns:
            True if category is restricted
        """
        return category.lower() in self.restricted_categories

    def calculate_profitability(self, product_data: Dict[str, Any], 
                               supplier_cost: float) -> Dict[str, Any]:
        """
        Calculate profitability metrics including ROI and profit margin.
        
        Args:
            product_data: Product data for fee calculation
            supplier_cost: Cost from supplier including shipping
            
        Returns:
            Dictionary with profitability metrics
        """
        # Calculate fees
        fee_result = self.calculate_fees(product_data)
        
        if fee_result.get('error'):
            return {
                'error': fee_result['error'],
                'profitable': False
            }
        
        selling_price = product_data.get('price', 0)
        total_fees = fee_result['total_fees']
        
        # Calculate profit
        total_cost = supplier_cost + total_fees
        profit = selling_price - total_cost
        
        # Calculate metrics
        roi = (profit / supplier_cost * 100) if supplier_cost > 0 else 0
        profit_margin = (profit / selling_price * 100) if selling_price > 0 else 0
        
        # Determine if profitable (minimum 30% ROI recommended)
        is_profitable = roi >= 30 and profit > 2  # At least £2 profit
        
        return {
            'selling_price': round(selling_price, 2),
            'supplier_cost': round(supplier_cost, 2),
            'total_fees': round(total_fees, 2),
            'total_cost': round(total_cost, 2),
            'profit': round(profit, 2),
            'roi': round(roi, 2),
            'profit_margin': round(profit_margin, 2),
            'profitable': is_profitable,
            'fee_breakdown': fee_result['fee_breakdown'],
            'size_tier': fee_result['size_tier'],
            'is_restricted': fee_result['is_restricted']
        }


# Example usage and testing
if __name__ == "__main__":
    calculator = FBACalculator()
    
    # Test product 1: Small electronics item
    test_product_1 = {
        'weight': 0.5,  # pounds
        'dimensions': (6, 4, 1),  # inches
        'category': 'electronics',
        'price': 29.99,
        'is_media': False,
        'monthly_units': 200
    }
    
    print("Test Product 1 - Small Electronics:")
    print("-" * 50)
    fees_1 = calculator.calculate_fees(test_product_1)
    print(f"Size Tier: {fees_1['size_tier']}")
    print(f"Fulfillment Fee: £{fees_1['fulfillment_fee']}")
    print(f"Referral Fee: £{fees_1['referral_fee']}")
    print(f"Monthly Storage Fee: £{fees_1['monthly_storage_fee']}")
    print(f"Total Fees: £{fees_1['total_fees']}")
    print(f"Restricted Category: {fees_1['is_restricted']}")
    
    # Calculate profitability
    profitability_1 = calculator.calculate_profitability(test_product_1, supplier_cost=10.00)
    print(f"\nProfitability Analysis:")
    print(f"Supplier Cost: £{profitability_1['supplier_cost']}")
    print(f"Total Cost: £{profitability_1['total_cost']}")
    print(f"Profit: £{profitability_1['profit']}")
    print(f"ROI: {profitability_1['roi']}%")
    print(f"Profit Margin: {profitability_1['profit_margin']}%")
    print(f"Profitable: {profitability_1['profitable']}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Test product 2: Large home item
    test_product_2 = {
        'weight': 15,  # pounds
        'dimensions': (20, 16, 10),  # inches
        'category': 'home',
        'price': 89.99,
        'is_media': False,
        'monthly_units': 50
    }
    
    print("Test Product 2 - Large Home Item:")
    print("-" * 50)
    fees_2 = calculator.calculate_fees(test_product_2)
    print(f"Size Tier: {fees_2['size_tier']}")
    print(f"Fulfillment Fee: £{fees_2['fulfillment_fee']}")
    print(f"Referral Fee: £{fees_2['referral_fee']}")
    print(f"Monthly Storage Fee: £{fees_2['monthly_storage_fee']}")
    print(f"Total Fees: £{fees_2['total_fees']}")
    
    # Calculate profitability
    profitability_2 = calculator.calculate_profitability(test_product_2, supplier_cost=35.00)
    print(f"\nProfitability Analysis:")
    print(f"Supplier Cost: £{profitability_2['supplier_cost']}")
    print(f"Total Cost: £{profitability_2['total_cost']}")
    print(f"Profit: £{profitability_2['profit']}")
    print(f"ROI: {profitability_2['roi']}%")
    print(f"Profit Margin: {profitability_2['profit_margin']}%")
    print(f"Profitable: {profitability_2['profitable']}")