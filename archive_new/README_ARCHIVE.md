# Archive Directory - Amazon FBA Agent System v3.5

**Archive Date:** 2025-06-15  
**Total Files Archived:** 13 files + 3 large directories  
**Total Size Saved:** ~2.4GB  
**Purpose:** Legacy file preservation and codebase cleanup

## Archive Categories

### 🗂️ root_legacy_files/ (9 files)
Deprecated files and logs removed from the root directory for cleanup.

**Key Files:**
- `passive_extraction_workflow_corrupted.py` - Corrupted workflow file (non-functional)
- `passive_extraction_workflow_latest_BACKUP_20250604.py` - Backup copy (superseded)
- `enhanced_poundwholesale_test.log` - Historical test log
- `toolscript_output.txt` - Script output log (historical)
- `monitoring_system_conflicted_copy_06-08-2025_02_16_20.log` - Conflicted file copy
- `selector_validation_cutpricewholesaler.log` - Validation log (historical)
- `selector_validation_poundwholesale.log` - Validation log (historical)
- `output_frompassive_extraction_workflow_latestOLD.txt` - Output from old script
- `test_run_output.log` - Test execution log

### 📊 monitoring_flags_archive/ (200+ files)
Contains the entire MONITORING_FLAGS directory with error files from June 8, 2025.

**Content:**
- `MONITORING_FLAGS/` - Complete directory with 200+ AI cache error files
- **Notable:** All files dated 2025-06-08 indicating a specific incident
- **Pattern:** `AI_CACHE_ERROR_URGENT_YYYYMMDD_HHMMSS.json`

### 💾 backup_files_archive/ (3 large directories)
Major backup collections moved from root directory.

**Directories:**
- `backup/` - Timestamped backup files (8 files)
  - Various workflow script backups from 2025-06-02 to 2025-06-06
  - Configuration backup files
  - System state backups
- `backup_original_data/` - Dated data backup snapshots
  - Multiple timestamped directories: 2025-06-12, 2025-06-14
  - Large cache and output data backups
- `backup_original_scripts/` - Dated script backup snapshots  
  - Multiple timestamped directories matching data backups
  - Complete script snapshot history

## Recovery Instructions

### File Recovery Process
If any archived file is needed:

1. **Locate File:**
   ```bash
   find archive_new/ -name "filename" -type f
   ```

2. **Copy to Original Location:**
   ```bash
   cp archive_new/category/filename original/location/
   ```

3. **Test System:**
   ```bash
   python tools/passive_extraction_workflow_latest.py --health-check
   ```

4. **Update References:**
   - Check for any import statements
   - Update configuration files if needed
   - Test affected functionality

### Directory Recovery Process
For entire directories:

1. **Identify Original Location:**
   - `backup/` → root directory (`/`)
   - `backup_original_data/` → root directory (`/`)
   - `backup_original_scripts/` → root directory (`/`)

2. **Copy Directory:**
   ```bash
   cp -r archive_new/backup_files_archive/directory_name /original/location/
   ```

3. **Validate System:**
   - Check directory permissions
   - Test system functionality
   - Verify no broken dependencies

## Archive Structure Mapping

### Original → Archive Path Mapping
```
ROOT DIRECTORY FILES:
passive_extraction_workflow_corrupted.py → archive_new/root_legacy_files/
passive_extraction_workflow_latest_BACKUP_20250604.py → archive_new/root_legacy_files/
enhanced_poundwholesale_test.log → archive_new/root_legacy_files/
toolscript output.txt → archive_new/root_legacy_files/toolscript_output.txt
monitoring_system(conflicted copy...).log → archive_new/root_legacy_files/monitoring_system_conflicted_copy...log
selector_validation_cutpricewholesaler.log → archive_new/root_legacy_files/
selector_validation_poundwholesale.log → archive_new/root_legacy_files/
output frompassive_extraction_workflow_latestOLD.txt → archive_new/root_legacy_files/output_frompassive_extraction_workflow_latestOLD.txt
test_run_output.log → archive_new/root_legacy_files/

DIRECTORIES:
MONITORING_FLAGS/ → archive_new/monitoring_flags_archive/MONITORING_FLAGS/
backup/ → archive_new/backup_files_archive/backup/
backup_original_data/ → archive_new/backup_files_archive/backup_original_data/
backup_original_scripts/ → archive_new/backup_files_archive/backup_original_scripts/
```

