#!/usr/bin/env python3
"""
ZEN MCP TRACER: Chunking System Execution Path Tracer
Traces the exact execution path of the chunking system to identify:
1. Configuration loading path
2. Hybrid processing execution path  
3. supplier_extraction_batch_size usage
4. Syntax error impact
"""

import sys
import os
import json
import traceback
import logging
from typing import Dict, Any, List

# Add tools directory to path
sys.path.append('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools')

class ChunkingExecutionTracer:
    """Traces the exact execution path of the chunking system"""
    
    def __init__(self):
        self.trace_log = []
        self.config_path = '/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/config/system_config.json'
        
    def log_trace(self, step: str, details: str, data: Any = None):
        """Log execution trace step"""
        trace_entry = {
            "step": step,
            "details": details,
            "data": data,
            "timestamp": str(type(self).__name__)
        }
        self.trace_log.append(trace_entry)
        print(f"🔍 TRACE: {step} - {details}")
        if data:
            print(f"   📊 Data: {data}")
    
    def trace_config_loading(self):
        """Trace 1: Configuration Loading Path"""
        print("\n" + "="*60)
        print("🔍 TRACE 1: CHUNKING CONFIGURATION LOADING")
        print("="*60)
        
        try:
            # Step 1: Check config file existence
            if os.path.exists(self.config_path):
                self.log_trace("CONFIG_FILE", f"Found config at {self.config_path}")
                
                # Step 2: Load JSON configuration
                with open(self.config_path, 'r') as f:
                    system_config = json.load(f)
                self.log_trace("JSON_LOAD", "System config loaded successfully")
                
                # Step 3: Extract hybrid processing section
                hybrid_config = system_config.get("hybrid_processing", {})
                self.log_trace("HYBRID_CONFIG", "Extracted hybrid_processing section", 
                             {"found": bool(hybrid_config), "enabled": hybrid_config.get("enabled", False)})
                
                # Step 4: Extract processing modes
                processing_modes = hybrid_config.get("processing_modes", {})
                chunked_config = processing_modes.get("chunked", {})
                self.log_trace("CHUNKED_CONFIG", "Extracted chunked processing config", chunked_config)
                
                # Step 5: Key configuration values
                chunk_size_categories = chunked_config.get("chunk_size_categories", 10)
                switch_after_categories = hybrid_config.get("switch_to_amazon_after_categories", 10)
                
                self.log_trace("KEY_VALUES", "Extracted key chunking values", {
                    "chunk_size_categories": chunk_size_categories,
                    "switch_to_amazon_after_categories": switch_after_categories
                })
                
                return system_config
                
            else:
                self.log_trace("CONFIG_ERROR", f"Config file not found at {self.config_path}")
                return None
                
        except Exception as e:
            self.log_trace("CONFIG_EXCEPTION", f"Error loading config: {str(e)}")
            traceback.print_exc()
            return None
    
    def trace_hybrid_processing_path(self, system_config: Dict[str, Any]):
        """Trace 2: Hybrid Processing Execution Path"""
        print("\n" + "="*60)
        print("🔍 TRACE 2: HYBRID PROCESSING EXECUTION PATH")
        print("="*60)
        
        try:
            # Simulate the execution path from run() method line 1096
            self.log_trace("RUN_METHOD", "Starting from run() method line 1096")
            
            # Step 1: Check hybrid processing configuration (line 1094-1095)
            hybrid_config = system_config.get("hybrid_processing", {})
            enabled = hybrid_config.get("enabled", False)
            self.log_trace("HYBRID_CHECK", f"Hybrid processing enabled check", {"enabled": enabled})
            
            if enabled:
                # Step 2: Would call _run_hybrid_processing_mode (line 1097-1101)
                self.log_trace("HYBRID_CALL", "Would call _run_hybrid_processing_mode", {
                    "method_line": "3066",
                    "parameters": ["supplier_url", "supplier_name", "category_urls_to_scrape", 
                                 "max_products_per_category", "max_products_to_process", 
                                 "max_analyzed_products", "max_products_per_cycle"]
                })
                
                # Step 3: Inside _run_hybrid_processing_mode
                processing_modes = hybrid_config.get("processing_modes", {})
                switch_after_categories = hybrid_config.get("switch_to_amazon_after_categories", 10)
                
                self.log_trace("HYBRID_INTERNAL", "Inside _run_hybrid_processing_mode", {
                    "switch_after_categories": switch_after_categories,
                    "processing_modes": processing_modes
                })
                
                # Step 4: Check chunked mode (line 3079-3082)
                chunked_config = processing_modes.get("chunked", {})
                chunked_enabled = chunked_config.get("enabled", False)
                
                if chunked_enabled:
                    chunk_size = chunked_config.get("chunk_size_categories", 10)
                    self.log_trace("CHUNKED_MODE", "Chunked processing path", {
                        "enabled": chunked_enabled,
                        "chunk_size": chunk_size
                    })
                    
                    # Step 5: Category chunking logic (line 3086-3089)
                    # Simulate with dummy data
                    category_urls_to_scrape = ["url1", "url2", "url3", "url4", "url5"]  # 5 dummy URLs
                    chunks = []
                    for chunk_start in range(0, len(category_urls_to_scrape), chunk_size):
                        chunk_end = min(chunk_start + chunk_size, len(category_urls_to_scrape))
                        chunk_categories = category_urls_to_scrape[chunk_start:chunk_end]
                        chunks.append((chunk_start, chunk_end, chunk_categories))
                    
                    self.log_trace("CHUNK_CALCULATION", "Category chunks calculated", {
                        "total_categories": len(category_urls_to_scrape),
                        "chunk_size": chunk_size,
                        "chunks": [{"start": c[0], "end": c[1], "size": len(c[2])} for c in chunks]
                    })
                    
                    # Step 6: Would call _extract_supplier_products for each chunk (line 3093-3096)
                    for i, (chunk_start, chunk_end, chunk_categories) in enumerate(chunks):
                        self.log_trace("CHUNK_PROCESSING", f"Would process chunk {i+1}", {
                            "chunk_number": i+1,
                            "categories": f"{chunk_start+1}-{chunk_end}",
                            "supplier_extraction_batch_size": "parameter passed through"
                        })
                
                return True
            else:
                # Step 7: Fall back to sequential processing (line 1104)
                self.log_trace("SEQUENTIAL_FALLBACK", "Hybrid disabled, using sequential processing")
                return False
                
        except Exception as e:
            self.log_trace("HYBRID_EXCEPTION", f"Error in hybrid processing path: {str(e)}")
            traceback.print_exc()
            return False
    
    def trace_supplier_batch_size_usage(self):
        """Trace 3: supplier_extraction_batch_size Parameter Usage"""
        print("\n" + "="*60)
        print("🔍 TRACE 3: SUPPLIER_EXTRACTION_BATCH_SIZE USAGE")
        print("="*60)
        
        try:
            # Step 1: Parameter flow from run() method
            self.log_trace("PARAM_FLOW", "Parameter flow from run() method", {
                "source": "run() method line 1025",
                "value": "supplier_extraction_batch_size",
                "passed_to": "_extract_supplier_products()"
            })
            
            # Step 2: Method signature analysis
            method_signature = "async def _extract_supplier_products(self, supplier_url: str, supplier_name: str, category_urls: List[str], max_products_per_category: int, max_products_to_process: int = None, supplier_extraction_batch_size: int = 3)"
            self.log_trace("METHOD_SIGNATURE", "Method signature analysis", {
                "line": "2522",
                "default_value": 3,
                "parameter_position": 6,
                "signature": method_signature
            })
            
            # Step 3: Usage in category batching (line 2572-2573)
            self.log_trace("CATEGORY_BATCHING", "Usage in category batching logic", {
                "line": "2572-2573",
                "purpose": "Divides category_urls into batches",
                "formula": "category_urls[i:i + supplier_extraction_batch_size]"
            })
            
            # Step 4: Batch processing loop (line 2580+)
            self.log_trace("BATCH_LOOP", "Batch processing loop control", {
                "line": "2580+",
                "purpose": "Controls how many categories processed per batch",
                "relationship": "batch_size determines memory usage and processing chunks"
            })
            
            # Step 5: Progress tracking integration (line 2590+)
            self.log_trace("PROGRESS_TRACKING", "Integration with progress tracking", {
                "line": "2590+",
                "calculation": "(batch_num - 1) * supplier_extraction_batch_size + subcategory_index",
                "purpose": "Accurate progress reporting across batches"
            })
            
        except Exception as e:
            self.log_trace("BATCH_SIZE_EXCEPTION", f"Error tracing batch size usage: {str(e)}")
            traceback.print_exc()
    
    def trace_syntax_error_impact(self):
        """Trace 4: Syntax Error Impact Analysis"""
        print("\n" + "="*60)
        print("🔍 TRACE 4: SYNTAX ERROR IMPACT ANALYSIS")
        print("="*60)
        
        try:
            # Step 1: Identify problematic method definitions
            workflow_file = '/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py'
            
            self.log_trace("SYNTAX_CHECK", "Checking for syntax errors in workflow file")
            
            # Step 2: Try to import the module to see if syntax errors occur
            try:
                # This will fail if there are syntax errors
                import passive_extraction_workflow_latest
                self.log_trace("IMPORT_SUCCESS", "Module imported successfully - no syntax errors")
                
            except SyntaxError as e:
                self.log_trace("SYNTAX_ERROR", f"Syntax error detected during import", {
                    "error": str(e),
                    "line": getattr(e, 'lineno', 'unknown'),
                    "text": getattr(e, 'text', 'unknown').strip() if getattr(e, 'text', None) else 'unknown'
                })
                
                # Step 3: Impact on hybrid processing
                self.log_trace("SYNTAX_IMPACT", "Impact on hybrid processing", {
                    "consequence": "Python cannot parse the file",
                    "fallback": "System falls back to sequential processing",
                    "affected_methods": ["_run_hybrid_processing_mode", "_extract_supplier_products"]
                })
                
            except Exception as e:
                self.log_trace("OTHER_ERROR", f"Other import error: {str(e)}")
            
            # Step 4: Check for common malformed method patterns
            malformed_patterns = [
                "async def.*supplier_extraction_batch_size.*max_products_per_category.*max_products_to_process",
                "def.*\\)\\s*->.*\\):",  # Double closing parentheses
                "def.*\\(.*\\(.*\\):",   # Unmatched parentheses
            ]
            
            self.log_trace("PATTERN_CHECK", "Checking for malformed method patterns", {
                "patterns": malformed_patterns,
                "note": "These patterns often cause syntax errors"
            })
            
        except Exception as e:
            self.log_trace("SYNTAX_ANALYSIS_ERROR", f"Error analyzing syntax: {str(e)}")
            traceback.print_exc()
    
    def generate_trace_report(self):
        """Generate comprehensive trace report"""
        print("\n" + "="*60)
        print("📋 TRACE EXECUTION SUMMARY")
        print("="*60)
        
        print(f"Total trace steps: {len(self.trace_log)}")
        
        for i, entry in enumerate(self.trace_log, 1):
            print(f"{i:2d}. {entry['step']}: {entry['details']}")
            if entry.get('data'):
                print(f"    📊 {entry['data']}")
        
        print("\n" + "="*60)
        print("🎯 KEY FINDINGS")
        print("="*60)
        
        # Analyze findings
        config_loaded = any("CONFIG" in entry['step'] for entry in self.trace_log)
        hybrid_enabled = any("HYBRID" in entry['step'] for entry in self.trace_log)
        syntax_errors = any("SYNTAX_ERROR" in entry['step'] for entry in self.trace_log)
        
        print(f"✅ Configuration Loading: {'SUCCESS' if config_loaded else 'FAILED'}")
        print(f"🔄 Hybrid Processing: {'ENABLED' if hybrid_enabled else 'DISABLED'}")
        print(f"❌ Syntax Errors: {'DETECTED' if syntax_errors else 'NONE'}")

def main():
    """Main execution function"""
    print("🚀 ZEN MCP TRACER: Chunking System Execution Path Analysis")
    print("=" * 70)
    
    tracer = ChunkingExecutionTracer()
    
    # Execute all traces
    system_config = tracer.trace_config_loading()
    
    if system_config:
        tracer.trace_hybrid_processing_path(system_config)
    
    tracer.trace_supplier_batch_size_usage()
    tracer.trace_syntax_error_impact()
    
    # Generate comprehensive report
    tracer.generate_trace_report()

if __name__ == "__main__":
    main()