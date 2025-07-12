#!/usr/bin/env python
"""
Run complete FBA analysis
"""
import asyncio
import argparse
import logging
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.main_orchestrator import FBASystemOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fba_analysis.log'),
        logging.StreamHandler()
    ]
)

async def main():
    parser = argparse.ArgumentParser(description='Run FBA analysis')
    parser.add_argument('--suppliers', nargs='+', default=['clearance-king'],
                       help='Supplier IDs to process')
    parser.add_argument('--max-products', type=int, default=50,
                       help='Maximum products per supplier')
    parser.add_argument('--config', default='config/system_config.json',
                       help='System configuration file')
    parser.add_argument('--min-roi', type=float, default=35.0,
                       help='Minimum ROI percentage')
    parser.add_argument('--min-profit', type=float, default=3.0,
                       help='Minimum profit per unit')
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    # Load configuration
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        # Default configuration
        config = {
            'suppliers': {
                'clearance-king': {
                    'base_url': 'https://www.clearance-king.co.uk',
                    'api_config': {'enabled': False},
                    'scraping_config': {'enabled': True},
                    'category_urls': {
                        'main_categories': [
                            '/pound-lines.html',
                            '/household.html',
                            '/health-beauty.html'
                        ]
                    }
                }
            },
            'analysis': {
                'min_roi_percent': 35.0,
                'min_profit_per_unit': 3.0,
                'min_rating': 4.0,
                'min_reviews': 50,
                'max_sales_rank': 150000
            },
            'output': {
                'base_dir': 'OUTPUTS/FBA_ANALYSIS',
                'report_format': 'json',
                'save_intermediate_results': True
            }
        }
    
    # Update config with command line args
    config['analysis']['min_roi_percent'] = args.min_roi
    config['analysis']['min_profit_per_unit'] = args.min_profit
    
    print("="*80)
    print("Amazon FBA Analysis System")
    print("="*80)
    print(f"Suppliers: {', '.join(args.suppliers)}")
    print(f"Max products per supplier: {args.max_products}")
    print(f"Min ROI: {args.min_roi}%")
    print(f"Min profit: £{args.min_profit}")
    print("="*80)
    
    # Run analysis
    orchestrator = FBASystemOrchestrator(config)
    await orchestrator.run(args.suppliers, args.max_products)
    
    print("Analysis complete! Check OUTPUTS/FBA_ANALYSIS for results.")

if __name__ == '__main__':
    asyncio.run(main())