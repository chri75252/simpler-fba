"""
Currency conversion module with caching and fallback support
"""
import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path

log = logging.getLogger(__name__)

class CurrencyConverter:
    """
    Currency converter with multiple API fallbacks and caching.
    """
    
    def __init__(self, cache_dir: str = "cache/currency"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rates_cache: Dict[str, Dict[str, float]] = {}
        self.cache_ttl = timedelta(hours=336)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API configurations (in order of preference)
        self.api_configs = [
            {
                'name': 'exchangerate-api',
                'url': 'https://api.exchangerate-api.com/v4/latest/{base}',
                'free_tier': True,
                'parse_func': self._parse_exchangerate_api
            },
            {
                'name': 'fixer',
                'url': 'http://data.fixer.io/api/latest?access_key={api_key}&base={base}',
                'free_tier': True,
                'requires_key': True,
                'parse_func': self._parse_fixer
            },
            {
                'name': 'currencyapi',
                'url': 'https://api.currencyapi.com/v3/latest?apikey={api_key}&base_currency={base}',
                'free_tier': True,
                'requires_key': True,
                'parse_func': self._parse_currencyapi
            }
        ]
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'GBP')
            
        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount
            
        # Check cache first
        rate = await self._get_exchange_rate(from_currency, to_currency)
        if rate is None:
            log.error(f"Could not get exchange rate for {from_currency} to {to_currency}")
            return amount  # Return unchanged as fallback
            
        return amount * rate
    
    async def _get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get exchange rate with caching and fallbacks."""
        # Check memory cache
        cache_key = f"{from_currency}_{to_currency}"
        if cache_key in self.rates_cache:
            cached_data = self.rates_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['rate']
        
        # Check disk cache
        cached_rate = self._load_from_disk_cache(from_currency, to_currency)
        if cached_rate is not None:
            return cached_rate
            
        # Fetch fresh rates
        rates = await self._fetch_rates(from_currency)
        if rates and to_currency in rates:
            rate = rates[to_currency]
            
            # Cache the rate
            self._save_to_cache(from_currency, to_currency, rate)
            
            return rate
            
        return None
    
    async def _fetch_rates(self, base_currency: str) -> Optional[Dict[str, float]]:
        """Fetch rates from APIs with fallbacks."""
        session = await self._get_session()
        
        for api_config in self.api_configs:
            try:
                # Skip APIs that require keys if not configured
                if api_config.get('requires_key') and not self._get_api_key(api_config['name']):
                    continue
                    
                url = self._build_api_url(api_config, base_currency)
                if not url:
                    continue
                    
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = api_config['parse_func'](data, base_currency)
                        if rates:
                            log.info(f"Successfully fetched rates from {api_config['name']}")
                            return rates
                            
            except Exception as e:
                log.warning(f"Failed to fetch from {api_config['name']}: {e}")
                continue
                
        log.error(f"All currency APIs failed for base currency {base_currency}")
        return None
    
    def _build_api_url(self, api_config: Dict[str, Any], base_currency: str) -> Optional[str]:
        """Build API URL with necessary parameters."""
        url = api_config['url']
        
        if api_config.get('requires_key'):
            api_key = self._get_api_key(api_config['name'])
            if not api_key:
                return None
            url = url.format(api_key=api_key, base=base_currency)
        else:
            url = url.format(base=base_currency)
            
        return url
    
    def _get_api_key(self, api_name: str) -> Optional[str]:
        """Get API key from environment or config."""
        import os
        return os.getenv(f"{api_name.upper()}_API_KEY")
    
    def _parse_exchangerate_api(self, data: Dict[str, Any], base_currency: str) -> Dict[str, float]:
        """Parse exchangerate-api.com response."""
        return data.get('rates', {})
    
    def _parse_fixer(self, data: Dict[str, Any], base_currency: str) -> Dict[str, float]:
        """Parse fixer.io response."""
        if data.get('success'):
            return data.get('rates', {})
        return {}
    
    def _parse_currencyapi(self, data: Dict[str, Any], base_currency: str) -> Dict[str, float]:
        """Parse currencyapi.com response."""
        rates = {}
        currency_data = data.get('data', {})
        for currency, info in currency_data.items():
            if isinstance(info, dict) and 'value' in info:
                rates[currency] = info['value']
        return rates
    
    def _save_to_cache(self, from_currency: str, to_currency: str, rate: float):
        """Save rate to both memory and disk cache."""
        # Memory cache
        cache_key = f"{from_currency}_{to_currency}"
        self.rates_cache[cache_key] = {
            'rate': rate,
            'timestamp': datetime.now()
        }
        
        # Disk cache
        cache_file = self.cache_dir / f"{from_currency}_rates.json"
        try:
            # Load existing rates
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    rates_data = json.load(f)
            else:
                rates_data = {}
                
            # Update rates
            rates_data[to_currency] = {
                'rate': rate,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save back
            with open(cache_file, 'w') as f:
                json.dump(rates_data, f, indent=2)
                
        except Exception as e:
            log.warning(f"Failed to save to disk cache: {e}")
    
    def _load_from_disk_cache(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Load rate from disk cache if available and not expired."""
        cache_file = self.cache_dir / f"{from_currency}_rates.json"
        
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                rates_data = json.load(f)
                
            if to_currency in rates_data:
                rate_info = rates_data[to_currency]
                timestamp = datetime.fromisoformat(rate_info['timestamp'])
                
                if datetime.now() - timestamp < self.cache_ttl:
                    return rate_info['rate']
                    
        except Exception as e:
            log.warning(f"Failed to load from disk cache: {e}")
            
        return None
    
    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()