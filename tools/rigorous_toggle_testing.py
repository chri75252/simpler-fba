#!/usr/bin/env python3
"""
Rigorous Toggle Testing with Proper Archiving and Evidence Collection
Addresses all issues: proper .bakN archiving, actual toggle updates, evidence-backed claims
"""

import sys
import os
import json
import subprocess
import time
import shutil
import signal
from datetime import datetime
from pathlib import Path

def create_experiment_archive(experiment_number, description):
    """Create .bakN archives for all relevant files before experiment"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_archive = [
        "config/system_config.json",
        "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
        "OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json",
        "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json"
    ]
    
    archive_results = {}
    
    for file_path in files_to_archive:
        if os.path.exists(file_path):
            backup_path = f"{file_path}.bak{experiment_number}"
            try:
                shutil.copy2(file_path, backup_path)
                archive_results[file_path] = backup_path
                print(f"📦 Archived: {file_path} → {backup_path}")
            except Exception as e:
                print(f"❌ Archive failed for {file_path}: {e}")
        else:
            print(f"⚠️  File not found for archiving: {file_path}")
    
    return archive_results

def clear_processing_state():
    """Clear all processing state files to ensure fresh start"""
    state_files = [
        "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
        "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json"
    ]
    
    cleared_files = []
    for file_path in state_files:
        if os.path.exists(file_path):
            os.remove(file_path)
            cleared_files.append(file_path)
            print(f"🗑️  Cleared: {file_path}")
    
    return cleared_files

def apply_toggle_configuration(config_changes):
    """Apply configuration changes and verify they were applied"""
    config_path = "config/system_config.json"
    
    # Load current config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Store original values
    original_values = {}
    applied_changes = {}
    
    for key_path, new_value in config_changes.items():
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
        applied_changes[key_path] = {
            'original': original_values[key_path],
            'new': new_value
        }
        
        print(f"🔧 {key_path}: {original_values[key_path]} → {new_value}")
    
    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Verify changes were applied
    with open(config_path, 'r') as f:
        verification_config = json.load(f)
    
    verification_results = {}
    for key_path, expected_value in config_changes.items():
        keys = key_path.split('.')
        current = verification_config
        
        for key in keys:
            current = current.get(key, {})
        
        verification_results[key_path] = {
            'expected': expected_value,
            'actual': current,
            'verified': current == expected_value
        }
    
    return applied_changes, verification_results

def run_experiment_with_timeout(experiment_name, timeout_seconds=90):
    """Run the workflow with specified timeout and capture all output"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/debug/rigorous_test_{experiment_name}_{timestamp}.log"
    
    print(f"▶️  Starting experiment: {experiment_name}")
    print(f"📝 Log file: {log_file}")
    print(f"⏰ Timeout: {timeout_seconds} seconds")
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Start the process
    start_time = time.time()
    process = subprocess.Popen(
        [sys.executable, "run_custom_poundwholesale.py"],
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid
    )
    
    # Wait for specified time
    try:
        process.wait(timeout=timeout_seconds)
        end_time = time.time()
        print(f"✅ Process completed normally after {end_time - start_time:.1f}s")
    except subprocess.TimeoutExpired:
        end_time = time.time()
        print(f"⏰ Process timed out after {timeout_seconds}s - terminating")
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait()
    
    return log_file, end_time - start_time

