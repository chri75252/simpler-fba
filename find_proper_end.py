#!/usr/bin/env python3
"""Find the proper end of the legitimate class content."""

def find_proper_end():
    with open('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py', 'r') as f:
        lines = f.readlines()
    
    # Find the legitimate methods in order
    legitimate_methods = [
        "_save_final_report",
        "_combine_data", 
        "_overlap_score",
        "_sanitize_filename",
        "_validate_product_match",
        "_is_product_meeting_criteria",
        "_apply_batch_synchronization"
    ]
    
    method_first_occurrence = {}
    
    for line_num, line in enumerate(lines, 1):
        for method in legitimate_methods:
            if f"def {method}(" in line and method not in method_first_occurrence:
                method_first_occurrence[method] = line_num
                print(f"First occurrence of {method}: line {line_num}")
    
    # Find the end of the last legitimate method
    last_method_line = max(method_first_occurrence.values()) if method_first_occurrence else 0
    print(f"\nLast method starts at line: {last_method_line}")
    
    # Find the end of that method by looking for the next method definition or class end
    for line_num in range(last_method_line + 1, len(lines)):
        line = lines[line_num]
        # Look for next method definition (same indentation) or class end
        if (line.startswith('    def ') or 
            (line.strip() and not line.startswith(' '))):
            print(f"Method ends around line: {line_num - 1}")
            return line_num - 1
    
    return len(lines)

if __name__ == "__main__":
    end_line = find_proper_end()
    print(f"Suggested truncation point: line {end_line}")