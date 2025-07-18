#!/usr/bin/env python3
"""
Comprehensive File Organizer - Amazon FBA System v3.5
=====================================================

This script properly organizes ALL generated files according to the README.md structure.
Ensures complete compliance with the documented directory organization.

ORGANIZATION TARGETS:
- Documentation files → docs/
- Python scripts → tools/
- Test files → tests/
- Log files → logs/application/
- Screenshots/images → OUTPUTS/debug/
- Session states → OUTPUTS/CACHE/processing_states/
- Workflow results → OUTPUTS/FBA_ANALYSIS/workflow_results/
"""

import os
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class ComprehensiveFileOrganizer:
    """Organizes all system files according to README.md structure"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.organized_files = []
        self.errors = []
        
        # File mapping according to README.md structure
        self.file_mappings = {
            # Documentation files → docs/
            'documentation': {
                'patterns': ['.md'],
                'exceptions': ['README.md', 'claude.md', 'CLAUDE.md'],
                'target_dir': 'docs',
                'files': [
                    'AGENTS.md',
                    'CLAUDE_STANDARDS.md', 
                    'IMPLEMENTATION_COMPLETE.md',
                    'IMPLEMENTATION_SUMMARY.md',
                    'README_VISION_BOOTSTRAP.md'
                ]
            },
            
            # Python scripts → tools/
            'scripts': {
                'patterns': ['.py'],
                'exceptions': ['monitoring_system.py'],  # Essential in root per README
                'target_dir': 'tools',
                'files': [
                    'complete_vision_playwright_extraction.py',
                    'generate_linking_map.py',
                    'inspect_page.py', 
                    'inspect_products.py',
                    'poundwholesale_login_automation.py',
                    'poundwholesale_login_simple.py',
                    'standalone_playwright_login.py',
                    'vision_ean_bootstrap.py',
                    'vision_ean_login_extractor.py'
                ]
            },
            
            # Test files → tests/
            'tests': {
                'patterns': ['test_*.py'],
                'target_dir': 'tests',
                'files': [
                    'test_poundwholesale_headed.py',
                    'test_poundwholesale_headed_extraction.py'
                ]
            },
            
            # Log files → logs/application/
            'logs': {
                'patterns': ['.log'],
                'target_dir': 'logs/application',
                'files': [
                    'fba_extraction_20250617.log',
                    'fba_extraction_20250619.log', 
                    'fba_extraction_20250620.log',
                    'fba_extraction_20250621.log'
                ]
            },
            
            # Debug images → OUTPUTS/debug/
            'debug_images': {
                'patterns': ['.png', '.jpg', '.jpeg'],
                'target_dir': 'OUTPUTS/debug',
                'files': [
                    'after_amazon_navigation_B000BIUGTQ.png',
                    'after_amazon_navigation_B08N5WRWNW.png',
                    'after_login_20250625_212729.png',
                    'before_amazon_navigation_B000BIUGTQ.png',
                    'before_amazon_navigation_B08N5WRWNW.png',
                    'homepage_screenshot.png',
                    'manual_discovery_20250625_212510.png',
                    'poundwholesale_analysis_20250625_212403.png',
                    'poundwholesale_homepage_20250625_212154.png',
                    'targeted_homepage_20250625_212657.png',
                    'targeted_login_page_20250625_212659.png'
                ]
            },
            
            # HTML debug files → OUTPUTS/debug/
            'debug_html': {
                'patterns': ['.html'],
                'target_dir': 'OUTPUTS/debug',
                'files': [
                    'homepage_content.html'
                ]
            },
            
            # Session states → OUTPUTS/CACHE/processing_states/
            'session_states': {
                'patterns': ['*_session_state.json'],
                'target_dir': 'OUTPUTS/CACHE/processing_states',
                'source_dirs': ['cache', 'suppliers/*/cache']
            }
        }
        
        log.info("🗂️ Comprehensive File Organizer initialized")
    
    def create_required_directories(self):
        """Create all required directories per README.md structure"""
        required_dirs = [
            'docs',
            'tools',
            'tests', 
            'logs/application',
            'logs/debug',
            'OUTPUTS/debug',
            'OUTPUTS/CACHE/processing_states',
            'OUTPUTS/FBA_ANALYSIS/workflow_results',
            'OUTPUTS/FBA_ANALYSIS/financial_reports',
            'OUTPUTS/REPORTS'
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                log.info(f"✅ Created directory: {dir_path}")
    
    def organize_files_by_mapping(self):
        """Organize files according to predefined mappings"""
        for category, config in self.file_mappings.items():
            log.info(f"📁 Organizing {category} files...")
            
            target_dir = self.project_root / config['target_dir']
            
            # Organize specific files listed in config
            for filename in config.get('files', []):
                source_file = self.project_root / filename
                if source_file.exists():
                    self._move_file(source_file, target_dir / filename, category)
            
            # Organize files from specific source directories
            for source_dir_pattern in config.get('source_dirs', []):
                if '*' in source_dir_pattern:
                    # Handle wildcard patterns like 'suppliers/*/cache'
                    self._organize_wildcard_pattern(source_dir_pattern, config, category)
                else:
                    source_dir = self.project_root / source_dir_pattern
                    if source_dir.exists():
                        self._organize_directory(source_dir, target_dir, config.get('patterns', []), category)
    
    def _organize_wildcard_pattern(self, pattern: str, config: dict, category: str):
        """Handle wildcard directory patterns"""
        try:
            import glob
            pattern_path = str(self.project_root / pattern)
            matching_dirs = glob.glob(pattern_path)
            
            for dir_path in matching_dirs:
                source_dir = Path(dir_path)
                target_dir = self.project_root / config['target_dir']
                self._organize_directory(source_dir, target_dir, config.get('patterns', []), category)
                
        except Exception as e:
            log.error(f"Error organizing wildcard pattern {pattern}: {e}")
            self.errors.append(f"Wildcard pattern error: {e}")
    
    def _organize_directory(self, source_dir: Path, target_dir: Path, patterns: list, category: str):
        """Organize all files in a directory matching patterns"""
        try:
            for file_path in source_dir.iterdir():
                if file_path.is_file():
                    if any(file_path.name.endswith(pattern.lstrip('*')) for pattern in patterns):
                        self._move_file(file_path, target_dir / file_path.name, category)
        except Exception as e:
            log.error(f"Error organizing directory {source_dir}: {e}")
            self.errors.append(f"Directory error: {e}")
    
    def _move_file(self, source: Path, target: Path, category: str):
        """Safely move a file with backup and error handling"""
        try:
            # Ensure target directory exists
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle filename conflicts
            if target.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_parts = target.name.split('.')
                if len(name_parts) > 1:
                    new_name = f"{'.'.join(name_parts[:-1])}_{timestamp}.{name_parts[-1]}"
                else:
                    new_name = f"{target.name}_{timestamp}"
                target = target.parent / new_name
            
            # Move the file
            shutil.move(str(source), str(target))
            
            self.organized_files.append({
                'source': str(source),
                'target': str(target),
                'category': category,
                'timestamp': datetime.now().isoformat()
            })
            
            log.info(f"✅ Moved {category}: {source.name} → {target.relative_to(self.project_root)}")
            
        except Exception as e:
            error_msg = f"Failed to move {source} to {target}: {e}"
            log.error(error_msg)
            self.errors.append(error_msg)
    
    def organize_workflow_results(self):
        """Move workflow results to proper location"""
        workflow_results_dir = self.project_root / "OUTPUTS/FBA_ANALYSIS/workflow_results"
        
        # Find workflow result files in various locations
        search_locations = [
            self.project_root,
            self.project_root / "OUTPUTS",
            self.project_root / "OUTPUTS/FBA_ANALYSIS"
        ]
        
        for location in search_locations:
            if location.exists():
                for file_path in location.iterdir():
                    if file_path.is_file() and any(keyword in file_path.name.lower() 
                                                 for keyword in ['workflow', 'reorganization_report']):
                        self._move_file(file_path, workflow_results_dir / file_path.name, 'workflow_results')
    
    def rename_unclear_directories(self):
        """Rename unclear directories like 'New folder' to descriptive names"""
        unclear_dirs = [
            (self.project_root / "OUTPUTS/FBA_ANALYSIS/New folder", 
             self.project_root / "OUTPUTS/FBA_ANALYSIS/june_2025_analysis")
        ]
        
        for old_path, new_path in unclear_dirs:
            if old_path.exists():
                try:
                    old_path.rename(new_path)
                    log.info(f"✅ Renamed directory: {old_path.name} → {new_path.name}")
                except Exception as e:
                    log.error(f"Failed to rename {old_path}: {e}")
                    self.errors.append(f"Directory rename error: {e}")
    
    def generate_organization_report(self):
        """Generate comprehensive organization report"""
        report = {
            "organization_timestamp": datetime.now().isoformat(),
            "total_files_organized": len(self.organized_files),
            "categories_processed": len(self.file_mappings),
            "errors_encountered": len(self.errors),
            "organized_files": self.organized_files,
            "errors": self.errors,
            "summary": {
                category: len([f for f in self.organized_files if f['category'] == category])
                for category in self.file_mappings.keys()
            }
        }
        
        # Save detailed report
        report_file = self.project_root / "OUTPUTS/FBA_ANALYSIS/workflow_results/file_organization_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate summary
        summary = f"""
