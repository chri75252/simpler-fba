"""
Configuration management for Amazon FBA Agent System v3.
Centralizes all configuration parameters with type safety and environment variable support.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OpenAIConfig:
    """OpenAI API configuration with model-specific settings."""
    api_key: str = "sk-4ntHqPkVpIoPyriiNcG8n0Wc_uQLbuCRChROpND4GbT3BlbkFJenqlgCSAIW6gipNFKE2MrqjvBMhzm0o4rxYOf4m9AA"
    
    # Model configurations for different use cases
    category_suggestion_model: str = "gpt-4o-mini-2024-07-18"
    ai_selector_discovery_model: str = "gpt-4.1-mini-2025-04-14"
    fallback_model: str = "gpt-4o-mini"
    
    # Model-specific parameters
    model_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "gpt-4o-mini-2024-07-18": {
            "temperature": 0.1,
            "max_tokens": 1200,
            "supports_temperature": True
        },
        "gpt-4.1-mini-2025-04-14": {
            "max_tokens": 1500,
            "supports_temperature": True
        },
        "gpt-4o-mini": {
            "temperature": 0.1,
            "max_tokens": 1200,
            "supports_temperature": True
        }
    })
    
    # Rate limiting
    requests_per_minute: int = 60
    retry_attempts: int = 3
    retry_delay_seconds: int = 2
    
    # Fallback API keys for different scripts
    ai_selector_api_key: str = "sk-A4Ey6Q3g_qjwbBwb0qcpfxyQ858Xa39d--IBJA46uHT3BlbkFJw34Wqh-Pc1TupmpD3OCj_Av9ibIcQUV-Q62b4WetIA"
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model."""
        return self.model_configs.get(model_name, self.model_configs[self.fallback_model])


@dataclass
class SupplierConfig:
    """Supplier-specific configuration."""
    name: str
    base_url: str
    
    # Scraping parameters
    product_list_limit: int = 64
    rate_limit_delay: float = 2.0
    requests_per_minute: int = 30
    max_pages_per_category: int = 10
    
    # Navigation timeouts
    navigation_timeout_ms: int = 60000
    page_load_timeout_ms: int = 10000
    stabilize_wait_seconds: int = 10
    
    # Default category URLs
    category_urls: List[str] = field(default_factory=list)
    pagination_pattern: str = "?p={page_num}"


@dataclass
class PriceRangeConfig:
    """Price range configuration for multi-phase processing."""
    # Phase 1: Low price range
    phase1_min_price: float = 0.1
    phase1_max_price: float = 10.0
    
    # Phase 2: Medium price range  
    phase2_min_price: float = 10.0
    phase2_max_price: float = 20.0
    
    # Phase transition settings
    phase_transition_threshold: int = 5  # Number of products above threshold to trigger phase change
    price_monitoring_window: int = 10   # Number of recent products to monitor
    
    @property
    def min_price(self) -> float:
        """Get minimum price (phase 1 default)."""
        return self.phase1_min_price
    
    @property
    def max_price(self) -> float:
        """Get maximum price (phase 2 default)."""
        return self.phase2_max_price


@dataclass
class ProcessingLimitsConfig:
    """Processing limits for unlimited vs limited runs."""
    # Core processing limits (0 = unlimited)
    max_products_per_category: int = 0
    max_analyzed_products: int = 0
    max_products_per_cycle: int = 0
    max_products_per_run: int = 0
    
    # Category limits
    max_categories_per_cycle: int = 3
    min_products_per_category: int = 2
    
    def is_unlimited_processing(self) -> bool:
        """Check if system is configured for unlimited processing."""
        return (self.max_products_per_category == 0 and 
                self.max_analyzed_products == 0 and 
                self.max_products_per_cycle == 0)


