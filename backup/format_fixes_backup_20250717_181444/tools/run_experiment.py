#!/usr/bin/env python3
"""
Run controlled toggle experiments with backup and verification
"""

import sys
import os
import json
import time
import subprocess
import signal
from datetime import datetime
from pathlib import Path

# Add tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from passive_extraction_workflow_latest import backup_experiment_files

def run_experiment(experiment_number, config_changes, max_runtime_seconds=60):
    """Run a single experiment with the specified configuration changes"""
    
    print(f"\n🚀 Starting Experiment {experiment_number}")
    print("=" * 50)
    
    # 1. Create backups if experiment number > 2
    if experiment_number > 2:
        backup_results = backup_experiment_files(experiment_number)
        print(f"📦 Created {len(backup_results)} backup files with .bak{experiment_number} suffix")
        for file_type, path in backup_results.items():
            if path:
                print(f"   - {file_type}: {path}")
    
    # 2. Apply configuration changes
    config_path = "config/system_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"🔧 Applying configuration changes:")
    for key_path, new_value in config_changes.items():
        keys = key_path.split('.')
        current = config
        
        # Navigate to the correct nested location
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        old_value = current.get(keys[-1], "NOT_SET")
        current[keys[-1]] = new_value
        print(f"   - {key_path}: {old_value} → {new_value}")
    
    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # 3. Clear processing state to start fresh
    state_path = "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json"
    if os.path.exists(state_path):
        os.remove(state_path)
        print(f"🗑️  Cleared processing state for fresh start")
    
    # 4. Run the experiment
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/debug/experiment_{experiment_number}_{timestamp}.log"
    
    print(f"▶️  Starting workflow (max runtime: {max_runtime_seconds}s)")
    print(f"📝 Log file: {log_file}")
    
    # Start the process
    process = subprocess.Popen(
        [sys.executable, "run_custom_poundwholesale.py"],
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid
    )
    
    # Wait for specified time
    try:
        process.wait(timeout=max_runtime_seconds)
        print(f"✅ Process completed normally")
    except subprocess.TimeoutExpired:
        print(f"⏰ Process timed out after {max_runtime_seconds}s - terminating")
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait()
    
    # 5. Verify outputs
    print(f"\n📊 Verifying Experiment {experiment_number} Results:")
    
    # Check mandatory outputs
    mandatory_outputs = {
        "supplier_cache": "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json",
        "processing_state": "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
        "log_file": log_file
    }
    
    results = {}
    for output_name, path in mandatory_outputs.items():
        if os.path.exists(path):
            stat = os.stat(path)
            results[output_name] = {
                "exists": True,
                "size": stat.st_size,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            print(f"✅ {output_name}: {path} ({stat.st_size} bytes)")
        else:
            results[output_name] = {"exists": False}
            print(f"❌ {output_name}: {path} NOT FOUND")
    
    # Check specific content
    if results["supplier_cache"]["exists"]:
        with open(mandatory_outputs["supplier_cache"], 'r') as f:
            cache_data = json.load(f)
        print(f"📦 Supplier cache: {len(cache_data)} products")
        
        if cache_data:
            # Check price range
            prices = [float(p.get('price', '0').replace('£', '')) for p in cache_data if p.get('price')]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                print(f"💰 Price range: £{min_price:.2f} - £{max_price:.2f}")
    
    if results["processing_state"]["exists"]:
        with open(mandatory_outputs["processing_state"], 'r') as f:
            state_data = json.load(f)
        print(f"📈 Processing state: {state_data.get('products_extracted_total', 0)} products extracted")
        print(f"📊 Categories completed: {len(state_data.get('supplier_extraction_progress', {}).get('categories_completed', []))}")
    
    return results

def main():
    """Run the sequential toggle experiments"""
    
    experiments = [
        {
            "number": 1,
            "name": "Processing Limits Test",
            "config_changes": {
                "processing_limits.max_products_per_category": 5,
                "processing_limits.max_products_per_run": 15,
                "system.max_products_per_cycle": 4
            },
            "runtime": 90
        },
        {
            "number": 2,
            "name": "System Configuration Test",
            "config_changes": {
                "system.max_products": 20,
                "system.max_analyzed_products": 15,
                "system.supplier_extraction_batch_size": 2
            },
            "runtime": 90
        },
        {
            "number": 3,
            "name": "Supplier Cache Control Test",
            "config_changes": {
                "supplier_cache_control.update_frequency_products": 5,
                "supplier_cache_control.force_update_on_interruption": False
            },
            "runtime": 90
        }
    ]
    
    print("🧪 Sequential Toggle Effect Experiments")
    print("=" * 60)
    
    all_results = {}
    
    for experiment in experiments:
        try:
            results = run_experiment(
                experiment["number"],
                experiment["config_changes"],
                experiment["runtime"]
            )
            all_results[experiment["number"]] = {
                "name": experiment["name"],
                "config_changes": experiment["config_changes"],
                "results": results,
                "status": "completed"
            }
            
            # Brief pause between experiments
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Experiment {experiment['number']} failed: {e}")
            all_results[experiment["number"]] = {
                "name": experiment["name"],
                "error": str(e),
                "status": "failed"
            }
    
    # Generate summary report
    print("\n📋 Final Experiment Summary")
    print("=" * 60)
    
    for exp_num, result in all_results.items():
        print(f"\n🧪 Experiment {exp_num}: {result['name']}")
        if result["status"] == "completed":
            print(f"   Status: ✅ COMPLETED")
            if "results" in result:
                for output_name, output_data in result["results"].items():
                    if output_data["exists"]:
                        print(f"   ✅ {output_name}: {output_data['size']} bytes")
                    else:
                        print(f"   ❌ {output_name}: NOT FOUND")
        else:
            print(f"   Status: ❌ FAILED - {result.get('error', 'Unknown error')}")
    
    # Save detailed results
    results_file = f"config/experiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📊 Detailed results saved to: {results_file}")
    
    # Return success if all experiments completed
    completed_count = sum(1 for r in all_results.values() if r["status"] == "completed")
    total_count = len(all_results)
    
    if completed_count == total_count:
        print(f"\n🎉 All {total_count} experiments completed successfully!")
        return True
    else:
        print(f"\n⚠️  {completed_count}/{total_count} experiments completed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)