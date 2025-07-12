"""
File Organization Migrator - Move existing files to claude.md compliant locations

This script migrates existing files to the standardized structure defined in claude.md.
It handles logs, documentation, outputs, and other files that may be in inconsistent locations.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import logging
import json
from typing import List, Tuple, Dict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class FileOrganizationMigrator:
    """Migrate files to claude.md compliant structure"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.migration_log = []
        self.dry_run = False  # Set to True for testing
        
        # Ensure target directories exist
        self._create_standard_directories()
    
    def _create_standard_directories(self):
        """Create all standard directories as defined in claude.md"""
        directories = [
            # Logs
            "logs/application",
            "logs/api_calls", 
            "logs/tests",
            "logs/monitoring",
            "logs/security",
            "logs/debug",
            
            # Documentation
            "docs/architecture",
            "docs/user_guides", 
            "docs/development",
            "docs/reports",
            
            # Outputs
            "OUTPUTS/FBA_ANALYSIS/financial_reports",
            "OUTPUTS/FBA_ANALYSIS/amazon_cache",
            "OUTPUTS/FBA_ANALYSIS/supplier_data",
            "OUTPUTS/FBA_ANALYSIS/linking_maps",
            "OUTPUTS/CACHE/processing_states",
            "OUTPUTS/CACHE/currency",
            "OUTPUTS/CACHE/api_responses",
            "OUTPUTS/CACHE/temporary",
            "OUTPUTS/REPORTS/daily_reports",
            "OUTPUTS/REPORTS/performance_metrics",
            "OUTPUTS/REPORTS/export_data",
            "OUTPUTS/BACKUPS/automated_backups",
            "OUTPUTS/BACKUPS/manual_snapshots"
        ]
        
        for directory in directories:
            target_dir = self.project_root / directory
            if not self.dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"✅ Created directory: {directory}")
    
    def migrate_api_logs(self):
        """Migrate API logs from incorrect locations to logs/api_calls/"""
        log.info("🔄 Migrating API logs...")
        
        # Find API log files in incorrect locations
        incorrect_locations = [
            "tools/OUTPUTS/FBA_ANALYSIS/api_logs",
            "OUTPUTS/FBA_ANALYSIS/api_logs",
            "api_logs"
        ]
        
        target_dir = self.project_root / "logs" / "api_calls"
        migrated_count = 0
        
        for location in incorrect_locations:
            source_dir = self.project_root / location
            if source_dir.exists():
                log.info(f"Found API logs in: {location}")
                
                # Move all log files
                for log_file in source_dir.glob("*.jsonl"):
                    target_file = target_dir / log_file.name
                    
                    if not self.dry_run:
                        shutil.move(str(log_file), str(target_file))
                    
                    self.migration_log.append({
                        "type": "api_log",
                        "source": str(log_file),
                        "target": str(target_file),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    log.info(f"  📋 Moved: {log_file.name} → logs/api_calls/")
                    migrated_count += 1
                
                # Remove empty directory
                if not self.dry_run and source_dir.exists() and not list(source_dir.iterdir()):
                    source_dir.rmdir()
                    log.info(f"  🗑️ Removed empty directory: {location}")
        
        log.info(f"✅ API logs migration complete: {migrated_count} files moved")
    
    def migrate_processing_states(self):
        """Migrate processing state files to OUTPUTS/CACHE/processing_states/"""
        log.info("🔄 Migrating processing state files...")
        
        # Find state files in various locations
        state_patterns = [
            "*_processing_state.json",
            "passive_extraction_state_*.json"
        ]
        
        search_locations = [
            "OUTPUTS",
            "tools/OUTPUTS", 
            ".",
            "tools"
        ]
        
        target_dir = self.project_root / "OUTPUTS" / "CACHE" / "processing_states"
        migrated_count = 0
        
        for location in search_locations:
            search_dir = self.project_root / location
            if search_dir.exists():
                for pattern in state_patterns:
                    for state_file in search_dir.glob(pattern):
                        # Skip if already in target location
                        if target_dir in state_file.parents:
                            continue
                        
                        target_file = target_dir / state_file.name
                        
                        if not self.dry_run:
                            shutil.move(str(state_file), str(target_file))
                        
                        self.migration_log.append({
                            "type": "processing_state",
                            "source": str(state_file),
                            "target": str(target_file),
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        log.info(f"  📋 Moved: {state_file.name} → OUTPUTS/CACHE/processing_states/")
                        migrated_count += 1
        
        log.info(f"✅ Processing state migration complete: {migrated_count} files moved")
    
    def migrate_application_logs(self):
        """Migrate application logs to logs/application/"""
        log.info("🔄 Migrating application logs...")
        
        # Find application log files
        log_patterns = [
            "fba_extraction_*.log",
            "passive_extraction_*.log",
            "monitoring_system*.log",
            "system_run.log"
        ]
        
        search_locations = [
            ".",
            "tools",
            "archive/logs_and_sessions",
            "archive/logs"
        ]
        
        target_dir = self.project_root / "logs" / "application"
        migrated_count = 0
        
        for location in search_locations:
            search_dir = self.project_root / location
            if search_dir.exists():
                for pattern in log_patterns:
                    for log_file in search_dir.glob(pattern):
                        # Skip if already in logs directory
                        if "logs" in str(log_file.parent):
                            continue
                        
                        target_file = target_dir / log_file.name
                        
                        if not self.dry_run:
                            shutil.move(str(log_file), str(target_file))
                        
                        self.migration_log.append({
                            "type": "application_log",
                            "source": str(log_file),
                            "target": str(target_file),
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        log.info(f"  📋 Moved: {log_file.name} → logs/application/")
                        migrated_count += 1
        
        log.info(f"✅ Application logs migration complete: {migrated_count} files moved")
    
    def migrate_test_logs(self):
        """Migrate test-related logs to logs/tests/"""
        log.info("🔄 Migrating test logs...")
        
        # Find test log files
        test_patterns = [
            "pytest*.log",
            "test_*.log",
            "coverage*.log"
        ]
        
        target_dir = self.project_root / "logs" / "tests"
        migrated_count = 0
        
        # Check tests directory and root
        for search_dir in [self.project_root, self.project_root / "tests"]:
            if search_dir.exists():
                for pattern in test_patterns:
                    for log_file in search_dir.glob(pattern):
                        # Skip if already in logs directory
                        if "logs" in str(log_file.parent):
                            continue
                        
                        target_file = target_dir / log_file.name
                        
                        if not self.dry_run:
                            shutil.move(str(log_file), str(target_file))
                        
                        self.migration_log.append({
                            "type": "test_log",
                            "source": str(log_file),
                            "target": str(target_file),
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        log.info(f"  📋 Moved: {log_file.name} → logs/tests/")
                        migrated_count += 1
        
        log.info(f"✅ Test logs migration complete: {migrated_count} files moved")
    
    def migrate_documentation(self):
        """Migrate documentation files to docs/ structure"""
        log.info("🔄 Migrating documentation files...")
        
        # Documentation files that should be in docs/
        doc_mappings = [
            ("*.md", "docs/", ["claude.md", "README.md"]),  # Exclude files that should stay at root
            ("*ANALYSIS*.md", "docs/reports/", []),
            ("*COMPARISON*.md", "docs/reports/", []),
            ("*AUDIT*.md", "docs/reports/", []),
            ("*TEST*.md", "docs/development/", []),
            ("*SETUP*.md", "docs/development/", []),
        ]
        
        migrated_count = 0
        
        for pattern, target_subdir, excludes in doc_mappings:
            target_dir = self.project_root / target_subdir
            
            for doc_file in self.project_root.glob(pattern):
                # Skip excluded files and files already in docs/
                if doc_file.name in excludes or "docs" in str(doc_file.parent):
                    continue
                
                target_file = target_dir / doc_file.name
                
                if not self.dry_run:
                    shutil.move(str(doc_file), str(target_file))
                
                self.migration_log.append({
                    "type": "documentation",
                    "source": str(doc_file),
                    "target": str(target_file),
                    "timestamp": datetime.now().isoformat()
                })
                
                log.info(f"  📋 Moved: {doc_file.name} → {target_subdir}")
                migrated_count += 1
        
        log.info(f"✅ Documentation migration complete: {migrated_count} files moved")
    
    def run_full_migration(self, dry_run: bool = False):
        """Run complete file organization migration"""
        self.dry_run = dry_run
        
        if dry_run:
            log.info("🧪 DRY RUN MODE - No files will be moved")
        
        log.info("🚀 Starting file organization migration to claude.md standards...")
        
        # Run all migrations
        self.migrate_api_logs()
        self.migrate_processing_states()
        self.migrate_application_logs()
        self.migrate_test_logs()
        self.migrate_documentation()
        
        # Save migration log
        if not dry_run:
            self._save_migration_log()
        
        log.info(f"✅ Migration complete! Moved {len(self.migration_log)} files")
        
        # Show summary
        self._print_migration_summary()
    
    def _save_migration_log(self):
        """Save migration log for audit purposes"""
        log_file = self.project_root / "logs" / "system" / f"file_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.migration_log, f, indent=2, ensure_ascii=False)
        
        log.info(f"📋 Migration log saved: {log_file}")
    
    def _print_migration_summary(self):
        """Print migration summary"""
        if not self.migration_log:
            log.info("📊 No files needed migration - structure already compliant!")
            return
        
        # Group by type
        by_type = {}
        for entry in self.migration_log:
            entry_type = entry["type"]
            if entry_type not in by_type:
                by_type[entry_type] = 0
            by_type[entry_type] += 1
        
        log.info("📊 Migration Summary:")
        for file_type, count in by_type.items():
            log.info(f"  {file_type}: {count} files")
        
        log.info(f"  Total: {len(self.migration_log)} files migrated")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate files to claude.md compliant structure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved without actually moving files")
    parser.add_argument("--project-root", type=str, help="Project root directory (default: auto-detect)")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root) if args.project_root else None
    migrator = FileOrganizationMigrator(project_root)
    
    migrator.run_full_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()