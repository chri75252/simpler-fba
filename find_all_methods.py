#!/usr/bin/env python3
"""Find all method definitions to understand the structure."""

def find_all_methods():
    with open('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py', 'r') as f:
        lines = f.readlines()
    
    methods = []
    in_class = False
    
    for line_num, line in enumerate(lines, 1):
        if line.strip().startswith('class PassiveExtractionWorkflow'):
            in_class = True
            print(f"Class starts at line {line_num}")
            continue
            
        if in_class and line.startswith('    def '):
            method_name = line.strip().split('(')[0].replace('def ', '')
            methods.append((method_name, line_num))
            print(f"Line {line_num}: {method_name}")
            
        # Look for potential class end
        if in_class and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            print(f"Potential class end at line {line_num}: {line.strip()}")
            break
    
    print(f"\nTotal methods found: {len(methods)}")
    
    # Look for duplicates
    method_names = [m[0] for m in methods]
    duplicates = {}
    for name in method_names:
        count = method_names.count(name)
        if count > 1:
            duplicates[name] = count
    
    if duplicates:
        print(f"\nDuplicate methods found:")
        for name, count in duplicates.items():
            print(f"  {name}: appears {count} times")
            lines_with_method = [line_num for method_name, line_num in methods if method_name == name]
            print(f"    At lines: {lines_with_method}")
            if len(lines_with_method) >= 2:
                print(f"    First duplicate at line {lines_with_method[1]} - truncate before this")
    
    return methods

if __name__ == "__main__":
    find_all_methods()