def analyze_experiment_results(experiment_name, log_file, config_changes):
    """Analyze experiment results with detailed file evidence"""
    results = {
        'experiment': experiment_name,
        'log_file': log_file,
        'config_changes': config_changes,
        'file_evidence': {},
        'log_evidence': {},
        'toggle_verification': {},
        'timestamp': datetime.now().isoformat()
    }
    
    # Analyze output files
    output_files = {
        'processing_state': 'OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json',
        'supplier_cache': 'OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json',
        'linking_map': 'OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json'
    }
    
    for file_type, file_path in output_files.items():
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            file_info = {
                'exists': True,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'content_analysis': {}
            }
            
            # Analyze file content
            try:
                with open(file_path, 'r') as f:
                    content = json.load(f)
                
                if file_type == 'processing_state':
                    progress = content.get('supplier_extraction_progress', {})
                    file_info['content_analysis'] = {
                        'products_extracted_total': progress.get('products_extracted_total', 0),
                        'current_batch_number': progress.get('current_batch_number', 0),
                        'current_category_index': progress.get('current_category_index', 0),
                        'extraction_phase': progress.get('extraction_phase', 'unknown'),
                        'categories_completed': len(progress.get('categories_completed', []))
                    }
                
                elif file_type == 'supplier_cache':
                    if isinstance(content, list):
                        categories = {}
                        for product in content:
                            cat = product.get('source_url', '').split('/')[-1] if product.get('source_url') else 'unknown'
                            categories[cat] = categories.get(cat, 0) + 1
                        
                        file_info['content_analysis'] = {
                            'total_products': len(content),
                            'products_per_category': categories,
                            'price_range': {
                                'min': min([float(str(p.get('price', 0)).replace('£', '')) for p in content if p.get('price')], default=0),
                                'max': max([float(str(p.get('price', 0)).replace('£', '')) for p in content if p.get('price')], default=0)
                            } if content else {'min': 0, 'max': 0}
                        }
                
                elif file_type == 'linking_map':
                    file_info['content_analysis'] = {
                        'total_mappings': len(content) if isinstance(content, dict) else 0
                    }
                    
            except Exception as e:
                file_info['content_analysis'] = {'error': str(e)}
            
            results['file_evidence'][file_type] = file_info
        else:
            results['file_evidence'][file_type] = {'exists': False}
    
    # Analyze log file for configuration values
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Extract configuration section
            config_patterns = [
                r'📊 CONFIGURATION VALUES:',
                r'max_products_to_process: (\d+)',
                r'max_products_per_category: (\d+)',
                r'supplier_extraction_batch_size: (\d+)',
                r'update_frequency_products: (\d+)',
                r'chunk_size_categories: (\d+)'
            ]
            
            log_evidence = {}
            for pattern in config_patterns:
                import re
                matches = re.findall(pattern, log_content)
                if matches:
                    log_evidence[pattern] = matches
            
            results['log_evidence'] = log_evidence
            
        except Exception as e:
            results['log_evidence'] = {'error': str(e)}
    
    return results

def test_supplier_extraction_progress():
    """Test supplier extraction progress toggles with rigorous evidence"""
    experiment_number = 1
    experiment_name = "supplier_extraction_progress"
    
    print(f"\n🧪 EXPERIMENT {experiment_number}: SUPPLIER EXTRACTION PROGRESS")
    print("=" * 60)
    
    # Create archives
    archive_results = create_experiment_archive(experiment_number, experiment_name)
    
    # Clear state
    cleared_files = clear_processing_state()
    
    # Apply configuration
    config_changes = {
        "supplier_extraction_progress.enabled": True,
        "supplier_extraction_progress.track_subcategory_index": True,
        "supplier_extraction_progress.track_product_index_within_category": True,
        "supplier_extraction_progress.recovery_mode": "product_resume",
        "supplier_extraction_progress.progress_display.show_subcategory_progress": True,
        "supplier_extraction_progress.progress_display.show_product_progress": True,
        "supplier_extraction_progress.progress_display.update_frequency_products": 2,
        "supplier_extraction_progress.state_persistence.save_on_category_completion": True,
        "supplier_extraction_progress.state_persistence.batch_save_frequency": 2,
        "system.max_products": 12,
        "system.max_products_per_category": 6
    }
    
    applied_changes, verification = apply_toggle_configuration(config_changes)
    
    # Verify changes were applied
    print("\n🔍 Configuration Verification:")
    for key, verify_data in verification.items():
        status = "✅" if verify_data['verified'] else "❌"
        print(f"  {status} {key}: expected {verify_data['expected']}, got {verify_data['actual']}")
    
    # Run experiment
    log_file, runtime = run_experiment_with_timeout(experiment_name, 120)
    
    # Analyze results
    results = analyze_experiment_results(experiment_name, log_file, config_changes)
    
    return results

def test_supplier_cache_control():
    """Test supplier cache control toggles with rigorous evidence"""
    experiment_number = 2
    experiment_name = "supplier_cache_control"
    
    print(f"\n🧪 EXPERIMENT {experiment_number}: SUPPLIER CACHE CONTROL")
    print("=" * 60)
    
    # Create archives
    archive_results = create_experiment_archive(experiment_number, experiment_name)
    
    # Clear state
    cleared_files = clear_processing_state()
    
    # Apply configuration
    config_changes = {
        "supplier_cache_control.enabled": True,
        "supplier_cache_control.update_frequency_products": 3,
        "supplier_cache_control.force_update_on_interruption": True,
        "supplier_cache_control.cache_modes.conservative.update_frequency_products": 2,
        "supplier_cache_control.cache_modes.conservative.force_validation": True,
        "system.max_products": 10,
        "system.max_products_per_category": 5
    }
    
    applied_changes, verification = apply_toggle_configuration(config_changes)
    
    # Verify changes were applied
    print("\n🔍 Configuration Verification:")
    for key, verify_data in verification.items():
        status = "✅" if verify_data['verified'] else "❌"
        print(f"  {status} {key}: expected {verify_data['expected']}, got {verify_data['actual']}")
    
    # Run experiment
    log_file, runtime = run_experiment_with_timeout(experiment_name, 120)
    
    # Analyze results
    results = analyze_experiment_results(experiment_name, log_file, config_changes)
    
    return results