@dataclass
class AmazonConfig:
    """Amazon marketplace and FBA configuration."""
    marketplace: str = "amazon.co.uk"
    currency: str = "GBP"
    vat_rate: float = 0.2
    
    # FBA fees
    referral_fee_rate: float = 0.15
    fulfillment_fee_minimum: float = 2.41
    storage_fee_per_cubic_foot: float = 0.75
    prep_house_fixed_fee: float = 0.55
    
    # Analysis criteria
    min_roi_percent: float = 35.0
    min_profit_per_unit: float = 3.0
    min_rating: float = 4.0
    min_reviews: int = 50
    max_sales_rank: int = 150000


@dataclass
class ChromeConfig:
    """Chrome browser configuration."""
    debug_port: int = 9222
    headless: bool = False
    extensions: List[str] = field(default_factory=lambda: ["Keepa", "SellerAmp"])
    extension_data_wait: int = 25


@dataclass
class CacheConfig:
    """Caching and storage configuration."""
    enabled: bool = True
    ttl_hours: int = 336  # 14 days
    max_size_mb: int = 500
    
    # Directory paths
    base_output_dir: str = "OUTPUTS/FBA_ANALYSIS"
    supplier_cache_dir: str = "OUTPUTS/cached_products"
    amazon_cache_dir: str = "OUTPUTS/FBA_ANALYSIS/amazon_cache"
    ai_category_cache_dir: str = "OUTPUTS/FBA_ANALYSIS/ai_category_cache"
    linking_map_dir: str = "OUTPUTS/FBA_ANALYSIS/Linking map"
    emergency_backup_dir: str = "OUTPUTS/cached_products/emergency_backups"
    
    # Selective clearing options
    preserve_analyzed_products: bool = True
    preserve_ai_categories: bool = True
    preserve_linking_map: bool = True
    clear_unanalyzed_only: bool = False
    clear_failed_extractions: bool = True


@dataclass
class MonitoringConfig:
    """System monitoring and metrics configuration."""
    enabled: bool = True
    metrics_interval: int = 60
    health_check_interval: int = 300
    log_level: str = "INFO"
    
    # Dashboard paths
    dashboard_dir: str = "DASHBOARD"
    metrics_summary_file: str = "DASHBOARD/metrics_summary.json"
    live_dashboard_file: str = "DASHBOARD/live_dashboard.txt"
    
    # Alert thresholds
    cpu_percent_threshold: int = 80
    memory_percent_threshold: int = 85
    error_rate_per_hour_threshold: int = 10


@dataclass
class PerformanceConfig:
    """Performance and optimization settings."""
    # Concurrency
    max_concurrent_requests: int = 10
    
    # Timeouts
    request_timeout_seconds: int = 30
    http_request_timeout_seconds: int = 15
    sitemap_timeout_seconds: int = 10
    
    # Retries
    retry_attempts: int = 3
    retry_delay_seconds: int = 2
    
    # Batching
    batch_size: int = 50
    ai_batch_size: int = 5
    
    # Rate limiting
    rate_limit_delay: float = 3.0
    batch_delay: float = 15.0
    
    # Navigation timeouts
    navigation_timeout_ms: int = 60000
    search_input_timeout_ms: int = 5000
    results_wait_timeout_ms: int = 15000
    selector_wait_timeout_ms: int = 20000
    page_load_timeout_ms: int = 10000
    
    # Matching thresholds
    title_similarity_threshold: float = 0.25
    brand_similarity_threshold: float = 0.85
    high_title_similarity_threshold: float = 0.75
    medium_title_similarity_threshold: float = 0.5
    confidence_high_threshold: float = 0.75
    confidence_medium_threshold: float = 0.45


@dataclass
class SecurityConfig:
    """Security and authentication configuration."""
    encryption_enabled: bool = False
    api_key_rotation_days: int = 90
    session_timeout_minutes: int = 60
    max_login_attempts: int = 3


