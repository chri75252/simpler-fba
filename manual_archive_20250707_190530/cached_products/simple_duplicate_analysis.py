#!/usr/bin/env python3
"""
Simple Product Duplicate Analysis Tool
Analyzes cached products for duplicates and category overlap patterns
"""

import json
import sys
from collections import defaultdict, Counter
from urllib.parse import urlparse
import re

def load_cached_products(file_path):
    """Load and parse the cached products JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cached products: {e}")
        return []

def extract_category_from_url(url):
    """Extract category path from URL"""
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p and not p.endswith('.html')]
        return '/'.join(path_parts) if path_parts else 'unknown'
    except:
        return 'unknown'

def analyze_duplicates_simple(products):
    """Simple duplicate analysis"""
    
    print("🔍 PRODUCT DUPLICATE ANALYSIS")
    print("=" * 60)
    print(f"Total products loaded: {len(products):,}")
    print()
    
    # Track duplicates by different criteria
    ean_groups = defaultdict(list)
    url_groups = defaultdict(list)
    title_groups = defaultdict(list)
    category_products = defaultdict(list)
    
    # Process each product
    for i, product in enumerate(products):
        # EAN duplicates
        if product.get('ean') and product['ean'].strip():
            ean_groups[product['ean'].strip()].append(product)
        
        # URL duplicates
        if product.get('url') and product['url'].strip():
            url_groups[product['url'].strip()].append(product)
        
        # Title duplicates (normalized)
        if product.get('title') and product['title'].strip():
            normalized_title = product['title'].lower().strip()
            title_groups[normalized_title].append(product)
        
        # Category grouping
        if product.get('source_category_url'):
            category = extract_category_from_url(product['source_category_url'])
            category_products[category].append(product)
    
    # Analyze EAN duplicates
    print("📊 EAN DUPLICATE ANALYSIS")
    print("-" * 30)
    ean_duplicates = {ean: products for ean, products in ean_groups.items() if len(products) > 1}
    
    total_ean_duplicates = 0
    cross_category_duplicates = 0
    
    if ean_duplicates:
        print(f"Unique EANs with duplicates: {len(ean_duplicates):,}")
        total_ean_duplicates = sum(len(prods) - 1 for prods in ean_duplicates.values())
        print(f"Total duplicate instances: {total_ean_duplicates:,}")
        
        # Show top duplicate EANs
        top_ean_dupes = sorted(ean_duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        print(f"\nTop {min(10, len(top_ean_dupes))} most duplicated EANs:")
        
        for ean, products in top_ean_dupes:
            categories = set()
            for prod in products:
                if prod.get('source_category_url'):
                    category = extract_category_from_url(prod['source_category_url'])
                    categories.add(category)
            
            print(f"  EAN: {ean}")
            print(f"    Instances: {len(products)}")
            print(f"    Title: {products[0].get('title', 'N/A')[:60]}...")
            print(f"    Different categories: {len(categories)}")
            
            if len(categories) > 1:
                cross_category_duplicates += 1
                print(f"    ⚠️  CROSS-CATEGORY DUPLICATE!")
                for cat in sorted(categories):
                    print(f"      - {cat}")
            print()
    else:
        print("✅ No EAN duplicates found")
    
    print()
    
    # Analyze URL duplicates
    print("🔗 URL DUPLICATE ANALYSIS")
    print("-" * 30)
    url_duplicates = {url: products for url, products in url_groups.items() if len(products) > 1}
    
    total_url_duplicates = 0
    
    if url_duplicates:
        total_url_duplicates = sum(len(prods) - 1 for prods in url_duplicates.values())
        print(f"Unique URLs with duplicates: {len(url_duplicates):,}")
        print(f"Total duplicate instances: {total_url_duplicates:,}")
        
        # Show examples
        for i, (url, products) in enumerate(list(url_duplicates.items())[:10]):
            categories = set()
            for prod in products:
                if prod.get('source_category_url'):
                    category = extract_category_from_url(prod['source_category_url'])
                    categories.add(category)
            
            print(f"\nDuplicate URL #{i+1}:")
            print(f"  URL: {url[:80]}...")
            print(f"  Instances: {len(products)}")
            print(f"  Different source categories: {len(categories)}")
            
            if len(categories) > 1:
                print("  ⚠️  SAME PRODUCT FROM MULTIPLE CATEGORIES!")
                for cat in sorted(categories):
                    print(f"    - {cat}")
    else:
        print("✅ No URL duplicates found")
    
    print()
    
    # Analyze title duplicates
    print("📝 TITLE DUPLICATE ANALYSIS")
    print("-" * 35)
    title_duplicates = {title: products for title, products in title_groups.items() if len(products) > 1}
    
    total_title_duplicates = 0
    
    if title_duplicates:
        total_title_duplicates = sum(len(prods) - 1 for prods in title_duplicates.values())
        print(f"Unique titles with duplicates: {len(title_duplicates):,}")
        print(f"Total duplicate instances: {total_title_duplicates:,}")
        
        # Show top few examples
        top_title_dupes = sorted(title_duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        
        for i, (title, products) in enumerate(top_title_dupes):
            categories = set()
            eans = set()
            for prod in products:
                if prod.get('source_category_url'):
                    category = extract_category_from_url(prod['source_category_url'])
                    categories.add(category)
                if prod.get('ean'):
                    eans.add(prod['ean'])
            
            print(f"\nDuplicate Title #{i+1}:")
            print(f"  Title: {title[:60]}...")
            print(f"  Instances: {len(products)}")
            print(f"  Different EANs: {len(eans)}")
            print(f"  Different categories: {len(categories)}")
            
            if len(eans) == 1 and len(categories) > 1:
                print("  ⚠️  SAME PRODUCT (SAME EAN) IN MULTIPLE CATEGORIES!")
    else:
        print("✅ No title duplicates found")
    
    print()
    
    # Category analysis
    print("📁 CATEGORY ANALYSIS")
    print("-" * 25)
    print(f"Total unique categories: {len(category_products):,}")
    
    # Show category distribution
    category_counts = [(cat, len(prods)) for cat, prods in category_products.items()]
    category_counts.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nTop {min(15, len(category_counts))} categories by product count:")
    for category, count in category_counts[:15]:
        print(f"  {category}: {count:,} products")
    
    # Look for potential parent/child relationships
    print(f"\nAnalyzing category hierarchy patterns...")
    potential_overlaps = []
    
    for i, (cat1, prods1) in enumerate(category_products.items()):
        for j, (cat2, prods2) in enumerate(category_products.items()):
            if i >= j:
                continue
            
            # Check if one category is a subset of another
            if cat1 in cat2 or cat2 in cat1:
                # Check for actual product overlap
                eans1 = set(p.get('ean') for p in prods1 if p.get('ean'))
                eans2 = set(p.get('ean') for p in prods2 if p.get('ean'))
                overlap = eans1 & eans2
                
                if overlap:
                    potential_overlaps.append({
                        'cat1': cat1,
                        'cat2': cat2,
                        'cat1_products': len(prods1),
                        'cat2_products': len(prods2),
                        'overlapping_products': len(overlap),
                        'overlap_percentage': (len(overlap) / min(len(eans1), len(eans2))) * 100 if eans1 and eans2 else 0
                    })
    
    if potential_overlaps:
        print(f"\n🔗 POTENTIAL CATEGORY OVERLAPS FOUND: {len(potential_overlaps)}")
        potential_overlaps.sort(key=lambda x: x['overlapping_products'], reverse=True)
        
        for i, overlap in enumerate(potential_overlaps[:10]):
            print(f"\nOverlap #{i+1}:")
            print(f"  Category 1: {overlap['cat1']} ({overlap['cat1_products']} products)")
            print(f"  Category 2: {overlap['cat2']} ({overlap['cat2_products']} products)")
            print(f"  Overlapping products: {overlap['overlapping_products']} ({overlap['overlap_percentage']:.1f}%)")
    else:
        print("✅ No significant category overlaps detected")
    
    # Calculate overall statistics
    print("\n📈 OVERALL DUPLICATION STATISTICS")
    print("-" * 40)
    
    total_products = len(products)
    unique_products = total_products - total_ean_duplicates - total_url_duplicates
    
    # More accurate duplication calculation
    all_duplicates = set()
    for ean, prods in ean_duplicates.items():
        for i in range(1, len(prods)):  # Skip first instance
            all_duplicates.add(id(prods[i]))
    
    for url, prods in url_duplicates.items():
        for i in range(1, len(prods)):  # Skip first instance
            all_duplicates.add(id(prods[i]))
    
    estimated_duplicates = len(all_duplicates)
    duplication_rate = (estimated_duplicates / total_products) * 100 if total_products > 0 else 0
    
    print(f"Total products: {total_products:,}")
    print(f"EAN duplicates: {total_ean_duplicates:,}")
    print(f"URL duplicates: {total_url_duplicates:,}")
    print(f"Cross-category duplicates: {cross_category_duplicates:,}")
    print(f"Estimated unique products: {total_products - estimated_duplicates:,}")
    print(f"Overall duplication rate: {duplication_rate:.2f}%")
    
    # Generate summary report
    print("\n" + "="*60)
    print("📋 EXECUTIVE SUMMARY")
    print("="*60)
    
    if duplication_rate > 10:
        print("🚨 HIGH DUPLICATION DETECTED!")
        severity = "HIGH"
    elif duplication_rate > 5:
        print("⚠️  MODERATE DUPLICATION DETECTED")
        severity = "MODERATE"
    else:
        print("✅ LOW DUPLICATION LEVELS")
        severity = "LOW"
    
    print(f"\nKey Findings:")
    print(f"- Total products analyzed: {total_products:,}")
    print(f"- Duplication severity: {severity}")
    print(f"- Overall duplication rate: {duplication_rate:.2f}%")
    print(f"- Cross-category duplicates: {cross_category_duplicates:,}")
    print(f"- Category overlaps detected: {len(potential_overlaps):,}")
    
    print(f"\nMost Common Duplication Patterns:")
    if cross_category_duplicates > 0:
        print("- Products appearing in multiple categories (cross-category duplication)")
    if potential_overlaps:
        print("- Parent/child category hierarchies causing overlap")
    if total_ean_duplicates > total_url_duplicates:
        print("- Same EAN appearing multiple times")
    else:
        print("- Same URL appearing multiple times")
    
    recommendations = []
    if duplication_rate > 5:
        recommendations.append("Implement EAN-based deduplication before caching")
        recommendations.append("Review category scraping logic for overlap")
    if cross_category_duplicates > 5:
        recommendations.append("Add cross-category duplicate detection")
    if len(potential_overlaps) > 3:
        recommendations.append("Implement category hierarchy-aware scraping")
        recommendations.append("Prioritize broader categories over specific subcategories")
    
    if recommendations:
        print(f"\nRecommendations:")
        for rec in recommendations:
            print(f"- {rec}")
    else:
        print(f"\n✅ Current duplication levels are acceptable")
    
    return {
        'total_products': total_products,
        'ean_duplicates': total_ean_duplicates,
        'url_duplicates': total_url_duplicates,
        'cross_category_duplicates': cross_category_duplicates,
        'duplication_rate': duplication_rate,
        'categories': len(category_products),
        'category_overlaps': len(potential_overlaps),
        'severity': severity
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 simple_duplicate_analysis.py <cached_products.json>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    products = load_cached_products(file_path)
    
    if not products:
        print("No products loaded. Exiting.")
        sys.exit(1)
    
    results = analyze_duplicates_simple(products)
    
    # Save results to JSON file
    output_file = file_path.replace('.json', '_duplicate_analysis_results.json')
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\n📁 Analysis results saved to: {output_file}")
    except Exception as e:
        print(f"Warning: Could not save results file: {e}")

if __name__ == "__main__":
    main()