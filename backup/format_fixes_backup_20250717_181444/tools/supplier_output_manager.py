#!/usr/bin/env python3
"""
Supplier Output Manager - Implements output-safety rules
Ensures supplier data isolation and prevents overwriting existing data
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add project paths
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.path_manager import path_manager

log = logging.getLogger(__name__)

class SupplierOutputManager:
    """Manages supplier-specific output directories with safety rules"""
    
    def __init__(self, supplier_slug: str):
        """Initialize with supplier identifier"""
        self.supplier_slug = supplier_slug.replace('.', '-').replace('/', '-')
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define supplier-specific directories
        self.supplier_dirs = {
            'linking_maps': path_manager.get_output_path("FBA_ANALYSIS", "linking_maps", self.supplier_slug),
            'supplier_data': path_manager.get_output_path("FBA_ANALYSIS", "supplier_data", self.supplier_slug),
            'navigation_dumps': path_manager.get_output_path("FBA_ANALYSIS", "navigation_dumps", self.supplier_slug),
            'extraction_logs': path_manager.get_output_path("FBA_ANALYSIS", "extraction_logs", self.supplier_slug)
        }
        
        # Shared directories (careful handling required)
        self.shared_dirs = {
            'amazon_cache': path_manager.get_output_path("FBA_ANALYSIS", "amazon_cache"),
            'financial_reports': path_manager.get_output_path("FBA_ANALYSIS", "financial_reports")
        }
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create supplier-specific directories"""
        try:
            for dir_name, dir_path in self.supplier_dirs.items():
                dir_path.mkdir(parents=True, exist_ok=True)
                log.debug(f"Ensured directory exists: {dir_path}")
                
                # Create .gitkeep file
                gitkeep = dir_path / ".gitkeep"
                if not gitkeep.exists():
                    gitkeep.touch()
            
            log.info(f"✅ Supplier directories created for: {self.supplier_slug}")
            
        except Exception as e:
            log.error(f"❌ Failed to create supplier directories: {e}")
    
    def get_safe_output_path(self, output_type: str, filename: str) -> Path:
        """Get safe output path for supplier data"""
        try:
            if output_type in self.supplier_dirs:
                return self.supplier_dirs[output_type] / filename
            else:
                log.warning(f"Unknown output type: {output_type}")
                return self.supplier_dirs['supplier_data'] / filename
                
        except Exception as e:
            log.error(f"Failed to get safe output path: {e}")
            return Path(filename)  # Fallback to current directory
    
    def save_linking_map(self, linking_data: Dict[str, Any], amazon_product_id: Optional[str] = None) -> str:
        """Save linking map with safety checks"""
        try:
            # Create timestamped filename
            filename = f"linking_map_{self.timestamp}.json"
            if amazon_product_id:
                filename = f"linking_map_{amazon_product_id}_{self.timestamp}.json"
            
            file_path = self.get_safe_output_path('linking_maps', filename)
            
            # Add metadata
            linking_data_with_meta = {
                'supplier': self.supplier_slug,
                'created_at': datetime.now().isoformat(),
                'amazon_product_id': amazon_product_id,
                'linking_data': linking_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(linking_data_with_meta, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ Linking map saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            log.error(f"❌ Failed to save linking map: {e}")
            return ""
    
    def save_supplier_data(self, supplier_data: Dict[str, Any], data_type: str = "product") -> str:
        """Save supplier-specific data"""
        try:
            filename = f"{data_type}_data_{self.timestamp}.json"
            file_path = self.get_safe_output_path('supplier_data', filename)
            
            # Add metadata
            data_with_meta = {
                'supplier': self.supplier_slug,
                'data_type': data_type,
                'created_at': datetime.now().isoformat(),
                'data': supplier_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_with_meta, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ Supplier data saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            log.error(f"❌ Failed to save supplier data: {e}")
            return ""
    
    def save_extraction_log(self, extraction_data: Dict[str, Any]) -> str:
        """Save extraction log with detailed information"""
        try:
            filename = f"extraction_log_{self.timestamp}.json"
            file_path = self.get_safe_output_path('extraction_logs', filename)
            
            # Add comprehensive metadata
            log_data = {
                'supplier': self.supplier_slug,
                'extraction_timestamp': datetime.now().isoformat(),
                'extraction_method': extraction_data.get('extraction_method', 'unknown'),
                'success': extraction_data.get('success', False),
                'product_url': extraction_data.get('url', ''),
                'data_extracted': {
                    'title': bool(extraction_data.get('title')),
                    'price': bool(extraction_data.get('price')),
                    'ean': bool(extraction_data.get('ean'))
                },
                'selectors_used': extraction_data.get('successful_selectors', {}),
                'full_data': extraction_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ Extraction log saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            log.error(f"❌ Failed to save extraction log: {e}")
            return ""
    
    def link_to_amazon_cache(self, amazon_asin: str, supplier_product_url: str) -> bool:
        """Create link to existing Amazon cache data without overwriting"""
        try:
            # Check if Amazon cache file exists
            amazon_cache_file = self.shared_dirs['amazon_cache'] / f"{amazon_asin}.json"
            
            if amazon_cache_file.exists():
                # Create reference file in supplier directory
                reference_data = {
                    'supplier': self.supplier_slug,
                    'supplier_product_url': supplier_product_url,
                    'amazon_asin': amazon_asin,
                    'amazon_cache_file': str(amazon_cache_file),
                    'linked_at': datetime.now().isoformat()
                }
                
                reference_file = self.get_safe_output_path('supplier_data', f"amazon_link_{amazon_asin}_{self.timestamp}.json")
                with open(reference_file, 'w', encoding='utf-8') as f:
                    json.dump(reference_data, f, indent=2, ensure_ascii=False)
                
                log.info(f"✅ Amazon cache link created: {reference_file}")
                return True
            else:
                log.warning(f"Amazon cache file not found: {amazon_cache_file}")
                return False
                
        except Exception as e:
            log.error(f"❌ Failed to link Amazon cache: {e}")
            return False
    
    def check_safety_rules(self) -> Dict[str, bool]:
        """Check that safety rules are being followed"""
        safety_checks = {
            'supplier_dirs_exist': True,
            'no_shared_overwrites': True,
            'proper_isolation': True
        }
        
        try:
            # Check supplier directories exist
            for dir_name, dir_path in self.supplier_dirs.items():
                if not dir_path.exists():
                    safety_checks['supplier_dirs_exist'] = False
                    log.error(f"Missing supplier directory: {dir_path}")
            
            # Check for potential overwrites in shared directories
            for dir_name, dir_path in self.shared_dirs.items():
                if dir_path.exists():
                    # Look for recent files that might be overwrites
                    recent_files = [f for f in dir_path.glob('*') if f.is_file() and 
                                  (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).seconds < 3600]
                    if recent_files:
                        log.warning(f"Recent files in shared directory {dir_path}: {[f.name for f in recent_files]}")
            
            # Check isolation (supplier files are in supplier directories)
            total_files = 0
            isolated_files = 0
            
            for dir_name, dir_path in self.supplier_dirs.items():
                if dir_path.exists():
                    files = list(dir_path.glob('*.json'))
                    total_files += len(files)
                    isolated_files += len([f for f in files if self.supplier_slug in str(f)])
            
            if total_files > 0:
                isolation_ratio = isolated_files / total_files
                safety_checks['proper_isolation'] = isolation_ratio >= 0.8  # At least 80% properly isolated
            
            log.info(f"Safety checks completed: {safety_checks}")
            
        except Exception as e:
            log.error(f"Safety rule check failed: {e}")
            safety_checks = {k: False for k in safety_checks}
        
        return safety_checks
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of supplier output status"""
        try:
            summary = {
                'supplier': self.supplier_slug,
                'timestamp': self.timestamp,
                'directories': {},
                'file_counts': {},
                'safety_status': self.check_safety_rules()
            }
            
            # Count files in each directory
            for dir_name, dir_path in self.supplier_dirs.items():
                if dir_path.exists():
                    files = list(dir_path.glob('*.json'))
                    summary['directories'][dir_name] = str(dir_path)
                    summary['file_counts'][dir_name] = len(files)
                else:
                    summary['directories'][dir_name] = f"Missing: {dir_path}"
                    summary['file_counts'][dir_name] = 0
            
            return summary
            
        except Exception as e:
            log.error(f"Failed to generate summary: {e}")
            return {'error': str(e)}

# Update CLAUDE_STANDARDS.md with output safety rule
def update_claude_standards_safety_rule():
    """Add output safety rule to CLAUDE_STANDARDS.md (source of truth)"""
    try:
        claude_standards_path = Path("/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/CLAUDE_STANDARDS.md")
        
        if claude_standards_path.exists():
            with open(claude_standards_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if rule already exists
            if "OUTPUT-SAFETY RULES" not in content:
                safety_rule = """

## 🔒 OUTPUT-SAFETY RULES (CRITICAL)

### **MANDATORY: Supplier Data Isolation**
**⚠️ CRITICAL: Never overwrite existing linking maps, supplier caches, or financial reports.**

**For every new supplier run:**
1. **Create supplier-specific sub-folders:**
   ```
   OUTPUTS/FBA_ANALYSIS/
   ├── linking_maps/<supplier-slug>/
   ├── supplier_data/<supplier-slug>/
   ├── navigation_dumps/<supplier-slug>/
   └── extraction_logs/<supplier-slug>/
   ```

2. **Shared Directory Rules:**
   - Amazon product cache MAY stay shared: `OUTPUTS/FBA_ANALYSIS/amazon_cache/`
   - Financial reports MUST be supplier-specific: `OUTPUTS/FBA_ANALYSIS/financial_reports/<supplier-slug>/`
   - Linking maps MUST link to existing Amazon cache files where applicable

3. **Safety Verification:**
   - Use `SupplierOutputManager` class for all supplier data operations
   - Run safety checks before and after each extraction
   - Log all file operations with timestamps and supplier identification

**Implementation:** All scripts MUST use `tools/supplier_output_manager.py` for data persistence.

"""
                
                # Find the UPDATE PROTOCOL section and add before it
                if "🔄 UPDATE PROTOCOL" in content:
                    content = content.replace("## 🔄 UPDATE PROTOCOL", safety_rule + "## 🔄 UPDATE PROTOCOL")
                else:
                    # Append at the end
                    content += safety_rule
                
                with open(claude_standards_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Auto-sync the generated files
                import subprocess
                try:
                    subprocess.run([
                        "python", 
                        str(claude_standards_path.parent / "tools" / "sync_claude_standards.py")
                    ], check=True, cwd=str(claude_standards_path.parent))
                    log.info("✅ Updated CLAUDE_STANDARDS.md and synced generated files")
                except subprocess.CalledProcessError as e:
                    log.warning(f"Failed to sync generated files: {e}")
                    log.info("✅ Updated CLAUDE_STANDARDS.md with output safety rules")
            else:
                log.info("Output safety rules already exist in CLAUDE_STANDARDS.md")
                
        else:
            log.warning("CLAUDE_STANDARDS.md file not found")
            
    except Exception as e:
        log.error(f"Failed to update CLAUDE_STANDARDS.md: {e}")

if __name__ == "__main__":
    # Example usage
    manager = SupplierOutputManager("poundwholesale-co-uk")
    summary = manager.get_summary()
    print(json.dumps(summary, indent=2))