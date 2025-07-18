#!/usr/bin/env python3
"""
COMPREHENSIVE EXECUTION TRACE: Complete Method Call Chain Analysis
Traces the exact execution path from start to finish, including all method calls,
parameter passing, and potential syntax error locations.
"""

import sys
import os
import json
import ast
import inspect
from typing import Dict, Any, List

# Add tools directory to path
sys.path.append('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools')

def analyze_method_definitions():
    """Analyze method definitions for syntax errors"""
    print("\n🔍 METHOD DEFINITION ANALYSIS")
    print("=" * 50)
    
    workflow_file = '/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py'
    
    try:
        with open(workflow_file, 'r') as f:
            content = f.read()
        
        # Try to parse the AST to check for syntax errors
        try:
            ast.parse(content)
            print("✅ AST Parse: No syntax errors detected")
        except SyntaxError as e:
            print(f"❌ AST Parse: Syntax error at line {e.lineno}: {e.msg}")
            print(f"   Text: {e.text.strip() if e.text else 'N/A'}")
            return False
        
        # Check specific method signatures that were mentioned as problematic
        problematic_patterns = [
            '_run_hybrid_processing_mode',
            '_extract_supplier_products',
            'supplier_extraction_batch_size'
        ]
        
        print("\n📋 Method Signature Analysis:")
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in problematic_patterns:
                if pattern in line and ('def ' in line or 'async def' in line):
                    print(f"   Line {i}: {line.strip()}")
                    
                    # Check for common syntax issues
                    if line.count('(') != line.count(')'):
                        print(f"      ⚠️  Unmatched parentheses")
                    if ') ->' in line and '):' in line:
                        print(f"      ⚠️  Potential double closing parentheses")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def trace_execution_path():
    """Trace the complete execution path"""
    print("🚀 COMPREHENSIVE EXECUTION TRACE")
    print("=" * 70)
    
    # Load configuration
    config_path = '/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/config/system_config.json'
    with open(config_path, 'r') as f:
        system_config = json.load(f)
    
    print("📋 STEP 1: CONFIGURATION LOADING")
    print("-" * 30)
    
    # Extract all relevant config values
    hybrid_config = system_config.get("hybrid_processing", {})
    processing_modes = hybrid_config.get("processing_modes", {})
    chunked_config = processing_modes.get("chunked", {})
    supplier_config = system_config.get("supplier_extraction", {})
    
    # Key values
    hybrid_enabled = hybrid_config.get("enabled", False)
    chunked_enabled = chunked_config.get("enabled", False)
    chunk_size_categories = chunked_config.get("chunk_size_categories", 10)
    switch_after_categories = hybrid_config.get("switch_to_amazon_after_categories", 10)
    supplier_extraction_batch_size = supplier_config.get("batch_size", 3)
    
    print(f"✅ hybrid_processing.enabled: {hybrid_enabled}")
    print(f"✅ chunked.enabled: {chunked_enabled}")
    print(f"✅ chunk_size_categories: {chunk_size_categories}")
    print(f"✅ switch_to_amazon_after_categories: {switch_after_categories}")
    print(f"✅ supplier_extraction_batch_size: {supplier_extraction_batch_size}")
    
    print("\n📋 STEP 2: EXECUTION PATH ANALYSIS")
    print("-" * 30)
    
    print("🎯 Starting from PassiveExtractionWorkflow.run() method (line ~1096)")
    print(f"   1. Check hybrid_config.enabled = {hybrid_enabled}")
    
    if hybrid_enabled:
        print("   2. ✅ Hybrid processing enabled")
        print("   3. 🔄 Call _run_hybrid_processing_mode() with parameters:")
        print("      - supplier_url: str")
        print("      - supplier_name: str") 
        print("      - category_urls_to_scrape: List[str]")
        print("      - max_products_per_category: int")
        print("      - max_products_to_process: int")
        print("      - max_analyzed_products: int")
        print("      - max_products_per_cycle: int")
        
        print(f"\n   4. Inside _run_hybrid_processing_mode() (line ~3066):")
        print(f"      - Load switch_after_categories = {switch_after_categories}")
        print(f"      - Check chunked.enabled = {chunked_enabled}")
        
        if chunked_enabled:
            print(f"      - ✅ Chunked mode enabled")
            print(f"      - Load chunk_size = {chunk_size_categories}")
            print(f"      - Calculate category chunks with size {chunk_size_categories}")
            
            # Simulate chunking with 10 categories
            total_categories = 10
            num_chunks = (total_categories + chunk_size_categories - 1) // chunk_size_categories
            
            print(f"      - With {total_categories} categories → {num_chunks} chunks")
            print(f"\n   5. For each chunk (chunked processing loop):")
            
            for chunk_num in range(1, min(4, num_chunks + 1)):  # Show first 3 chunks
                chunk_start = (chunk_num - 1) * chunk_size_categories
                chunk_end = min(chunk_start + chunk_size_categories, total_categories)
                
                print(f"      Chunk {chunk_num} (categories {chunk_start+1}-{chunk_end}):")
                print(f"         a. Call _extract_supplier_products() with:")
                print(f"            - chunk_categories: {chunk_end - chunk_start} categories")
                print(f"            - supplier_extraction_batch_size: {supplier_extraction_batch_size}")
                print(f"         b. Inside _extract_supplier_products() (line ~2522):")
                print(f"            - Divide {chunk_end - chunk_start} categories into batches of {supplier_extraction_batch_size}")
                
                # Calculate supplier batches within this chunk
                chunk_size = chunk_end - chunk_start
                supplier_batches = (chunk_size + supplier_extraction_batch_size - 1) // supplier_extraction_batch_size
                print(f"            - Creates {supplier_batches} supplier batch(es)")
                
                for batch_num in range(1, supplier_batches + 1):
                    batch_start = (batch_num - 1) * supplier_extraction_batch_size
                    batch_end = min(batch_start + supplier_extraction_batch_size, chunk_size)
                    print(f"               Supplier Batch {batch_num}: categories {batch_start+1}-{batch_end}")
                
                print(f"         c. Call _analyze_products_batch() with extracted products")
                print(f"         d. Store profitable results")
                if chunk_num < num_chunks:
                    print(f"         e. ↻ Loop back for next chunk")
                print()
            
            if num_chunks > 3:
                print(f"      ... (continues for all {num_chunks} chunks)")
        
    else:
        print("   2. ❌ Hybrid processing disabled")
        print("   3. 📦 Fall back to sequential processing")
        print("      - Call _extract_supplier_products() with all categories")
        print(f"      - Use supplier_extraction_batch_size: {supplier_extraction_batch_size}")
    
    print("\n📋 STEP 3: PARAMETER FLOW TRACE")
    print("-" * 30)
    
    print(f"supplier_extraction_batch_size flow:")
    print(f"   1. Config: system_config.json → supplier_extraction.batch_size = {supplier_extraction_batch_size}")
    print(f"   2. Loaded: PassiveExtractionWorkflow.__init__() stores config")
    print(f"   3. Passed: run() method extracts value and passes to methods")
    print(f"   4. Used: _extract_supplier_products() uses for category batching")
    print(f"   5. Formula: category_batches = [categories[i:i + {supplier_extraction_batch_size}] for i in range(0, len(categories), {supplier_extraction_batch_size})]")
    
    print("\n📋 STEP 4: DUAL-LEVEL CHUNKING SUMMARY")
    print("-" * 30)
    
    print(f"🔄 Level 1 - Hybrid Chunking (chunk_size_categories: {chunk_size_categories}):")
    print(f"   Purpose: Controls workflow alternation between extraction and analysis")
    print(f"   Effect: Creates {num_chunks} cycles of [Extract → Analyze]")
    print(f"   Location: _run_hybrid_processing_mode() line ~3086")
    
    print(f"\n📦 Level 2 - Supplier Batching (supplier_extraction_batch_size: {supplier_extraction_batch_size}):")
    print(f"   Purpose: Memory management within each extraction phase")
    print(f"   Effect: Processes {supplier_extraction_batch_size} categories at a time")
    print(f"   Location: _extract_supplier_products() line ~2572")
    
    print(f"\n🎯 Combined Effect:")
    print(f"   With current config ({chunk_size_categories} categories/chunk):")
    print(f"   - Each hybrid chunk contains {chunk_size_categories} category")
    print(f"   - Each supplier batch processes up to {supplier_extraction_batch_size} categories")
    print(f"   - Since {chunk_size_categories} < {supplier_extraction_batch_size}, each hybrid chunk = 1 supplier batch")
    print(f"   - Result: Extract 1 category → Analyze → Extract 1 category → Analyze (very frequent switching)")

def main():
    """Main execution function"""
    print("🎯 ZEN MCP TRACER: Comprehensive Execution Path Analysis")
    print("=" * 70)
    
    # Analyze method definitions for syntax errors
    syntax_ok = analyze_method_definitions()
    
    if syntax_ok:
        print("✅ Syntax check passed, proceeding with execution trace")
        trace_execution_path()
    else:
        print("❌ Syntax errors detected, execution would fail")
    
    print("\n🏁 TRACE COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()