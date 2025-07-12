#!/usr/bin/env python3
"""
Headed Browser Test for Poundwholesale.co.uk
Tests selector extraction using Playwright in headed mode to bypass network restrictions.
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Add the tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    log.error("Playwright not available. Install with: pip install playwright")

async def test_poundwholesale_with_headed_browser():
    """Test poundwholesale.co.uk using headed Playwright browser."""
    
    if not PLAYWRIGHT_AVAILABLE:
        log.error("Cannot run headed browser test - Playwright not installed")
        return None
        
    log.info("🔍 Testing poundwholesale.co.uk with headed browser")
    
    # Load selector configuration
    selector_config_path = Path("config/supplier_configs/poundwholesale.co.uk.json")
    if not selector_config_path.exists():
        log.error(f"Selector config not found: {selector_config_path}")
        return None
        
    with open(selector_config_path, 'r') as f:
        selectors = json.load(f)
    
    log.info(f"Loaded selectors: {selectors}")
    
    async with async_playwright() as p:
        # Launch browser in headed mode
        browser = await p.chromium.launch(
            headless=False,  # Key: headed mode to bypass bot detection
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        try:
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Navigate to poundwholesale
            url = "https://www.poundwholesale.co.uk/"
            log.info(f"Navigating to: {url}")
            
            try:
                await page.goto(url, timeout=30000)
                log.info("✅ Successfully loaded poundwholesale.co.uk")
                
                # Wait for page to load completely
                await page.wait_for_load_state('networkidle')
                
                # Test selector extraction
                results = await extract_data_with_selectors(page, selectors)
                
                # Save results
                await save_test_results(results)
                
                return results
                
            except Exception as e:
                log.error(f"❌ Failed to load page: {e}")
                
                # Create stub HTML for testing selectors offline
                stub_html = create_stub_html()
                log.info("📄 Creating stub HTML for offline selector testing")
                
                await page.set_content(stub_html)
                
                # Test selectors against stub
                results = await extract_data_with_selectors(page, selectors, is_stub=True)
                await save_test_results(results, is_stub=True)
                
                return results
                
        finally:
            await browser.close()

async def extract_data_with_selectors(page, selectors: Dict[str, Any], is_stub: bool = False):
    """Extract data using configured selectors."""
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'url': await page.url(),
        'is_stub': is_stub,
        'extractions': {},
        'selector_tests': {}
    }
    
    field_mappings = selectors.get('field_mappings', {})
    
    # Test each field mapping
    for field_name, field_selectors in field_mappings.items():
        log.info(f"Testing field: {field_name}")
        
        if not isinstance(field_selectors, list):
            field_selectors = [field_selectors]
            
        field_results = []
        
        for selector in field_selectors:
            try:
                # Test if selector finds elements
                elements = await page.query_selector_all(selector)
                
                if elements:
                    log.info(f"✅ Selector '{selector}' found {len(elements)} elements for {field_name}")
                    
                    # Extract sample values
                    sample_values = []
                    for i, element in enumerate(elements[:3]):  # Test first 3 elements
                        try:
                            if field_name == 'price' and 'login' in selector.lower():
                                # For login-required price, just check presence
                                text = await element.inner_text()
                                sample_values.append(f"LOGIN_REQUIRED: {text}")
                            elif field_name in ['url', 'image']:
                                # For URLs and images, get href/src
                                href = await element.get_attribute('href')
                                src = await element.get_attribute('src')
                                sample_values.append(href or src or await element.inner_text())
                            else:
                                # For other fields, get text content
                                text = await element.inner_text()
                                sample_values.append(text)
                        except Exception as e:
                            sample_values.append(f"ERROR: {e}")
                    
                    field_results.append({
                        'selector': selector,
                        'found_count': len(elements),
                        'sample_values': sample_values,
                        'status': 'success'
                    })
                else:
                    log.warning(f"⚠️ Selector '{selector}' found no elements for {field_name}")
                    field_results.append({
                        'selector': selector,
                        'found_count': 0,
                        'sample_values': [],
                        'status': 'no_matches'
                    })
                    
            except Exception as e:
                log.error(f"❌ Error testing selector '{selector}': {e}")
                field_results.append({
                    'selector': selector,
                    'error': str(e),
                    'status': 'error'
                })
        
        results['selector_tests'][field_name] = field_results
        
        # Determine best extraction for this field
        successful_extractions = [r for r in field_results if r['status'] == 'success' and r['sample_values']]
        if successful_extractions:
            best_extraction = successful_extractions[0]  # Use first successful
            results['extractions'][field_name] = {
                'value': best_extraction['sample_values'][0] if best_extraction['sample_values'] else None,
                'selector_used': best_extraction['selector'],
                'confidence': 'high' if best_extraction['found_count'] > 0 else 'low'
            }
        else:
            results['extractions'][field_name] = {
                'value': None,
                'selector_used': None,
                'confidence': 'none'
            }
    
    return results

def create_stub_html() -> str:
    """Create stub HTML for offline selector testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Poundwholesale.co.uk - Stub for Testing</title>
        <meta property="product:price:amount" content="15.99">
        <meta property="product:ean" content="1234567890123">
    </head>
    <body>
        <div class="product-item">
            <h2 class="product-title">Test Product Title</h2>
            <div class="product-code">SKU123</div>
            <div class="sku">ABC-123</div>
            <img class="product-image" src="/test-image.jpg" alt="Test Product">
            <a class="product-link" href="/test-product">View Product</a>
            <a class="btn customer-login-link login-btn">Login to view price</a>
        </div>
        
        <div class="product-item">
            <h2 class="product-title">Another Test Product</h2>
            <div class="product-code">SKU456</div>
            <div class="sku">XYZ-456</div>
            <img class="product-image" src="/test-image2.jpg" alt="Test Product 2">
            <a class="product-link" href="/test-product2">View Product</a>
            <a class="btn customer-login-link login-btn">Login to view price</a>
        </div>
        
        <script>
            var productData = {
                ean: "1234567890123",
                price: "login_required"
            };
        </script>
    </body>
    </html>
    """

async def save_test_results(results: Dict[str, Any], is_stub: bool = False):
    """Save test results to log files according to claude.md standards."""
    
    # Ensure log directories exist
    log_dir = Path("logs/tests")
    debug_dir = Path("logs/debug")
    
    log_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filenames with date
    date_str = datetime.now().strftime('%Y%m%d')
    
    # Save to test log
    test_log_file = log_dir / f"pytest_run_{date_str}.log"
    with open(test_log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n=== Poundwholesale Headed Browser Test - {datetime.now().isoformat()} ===\n")
        f.write(f"Stub Mode: {is_stub}\n")
        f.write(f"URL: {results.get('url', 'N/A')}\n")
        
        # Log extraction results
        extractions = results.get('extractions', {})
        f.write("\nField Extraction Results:\n")
        for field, data in extractions.items():
            confidence = data.get('confidence', 'unknown')
            value = data.get('value', 'None')
            selector = data.get('selector_used', 'None')
            f.write(f"  {field}: {confidence} - '{value}' (selector: {selector})\n")
        
        # Summary
        successful_fields = [f for f, d in extractions.items() if d.get('value')]
        f.write(f"\nSummary: {len(successful_fields)}/{len(extractions)} fields extracted successfully\n")
        
        if 'barcode' in extractions or 'ean' in extractions:
            barcode_val = extractions.get('ean', {}).get('value') or extractions.get('barcode', {}).get('value')
            f.write(f"EAN/Barcode detected: {barcode_val}\n")
        
        if 'title' in extractions:
            title_val = extractions.get('title', {}).get('value')
            f.write(f"Title detected: {title_val}\n")
            
        if 'url' in extractions:
            url_val = extractions.get('url', {}).get('value')
            f.write(f"URL detected: {url_val}\n")
            
        price_val = extractions.get('price', {}).get('value')
        if price_val and 'login' in price_val.lower():
            f.write(f"Price: Login required (as expected)\n")
        else:
            f.write(f"Price detected: {price_val}\n")
    
    # Save detailed results to debug log
    debug_log_file = debug_dir / f"supplier_scraping_debug_{date_str}.log"
    with open(debug_log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n=== Poundwholesale Detailed Debug - {datetime.now().isoformat()} ===\n")
        f.write(json.dumps(results, indent=2, default=str))
        f.write("\n")
    
    log.info(f"✅ Test results saved to {test_log_file} and {debug_log_file}")

if __name__ == "__main__":
    asyncio.run(test_poundwholesale_with_headed_browser())