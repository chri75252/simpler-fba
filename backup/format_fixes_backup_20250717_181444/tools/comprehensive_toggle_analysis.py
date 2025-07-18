#!/usr/bin/env python3
"""
Comprehensive Toggle Analysis and Testing Script
Analyzes batches vs chunks, toggle integration, and provides detailed experiments
"""

import sys
import os
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Add tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

def analyze_code_integration(search_pattern, code_files):
    """Search for toggle integration in code files"""
    results = []
    
    for file_path in code_files:
        if not os.path.exists(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Search for pattern
            matches = re.finditer(search_pattern, content, re.IGNORECASE)
            for match in matches:
                # Get line number
                line_num = content[:match.start()].count('\n') + 1
                line_content = content.split('\n')[line_num - 1].strip()
                
                results.append({
                    'file': file_path,
                    'line': line_num,
                    'content': line_content,
                    'match': match.group()
                })
                
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    return results

def test_toggle_integration(toggle_path, expected_behavior, test_config):
    """Test a specific toggle by modifying config and observing behavior"""
    print(f"\n🧪 Testing Toggle: {toggle_path}")
    print(f"Expected Behavior: {expected_behavior}")
    
    # Load current config
    with open('config/system_config.json', 'r') as f:
        config = json.load(f)
    
    # Apply test configuration
    original_values = {}
    for key_path, new_value in test_config.items():
        keys = key_path.split('.')
        current = config
        
        # Navigate to the correct nested location
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Store original value
        original_values[key_path] = current.get(keys[-1], "NOT_SET")
        
        # Set new value
        current[keys[-1]] = new_value
        print(f"   {key_path}: {original_values[key_path]} → {new_value}")
    
    # Save test config
    with open('config/system_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Clear processing state
    state_path = "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json"
    if os.path.exists(state_path):
        os.remove(state_path)
    
    # Run test
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/debug/toggle_test_{toggle_path.replace('.', '_')}_{timestamp}.log"
    
    print(f"   Running test (60s timeout)...")
    process = subprocess.Popen(
        [sys.executable, "run_custom_poundwholesale.py"],
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid
    )
    
    # Wait 60 seconds
    try:
        process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait()
    
    # Analyze results
    results = analyze_test_results(log_file, expected_behavior)
    
    # Restore original config
    for key_path, original_value in original_values.items():
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            current = current[key]
        
        if original_value == "NOT_SET":
            if keys[-1] in current:
                del current[keys[-1]]
        else:
            current[keys[-1]] = original_value
    
    with open('config/system_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    return results

def analyze_test_results(log_file, expected_behavior):
    """Analyze test results from log file"""
    results = {
        'log_file': log_file,
        'expected': expected_behavior,
        'observed': [],
        'evidence': []
    }
    
    if not os.path.exists(log_file):
        results['observed'].append("Log file not found")
        return results
    
    # Read log file
    with open(log_file, 'r') as f:
        log_content = f.read()
    
    # Extract configuration values
    config_pattern = r'📊 CONFIGURATION VALUES:(.*?)(?=\n\d{4}-\d{2}-\d{2}|\n---|\nStarting|$)'
    config_match = re.search(config_pattern, log_content, re.DOTALL)
    
    if config_match:
        config_section = config_match.group(1)
        results['evidence'].append(f"Configuration section found: {len(config_section)} chars")
        
        # Extract specific values
        value_patterns = [
            r'max_products_to_process: (\d+)',
            r'max_products_per_category: (\d+)',
            r'supplier_extraction_batch_size: (\d+)',
            r'max_products_per_cycle: (\d+)',
            r'update_frequency_products: (\d+)'
        ]
        
        for pattern in value_patterns:
            matches = re.findall(pattern, config_section)
            if matches:
                results['observed'].append(f"{pattern.split(':')[0].strip('r')}: {matches[0]}")
    
    # Check for processing state
    state_files = [
        "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
        "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json"
    ]
    
    for state_file in state_files:
        if os.path.exists(state_file):
            stat = os.stat(state_file)
            results['evidence'].append(f"{state_file}: {stat.st_size} bytes, {datetime.fromtimestamp(stat.st_mtime).isoformat()}")
            
            # Analyze content
            if state_file.endswith('.json'):
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    
                    if 'products_cache' in state_file:
                        results['observed'].append(f"Products in cache: {len(data)}")
                        if data:
                            categories = {}
                            for product in data:
                                cat = product.get('source_url', '').split('/')[-1]
                                categories[cat] = categories.get(cat, 0) + 1
                            results['observed'].append(f"Products per category: {categories}")
                    
                    elif 'processing_state' in state_file:
                        results['observed'].append(f"Products extracted: {data.get('supplier_extraction_progress', {}).get('products_extracted_total', 0)}")
                        results['observed'].append(f"Current batch: {data.get('supplier_extraction_progress', {}).get('current_batch_number', 0)}")
                        
                except Exception as e:
                    results['evidence'].append(f"Error reading {state_file}: {e}")
    
    return results

def main():
    """Main analysis function"""
    print("🔍 Comprehensive Toggle Analysis and Testing")
    print("=" * 60)
    
    # Define code files to analyze
    code_files = [
        "tools/passive_extraction_workflow_latest.py",
        "tools/configurable_supplier_scraper.py",
        "tools/enhanced_state_manager.py"
    ]
    
    # Test 1: Batch vs Chunk Terminology
    print("\n📊 BATCH vs CHUNK ANALYSIS")
    print("=" * 40)
    
    batch_integrations = analyze_code_integration(r'batch.*size|batch.*frequency', code_files)
    chunk_integrations = analyze_code_integration(r'chunk.*size|chunk.*categories', code_files)
    
    print(f"Batch-related integrations found: {len(batch_integrations)}")
    for integration in batch_integrations[:5]:  # Show first 5
        print(f"  {integration['file']}:{integration['line']} - {integration['content'][:80]}...")
    
    print(f"\nChunk-related integrations found: {len(chunk_integrations)}")
    for integration in chunk_integrations[:5]:  # Show first 5
        print(f"  {integration['file']}:{integration['line']} - {integration['content'][:80]}...")
    
    # Test 2: Duplicate max_products_per_category toggles
    print("\n🔄 DUPLICATE TOGGLE ANALYSIS")
    print("=" * 40)
    
    # Test processing_limits.max_products_per_category
    results_1 = test_toggle_integration(
        "processing_limits.max_products_per_category",
        "Products per category limited to test value",
        {"processing_limits.max_products_per_category": 3}
    )
    
    # Test system.max_products_per_category
    results_2 = test_toggle_integration(
        "system.max_products_per_category",
        "Products per category limited to test value",
        {"system.max_products_per_category": 7}
    )
    
    # Test 3: Supplier extraction progress
    print("\n📈 SUPPLIER EXTRACTION PROGRESS ANALYSIS")
    print("=" * 40)
    
    progress_results = test_toggle_integration(
        "supplier_extraction_progress",
        "Detailed progress tracking with subcategory index",
        {
            "supplier_extraction_progress.enabled": True,
            "supplier_extraction_progress.track_subcategory_index": True,
            "supplier_extraction_progress.update_frequency_products": 2
        }
    )
    
    # Test 4: Hybrid processing chunks
    print("\n🔄 HYBRID PROCESSING CHUNK ANALYSIS")
    print("=" * 40)
    
    hybrid_results = test_toggle_integration(
        "hybrid_processing.chunked",
        "Categories processed in chunks",
        {
            "hybrid_processing.enabled": True,
            "hybrid_processing.chunked.enabled": True,
            "hybrid_processing.chunked.chunk_size_categories": 2
        }
    )
    
    # Test 5: Batch synchronization
    print("\n⚡ BATCH SYNCHRONIZATION ANALYSIS")
    print("=" * 40)
    
    batch_sync_results = test_toggle_integration(
        "batch_synchronization",
        "All batch sizes synchronized",
        {
            "batch_synchronization.enabled": True,
            "batch_synchronization.synchronize_all_batch_sizes": True,
            "batch_synchronization.target_batch_size": 4
        }
    )
    
    # Generate comprehensive report
    print("\n📋 COMPREHENSIVE RESULTS SUMMARY")
    print("=" * 60)
    
    all_results = {
        "batch_vs_chunk_analysis": {
            "batch_integrations": len(batch_integrations),
            "chunk_integrations": len(chunk_integrations)
        },
        "duplicate_toggles": {
            "processing_limits": results_1,
            "system": results_2
        },
        "supplier_extraction_progress": progress_results,
        "hybrid_processing": hybrid_results,
        "batch_synchronization": batch_sync_results
    }
    
    # Save detailed results
    results_file = f"config/comprehensive_toggle_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"Detailed results saved to: {results_file}")
    
    return all_results

if __name__ == "__main__":
    import signal
    results = main()
    
    # Print summary
    print("\n🎯 FINAL SUMMARY")
    print("=" * 30)
    
    for test_name, result in results.items():
        if isinstance(result, dict) and 'observed' in result:
            print(f"{test_name}: {len(result['observed'])} observations")
        else:
            print(f"{test_name}: {result}")