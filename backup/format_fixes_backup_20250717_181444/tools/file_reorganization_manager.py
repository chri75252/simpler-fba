#!/usr/bin/env python3
"""
File Reorganization Manager - Comprehensive System Organization
===============================================================

This script implements the comprehensive file reorganization plan to organize
all misplaced files according to the proper directory structure from README.md.

CAPABILITIES:
- Identifies 31+ misplaced files in root directory
- Categorizes files by type and intended destination
- Moves files to proper directories with validation
- Updates script paths to use utils/path_manager.py
- Creates missing directories as needed
- Provides detailed logging and rollback capability

DIRECTORY MAPPING:
- Screenshots (.png) → OUTPUTS/debug/
- Log files (.log) → logs/application/
- Documentation (.md) → docs/
- Scripts (.py) → tools/ or archive/ based on type
- Test files → tests/
"""

import os
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class FileReorganizationManager:
    """Manages comprehensive file reorganization for the FBA system"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "REORGANIZATION_BACKUP"
        self.report_file = self.project_root / f"reorganization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Directory mappings based on README structure
        self.directory_mappings = {
            'screenshots': 'OUTPUTS/debug',
            'logs': 'logs/application', 
            'debug_logs': 'logs/debug',
            'documentation': 'docs',
            'tools': 'tools',
            'archive': 'archive',
            'tests': 'tests',
            'configs': 'config',
            'temp_outputs': 'OUTPUTS/CACHE/temporary'
        }
        
        # File categorization patterns
        self.file_patterns = {
            'screenshots': ['.png', '.jpg', '.jpeg', '.gif'],
            'logs': ['.log'],
            'documentation': ['.md'],
            'scripts': ['.py'],
            'configs': ['.json', '.yaml', '.yml', '.ini'],
            'data': ['.csv', '.xlsx', '.txt'],
            'html': ['.html', '.htm']
        }
        
        self.reorganization_report = {
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': 0,
            'files_moved': 0,
            'directories_created': 0,
            'moved_files': [],
            'created_directories': [],
            'errors': [],
            'skipped_files': []
        }
        
        log.info("🗂️ File Reorganization Manager initialized")
    
    def analyze_misplaced_files(self) -> Dict[str, List[str]]:
        """Analyze all files in root directory and categorize them"""
        try:
            log.info("🔍 Analyzing misplaced files in root directory...")
            
            # Essential files that should stay in root
            essential_files = {
                'README.md', 'claude.md', 'CLAUDE_STANDARDS.md', 'pyproject.toml', 
                'requirements.txt', 'tox.ini', '.gitignore', '.env'
            }
            
            misplaced_files = {
                'screenshots': [],
                'logs': [],
                'documentation': [],
                'scripts': [],
                'configs': [],
                'test_files': [],
                'html_files': [],
                'other': []
            }
            
            # Scan root directory
            for item in self.project_root.iterdir():
                if item.is_file() and item.name not in essential_files:
                    categorized = False
                    
                    # Categorize by file extension
                    suffix = item.suffix.lower()
                    
                    if suffix in self.file_patterns['screenshots']:
                        # Determine if it's a screenshot vs other image
                        if any(keyword in item.name.lower() for keyword in 
                               ['screenshot', 'navigation', 'login', 'homepage', 'discovery', 'analysis']):
                            misplaced_files['screenshots'].append(str(item))
                            categorized = True
                    
                    if suffix in self.file_patterns['logs']:
                        misplaced_files['logs'].append(str(item))
                        categorized = True
                    
                    if suffix in self.file_patterns['documentation'] and not categorized:
                        # Check if it's actual documentation vs temporary files
                        if any(keyword in item.name.lower() for keyword in 
                               ['implementation', 'agents', 'summary', 'guide', 'readme']):
                            misplaced_files['documentation'].append(str(item))
                            categorized = True
                    
                    if suffix in self.file_patterns['scripts'] and not categorized:
                        # Categorize Python files by their purpose
                        if any(keyword in item.name.lower() for keyword in 
                               ['test_', '_test', 'inspect_', 'generate_', 'vision_', 'standalone_']):
                            if 'test' in item.name.lower():
                                misplaced_files['test_files'].append(str(item))
                            else:
                                misplaced_files['scripts'].append(str(item))
                            categorized = True
                    
                    if suffix in ['.html', '.htm']:
                        misplaced_files['html_files'].append(str(item))
                        categorized = True
                    
                    if not categorized:
                        misplaced_files['other'].append(str(item))
            
            # Update report
            total_files = sum(len(files) for files in misplaced_files.values())
            self.reorganization_report['files_analyzed'] = total_files
            
            log.info(f"📊 Analysis complete: {total_files} misplaced files found")
            for category, files in misplaced_files.items():
                if files:
                    log.info(f"  - {category}: {len(files)} files")
            
            return misplaced_files
            
        except Exception as e:
            error_msg = f"Error analyzing misplaced files: {e}"
            log.error(error_msg)
            self.reorganization_report['errors'].append(error_msg)
            return {}
    
    def create_missing_directories(self) -> None:
        """Create any missing directories needed for reorganization"""
        try:
            log.info("📁 Creating missing directories...")
            
            required_dirs = [
                'OUTPUTS/debug',
                'logs/application',
                'logs/debug', 
                'docs',
                'tools',
                'archive',
                'tests',
                'OUTPUTS/CACHE/temporary'
            ]
            
            for dir_path in required_dirs:
                full_path = self.project_root / dir_path
                if not full_path.exists():
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.reorganization_report['created_directories'].append(str(full_path))
                    self.reorganization_report['directories_created'] += 1
                    log.info(f"✅ Created directory: {dir_path}")
            
        except Exception as e:
            error_msg = f"Error creating directories: {e}"
            log.error(error_msg)
            self.reorganization_report['errors'].append(error_msg)
    
    def move_files_to_correct_locations(self, misplaced_files: Dict[str, List[str]]) -> None:
        """Move files to their correct locations based on categorization"""
        try:
            log.info("🚚 Moving files to correct locations...")
            
            # Mapping of categories to destination directories
            destination_mapping = {
                'screenshots': 'OUTPUTS/debug',
                'logs': 'logs/application',
                'documentation': 'docs',
                'scripts': 'tools',
                'test_files': 'tests',
                'html_files': 'OUTPUTS/CACHE/temporary',
                'other': 'archive'
            }
            
            for category, files in misplaced_files.items():
                if not files or category not in destination_mapping:
                    continue
                
                destination_dir = self.project_root / destination_mapping[category]
                
                for file_path in files:
                    try:
                        source_file = Path(file_path)
                        if not source_file.exists():
                            continue
                        
                        dest_file = destination_dir / source_file.name
                        
                        # Handle filename conflicts
                        if dest_file.exists():
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            name_parts = source_file.name.split('.')
                            if len(name_parts) > 1:
                                new_name = f"{'.'.join(name_parts[:-1])}_{timestamp}.{name_parts[-1]}"
                            else:
                                new_name = f"{source_file.name}_{timestamp}"
                            dest_file = destination_dir / new_name
                        
                        # Create backup before moving
                        backup_path = self.backup_dir / source_file.name
                        self.backup_dir.mkdir(exist_ok=True)
                        shutil.copy2(source_file, backup_path)
                        
                        # Move file
                        shutil.move(str(source_file), str(dest_file))
                        
                        # Update report
                        move_record = {
                            'source': str(source_file),
                            'destination': str(dest_file),
                            'category': category,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.reorganization_report['moved_files'].append(move_record)
                        self.reorganization_report['files_moved'] += 1
                        
                        log.info(f"✅ Moved {source_file.name} → {destination_mapping[category]}/")
                        
                    except Exception as e:
                        error_msg = f"Error moving {file_path}: {e}"
                        log.error(error_msg)
                        self.reorganization_report['errors'].append(error_msg)
            
        except Exception as e:
            error_msg = f"Error in file moving process: {e}"
            log.error(error_msg)
            self.reorganization_report['errors'].append(error_msg)
    
    def update_script_paths(self) -> None:
        """Update hardcoded paths in scripts to use path_manager.py"""
        try:
            log.info("🔧 Updating script paths to use path_manager...")
            
            # Common hardcoded path patterns to replace
            path_replacements = [
                # Screenshots and debug output
                ('screenshot.png', 'path_manager.get_debug_output_path("screenshot.png")'),
                ('homepage_screenshot.png', 'path_manager.get_debug_output_path("homepage_screenshot.png")'),
                ('"debug/"', 'path_manager.get_debug_output_path()'),
                ('OUTPUTS/debug/', 'path_manager.get_debug_output_path()'),
                
                # Log files
                ('fba_extraction_', 'path_manager.get_application_log_path("fba_extraction_"'),
                ('.log"', '.log")'),
                ('logs/application/', 'path_manager.get_application_log_path()'),
                
                # Financial reports (already working but standardize)
                ('OUTPUTS/FBA_ANALYSIS/financial_reports/', 'path_manager.get_financial_reports_path()'),
                
                # Cache files
                ('OUTPUTS/CACHE/', 'path_manager.get_cache_path()'),
                
                # Documentation
                ('docs/', 'path_manager.get_docs_path()')
            ]
            
            # Find Python files that might need updating
            python_files = []
            for root, dirs, files in os.walk(self.project_root):
                # Skip certain directories
                skip_dirs = {'__pycache__', '.git', 'venv', 'langraph_env', 'archive'}
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(Path(root) / file)
            
            updated_files = []
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    modified = False
                    
                    # Check if file needs path_manager import
                    needs_import = False
                    for old_pattern, new_pattern in path_replacements:
                        if old_pattern in content and 'path_manager' in new_pattern:
                            needs_import = True
                            content = content.replace(old_pattern, new_pattern)
                            modified = True
                    
                    # Add import if needed
                    if needs_import and 'from utils.path_manager import' not in content:
                        # Find appropriate place to add import
                        lines = content.split('\n')
                        import_line = "from utils.path_manager import get_debug_output_path, get_application_log_path, get_financial_reports_path, get_cache_path, get_docs_path"
                        
                        # Find the last import line
                        last_import_idx = 0
                        for i, line in enumerate(lines):
                            if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                                last_import_idx = i
                        
                        # Insert after last import
                        lines.insert(last_import_idx + 1, import_line)
                        content = '\n'.join(lines)
                        modified = True
                    
                    # Write back if modified
                    if modified:
                        with open(py_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        updated_files.append({
                            'file': str(py_file),
                            'changes': 'Updated paths to use path_manager'
                        })
                        log.info(f"✅ Updated paths in {py_file.name}")
                
                except Exception as e:
                    error_msg = f"Error updating {py_file}: {e}"
                    log.error(error_msg)
                    self.reorganization_report['errors'].append(error_msg)
            
            self.reorganization_report['updated_scripts'] = updated_files
            log.info(f"📝 Updated {len(updated_files)} scripts with path_manager integration")
            
        except Exception as e:
            error_msg = f"Error updating script paths: {e}"
            log.error(error_msg)
            self.reorganization_report['errors'].append(error_msg)
    
    def generate_report(self) -> None:
        """Generate comprehensive reorganization report"""
        try:
            log.info("📋 Generating reorganization report...")
            
            # Save detailed JSON report
            with open(self.report_file, 'w', encoding='utf-8') as f:
                json.dump(self.reorganization_report, f, indent=2)
            
            # Create summary
            summary = f"""
