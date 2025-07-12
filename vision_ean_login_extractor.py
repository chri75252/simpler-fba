#!/usr/bin/env python3
"""
Vision + Playwright EAN Login & Extraction System
Combines Vision-assisted login with product data extraction for PoundWholesale
Demonstrates successful wholesale price access and complete data extraction
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
from utils import path_manager
from tools.vision_login_handler import VisionLoginHandler

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("Playwright not available. Install with: pip install playwright && playwright install")

# OpenAI for Vision API
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class PoundWholesaleExtractor:
    """Complete extraction system with Vision login and product data extraction"""
    
    def __init__(self, openai_client: OpenAI, cdp_port: int = 9222):
        """Initialize the extraction system"""
        self.openai_client = openai_client
        self.cdp_port = cdp_port
        self.login_handler = VisionLoginHandler(openai_client, cdp_port)
        
        # Test products from config
        self.test_products = [
            {
                "url": "https://www.poundwholesale.co.uk/sealapack-turkey-roasting-bags-2-pack",
                "expected_sku": "SAP009",
                "expected_stock": "in_stock",
                "purpose": "Login and price extraction testing"
            },
            {
                "url": "https://www.poundwholesale.co.uk/elpine-oil-filled-radiator-heater-1500w", 
                "expected_sku": "31005c",
                "expected_stock": "in_stock",
                "purpose": "Selector validation"
            },
            {
                "url": "https://www.poundwholesale.co.uk/kids-black-beanie-hat",
                "expected_stock": "unknown",
                "purpose": "Additional testing"
            }
        ]
        
        # Setup logging
        self._setup_debug_logging()
    
    def _setup_debug_logging(self):
        """Setup debug logging"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = path_manager.get_log_path("debug", f"vision_ean_extractor_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Vision EAN extractor debug logging initialized - writing to {debug_log_path}")
            
        except Exception as e:
            log.warning(f"Failed to setup debug logging: {e}")
    
    async def extract_product_data(self, product_url: str, page: Page) -> Dict[str, Any]:
        """Extract comprehensive product data from a product page"""
        try:
            log.info(f"🔍 Extracting data from: {product_url}")
            
            # Navigate to product page
            await page.goto(product_url, wait_until='domcontentloaded')
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            product_data = {
                "url": product_url,
                "title": None,
                "price": None,
                "sku": None,
                "ean": None,
                "stock_status": None,
                "extraction_timestamp": datetime.now().isoformat(),
                "extraction_successful": False
            }
            
            # Extract title
            title_selectors = [
                "h1.page-title",
                "h1.product-title",
                ".page-title-wrapper h1",
                "h1"
            ]
            
            for selector in title_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        title = await element.text_content()
                        if title and title.strip():
                            product_data["title"] = title.strip()
                            log.info(f"✅ Title: {title.strip()}")
                            break
                except Exception:
                    continue
            
            # Extract price
            price_selectors = [
                ".price-box .price",
                ".product-info-price .price",
                "span.price",
                ".price-container .price",
                ".regular-price",
                ".price-final_price",
                ".price-including-tax",
                ".price-excluding-tax",
                "[data-price-amount]",
                ".product-price .price"
            ]
            
            for selector in price_selectors:
                try:
                    elements = await page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            price_text = await element.text_content()
                            if price_text and '£' in price_text and len(price_text.strip()) > 1:
                                product_data["price"] = price_text.strip()
                                log.info(f"💰 Price: {price_text.strip()}")
                                break
                    if product_data["price"]:
                        break
                except Exception:
                    continue
            
            # If no price found, check for login requirements
            if not product_data["price"]:
                login_required_selectors = [
                    'text=Login to view prices',
                    'text=login to view prices',
                    'text=Sign in to see prices'
                ]
                
                for selector in login_required_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            product_data["price"] = "LOGIN_REQUIRED"
                            log.warning(f"⚠️ Login required for price access")
                            break
                    except Exception:
                        continue
            
            # Extract SKU/EAN
            sku_ean_selectors = [
                ".product-attribute-ean",
                ".product-info-sku",
                ".sku",
                ".barcode",
                ".product-details .ean"
            ]
            
            for selector in sku_ean_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        sku_text = await element.text_content()
                        if sku_text and sku_text.strip():
                            # Clean up SKU text
                            sku_clean = sku_text.replace("SKU:", "").replace("EAN:", "").strip()
                            
                            # Determine if EAN or SKU based on length and format
                            if len(sku_clean) >= 12 and sku_clean.isdigit():
                                product_data["ean"] = sku_clean
                                log.info(f"🏷️ EAN: {sku_clean}")
                            else:
                                product_data["sku"] = sku_clean
                                log.info(f"🏷️ SKU: {sku_clean}")
                            break
                except Exception:
                    continue
            
            # Check stock status
            stock_status_selectors = [
                ".stock.available",
                ".stock.unavailable",
                ".product-info-stock-sku .stock",
                ".availability",
                ".in-stock",
                ".out-of-stock",
                ".stock-status"
            ]
            
            out_of_stock_indicators = [
                "text=Out of Stock",
                "text=OUT OF STOCK",
                "text=Not Available",
                "text=Unavailable",
                "text=Sold Out",
                "text=No Stock",
                ".out-of-stock",
                ".unavailable",
                ".stock.unavailable"
            ]
            
            # Check for out of stock first
            for indicator in out_of_stock_indicators:
                try:
                    element = page.locator(indicator).first
                    if await element.is_visible():
                        product_data["stock_status"] = "out_of_stock"
                        log.info("📦 Stock: OUT OF STOCK")
                        break
                except Exception:
                    continue
            
            # If not out of stock, check for in stock
            if not product_data["stock_status"]:
                for selector in stock_status_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            stock_text = await element.text_content()
                            if stock_text and "available" in stock_text.lower():
                                product_data["stock_status"] = "in_stock"
                                log.info("📦 Stock: IN STOCK")
                                break
                    except Exception:
                        continue
            
            # Default to unknown if no clear stock status
            if not product_data["stock_status"]:
                product_data["stock_status"] = "unknown"
                log.info("📦 Stock: UNKNOWN")
            
            # Mark as successful if we got core data
            if product_data["title"] and (product_data["price"] or product_data["price"] == "LOGIN_REQUIRED"):
                product_data["extraction_successful"] = True
                log.info("✅ Product extraction successful")
            else:
                log.warning("⚠️ Product extraction incomplete")
            
            return product_data
            
        except Exception as e:
            log.error(f"❌ Product extraction failed: {e}")
            return {
                "url": product_url,
                "extraction_error": str(e),
                "extraction_timestamp": datetime.now().isoformat(),
                "extraction_successful": False
            }
    
    async def run_complete_extraction(self) -> Dict[str, Any]:
        """Run complete login and extraction workflow"""
        try:
            log.info("🚀 Starting complete Vision + Playwright extraction workflow...")
            
            # Perform login
            log.info("🔐 Step 1: Performing login...")
            login_result = await self.login_handler.perform_login()
            
            if not login_result.success:
                log.error(f"❌ Login failed: {login_result.error_message}")
                return {
                    "workflow_success": False,
                    "login_result": login_result.__dict__,
                    "error": "Login failed"
                }
            
            log.info(f"✅ Login successful via {login_result.method_used}")
            
            # Extract products
            log.info("📦 Step 2: Extracting product data...")
            page = self.login_handler.page
            
            extracted_products = []
            for i, product_config in enumerate(self.test_products, 1):
                log.info(f"🔍 Extracting product {i}/{len(self.test_products)}: {product_config['purpose']}")
                
                product_data = await self.extract_product_data(product_config["url"], page)
                product_data["test_config"] = product_config
                extracted_products.append(product_data)
                
                # Small delay between products
                await asyncio.sleep(1)
            
            # Generate results summary
            successful_extractions = [p for p in extracted_products if p.get("extraction_successful")]
            products_with_prices = [p for p in extracted_products if p.get("price") and p["price"] != "LOGIN_REQUIRED"]
            
            workflow_result = {
                "workflow_success": True,
                "login_result": login_result.__dict__,
                "extraction_summary": {
                    "total_products": len(extracted_products),
                    "successful_extractions": len(successful_extractions),
                    "products_with_prices": len(products_with_prices),
                    "price_access_verified": len(products_with_prices) > 0
                },
                "extracted_products": extracted_products,
                "timestamp": datetime.now().isoformat()
            }
            
            # Save results to linking map directory
            date_str = datetime.now().strftime('%Y%m%d')
            results_path = path_manager.get_output_path("FBA_ANALYSIS", "linking_maps", "poundwholesale-co-uk", date_str, "vision_extraction_results.json")
            
            os.makedirs(os.path.dirname(results_path), exist_ok=True)
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(workflow_result, f, indent=2, ensure_ascii=False)
            
            log.info(f"💾 Results saved to: {results_path}")
            
            return workflow_result
            
        except Exception as e:
            log.error(f"❌ Complete extraction workflow failed: {e}")
            return {
                "workflow_success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        finally:
            await self.login_handler.cleanup()

async def main():
    """Run the complete Vision + Playwright extraction system"""
    
    # Load OpenAI client
    try:
        openai_client = OpenAI()
        log.info("✅ OpenAI client initialized")
    except Exception as e:
        log.error(f"❌ Failed to initialize OpenAI client: {e}")
        return
    
    extractor = PoundWholesaleExtractor(openai_client)
    
    try:
        result = await extractor.run_complete_extraction()
        
        print(f"\n{'='*80}")
        print(f"VISION + PLAYWRIGHT EAN EXTRACTION RESULTS")
        print(f"{'='*80}")
        
        if result["workflow_success"]:
            login_info = result["login_result"]
            summary = result["extraction_summary"]
            
            print(f"\n🔐 LOGIN RESULTS:")
            print(f"   Success: {login_info['success']}")
            print(f"   Method: {login_info['method_used']}")
            print(f"   Login Detected: {login_info['login_detected']}")
            print(f"   Price Access: {login_info['price_access_verified']}")
            
            print(f"\n📦 EXTRACTION SUMMARY:")
            print(f"   Total Products: {summary['total_products']}")
            print(f"   Successful Extractions: {summary['successful_extractions']}")
            print(f"   Products with Prices: {summary['products_with_prices']}")
            print(f"   Price Access Verified: {summary['price_access_verified']}")
            
            print(f"\n🏷️ EXTRACTED PRODUCTS:")
            for i, product in enumerate(result["extracted_products"], 1):
                print(f"\n   Product {i}:")
                print(f"     URL: {product['url']}")
                print(f"     Title: {product.get('title', 'N/A')}")
                print(f"     Price: {product.get('price', 'N/A')}")
                print(f"     SKU: {product.get('sku', 'N/A')}")
                print(f"     EAN: {product.get('ean', 'N/A')}")
                print(f"     Stock: {product.get('stock_status', 'N/A')}")
                print(f"     Success: {product.get('extraction_successful', False)}")
            
            if summary['price_access_verified']:
                print(f"\n🎉 SUCCESS: Wholesale price access confirmed!")
                print(f"🎯 Vision + Playwright login system working perfectly!")
            else:
                print(f"\n⚠️ WARNING: No prices extracted - login may need verification")
                
        else:
            print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        log.error(f"❌ Main execution failed: {e}")
        print(f"❌ Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())