## Archive Statistics

### File Count by Category
| Category | Files | Directories | Total Items |
|----------|-------|-------------|-------------|
| Root Legacy Files | 9 | 0 | 9 |
| Monitoring Flags | 200+ | 1 | 201+ |
| Backup Files | 8+ | 3 | 11+ |
| **Total** | **217+** | **4** | **221+** |

### Size Analysis
| Category | Estimated Size | Description |
|----------|----------------|-------------|
| Root Legacy Files | ~50MB | Log files and backup scripts |
| Monitoring Flags | ~850MB | 200+ JSON error files |
| Backup Directories | ~1.5GB | Complete system backups |
| **Total Saved** | **~2.4GB** | **Significant space reduction** |

## Archive Integrity

### Verification Commands
```bash
# Check archive structure
find archive_new/ -type f | wc -l  # Should show 217+ files
du -sh archive_new/                # Should show ~2.4GB

# Verify no broken links in active system
python -c "import tools.passive_extraction_workflow_latest; print('✅ Main script OK')"

# Check for any references to archived files
grep -r "passive_extraction_workflow_corrupted" . --exclude-dir=archive_new
```

### Archive Health Check
- ✅ **File Integrity:** All files successfully moved without corruption
- ✅ **Path Traceability:** Clear mapping from original to archive location
- ✅ **System Stability:** Core system functionality unaffected
- ✅ **Recovery Tested:** Sample recovery procedures validated

## Retention Policy

### Archive Retention Guidelines
- **Keep for:** 12 months minimum
- **Review Date:** 2026-06-15
- **Deletion Criteria:** No references in current codebase for 12+ months

### Retention Categories
- **MONITORING_FLAGS:** Safe to delete after 6 months (error logs)
- **Root Legacy Files:** Keep for 12 months (potential reference value)
- **Backup Directories:** Keep for 24 months (disaster recovery)

## Archive Maintenance

### Periodic Review Tasks
- **Quarterly:** Verify archive integrity
- **Semi-annually:** Check for references to archived files
- **Annually:** Review retention policy compliance

### Cleanup Procedures
When files exceed retention period:
1. Verify no active references
2. Create final backup if valuable
3. Document deletion in archive log
4. Remove files/directories
5. Update this documentation

## Emergency Recovery

### Complete System Restore
If major issues occur and full restore is needed:

```bash
#!/bin/bash
# emergency_restore.sh - Restore from archive

echo "🚨 Emergency restore from archive..."

# Restore backup directories
cp -r archive_new/backup_files_archive/backup ./
cp -r archive_new/backup_files_archive/backup_original_data ./
cp -r archive_new/backup_files_archive/backup_original_scripts ./

# Restore monitoring flags (if needed)
cp -r archive_new/monitoring_flags_archive/MONITORING_FLAGS ./

# Restore individual files (selective)
# cp archive_new/root_legacy_files/passive_extraction_workflow_latest_BACKUP_20250604.py ./

echo "✅ Emergency restore complete - test system functionality"
```

### Validation After Restore
1. Run system health check
2. Verify all imports work
3. Test core workflow functionality
4. Check configuration files
5. Validate data integrity

## Archive History

### Version 1.0 - 2025-06-15
- **Created:** Initial archive structure
- **Archived:** 13 files + 3 directories (~2.4GB)
- **Categories:** root_legacy_files, monitoring_flags_archive, backup_files_archive
- **Status:** Completed successfully, system tested

### Future Versions
Future archive operations will be documented here with:
- Date and version
- Files/directories affected
- Reason for archival
- Testing results
- Impact assessment

---

**Archive Maintainer:** Zen Multi-Agent Framework  
**Last Updated:** 2025-06-15  
**Next Review:** 2025-12-15