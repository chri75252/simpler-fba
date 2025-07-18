# MASTER PLAN FOR MULTI-AGENT TESTING

## GLOBAL CONTEXT
- **Project root**: C:\Users\chris\Desktop\Amazon-FBA-Agent-System-v32
- **Workflow & outputs**: docs\README.md
- **Toggle definitions**: config\system-config-toggle-v2.md
- **Golden reference log**: logs\debug\run_custom_poundwholesale_20250712_092246.log
- **Crash snippet**: (see "REFERENCE ERROR" section at bottom)

## WHY MULTI-WORKTREE?
Allows parallel agent runs (prep, exec, debug) that share the same .git object store but keep code & logs isolated. Quick rollback and no massive folder copies.

### INITIAL WORKTREES (run once):
```bash
git worktree add ../Amazon-FBA-Agent-System-v32-prep  -b prep-run
git worktree add ../Amazon-FBA-Agent-System-v32-test  -b test-run
git worktree add ../Amazon-FBA-Agent-System-v32-debug -b debug-run
```

Each agent below operates ONLY inside its own worktree.

---

## STRICT RULES (NO EXCEPTIONS)
1. Delete only files listed in docs\README.md (state & cache cleanup section).
2. Never delete OUTPUTS\FBA_ANALYSIS\amazon_cache or any folders.
3. No artificial timeouts; wait for natural finish or crash.
4. After every run, catalogue **every** new/modified file:
   ```
   full-path | timestamp | size | one-line summary
   ```
5. The toggle values shown in this file are **examples**.  
   First run must honour the values already present in system-config-toggle-v2.md; later runs may tweak them to verify behaviour.
6. Persist browser session (debug port 9222) across the whole workflow.
7. Monitor & document the **state-reset-after-3-categories** issue.
8. Save all agent logs inside their own worktree's logs/ sub-folder.
9. Upon any crash, /zen:debug, commit fix to that worktree branch, then /zen:tracer map call-flow changes, and re-run from PHASE 1.

---

## CRITICAL TOGGLES (must be validated each run)
```json
processing_limits: {
  max_products_per_category: 5,
  min_price_gbp: 0.1,
  max_price_gbp: 20.0,
  price_midpoint_gbp: 20.0,
  max_products_per_run: 12,
  min_products_per_category: 1
}

system: {
  max_products: 999999,
  max_products_per_cycle: 10,
  linking_map_batch_size: 10,
  financial_report_batch_size: 30,
  supplier_extraction_batch_size: 3
}

supplier_cache_control: {
  enabled: true,
  update_frequency_products: 10
}

hybrid_processing: {
  chunked: {
    enabled: true,
    chunk_size_categories: 3
  }
}

batch_synchronization: {
  enabled: false
}
```

---

## MULTI-AGENT PIPELINE

### AGENT FLOW DIAGRAM
```
```


### AGENT 1:
**Tools**: /zen-mcp-tools

**Tasks**:

**Gate**:

---

### AGENT N+1 :
**Tools**: 

**Tasks**:

---


## SUCCESS CRITERIA
- No "workflow errors" (AttributeError, output_dir, event-loop, etc.)
- All expected output files present & valid (see README list)

When all criteria met → write **SUCCESS** line in testing_plan.md, append summary to root SUCCESS_LOG.md, and notify user.

---

## REFERENCE ERROR (full snippet – keep verbatim)
```
Remover Spray 250ml - £1.32 (EAN: 5055319531696)
2025-07-13 18:57:35,828 - configurable_supplier_scraper - INFO - Successfully extracted 5 products from https://www.poundwholesale.co.uk/wholesale-cleaning/cleaning-wipes-sprays/multi-purpose-cleaners
2025-07-13 18:57:35,829 - PassiveExtractionWorkflow - ERROR - Unexpected error occurred during workflow execution: 'PassiveExtractionWorkflow' object has no attribute 'max_price'
Traceback (most recent call last):
  File ".../passive_extraction_workflow_latest.py", line 1033, in run
    supplier_products = await self._extract_supplier_products(
  File ".../passive_extraction_workflow_latest.py", line 2526, in _extract_supplier_products
    if price <= self.max_price:
AttributeError: 'PassiveExtractionWorkflow' object has no attribute 'max_price'
2025-07-13 18:57:35,836 - __main__ - INFO - 🌐 Keeping browser persistent for next run
2025-07-13 18:57:35,838 - utils.browser_manager - WARNING - Error during global cleanup: event loop closed
```

---

## EXECUTION STATUS
- [✅]
- [✅] 
- [✅] 
- [✅] **SUCCESS**: MULTI-AGENT TESTING SYSTEM FULLY OPERATIONAL

## 🎯 SUCCESS SUMMARY

**AttributeError Fixes Applied and Verified:**


**System Capabilities Verified:**


**Output Files Successfully Generated:**


**System Ready for Infinite Mode Operation**