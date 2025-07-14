"""
Advanced Price and Profit Analysis Module
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import statistics

log = logging.getLogger(__name__)

@dataclass
class PricePoint:
    """Represents a price at a specific point in time."""
    price: float
    currency: str
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = None

@dataclass
class ProfitAnalysis:
    """Complete profit analysis for a product."""
    supplier_cost: float
    amazon_price: float
    fba_fees: float
    gross_profit: float
    net_profit: float
    roi_percent: float
    profit_margin: float
    break_even_price: float
    recommended_price: float
    confidence_score: float

class PriceAnalyzer:
    """
    Comprehensive price and profit analysis system.
    """
    
    def __init__(self, fba_calculator, currency_converter=None):
        self.fba_calculator = fba_calculator
        self.currency_converter = currency_converter
        self.price_history: Dict[str, List[PricePoint]] = defaultdict(list)
        self.market_data_cache: Dict[str, Any] = {}
        
    async def analyze_product_profitability(self, 
                                          supplier_product: Dict[str, Any],
                                          amazon_product: Dict[str, Any],
                                          market_data: Optional[Dict[str, Any]] = None) -> ProfitAnalysis:
        """
        Perform comprehensive profitability analysis.
        
        Args:
            supplier_product: Product data from supplier
            amazon_product: Product data from Amazon
            market_data: Additional market data (competitors, trends, etc.)
            
        Returns:
            Complete profit analysis
        """
        # Extract and normalize prices
        supplier_price = await self._normalize_price(
            supplier_product.get('price'),
            supplier_product.get('currency', 'GBP')
        )
        
        amazon_price = await self._normalize_price(
            amazon_product.get('current_price'),
            'GBP'  # Amazon UK prices
        )
        
        # Calculate FBA fees
        fba_fees = self._calculate_comprehensive_fees(amazon_product)
        
        # Basic profit calculations
        gross_profit = amazon_price - supplier_price
        net_profit = gross_profit - fba_fees
        
        # Calculate ROI and margins
        roi_percent = (net_profit / supplier_price) * 100 if supplier_price > 0 else 0
        profit_margin = (net_profit / amazon_price) * 100 if amazon_price > 0 else 0
        
        # Calculate break-even and recommended prices
        break_even_price = supplier_price + fba_fees
        recommended_price = await self._calculate_recommended_price(
            supplier_price=supplier_price,
            fba_fees=fba_fees,
            market_data=market_data,
            amazon_product=amazon_product
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            supplier_product=supplier_product,
            amazon_product=amazon_product,
            market_data=market_data
        )
        
        # Store price history
        self._record_price_history(
            product_id=amazon_product.get('asin', supplier_product.get('ean')),
            supplier_price=supplier_price,
            amazon_price=amazon_price
        )
        
        return ProfitAnalysis(
            supplier_cost=supplier_price,
            amazon_price=amazon_price,
            fba_fees=fba_fees,
            gross_profit=gross_profit,
            net_profit=net_profit,
            roi_percent=roi_percent,
            profit_margin=profit_margin,
            break_even_price=break_even_price,
            recommended_price=recommended_price,
            confidence_score=confidence_score
        )
    
    async def _normalize_price(self, price: Any, currency: str) -> float:
        """Normalize price to GBP."""
        if price is None:
            return 0.0
            
        # Extract numeric value
        if isinstance(price, str):
            import re
            match = re.search(r'[\d,]+\.?\d*', price)
            if match:
                price = float(match.group().replace(',', ''))
            else:
                return 0.0
        else:
            price = float(price)
        
        # Convert currency if needed
        if currency != 'GBP' and self.currency_converter:
            price = await self.currency_converter.convert(price, currency, 'GBP')
            
        return price
    
    def _calculate_comprehensive_fees(self, amazon_product: Dict[str, Any]) -> float:
        """Calculate all FBA fees including storage."""
        # Use the FBA calculator for accurate fee calculation
        product_data = {
            'weight': self._extract_weight(amazon_product),
            'dimensions': self._extract_dimensions(amazon_product),
            'category': amazon_product.get('category', 'default'),
            'price': amazon_product.get('current_price', 0),
            'is_media': self._is_media_product(amazon_product),
            'monthly_units': amazon_product.get('estimated_monthly_sales', 100)
        }
        
        fee_result = self.fba_calculator.calculate_fees(product_data)
        return fee_result.get('total_fees', 0) if not fee_result.get('error') else 0
    
    async def _calculate_recommended_price(self,
                                         supplier_price: float,
                                         fba_fees: float,
                                         market_data: Optional[Dict[str, Any]],
                                         amazon_product: Dict[str, Any]) -> float:
        """
        Calculate optimal selling price based on multiple factors.
        """
        # Base calculation: cost + fees + target profit margin
        target_margin = 0.35  # 35% profit margin
        base_price = (supplier_price + fba_fees) / (1 - target_margin)
        
        # Adjust based on competition
        if market_data and 'competitor_prices' in market_data:
            competitor_prices = market_data['competitor_prices']
            if competitor_prices:
                avg_competitor_price = statistics.mean(competitor_prices)
                # Price slightly below average competitor
                competitive_price = avg_competitor_price * 0.95
                
                # Balance between profit target and competitive pricing
                base_price = (base_price + competitive_price) / 2
        
        # Adjust based on sales rank
        sales_rank = amazon_product.get('sales_rank', 0)
        if 0 < sales_rank < 1000:
            # High demand, can price higher
            base_price *= 1.1
        elif sales_rank > 100000:
            # Lower demand, need competitive pricing
            base_price *= 0.95
            
        # Round to psychological pricing
        return self._apply_psychological_pricing(base_price)
    
    def _apply_psychological_pricing(self, price: float) -> float:
        """Apply psychological pricing strategies."""
        if price < 10:
            # End in .99 for low prices
            return float(int(price) + 0.99)
        elif price < 50:
            # End in .95 or .99 for medium prices
            return float(int(price) + 0.95)
        else:
            # Round to nearest .00 for higher prices
            return float(round(price))
    
    def _calculate_confidence_score(self,
                                   supplier_product: Dict[str, Any],
                                   amazon_product: Dict[str, Any],
                                   market_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate confidence score for the analysis (0-100).
        """
        score = 100.0
        
        # Reduce score for missing data
        if not supplier_product.get('ean'):
            score -= 10
        if not amazon_product.get('sales_rank'):
            score -= 15
        if not amazon_product.get('review_count'):
            score -= 10
        if not market_data:
            score -= 20
            
        # Reduce score for low match confidence
        match_confidence = amazon_product.get('match_confidence', 0.5)
        score *= match_confidence
        
        # Reduce score for volatile prices
        if hasattr(self, '_is_price_volatile'):
            product_id = amazon_product.get('asin')
            if product_id and self._is_price_volatile(product_id):
                score -= 15
                
        return max(0, min(100, score))
    
    def _record_price_history(self, product_id: str, supplier_price: float, amazon_price: float):
        """Record price points for historical analysis."""
        timestamp = datetime.now()
        
        self.price_history[f"{product_id}_supplier"].append(
            PricePoint(
                price=supplier_price,
                currency='GBP',
                timestamp=timestamp,
                source='supplier'
            )
        )
        
        self.price_history[f"{product_id}_amazon"].append(
            PricePoint(
                price=amazon_price,
                currency='GBP',
                timestamp=timestamp,
                source='amazon'
            )
        )
    
    async def get_price_trends(self, product_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze price trends over specified period.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        supplier_history = [
            p for p in self.price_history.get(f"{product_id}_supplier", [])
            if p.timestamp >= cutoff_date
        ]
        
        amazon_history = [
            p for p in self.price_history.get(f"{product_id}_amazon", [])
            if p.timestamp >= cutoff_date
        ]
        
        return {
            'supplier_trend': self._calculate_trend(supplier_history),
            'amazon_trend': self._calculate_trend(amazon_history),
            'price_volatility': self._calculate_volatility(amazon_history),
            'optimal_buying_time': self._find_optimal_buying_time(supplier_history)
        }
    
    def _calculate_trend(self, price_history: List[PricePoint]) -> Dict[str, Any]:
        """Calculate price trend from history."""
        if len(price_history) < 2:
            return {'trend': 'insufficient_data', 'change_percent': 0}
            
        prices = [p.price for p in price_history]
        first_price = prices[0]
        last_price = prices[-1]
        
        change_percent = ((last_price - first_price) / first_price) * 100
        
        if change_percent > 5:
            trend = 'increasing'
        elif change_percent < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'
            
        return {
            'trend': trend,
            'change_percent': change_percent,
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': statistics.mean(prices)
        }
    
    def _calculate_volatility(self, price_history: List[PricePoint]) -> float:
        """Calculate price volatility score (0-100)."""
        if len(price_history) < 3:
            return 0
            
        prices = [p.price for p in price_history]
        if not prices:
            return 0
            
        mean_price = statistics.mean(prices)
        std_dev = statistics.stdev(prices) if len(prices) > 1 else 0
        
        # Calculate coefficient of variation
        cv = (std_dev / mean_price) * 100 if mean_price > 0 else 0
        
        # Normalize to 0-100 scale
        return min(100, cv * 10)
    
    def _find_optimal_buying_time(self, price_history: List[PricePoint]) -> Optional[str]:
        """Find patterns in price history to suggest optimal buying times."""
        if len(price_history) < 7:
            return None
            
        # Group prices by day of week
        day_prices = defaultdict(list)
        for point in price_history:
            day_name = point.timestamp.strftime('%A')
            day_prices[day_name].append(point.price)
            
        # Find day with lowest average price
        if not day_prices:
            return None
            
        best_day = min(day_prices.items(), key=lambda x: statistics.mean(x[1]))
        return best_day[0]
    
    def _extract_weight(self, product: Dict[str, Any]) -> float:
        """Extract product weight in pounds."""
        # Implementation would extract weight from product data
        # This is a simplified version
        return product.get('weight_pounds', 1.0)
    
    def _extract_dimensions(self, product: Dict[str, Any]) -> Tuple[float, float, float]:
        """Extract product dimensions in inches."""
        # Implementation would extract dimensions from product data
        # This is a simplified version
        return product.get('dimensions_inches', (10, 8, 6))
    
    def _is_media_product(self, product: Dict[str, Any]) -> bool:
        """Check if product is a media item."""
        category = product.get('category', '').lower()
        return any(media in category for media in ['book', 'music', 'dvd', 'video'])
    
    def _is_price_volatile(self, product_id: str) -> bool:
        """Check if product has volatile pricing."""
        history = self.price_history.get(f"{product_id}_amazon", [])
        if len(history) < 5:
            return False
            
        volatility = self._calculate_volatility(history)
        return volatility > 30  # 30% volatility threshold