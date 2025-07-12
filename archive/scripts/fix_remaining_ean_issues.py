#!/usr/bin/env python3
"""
Enhanced EAN Extraction for Remaining Amazon Cache Files
Handles edge cases like multiple EANs, different formats, etc.
"""

import os
import json
import re
from pathlib import Path
from typing import Optional, List

class EnhancedEANExtractor:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.amazon_cache_dir = self.base_dir / "OUTPUTS" / "FBA_ANALYSIS" / "amazon_cache"
        
    def extract_ean_from_multiple_sources(self, data: dict) -> Optional[str]:
        """Enhanced EAN extraction that handles multiple sources and formats"""
        
        # Source 1: Direct EAN fields
        direct_ean_sources = [
            data.get("ean_on_page"),
            data.get("eans_on_page", [None])[0] if data.get("eans_on_page") else None
        ]
        
        for ean in direct_ean_sources:
            if self._is_valid_ean(ean):
                return ean
        
        # Source 2: Keepa product details
        keepa_data = data.get("keepa", {}).get("product_details_tab_data", {})
        if keepa_data:
            # Try standard EAN field
            ean_field = keepa_data.get("Product Codes - EAN")
            if ean_field:
                # Handle multiple EANs (comma-separated)
                if "," in str(ean_field):
                    eans = [ean.strip() for ean in str(ean_field).split(",")]
                    for ean in eans:
                        if self._is_valid_ean(ean):
                            return ean
                else:
                    if self._is_valid_ean(ean_field):
                        return str(ean_field)
            
            # Try other EAN-related fields
            ean_fields = [
                keepa_data.get("EAN"),
                keepa_data.get("Barcode"),
                keepa_data.get("Product Codes - UPC"),
                keepa_data.get("UPC")
            ]
            
            for ean in ean_fields:
                if self._is_valid_ean(ean):
                    return str(ean)
        
        # Source 3: Search in all string values for EAN patterns
        return self._find_ean_in_text(data)
    
    def _is_valid_ean(self, ean) -> bool:
        """Check if EAN is valid (12-14 digits)"""
        if not ean:
            return False
        ean_str = str(ean).strip()
        return ean_str.isdigit() and 12 <= len(ean_str) <= 14
    
    def _find_ean_in_text(self, data: dict) -> Optional[str]:
        """Search for EAN patterns in all text content"""
        # Convert entire data to string and search for EAN patterns
        text_content = json.dumps(data, default=str)
        
        # Pattern for 13-digit EAN (most common)
        ean_patterns = [
            r'\b(\d{13})\b',  # 13-digit EAN
            r'\b(\d{12})\b',  # 12-digit UPC
            r'\b(\d{14})\b'   # 14-digit EAN
        ]
        
        for pattern in ean_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if self._is_valid_ean(match):
                    # Additional validation: avoid obvious non-EANs
                    if not self._is_likely_non_ean(match):
                        return match
        
        return None
    
    def _is_likely_non_ean(self, ean: str) -> bool:
        """Check if number is likely NOT an EAN (e.g., dates, prices)"""
        # Avoid numbers that look like years, dates, or prices
        if ean.startswith(('19', '20')) and len(ean) == 13:
            return True
        if ean.startswith('0000'):
            return True
        if ean == '0' * len(ean):
            return True
        return False
    
    def process_remaining_files(self):
        """Process files that still need EAN extraction"""
        if not self.amazon_cache_dir.exists():
            print("❌ Amazon cache directory not found")
            return
        
        # Find files without EAN in filename
        files_needing_ean = []
        for file_path in self.amazon_cache_dir.glob("amazon_*.json"):
            if "_" not in file_path.stem[7:]:  # No EAN in filename after "amazon_"
                files_needing_ean.append(file_path)
        
        print(f"🔍 Found {len(files_needing_ean)} files that might need EAN extraction")
        
        fixed_count = 0
        failed_count = 0
        
        for file_path in files_needing_ean:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check if file has Keepa data
                keepa_data = data.get("keepa", {}).get("product_details_tab_data", {})
                if not keepa_data:
                    print(f"  ⚠️  Skipping {file_path.name} - no Keepa data")
                    continue
                
                # Extract EAN
                ean = self.extract_ean_from_multiple_sources(data)
                
                if ean:
                    # Extract ASIN
                    asin = data.get("asin") or data.get("asin_extracted_from_page") or data.get("asin_queried")
                    
                    if asin:
                        new_filename = f"amazon_{asin}_{ean}.json"
                        new_path = file_path.parent / new_filename
                        
                        if new_path.exists():
                            print(f"  ⚠️  Target exists: {file_path.name} → {new_filename}")
                        else:
                            file_path.rename(new_path)
                            print(f"  ✅ RENAMED: {file_path.name} → {new_filename}")
                            fixed_count += 1
                    else:
                        print(f"  ❌ No ASIN found in {file_path.name}")
                        failed_count += 1
                else:
                    print(f"  ❌ No EAN found in {file_path.name}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"  ❌ Error processing {file_path.name}: {e}")
                failed_count += 1
        
        print(f"\n📊 Enhanced EAN Extraction Results:")
        print(f"  ✅ Files fixed: {fixed_count}")
        print(f"  ❌ Files failed: {failed_count}")
        
        return fixed_count, failed_count

def main():
    extractor = EnhancedEANExtractor()
    
    print("🔧 Enhanced EAN Extraction Tool")
    print("=" * 50)
    print("This tool handles edge cases like:")
    print("- Multiple EANs in comma-separated lists")
    print("- EANs in different Keepa fields")
    print("- EAN patterns in text content")
    
    fixed, failed = extractor.process_remaining_files()
    
    if fixed > 0:
        print(f"\n🎉 Successfully fixed {fixed} additional files!")
        print("   FBA Financial Calculator compatibility further improved!")
    
    if failed > 0:
        print(f"\n⚠️  {failed} files still need manual review")
        print("   These may have non-standard EAN formats or missing EANs")

if __name__ == "__main__":
    main()
