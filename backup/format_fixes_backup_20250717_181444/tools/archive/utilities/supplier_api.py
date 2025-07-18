"""
Supplier API Handler with integrated rate limiting and retry logic
"""
import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

log = logging.getLogger(__name__)

class RateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, rate: int, per: float, burst: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed
            per: Time period in seconds
            burst: Maximum burst size (defaults to rate)
        """
        self.rate = rate
        self.per = per
        self.burst = burst or rate
        self.tokens = self.burst
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self.lock:
            while self.tokens <= 0:
                await self._refill()
                if self.tokens <= 0:
                    sleep_time = self.per / self.rate
                    await asyncio.sleep(sleep_time)
            
            self.tokens -= 1
            
    async def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(
            self.burst,
            self.tokens + (elapsed * self.rate / self.per)
        )
        self.last_update = now

class SupplierAPIHandler:
    """
    Unified handler for supplier API interactions with rate limiting.
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.api_configs: Dict[str, Dict[str, Any]] = {}
        self.retry_config = {
            'max_retries': 3,
            'initial_delay': 1.0,
            'backoff_factor': 2.0,
            'max_delay': 60.0
        }
        self._load_api_configs()
        
    def _load_api_configs(self):
        """Load API configurations for different suppliers."""
        # This would load from config files in production
        self.api_configs = {
            'clearance-king': {
                'base_url': 'https://api.clearance-king.co.uk',
                'auth_type': 'bearer',
                'rate_limit': {'rate': 60, 'per': 60, 'burst': 10},
                'timeout': 30,
                'headers': {
                    'Accept': 'application/json',
                    'User-Agent': 'Amazon-FBA-Agent/1.0'
                }
            },
            'wholesale-supplier': {
                'base_url': 'https://api.wholesale-supplier.com',
                'auth_type': 'api_key',
                'rate_limit': {'rate': 100, 'per': 60, 'burst': 20},
                'timeout': 45,
                'headers': {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            }
        }
        
        # Initialize rate limiters
        for supplier_id, config in self.api_configs.items():
            rl_config = config.get('rate_limit', {'rate': 60, 'per': 60})
            self.rate_limiters[supplier_id] = RateLimiter(**rl_config)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def fetch_data(self, 
                        supplier_id: str, 
                        endpoint: str, 
                        method: str = 'GET',
                        params: Optional[Dict[str, Any]] = None,
                        data: Optional[Dict[str, Any]] = None,
                        auth_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch data from supplier API with rate limiting and retry logic.
        
        Args:
            supplier_id: Supplier identifier
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            data: Request body data
            auth_token: Authentication token
            
        Returns:
            API response data
        """
        config = self.api_configs.get(supplier_id)
        if not config:
            raise ValueError(f"No API configuration for supplier: {supplier_id}")
            
        # Rate limiting
        rate_limiter = self.rate_limiters.get(supplier_id)
        if rate_limiter:
            await rate_limiter.acquire()
            
        # Prepare request
        url = f"{config['base_url']}/{endpoint.lstrip('/')}"
        headers = config.get('headers', {}).copy()
        
        # Add authentication
        if auth_token and config.get('auth_type') == 'bearer':
            headers['Authorization'] = f'Bearer {auth_token}'
        elif auth_token and config.get('auth_type') == 'api_key':
            headers['X-API-Key'] = auth_token
            
        # Execute with retry logic
        return await self._execute_with_retry(
            url=url,
            method=method,
            headers=headers,
            params=params,
            json=data,
            timeout=config.get('timeout', 30),
            supplier_id=supplier_id
        )
    
    async def _execute_with_retry(self, **kwargs) -> Dict[str, Any]:
        """Execute request with exponential backoff retry."""
        supplier_id = kwargs.pop('supplier_id', 'unknown')
        session = await self._get_session()
        
        last_error = None
        for attempt in range(self.retry_config['max_retries']):
            try:
                async with session.request(**kwargs) as response:
                    # Check for rate limit headers
                    self._update_rate_limits(response.headers, supplier_id)
                    
                    if response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', 60))
                        log.warning(f"Rate limited by {supplier_id}. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < self.retry_config['max_retries'] - 1:
                    delay = min(
                        self.retry_config['initial_delay'] * (self.retry_config['backoff_factor'] ** attempt),
                        self.retry_config['max_delay']
                    )
                    log.warning(f"Request failed (attempt {attempt + 1}): {e}. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    log.error(f"Request failed after {self.retry_config['max_retries']} attempts: {e}")
                    
        raise last_error or Exception("Request failed")
    
    def _update_rate_limits(self, headers: Dict[str, str], supplier_id: str):
        """Update rate limits based on response headers."""
        # Common rate limit headers
        remaining = headers.get('X-RateLimit-Remaining') or headers.get('X-Rate-Limit-Remaining')
        reset = headers.get('X-RateLimit-Reset') or headers.get('X-Rate-Limit-Reset')
        
        if remaining and reset:
            try:
                remaining_requests = int(remaining)
                reset_timestamp = int(reset)
                
                # Log if getting close to limit
                if remaining_requests < 10:
                    reset_time = datetime.fromtimestamp(reset_timestamp)
                    log.warning(f"Low rate limit for {supplier_id}: {remaining_requests} requests remaining until {reset_time}")
                    
            except (ValueError, TypeError):
                pass
                
    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

# Specific supplier API implementations
class ClearanceKingAPI(SupplierAPIHandler):
    """Clearance King specific API implementation."""
    
    async def get_products(self, category_id: str, page: int = 1, auth_token: str = None) -> Dict[str, Any]:
        """Get products from a specific category."""
        return await self.fetch_data(
            supplier_id='clearance-king',
            endpoint=f'/categories/{category_id}/products',
            params={'page': page, 'limit': 50},
            auth_token=auth_token
        )
    
    async def get_product_details(self, product_id: str, auth_token: str = None) -> Dict[str, Any]:
        """Get detailed information for a specific product."""
        return await self.fetch_data(
            supplier_id='clearance-king',
            endpoint=f'/products/{product_id}',
            auth_token=auth_token
        )
    
    async def get_inventory(self, product_ids: List[str], auth_token: str = None) -> Dict[str, Any]:
        """Get inventory levels for multiple products."""
        return await self.fetch_data(
            supplier_id='clearance-king',
            endpoint='/inventory/batch',
            method='POST',
            data={'product_ids': product_ids},
            auth_token=auth_token
        )