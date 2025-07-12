"""
Enhanced Cache Manager for Amazon FBA Agent System

This module provides a centralized, robust cache management system with:
- Multiple clearing strategies
- Data validation and recovery
- Performance monitoring
- Automated maintenance
- Configuration-driven behavior
"""

import asyncio
import json
import logging
import os
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import hashlib
import gzip
from concurrent.futures import ThreadPoolExecutor
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    """Cache performance and health metrics"""
    hit_count: int = 0
    miss_count: int = 0
    total_size_bytes: int = 0
    file_count: int = 0
    corruption_count: int = 0
    last_validation: Optional[datetime] = None
    last_cleanup: Optional[datetime] = None
    avg_access_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    @property
    def size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)

@dataclass
class ValidationResult:
    """Result of cache validation operation"""
    is_valid: bool
    file_path: Path
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    file_size: int = 0
    last_modified: Optional[datetime] = None
    
@dataclass
class ClearingResult:
    """Result of cache clearing operation"""
    files_removed: int = 0
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    strategy_used: str = ""

class CacheStrategy(ABC):
    """Abstract base class for cache management strategies"""
    
    @abstractmethod
    async def should_clear(self, cache_info: Dict[str, Any]) -> bool:
        """Determine if cache should be cleared"""
        pass
    
    @abstractmethod
    async def clear_cache(self, cache_path: Path, config: Dict[str, Any]) -> ClearingResult:
        """Execute cache clearing logic"""
        pass

