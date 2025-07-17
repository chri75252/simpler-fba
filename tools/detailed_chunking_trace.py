#!/usr/bin/env python3
"""
DETAILED CHUNKING TRACE: Dual-Level Chunking System Analysis
Shows how the two different chunking mechanisms work together:
1. chunk_size_categories: 1 (hybrid processing level)
2. supplier_extraction_batch_size: 3 (internal processing level)
"""

import sys
import os
import json
from typing import Dict, Any, List

# Add tools directory to path
sys.path.append('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools')

def detailed_chunking_trace():
    """Trace the dual-level chunking system in detail"""
    
    print("🔍 DETAILED CHUNKING TRACE: Dual-Level System Analysis")
    print("=" * 70)
    
    # Load actual configuration
    config_path = '/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/config/system_config.json'
    with open(config_path, 'r') as f:
        system_config = json.load(f)
    
    # Extract hybrid processing configuration
    hybrid_config = system_config.get("hybrid_processing", {})
    processing_modes = hybrid_config.get("processing_modes", {})
    chunked_config = processing_modes.get("chunked", {})
    
    # Key configuration values
    chunk_size_categories = chunked_config.get("chunk_size_categories", 10)
    switch_after_categories = hybrid_config.get("switch_to_amazon_after_categories", 10)
    
    print(f"📋 HYBRID PROCESSING CONFIG:")
    print(f"   ✅ Enabled: {hybrid_config.get('enabled', False)}")
    print(f"   🔢 chunk_size_categories: {chunk_size_categories}")
    print(f"   🔄 switch_to_amazon_after_categories: {switch_after_categories}")
    print()
    
    # Extract supplier extraction configuration  
    supplier_extraction_config = system_config.get("supplier_extraction", {})
    supplier_extraction_batch_size = supplier_extraction_config.get("batch_size", 3)
    
    print(f"📦 SUPPLIER EXTRACTION CONFIG:")
    print(f"   🔢 supplier_extraction_batch_size: {supplier_extraction_batch_size}")
    print()
    
    # Simulate execution with realistic data
    print("🚀 EXECUTION SIMULATION")
    print("=" * 50)
    
    # Simulate category list (10 categories)
    category_urls = [f"category_{i}" for i in range(1, 11)]
    print(f"📂 Total categories to process: {len(category_urls)}")
    print(f"   Categories: {category_urls}")
    print()
    
    # LEVEL 1: Hybrid Processing Chunking (chunk_size_categories)
    print("🔄 LEVEL 1: HYBRID PROCESSING CHUNKING")
    print("-" * 40)
    
    hybrid_chunks = []
    for chunk_start in range(0, len(category_urls), chunk_size_categories):
        chunk_end = min(chunk_start + chunk_size_categories, len(category_urls))
        chunk_categories = category_urls[chunk_start:chunk_end]
        hybrid_chunks.append((chunk_start, chunk_end, chunk_categories))
    
    print(f"🔢 Chunk size (categories): {chunk_size_categories}")
    print(f"📦 Number of hybrid chunks: {len(hybrid_chunks)}")
    
    for i, (start, end, categories) in enumerate(hybrid_chunks, 1):
        print(f"   Chunk {i}: categories {start+1}-{end} ({len(categories)} categories)")
        print(f"      📋 {categories}")
    print()
    
    # LEVEL 2: Supplier Extraction Batching (supplier_extraction_batch_size)
    print("📦 LEVEL 2: SUPPLIER EXTRACTION BATCHING")
    print("-" * 40)
    
    for hybrid_chunk_num, (start, end, chunk_categories) in enumerate(hybrid_chunks, 1):
        print(f"🔄 Processing Hybrid Chunk {hybrid_chunk_num} ({len(chunk_categories)} categories)")
        
        # Internal batching within this hybrid chunk
        supplier_batches = []
        for batch_start in range(0, len(chunk_categories), supplier_extraction_batch_size):
            batch_end = min(batch_start + supplier_extraction_batch_size, len(chunk_categories))
            batch_categories = chunk_categories[batch_start:batch_end]
            supplier_batches.append((batch_start, batch_end, batch_categories))
        
        print(f"   🔢 Supplier batch size: {supplier_extraction_batch_size}")
        print(f"   📦 Number of supplier batches: {len(supplier_batches)}")
        
        for j, (batch_start, batch_end, batch_categories) in enumerate(supplier_batches, 1):
            print(f"      Supplier Batch {j}: {batch_categories}")
            
            # Simulate processing each category in the batch
            for k, category in enumerate(batch_categories, 1):
                category_index = start + batch_start + k
                print(f"         └─ Processing {category} (global index: {category_index})")
        
        print(f"   🎯 After processing chunk {hybrid_chunk_num}, system would switch to Amazon analysis")
        print()
    
    # Show the dual-level relationship
    print("🧩 DUAL-LEVEL CHUNKING RELATIONSHIP")
    print("-" * 40)
    print(f"🔄 Hybrid Level (chunk_size_categories: {chunk_size_categories}):")
    print(f"   - Controls when to switch between supplier extraction and Amazon analysis")
    print(f"   - Creates {len(hybrid_chunks)} hybrid chunks")
    print(f"   - Each chunk triggers one cycle of supplier extraction + Amazon analysis")
    print()
    print(f"📦 Supplier Level (supplier_extraction_batch_size: {supplier_extraction_batch_size}):")
    print(f"   - Controls memory management within each hybrid chunk")
    print(f"   - Processes categories in smaller batches to avoid memory issues")
    print(f"   - Each supplier batch processes {supplier_extraction_batch_size} categories at once")
    print()
    
    # Show configuration impact
    print("⚡ CONFIGURATION IMPACT ANALYSIS")
    print("-" * 40)
    print(f"Current Config Impact:")
    print(f"   📊 chunk_size_categories = {chunk_size_categories}")
    print(f"      → Creates {len(hybrid_chunks)} cycles of [Extract→Analyze]")
    print(f"      → Very frequent switching between extraction and analysis")
    print(f"      → Immediate analysis after each category")
    print()
    print(f"   📦 supplier_extraction_batch_size = {supplier_extraction_batch_size}")
    print(f"      → Within each hybrid chunk, processes {supplier_extraction_batch_size} categories per memory batch")
    print(f"      → Good for memory management")
    print()
    
    # Show execution flow
    print("🎯 ACTUAL EXECUTION FLOW")
    print("-" * 40)
    total_cycles = len(hybrid_chunks)
    print(f"With {len(category_urls)} categories, system will execute {total_cycles} cycles:")
    print()
    
    for i, (start, end, chunk_categories) in enumerate(hybrid_chunks, 1):
        print(f"Cycle {i}:")
        print(f"   1️⃣ Extract from categories: {chunk_categories}")
        print(f"      └─ Internal batching: {supplier_extraction_batch_size} categories per batch")
        print(f"   2️⃣ Immediately analyze extracted products")
        print(f"   3️⃣ Store profitable results")
        if i < total_cycles:
            print(f"   ↓ Switch back to supplier extraction")
        print()

if __name__ == "__main__":
    detailed_chunking_trace()