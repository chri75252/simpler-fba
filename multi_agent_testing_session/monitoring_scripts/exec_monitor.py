#!/usr/bin/env python3
import time
import glob
import re
from pathlib import Path
from datetime import datetime

print("🚀 EXEC-AGENT MONITOR STARTED")
print("=" * 50)
print("📍 Monitoring: ../AFBAS32-test/logs/debug/run_custom_poundwholesale_*.log")
print("🎯 Focus: Main workflow execution, product processing, authentication")
print("=" * 50)

base_dir = Path.cwd()
last_position = 0
metrics = {"products": 0, "categories": 0, "errors": 0, "successes": 0}

while True:
    try:
        # Find latest log file
        pattern = str(base_dir / "../AFBAS32-test/logs/debug/run_custom_poundwholesale_*.log")
        files = glob.glob(pattern)
        
        if not files:
            pattern = str(base_dir / "logs/debug/run_custom_poundwholesale_*.log")
            files = glob.glob(pattern)
        
        if files:
            latest_file = max(files, key=os.path.getmtime)
            
            if Path(latest_file).exists():
                current_size = Path(latest_file).stat().st_size
                
                if current_size > last_position:
                    with open(latest_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        last_position = f.tell()
                    
                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        # Critical patterns
                        if re.search(r'ERROR|error|Error', line):
                            metrics["errors"] += 1
                            print(f"🚨 [{timestamp}] ERROR: {line}")
                        elif re.search(r'SUCCESS|success|Successfully|✅', line):
                            metrics["successes"] += 1
                            print(f"✅ [{timestamp}] SUCCESS: {line}")
                        elif re.search(r'Processing category|Found \d+ products', line):
                            print(f"📊 [{timestamp}] PROGRESS: {line}")
                        elif re.search(r'Product \d+ of \d+|--- Processing supplier product', line):
                            if 'Processing supplier product' in line:
                                metrics["products"] += 1
                            print(f"🔄 [{timestamp}] PRODUCT: {line}")
                        elif re.search(r'authentication|login|Login', line):
                            print(f"🔐 [{timestamp}] AUTH: {line}")
                        elif re.search(r'browser|Browser|playwright', line):
                            print(f"🌐 [{timestamp}] BROWSER: {line}")
                        elif re.search(r'WARNING|warning|Warning', line):
                            print(f"⚠️  [{timestamp}] WARNING: {line}")
                        
                        # Show every 10th line for context
                        if metrics["products"] % 10 == 0 and metrics["products"] > 0:
                            print(f"📈 [{timestamp}] METRICS: Products: {metrics['products']}, Errors: {metrics['errors']}, Successes: {metrics['successes']}")
        
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Exec monitor stopped")
        break
    except Exception as e:
        print(f"❌ Monitor error: {e}")
        time.sleep(5)
