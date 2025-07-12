# CLAUDE.MD - Amazon FBA Agent System v3.5 File Organization & Development Standards

## 🚨 CLAUDE_DIRECTIVES - EXECUTE IMMEDIATELY

### **🚨 CRITICAL TESTING & VERIFICATION STANDARDS:**
- 🚨 **MANDATORY_FIX_TESTING**: WHENEVER A FIX IS IMPLEMENTED YOU MUST THOROUGHLY TEST YOUR FIXES
- 🚨 **NO_CLAIMS_WITHOUT_VERIFICATION**: Tasks cannot be marked complete without actual verification
- 🚨 **MANDATORY_FILE_VERIFICATION_PROTOCOL**: For any future response whenever referencing files (primarily output files, scripts, folders, subfolders, etc.) you MUST:
  1. ✅ **VERIFY_ACTUAL_EXISTENCE**: Check file/directory actually exists at specified path
  2. ✅ **CHECK_TIMESTAMP**: Verify file creation/modification timestamp and confirm it's recent/relevant
  3. ✅ **VERIFY_CONTENT**: Read and analyze actual file content before making any claims about what it contains
  4. ✅ **CONFIRM_CORRECT_SUPPLIER**: Ensure files reference the correct supplier (poundwholesale.co.uk, NOT clearance-king.co.uk)
  5. ✅ **PROVIDE_FULL_PATHS**: Always provide complete absolute directory paths, timestamps, and content verification
  6. ✅ **NO_ASSUMPTIONS**: Never reference files without first reading and verifying their actual content and relevance
- 🚨 **MANDATORY_BACKUP_PROTOCOL**: Before testing any script, parameter, toggle, or making major edits that might affect functionality:
  1. ✅ **CREATE_BACKUP_DIRECTORY**: Create a "backup" folder in the same directory if it doesn't exist
  2. ✅ **DATED_SUBFOLDER**: Create subfolder titled with brief reason + date (e.g., "clear_cache_toggle_test_20250701")
  3. ✅ **BACKUP_ALL_AFFECTED**: Copy ALL files/folders/scripts that might be affected by the test/change
  4. ✅ **VERIFY_BACKUP**: Confirm backup was created successfully before proceeding
