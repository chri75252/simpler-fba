#!/usr/bin/env python3
"""
Test script to verify the "Price not found" → Authentication Fallback mechanism
This script specifically tests whether "Price not found" messages trigger authentication fallback
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def test_price_authentication_trigger():
    """Test the price-based authentication trigger mechanism"""
    log.info("🧪 TESTING: Price Authentication Trigger Mechanism")
    
    # Test case 1: Check if 'Price not found' pattern is properly detected
    test_price_responses = [
        'Price not found',
        'Login required to view price', 
        'Not found',
        '£12.99',  # Valid price
        None,  # No price
        '',  # Empty price
    ]
    
    products_without_price_count = 0
    price_missing_threshold = 3
    
    log.info(f"Testing with threshold: {price_missing_threshold}")
    
    for i, price_response in enumerate(test_price_responses):
        log.info(f"\n--- Testing price response {i+1}: '{price_response}' ---")
        
        # Logic from passive_extraction_workflow_latest.py
        price_missing = False
        
        if not price_response or price_response == '':
            price_missing = True
            log.info("❌ No price value detected")
        elif 'not found' in str(price_response).lower():
            price_missing = True
            log.info("❌ 'Not found' pattern detected in price")
        elif 'login required' in str(price_response).lower():
            price_missing = True
            log.info("❌ 'Login required' pattern detected in price")
        else:
            log.info("✅ Valid price detected")
        
        if price_missing:
            products_without_price_count += 1
            log.info(f"🔍 PRICE MISSING: Product without price ({products_without_price_count}/{price_missing_threshold})")
            
            # Check if threshold reached
            if products_without_price_count >= price_missing_threshold:
                log.warning(f"🔐 AUTH TRIGGER: {products_without_price_count} products without price (threshold: {price_missing_threshold})")
                log.info("🔐 WOULD TRIGGER: Authentication fallback at this point")
                break
        else:
            if products_without_price_count > 0:
                log.info(f"✅ PRICE FOUND: Resetting price missing counter (was {products_without_price_count})")
                products_without_price_count = 0
    
    log.info(f"\n🧪 TEST RESULTS:")
    log.info(f"   Final products_without_price_count: {products_without_price_count}")
    log.info(f"   Authentication trigger activated: {'YES' if products_without_price_count >= price_missing_threshold else 'NO'}")
    
    # Test case 2: Check recent log files for actual "Price not found" patterns
    log.info(f"\n🔍 CHECKING RECENT LOG FILES for 'Price not found' patterns...")
    
    log_dir = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/logs/debug")
    recent_logs = []
    
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            recent_logs.append((log_file.stat().st_mtime, log_file))
    
    # Sort by modification time, newest first
    recent_logs.sort(reverse=True)
    
    price_not_found_count = 0
    for _, log_file in recent_logs[:3]:  # Check last 3 log files
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Count "Price not found" patterns
            patterns = ['Price not found', 'No price found', 'price.*not.*found']
            
            for pattern in patterns:
                if pattern.lower() in content.lower():
                    count = content.lower().count(pattern.lower())
                    price_not_found_count += count
                    log.info(f"   📋 Found {count} instances of '{pattern}' in {log_file.name}")
            
        except Exception as e:
            log.warning(f"   ⚠️ Could not read {log_file.name}: {e}")
    
    log.info(f"   📊 Total 'Price not found' messages in recent logs: {price_not_found_count}")
    
    # Test case 3: Verify authentication fallback configuration
    log.info(f"\n🔧 CHECKING AUTHENTICATION FALLBACK CONFIGURATION...")
    
    # Check if config files contain proper authentication settings
    config_path = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/config/system_config.json")
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            auth_config = config.get('authentication_fallback', {})
            log.info(f"   🔐 Authentication fallback config found: {bool(auth_config)}")
            log.info(f"   🔐 Price missing threshold: {auth_config.get('price_missing_threshold', 'Not set')}")
            log.info(f"   🔐 Time-based trigger: {auth_config.get('time_based_hours', 'Not set')} hours")
            log.info(f"   🔐 Product count trigger: {auth_config.get('product_count_trigger', 'Not set')} products")
            
        except Exception as e:
            log.warning(f"   ⚠️ Could not read system config: {e}")
    else:
        log.warning("   ❌ System config file not found")
    
    log.info("\n✅ Price Authentication Trigger Test Completed")

if __name__ == "__main__":
    test_price_authentication_trigger()