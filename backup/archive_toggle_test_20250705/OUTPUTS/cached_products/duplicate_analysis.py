#!/usr/bin/env python3
"""
Product Duplicate Analysis Tool
Analyzes cached products for duplicates and category overlap patterns
"""

import json
import sys
from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs
import re
from datetime import datetime

def load_cached_products(file_path):
    """Load and parse the cached products JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cached products: {e}")
        return []

def extract_category_hierarchy(url):
    """Extract category hierarchy from URL"""
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p and p != 'html']
        
        # Remove file extensions
        if path_parts and path_parts[-1].endswith('.html'):
            path_parts[-1] = path_parts[-1].replace('.html', '')
        
        return path_parts
    except:
        return []

def normalize_category_url(url):
    """Normalize category URL by removing query parameters for comparison"""
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return base_url.rstrip('/')
    except:
        return url

def analyze_duplicates(products):
    """Comprehensive duplicate analysis"""
    
    print("🔍 PRODUCT DUPLICATE ANALYSIS")
    print("=" * 60)
    print(f"Total products loaded: {len(products):,}")
    print()
    
    # Track duplicates by different criteria
    ean_groups = defaultdict(list)
    url_groups = defaultdict(list)
    title_groups = defaultdict(list)
    
    # Category analysis
    category_urls = set()
    category_hierarchies = defaultdict(list)
    products_by_category = defaultdict(list)
    
    # Process each product
    for i, product in enumerate(products):
        # EAN duplicates
        if product.get('ean'):
            ean_groups[product['ean']].append((i, product))
        
        # URL duplicates
        if product.get('url'):
            url_groups[product['url']].append((i, product))
        
        # Title duplicates (normalized)
        if product.get('title'):
            normalized_title = product['title'].lower().strip()
            title_groups[normalized_title].append((i, product))
        
        # Category analysis
        if product.get('source_category_url'):
            category_url = product['source_category_url']
            category_urls.add(category_url)
            normalized_cat = normalize_category_url(category_url)
            hierarchy = extract_category_hierarchy(category_url)
            
            category_hierarchies[normalized_cat].append(hierarchy)
            products_by_category[normalized_cat].append((i, product))
    
    # Analyze EAN duplicates
    print("📊 EAN DUPLICATE ANALYSIS")
    print("-" * 30)
    ean_duplicates = {ean: products for ean, products in ean_groups.items() if len(products) > 1}
    
    if ean_duplicates:
        print(f"Products with duplicate EANs: {len(ean_duplicates):,}")
        print(f"Total duplicate instances: {sum(len(prods) for prods in ean_duplicates.values()):,}")
        
        # Show top duplicate EANs
        top_ean_dupes = sorted(ean_duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        print("\nTop 10 most duplicated EANs:")
        for ean, products in top_ean_dupes:
            categories = set()
            for _, prod in products:
                if prod.get('source_category_url'):
                    normalized_cat = normalize_category_url(prod['source_category_url'])
                    categories.add(normalized_cat)
            
            print(f"  EAN: {ean}")
            print(f"    Instances: {len(products)}")
            print(f"    Title: {products[0][1].get('title', 'N/A')[:60]}...")
            print(f"    Categories: {len(categories)}")
            if len(categories) > 1:
                print(f"    ⚠️  CROSS-CATEGORY DUPLICATE!")
                for cat in sorted(categories)[:3]:
                    hierarchy = extract_category_hierarchy(cat)
                    print(f"      - {' > '.join(hierarchy[-3:])}")
            print()
    else:
        print("✅ No EAN duplicates found")
    
    print()
    
    # Analyze URL duplicates
    print("🔗 URL DUPLICATE ANALYSIS")
    print("-" * 30)
    url_duplicates = {url: products for url, products in url_groups.items() if len(products) > 1}
    
    if url_duplicates:
        print(f"Products with duplicate URLs: {len(url_duplicates):,}")
        print(f"Total duplicate instances: {sum(len(prods) for prods in url_duplicates.values()):,}")
        
        # Show examples
        for i, (url, products) in enumerate(list(url_duplicates.items())[:5]):
            print(f"\nDuplicate URL #{i+1}:")
            print(f"  URL: {url[:80]}...")
            print(f"  Instances: {len(products)}")
            categories = set()
            for _, prod in products:
                if prod.get('source_category_url'):
                    categories.add(normalize_category_url(prod['source_category_url']))
            print(f"  Different source categories: {len(categories)}")
            if len(categories) > 1:
                print("  ⚠️  SAME PRODUCT FROM MULTIPLE CATEGORIES!")
    else:
        print("✅ No URL duplicates found")
    
    print()
    
    # Analyze category overlap patterns
    print("📁 CATEGORY OVERLAP ANALYSIS")
    print("-" * 35)
    print(f"Total unique category URLs: {len(category_urls):,}")
    print(f"Normalized category bases: {len(category_hierarchies):,}")
    
    # Find parent/child relationships
    parent_child_relationships = []
    category_list = list(category_hierarchies.keys())
    
    for i, cat1 in enumerate(category_list):
        hierarchy1 = extract_category_hierarchy(cat1)
        for j, cat2 in enumerate(category_list[i+1:], i+1):
            hierarchy2 = extract_category_hierarchy(cat2)
            
            # Check if one is parent of another
            if hierarchy1 and hierarchy2:
                if (len(hierarchy1) < len(hierarchy2) and 
                    hierarchy2[:len(hierarchy1)] == hierarchy1):
                    parent_child_relationships.append((cat1, cat2, 'parent_child'))
                elif (len(hierarchy2) < len(hierarchy1) and 
                      hierarchy1[:len(hierarchy2)] == hierarchy2):
                    parent_child_relationships.append((cat2, cat1, 'parent_child'))
    
    if parent_child_relationships:
        print(f"\n🔗 Parent/Child Category Relationships Found: {len(parent_child_relationships)}")
        
        # Group by potential overlap
        overlap_analysis = defaultdict(list)
        for parent, child, rel_type in parent_child_relationships:
            parent_products = len(products_by_category.get(parent, []))
            child_products = len(products_by_category.get(child, []))
            
            if parent_products > 0 and child_products > 0:
                overlap_analysis[parent].append({
                    'child': child,
                    'parent_products': parent_products,
                    'child_products': child_products
                })
        
        print("\nPotential Category Overlap Issues:")
        for parent, children in overlap_analysis.items():
            parent_hierarchy = extract_category_hierarchy(parent)
            print(f"\nParent: {' > '.join(parent_hierarchy[-3:])}")
            
            for child_info in children[:3]:  # Show top 3
                child_hierarchy = extract_category_hierarchy(child_info['child'])
                print(f"  └─ Child: {' > '.join(child_hierarchy[-3:])}")
                print(f"     Parent products: {child_info['parent_products']:,}")
                print(f"     Child products: {child_info['child_products']:,}")
                
                # Check for actual duplicate products
                parent_eans = set()
                child_eans = set()
                
                for _, prod in products_by_category.get(parent, []):
                    if prod.get('ean'):
                        parent_eans.add(prod['ean'])
                
                for _, prod in products_by_category.get(child_info['child'], []):
                    if prod.get('ean'):
                        child_eans.add(prod['ean'])
                
                overlap_count = len(parent_eans & child_eans)
                if overlap_count > 0:
                    overlap_rate = (overlap_count / min(len(parent_eans), len(child_eans))) * 100
                    print(f"     ⚠️  ACTUAL OVERLAP: {overlap_count} products ({overlap_rate:.1f}%)")
    
    # Calculate overall duplication statistics
    print("\n📈 OVERALL DUPLICATION STATISTICS")
    print("-" * 40)
    
    total_products = len(products)
    ean_duplicate_count = sum(len(prods) - 1 for prods in ean_duplicates.values())
    url_duplicate_count = sum(len(prods) - 1 for prods in url_duplicates.values())
    
    print(f"Total products: {total_products:,}")
    print(f"EAN duplicates: {ean_duplicate_count:,} ({(ean_duplicate_count/total_products)*100:.2f}%)")
    print(f"URL duplicates: {url_duplicate_count:,} ({(url_duplicate_count/total_products)*100:.2f}%)")
    
    # Category distribution
    print(f"\nCategory distribution:")
    category_counts = Counter()
    for _, product in enumerate(products):
        if product.get('source_category_url'):
            normalized_cat = normalize_category_url(product['source_category_url'])
            hierarchy = extract_category_hierarchy(normalized_cat)
            if hierarchy:
                category_counts[' > '.join(hierarchy[-2:])] += 1
    
    print("Top 10 categories by product count:")
    for category, count in category_counts.most_common(10):
        print(f"  {category}: {count:,} products")
    
    # Look for deduplication logic evidence
    print("\n🔍 DEDUPLICATION LOGIC ANALYSIS")
    print("-" * 40)
    
    # Check extraction timestamps for patterns
    timestamp_patterns = defaultdict(list)
    for product in products:
        if product.get('extraction_timestamp'):
            timestamp = product['extraction_timestamp'][:16]  # YYYY-MM-DDTHH:MM
            timestamp_patterns[timestamp].append(product)
    
    # Look for batch processing patterns that might indicate deduplication
    large_batches = {ts: prods for ts, prods in timestamp_patterns.items() if len(prods) > 100}
    
    if large_batches:
        print(f"Large extraction batches found: {len(large_batches)}")
        print("This might indicate batch deduplication processing")
        
        for ts, prods in list(large_batches.items())[:3]:
            categories_in_batch = set()
            for prod in prods:
                if prod.get('source_category_url'):
                    categories_in_batch.add(normalize_category_url(prod['source_category_url']))
            print(f"  {ts}: {len(prods):,} products from {len(categories_in_batch)} categories")
    
    # Generate summary report
    print("\n" + "="*60)
    print("📋 EXECUTIVE SUMMARY")
    print("="*60)
    
    duplicate_rate = ((ean_duplicate_count + url_duplicate_count) / total_products) * 100
    
    if duplicate_rate > 10:
        print("🚨 HIGH DUPLICATION DETECTED!")
    elif duplicate_rate > 5:
        print("⚠️  MODERATE DUPLICATION DETECTED")
    else:
        print("✅ LOW DUPLICATION LEVELS")
    
    print(f"\nKey Metrics:")
    print(f"- Total products analyzed: {total_products:,}")
    print(f"- Overall duplication rate: {duplicate_rate:.2f}%")
    print(f"- Unique categories: {len(category_hierarchies):,}")
    print(f"- Parent/child category pairs: {len(parent_child_relationships):,}")
    
    if ean_duplicates:
        cross_category_dupes = 0
        for ean, products in ean_duplicates.items():
            categories = set()
            for _, prod in products:
                if prod.get('source_category_url'):
                    categories.add(normalize_category_url(prod['source_category_url']))
            if len(categories) > 1:
                cross_category_dupes += 1
        
        print(f"- Cross-category duplicates: {cross_category_dupes:,}")
    
    print(f"\nRecommendations:")
    if duplicate_rate > 5:
        print("- Implement EAN-based deduplication before caching")
        print("- Review category scraping logic for overlap")
        print("- Add parent/child category detection")
    if len(parent_child_relationships) > 10:
        print("- Prioritize parent categories over child categories")
        print("- Implement category hierarchy-aware scraping")
    
    return {
        'total_products': total_products,
        'ean_duplicates': len(ean_duplicates),
        'url_duplicates': len(url_duplicates),
        'duplicate_rate': duplicate_rate,
        'categories': len(category_hierarchies),
        'parent_child_relationships': len(parent_child_relationships)
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 duplicate_analysis.py <cached_products.json>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    products = load_cached_products(file_path)
    
    if not products:
        print("No products loaded. Exiting.")
        sys.exit(1)
    
    results = analyze_duplicates(products)
    
    # Save results to JSON file
    output_file = file_path.replace('.json', '_duplicate_analysis.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Detailed analysis saved to: {output_file}")

if __name__ == "__main__":
    main()