def test_hybrid_processing():
    """Test hybrid processing toggles with rigorous evidence"""
    experiment_number = 3
    experiment_name = "hybrid_processing"
    
    print(f"\n🧪 EXPERIMENT {experiment_number}: HYBRID PROCESSING")
    print("=" * 60)
    
    # Create archives
    archive_results = create_experiment_archive(experiment_number, experiment_name)
    
    # Clear state
    cleared_files = clear_processing_state()
    
    # Apply configuration
    config_changes = {
        "hybrid_processing.enabled": True,
        "hybrid_processing.switch_to_amazon_after_categories": 2,
        "hybrid_processing.processing_modes.sequential.enabled": False,
        "hybrid_processing.processing_modes.chunked.enabled": True,
        "hybrid_processing.processing_modes.chunked.chunk_size_categories": 3,
        "hybrid_processing.processing_modes.balanced.enabled": False,
        "hybrid_processing.chunked.enabled": True,
        "hybrid_processing.chunked.chunk_size_categories": 3,
        "system.max_products": 15,
        "system.max_products_per_category": 5
    }
    
    applied_changes, verification = apply_toggle_configuration(config_changes)
    
    # Verify changes were applied
    print("\n🔍 Configuration Verification:")
    for key, verify_data in verification.items():
        status = "✅" if verify_data['verified'] else "❌"
        print(f"  {status} {key}: expected {verify_data['expected']}, got {verify_data['actual']}")
    
    # Run experiment
    log_file, runtime = run_experiment_with_timeout(experiment_name, 120)
    
    # Analyze results
    results = analyze_experiment_results(experiment_name, log_file, config_changes)
    
    return results

def test_batch_synchronization():
    """Test batch synchronization toggles with rigorous evidence"""
    experiment_number = 4
    experiment_name = "batch_synchronization"
    
    print(f"\n🧪 EXPERIMENT {experiment_number}: BATCH SYNCHRONIZATION")
    print("=" * 60)
    
    # Create archives
    archive_results = create_experiment_archive(experiment_number, experiment_name)
    
    # Clear state
    cleared_files = clear_processing_state()
    
    # Apply configuration
    config_changes = {
        "batch_synchronization.enabled": True,
        "batch_synchronization.synchronize_all_batch_sizes": True,
        "batch_synchronization.target_batch_size": 4,
        "system.supplier_extraction_batch_size": 4,
        "system.linking_map_batch_size": 4,
        "system.financial_report_batch_size": 4,
        "system.max_products_per_cycle": 4,
        "system.max_products": 16,
        "system.max_products_per_category": 4
    }
    
    applied_changes, verification = apply_toggle_configuration(config_changes)
    
    # Verify changes were applied
    print("\n🔍 Configuration Verification:")
    for key, verify_data in verification.items():
        status = "✅" if verify_data['verified'] else "❌"
        print(f"  {status} {key}: expected {verify_data['expected']}, got {verify_data['actual']}")
    
    # Run experiment
    log_file, runtime = run_experiment_with_timeout(experiment_name, 120)
    
    # Analyze results
    results = analyze_experiment_results(experiment_name, log_file, config_changes)
    
    return results

def main():
    """Run all rigorous toggle tests"""
    print("🔬 RIGOROUS TOGGLE TESTING WITH EVIDENCE COLLECTION")
    print("=" * 70)
    
    all_results = {}
    
    # Run each test
    tests = [
        test_supplier_extraction_progress,
        test_supplier_cache_control,
        test_hybrid_processing,
        test_batch_synchronization
    ]
    
    for test_func in tests:
        try:
            result = test_func()
            all_results[result['experiment']] = result
            
            # Brief pause between tests
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Save comprehensive results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"config/rigorous_toggle_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to: {results_file}")
    
    # Generate evidence summary
    print("\n📋 EVIDENCE SUMMARY")
    print("=" * 40)
    
    for experiment_name, result in all_results.items():
        print(f"\n🧪 {experiment_name.upper()}:")
        
        # File evidence
        for file_type, evidence in result.get('file_evidence', {}).items():
            if evidence.get('exists'):
                print(f"  📁 {file_type}: {evidence['size']} bytes, {evidence['modified']}")
                if 'content_analysis' in evidence:
                    for key, value in evidence['content_analysis'].items():
                        print(f"    - {key}: {value}")
            else:
                print(f"  ❌ {file_type}: Not found")
        
        # Configuration verification
        config_changes = result.get('config_changes', {})
        print(f"  🔧 Applied {len(config_changes)} configuration changes")
    
    return all_results

if __name__ == "__main__":
    results = main()