@dataclass
class SystemConfig:
    """Main system configuration class."""
    # System metadata
    name: str = "Amazon FBA Agent System"
    version: str = "3.0.0"
    environment: str = "production"
    
    # Feature flags
    test_mode: bool = False
    clear_cache: bool = False
    selective_cache_clear: bool = False
    force_ai_scraping: bool = True
    force_ai_category_suggestion: bool = True
    bypass_ai_scraping: bool = False
    enable_supplier_parser: bool = False
    
    # Configuration sections
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    price_ranges: PriceRangeConfig = field(default_factory=PriceRangeConfig)
    processing_limits: ProcessingLimitsConfig = field(default_factory=ProcessingLimitsConfig)
    amazon: AmazonConfig = field(default_factory=AmazonConfig)
    chrome: ChromeConfig = field(default_factory=ChromeConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Supplier configurations
    suppliers: Dict[str, SupplierConfig] = field(default_factory=lambda: {
        "clearance-king": SupplierConfig(
            name="Clearance King UK",
            base_url="https://www.clearance-king.co.uk",
            category_urls=[
                "/pound-lines.html",
                "/household.html", 
                "/health-beauty.html",
                "/gifts-toys.html",
                "/stationery-crafts.html",
                "/pets.html",
                "/baby-kids.html",
                "/clearance-lines.html"
            ]
        )
    })
    
    # Default supplier settings
    default_supplier_url: str = "https://www.clearance-king.co.uk"
    default_supplier_name: str = "clearance-king.co.uk"
    
    def get_supplier_config(self, supplier_name: str) -> Optional[SupplierConfig]:
        """Get configuration for a specific supplier."""
        return self.suppliers.get(supplier_name)
    
    def validate_configuration(self) -> List[str]:
        """Validate that required configuration is set."""
        issues = []
        
        if not self.openai.api_key or len(self.openai.api_key) < 10:
            issues.append("OpenAI API key is missing or invalid")
            
        if not self.openai.ai_selector_api_key or len(self.openai.ai_selector_api_key) < 10:
            issues.append("OpenAI AI Selector API key is missing or invalid")
            
        return issues


# Global settings instance
settings = SystemConfig()


# Utility functions for backward compatibility
def get_openai_config() -> OpenAIConfig:
    """Get OpenAI configuration."""
    return settings.openai


def get_price_ranges() -> PriceRangeConfig:
    """Get price range configuration."""
    return settings.price_ranges


def get_processing_limits() -> ProcessingLimitsConfig:
    """Get processing limits configuration."""
    return settings.processing_limits


def get_supplier_config(supplier_name: str = None) -> SupplierConfig:
    """Get supplier configuration."""
    if supplier_name:
        config = settings.get_supplier_config(supplier_name)
        if config:
            return config
    
    # Return default clearance-king config
    return settings.suppliers["clearance-king"]


def validate_configuration() -> bool:
    """Validate the complete configuration."""
    issues = settings.validate_configuration()
    
    if issues:
        print(f"❌ Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("✅ Configuration validation passed")
    return True


if __name__ == "__main__":
    # Test configuration loading
    print("🔧 Amazon FBA Agent System v3 Configuration")
    print("=" * 50)
    
    print(f"System: {settings.name} v{settings.version}")
    print(f"Environment: {settings.environment}")
    print(f"Test Mode: {settings.test_mode}")
    print(f"Unlimited Processing: {settings.processing_limits.is_unlimited_processing()}")
    
    print(f"\n📊 Price Ranges:")
    print(f"Phase 1: £{settings.price_ranges.phase1_min_price} - £{settings.price_ranges.phase1_max_price}")
    print(f"Phase 2: £{settings.price_ranges.phase2_min_price} - £{settings.price_ranges.phase2_max_price}")
    print(f"Current: £{settings.price_ranges.min_price} - £{settings.price_ranges.max_price}")
    
    print(f"\n🤖 OpenAI Models:")
    print(f"Category Suggestions: {settings.openai.category_suggestion_model}")
    print(f"AI Selector Discovery: {settings.openai.ai_selector_discovery_model}")
    
    print(f"\n🏪 Suppliers:")
    for name, supplier in settings.suppliers.items():
        print(f"  {name}: {supplier.name} ({supplier.base_url})")
    
    # Validate configuration
    print(f"\n🔍 Configuration Validation:")
    validate_configuration()