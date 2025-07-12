# Deprecated Tests Archive

## Overview
This directory contains test files that were moved from the main test suite during pytest collection fixes on 2025-06-15.

## Reason for Archival
These tests were testing components that were moved to `tools/archive/utilities/` during Phase 2 system cleanup:
- `supplier_parser` module functionality
- `main_orchestrator` system orchestration
- Legacy integration patterns

## Archived Test Files

### test_supplier_parser.py
- **Purpose**: Tested SupplierDataParser functionality
- **Dependencies**: `tools.supplier_parser.SupplierDataParser` (now archived)
- **Status**: Replaced by current supplier scraping architecture

### test_supplier_parser_toggle.py  
- **Purpose**: Tested supplier parser toggle feature
- **Dependencies**: `main_orchestrator.FBASystemOrchestrator` (now archived)
- **Status**: Feature integrated into current workflow system

### test_orchestrator.py
- **Purpose**: Tested FBASystemOrchestrator with 5 products
- **Dependencies**: `main_orchestrator.FBASystemOrchestrator` (now archived)  
- **Status**: Replaced by current passive extraction workflow

### test_integration_phase3.py
- **Purpose**: Integration tests for Phase 3 supplier integration
- **Dependencies**: Multiple archived modules (supplier_parser, etc.)
- **Status**: Functionality integrated into current system architecture

## Current Testing Strategy
The main test suite now focuses on:
- Current active modules in `tools/` directory
- Modern pytest fixtures in `tests/conftest.py`
- Integration tests for active system components

## Recovery Instructions
If any of these tests need to be reactivated:
1. Update import paths to point to `tools/archive/utilities/`
2. Verify configuration dependencies still exist
3. Update test expectations to match current system behavior
4. Consider whether the functionality is still relevant

## Related Documentation
- Phase 2 Completion Summary: `archive/docs/PHASE_2_COMPLETION_SUMMARY.md`
- System Architecture: `docs/SYSTEM_DEEP_DIVE.md`
- Current Test Structure: `tests/conftest.py`