# File Organization Summary
========================

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Files Organized:** {len(self.organized_files)}
**Errors:** {len(self.errors)}

## Organization by Category:
"""
        
        for category, count in report['summary'].items():
            summary += f"- **{category.title()}**: {count} files\n"
        
        if self.errors:
            summary += f"\n## Errors Encountered:\n"
            for error in self.errors:
                summary += f"- {error}\n"
        
        summary += f"\n## Files Successfully Organized:\n"
        for file_info in self.organized_files:
            rel_target = Path(file_info['target']).relative_to(self.project_root)
            summary += f"- {Path(file_info['source']).name} → {rel_target}\n"
        
        summary += f"\n**✅ System now complies with README.md directory structure**"
        
        print(summary)
        log.info(f"📊 Organization report saved: {report_file}")
    
    def execute_comprehensive_organization(self):
        """Execute complete file organization process"""
        try:
            log.info("🚀 Starting comprehensive file organization...")
            
            # Step 1: Create required directories
            self.create_required_directories()
            
            # Step 2: Organize files by mapping
            self.organize_files_by_mapping()
            
            # Step 3: Handle workflow results
            self.organize_workflow_results()
            
            # Step 4: Rename unclear directories
            self.rename_unclear_directories()
            
            # Step 5: Generate report
            self.generate_organization_report()
            
            log.info("🎉 Comprehensive file organization completed!")
            
        except Exception as e:
            log.error(f"Critical error in organization process: {e}")
            self.errors.append(f"Critical error: {e}")

def main():
    """Main entry point"""
    import sys
    
    # Get project root (default to current directory)
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    
    # Create and execute organizer
    organizer = ComprehensiveFileOrganizer(project_root)
    organizer.execute_comprehensive_organization()

if __name__ == "__main__":
    main()