#!/usr/bin/env python3

"""
SIGNAL HANDLER ADDITION FOR MAIN SCRIPT
========================================

Add this code to the top of passive_extraction_workflow_latest.py
after the imports section but before the class definition.

This adds minimal signal handling to enable external backup triggering
without affecting normal operation.
"""

import signal
import os
from datetime import datetime

# ==========================================
# ADD THIS CODE TO THE MAIN SCRIPT
# ==========================================

def setup_signal_handlers(workflow_instance):
    """
    Setup signal handlers for external backup triggering
    Add this function to the main script
    """
    
    def handle_backup_signal(signum, frame):
        """Handle SIGUSR1 signal to trigger backup saves"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            print(f"\n🔔 [{timestamp}] External backup signal received")
            
            # Create backup files with timestamp
            if hasattr(workflow_instance, 'linking_map') and workflow_instance.linking_map:
                backup_linking_path = f"/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map_signal_backup_{timestamp}.json"
                
                import json
                with open(backup_linking_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow_instance.linking_map, f, indent=2, ensure_ascii=False)
                
                print(f"✅ [{timestamp}] Linking map backed up: {len(workflow_instance.linking_map)} entries")
            
            # Backup cached products if available
            if hasattr(workflow_instance, 'supplier_products') and workflow_instance.supplier_products:
                backup_cache_path = f"/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/cached_products/cached_products_signal_backup_{timestamp}.json"
                
                with open(backup_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow_instance.supplier_products, f, indent=2, ensure_ascii=False)
                
                print(f"✅ [{timestamp}] Cached products backed up: {len(workflow_instance.supplier_products)} entries")
            
            print(f"📁 [{timestamp}] Signal-triggered backup complete")
            
        except Exception as e:
            print(f"❌ Error in signal handler: {e}")
    
    # Register the signal handler
    signal.signal(signal.SIGUSR1, handle_backup_signal)
    print("🔧 Signal handler registered (SIGUSR1 = external backup trigger)")

# ==========================================
# USAGE INSTRUCTIONS
# ==========================================

"""
TO ADD TO MAIN SCRIPT:

1. Add the import at the top:
   import signal
   from datetime import datetime

2. Add the setup_signal_handlers function

3. Call it in the __init__ method of your main class:
   setup_signal_handlers(self)

That's it! The script will now respond to SIGUSR1 signals
and create timestamped backups without interrupting normal operation.
"""

# ==========================================
# PATCH CREATOR SCRIPT
# ==========================================

def create_patch_file():
    """Create a patch that can be safely applied"""
    
    patch_content = '''
# Add these lines after the imports in passive_extraction_workflow_latest.py:

import signal
from datetime import datetime

# Add this function before the class definition:

def setup_signal_handlers(workflow_instance):
    """Setup signal handlers for external backup triggering"""
    
    def handle_backup_signal(signum, frame):
        """Handle SIGUSR1 signal to trigger backup saves"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            print(f"\\n🔔 [{timestamp}] External backup signal received")
            
            # Create backup files with timestamp
            if hasattr(workflow_instance, 'linking_map') and workflow_instance.linking_map:
                backup_linking_path = f"/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map_signal_backup_{timestamp}.json"
                
                import json
                with open(backup_linking_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow_instance.linking_map, f, indent=2, ensure_ascii=False)
                
                print(f"✅ [{timestamp}] Linking map backed up: {len(workflow_instance.linking_map)} entries")
            
            # Also trigger the existing save function if available
            if hasattr(workflow_instance, '_save_linking_map'):
                workflow_instance._save_linking_map()
                print(f"✅ [{timestamp}] Main linking map updated")
                
            print(f"📁 [{timestamp}] Signal-triggered backup complete")
            
        except Exception as e:
            print(f"❌ Error in signal handler: {e}")
    
    # Register the signal handler
    signal.signal(signal.SIGUSR1, handle_backup_signal)
    print("🔧 Signal handler registered (SIGUSR1 = external backup trigger)")

# Add this line in the __init__ method of your main workflow class:
# setup_signal_handlers(self)
'''
    
    with open('/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/cached_products/SIGNAL_PATCH_INSTRUCTIONS.txt', 'w') as f:
        f.write(patch_content)
    
    print("📄 Patch instructions created: SIGNAL_PATCH_INSTRUCTIONS.txt")

if __name__ == "__main__":
    create_patch_file()
    print("\n✅ Signal handler code ready!")
    print("\nTo use:")
    print("1. Add the signal handler to main script (see SIGNAL_PATCH_INSTRUCTIONS.txt)")
    print("2. Run continuous_backup_monitor.py to monitor file changes")
    print("3. Run signal_based_backup_trigger.py to trigger periodic saves")