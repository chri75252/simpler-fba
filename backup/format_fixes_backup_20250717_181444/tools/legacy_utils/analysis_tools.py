"""
Analysis tools for FBA Agent System.
Provides capabilities for analyzing profitability and sales velocity.
"""

from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field


class ProfitabilityAnalyzerInput(BaseModel):
    """Input for the ProfitabilityAnalyzerTool."""
    supplier_price: float = Field(description="Wholesale price from supplier")
    amazon_price: float = Field(description="Current selling price on Amazon")
    asin: Optional[str] = Field(default=None, description="Amazon ASIN (optional)")
    product_details: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional product details like weight, dimensions, category"
    )


class ProfitabilityAnalyzerTool(BaseTool):
    """Tool for analyzing profitability of potential FBA products."""
    
    name = "profitability_analyzer"
    description = "Calculates ROI, margin, and other profitability metrics for FBA products"
    args_schema = ProfitabilityAnalyzerInput
    
    def _run(self, 
             supplier_price: float,
             amazon_price: float,
             asin: Optional[str] = None,
             product_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate profitability metrics for a potential FBA product.
        
        Args:
            supplier_price: Wholesale price from supplier
            amazon_price: Current selling price on Amazon
            asin: Amazon ASIN (optional)
            product_details: Additional product details (optional)
            
        Returns:
            Dictionary with profitability metrics
        """
        # Ensure product_details is a dictionary
        if product_details is None:
            product_details = {}
            
        # Simple FBA fee calculation (placeholder)
        # In a real implementation, this would use the FBA fee calculator API or more complex logic
        
        # Example weight-based FBA fee calculation (simplified)
        weight_kg = product_details.get("weight_kg", 0.5)
        
        if weight_kg < 0.25:
            fba_fee = 2.35
        elif weight_kg < 0.5:
            fba_fee = 2.80
        elif weight_kg < 1.0:
            fba_fee = 3.40
        else:
            fba_fee = 3.40 + (weight_kg - 1.0) * 0.40
            
        # Referral fee (usually 15% for most categories)
        referral_fee = amazon_price * 0.15
        
        # Total Amazon fees
        total_fees = fba_fee + referral_fee
        
        # Profit calculation
        profit = amazon_price - supplier_price - total_fees
        margin = (profit / amazon_price) * 100
        roi = (profit / supplier_price) * 100
        
        return {
            "supplier_price": supplier_price,
            "amazon_price": amazon_price,
            "fba_fee": round(fba_fee, 2),
            "referral_fee": round(referral_fee, 2),
            "total_fees": round(total_fees, 2),
            "profit": round(profit, 2),
            "margin_percentage": round(margin, 2),
            "roi_percentage": round(roi, 2),
            "break_even_price": round(supplier_price + total_fees, 2),
        }
    
    async def _arun(self, 
                   supplier_price: float,
                   amazon_price: float,
                   asin: Optional[str] = None,
                   product_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Async version of _run."""
        return self._run(supplier_price, amazon_price, asin, product_details)


class SalesVelocityAnalyzerInput(BaseModel):
    """Input for the SalesVelocityAnalyzerTool."""
    keepa_data: Dict[str, Any] = Field(
        description="Historical data from Keepa including sales rank history"
    )


class SalesVelocityAnalyzerTool(BaseTool):
    """Tool for analyzing sales velocity and patterns."""
    
    name = "sales_velocity_analyzer"
    description = "Analyzes historical sales patterns to estimate sales velocity"
    args_schema = SalesVelocityAnalyzerInput
    
    def _run(self, keepa_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze sales velocity based on Keepa data.
        
        Args:
            keepa_data: Historical data from Keepa
            
        Returns:
            Dictionary with sales velocity analysis
        """
        # Placeholder implementation
        # In a real implementation, this would use more sophisticated algorithms
        
        # Extract sales rank history for analysis
        sales_rank_history = keepa_data.get("sales_rank_history", [])
        
        # Calculate average sales rank
        ranks = [entry["rank"] for entry in sales_rank_history]
        avg_rank = sum(ranks) / len(ranks) if ranks else 0
        
        # Simple estimate based on average rank
        if avg_rank < 1000:
            daily_sales = 10
        elif avg_rank < 5000:
            daily_sales = 5
        elif avg_rank < 10000:
            daily_sales = 2
        else:
            daily_sales = 1
            
        monthly_sales = daily_sales * 30
        
        return {
            "estimated_daily_sales": daily_sales,
            "estimated_monthly_sales": monthly_sales,
            "average_sales_rank": round(avg_rank),
            "trend": "stable",  # Could be "increasing", "decreasing", or "stable"
            "seasonality_detected": False,
            "confidence": "medium",  # Could be "high", "medium", or "low"
        }
    
    async def _arun(self, keepa_data: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of _run."""
        return self._run(keepa_data)
