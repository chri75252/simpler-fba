#!/usr/bin/env python3
"""
Configuration Usage Analyzer for Amazon FBA Agent System v3

This script analyzes system_config.json to determine:
1. Which configuration toggles are actively used in the codebase
2. Which toggles are orphaned/inactive 
3. Hardcoded values that should be configurable
4. Missing configuration references

Author: Configuration Analysis System
Date: 2025-07-04
"""

import os
import json
import re
import glob
from pathlib import Path
from typing import Dict, List, Set, Tuple

def load_system_config() -> Dict:
    """Load system_config.json"""
    config_path = Path(__file__).parent.parent / "config" / "system_config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def get_python_files() -> List[Path]:
    """Get all Python files in tools directory"""
    tools_dir = Path(__file__).parent
    return list(tools_dir.glob("*.py"))

def extract_config_keys(config_dict: Dict, prefix: str = "") -> Set[str]:
    """Recursively extract all configuration keys"""
    keys = set()
    for key, value in config_dict.items():
        if key.startswith("_"):  # Skip comments
            continue
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(extract_config_keys(value, full_key))
    return keys

def find_config_usage_in_file(file_path: Path, config_keys: Set[str]) -> Dict[str, List[str]]:
    """Find configuration usage in a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}
    
    usage = {}
    
    # Patterns to match configuration access
    patterns = [
        r'config\.get\(["\']([^"\']+)["\']',  # config.get("key")
        r'config\[["\']([^"\']+)["\']\]',     # config["key"]
        r'system_config\.get\(["\']([^"\']+)["\']',  # system_config.get("key")
        r'system_config\[["\']([^"\']+)["\']\]',     # system_config["key"]
        r'\.get\(["\']([^"\']+)["\']',        # .get("key") 
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if match not in usage:
                usage[match] = []
            # Find line number
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if match in line and ('config' in line or 'Config' in line):
                    usage[match].append(f"Line {i}: {line.strip()}")
                    break
    
    # Also check for nested key access like config.get("system", {}).get("force_ai_scraping")
    nested_pattern = r'\.get\(["\']([^"\']+)["\'][^)]*\)\.get\(["\']([^"\']+)["\']'
    nested_matches = re.findall(nested_pattern, content)
    for section, key in nested_matches:
        nested_key = f"{section}.{key}"
        if nested_key not in usage:
            usage[nested_key] = []
        # Find line number
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if section in line and key in line and 'config' in line:
                usage[nested_key].append(f"Line {i}: {line.strip()}")
                break
    
    return usage

def find_hardcoded_values(file_path: Path) -> List[Tuple[str, str]]:
    """Find hardcoded values that could be configurable"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return []
    
    hardcoded = []
    lines = content.split('\n')
    
    # Patterns for common hardcoded values
    patterns = [
        (r'timeout[=\s]*(\d+)', 'timeout value'),
        (r'sleep\((\d+\.?\d*)\)', 'sleep duration'),
        (r'max_\w+[=\s]*(\d+)', 'max limit value'),
        (r'batch_size[=\s]*(\d+)', 'batch size'),
        (r'port[=\s]*(\d+)', 'port number'),
        (r'wait_time[=\s]*(\d+)', 'wait time'),
        (r'retry[=\s]*(\d+)', 'retry count'),
    ]
    
    for i, line in enumerate(lines, 1):
        if 'config' in line.lower():  # Skip lines that already use config
            continue
        for pattern, desc in patterns:
            matches = re.findall(pattern, line.lower())
            if matches:
                hardcoded.append((f"Line {i}: {line.strip()}", f"{desc}: {matches[0]}"))
    
    return hardcoded

def analyze_configuration():
    """Main analysis function"""
    print("=== Amazon FBA Agent System v3 Configuration Analysis ===\n")
    
    # Load configuration
    config = load_system_config()
    if not config:
        print("Failed to load configuration!")
        return
    
    # Extract all configuration keys
    all_config_keys = extract_config_keys(config)
    print(f"Total configuration keys found: {len(all_config_keys)}\n")
    
    # Analyze Python files
    python_files = get_python_files()
    print(f"Analyzing {len(python_files)} Python files in tools directory...\n")
    
    active_keys = set()
    all_usage = {}
    all_hardcoded = {}
    
    for file_path in python_files:
        print(f"Analyzing {file_path.name}...")
        
        # Find config usage
        usage = find_config_usage_in_file(file_path, all_config_keys)
        if usage:
            all_usage[str(file_path)] = usage
            active_keys.update(usage.keys())
        
        # Find hardcoded values
        hardcoded = find_hardcoded_values(file_path)
        if hardcoded:
            all_hardcoded[str(file_path)] = hardcoded
    
    # Determine active vs inactive keys
    inactive_keys = all_config_keys - active_keys
    
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"Active configuration keys: {len(active_keys)}")
    print(f"Inactive/orphaned keys: {len(inactive_keys)}")
    print(f"Files with hardcoded values: {len(all_hardcoded)}")
    
    # Detailed results
    print(f"\n=== ACTIVE CONFIGURATION KEYS ===")
    for key in sorted(active_keys):
        print(f"✓ {key}")
        for file_path, usage in all_usage.items():
            if key in usage:
                print(f"  Used in {Path(file_path).name}:")
                for line_info in usage[key][:2]:  # Show first 2 occurrences
                    print(f"    {line_info}")
        print()
    
    print(f"\n=== INACTIVE/ORPHANED KEYS ===")
    for key in sorted(inactive_keys):
        print(f"✗ {key}")
    
    print(f"\n=== HARDCODED VALUES THAT COULD BE CONFIGURABLE ===")
    for file_path, hardcoded_list in all_hardcoded.items():
        print(f"\n{Path(file_path).name}:")
        for line, desc in hardcoded_list[:5]:  # Show first 5
            print(f"  {desc}")
            print(f"    {line}")
    
    return {
        'active_keys': active_keys,
        'inactive_keys': inactive_keys, 
        'usage_details': all_usage,
        'hardcoded_values': all_hardcoded
    }

if __name__ == "__main__":
    results = analyze_configuration()