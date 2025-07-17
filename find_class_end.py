#!/usr/bin/env python3
"""Find where the PassiveExtractionWorkflow class legitimately ends."""

import re

def find_class_end():
    with open('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py', 'r') as f:
        lines = f.readlines()
    
    in_class = False
    class_start_line = None
    method_counts = {}
    
    for line_num, line in enumerate(lines, 1):
        # Track class start
        if line.strip().startswith('class PassiveExtractionWorkflow'):
            in_class = True
            class_start_line = line_num
            print(f"Class starts at line {line_num}")
            continue
            
        if in_class:
            # Track method definitions
            if re.match(r'    def ([a-zA-Z_][a-zA-Z0-9_]*)', line):
                method_name = re.match(r'    def ([a-zA-Z_][a-zA-Z0-9_]*)', line).group(1)
                method_counts[method_name] = method_counts.get(method_name, 0) + 1
                
                # If we see a duplicate method, this might be where duplication starts
                if method_counts[method_name] > 1:
                    print(f"DUPLICATE METHOD: {method_name} seen {method_counts[method_name]} times at line {line_num}")
                    if method_counts[method_name] == 2:
                        print(f"  -> First duplication starts around line {line_num}")
                        # Print the previous 10 lines for context
                        print("  Context (previous 10 lines):")
                        for i in range(max(0, line_num-11), line_num-1):
                            print(f"    {i+1}: {lines[i].rstrip()}")
                        print(f"    {line_num}: {line.rstrip()} <-- DUPLICATE STARTS HERE")
                        return line_num - 5  # Approximate where legitimate class ends
            
            # Check for module-level code (not indented) that would end the class
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                print(f"Class potentially ends at line {line_num-1} due to module-level code: {line.strip()}")
                return line_num - 1
    
    print("No clear end found")
    return len(lines)

if __name__ == "__main__":
    end_line = find_class_end()
    print(f"Suggested truncation point: line {end_line}")