#!/usr/bin/env python3
"""
Script to fix the duplicate _extract_supplier_products method definitions
in passive_extraction_workflow_latest.py
"""

import re

def fix_duplicate_methods():
    file_path = "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Find all lines with _extract_supplier_products method definitions
    method_lines = []
    for i, line in enumerate(lines):
        if re.search(r'^\s*async def _extract_supplier_products', line):
            method_lines.append(i)
    
    print(f"Found method definitions at lines: {[l+1 for l in method_lines]}")
    
    # Keep only the first method (line 2420, 0-indexed)
    # Remove all subsequent methods by finding their end points
    
    # Find where each method ends (next method definition or end of class)
    methods_to_remove = []
    
    for i in range(1, len(method_lines)):  # Skip first method
        start_line = method_lines[i]
        
        # Find end of this method (next method or end of class/file)
        end_line = len(lines) - 1  # Default to end of file
        
        # Look for next method definition at same indentation or class end
        method_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for j in range(start_line + 1, len(lines)):
            line = lines[j]
            if line.strip() == '':
                continue
                
            current_indent = len(line) - len(line.lstrip())
            
            # If we find a line at same or less indentation that's not empty, this is the end
            if current_indent <= method_indent and line.strip():
                # Check if it's another method or class definition
                if (re.search(r'^\s*async def ', line) or 
                    re.search(r'^\s*def ', line) or
                    re.search(r'^\s*class ', line)):
                    end_line = j - 1
                    break
        
        methods_to_remove.append((start_line, end_line))
        print(f"Will remove method from line {start_line+1} to {end_line+1}")
    
    # Remove methods in reverse order to maintain line numbers
    for start_line, end_line in reversed(methods_to_remove):
        del lines[start_line:end_line+1]
        print(f"Removed lines {start_line+1} to {end_line+1}")
    
    # Write the fixed content back
    fixed_content = '\n'.join(lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"Fixed file written. Reduced from {len(content.split('\n'))} to {len(lines)} lines")

if __name__ == "__main__":
    fix_duplicate_methods()