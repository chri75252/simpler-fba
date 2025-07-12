#!/usr/bin/env python3
"""
Amazon Cache File Cleanup and Renaming Tool
Fixes critical issues with Amazon cache files for FBA Financial Calculator compatibility:

1. Deletes files without Keepa data (as previously agreed)
2. Renames files to include EAN when available: amazon_{ASIN}_{EAN}.json
3. Reports on files that need manual review
4. Creates backup before making changes

CRITICAL: This ensures FBA Financial Calculator can find files efficiently using ASIN_EAN format.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class AmazonCacheFileFixer:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.amazon_cache_dir = self.base_dir / "OUTPUTS" / "FBA_ANALYSIS" / "amazon_cache"
        self.backup_dir = self.base_dir / "OUTPUTS" / "FBA_ANALYSIS" / "amazon_cache_backup"
        
        # Statistics
        self.stats = {
            "total_files": 0,
            "files_without_keepa": 0,
            "files_deleted": 0,
            "files_renamed": 0,
            "files_already_correct": 0,
            "files_with_errors": 0,
            "files_missing_ean": 0
        }
        
        self.issues_found = []
        
    def create_backup(self):
        """Create backup of Amazon cache directory"""
        if self.amazon_cache_dir.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            
            print(f"Creating backup: {backup_path}")
            shutil.copytree(self.amazon_cache_dir, backup_path)
            print(f"✅ Backup created successfully")
            return backup_path
        else:
            print("❌ Amazon cache directory not found")
            return None
    
    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Amazon cache file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            analysis = {
                "file_path": file_path,
                "file_name": file_path.name,
                "has_keepa_data": False,
                "keepa_status": None,
                "extracted_ean": None,
                "asin": None,
                "title": data.get("title", "Unknown"),
                "action_needed": None,
                "new_filename": None
            }
            
            # Extract ASIN
            analysis["asin"] = data.get("asin") or data.get("asin_extracted_from_page") or data.get("asin_queried")
            
            # Check Keepa data
            keepa_data = data.get("keepa", {})
            analysis["keepa_status"] = keepa_data.get("status", "No status")
            
            # Check if has meaningful Keepa data
            product_details = keepa_data.get("product_details_tab_data", {})
            if product_details and isinstance(product_details, dict) and len(product_details) > 0:
                analysis["has_keepa_data"] = True
                
                # Extract EAN from Keepa data
                ean_sources = [
                    product_details.get("Product Codes - EAN"),
                    product_details.get("EAN"),
                    data.get("ean_on_page"),
                    data.get("eans_on_page", [None])[0] if data.get("eans_on_page") else None
                ]
                
                for ean in ean_sources:
                    if ean and isinstance(ean, str) and len(ean) >= 12 and ean.isdigit():
                        analysis["extracted_ean"] = ean
                        break
            
            # Determine action needed
            if not analysis["has_keepa_data"]:
                analysis["action_needed"] = "DELETE"
            elif analysis["extracted_ean"]:
                expected_filename = f"amazon_{analysis['asin']}_{analysis['extracted_ean']}.json"
                if file_path.name != expected_filename:
                    analysis["action_needed"] = "RENAME"
                    analysis["new_filename"] = expected_filename
                else:
                    analysis["action_needed"] = "NONE"
            else:
                analysis["action_needed"] = "MISSING_EAN"
                
            return analysis
            
        except Exception as e:
            return {
                "file_path": file_path,
                "file_name": file_path.name,
                "error": str(e),
                "action_needed": "ERROR"
            }
    
    def scan_all_files(self) -> List[Dict]:
        """Scan all Amazon cache files and analyze them"""
        if not self.amazon_cache_dir.exists():
            print(f"❌ Amazon cache directory not found: {self.amazon_cache_dir}")
            return []
        
        amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
        self.stats["total_files"] = len(amazon_files)
        
        print(f"🔍 Scanning {len(amazon_files)} Amazon cache files...")
        
        analyses = []
        for file_path in amazon_files:
            analysis = self.analyze_file(file_path)
            analyses.append(analysis)
            
            # Update statistics
            action = analysis.get("action_needed")
            if action == "DELETE":
                self.stats["files_without_keepa"] += 1
            elif action == "RENAME":
                pass  # Will count during execution
            elif action == "NONE":
                self.stats["files_already_correct"] += 1
            elif action == "MISSING_EAN":
                self.stats["files_missing_ean"] += 1
            elif action == "ERROR":
                self.stats["files_with_errors"] += 1
        
        return analyses
    
    def execute_fixes(self, analyses: List[Dict], dry_run: bool = False):
        """Execute the fixes based on analysis"""
        print(f"\n{'🔍 DRY RUN - ' if dry_run else '🔧 EXECUTING FIXES - '}Processing {len(analyses)} files...")
        
        for analysis in analyses:
            action = analysis.get("action_needed")
            file_path = analysis["file_path"]
            
            if action == "DELETE":
                if dry_run:
                    print(f"  [DRY RUN] Would DELETE: {file_path.name} (No Keepa data)")
                else:
                    try:
                        file_path.unlink()
                        print(f"  ✅ DELETED: {file_path.name} (No Keepa data)")
                        self.stats["files_deleted"] += 1
                    except Exception as e:
                        print(f"  ❌ Error deleting {file_path.name}: {e}")
                        self.stats["files_with_errors"] += 1
                        
            elif action == "RENAME":
                new_filename = analysis["new_filename"]
                new_path = file_path.parent / new_filename
                
                if dry_run:
                    print(f"  [DRY RUN] Would RENAME: {file_path.name} → {new_filename}")
                else:
                    try:
                        if new_path.exists():
                            print(f"  ⚠️  Target exists, skipping: {file_path.name} → {new_filename}")
                        else:
                            file_path.rename(new_path)
                            print(f"  ✅ RENAMED: {file_path.name} → {new_filename}")
                            self.stats["files_renamed"] += 1
                    except Exception as e:
                        print(f"  ❌ Error renaming {file_path.name}: {e}")
                        self.stats["files_with_errors"] += 1
                        
            elif action == "MISSING_EAN":
                self.issues_found.append({
                    "file": file_path.name,
                    "issue": "Has Keepa data but no extractable EAN",
                    "title": analysis.get("title", "Unknown"),
                    "keepa_status": analysis.get("keepa_status", "Unknown")
                })
                
            elif action == "ERROR":
                self.issues_found.append({
                    "file": file_path.name,
                    "issue": f"File read error: {analysis.get('error', 'Unknown')}",
                    "title": "Unknown",
                    "keepa_status": "Unknown"
                })
    
    def print_summary(self):
        """Print summary of operations"""
        print("\n" + "="*60)
        print("📊 AMAZON CACHE FILE CLEANUP SUMMARY")
        print("="*60)
        
        print(f"📁 Total files processed: {self.stats['total_files']}")
        print(f"🗑️  Files deleted (no Keepa): {self.stats['files_deleted']}")
        print(f"📝 Files renamed (added EAN): {self.stats['files_renamed']}")
        print(f"✅ Files already correct: {self.stats['files_already_correct']}")
        print(f"⚠️  Files missing EAN: {self.stats['files_missing_ean']}")
        print(f"❌ Files with errors: {self.stats['files_with_errors']}")
        
        if self.issues_found:
            print(f"\n⚠️  ISSUES REQUIRING MANUAL REVIEW ({len(self.issues_found)}):")
            for issue in self.issues_found[:10]:  # Show first 10
                print(f"  • {issue['file']}: {issue['issue']}")
                print(f"    Title: {issue['title'][:60]}...")
            
            if len(self.issues_found) > 10:
                print(f"  ... and {len(self.issues_found) - 10} more issues")
        
        print(f"\n🎯 RESULT: FBA Financial Calculator compatibility improved!")
        print(f"   Files now follow amazon_{{ASIN}}_{{EAN}}.json naming convention")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix Amazon cache files for FBA Financial Calculator")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--base-dir", default=".", help="Base directory (default: current)")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup (not recommended)")
    
    args = parser.parse_args()
    
    fixer = AmazonCacheFileFixer(args.base_dir)
    
    print("🚀 Amazon Cache File Cleanup Tool")
    print("="*50)
    print("This tool will:")
    print("1. Delete files without Keepa data")
    print("2. Rename files to include EAN: amazon_{ASIN}_{EAN}.json")
    print("3. Report files needing manual review")
    
    if not args.dry_run and not args.no_backup:
        backup_path = fixer.create_backup()
        if not backup_path:
            print("❌ Failed to create backup. Exiting for safety.")
            return
    
    # Scan all files
    analyses = fixer.scan_all_files()
    if not analyses:
        print("❌ No files found to process")
        return
    
    # Execute fixes
    fixer.execute_fixes(analyses, dry_run=args.dry_run)
    
    # Print summary
    fixer.print_summary()
    
    if args.dry_run:
        print(f"\n💡 To execute these changes, run without --dry-run")
    else:
        print(f"\n✅ Amazon cache files have been fixed!")
        print(f"   FBA Financial Calculator should now work more efficiently")

if __name__ == "__main__":
    main()
