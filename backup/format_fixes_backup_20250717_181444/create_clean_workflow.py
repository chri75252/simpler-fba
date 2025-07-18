#!/usr/bin/env python3
"""Create a clean version of the workflow file by removing duplicated content."""

def create_clean_workflow():
    # Read the corrupted file
    with open('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py', 'r') as f:
        lines = f.readlines()
    
    # Find legitimate content based on our analysis
    # The class legitimately contains these methods in order:
    legitimate_methods = [
        "__init__",
        "_initialize_output_directory", 
        "_initialize_amazon_extractor",
        "_initialize_supplier_scraper",
        "_validate_initialization",
        "run",  # This is the main method we're missing from our analysis
        "_load_linking_map",
        "_save_linking_map",
        "_classify_url",
        "_load_history",
        "_load_ai_memory", 
        "_get_default_history",
        "_save_history",
        "_record_ai_decision",
        "_is_url_previously_scraped",
        "_add_url_to_history", 
        "_record_category_performance",
        "_get_category_performance_summary",
        "_detect_parent_child_urls",
        "_filter_urls_by_subcategory_deduplication"
    ]
    
    clean_lines = []
    in_class = False
    method_count = 0
    current_method = None
    
    for line_num, line in enumerate(lines, 1):
        # Track class start
        if line.strip().startswith('class PassiveExtractionWorkflow'):
            in_class = True
            clean_lines.append(line)
            print(f"Class starts at line {line_num}")
            continue
            
        if not in_class:
            # Keep all content before the class
            clean_lines.append(line)
            continue
            
        # We're in the class now
        if line.startswith('    def '):
            method_name = line.strip().split('(')[0].replace('def ', '')
            
            # If this is a method we've already seen, stop here - corruption starts
            if current_method and method_name in legitimate_methods[:legitimate_methods.index(current_method)+1]:
                print(f"Found duplicate method {method_name} at line {line_num} - stopping here")
                break
                
            current_method = method_name
            method_count += 1
            print(f"Line {line_num}: Adding method {method_name}")
            
        # Add line to clean content
        clean_lines.append(line)
        
        # Check for potential corruption indicators
        if in_class and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            print(f"Found unindented content at line {line_num} - potential corruption: {line.strip()[:50]}")
            break
    
    print(f"Clean file will have {len(clean_lines)} lines (original: {len(lines)})")
    print(f"Removed {len(lines) - len(clean_lines)} lines of corrupted content")
    
    # Write clean file
    with open('/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest_clean.py', 'w') as f:
        f.writelines(clean_lines)
    
    print("Clean file created: passive_extraction_workflow_latest_clean.py")
    
    return len(clean_lines)

if __name__ == "__main__":
    create_clean_workflow()