"""
OpenAI API Abstraction Layer for Amazon FBA Agent System v3.
Provides centralized LLM interaction with model routing, error handling, and retry logic.
"""

import asyncio
import json
import logging
import re
import time
from typing import Dict, List, Optional, Any, Union
from openai import OpenAI, AsyncOpenAI
from config import settings, OpenAIConfig

# Setup logging
log = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass


class ModelNotSupportedError(LLMServiceError):
    """Raised when a requested model is not supported."""
    pass


class APIKeyError(LLMServiceError):
    """Raised when API key is invalid or missing."""
    pass


class RateLimitError(LLMServiceError):
    """Raised when rate limit is exceeded."""
    pass


class LLMService:
    """
    Centralized OpenAI API service with model routing and error handling.
    
    Features:
    - Model-specific configuration and routing
    - Automatic retry with exponential backoff
    - Rate limiting and request tracking
    - Support for both sync and async operations
    - Temperature parameter compatibility checking
    - Comprehensive error handling and logging
    """
    
    def __init__(self, config: Optional[OpenAIConfig] = None):
        """Initialize LLM service with configuration."""
        self.config = config or settings.openai
        
        # Validate API keys
        if not self.config.api_key:
            raise APIKeyError("Primary OpenAI API key is required")
        
        # Initialize OpenAI clients
        self.sync_client = OpenAI(api_key=self.config.api_key)
        self.async_client = AsyncOpenAI(api_key=self.config.api_key)
        
        # Initialize secondary client for AI selector discovery if different key provided
        self.ai_selector_client = None
        self.ai_selector_async_client = None
        
        if self.config.ai_selector_api_key and self.config.ai_selector_api_key != self.config.api_key:
            self.ai_selector_client = OpenAI(api_key=self.config.ai_selector_api_key)
            self.ai_selector_async_client = AsyncOpenAI(api_key=self.config.ai_selector_api_key)
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        
        log.info(f"LLM Service initialized with models: {list(self.config.model_configs.keys())}")
    
    def _get_client_for_model(self, model: str, async_mode: bool = False) -> Union[OpenAI, AsyncOpenAI]:
        """Get the appropriate client for a specific model."""
        # Use AI selector client for AI selector discovery model
        if model == self.config.ai_selector_discovery_model and self.ai_selector_client:
            return self.ai_selector_async_client if async_mode else self.ai_selector_client
        
        # Use primary client for all other models
        return self.async_client if async_mode else self.sync_client
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        current_time = time.time()
        
        # Reset counter if window expired
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        # Check if we're over the limit
        if self.request_count >= self.config.requests_per_minute:
            sleep_time = 60 - (current_time - self.request_window_start)
            if sleep_time > 0:
                log.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
                self.request_window_start = time.time()
        
        self.request_count += 1
    
    def _prepare_api_params(self, model: str, **kwargs) -> Dict[str, Any]:
        """Prepare API parameters with model-specific configurations."""
        model_config = self.config.get_model_config(model)
        
        # Start with model defaults
        api_params = {
            "model": model,
            **model_config
        }
        
        # Remove internal configuration flags
        api_params.pop("supports_temperature", None)
        
        # Override with provided parameters
        api_params.update(kwargs)
        
        # Handle temperature parameter compatibility
        if "temperature" in api_params and not model_config.get("supports_temperature", True):
            log.debug(f"Removing temperature parameter for model {model} (not supported)")
            api_params.pop("temperature")
        
        return api_params
    
    def _make_sync_request(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make a synchronous OpenAI API request with retry logic."""
        max_retries = self.config.retry_attempts
        base_delay = self.config.retry_delay_seconds
        
        for attempt in range(max_retries):
            try:
                self._check_rate_limit()
                
                client = self._get_client_for_model(model, async_mode=False)
                api_params = self._prepare_api_params(model, **kwargs)
                
                log.debug(f"Making sync request to {model} with {len(messages)} messages (attempt {attempt + 1})")
                
                response = client.chat.completions.create(
                    messages=messages,
                    **api_params
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise LLMServiceError("Empty response from OpenAI API")
                
                log.debug(f"Received response from {model}: {len(content)} characters")
                return content
                
            except Exception as e:
                is_last_attempt = attempt == max_retries - 1
                
                log.error(f"OpenAI API request failed for model {model} (attempt {attempt + 1}): {e}")
                
                # Convert specific OpenAI errors to our custom exceptions
                error_message = str(e).lower()
                if "rate limit" in error_message:
                    if not is_last_attempt:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        log.warning(f"Rate limit hit, retrying after {delay} seconds")
                        time.sleep(delay)
                        continue
                    raise RateLimitError(f"Rate limit exceeded for model {model}: {e}")
                elif "api key" in error_message or "unauthorized" in error_message:
                    raise APIKeyError(f"API key error for model {model}: {e}")
                elif "model" in error_message and "not found" in error_message:
                    raise ModelNotSupportedError(f"Model {model} not supported: {e}")
                else:
                    if not is_last_attempt:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        log.warning(f"Request failed, retrying after {delay} seconds")
                        time.sleep(delay)
                        continue
                    raise LLMServiceError(f"API request failed for model {model}: {e}")
        
        # Should never reach here
        raise LLMServiceError(f"Max retries exceeded for model {model}")
    
    async def _make_async_request(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make an asynchronous OpenAI API request with retry logic."""
        max_retries = self.config.retry_attempts
        base_delay = self.config.retry_delay_seconds
        
        for attempt in range(max_retries):
            try:
                # Note: Rate limiting is simplified for async - in production might need async-aware implementation
                
                client = self._get_client_for_model(model, async_mode=True)
                api_params = self._prepare_api_params(model, **kwargs)
                
                log.debug(f"Making async request to {model} with {len(messages)} messages (attempt {attempt + 1})")
                
                response = await client.chat.completions.create(
                    messages=messages,
                    **api_params
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise LLMServiceError("Empty response from OpenAI API")
                
                log.debug(f"Received async response from {model}: {len(content)} characters")
                return content
                
            except Exception as e:
                is_last_attempt = attempt == max_retries - 1
                
                log.error(f"Async OpenAI API request failed for model {model} (attempt {attempt + 1}): {e}")
                
                # Convert specific OpenAI errors to our custom exceptions
                error_message = str(e).lower()
                if "rate limit" in error_message:
                    if not is_last_attempt:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        log.warning(f"Rate limit hit, retrying after {delay} seconds")
                        await asyncio.sleep(delay)
                        continue
                    raise RateLimitError(f"Rate limit exceeded for model {model}: {e}")
                elif "api key" in error_message or "unauthorized" in error_message:
                    raise APIKeyError(f"API key error for model {model}: {e}")
                elif "model" in error_message and "not found" in error_message:
                    raise ModelNotSupportedError(f"Model {model} not supported: {e}")
                else:
                    if not is_last_attempt:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        log.warning(f"Request failed, retrying after {delay} seconds")
                        await asyncio.sleep(delay)
                        continue
                    raise LLMServiceError(f"API request failed for model {model}: {e}")
        
        # Should never reach here
        raise LLMServiceError(f"Max retries exceeded for model {model}")
    
    # High-level methods for specific use cases
    
    def get_category_suggestions(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> List[str]:
        """Get AI category suggestions using the category suggestion model."""
        messages = history or []
        messages.append({"role": "user", "content": prompt})
        
        response_text = self._make_sync_request(
            model=self.config.category_suggestion_model,
            messages=messages
        )
        
        return self._parse_category_suggestions(response_text)
    
    async def get_category_suggestions_async(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> List[str]:
        """Get AI category suggestions asynchronously."""
        messages = history or []
        messages.append({"role": "user", "content": prompt})
        
        response_text = await self._make_async_request(
            model=self.config.category_suggestion_model,
            messages=messages
        )
        
        return self._parse_category_suggestions(response_text)
    
    def discover_selectors(self, html_content: str, context_url: str) -> Dict[str, Any]:
        """Discover CSS selectors using AI selector discovery model."""
        prompt = self._build_selector_discovery_prompt(html_content, context_url)
        
        messages = [{"role": "user", "content": prompt}]
        
        response_text = self._make_sync_request(
            model=self.config.ai_selector_discovery_model,
            messages=messages
        )
        
        return self._parse_selector_discovery_response(response_text)
    
    async def discover_selectors_async(self, html_content: str, context_url: str) -> Dict[str, Any]:
        """Discover CSS selectors asynchronously."""
        prompt = self._build_selector_discovery_prompt(html_content, context_url)
        
        messages = [{"role": "user", "content": prompt}]
        
        response_text = await self._make_async_request(
            model=self.config.ai_selector_discovery_model,
            messages=messages
        )
        
        return self._parse_selector_discovery_response(response_text)
    
    def chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> str:
        """Generic chat completion method."""
        model = model or self.config.category_suggestion_model
        return self._make_sync_request(model=model, messages=messages, **kwargs)
    
    async def chat_completion_async(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> str:
        """Generic async chat completion method."""
        model = model or self.config.category_suggestion_model
        return await self._make_async_request(model=model, messages=messages, **kwargs)
    
    # Helper methods for parsing responses
    
    def _parse_category_suggestions(self, response_text: str) -> List[str]:
        """Parse category suggestions from AI response."""
        try:
            # Try to parse as JSON first
            if response_text.strip().startswith('['):
                return json.loads(response_text)
            
            # Extract URLs from text response
            url_pattern = r'(/[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=%]*)'
            urls = re.findall(url_pattern, response_text)
            
            # Filter for reasonable category URLs
            category_urls = []
            for url in urls:
                if len(url) > 3 and '.html' in url or any(keyword in url.lower() for keyword in 
                    ['category', 'product', 'shop', 'collection', 'department']):
                    category_urls.append(url)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in category_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            return unique_urls[:10]  # Limit to top 10
            
        except Exception as e:
            log.error(f"Failed to parse category suggestions: {e}")
            return []
    
    def _build_selector_discovery_prompt(self, html_content: str, context_url: str) -> str:
        """Build prompt for CSS selector discovery."""
        # Truncate HTML if too long
        max_html_length = 8000
        if len(html_content) > max_html_length:
            html_content = html_content[:max_html_length] + "... [truncated]"
        
        return f"""
Analyze this HTML from {context_url} and discover CSS selectors for product elements.

HTML Content:
{html_content}

Please provide JSON response with:
{{
    "product_selectors": ["selector1", "selector2"],
    "price_selectors": ["price_selector1", "price_selector2"],
    "title_selectors": ["title_selector1", "title_selector2"],
    "image_selectors": ["img_selector1", "img_selector2"],
    "ean_selectors": ["ean_selector1", "ean_selector2"],
    "pagination_selectors": ["next_page_selector"],
    "confidence": 0.85
}}

Focus on finding reliable selectors for ecommerce product listing pages.
"""
    
    def _parse_selector_discovery_response(self, response_text: str) -> Dict[str, Any]:
        """Parse selector discovery response."""
        try:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find JSON directly in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")
            
            parsed_response = json.loads(json_text)
            
            # Validate required fields
            required_fields = ["product_selectors", "price_selectors", "title_selectors"]
            for field in required_fields:
                if field not in parsed_response:
                    parsed_response[field] = []
            
            # Set default confidence if not provided
            if "confidence" not in parsed_response:
                parsed_response["confidence"] = 0.5
            
            return parsed_response
            
        except Exception as e:
            log.error(f"Failed to parse selector discovery response: {e}")
            return {
                "product_selectors": [],
                "price_selectors": [],
                "title_selectors": [],
                "image_selectors": [],
                "ean_selectors": [],
                "pagination_selectors": [],
                "confidence": 0.0
            }
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return list(self.config.model_configs.keys())
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        return self.config.get_model_config(model)


# Global service instance (will be initialized when API key is available)
llm_service = None


# Initialize global service when needed
def _get_service() -> LLMService:
    """Get or initialize the global LLM service."""
    global llm_service
    if llm_service is None:
        llm_service = LLMService()
    return llm_service


# Convenience functions for backward compatibility
def get_category_suggestions(prompt: str, history: Optional[List[Dict[str, str]]] = None) -> List[str]:
    """Get category suggestions (sync)."""
    return _get_service().get_category_suggestions(prompt, history)


async def get_category_suggestions_async(prompt: str, history: Optional[List[Dict[str, str]]] = None) -> List[str]:
    """Get category suggestions (async)."""
    return await _get_service().get_category_suggestions_async(prompt, history)


def discover_selectors(html_content: str, context_url: str) -> Dict[str, Any]:
    """Discover CSS selectors (sync)."""
    return _get_service().discover_selectors(html_content, context_url)


async def discover_selectors_async(html_content: str, context_url: str) -> Dict[str, Any]:
    """Discover CSS selectors (async)."""
    return await _get_service().discover_selectors_async(html_content, context_url)


if __name__ == "__main__":
    # Test the LLM service
    import os
    
    print("🤖 Testing LLM Service")
    print("=" * 30)
    
    # Set test environment variables
    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["OPENAI_AI_SELECTOR_API_KEY"] = "test-key-2"
    
    try:
        # This will fail with real API calls, but tests the initialization
        service = LLMService()
        print(f"✅ Service initialized successfully")
        print(f"Available models: {service.get_available_models()}")
        
        for model in service.get_available_models():
            info = service.get_model_info(model)
            print(f"  {model}: {info}")
            
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")