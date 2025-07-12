"""
Linking Map Writer - Array format implementation
==============================================

Replaces matching_result dict with array schema:
- Save to OUTPUTS/{supplier}/{run_ts}/linking_maps/linking_map.json
- Each element: {supplier_product_identifier, supplier_title_snippet, chosen_amazon_asin, 
  amazon_title_snippet, amazon_ean_on_page, match_method}
- Uses proper array format instead of dict
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.path_manager import get_run_output_dir

logger = logging.getLogger(__name__)


class LinkingMapWriter:
    """Writes linking map data in proper array format"""
    
    def __init__(self):
        logger.info("🔗 Linking Map Writer initialized with array format")
    
    def write_linking_map(
        self,
        supplier_name: str,
        linking_results: List[Dict[str, Any]],
        run_output_dir: Optional[Path] = None
    ) -> Path:
        """
        Write linking map in array format to run output directory
        
        Args:
            supplier_name: Supplier domain identifier
            linking_results: List of linking result dictionaries
            run_output_dir: Optional specific run directory
            
        Returns:
            Path to written linking_map.json file
        """
        try:
            # FIXED: Always use supplier-specific subdirectory structure to match existing clearance-king.co.uk pattern
            if run_output_dir is None:
                # Use consistent subdirectory structure: OUTPUTS/FBA_ANALYSIS/linking_maps/{supplier}/linking_map.json
                supplier_linking_dir = Path("OUTPUTS") / "FBA_ANALYSIS" / "linking_maps" / supplier_name
                supplier_linking_dir.mkdir(parents=True, exist_ok=True)
                linking_map_path = supplier_linking_dir / "linking_map.json"
            else:
                # Legacy run-based directory support for backward compatibility
                linking_maps_dir = run_output_dir / "linking_maps"
                linking_maps_dir.mkdir(exist_ok=True)
                linking_map_path = linking_maps_dir / "linking_map.json"
            
            logger.info(f"🔗 Writing {len(linking_results)} linking results for {supplier_name}")
            
            # Convert results to proper array format
            linking_map_array = []
            
            for result in linking_results:
                if isinstance(result, dict):
                    # Convert to required schema format
                    array_entry = self._convert_to_array_format(result)
                    if array_entry:
                        linking_map_array.append(array_entry)
            
            # Save as JSON array
            with open(linking_map_path, 'w', encoding='utf-8') as f:
                json.dump(linking_map_array, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Linking map written: {linking_map_path} ({len(linking_map_array)} entries)")
            return linking_map_path
            
        except Exception as e:
            logger.error(f"Failed to write linking map for {supplier_name}: {e}")
            raise
    
    def _convert_to_array_format(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert linking result to array entry format
        
        Args:
            result: Linking result dictionary
            
        Returns:
            Converted array entry or None if invalid
        """
        try:
            # Required fields for array format
            required_fields = [
                "supplier_product_identifier",
                "supplier_title_snippet", 
                "chosen_amazon_asin",
                "amazon_title_snippet",
                "match_method"
            ]
            
            # Extract data from various possible input formats
            array_entry = {}
            
            # Supplier product identifier (EAN, SKU, or URL-based)
            if result.get('supplier_ean'):
                array_entry["supplier_product_identifier"] = f"EAN_{result['supplier_ean']}"
            elif result.get('supplier_sku'):
                array_entry["supplier_product_identifier"] = f"SKU_{result['supplier_sku']}"
            elif result.get('supplier_product_id'):
                array_entry["supplier_product_identifier"] = result['supplier_product_id']
            elif result.get('supplier_url'):
                # Extract ID from URL
                url_id = self._extract_id_from_url(result['supplier_url'])
                array_entry["supplier_product_identifier"] = f"URL_{url_id}"
            else:
                # Generate from title hash as fallback
                title = result.get('supplier_title', result.get('title', ''))
                if title:
                    title_hash = str(hash(title))[-8:]  # Last 8 digits of hash
                    array_entry["supplier_product_identifier"] = f"TITLE_{title_hash}"
                else:
                    logger.warning(f"Cannot create product identifier for result: {result}")
                    return None
            
            # Supplier title snippet
            supplier_title = result.get('supplier_title', result.get('title', ''))
            if len(supplier_title) > 200:
                supplier_title = supplier_title[:197] + "..."
            array_entry["supplier_title_snippet"] = supplier_title
            
            # Amazon ASIN
            asin = result.get('amazon_asin', result.get('asin', ''))
            if not asin or len(asin) != 10 or not asin.startswith('B'):
                logger.warning(f"Invalid ASIN in result: {asin}")
                return None
            array_entry["chosen_amazon_asin"] = asin
            
            # Amazon title snippet
            amazon_title = result.get('amazon_title', result.get('amazon_product_title', ''))
            if len(amazon_title) > 200:
                amazon_title = amazon_title[:197] + "..."
            array_entry["amazon_title_snippet"] = amazon_title
            
            # Amazon EAN (optional)
            amazon_ean = result.get('amazon_ean', result.get('amazon_ean_on_page'))
            array_entry["amazon_ean_on_page"] = amazon_ean if amazon_ean else None
            
            # Match method
            match_method = result.get('match_method', result.get('matching_method', 'unknown'))
            valid_methods = ["EAN_search", "title_search", "hybrid_search", "manual_match", "ai_match"]
            if match_method not in valid_methods:
                # Map common variants
                method_mapping = {
                    'ean': 'EAN_search',
                    'title': 'title_search',
                    'hybrid': 'hybrid_search',
                    'manual': 'manual_match',
                    'ai': 'ai_match'
                }
                match_method = method_mapping.get(match_method.lower(), 'title_search')
            array_entry["match_method"] = match_method
            
            # Additional optional fields
            if result.get('confidence_score'):
                array_entry["confidence_score"] = result['confidence_score']
            
            if result.get('match_timestamp'):
                array_entry["match_timestamp"] = result['match_timestamp']
            elif result.get('timestamp'):
                array_entry["match_timestamp"] = result['timestamp']
            else:
                array_entry["match_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Validate required fields are present
            for field in required_fields:
                if not array_entry.get(field):
                    logger.warning(f"Missing required field '{field}' in result: {result}")
                    return None
            
            return array_entry
            
        except Exception as e:
            logger.error(f"Error converting result to array format: {e}")
            logger.debug(f"Problematic result: {result}")
            return None
    
    def _extract_id_from_url(self, url: str) -> str:
        """Extract identifier from URL"""
        try:
            # Extract last path segment or ID parameter
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(url)
            
            # Try to get ID from query parameters
            query_params = parse_qs(parsed.query)
            for param in ['id', 'product_id', 'item_id', 'p']:
                if param in query_params and query_params[param]:
                    return query_params[param][0]
            
            # Extract from path
            path_segments = [seg for seg in parsed.path.split('/') if seg]
            if path_segments:
                # Use last segment that looks like an ID
                for segment in reversed(path_segments):
                    if any(c.isdigit() for c in segment) and len(segment) > 2:
                        return segment
                
                # Fallback to last segment
                return path_segments[-1]
            
            # Fallback to domain + path hash
            return f"{parsed.netloc}_{abs(hash(parsed.path))}".replace('.', '-')
            
        except Exception:
            # Final fallback
            return f"url_{abs(hash(url))}"
    
    def append_to_linking_map(
        self,
        supplier_name: str,
        new_results: List[Dict[str, Any]],
        run_output_dir: Optional[Path] = None
    ) -> Path:
        """
        Append new results to existing linking map
        
        Args:
            supplier_name: Supplier domain identifier
            new_results: New linking results to append
            run_output_dir: Optional specific run directory
            
        Returns:
            Path to updated linking_map.json file
        """
        try:
            # FIXED: Always use supplier-specific subdirectory structure to match existing clearance-king.co.uk pattern
            if run_output_dir is None:
                # Use consistent subdirectory structure: OUTPUTS/FBA_ANALYSIS/linking_maps/{supplier}/linking_map.json
                supplier_linking_dir = Path("OUTPUTS") / "FBA_ANALYSIS" / "linking_maps" / supplier_name
                supplier_linking_dir.mkdir(parents=True, exist_ok=True)
                linking_map_path = supplier_linking_dir / "linking_map.json"
            else:
                # Legacy run-based directory support for backward compatibility
                linking_maps_dir = run_output_dir / "linking_maps"
                linking_map_path = linking_maps_dir / "linking_map.json"
            
            # Load existing data if it exists
            existing_data = []
            if linking_map_path.exists():
                try:
                    with open(linking_map_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    
                    # Ensure it's a list
                    if not isinstance(existing_data, list):
                        logger.warning(f"Existing linking map is not an array, converting...")
                        existing_data = []
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Existing linking map is invalid JSON, starting fresh: {e}")
                    existing_data = []
            
            # Convert new results to array format
            new_entries = []
            for result in new_results:
                entry = self._convert_to_array_format(result)
                if entry:
                    new_entries.append(entry)
            
            # Check for duplicates based on supplier_product_identifier
            existing_ids = {entry.get("supplier_product_identifier") for entry in existing_data}
            unique_new_entries = []
            
            for entry in new_entries:
                if entry["supplier_product_identifier"] not in existing_ids:
                    unique_new_entries.append(entry)
                else:
                    logger.debug(f"Skipping duplicate entry: {entry['supplier_product_identifier']}")
            
            # Combine data
            combined_data = existing_data + unique_new_entries
            
            # Write back to file
            linking_map_path.parent.mkdir(parents=True, exist_ok=True)
            with open(linking_map_path, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"🔗 Appended {len(unique_new_entries)} new entries to linking map "
                       f"(total: {len(combined_data)})")
            
            return linking_map_path
            
        except Exception as e:
            logger.error(f"Failed to append to linking map for {supplier_name}: {e}")
            raise
    
    def validate_linking_map(self, linking_map_path: Path) -> Dict[str, Any]:
        """
        Validate linking map format and content
        
        Args:
            linking_map_path: Path to linking map file
            
        Returns:
            Validation results dictionary
        """
        validation_result = {
            "valid": False,
            "file_exists": False,
            "is_array": False,
            "entry_count": 0,
            "errors": [],
            "warnings": []
        }
        
        try:
            if not linking_map_path.exists():
                validation_result["errors"].append("File does not exist")
                return validation_result
            
            validation_result["file_exists"] = True
            
            # Load and validate JSON
            with open(linking_map_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                validation_result["errors"].append("Linking map must be an array")
                return validation_result
            
            validation_result["is_array"] = True
            validation_result["entry_count"] = len(data)
            
            # Validate each entry
            required_fields = [
                "supplier_product_identifier",
                "supplier_title_snippet",
                "chosen_amazon_asin",
                "amazon_title_snippet",
                "match_method"
            ]
            
            valid_entries = 0
            for i, entry in enumerate(data):
                if not isinstance(entry, dict):
                    validation_result["errors"].append(f"Entry {i} is not an object")
                    continue
                
                entry_valid = True
                for field in required_fields:
                    if field not in entry or not entry[field]:
                        validation_result["errors"].append(f"Entry {i} missing required field: {field}")
                        entry_valid = False
                
                # Validate ASIN format
                asin = entry.get("chosen_amazon_asin", "")
                if not (len(asin) == 10 and asin.startswith('B')):
                    validation_result["warnings"].append(f"Entry {i} has invalid ASIN format: {asin}")
                
                if entry_valid:
                    valid_entries += 1
            
            # Overall validation
            if validation_result["errors"]:
                validation_result["valid"] = False
            else:
                validation_result["valid"] = True
                validation_result["valid_entries"] = valid_entries
            
            logger.info(f"Linking map validation: {valid_entries}/{len(data)} valid entries")
            
        except json.JSONDecodeError as e:
            validation_result["errors"].append(f"Invalid JSON: {e}")
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {e}")
        
        return validation_result


# Convenience functions
def write_linking_map(
    supplier_name: str,
    linking_results: List[Dict[str, Any]],
    run_output_dir: Optional[Path] = None
) -> Path:
    """Write linking map in array format"""
    writer = LinkingMapWriter()
    return writer.write_linking_map(supplier_name, linking_results, run_output_dir)


def append_to_linking_map(
    supplier_name: str,
    new_results: List[Dict[str, Any]],
    run_output_dir: Optional[Path] = None
) -> Path:
    """Append to existing linking map"""
    writer = LinkingMapWriter()
    return writer.append_to_linking_map(supplier_name, new_results, run_output_dir)


def validate_linking_map(linking_map_path: Path) -> Dict[str, Any]:
    """Validate linking map format"""
    writer = LinkingMapWriter()
    return writer.validate_linking_map(linking_map_path)


if __name__ == "__main__":
    # Test linking map writer
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    test_results = [
        {
            "supplier_ean": "5055453430411",
            "supplier_title": "Kitchen Knife Set Stainless Steel 5 Piece",
            "supplier_url": "https://poundwholesale.co.uk/products/knife-set-123",
            "amazon_asin": "B08N5WRWNW",
            "amazon_title": "Kitchen Knife Set Stainless Steel Professional 5 Piece",
            "amazon_ean": "5055453430411",
            "match_method": "EAN_search",
            "confidence_score": 0.95
        },
        {
            "supplier_sku": "PWS-SANITIZER-500",
            "supplier_title": "Hand Sanitizer Gel 500ml Antibacterial",
            "amazon_asin": "B087G1VKN3",
            "amazon_title": "Hand Sanitizer Gel 500ml Antibacterial Protection",
            "match_method": "title_search",
            "confidence_score": 0.82
        }
    ]
    
    try:
        # Test writing
        linking_map_path = write_linking_map("test-supplier.com", test_results)
        print(f"✅ Linking map written: {linking_map_path}")
        
        # Test validation
        validation = validate_linking_map(linking_map_path)
        print(f"Validation result: {validation}")
        
        # Test appending
        additional_results = [
            {
                "supplier_title": "Another Test Product",
                "amazon_asin": "B012345678",
                "amazon_title": "Amazon Test Product",
                "match_method": "manual_match"
            }
        ]
        
        append_path = append_to_linking_map("test-supplier.com", additional_results)
        print(f"✅ Appended to linking map: {append_path}")
        
        # Final validation
        final_validation = validate_linking_map(append_path)
        print(f"Final validation: {final_validation}")
        
        print("✅ All linking map writer tests passed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")