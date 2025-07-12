"""
AI Category Suggester v3 - URL Clustering with Validation
========================================================

Complete replacement implementing:
- Signature: generate_categories(supplier_domain, products, url_discovery_output)
- Cluster URLs → candidate categories
- Call ConfigurableSupplierScraper.quick_count(url) for validation
- APPEND to ai_suggestion_history, increment total_ai_calls
- Save to OUTPUTS/{supplier}/{run_ts}/ai_category_cache.json
- Must match the gold-standard clearance-king schema with deep reasoning
"""

import json
import logging
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from urllib.parse import urlparse, urljoin
import re

import openai
# Removed dependency on path_manager - using authoritative path tracker

logger = logging.getLogger(__name__)


class AICategorySuggester:
    """AI-powered category suggestion with URL clustering and validation"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-4.1-mini-2025-04-14"
        self.max_tokens = 2000
        self.temperature = 0.1  # Low for consistent clustering
        
        logger.info("🧠 AI Category Suggester v3 initialized with URL clustering")
    
    async def generate_categories(
        self, 
        supplier_domain: str, 
        products: List[Dict[str, Any]], 
        url_discovery_output: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Generate categories using URL clustering and validation
        
        Args:
            supplier_domain: Supplier domain (e.g., "clearance-king.co.uk")
            products: List of product dictionaries 
            url_discovery_output: Optional discovery data with URLs
            
        Returns:
            Path to ai_category_cache.json file in run output directory
        """
        try:
            logger.info(f"🧠 Generating categories for {supplier_domain} with {len(products)} products")
            
            # Get supplier-specific directory per authoritative path tracker
            supplier_cache_dir = Path("OUTPUTS") / "FBA_ANALYSIS" / "ai_category_cache"
            supplier_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file_path = supplier_cache_dir / f"{supplier_domain}_ai_categories.json"
            
            # Load existing cache or create new one
            cache_data = self._load_or_create_cache(supplier_domain, cache_file_path)
            
            # Extract URLs from products and discovery data
            candidate_urls = self._extract_candidate_urls(products, url_discovery_output, supplier_domain)
            
            if not candidate_urls:
                logger.warning("No candidate URLs found for clustering")
                return await self._save_empty_suggestion(cache_data, cache_file_path, len(products))
            
            # Cluster URLs into categories
            clustered_categories = await self._cluster_urls_to_categories(candidate_urls, supplier_domain)
            
            # Validate categories with quick_count
            validated_categories = await self._validate_categories_with_scraper(
                clustered_categories, supplier_domain
            )
            
            # Generate AI suggestion with reasoning
            ai_suggestion = await self._generate_ai_suggestion_with_reasoning(
                validated_categories, len(products), len(candidate_urls)
            )
            
            # Update cache with new suggestion
            updated_cache = self._update_cache_with_suggestion(
                cache_data, ai_suggestion, len(products)
            )
            
            # Save updated cache
            await self._save_cache(updated_cache, cache_file_path)
            
            logger.info(f"✅ Generated categories saved to {cache_file_path}")
            return cache_file_path
            
        except Exception as e:
            logger.error(f"❌ Category generation failed for {supplier_domain}: {e}")
            # Still try to save empty suggestion to maintain schema
            try:
                supplier_cache_dir = Path("OUTPUTS") / "FBA_ANALYSIS" / "ai_category_cache"
                supplier_cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file_path = supplier_cache_dir / f"{supplier_domain}_ai_categories.json"
                cache_data = self._load_or_create_cache(supplier_domain, cache_file_path)
                return await self._save_empty_suggestion(cache_data, cache_file_path, len(products))
            except:
                raise e
    
    def _load_or_create_cache(self, supplier_domain: str, cache_file_path: Path) -> Dict[str, Any]:
        """Load existing cache or create new cache structure"""
        try:
            if cache_file_path.exists():
                with open(cache_file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                logger.info(f"📁 Loaded existing cache with {cache_data.get('total_ai_calls', 0)} previous calls")
                return cache_data
        except Exception as e:
            logger.warning(f"Failed to load existing cache: {e}")
        
        # Create new cache with clearance-king schema
        return {
            "supplier": supplier_domain,
            "url": f"https://www.{supplier_domain.replace('-', '.')}",
            "created": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_ai_calls": 0,
            "ai_suggestion_history": []
        }
    
    def _extract_candidate_urls(
        self, 
        products: List[Dict[str, Any]], 
        url_discovery_output: Optional[Dict[str, Any]], 
        supplier_domain: str
    ) -> List[str]:
        """Extract and normalize candidate URLs from products and discovery data"""
        candidate_urls = set()
        base_url = f"https://www.{supplier_domain.replace('-', '.')}"
        
        # Extract from products
        for product in products:
            if isinstance(product, dict):
                # Product URL
                if product.get('url'):
                    candidate_urls.add(product['url'])
                
                # Source category URL
                if product.get('source_category_url'):
                    candidate_urls.add(product['source_category_url'])
        
        # Extract from URL discovery output
        if url_discovery_output and isinstance(url_discovery_output, dict):
            # Navigation URLs
            if 'navigation_urls' in url_discovery_output:
                for nav_url in url_discovery_output['navigation_urls']:
                    if isinstance(nav_url, str):
                        candidate_urls.add(nav_url)
                    elif isinstance(nav_url, dict) and nav_url.get('url'):
                        candidate_urls.add(nav_url['url'])
            
            # Category URLs
            if 'category_urls' in url_discovery_output:
                for cat_url in url_discovery_output['category_urls']:
                    if isinstance(cat_url, str):
                        candidate_urls.add(cat_url)
                    elif isinstance(cat_url, dict) and cat_url.get('url'):
                        candidate_urls.add(cat_url['url'])
        
        # Normalize URLs
        normalized_urls = []
        for url in candidate_urls:
            try:
                # Make relative URLs absolute
                if url.startswith('/'):
                    url = urljoin(base_url, url)
                
                # Filter to domain URLs only
                parsed = urlparse(url)
                if supplier_domain.replace('-', '.') in parsed.netloc:
                    # Remove query parameters and fragments for clustering
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    normalized_urls.append(clean_url)
                    
            except Exception as e:
                logger.debug(f"Failed to normalize URL {url}: {e}")
        
        logger.info(f"📊 Extracted {len(normalized_urls)} candidate URLs from {len(products)} products")
        return list(set(normalized_urls))  # Remove duplicates
    
    async def _cluster_urls_to_categories(
        self, 
        candidate_urls: List[str], 
        supplier_domain: str
    ) -> List[Dict[str, Any]]:
        """Cluster URLs into logical categories using AI"""
        try:
            if len(candidate_urls) > 30:
                # Limit for AI processing efficiency
                candidate_urls = candidate_urls[:30]
            
            # Create clustering prompt
            urls_text = "\n".join([f"- {url}" for url in candidate_urls])
            
            prompt = f"""Analyze these URLs from {supplier_domain} and cluster them into 5-15 logical product categories.

URLs to analyze:
{urls_text}

Requirements:
1. Create 5-15 distinct category clusters
2. Each cluster should represent a logical product category (e.g., "household", "health-beauty", "electronics")
3. Assign URLs to clusters based on path patterns and keywords
4. For each category provide:
   - name: Clear category name (e.g., "Health & Beauty", "Household Essentials")
   - description: What products this category likely contains
   - urls: Array of URLs that belong to this category
   - keywords: Key terms that identify this category
   - estimated_products: Rough estimate of products per URL (1-50)

Return as JSON array. Focus on creating meaningful clusters for retail arbitrage analysis.

Example format:
[
  {{
    "name": "Health & Beauty",
    "description": "Personal care, cosmetics, and health products",
    "urls": ["https://site.com/health", "https://site.com/beauty"],
    "keywords": ["health", "beauty", "care", "cosmetics"],
    "estimated_products": 25
  }}
]

Return only the JSON array, no other text."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at e-commerce URL analysis and product categorization for retail arbitrage."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Clean JSON formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            clusters = json.loads(content)
            
            # Validate clusters structure
            validated_clusters = []
            for cluster in clusters:
                if isinstance(cluster, dict) and cluster.get('urls'):
                    validated_cluster = {
                        "name": cluster.get("name", "Unknown Category"),
                        "description": cluster.get("description", "Product category"),
                        "urls": cluster.get("urls", []),
                        "keywords": cluster.get("keywords", []),
                        "estimated_products": max(1, int(cluster.get("estimated_products", 10)))
                    }
                    validated_clusters.append(validated_cluster)
            
            logger.info(f"🎯 Clustered {len(candidate_urls)} URLs into {len(validated_clusters)} categories")
            return validated_clusters
            
        except Exception as e:
            logger.error(f"URL clustering failed: {e}")
            # Create simple fallback clusters
            return self._create_fallback_clusters(candidate_urls)
    
    def _create_fallback_clusters(self, candidate_urls: List[str]) -> List[Dict[str, Any]]:
        """Create fallback clusters when AI clustering fails"""
        # Simple path-based clustering
        path_clusters = defaultdict(list)
        
        for url in candidate_urls:
            try:
                path = urlparse(url).path.strip('/')
                # Extract first path segment as category
                category = path.split('/')[0] if path else 'root'
                path_clusters[category].append(url)
            except:
                path_clusters['general'].append(url)
        
        clusters = []
        for category, urls in path_clusters.items():
            clusters.append({
                "name": category.replace('-', ' ').title(),
                "description": f"Category based on /{category}/ URL path",
                "urls": urls,
                "keywords": [category],
                "estimated_products": 10
            })
        
        return clusters
    
    async def _validate_categories_with_scraper(
        self, 
        clustered_categories: List[Dict[str, Any]], 
        supplier_domain: str
    ) -> List[Dict[str, Any]]:
        """Validate categories using ConfigurableSupplierScraper.quick_count"""
        try:
            # Import here to avoid circular dependencies
            from tools.configurable_supplier_scraper import ConfigurableSupplierScraper
            
            scraper = ConfigurableSupplierScraper()
            validated_categories = []
            
            for category in clustered_categories:
                validation_results = []
                
                # Test each URL in the category
                for url in category.get('urls', [])[:3]:  # Limit to first 3 URLs per category
                    try:
                        # Call quick_count with timeout
                        count_result = await asyncio.wait_for(
                            scraper.quick_count(url),
                            timeout=15.0
                        )
                        
                        validation_results.append({
                            "url": url,
                            "product_count": count_result.get('product_count', 0),
                            "success": count_result.get('success', False),
                            "error": count_result.get('error')
                        })
                        
                        # Small delay between requests
                        await asyncio.sleep(0.5)
                        
                    except asyncio.TimeoutError:
                        validation_results.append({
                            "url": url,
                            "product_count": 0,
                            "success": False,
                            "error": "Timeout"
                        })
                    except Exception as e:
                        validation_results.append({
                            "url": url,
                            "product_count": 0,
                            "success": False,
                            "error": str(e)
                        })
                
                # Calculate category metrics
                total_products = sum(r.get('product_count', 0) for r in validation_results)
                success_rate = len([r for r in validation_results if r.get('success')]) / len(validation_results) if validation_results else 0
                
                # Add validation data to category
                validated_category = category.copy()
                validated_category.update({
                    "validation_results": validation_results,
                    "total_validated_products": total_products,
                    "validation_success_rate": success_rate,
                    "validated_at": datetime.now(timezone.utc).isoformat()
                })
                
                validated_categories.append(validated_category)
            
            logger.info(f"✅ Validated {len(validated_categories)} categories with scraper")
            return validated_categories
            
        except Exception as e:
            logger.error(f"Category validation failed: {e}")
            # Return categories without validation data
            return clustered_categories
    
    async def _generate_ai_suggestion_with_reasoning(
        self, 
        validated_categories: List[Dict[str, Any]], 
        total_products: int,
        discovered_urls: int
    ) -> Dict[str, Any]:
        """Generate AI suggestion with detailed reasoning (clearance-king schema)"""
        try:
            # Sort categories by validation metrics
            sorted_categories = sorted(
                validated_categories,
                key=lambda x: (
                    x.get('total_validated_products', 0),
                    x.get('validation_success_rate', 0)
                ),
                reverse=True
            )
            
            # Select top categories
            top_3_urls = []
            secondary_urls = []
            skip_urls = []
            
            for i, category in enumerate(sorted_categories):
                category_urls = category.get('urls', [])
                
                if i < 3:  # Top 3 categories
                    top_3_urls.extend(category_urls[:2])  # Max 2 URLs per category
                elif i < 8:  # Next 5 categories
                    secondary_urls.extend(category_urls[:1])  # 1 URL per category
                else:  # Remaining categories
                    skip_urls.extend(category_urls)
            
            # Limit URL counts
            top_3_urls = top_3_urls[:6]
            secondary_urls = secondary_urls[:10]
            
            # Generate detailed reasoning
            reasoning_prompt = f"""Analyze these validated e-commerce categories and provide detailed arbitrage reasoning.

Categories with validation:
{json.dumps(sorted_categories[:5], indent=2)}

Total products analyzed: {total_products}
URLs discovered: {discovered_urls}

Provide detailed reasoning for:
1. Why the top 3 categories were selected
2. Product potential assessment
3. Arbitrage opportunity analysis
4. Risk factors
5. Recommended strategy

Focus on retail arbitrage potential and profitability indicators."""

            reasoning_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert in retail arbitrage analysis and category optimization."},
                    {"role": "user", "content": reasoning_prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            detailed_reasoning = reasoning_response.choices[0].message.content.strip()
            
            # Create AI suggestion structure
            ai_suggestion = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_context": {
                    "categories_discovered": len(validated_categories),
                    "total_products_processed": total_products,
                    "previous_categories_count": 0  # TODO: Get from cache
                },
                "ai_suggestions": {
                    "top_3_urls": top_3_urls,
                    "secondary_urls": secondary_urls,
                    "skip_urls": skip_urls,
                    "detailed_reasoning": {
                        "category_analysis": detailed_reasoning,
                        "selection_criteria": "Validation-based ranking with product count and success rate",
                        "arbitrage_potential": "High" if len(top_3_urls) >= 3 else "Medium",
                        "risk_assessment": "Standard retail arbitrage risks apply"
                    },
                    "validation_results": {
                        category['name']: {
                            "total_products": category.get('total_validated_products', 0),
                            "success_rate": category.get('validation_success_rate', 0),
                            "urls_tested": len(category.get('validation_results', []))
                        }
                        for category in sorted_categories[:10]
                    }
                }
            }
            
            logger.info(f"🎯 Generated AI suggestion with {len(top_3_urls)} top URLs")
            return ai_suggestion
            
        except Exception as e:
            logger.error(f"AI reasoning generation failed: {e}")
            # Create minimal suggestion
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_context": {
                    "categories_discovered": len(validated_categories),
                    "total_products_processed": total_products,
                    "previous_categories_count": 0
                },
                "ai_suggestions": {
                    "top_3_urls": [cat.get('urls', [])[0] for cat in validated_categories[:3] if cat.get('urls')],
                    "secondary_urls": [],
                    "skip_urls": [],
                    "detailed_reasoning": {"error": "Failed to generate detailed reasoning"},
                    "validation_results": {}
                }
            }
    
    def _update_cache_with_suggestion(
        self, 
        cache_data: Dict[str, Any], 
        ai_suggestion: Dict[str, Any],
        total_products: int
    ) -> Dict[str, Any]:
        """Update cache with new AI suggestion (APPEND to history, increment calls)"""
        # Increment AI calls counter
        cache_data["total_ai_calls"] = cache_data.get("total_ai_calls", 0) + 1
        
        # Update timestamps
        cache_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # APPEND to ai_suggestion_history
        if "ai_suggestion_history" not in cache_data:
            cache_data["ai_suggestion_history"] = []
        
        cache_data["ai_suggestion_history"].append(ai_suggestion)
        
        return cache_data
    
    async def _save_cache(self, cache_data: Dict[str, Any], cache_file_path: Path) -> None:
        """Save cache data to file"""
        try:
            # Ensure directory exists
            cache_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with pretty formatting
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved cache with {cache_data.get('total_ai_calls', 0)} total AI calls")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            raise
    
    async def _save_empty_suggestion(
        self, 
        cache_data: Dict[str, Any], 
        cache_file_path: Path,
        total_products: int
    ) -> Path:
        """Save empty suggestion when generation fails"""
        empty_suggestion = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_context": {
                "categories_discovered": 0,
                "total_products_processed": total_products,
                "previous_categories_count": len(cache_data.get("ai_suggestion_history", []))
            },
            "ai_suggestions": {
                "top_3_urls": [],
                "secondary_urls": [],
                "skip_urls": [],
                "detailed_reasoning": {"error": "Failed to generate categories"},
                "validation_results": {}
            }
        }
        
        updated_cache = self._update_cache_with_suggestion(cache_data, empty_suggestion, total_products)
        await self._save_cache(updated_cache, cache_file_path)
        
        return cache_file_path


# Main function matching required signature
async def generate_categories(
    supplier_domain: str, 
    products: List[Dict[str, Any]], 
    url_discovery_output: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Generate categories with URL clustering and validation
    
    Args:
        supplier_domain: Supplier domain identifier
        products: List of product dictionaries
        url_discovery_output: Optional URL discovery data
        
    Returns:
        Path to ai_category_cache.json in OUTPUTS/{supplier}/{run_ts}/
    """
    suggester = AICategorySuggester()
    return await suggester.generate_categories(supplier_domain, products, url_discovery_output)


# Synchronous wrapper for backward compatibility
def generate_categories_sync(
    supplier_domain: str, 
    products: List[Dict[str, Any]], 
    url_discovery_output: Optional[Dict[str, Any]] = None
) -> Path:
    """Synchronous wrapper for generate_categories"""
    return asyncio.run(generate_categories(supplier_domain, products, url_discovery_output))


if __name__ == "__main__":
    # Test the new category suggester
    async def test_category_suggester():
        test_products = [
            {
                "title": "Kitchen Knife Set Stainless Steel",
                "url": "https://clearance-king.co.uk/household/kitchen-knife-set",
                "source_category_url": "https://clearance-king.co.uk/household"
            },
            {
                "title": "Hand Sanitizer Gel 500ml",
                "url": "https://clearance-king.co.uk/health-beauty/hand-sanitizer",
                "source_category_url": "https://clearance-king.co.uk/health-beauty"
            }
        ]
        
        test_discovery = {
            "navigation_urls": [
                "https://clearance-king.co.uk/household",
                "https://clearance-king.co.uk/health-beauty",
                "https://clearance-king.co.uk/electronics"
            ]
        }
        
        try:
            result_path = await generate_categories(
                "clearance-king.co.uk", 
                test_products, 
                test_discovery
            )
            print(f"✅ Test completed: {result_path}")
            
            # Show results
            with open(result_path, 'r') as f:
                data = json.load(f)
            
            print(f"Total AI calls: {data.get('total_ai_calls', 0)}")
            print(f"History entries: {len(data.get('ai_suggestion_history', []))}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    asyncio.run(test_category_suggester())