class SmartSelectiveStrategy(CacheStrategy):
    """Intelligent selective clearing based on usage patterns and relationships"""
    
    def __init__(self, linking_map_path: Path):
        self.linking_map_path = linking_map_path
        self.processed_identifiers: Set[str] = set()
        
    async def should_clear(self, cache_info: Dict[str, Any]) -> bool:
        """Clear if cache is stale or contains processed items"""
        cache_age_hours = cache_info.get('age_hours', 0)
        max_age = cache_info.get('config', {}).get('ttl_hours', 336)
        
        # Always clear if cache is too old
        if cache_age_hours > max_age:
            return True
            
        # Clear if significant portion is processed
        processed_ratio = await self._get_processed_ratio(cache_info['path'])
        return processed_ratio > 0.7  # Clear if >70% processed
    
    async def clear_cache(self, cache_path: Path, config: Dict[str, Any]) -> ClearingResult:
        """Clear processed items and stale data"""
        start_time = time.time()
        result = ClearingResult(strategy_used="smart_selective")
        
        try:
            # Load processed identifiers from linking map
            await self._load_processed_identifiers()
            
            if cache_path.is_file():
                # Handle single cache file
                await self._clear_cache_file(cache_path, result)
            elif cache_path.is_dir():
                # Handle cache directory
                await self._clear_cache_directory(cache_path, result)
                
        except Exception as e:
            result.errors.append(f"Error during smart selective clearing: {str(e)}")
            log.error(f"Smart selective clearing failed: {e}")
            
        result.duration_seconds = time.time() - start_time
        return result
    
    async def _load_processed_identifiers(self):
        """Load processed product identifiers from linking map"""
        if not self.linking_map_path.exists():
            return
            
        try:
            with open(self.linking_map_path, 'r', encoding='utf-8') as f:
                linking_map = json.load(f)
                
            self.processed_identifiers = {
                entry.get("supplier_product_identifier", "")
                for entry in linking_map
                if entry.get("supplier_product_identifier")
            }
            
            log.info(f"Loaded {len(self.processed_identifiers)} processed identifiers")
            
        except Exception as e:
            log.error(f"Failed to load linking map: {e}")
    
    async def _clear_cache_file(self, file_path: Path, result: ClearingResult):
        """Clear processed items from a single cache file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                
            if isinstance(cached_data, list):
                # Filter out processed products
                original_count = len(cached_data)
                filtered_data = []
                
                for item in cached_data:
                    identifier = self._get_product_identifier(item)
                    if identifier not in self.processed_identifiers:
                        filtered_data.append(item)
                
                removed_count = original_count - len(filtered_data)
                
                if removed_count > 0:
                    # Create backup before modifying
                    backup_path = file_path.with_suffix(f'.backup_{int(time.time())}')
                    shutil.copy2(file_path, backup_path)
                    
                    # Save filtered data
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
                    
                    result.files_removed += removed_count
                    log.info(f"Removed {removed_count} processed items from {file_path.name}")
                    
        except Exception as e:
            result.errors.append(f"Error processing {file_path}: {str(e)}")
    
    async def _clear_cache_directory(self, dir_path: Path, result: ClearingResult):
        """Clear processed items from cache directory"""
        for file_path in dir_path.glob("*.json"):
            await self._clear_cache_file(file_path, result)
    
    def _get_product_identifier(self, product: Dict[str, Any]) -> str:
        """Generate product identifier for matching"""
        ean = product.get("ean")
        url = product.get("url")
        
        if ean:
            return f"EAN_{ean}"
        elif url:
            return f"URL_{url}"
        else:
            return ""
    
    async def _get_processed_ratio(self, cache_path: Path) -> float:
        """Calculate ratio of processed items in cache"""
        try:
            if not cache_path.exists():
                return 0.0
                
            await self._load_processed_identifiers()
            
            if cache_path.is_file():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    
                if isinstance(cached_data, list) and cached_data:
                    processed_count = sum(
                        1 for item in cached_data
                        if self._get_product_identifier(item) in self.processed_identifiers
                    )
                    return processed_count / len(cached_data)
                    
        except Exception as e:
            log.error(f"Error calculating processed ratio: {e}")
            
        return 0.0

class SizeBasedStrategy(CacheStrategy):
    """Clear cache when size limits are exceeded using LRU eviction"""
    
    async def should_clear(self, cache_info: Dict[str, Any]) -> bool:
        """Clear if cache exceeds size limits"""
        current_size_mb = cache_info.get('size_mb', 0)
        max_size_mb = cache_info.get('config', {}).get('max_size_mb', 1000)
        
        return current_size_mb > max_size_mb
    
    async def clear_cache(self, cache_path: Path, config: Dict[str, Any]) -> ClearingResult:
        """Clear oldest files until under size limit"""
        start_time = time.time()
        result = ClearingResult(strategy_used="size_based")
        
        try:
            max_size_bytes = config.get('max_size_mb', 1000) * 1024 * 1024
            current_size = await self._get_directory_size(cache_path)
            
            if current_size <= max_size_bytes:
                return result
            
            # Get files sorted by access time (LRU first)
            files_by_age = await self._get_files_by_age(cache_path)
            
            bytes_to_remove = current_size - max_size_bytes
            bytes_removed = 0
            
            for file_path, file_size, _ in files_by_age:
                if bytes_removed >= bytes_to_remove:
                    break
                    
                try:
                    file_path.unlink()
                    bytes_removed += file_size
                    result.files_removed += 1
                    log.info(f"Removed {file_path.name} ({file_size} bytes)")
                    
                except Exception as e:
                    result.errors.append(f"Failed to remove {file_path}: {str(e)}")
            
            result.bytes_freed = bytes_removed
            
        except Exception as e:
            result.errors.append(f"Size-based clearing failed: {str(e)}")
            
        result.duration_seconds = time.time() - start_time
        return result
    
    async def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            log.error(f"Error calculating directory size: {e}")
        return total_size
    
    async def _get_files_by_age(self, path: Path) -> List[Tuple[Path, int, float]]:
        """Get files sorted by last access time (oldest first)"""
        files = []
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append((file_path, stat.st_size, stat.st_atime))
            
            # Sort by access time (oldest first)
            files.sort(key=lambda x: x[2])
            
        except Exception as e:
            log.error(f"Error getting files by age: {e}")
            
        return files

class SelectiveStrategy(CacheStrategy):
    """Selective clearing based on TTL and usage patterns"""
    
    async def should_clear(self, cache_info: Dict[str, Any]) -> bool:
        """Clear if cache has expired based on TTL"""
        cache_age_hours = cache_info.get('age_hours', 0)
        ttl_hours = cache_info.get('config', {}).get('ttl_hours', 336)
        
        # Don't clear if TTL is -1 (permanent cache)
        if ttl_hours == -1:
            return False
            
        return cache_age_hours > ttl_hours
    
    async def clear_cache(self, cache_path: Path, config: Dict[str, Any]) -> ClearingResult:
        """Clear expired cache files selectively"""
        start_time = time.time()
        result = ClearingResult(strategy_used="selective")
        
        try:
            ttl_hours = config.get('ttl_hours', 336)
            if ttl_hours == -1:
                return result  # Don't clear permanent caches
            
            cutoff_time = time.time() - (ttl_hours * 3600)
            
            if cache_path.is_file():
                await self._clear_expired_file(cache_path, cutoff_time, result)
            elif cache_path.is_dir():
                await self._clear_expired_directory(cache_path, cutoff_time, result)
                
        except Exception as e:
            result.errors.append(f"Selective clearing failed: {str(e)}")
            
        result.duration_seconds = time.time() - start_time
        return result
    
    async def _clear_expired_file(self, file_path: Path, cutoff_time: float, result: ClearingResult):
        """Clear single file if expired"""
        try:
            stat = file_path.stat()
            if stat.st_mtime < cutoff_time:
                file_size = stat.st_size
                file_path.unlink()
                result.files_removed += 1
                result.bytes_freed += file_size
                log.info(f"Removed expired file: {file_path.name}")
        except Exception as e:
            result.errors.append(f"Error clearing {file_path}: {str(e)}")
    
    async def _clear_expired_directory(self, dir_path: Path, cutoff_time: float, result: ClearingResult):
        """Clear expired files in directory"""
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    await self._clear_expired_file(file_path, cutoff_time, result)
        except Exception as e:
            result.errors.append(f"Error clearing directory {dir_path}: {str(e)}")

class ArchiveOldStrategy(CacheStrategy):
    """Archive old files instead of deleting them"""
    
    async def should_clear(self, cache_info: Dict[str, Any]) -> bool:
        """Archive if cache has old files that should be preserved"""
        cache_age_hours = cache_info.get('age_hours', 0)
        # Archive files older than 30 days
        return cache_age_hours > (30 * 24)
    
    async def clear_cache(self, cache_path: Path, config: Dict[str, Any]) -> ClearingResult:
        """Archive old files to preserve them"""
        start_time = time.time()
        result = ClearingResult(strategy_used="archive_old")
        
        try:
            # Create archive directory
            archive_dir = cache_path.parent / f"{cache_path.name}_archive"
            archive_dir.mkdir(exist_ok=True)
            
            # Archive files older than 30 days
            cutoff_time = time.time() - (30 * 24 * 3600)
            
            if cache_path.is_file():
                await self._archive_file(cache_path, archive_dir, cutoff_time, result)
            elif cache_path.is_dir():
                await self._archive_directory(cache_path, archive_dir, cutoff_time, result)
                
        except Exception as e:
            result.errors.append(f"Archive strategy failed: {str(e)}")
            
        result.duration_seconds = time.time() - start_time
        return result
    
    async def _archive_file(self, file_path: Path, archive_dir: Path, cutoff_time: float, result: ClearingResult):
        """Archive single file if old enough"""
        try:
            stat = file_path.stat()
            if stat.st_mtime < cutoff_time:
                archive_path = archive_dir / file_path.name
                shutil.move(str(file_path), str(archive_path))
                result.files_removed += 1
                result.bytes_freed += stat.st_size
                log.info(f"Archived old file: {file_path.name}")
        except Exception as e:
            result.errors.append(f"Error archiving {file_path}: {str(e)}")
    
    async def _archive_directory(self, dir_path: Path, archive_dir: Path, cutoff_time: float, result: ClearingResult):
        """Archive old files in directory"""
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    await self._archive_file(file_path, archive_dir, cutoff_time, result)
        except Exception as e:
            result.errors.append(f"Error archiving directory {dir_path}: {str(e)}")

class CacheValidator:
    """Validate cache files for corruption and consistency"""
    
    def __init__(self):
        self.validation_schemas = {
            'supplier_cache': self._validate_supplier_cache,
            'amazon_cache': self._validate_amazon_cache,
            'linking_map': self._validate_linking_map,
            'ai_category_cache': self._validate_ai_category_cache
        }
    
    async def validate_file(self, file_path: Path, cache_type: str = 'generic') -> ValidationResult:
        """Validate a single cache file"""
        result = ValidationResult(is_valid=True, file_path=file_path)
        
        try:
            if not file_path.exists():
                result.is_valid = False
                result.errors.append("File does not exist")
                return result
            
            stat = file_path.stat()
            result.file_size = stat.st_size
            result.last_modified = datetime.fromtimestamp(stat.st_mtime)
            
            # Basic file checks
            if stat.st_size == 0:
                result.is_valid = False
                result.errors.append("File is empty")
                return result
            
            # JSON structure validation
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                result.is_valid = False
                result.errors.append(f"Invalid JSON: {str(e)}")
                return result
            except UnicodeDecodeError as e:
                result.is_valid = False
                result.errors.append(f"Encoding error: {str(e)}")
                return result
            
            # Schema-specific validation
            validator = self.validation_schemas.get(cache_type, self._validate_generic)
            await validator(data, result)
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation error: {str(e)}")
        
        return result
    
    async def _validate_supplier_cache(self, data: Any, result: ValidationResult):
        """Validate supplier cache structure"""
        if not isinstance(data, list):
            result.errors.append("Supplier cache must be a list")
            result.is_valid = False
            return
        
        required_fields = ['title', 'price', 'url']
        for i, item in enumerate(data[:10]):  # Check first 10 items
            if not isinstance(item, dict):
                result.errors.append(f"Item {i} is not a dictionary")
                result.is_valid = False
                continue
                
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                result.warnings.append(f"Item {i} missing fields: {missing_fields}")
    
    async def _validate_amazon_cache(self, data: Any, result: ValidationResult):
        """Validate Amazon cache structure"""
        if not isinstance(data, dict):
            result.errors.append("Amazon cache must be a dictionary")
            result.is_valid = False
            return
        
        required_fields = ['title', 'asin']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            result.warnings.append(f"Missing fields: {missing_fields}")
    
    async def _validate_linking_map(self, data: Any, result: ValidationResult):
        """Validate linking map structure"""
        if not isinstance(data, list):
            result.errors.append("Linking map must be a list")
            result.is_valid = False
            return
        
        required_fields = ['supplier_product_identifier', 'chosen_amazon_asin']
        for i, item in enumerate(data[:10]):  # Check first 10 items
            if not isinstance(item, dict):
                result.errors.append(f"Item {i} is not a dictionary")
                result.is_valid = False
                continue
                
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                result.warnings.append(f"Item {i} missing fields: {missing_fields}")
    
    async def _validate_ai_category_cache(self, data: Any, result: ValidationResult):
        """Validate AI category cache structure"""
        if not isinstance(data, dict):
            result.errors.append("AI category cache must be a dictionary")
            result.is_valid = False
            return
        
        expected_keys = ['supplier_domain', 'timestamp', 'categories_suggested']
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            result.warnings.append(f"Missing keys: {missing_keys}")
    
    async def _validate_generic(self, data: Any, result: ValidationResult):
        """Generic validation for unknown cache types"""
        # Just ensure it's valid JSON (already checked) and not empty
        if data is None:
            result.warnings.append("Cache data is null")

class CacheManager:
    """Centralized cache management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_config = config.get('cache', {})
        self.strategies = self._initialize_strategies()
        self.validator = CacheValidator()
        self.metrics = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize cache directories
        self.cache_dirs = self._get_cache_directories()
        self._ensure_directories_exist()
    
    def _initialize_strategies(self) -> Dict[str, CacheStrategy]:
        """Initialize cache clearing strategies"""
        linking_map_path = Path(self.cache_config.get('directories', {}).get('linking_map', 'OUTPUTS/FBA_ANALYSIS/Linking map')) / 'linking_map.json'
        
        return {
            'smart_selective': SmartSelectiveStrategy(linking_map_path),
            'size_based': SizeBasedStrategy(),
            'selective': SelectiveStrategy(),
            'archive_old': ArchiveOldStrategy(),
        }
    
    def _get_cache_directories(self) -> Dict[str, Path]:
        """Get all cache directory paths"""
        cache_dirs = {}
        directories_config = self.cache_config.get('directories', {})
        
        for cache_type, path_str in directories_config.items():
            cache_dirs[cache_type] = Path(path_str)
            
        return cache_dirs
    
    def _ensure_directories_exist(self):
        """Ensure all cache directories exist"""
        for cache_type, path in self.cache_dirs.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
                log.debug(f"Ensured cache directory exists: {path}")
            except Exception as e:
                log.error(f"Failed to create cache directory {path}: {e}")
    
    async def clear_cache(self, strategy: str = "smart_selective", cache_types: Optional[List[str]] = None) -> Dict[str, ClearingResult]:
        """Clear cache using specified strategy"""
        log.info(f"Starting cache clearing with strategy: {strategy}")
        
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}. Available: {list(self.strategies.keys())}")
        
        strategy_instance = self.strategies[strategy]
        results = {}
        
        # Determine which caches to clear
        target_caches = cache_types or list(self.cache_dirs.keys())
        
        # Clear caches in parallel where possible
        tasks = []
        for cache_type in target_caches:
            if cache_type in self.cache_dirs:
                task = self._clear_single_cache(cache_type, strategy_instance)
                tasks.append((cache_type, task))
        
        # Execute clearing tasks
        for cache_type, task in tasks:
            try:
                result = await task
                results[cache_type] = result
                log.info(f"Cleared {cache_type}: {result.files_removed} files, {result.bytes_freed} bytes freed")
            except Exception as e:
                error_result = ClearingResult(strategy_used=strategy)
                error_result.errors.append(str(e))
                results[cache_type] = error_result
                log.error(f"Failed to clear {cache_type}: {e}")
        
        return results
    
    async def _clear_single_cache(self, cache_type: str, strategy: CacheStrategy) -> ClearingResult:
        """Clear a single cache using the specified strategy"""
        cache_path = self.cache_dirs[cache_type]
        cache_config = self.cache_config.get('cache_types', {}).get(cache_type, {})
        
        # Get cache info for strategy decision
        cache_info = await self._get_cache_info(cache_path, cache_config)
        
        # Check if clearing is needed
        if not await strategy.should_clear(cache_info):
            log.info(f"Skipping {cache_type} - clearing not needed")
            return ClearingResult(strategy_used=strategy.__class__.__name__)
        
        # Execute clearing
        return await strategy.clear_cache(cache_path, cache_config)
    
    async def _get_cache_info(self, cache_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get cache information for strategy decisions"""
        info = {
            'path': cache_path,
            'config': config,
            'exists': cache_path.exists(),
            'size_mb': 0,
            'file_count': 0,
            'age_hours': 0
        }
        
        if cache_path.exists():
            try:
                if cache_path.is_file():
                    stat = cache_path.stat()
                    info['size_mb'] = stat.st_size / (1024 * 1024)
                    info['file_count'] = 1
                    info['age_hours'] = (time.time() - stat.st_mtime) / 3600
                elif cache_path.is_dir():
                    total_size = 0
                    file_count = 0
                    oldest_time = time.time()
                    
                    for file_path in cache_path.rglob('*'):
                        if file_path.is_file():
                            stat = file_path.stat()
                            total_size += stat.st_size
                            file_count += 1
                            oldest_time = min(oldest_time, stat.st_mtime)
                    
                    info['size_mb'] = total_size / (1024 * 1024)
                    info['file_count'] = file_count
                    info['age_hours'] = (time.time() - oldest_time) / 3600
                    
            except Exception as e:
                log.error(f"Error getting cache info for {cache_path}: {e}")
        
        return info
    
    async def validate_cache(self, cache_types: Optional[List[str]] = None) -> Dict[str, List[ValidationResult]]:
        """Validate cache files for corruption"""
        log.info("Starting cache validation")
        
        target_caches = cache_types or list(self.cache_dirs.keys())
        results = {}
        
        for cache_type in target_caches:
            cache_path = self.cache_dirs[cache_type]
            cache_results = []
            
            try:
                if cache_path.is_file():
                    result = await self.validator.validate_file(cache_path, cache_type)
                    cache_results.append(result)
                elif cache_path.is_dir():
                    for file_path in cache_path.glob('*.json'):
                        result = await self.validator.validate_file(file_path, cache_type)
                        cache_results.append(result)
                
                results[cache_type] = cache_results
                
                # Log validation summary
                valid_count = sum(1 for r in cache_results if r.is_valid)
                invalid_count = len(cache_results) - valid_count
                
                if invalid_count > 0:
                    log.warning(f"{cache_type}: {valid_count} valid, {invalid_count} invalid files")
                else:
                    log.info(f"{cache_type}: All {valid_count} files valid")
                    
            except Exception as e:
                log.error(f"Error validating {cache_type}: {e}")
                results[cache_type] = []
        
        return results
    
    async def get_cache_metrics(self) -> Dict[str, CacheMetrics]:
        """Get comprehensive cache metrics"""
        metrics = {}
        
        for cache_type, cache_path in self.cache_dirs.items():
            cache_metrics = CacheMetrics()
            
            try:
                if cache_path.exists():
                    if cache_path.is_file():
                        stat = cache_path.stat()
                        cache_metrics.total_size_bytes = stat.st_size
                        cache_metrics.file_count = 1
                    elif cache_path.is_dir():
                        for file_path in cache_path.rglob('*'):
                            if file_path.is_file():
                                cache_metrics.total_size_bytes += file_path.stat().st_size
                                cache_metrics.file_count += 1
                
                metrics[cache_type] = cache_metrics
                
            except Exception as e:
                log.error(f"Error collecting metrics for {cache_type}: {e}")
                metrics[cache_type] = cache_metrics
        
        return metrics
    
    async def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache for better performance"""
        log.info("Starting cache optimization")
        
        optimization_results = {
            'compression_savings': 0,
            'defragmentation_time': 0,
            'index_rebuild_time': 0,
            'errors': []
        }
        
        try:
            # Compress old cache files
            compression_savings = await self._compress_old_files()
            optimization_results['compression_savings'] = compression_savings
            
            # Additional optimization tasks can be added here
            
        except Exception as e:
            optimization_results['errors'].append(str(e))
            log.error(f"Cache optimization error: {e}")
        
        return optimization_results
    
    async def _compress_old_files(self) -> int:
        """Compress old cache files to save space"""
        total_savings = 0
        cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days ago
        
        for cache_type, cache_path in self.cache_dirs.items():
            if not cache_path.exists() or not cache_path.is_dir():
                continue
                
            try:
                for file_path in cache_path.glob('*.json'):
                    stat = file_path.stat()
                    
                    # Compress files older than cutoff
                    if stat.st_mtime < cutoff_time and not file_path.name.endswith('.gz'):
                        original_size = stat.st_size
                        compressed_path = file_path.with_suffix('.json.gz')
                        
                        with open(file_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Remove original file
                        file_path.unlink()
                        
                        compressed_size = compressed_path.stat().st_size
                        savings = original_size - compressed_size
                        total_savings += savings
                        
                        log.info(f"Compressed {file_path.name}: {savings} bytes saved")
                        
            except Exception as e:
                log.error(f"Error compressing files in {cache_type}: {e}")
        
        return total_savings
    
    async def create_backup(self, cache_types: Optional[List[str]] = None) -> Dict[str, bool]:
        """Create backups of cache data"""
        log.info("Creating cache backups")
        
        target_caches = cache_types or list(self.cache_dirs.keys())
        results = {}
        
        backup_base_dir = Path("OUTPUTS/cache_backups")
        backup_base_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for cache_type in target_caches:
            try:
                cache_path = self.cache_dirs[cache_type]
                if not cache_path.exists():
                    results[cache_type] = True  # Nothing to backup
                    continue
                
                backup_path = backup_base_dir / f"{cache_type}_{timestamp}"
                
                if cache_path.is_file():
                    shutil.copy2(cache_path, backup_path.with_suffix('.json'))
                elif cache_path.is_dir():
                    shutil.copytree(cache_path, backup_path)
                
                results[cache_type] = True
                log.info(f"Created backup for {cache_type}: {backup_path}")
                
            except Exception as e:
                results[cache_type] = False
                log.error(f"Failed to backup {cache_type}: {e}")
        
        return results
    
    def get_system_resources(self) -> Dict[str, float]:
        """Get current system resource usage"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent
            }
        except Exception as e:
            log.error(f"Error getting system resources: {e}")
            return {'cpu_percent': 0, 'memory_percent': 0, 'disk_usage_percent': 0}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive cache health check"""
        log.info("Performing cache health check")
        
        health_report = {
            'overall_status': 'healthy',
            'cache_status': {},
            'system_resources': self.get_system_resources(),
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Validate all caches
            validation_results = await self.validate_cache()
            
            # Get cache metrics
            metrics = await self.get_cache_metrics()
            
            # Analyze each cache
            for cache_type in self.cache_dirs.keys():
                cache_status = {
                    'status': 'healthy',
                    'issues': [],
                    'metrics': metrics.get(cache_type, CacheMetrics()).__dict__
                }
                
                # Check validation results
                validations = validation_results.get(cache_type, [])
                invalid_files = [v for v in validations if not v.is_valid]
                
                if invalid_files:
                    cache_status['status'] = 'degraded'
                    cache_status['issues'].append(f"{len(invalid_files)} corrupted files")
                    health_report['overall_status'] = 'degraded'
                
                # Check size limits
                cache_metrics = metrics.get(cache_type, CacheMetrics())
                cache_config = self.cache_config.get('cache_types', {}).get(cache_type, {})
                max_size_mb = cache_config.get('max_size_mb', 1000)
                
                if cache_metrics.size_mb > max_size_mb:
                    cache_status['status'] = 'warning'
                    cache_status['issues'].append(f"Size limit exceeded: {cache_metrics.size_mb:.1f}MB > {max_size_mb}MB")
                    health_report['recommendations'].append(f"Clear {cache_type} cache to reduce size")
                
                health_report['cache_status'][cache_type] = cache_status
            
            # System resource checks
            resources = health_report['system_resources']
            if resources['disk_usage_percent'] > 90:
                health_report['overall_status'] = 'critical'
                health_report['recommendations'].append("Critical: Disk space low - immediate cache clearing recommended")
            elif resources['disk_usage_percent'] > 80:
                health_report['recommendations'].append("Warning: Disk space getting low - consider cache clearing")
            
        except Exception as e:
            health_report['overall_status'] = 'error'
            health_report['recommendations'].append(f"Health check failed: {str(e)}")
            log.error(f"Health check error: {e}")
        
        return health_report
    
    async def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

# Example usage and configuration
async def main():
    """Example usage of the CacheManager"""
    
    # Load configuration (in real usage, this would come from system_config.json)
    config = {
        "cache": {
            "enabled": True,
            "global_settings": {
                "max_total_size_gb": 5.0,
                "default_ttl_hours": 336,
                "backup_retention_days": 7,
                "validation_interval_hours": 6,
                "optimization_interval_hours": 24
            },
            "cache_types": {
                "supplier_cache": {
                    "ttl_hours": 336,
                    "max_size_mb": 1000,
                    "backup_enabled": True,
                    "validation_enabled": True,
                    "cleanup_strategy": "smart_selective"
                },
                "amazon_cache": {
                    "ttl_hours": 336,
                    "max_size_mb": 2000,
                    "backup_enabled": True,
                    "validation_enabled": True,
                    "cleanup_strategy": "size_based"
                },
                "ai_category_cache": {
                    "ttl_hours": 720,
                    "max_size_mb": 100,
                    "backup_enabled": False,
                    "validation_enabled": True,
                    "cleanup_strategy": "selective"
                },
                "linking_map": {
                    "ttl_hours": -1,
                    "max_size_mb": 500,
                    "backup_enabled": True,
                    "validation_enabled": True,
                    "cleanup_strategy": "archive_old"
                }
            },
            "directories": {
                "supplier_cache": "OUTPUTS/cached_products",
                "amazon_cache": "OUTPUTS/FBA_ANALYSIS/amazon_cache",
                "ai_category_cache": "OUTPUTS/FBA_ANALYSIS/ai_category_cache",
                "linking_map": "OUTPUTS/FBA_ANALYSIS/Linking map"
            }
        }
    }
    
    # Initialize cache manager
    cache_manager = CacheManager(config)
    
    try:
        # Perform health check
        print("=== Cache Health Check ===")
        health_report = await cache_manager.health_check()
        print(f"Overall Status: {health_report['overall_status']}")
        
        for cache_type, status in health_report['cache_status'].items():
            print(f"{cache_type}: {status['status']}")
            if status['issues']:
                for issue in status['issues']:
                    print(f"  - {issue}")
        
        if health_report['recommendations']:
            print("\nRecommendations:")
            for rec in health_report['recommendations']:
                print(f"  - {rec}")
        
        # Get cache metrics
        print("\n=== Cache Metrics ===")
        metrics = await cache_manager.get_cache_metrics()
        for cache_type, cache_metrics in metrics.items():
            print(f"{cache_type}: {cache_metrics.file_count} files, {cache_metrics.size_mb:.1f} MB")
        
        # Validate caches
        print("\n=== Cache Validation ===")
        validation_results = await cache_manager.validate_cache()
        for cache_type, results in validation_results.items():
            valid_count = sum(1 for r in results if r.is_valid)
            total_count = len(results)
            print(f"{cache_type}: {valid_count}/{total_count} files valid")
        
        # Clear cache using smart selective strategy
        print("\n=== Cache Clearing ===")
        clearing_results = await cache_manager.clear_cache("smart_selective")
        for cache_type, result in clearing_results.items():
            if result.files_removed > 0 or result.bytes_freed > 0:
                print(f"{cache_type}: Removed {result.files_removed} files, freed {result.bytes_freed} bytes")
            if result.errors:
                print(f"{cache_type} errors: {result.errors}")
        
    finally:
        await cache_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
