"""
FBA Financial Calculator
========================
Calculates ROI, net‑profit, breakeven price and profit margin by combining
supplier data (from OUTPUTS/FBA_ANALYSIS/cache) with Amazon scrape data
(from OUTPUTS/AMAZON_SCRAPE).

* VAT rate hard‑coded to 20 % (UK seller).
* Prep cost (ex‑VAT) default 0.50 £ / unit.
* Shipping cost (ex‑VAT) default 0.00 £ / unit.
* If FBA and Referral fees are missing in Keepa product details, you can supply fallback values.
* Results are saved to the financial reports directory in OUTPUTS/FBA_ANALYSIS/financial_reports
"""

import os
import json
import pandas as pd
from datetime import datetime
import logging

# Set up logging
log = logging.getLogger(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUPPLIER_CACHE = os.path.join(BASE_DIR, "OUTPUTS", "cached_products", "Clearance King UK_products_cache.json")
AMAZON_SCRAPE_DIR = os.path.join(BASE_DIR, "OUTPUTS", "FBA_ANALYSIS", "amazon_cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "OUTPUTS", "FBA_ANALYSIS")
FINANCIAL_REPORTS_DIR = os.path.join(OUTPUT_DIR, "financial_reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FINANCIAL_REPORTS_DIR, exist_ok=True)

# Load configuration from system_config.json
def load_system_config():
    """Load system configuration including VAT and fee settings."""
    try:
        config_path = os.path.join(BASE_DIR, "config", "system_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        log.warning(f"Failed to load system config: {e}, using defaults")
        return {}

# Load configuration
_config = load_system_config()

# Parameters from config with fallbacks
VAT_RATE = _config.get("amazon", {}).get("vat_rate", 0.2)
PREP_COST = _config.get("amazon", {}).get("fba_fees", {}).get("prep_house_fixed_fee", 0.55)  # Updated default to 0.55
SHIP_COST = 0.0
SUPPLIER_PRICES_INCLUDE_VAT = _config.get("supplier", {}).get("prices_include_vat", True)

# Global variable to cache the linking map
_linking_map = None

# Define persistent linking map path with relative path
LINKING_MAP_PATH = os.path.join(BASE_DIR, "OUTPUTS", "FBA_ANALYSIS", "Linking map", "linking_map.json")

def load_linking_map():
    """Load the persistent linking map file for enhanced product matching."""
    global _linking_map
    if _linking_map is not None:
        return _linking_map
    
    # First try the persistent linking map
    if os.path.exists(LINKING_MAP_PATH):
        try:
            with open(LINKING_MAP_PATH, 'r', encoding='utf-8') as f:
                _linking_map = json.load(f)
            print(f"Loaded persistent linking map with {len(_linking_map)} entries")
            return _linking_map
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading persistent linking map: {e}")
    
    # Fallback: Look for linking map files in the output directory (legacy)
    linking_files = []
    
    if os.path.exists(OUTPUT_DIR):
        for fname in os.listdir(OUTPUT_DIR):
            if fname.startswith("linking_map_") and fname.endswith(".json"):
                linking_files.append(os.path.join(OUTPUT_DIR, fname))
    
    if not linking_files:
        print("No linking map found - using fallback lookup methods")
        _linking_map = []
        return _linking_map
    
    # Use the most recent linking map
    latest_map = max(linking_files, key=os.path.getmtime)
    try:
        with open(latest_map, 'r', encoding='utf-8') as f:
            _linking_map = json.load(f)
        print(f"Loaded legacy linking map: {latest_map} with {len(_linking_map)} entries")
        return _linking_map
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Error reading legacy linking map {latest_map}: {e}")
        _linking_map = []
        return _linking_map

def find_amazon_json_by_linking_map(ean, title, url):
    """Use linking map to find Amazon data for supplier product."""
    linking_map = load_linking_map()
    
    # Create possible identifiers for this supplier product
    possible_identifiers = []
    if ean:
        possible_identifiers.append(f"EAN_{ean}")
    if url:
        possible_identifiers.append(f"URL_{url}")
    
    # Search linking map for matching supplier product
    for link_record in linking_map:
        supplier_id = link_record.get("supplier_product_identifier", "")
        
        # Check if this record matches our supplier product
        if any(identifier == supplier_id for identifier in possible_identifiers):
            asin = link_record.get("chosen_amazon_asin")
            if asin:
                # Try to find the Amazon data file for this ASIN
                amazon_data = find_amazon_json_by_asin(asin, link_record.get("amazon_ean_on_page"))
                if amazon_data:
                    print(f"Found Amazon data via linking map: {supplier_id} -> {asin}")
                    return amazon_data
    
    return None

def find_amazon_json_by_asin(asin, ean=None):
    """Find Amazon JSON data by ASIN, with optional EAN for enhanced filename matching."""
    if not asin:
        return None
    
    # Try EAN-enhanced filename first if EAN is available
    if ean:
        ean_filename = f"amazon_{asin}_{ean}.json"
        ean_path = os.path.join(AMAZON_SCRAPE_DIR, ean_filename)
        if os.path.exists(ean_path):
            try:
                with open(ean_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error reading {ean_filename}: {e}")
    
    # Fallback to standard ASIN filename
    standard_filename = f"amazon_{asin}.json"
    standard_path = os.path.join(AMAZON_SCRAPE_DIR, standard_filename)
    if os.path.exists(standard_path):
        try:
            with open(standard_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading {standard_filename}: {e}")
    
    # Final fallback: search for any file containing the ASIN
    for fname in os.listdir(AMAZON_SCRAPE_DIR):
        if asin in fname and fname.endswith('.json'):
            try:
                with open(os.path.join(AMAZON_SCRAPE_DIR, fname), 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error reading {fname}: {e}")
                continue
    
    return None

# Helper to find Amazon data file by ASIN, EAN, or fuzzy title

def find_amazon_json(ean, asin, title, url=None):
    """
    Enhanced Amazon data lookup using linking map as primary method.
    Falls back to legacy methods if linking map fails.
    """
    # Method 1: Use linking map (primary method for Fix 2.6)
    amazon_data = find_amazon_json_by_linking_map(ean, title, url)
    if amazon_data:
        return amazon_data
    
    # Method 2: Direct ASIN lookup (if ASIN is provided)
    if asin:
        amazon_data = find_amazon_json_by_asin(asin, ean)
        if amazon_data:
            return amazon_data
    
    # Method 3: Legacy fallback methods for backwards compatibility
    # First try exact match for amazon_{ASIN}.json format
    if asin:
        exact_match_filename = f"amazon_{asin}.json"
        exact_match_path = os.path.join(AMAZON_SCRAPE_DIR, exact_match_filename)
        if os.path.exists(exact_match_path):
            try:
                with open(exact_match_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error reading {exact_match_filename}: {e}")
    
    # Fallback 1: Try any other filename containing EAN or ASIN
    for fname in os.listdir(AMAZON_SCRAPE_DIR):
        if (asin and asin in fname) or (ean and ean in fname):
            try:
                with open(os.path.join(AMAZON_SCRAPE_DIR, fname), 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error reading {fname}: {e}")
                continue
    
    # Fallback 2: Try fuzzy title search
    if title:
        title_main = title.lower().replace(' ', '').replace('-', '').replace('&', '')
        for fname in os.listdir(AMAZON_SCRAPE_DIR):
            if all(tok in fname.lower() for tok in title_main.split()[:3]):
                try:
                    with open(os.path.join(AMAZON_SCRAPE_DIR, fname), 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"Error reading {fname}: {e}")
                    continue
    
    return None

def extract_keepa_fees(product_details):
    # Accepts Keepa "Product Details" dict as loaded from Amazon scrape JSON
    # Returns referral_fee, fba_fee (both in £)
    # Looks for 'Referral fee' and 'FBA fee' in the block
    ref, fba = None, None
    if not product_details:
        return None, None
    for k, v in product_details.items():
        k_lower = k.lower()
        v_str = str(v).strip()

        if 'referral' in k_lower and 'fee' in k_lower:
            try:
                # Skip percentage fields and look for actual fee values
                if '%' in v_str:
                    continue
                # Remove currency symbols and parse
                ref = float(v_str.replace('£','').replace('$','').replace('€','').replace(',','').strip())
            except (ValueError, TypeError):
                print(f"Could not parse referral fee value: {v_str}")
                continue
                
        if ('fba' in k_lower or 'fulfillment' in k_lower or 'pick&pack' in k_lower) and 'fee' in k_lower:
            try:
                # Skip percentage fields
                if '%' in v_str:
                    continue
                # Remove currency symbols and parse
                fba = float(v_str.replace('£','').replace('$','').replace('€','').replace(',','').strip())
            except (ValueError, TypeError):
                print(f"Could not parse FBA fee value: {v_str}")
                continue
                
    return ref, fba

def extract_enhanced_metrics(amazon_data):
    """
    Extract enhanced metrics from Amazon data including:
    - Bought in past month data
    - FBA/FBM seller counts from Keepa
    """
    enhanced_metrics = {
        'bought_in_past_month': None,
        'fba_seller_count': None,
        'fbm_seller_count': None,
        'total_offer_count': None
    }

    # Extract "Bought in past month" data
    if amazon_data.get('amazon_monthly_sales_badge'):
        enhanced_metrics['bought_in_past_month'] = amazon_data['amazon_monthly_sales_badge']

    # Extract seller counts from Keepa data
    keepa_data = amazon_data.get('keepa', {})
    if keepa_data:
        product_details = keepa_data.get('product_details_tab_data', {})
        if product_details:
            # Extract total offer count
            if 'Total Offer Count' in product_details:
                try:
                    enhanced_metrics['total_offer_count'] = int(str(product_details['Total Offer Count']).replace(',', ''))
                except (ValueError, TypeError):
                    pass

            # Look for FBA/FBM seller information
            # Check for specific seller count fields first
            for key, value in product_details.items():
                key_lower = key.lower()
                if 'fba seller count' in key_lower or 'fba count' in key_lower:
                    try:
                        enhanced_metrics['fba_seller_count'] = int(str(value).replace(',', ''))
                    except (ValueError, TypeError):
                        enhanced_metrics['fba_seller_count'] = value
                elif 'fbm seller count' in key_lower or 'fbm count' in key_lower:
                    try:
                        enhanced_metrics['fbm_seller_count'] = int(str(value).replace(',', ''))
                    except (ValueError, TypeError):
                        enhanced_metrics['fbm_seller_count'] = value

            # Fallback: Look for presence indicators if specific counts not found
            if enhanced_metrics['fba_seller_count'] is None and 'Lowest FBA Seller' in product_details:
                enhanced_metrics['fba_seller_count'] = 'Available (see Keepa data)'
            if enhanced_metrics['fbm_seller_count'] is None and 'Lowest FBM Seller' in product_details:
                enhanced_metrics['fbm_seller_count'] = 'Available (see Keepa data)'

    return enhanced_metrics

def financials(supplier, amazon, supplier_price_inc_vat):
    # Get current price from various possible locations in the Amazon data structure
    amazon_price = None
    if 'current_price' in amazon:
        amazon_price = amazon['current_price']
    elif 'price' in amazon:
        amazon_price = amazon['price']
    else:
        # Log warning and return empty dict if no price found
        print(f"WARNING: No price found in Amazon data for {amazon.get('asin_queried', 'unknown ASIN')}")
        return {}
        
    # Defaults (if Keepa block is missing)
    referral_fee = 0.15 * amazon_price
    fba_fee = 2.8
    
    # Extract fees from Keepa data structure as organized by amazon_playwright_extractor.py
    if 'keepa' in amazon and amazon['keepa']:
        keepa_data = amazon['keepa']
        if 'product_details_tab_data' in keepa_data and keepa_data['product_details_tab_data']:
            ref, fba = extract_keepa_fees(keepa_data['product_details_tab_data'])
            if ref: referral_fee = ref
            if fba: fba_fee = fba
        # Fallback to old structure if needed
        elif 'keepa_product_details' in amazon and amazon['keepa_product_details']:
            ref, fba = extract_keepa_fees(amazon['keepa_product_details'])
            if ref: referral_fee = ref
            if fba: fba_fee = fba
            
    selling_price_inc_vat = amazon_price
    
    # Handle VAT calculations based on supplier price configuration
    if SUPPLIER_PRICES_INCLUDE_VAT:
        # Supplier prices already include VAT
        supplier_price_ex_vat = supplier_price_inc_vat / (1 + VAT_RATE)
        input_vat = supplier_price_inc_vat * VAT_RATE / (1 + VAT_RATE)
    else:
        # Supplier prices are ex-VAT
        supplier_price_ex_vat = supplier_price_inc_vat  # This is actually ex-VAT
        input_vat = supplier_price_ex_vat * VAT_RATE
        supplier_price_inc_vat = supplier_price_ex_vat + input_vat  # Recalculate inc VAT
    
    amazon_price_ex_vat = selling_price_inc_vat / (1 + VAT_RATE)
    output_vat = selling_price_inc_vat * VAT_RATE / (1 + VAT_RATE)
    net_proceeds = selling_price_inc_vat - referral_fee - fba_fee - output_vat
    hmrc = output_vat - input_vat
    net_profit = net_proceeds - hmrc - PREP_COST - SHIP_COST
    
    # Fixed ROI calculation: ROI = (Net Profit / Total Cost) * 100
    # Total cost = supplier cost + all fees
    total_cost = supplier_price_ex_vat + PREP_COST + SHIP_COST
    roi = (net_profit / total_cost) * 100 if total_cost > 0 else 0
    
    breakeven = supplier_price_inc_vat + referral_fee + fba_fee + PREP_COST + SHIP_COST
    
    # Fixed Profit Margin calculation: Profit Margin = (Net Profit / Revenue) * 100
    profit_margin = (net_profit / selling_price_inc_vat) * 100 if selling_price_inc_vat > 0 else 0
    return {
        'SupplierPrice_incVAT': supplier_price_inc_vat,
        'SupplierPrice_exVAT': supplier_price_ex_vat,
        'SellingPrice_incVAT': selling_price_inc_vat,
        'ReferralFee': referral_fee,
        'FBAFee': fba_fee,
        'PrepHouseFee': PREP_COST,  # Added prep house fee as separate column
        'OutputVAT': output_vat,
        'InputVAT': input_vat,
        'NetProceeds': net_proceeds,
        'HMRC': hmrc,
        'NetProfit': net_profit,
        'ROI': roi,
        'Breakeven': breakeven,
        'ProfitMargin': profit_margin,
    }

def run_calculations(supplier_cache_path=None, output_dir=None, amazon_scrape_dir=None):
    """
    Core calculation function extracted from main() for testability.
    
    Args:
        supplier_cache_path: Path to supplier cache JSON file
        output_dir: Directory to save financial reports
        amazon_scrape_dir: Directory containing Amazon scrape data
        
    Returns:
        dict: Results containing DataFrame, statistics, and file path
    """
    # Use parameters or default paths
    cache_path = supplier_cache_path or SUPPLIER_CACHE
    out_dir = output_dir or FINANCIAL_REPORTS_DIR
    amazon_dir = amazon_scrape_dir or AMAZON_SCRAPE_DIR
    
    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    # === BEGIN ADDED DEBUG ===
    if not os.path.exists(amazon_dir):
        raise FileNotFoundError(f"CRITICAL FBA_Financial_calculator: amazon_dir does not exist: {amazon_dir}")
    if not os.path.isdir(amazon_dir):
        raise NotADirectoryError(f"CRITICAL FBA_Financial_calculator: amazon_dir is not a directory: {amazon_dir}")
    log.info(f"FBA_Financial_calculator: amazon_dir confirmed to exist and is a directory: {amazon_dir}")
    # === END ADDED DEBUG ===

    print(f"Loading supplier products from: {cache_path}")
    print(f"Using Amazon data from: {amazon_dir}")
    print(f"Output will be saved to: {out_dir}")
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            supplier_products = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise Exception(f"Error reading supplier cache: {e}")

    records = []
    
    print(f"Processing {len(supplier_products)} supplier products...")
    processed = 0
    found_matches = 0
    
    for sp in supplier_products:
        ean = sp.get('ean')
        asin = sp.get('asin')
        title = sp.get('title')
        url = sp.get('url')  # Get supplier URL for linking map lookup
        
        # Skip if no linking information
        if not any([ean, asin, title]):
            print(f"Skipping product with no EAN, ASIN, or title")
            continue
            
        supplier_price = float(sp['price']) if 'price' in sp and sp['price'] else 0
        amazon = find_amazon_json(ean, asin, title, url)  # Pass URL parameter
        processed += 1
        
        if not amazon:
            if processed % 25 == 0:
                print(f"Processed {processed}/{len(supplier_products)} - No Amazon data for: EAN={ean}, ASIN={asin}")
            continue
            
        found_matches += 1
            
        # Check for current_price (primary) or fallback to price
        price = amazon.get('current_price')
        if price is None:
            price = amazon.get('price')
        
        if not price:
            print(f"No price found for: EAN={ean}, ASIN={asin}, Title={title}")
            continue
            
        # Get Amazon URL 
        amazon_url = amazon.get('url')
        if not amazon_url and 'asin_queried' in amazon:
            amazon_url = f"https://www.amazon.co.uk/dp/{amazon['asin_queried']}"
            
        # Get Amazon title for the CSV
        amazon_title = amazon.get('title', amazon.get('product_title', 'N/A'))
        
        # Create the row data with improved fields
        row = {
            'EAN': ean,
            'EAN_OnPage': amazon.get('ean_on_page'),  # Include the EAN found on the Amazon page
            'ASIN': asin if asin else amazon.get('asin_queried', amazon.get('asin_from_details')),
            'SupplierTitle': title,  # Renamed for clarity
            'AmazonTitle': amazon_title,  # Added Amazon product title
            'SupplierURL': sp.get('url'),
            'AmazonURL': amazon_url
        }

        # Add enhanced metrics
        enhanced_metrics = extract_enhanced_metrics(amazon)
        row.update(enhanced_metrics)

        financial_data = financials(sp, amazon, supplier_price)
        if financial_data:  # Only add if financial calculations were successful
            row.update(financial_data)
            records.append(row)
        
    if not records:
        raise Exception("No matching records found. Check file paths and data consistency.")
        
    df = pd.DataFrame(records)
    
    # Sort by ROI (highest first) for better analysis
    if 'ROI' in df.columns:
        df = df.sort_values(by='ROI', ascending=False)
    
    dt = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(out_dir, f'fba_financial_report_{dt}.csv')
    df.to_csv(out_path, index=False)
    
    # Calculate statistics
    stats = {
        'processed': processed,
        'found_matches': found_matches,
        'generated_calculations': len(records),
        'output_file': out_path
    }
    
    if 'ROI' in df.columns:
        stats['profitable_count'] = df[df['ROI'] > 0.3].shape[0]
        stats['marginal_count'] = df[(df['ROI'] <= 0.3) & (df['ROI'] > 0)].shape[0] 
        stats['unprofitable_count'] = df[df['ROI'] <= 0].shape[0]
        stats['top_5_by_roi'] = df.head(5)[['ASIN', 'EAN', 'SupplierTitle', 'ROI', 'NetProfit', 'SellingPrice_incVAT', 'SupplierPrice_incVAT']].to_dict('records')
    
    return {
        'dataframe': df,
        'statistics': stats,
        'records': records,
        'supplier_products_total': len(supplier_products)
    }

def main():
    """Main entry point that calls run_calculations and displays results."""
    try:
        results = run_calculations()
        
        df = results['dataframe']
        stats = results['statistics']
        
        print(f"\nProcessed {stats['processed']}/{results['supplier_products_total']} products")
        print(f"Found {stats['found_matches']} matching Amazon records")
        print(f"Generated {stats['generated_calculations']} financial calculations")
        print(f"\nFinancial report saved to: {stats['output_file']}")
        
        # Display statistics on results
        if 'ROI' in df.columns:
            print(f"\nTop 5 items by ROI:")
            print(df.head(5)[['ASIN', 'EAN', 'SupplierTitle', 'ROI', 'NetProfit', 'SellingPrice_incVAT', 'SupplierPrice_incVAT']])
            
            # Show profitability breakdown
            print(f"\nProfitability breakdown:")
            print(f"  - Good ROI (>30%): {stats.get('profitable_count', 0)} items")
            print(f"  - Marginal (0-30%): {stats.get('marginal_count', 0)} items")
            print(f"  - Unprofitable: {stats.get('unprofitable_count', 0)} items")
            
    except Exception as e:
        print(f"Error in financial calculations: {e}")
        return

if __name__ == '__main__':
    main()