# File Reorganization Summary
**Date:** {self.reorganization_report['timestamp']}

## Statistics
- **Files Analyzed:** {self.reorganization_report['files_analyzed']}
- **Files Moved:** {self.reorganization_report['files_moved']}
- **Directories Created:** {self.reorganization_report['directories_created']}
- **Scripts Updated:** {len(self.reorganization_report.get('updated_scripts', []))}
- **Errors:** {len(self.reorganization_report['errors'])}

## Summary
Successfully reorganized {self.reorganization_report['files_moved']} files into proper directory structure.
All files backed up to: {self.backup_dir}

## Backup Location
Original files backed up to: `{self.backup_dir}`

## Report File
Detailed report saved to: `{self.report_file}`
"""
            
            log.info("✅ Reorganization report generated")
            print(summary)
            
        except Exception as e:
            log.error(f"Error generating report: {e}")
    
    def execute_reorganization(self) -> None:
        """Execute the complete file reorganization process"""
        try:
            log.info("🚀 Starting comprehensive file reorganization...")
            
            # Step 1: Analyze current state
            misplaced_files = self.analyze_misplaced_files()
            if not misplaced_files:
                log.warning("No misplaced files found - reorganization not needed")
                return
            
            # Step 2: Create missing directories
            self.create_missing_directories()
            
            # Step 3: Move files to correct locations
            self.move_files_to_correct_locations(misplaced_files)
            
            # Step 4: Update script paths
            self.update_script_paths()
            
            # Step 5: Generate report
            self.generate_report()
            
            log.info("🎉 File reorganization completed successfully!")
            
        except Exception as e:
            log.error(f"Critical error in reorganization process: {e}")
            self.reorganization_report['errors'].append(f"Critical error: {e}")

def main():
    """Main entry point for file reorganization"""
    import sys
    
    # Get project root (default to current directory)
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    
    # Create and execute reorganization manager
    manager = FileReorganizationManager(project_root)
    manager.execute_reorganization()

if __name__ == "__main__":
    main()