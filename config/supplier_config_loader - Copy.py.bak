"""
Supplier Config Loader module.
Loads supplier-specific CSS selectors and configurations from external JSON files.
Provides a standardized interface for accessing supplier-specific scraping configurations.
"""

import os
import json
import logging
import argparse
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Main config directory path
CONFIG_DIR = Path(__file__).parent / "supplier_configs"


def load_supplier_selectors(domain: str) -> Dict[str, Any]:
    """
    Loads selectors for a given domain from a JSON config file.
    
    Args:
        domain: The domain name to load selectors for (e.g., "clearance-king.co.uk")
        
    Returns:
        Dict containing selectors and configuration for the domain, or empty dict if not found
    """
    # Clean the domain name (remove www. prefix if present)
    clean_domain = domain.lower().replace("www.", "")
    
    # Build paths to the domain-specific and default config files
    config_file = CONFIG_DIR / f"{clean_domain}.json"
    default_config_file = CONFIG_DIR / "default.json"
    
    loaded_config = {}
    
    try:
        # First try domain-specific config
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            log.info(f"Loaded supplier selector config for domain: {clean_domain}")
        # Fall back to default config if domain-specific not found
        elif os.path.exists(default_config_file):
            with open(default_config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            log.info(f"Loaded default selector config for domain: {clean_domain}")
        else:
            log.warning(f"No selector config file found for domain: {clean_domain} and no default.json found.")
        
        return loaded_config
        
    except Exception as e:
        log.error(f"Error loading selector config for {clean_domain}: {e}")
        
        # Optionally try default config if domain-specific config failed
        if config_file != default_config_file and os.path.exists(default_config_file):
            try:
                with open(default_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as de:
                log.error(f"Error loading default selector config: {de}")
        
        return {}


def get_domain_from_url(url: str) -> str:
    """
    Extract domain name from a URL.
    
    Args:
        url: The URL to extract domain from
        
    Returns:
        Domain name extracted from URL
    """
    try:
        if not url:
            return ""
            
        # Handle protocol-less URLs
        if not url.startswith(('http://', 'https://', 'ftp://', '//', 'file://')):
            # Check if it looks like a domain/path (contains a dot and no spaces)
            if '.' in url and ' ' not in url:
                # Prepend https:// to make it parseable
                url = 'https://' + url
            else:
                # Not a recognizable URL format
                return ""
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except Exception as e:
        log.error(f"Error extracting domain from URL {url}: {e}")
        return ""


def save_supplier_selectors(domain: str, config: Dict[str, Any]) -> bool:
    """
    Saves domain-specific selectors to a JSON config file.
    
    Args:
        domain: The domain name to save selectors for
        config: The configuration dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    clean_domain = domain.lower().replace("www.", "")
    config_file = CONFIG_DIR / f"{clean_domain}.json"
    
    try:
        # Ensure the config directory exists
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log.info(f"Saved supplier selector config for domain: {clean_domain}")
        return True
    except Exception as e:
        log.error(f"Error saving selector config for {clean_domain}: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supplier Config Loader")
    parser.add_argument("--force-write", action="store_true", 
                       help="Force overwrite JSON config file even if it exists")
    parser.add_argument("--domain", type=str, default="clearance-king.co.uk",
                       help="Domain to create/update config for")
    
    args = parser.parse_args()
    
    print("Supplier Config Loader")
    print(f"Config directory: {os.path.abspath(CONFIG_DIR)}")
    
    # Test loading a config
    test_domain = args.domain
    config = load_supplier_selectors(test_domain)
    print(f"Loaded config for {test_domain}: {'Found' if config else 'Not found'}")
    
    # Generate config file path
    clean_domain = test_domain.lower().replace("www.", "")
    out_path = CONFIG_DIR / f"{clean_domain}.json"
    
    if not config or args.force_write:
        # Create a sample config
        sample_config = {
            "product_item": "li.item.product.product-item",
            "title": "a.product-item-link",
            "price": "span.price",
            "url": "a.product-item-link",
            "image": "img.product-image-photo",
            "ean_selector_product_page": [], 
            "barcode_selector_product_page": [],
            "pagination": {
                "pattern": "?p={page_num}",
                "next_button_selector": "a.action.next"
            }
        }
        
        # Write JSON based on conditions
        if args.force_write or not os.path.exists(out_path):
            save_result = save_supplier_selectors(test_domain, sample_config)
            if save_result:
                log.info(f"Saved: {out_path}")
                assert os.path.isfile(out_path), "JSON not written!"
                print(f"Created/updated config: {'Success' if save_result else 'Failed'}")
            else:
                print("Failed to save config")
        else:
            print(f"Config already exists at {out_path}. Use --force-write to overwrite.")
    else:
        print("Config already loaded and --force-write not specified.")