- 🚨 **TASK_SUCCESS_CRITERIA**/**TASK_TESTING_CRITERIA**: For any task TESTING involving file/folder/script output through the use of full workflow or specific scripts to be considered successfully completed:
  1. ✅ **CORRECT_TIMESTAMP**: EVERY File must have accurate creation/modification timestamp based on the script or workflow involved in the test
  2. ✅ **CORRECT_FILE_PATH**: Exact absolute path must be verified and accessible and match the expected output location ( as per line 90 - 233 which the output tracker)
  3. ✅ **CORRCT_SCRIPT_EXECUTION_&_CHRONOLOGY**: Chekc if all exepcted script ran and in the correct order ( as per Workflow Diagram 12 - 138 which workflow diagram )
  3. ✅ **CONTENT_VERIFICATION**: File content must be analyzed and verified against expectations
- 🚨 **NO_FAKE_OUTPUTS**: Never claim file paths or content that haven't been actually verified
- 🚨 **ASK_FOR_SCREENSHOTS**: When fix involves verification you cannot perform (like LangSmith dashboard), explicitly ask user for screenshots

## ⚠️ MANDATORY_PROTOCOLS

### **⚠️ UPDATE PROTOCOL - CRITICAL COMPLIANCE**
<!-- LOAD_FOR: ALL_COMPLEXITY_LEVELS -->
<!-- SELECTIVE: false -->

**⚠️ MANDATORY EXECUTION - Whenever you update ANY file, script, output, or folder:**

1. **⚠️ CASCADING UPDATES** (All complexity levels)
   - ✅ REQUIRED: Check ALL related files that reference the changed item
   - ✅ REQUIRED: Update ALL scripts that use the modified paths/functions
   - ✅ REQUIRED: Update ALL documentation that mentions the changed item
   - ✅ REQUIRED: Update ALL configuration files with new references

2. **⚠️ DOCUMENTATION SYNC** (Medium+ complexity)
   - ✅ REQUIRED: Update ALL relevant documentation in `docs/`
   - ✅ REQUIRED: Update README.md with new paths/procedures
   - ✅ REQUIRED: Update architecture diagrams if applicable
   - ✅ REQUIRED: Update troubleshooting guides with new references

3. **⚠️ PATH CONSISTENCY CHECK** (All complexity levels)
   - ✅ REQUIRED: Verify path_manager.py reflects changes
   - ✅ REQUIRED: Update system_config.json if paths changed
   - ✅ REQUIRED: Test that all scripts still work with new paths


### **🔧 ZEN MCP TOOLS AVAILABLE:**
When user explicitly requests ZEN MCP tools, available tools include:
- **chat**: General collaborative thinking and brainstorming (models: o3, flash)
- **thinkdeep**: Multi-stage comprehensive investigation and reasoning (models: o3, flash)
- **planner**: Interactive sequential planning with step-by-step breakdown (models: o3, flash)
- **consensus**: Multi-model consensus workflow for decision making (models: o3, flash)
- **codereview**: Step-by-step code review with expert analysis (models: o3, flash)
- **precommit**: Pre-commit validation workflow with expert analysis (models: o3, flash)
- **debug**: Root cause analysis and systematic debugging (models: o3, flash)
- **secaudit**: Security audit workflow with OWASP compliance (models: o3, flash)
- **docgen**: Documentation generation with complexity analysis (models: o3, flash)
- **analyze**: Comprehensive code analysis and architectural assessment (models: o3, flash)
- **refactor**: Refactoring analysis with code smell detection (models: o3, flash)
- **tracer**: Code tracing workflow for execution flow analysis (models: o3, flash)
- **testgen**: Test generation with edge case coverage (models: o3, flash)

### **MANDATORY_SESSION_INITIALIZATION:**
- 🚨 **SELECTIVE_FILE_ACCESS**: REQUIRED - Only read files when explicitly requested or necessary for specific tasks
- 🚨 **PATH_MANAGEMENT_ACTIVE**: REQUIRED - Ensure path_manager.py functions are used when working with paths

### **MANDATORY_ONGOING_BEHAVIOR:**
- ⚠️ **UPDATE_PROTOCOL_COMPLIANCE**: CRITICAL - Cascading updates for ANY file changes
- ⚠️ **DOCUMENTATION_SYNC**: Update ALL related docs when changes occur
- 🚨 **API_KEY_PRESERVATION**: CRITICAL - NEVER remove or modify existing API keys in scripts or env files

### **PROJECT_DIRECTIVE_EXECUTION_CHECKLIST:**
```
✅ EXECUTION_VALIDATION (Update after completion):
- [ ] Path management functions verified active
- [ ] Update protocol compliance confirmed
- [ ] Documentation sync mechanisms active
```

### **AUTO_UPDATE_TRIGGER_CONDITIONS:**
```
🚨 DIRECTIVE: AUTO_REGENERATION
TRIGGERS:
- File modifications in tools/, config/, docs/
- CLAUDE_STANDARDS.md changes
- New supplier configurations
- Security policy updates
- Path structure changes
ACTIONS: Regenerate dependent files, update documentation, validate consistency
```

---

## 🎯 Purpose
This document establishes the standardized file organization system for the Amazon FBA Agent System v3.5. All scripts, tools, and processes MUST follow these conventions to maintain consistency, enable proper automation, and ensure maintainability.

⚠️ **AUTO-GENERATED FILE**: This file is automatically generated from CLAUDE_STANDARDS.md. DO NOT EDIT DIRECTLY.
**Generated**: 2025-06-23 01:20:00
**Source**: CLAUDE_STANDARDS.md

---




## 📁 Complete Directory Structure

### Root Level Organization (Post Phase 2 Cleanup)
```

Amazon-FBA-Agent-System-v3/
├── 🎯 CORE SYSTEM (VERIFIED OPERATIONAL)
│   ├── tools/                                    # ✅ ESSENTIAL TOOLS & ENGINES
│   │   ├── passive_extraction_workflow_latest.py # 🔧 MAIN ORCHESTRATOR (Orchestrates scraping, AI analysis, Amazon matching, financial analysis, and state management)
│   │   ├── amazon_playwright_extractor.py        # └── helper: Amazon Interaction Engine (Handles Amazon product search and data extraction)
│   │   ├── configurable_supplier_scraper.py      # └── helper: Supplier Scraping Engine (Manages supplier website navigation, category discovery, and product data scraping)
│   │   ├── supplier_guard.py                     # └── helper: Checks if supplier is ready (Determines if a supplier's automation package is complete)
│   │   ├── supplier_script_generator.py          # └── helper: Generates new supplier scripts (Creates dynamic configuration and scraping scripts for new suppliers)
│   │   ├── supplier_authentication_service.py    # └── helper: Handles supplier login (Manages authentication to supplier websites)
│   │   ├── output_verification_node.py           # └── helper: Verifies output file schemas (Performs final validation of all generated output files)
│   │   └── cache_manager.py                      # └── helper: Manages file-based caching (Caches raw data from supplier and Amazon to prevent re-scraping)
│   ├── config/                                   # ⚙️ System configuration
│   │   ├── system_config.json                    # 🔧 Main system settings
│   │   └── supplier_configs/                     # 🏪 Supplier-specific configs
│   ├── utils/                                    # ✅ UTILITY MODULES (Used by tools)
│   │   ├── path_manager.py                       # └── helper: Manages all file paths (Centralizes logic for creating and retrieving file paths)
│   │   ├── browser_manager.py                    # └── helper: Manages browser lifecycle (Handles Playwright browser setup and teardown)
│   │   └── enhanced_state_manager.py             # └── helper: Manages workflow state (Saves and loads workflow progress for resumability)
│   ├── docs/                                     # 📚 Enhanced documentation
│   │   ├── README.md                             # 📖 This comprehensive guide
│   │   └── LANGGRAPH_INTEGRATION.md              # 🧠 Advanced workflow docs
│   └── monitoring_system.py                      # 📊 System monitoring (inactive)
├── 🔄 OPERATIONAL SCRIPTS 
│   ├── start_monitoring.bat                      # 🚀 Monitoring service launcher
│   ├── health-check.sh                           # 🏥 System health check
│   ├── install-fba-tool.sh                       # 📦 Installation script
│   ├── setup-browser.sh                          # 🌐 Browser setup
│   ├── setup-dev.sh                              # 🛠️ Development setup
│   └── cleanup_incomplete_keepa.ps1              # 🧹 Cleanup utility
├── 📤 OUTPUTS (VERIFIED WORKING - ALL FILE TYPES CONFIRMED)
│   ├── cached_products/                          # 🏪 Supplier product cache
│   │   └── poundwholesale-co-uk_products_cache.json # ✅ VERIFIED (306 lines, 25+ products)
│   ├── FBA_ANALYSIS/                             # 💹 Analysis results
│   │   ├── ai_category_cache/                    # 🤖 AI category suggestions
│   │   │   └── poundwholesale-co-uk_ai_category_cache.json # ✅ VERIFIED (4 AI calls)
│   │   ├── linking_maps/                         # 🔗 Product mapping
│   │   │   └── poundwholesale-co-uk/linking_map.json # ✅ VERIFIED (EAN→ASIN mapping)
│   │   ├── amazon_cache/                         # 🌐 Amazon product data
│   │   │   └── amazon_B0DYFB7XSG_5055566938651.json # ✅ VERIFIED (Keepa data)
│   │   └── financial_reports/                    # 💰 Financial analysis
│   │       └── fba_financial_report_20250704_224021.csv # ✅ VERIFIED (ROI 228.49%)
│   └── CACHE/                                    # 🗃️ Application cache
│       └── processing_states/                    # 📊 Workflow state persistence
│           └── poundwholesale-co-uk_processing_state.json # ✅ VERIFIED (13/15 processed)
├── 📋 logs/                                      # 📊 Organized logging
│   ├── application/                              # 📱 Application logs
│   └── debug/                                    # 🐛 Debug logs
└── 🗂️ ARCHIVE SYSTEM (TOGGLE DISABLED - NOT ACTIVE) # 🗃️ Archive control verified OFF
    ├── logs_and_sessions/                        # 📋 All system logs (10 files)
    ├── documentation/                            # 📜 Historical docs (11 files)
    ├── scripts/                                  # 🛠️ Utility scripts (5 files)
    ├── tests/                                    # 🧪 Test files (4 files)
    ├── root_legacy/                              # 🗃️ Phase 1 root scripts
    ├── docs/                                     # 📚 Phase 1 docs
    └── old_versions/                             # 🔄 File versions
```

## 📋 Essential File Organization Rules

### **✅ VERIFIED OUTPUT FILES:**
| Output Type | File Path | Status | Content Verified | Generating Script |
|-------------|-----------|--------|------------------|-------------------|
| **Supplier Cache** | `OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json` | ✅ CREATED | 306 lines, 25+ products | `tools/passive_extraction_workflow_latest.py` |
| **AI Categories** | `OUTPUTS/FBA_ANALYSIS/ai_category_cache/poundwholesale-co-uk_ai_category_cache.json` | ✅ CREATED | 4 AI calls, comprehensive suggestions | `tools/passive_extraction_workflow_latest.py` |
| **Linking Maps** | `OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale-co-uk/linking_map.json` | ✅ CREATED | EAN_5055566938651→ASIN B0DYFB7XSG | `tools/passive_extraction_workflow_latest.py` |
| **Processing State** | `OUTPUTS/CACHE/processing_states/poundwholesale-co-uk_processing_state.json` | ✅ CREATED | 13/15 products processed | `tools/passive_extraction_workflow_latest.py` |
| **Amazon Cache** | `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_B0DYFB7XSG_5055566938651.json` | ✅ CREATED | Complete Keepa data, BSR 1020 | `tools/amazon_playwright_extractor.py` |
| **Financial Reports** | `OUTPUTS/FBA_ANALYSIS/financial_reports/fba_financial_report_20250704_224021.csv` | ✅ CREATED | ROI 228.49%, NetProfit £3.41 | `tools/passive_extraction_workflow_latest.py` |
| **Login Config** | `suppliers/<supplier_name>/config/login_config.json` | ✅ CREATED | Supplier login configuration | `tools/supplier_script_generator.py` |
| **Login Script** | `suppliers/<supplier_name>/scripts/<supplier_name>_login.py` | ✅ CREATED | Dynamically generated login script | `tools/supplier_script_generator.py` |
| **Scrape Script** | `suppliers/<supplier_name>/scripts/<supplier_name>_scrape.py` | ✅ CREATED | Dynamically generated scraping script | `tools/supplier_script_generator.py` |
| **Supplier Ready Marker** | `suppliers/<supplier_name>/.supplier_ready` | ✅ CREATED | Indicates successful supplier setup | `tools/supplier_guard.py` |
| **Debug Log** | `logs/debug/run_complete_fba_system_<timestamp>.log` | ✅ CREATED | Detailed system debug log | `run_complete_fba_system.py` |
| **Archived Run Data** | `archive_pre_test_<timestamp>/` | ✅ CREATED (if enabled) | Backup of previous run data | `run_complete_fba_system.py` 

### Path Management (AUTO-UPDATE TRIGGER: New utility functions, path requirements, or directory changes)
Always use path helper functions from `utils/path_manager.py`:
```python
from utils.path_manager import get_log_path, get_output_path

# Log files
log_file = get_log_path("application", f"script_name_{datetime.now().strftime('%Y%m%d')}.log")

# Output files  
output_file = get_output_path("FBA_ANALYSIS", "financial_reports", f"report_{datetime.now().strftime('%Y%m%d')}.csv")
```

### State File Management Standards (AUTO-UPDATE TRIGGER: New processing states, supplier configs, or metadata requirements)
- **Location**: `OUTPUTS/CACHE/processing_states/`
- **Format**: JSON with comprehensive metadata
- **Required Fields**:
  ```json
  {
    "schema_version": "1.0",
    "created_at": "2025-06-15T10:30:00Z",
    "last_updated": "2025-06-15T12:45:30Z",
    "supplier_name": "clearance-king",
    "last_processed_index": 150,
    "total_products": 500,
    "processing_status": "in_progress"
  }
  ```

## Configuration (AUTO-UPDATE TRIGGER: New suppliers, system settings, or browser requirements)

### System Configuration
Main system settings are detailed in `docs/README.md` and `docs/SYSTEM_DEEP_DIVE.md`. The security suite validates configuration integrity through `tools/security_checks.py`.

### Supplier Configuration  
Individual configs: `config/supplier_configs/*.json`
- Supplier-specific scraping rules
- Category mappings and pricing filters
- Authentication and navigation settings

## Security Management (AUTO-UPDATE TRIGGER: New security protocols, API changes, or safety requirements)

### 🚨 CRITICAL API KEY PRESERVATION POLICY
**🚨 MANDATORY DIRECTIVE: NEVER REMOVE OR MODIFY EXISTING API KEYS**
- ✅ **PRESERVE ALL EXISTING API KEYS** in scripts and environment files
- ✅ **USER-PROVIDED KEYS ARE SACRED** - Do not remove OpenAI or LangSmith API keys
- ✅ **ADD KEYS WHEN NEEDED** but never remove working configurations
- ✅ **MAINTAIN FUNCTIONALITY** - Keep all working API integrations intact

**Current Working API Keys (PRESERVE THESE):**
- OpenAI API Key: `sk-ZVcoRkU6brREgixWUDk7lTq_aBNRZwdh_PWwOZuJwKT3BlbkFJvOyKLWAM8OhjyHN0b8e66E1O2G7N2Ew_g3SngsDToA`
- LangSmith API Key: `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`
- LangSmith Project ID: `4e8c47f9-4c52-4d1d-85d0-00b31bb3ef5e`
- GitHub Token: `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`

**🚨 NEVER REMOVE API KEYS FROM .env FILE OR ANY SCRIPTS**

### ✅ Environment-Based Secrets Policy
The repository now follows secure `.env-based secrets` policy:
- ✅ **All API keys migrated** to environment variables
- ✅ **Security validation** enforced by `tools/security_checks.py`
- ✅ **No hardcoded secrets** in active codebase
- ✅ **Pre-commit hooks** prevent accidental key exposure

**Security Tools:**
- `tools/security_checks.py` - API key detection and validation
- `.githooks/pre-commit` - Pre-commit security verification
- `.github/workflows/claude_sync_validate.yml` - CI security checks

### Output Safety Rules (AUTO-UPDATE TRIGGER: New supplier integrations or output isolation requirements)
- **amazon_cache/**: Shared store across ALL suppliers for linking-map reuse
- **All other caches**: Must be supplier-scoped for isolation
- **supplier_data/**: Automatic subdirectory creation per supplier
- **No cross-contamination** between supplier data

## 🔄 New Automation Systems

### GitHub Checkpoint Workflow
- **Tool**: `tools/git_checkpoint.py`
- **Hook**: `.githooks/pre-commit` 
- **CI**: `.github/workflows/claude_sync_validate.yml`
- **Purpose**: Automated branch creation, commits, and GitHub integration

### Auto-Sync Engine
- **Source**: `CLAUDE_STANDARDS.md` (single source of truth)
- **Targets**: `claude.md` (filtered) + `docs/CLAUDE_STANDARDS.md` (full copy)
- **Engine**: `tools/sync_claude_standards.py`
- **Detection**: `tools/sync_opportunity_detector.py`
- **Triggers**: Content changes, code events, session checkpoints

### Security-Checks Suite
- **Tool**: `tools/security_checks.py`
- **Features**: API key scanning, .env validation, .gitignore coverage
- **Integration**: Pre-commit hooks, CI validation, config verification
- **Coverage**: Comprehensive security posture monitoring

---

## ✅ RECOMMENDED_PRACTICES
<!-- LOAD_FOR: COMPLEX -->
<!-- SELECTIVE: true -->

### **✅ Advanced FBA Analysis Workflows**
<!-- RELEVANCE_KEYWORDS: fba, analysis, financial, roi, profitability -->
<!-- ZEN_MCP_PRIORITY: thinkdeep:HIGH, analyze:HIGH, debug:MEDIUM -->

**✅ RECOMMENDED - For complex FBA analysis projects:**

1. **✅ MULTI-TIER AI FALLBACK SYSTEM**
   - 4-tier AI approach with >99% success rate
   - Temperature progression (0.1 → 0.3 → 0.5 → manual)
   - Graceful degradation for extraction failures

2. **✅ SMART CACHING STRATEGIES**
   - 240x performance improvement through state management
   - JSON-based with periodic saves, integrity validation
   - Supplier-isolated caching to prevent cross-contamination

### **✅ Vision System Integration**
<!-- RELEVANCE_KEYWORDS: vision, ean, product, extraction, bootstrap -->
<!-- ZEN_MCP_PRIORITY: thinkdeep:HIGH, analyze:MEDIUM, debug:HIGH -->

**✅ RECOMMENDED - For vision-based product extraction:**

- CDP Browser Connection for shared Chrome instances
- Login state detection and maintenance
- EAN extraction with supplier-specific patterns
- Product page validation before extraction

---

## 📋 DOCUMENTATION_REFERENCE
<!-- LOAD_ON_DEMAND: true -->
<!-- SELECTIVE: true -->

### **📋 Complete Technical Documentation**
<!-- RELEVANCE_KEYWORDS: documentation, technical, architecture, system -->
<!-- ZEN_MCP_PRIORITY: thinkdeep:MEDIUM, analyze:LOW, debug:LOW -->

**📋 REFERENCE - Load when documentation context is detected:**

**Complete technical details available in:**
- `/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/docs/README.md`
- `/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/docs/SYSTEM_DEEP_DIVE.md`
- `/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/docs/CLAUDE_STANDARDS.md`

## 🔄 Trigger Definitions

### Content-Driven Regeneration
- **CLAUDE_STANDARDS.md changes** → Regenerate claude.md (filtered) + docs/CLAUDE_STANDARDS.md (full)
- **New rules/policies** → Update all target files
- **Path updates** → Cascade through automation scripts

### Event-Driven Regeneration  
- **Script output changes** → Update documentation references
- **Test completion** → Prompt for sync opportunities
- **Git activity** → Smart prompting based on workflow state

### Cross-Documentation Sync
⚠️ **HIGH-PRIORITY TODO**: Create hooks to push critical updates into README.md and SYSTEM_DEEP_DIVE.md automatically.

## 🚨 CRITICAL IMPLEMENTATION NOTES

### **Vision + Playwright EAN Bootstrap System (June 2025)**

**Status**: 🚧 **IN PROGRESS**  
**Location**: `vision_ean_bootstrap.py`, `tools/vision_product_locator.py`

#### **Current Status**:
- ✅ **CDP Browser Connection**: Successfully connects to shared Chrome (port 9222)
- ✅ **Login Detection**: Correctly detects existing login state 
- ✅ **Homepage Product Detection**: Finds 10+ product links on homepage
- ✅ **Output Safety Rules**: Proper supplier isolation in OUTPUTS/FBA_ANALYSIS/
- ✅ **Debug Logging**: Comprehensive logging to logs/debug/
- ✅ **Vision API Integration**: GPT-4.1-mini-2025-04-14 fallback working
- ⚠️ **EAN Extraction**: Poundwholesale experiment incomplete - requires refinement

#### **HIGH-Priority Implementation Tasks** (moved to master TODO):
- Product link refinement for actual product pages vs blog content
- Login-required price extraction implementation  
- EAN pattern expansion for supplier-specific barcode detection
- Category navigation fallback system
- Product page validation before extraction

---

## 📚 Related Documentation

**Complete technical details available in:**
- `/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/docs/README.md`
- `/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/docs/SYSTEM_DEEP_DIVE.md`
- `/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/docs/CLAUDE_STANDARDS.md`

---

**Last Updated**: 2025-06-23
**Version**: 3.6
**Maintained By**: Amazon FBA Agent System Team
**Status**: ACTIVE STANDARD - All development must comply

**⚠️ NOTICE**: This file is auto-generated from CLAUDE_STANDARDS.md. For complete development guidance, see CLAUDE_STANDARDS.md