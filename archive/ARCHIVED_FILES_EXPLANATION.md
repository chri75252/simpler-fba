# Archived Files Explanation

This document explains the contents of the `archive/` directory, which houses files that are not part of the active Amazon FBA Agent System workflow but are preserved for historical, testing, or backup purposes.

## Categories of Archived Files:

### 1. `archive/backup_files/`
- **Purpose:** Contains direct backups of core scripts, created at various points during development. These files typically have `_backup` in their names.
- **Original Functionality:** These were snapshots of active development files. Their functionality mirrors the script they are a backup of, at the time the backup was made.
- **Functionality Lost by Archiving:** None, as these were backups, not active components.
- **Recovery:** If a core script becomes corrupted or needs to be reverted to a previous state, these backups can be consulted or restored by copying them back to the `tools/` directory (and potentially renaming).

**Contents:**
- `main_orchestrator_backup.py`: A backup of `main_orchestrator.py`.
- `amazon_playwright_extractor_backup.py`: A backup of `amazon_playwright_extractor.py`.
- `passive_extraction_workflow_latest_backup.py`: A backup of `passive_extraction_workflow_latest.py`.
- `zero_token_triage_module_backup.py`: A backup of `zero_token_triage_module.py`.
- `configurable_supplier_scraper_backup_20250523.py`: A dated backup of `configurable_supplier_scraper.py`.

### 2. `archive/old_versions/`
- **Purpose:** Stores older versions of workflow scripts or scripts that were part of previous iterations of the system. These include files with `_v1`, `_precop`, or specific date markers.
- **Original Functionality:** These represented earlier development stages or alternative approaches to the workflow.
  - `passive_extraction_workflow_latest_v1.py`: An earlier version of the main passive extraction workflow.
  - `passive_extraction_workflow_latest - precop.py`: A version of the passive extraction workflow before a significant refactor or integration (likely "pre-copy" or "pre-componentization").
  - `amazon_playwright_extractor - pre cop.py`: A version of the Amazon extractor before a significant refactor.
  - `configurable_supplier_scraper20250523_2250.py`: A specific, dated version of the supplier scraper.
- **Functionality Lost by Archiving:** None from the current active system. These are superseded versions.
- **Recovery:** These can be reviewed for historical logic or if a feature from an older version needs to be re-evaluated. Recovery would involve careful comparison and integration with current scripts if any part is deemed useful.

### 3. `archive/tests/`
- **Purpose:** Contains test scripts, demonstration scripts, or specific feature tests developed during the project.
- **Original Functionality:**
  - `test_enhanced_features.py`: Likely tested specific new features or enhancements.
  - `test_sponsored_detection_enhanced.py`: Tested enhanced logic for detecting sponsored products on Amazon.
  - `test_sponsored_detection.py`: Tested basic logic for detecting sponsored products.
  - `demo_cache_manager.py`: A demonstration script for the `CacheManager` functionality.
- **Functionality Lost by Archiving:** No core system functionality is lost. These are for testing and demonstration, not part of the production workflow.
- **Recovery:** If specific test cases need to be run or demo functionality reviewed, these scripts can be executed. They might require adjustments to import paths or dependencies if run directly after a long time.

## General Notes on Archiving:
- **No Functionality Lost:** Archiving these files does not remove any functionality from the **current, active** FBA Agent System. The system is designed to run using the scripts in the `tools/` directory and its `utils/` subdirectory.
- **Purpose of Archiving:**
  - To clean up the main `tools/` directory, making it easier to navigate and understand the active components.
  - To preserve historical versions and test utilities for reference or potential future use without cluttering the main development area.
- **Restoring Files:** If any archived file needs to be made active again, it should be:
  1. Copied back to the appropriate location (e.g., `tools/` or a new `tests/` directory at the project root if a more formal testing structure is desired).
  2. Import paths within the restored script and any scripts that might call it would need to be verified and updated.
  3. The script's relevance to the current system architecture should be carefully evaluated. 