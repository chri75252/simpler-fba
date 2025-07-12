#!/usr/bin/env python3
"""
Fix Tool Abstractions - Add missing _run methods to all LangGraph tools
======================================================================

This script adds the required synchronous _run method to all tool classes
to fix the abstract method implementation requirements.
"""

import os
import re
from pathlib import Path

def add_sync_run_method(file_path):
    """Add synchronous _run method to all BaseTool classes in a file"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find class definitions that inherit from BaseTool
    class_pattern = r'(class \w+Tool\(BaseTool\):.*?args_schema: Type\[BaseModel\] = \w+)'
    
    # Pattern for the method to add
    sync_method_template = '''
    def _run(self, *args, **kwargs) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(*args, **kwargs))'''
    
    # Find all class definitions and add sync method if not present
    modified = False
    
    # Look for classes that have _arun but not _run
    matches = re.finditer(r'(class \w+Tool\(BaseTool\):.*?)(\n    async def _arun)', content, re.DOTALL)
    
    for match in matches:
        class_content = match.group(1)
        # Check if _run method already exists
        if 'def _run(' not in class_content:
            # Insert the sync method before _arun
            replacement = match.group(1) + sync_method_template + match.group(2)
            content = content.replace(match.group(0), replacement)
            modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated {file_path}")
        return True
    else:
        print(f"⏭️  No changes needed for {file_path}")
        return False

def main():
    """Fix all tool files in the langraph_integration directory"""
    
    integration_dir = Path(__file__).parent / "langraph_integration"
    tool_files = [
        "critical_system_tools.py",
        "medium_priority_tools.py", 
        "utility_tools.py"
    ]
    
    total_updated = 0
    
    for file_name in tool_files:
        file_path = integration_dir / file_name
        if file_path.exists():
            if add_sync_run_method(file_path):
                total_updated += 1
        else:
            print(f"❌ File not found: {file_path}")
    
    print(f"\n🎉 Updated {total_updated} files with sync _run methods")
    print("✅ All tool abstractions should now be properly implemented")

if __name__ == "__main__":
    main()