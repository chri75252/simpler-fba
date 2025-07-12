#!/usr/bin/env python3
"""
Vision Discovery Engine - AI-Powered Element Detection
======================================================

This engine uses GPT-4 Vision API to automatically discover login forms,
product selectors, and navigation elements on any supplier website.

INTEGRATION:
    - Called by supplier_script_generator.py for automated setup
    - Used by LangGraph workflow for "once per supplier" discovery
    - Provides fallback when heuristic selectors fail

CAPABILITIES:
    - Login form element detection
    - Product listing selector discovery
    - Navigation pattern recognition
    - Price extraction optimization
    - EAN/Barcode pattern detection
"""

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import openai
from playwright.async_api import Page

# Configure logging with base64 image data filter
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class Base64ImageFilter(logging.Filter):
    """Filter to prevent massive base64 image data from being logged"""
    
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Check if log message contains base64 image data patterns
            if 'data:image/' in record.msg and len(record.msg) > 10000:
                # Replace base64 data with truncated version
                import re
                record.msg = re.sub(
                    r'data:image/[^,]+,([A-Za-z0-9+/]{100})[A-Za-z0-9+/=]*',
                    r'data:image/png;base64,\1...[TRUNCATED_BASE64_IMAGE_DATA]',
                    record.msg
                )
            # Also filter OpenAI request data containing base64
            elif 'image_url' in record.msg and len(record.msg) > 10000:
                record.msg = re.sub(
                    r'"url":\s*"data:image/[^"]+',
                    '"url": "data:image/png;base64,[TRUNCATED_BASE64_IMAGE_DATA]"',
                    record.msg
                )
        return True

# Apply filter to prevent base64 image logging issues
base64_filter = Base64ImageFilter()
logging.getLogger('openai._base_client').addFilter(base64_filter)
logging.getLogger().addFilter(base64_filter)

class VisionDiscoveryEngine:
    """AI-powered element discovery using GPT-4 Vision with multimodal analysis"""
    
    def __init__(self, page: Page):
        self.page = page
        # Use environment variable for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = openai.OpenAI(api_key=api_key)
        
        # Enhanced discovery configuration
        self.model = "gpt-4.1-mini-2025-04-14"  # Updated model for supplier package generation
        self.max_tokens = 4000
        self.temperature = 0.1  # Low for consistent results
        
        # Token consumption safeguards
        self.MAX_HTML_CHARS = 15000   # 🚨 REDUCED: Hard limit for HTML content sent to AI (90% reduction)
        self.MAX_SITEMAP_URLS = 200   # Limit sitemap processing
        
        log.info("🔍 Enhanced Vision Discovery Engine initialized with multimodal AI capabilities")
    
    def _prune_html_for_ai(self, html_content: str) -> str:
        """
        Aggressively prune HTML content to focus only on essential form/product elements.
        Removes script, style, svg tags and large navigation sections.
        """
        log.debug("🧹 Aggressively pruning HTML content for AI analysis...")
        
        # Remove script, style, and svg tags completely
        html_content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<svg\b[^<]*(?:(?!<\/svg>)<[^<]*)*<\/svg>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove comments
        html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
        
        # 🚨 NEW: Remove massive navigation menus and repeated elements
        html_content = re.sub(r'<nav\b[^<]*(?:(?!<\/nav>)<[^<]*)*<\/nav>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<ul\s+class="[^"]*menu[^"]*"[^<]*(?:(?!<\/ul>)<[^<]*)*<\/ul>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<div\s+class="[^"]*menu[^"]*"[^<]*(?:(?!<\/div>)<[^<]*)*<\/div>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Compress whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        
        # Enforce character limit with warning
        if len(html_content) > self.MAX_HTML_CHARS:
            log.warning(f"HTML content for AI analysis was truncated to {self.MAX_HTML_CHARS} characters. "
                       f"The original size was {len(html_content)}. AI context may be incomplete.")
            html_content = html_content[:self.MAX_HTML_CHARS]
            
        log.debug(f"✅ HTML aggressively pruned to {len(html_content)} characters")
        return html_content
    
    async def discover_login_elements(self) -> Optional[Dict[str, str]]:
        """
        Enhanced multimodal login discovery using both visual and HTML analysis
        
        Returns:
            dict: Login configuration with selectors
        """
        try:
            log.info("🔐 Starting enhanced multimodal login discovery...")
            
            # Step 1: Extract HTML content and try local analysis first
            log.info("📄 Extracting page HTML content...")
            html_content = await self.page.content()
            
            # Try local HTML analysis first (NO API CALLS)
            log.info("🔍 Attempting local HTML analysis first...")
            login_config = await self._analyze_login_form_locally(html_content)
            
            if login_config:
                log.info("✅ Login elements discovered via local analysis")
                
                # Validate discovered selectors on actual page
                log.info("🔍 Validating locally discovered selectors...")
                validated_config = await self._validate_login_selectors(login_config)
                
                if validated_config:
                    log.info("✅ Local login selectors validated successfully")
                    return validated_config
                else:
                    log.warning("⚠️ Local selectors failed validation, trying multimodal analysis...")
            
            # Fallback to multimodal analysis if local fails
            log.info("🧠 Falling back to multimodal AI analysis...")
            
            # Prune HTML for AI analysis
            pruned_html = self._prune_html_for_ai(html_content)
            log.info(f"📊 HTML content processed: {len(pruned_html)} characters after pruning")
            
            # Take screenshot for visual analysis
            log.info("📸 Capturing page screenshot...")
            screenshot_data = await self._capture_page_screenshot()
            
            if not screenshot_data:
                log.error("❌ Failed to capture screenshot for visual analysis")
                return None
            
            # Multimodal AI analysis combining HTML and visual data
            log.info("🧠 Performing multimodal AI analysis for login elements...")
            login_config = await self._analyze_login_form_multimodal(screenshot_data, pruned_html)
            
            if login_config:
                log.info("✅ Login elements discovered successfully via multimodal analysis")
                
                # Validate discovered selectors on actual page
                log.info("🔍 Validating discovered selectors...")
                validated_config = await self._validate_login_selectors(login_config)
                
                if validated_config:
                    log.info("✅ Login selectors validated successfully")
                    return validated_config
                else:
                    log.warning("⚠️ Discovered selectors failed validation")
            
            # Fallback to heuristic discovery
            log.info("🔄 Falling back to heuristic discovery...")
            return await self._heuristic_login_discovery()
            
        except Exception as e:
            log.error(f"❌ Login discovery failed: {e}")
            return None
    
    async def _analyze_login_form_locally(self, page_html: str) -> Optional[Dict[str, str]]:
        """
        Analyze login form locally by saving HTML to file and searching for selectors
        NO API CALLS - purely local analysis
        """
        try:
            import re
            import os
            from datetime import datetime
            
            log.info("🔍 Performing local HTML analysis for login selectors...")
            
            # Save full HTML to file for analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = f"logs/debug/login_html_analysis_{timestamp}.html"
            
            os.makedirs("logs/debug", exist_ok=True)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            log.info(f"📄 Saved HTML to: {html_file}")
            
            # Search for login URLs first
            login_urls = []
            url_patterns = [
                r'href="[^"]*login[^"]*"',
                r'href="[^"]*account[^"]*"',
                r'href="[^"]*signin[^"]*"',
                r'href="[^"]*customer[^"]*"'
            ]
            
            for pattern in url_patterns:
                matches = re.findall(pattern, page_html, re.IGNORECASE)
                for match in matches:
                    url = match.split('"')[1]
                    if url not in login_urls:
                        login_urls.append(url)
            
            log.info(f"🔗 Found potential login URLs: {login_urls}")
            
            # Search for form elements with specific patterns
            selectors = {}
            
            # Email/Username selector patterns
            email_patterns = [
                r'<input[^>]*id="email"[^>]*>',
                r'<input[^>]*name="email"[^>]*>',
                r'<input[^>]*type="email"[^>]*>',
                r'<input[^>]*id="username"[^>]*>',
                r'<input[^>]*name="username"[^>]*>',
                r'<input[^>]*placeholder="[^"]*email[^"]*"[^>]*>',
                r'<input[^>]*class="[^"]*email[^"]*"[^>]*>'
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, page_html, re.IGNORECASE)
                if matches:
                    # Extract the most specific selector from the first match
                    match = matches[0]
                    if 'id=' in match:
                        id_match = re.search(r'id="([^"]*)"', match)
                        if id_match:
                            selectors['email_selector'] = f"#{id_match.group(1)}"
                            break
                    elif 'name=' in match:
                        name_match = re.search(r'name="([^"]*)"', match)
                        if name_match:
                            selectors['email_selector'] = f"input[name='{name_match.group(1)}']"
                            break
                    elif 'type="email"' in match:
                        selectors['email_selector'] = 'input[type="email"]'
                        break
            
            # Password selector patterns
            password_patterns = [
                r'<input[^>]*id="password"[^>]*>',
                r'<input[^>]*id="pass"[^>]*>',
                r'<input[^>]*name="password"[^>]*>',
                r'<input[^>]*name="pass"[^>]*>',
                r'<input[^>]*type="password"[^>]*>',
                r'<input[^>]*placeholder="[^"]*password[^"]*"[^>]*>'
            ]
            
            for pattern in password_patterns:
                matches = re.findall(pattern, page_html, re.IGNORECASE)
                if matches:
                    match = matches[0]
                    if 'id=' in match:
                        id_match = re.search(r'id="([^"]*)"', match)
                        if id_match:
                            selectors['password_selector'] = f"#{id_match.group(1)}"
                            break
                    elif 'name=' in match:
                        name_match = re.search(r'name="([^"]*)"', match)
                        if name_match:
                            selectors['password_selector'] = f"input[name='{name_match.group(1)}']"
                            break
                    elif 'type="password"' in match:
                        selectors['password_selector'] = 'input[type="password"]'
                        break
            
            # Submit button patterns
            submit_patterns = [
                r'<button[^>]*id="[^"]*login[^"]*"[^>]*>',
                r'<button[^>]*id="[^"]*submit[^"]*"[^>]*>',
                r'<button[^>]*type="submit"[^>]*>',
                r'<input[^>]*type="submit"[^>]*>',
                r'<button[^>]*class="[^"]*login[^"]*"[^>]*>',
                r'<button[^>]*class="[^"]*submit[^"]*"[^>]*>',
                r'<button[^>]*>[\s]*[^<]*login[^<]*</button>',
                r'<button[^>]*>[\s]*[^<]*sign in[^<]*</button>'
            ]
            
            for pattern in submit_patterns:
                matches = re.findall(pattern, page_html, re.IGNORECASE)
                if matches:
                    match = matches[0]
                    if 'id=' in match:
                        id_match = re.search(r'id="([^"]*)"', match)
                        if id_match:
                            selectors['submit_selector'] = f"#{id_match.group(1)}"
                            break
                    elif 'type="submit"' in match:
                        selectors['submit_selector'] = 'button[type="submit"]'
                        break
                    elif 'class=' in match:
                        class_match = re.search(r'class="([^"]*)"', match)
                        if class_match:
                            selectors['submit_selector'] = f".{class_match.group(1).split()[0]}"
                            break
            
            # Add login URLs to response
            if login_urls:
                selectors['login_urls'] = login_urls
            
            log.info(f"🎯 Local analysis found selectors: {selectors}")
            
            # Save analysis results
            analysis_file = f"logs/debug/login_analysis_{timestamp}.json"
            with open(analysis_file, 'w') as f:
                json.dump({
                    'selectors': selectors,
                    'login_urls': login_urls,
                    'html_file': html_file,
                    'timestamp': timestamp
                }, f, indent=2)
            
            log.info(f"💾 Saved analysis to: {analysis_file}")
            
            return selectors if selectors else None
            
        except Exception as e:
            log.error(f"❌ Local HTML analysis failed: {e}")
            return None

    async def _analyze_login_form_multimodal(self, screenshot_data: str, pruned_html: str) -> Optional[Dict[str, str]]:
        """
        Analyze login form using both screenshot and HTML with definitive prompt
        """
        try:
            log.debug("🧠 Sending multimodal request to AI model...")
            
            # Definitive prompt as specified in master prompt
            prompt = """# ROLE AND OBJECTIVE
You are an expert web developer and automation engineer. Your task is to analyze a screenshot of a login page and its pruned HTML to identify the most robust and unique CSS selectors for the login form elements.

# INSTRUCTIONS
1. Cross-reference the visual layout in the screenshot with the provided HTML structure.
2. Identify the optimal CSS selectors for the user input field (email/username), the password field, and the main submit button.
3. Prioritize selectors in this order: unique `id` > specific `name` attribute > unique `class` combination > `type` attribute with other context.
4. The selectors must be precise enough to avoid ambiguity.

# CONTEXT
- The HTML has been pruned of scripts, styles, and SVG tags. Focus on `form`, `input`, and `button` elements.
- The goal is to find selectors that can be reliably used by a Playwright automation script.

# OUTPUT FORMAT
Your response MUST be a single, valid JSON object and nothing else.
{
  "email_selector": "<selector>",
  "password_selector": "<selector>",
  "submit_selector": "<selector>"
}"""
            
            # Load system config for AI assistance injection
            try:
                with open("config/system_config.json", "r") as f:
                    system_config = json.load(f)
                discovery_config = system_config.get("ai_features", {}).get("discovery_assistance", {})
                if discovery_config.get("enabled"):
                    login_hint = discovery_config.get("prompt_injection", {}).get("login_discovery_hints", "")
                    if login_hint:
                        prompt += f"\n\n# USER-PROVIDED HINTS\n{login_hint}"
                        log.info("🧠 Injecting user-provided hints into login discovery prompt.")
            except Exception as e:
                log.warning(f"Could not load or apply AI assistance hint: {e}")

            # Make multimodal API call
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "text", "text": f"\n\nPRUNED HTML CONTENT:\n{pruned_html}"},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{screenshot_data}"}
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content.strip()
            log.debug(f"🎯 AI response received: {content[:100]}...")
            
            # Parse JSON response
            try:
                selectors = json.loads(content)
                log.info(f"✅ Login selectors extracted: {selectors}")
                return selectors
            except json.JSONDecodeError as e:
                log.error(f"❌ Failed to parse AI response as JSON: {e}")
                log.debug(f"Raw response: {content}")
                return None
                
        except Exception as e:
            log.error(f"❌ Multimodal analysis failed: {e}")
            return None
            
        except Exception as e:
            log.error(f"Vision login discovery failed: {e}")
            return await self._heuristic_login_discovery()
    
    async def discover_product_and_pagination_selectors(self) -> Optional[Dict[str, Any]]:
        """
        Discover product and pagination selectors using AI vision with definitive prompt
        
        Returns:
            dict: Product and pagination selectors configuration
        """
        try:
            log.info("🕷️ Starting vision-based product and pagination selector discovery...")
            
            # Step 1: Extract and prune HTML content
            log.info("📄 Extracting page HTML content...")
            html_content = await self.page.content()
            pruned_html = self._prune_html_for_ai(html_content)
            log.info(f"📊 HTML content processed: {len(pruned_html)} characters after pruning")
            
            # Step 2: Take screenshot for visual analysis
            log.info("📸 Capturing page screenshot...")
            screenshot_data = await self._capture_page_screenshot()
            
            if not screenshot_data:
                log.error("❌ Failed to capture screenshot for visual analysis")
                return None
            
            # Step 3: Multimodal AI analysis combining HTML and visual data
            log.info("🧠 Performing multimodal AI analysis for product and pagination elements...")
            config = await self._analyze_product_page_multimodal(screenshot_data, pruned_html)
            
            if config:
                log.info("✅ Product and pagination elements discovered successfully via multimodal analysis")
                
                # Step 4: Validate discovered selectors on actual page
                log.info("🔍 Validating discovered selectors...")
                validated_config = await self._validate_product_and_pagination_selectors(config)
                
                if validated_config:
                    log.info("✅ Product and pagination selectors validated successfully")
                    return validated_config
                else:
                    log.warning("⚠️ Discovered selectors failed validation")
            
            # Fallback to heuristic discovery
            log.info("🔄 Falling back to heuristic discovery...")
            return await self._heuristic_product_discovery()
            
        except Exception as e:
            log.error(f"❌ Product and pagination discovery failed: {e}")
            return None
    
    async def discover_product_selectors(self, sample_pages: int = 3) -> Optional[Dict[str, List[str]]]:
        """
        Legacy method - discover product listing selectors using AI vision
        
        Args:
            sample_pages: Number of pages to analyze
            
        Returns:
            dict: Product selectors configuration
        """
        try:
            log.info("🕷️ Starting vision-based product selector discovery...")
            
            selectors_config = {
                "product_item": [],
                "title": [],
                "price": [],
                "url": [],
                "image": [],
                "ean": [],
                "barcode": []
            }
            
            # Analyze multiple pages for pattern consistency
            for page_num in range(1, sample_pages + 1):
                log.info(f"📄 Analyzing page {page_num}...")
                
                # Navigate to page
                current_url = self.page.url
                page_url = f"{current_url}?page={page_num}"
                
                try:
                    await self.page.goto(page_url, wait_until='domcontentloaded', timeout=10000)
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                except:
                    log.warning(f"Could not load page {page_num}, using current page")
                
                # Take screenshot
                screenshot_data = await self._capture_page_screenshot()
                
                if screenshot_data:
                    # Analyze with vision API
                    page_selectors = await self._analyze_product_page(screenshot_data)
                    
                    if page_selectors:
                        # Merge selectors
                        for field, selectors in page_selectors.items():
                            if field in selectors_config:
                                selectors_config[field].extend(selectors)
            
            # Remove duplicates and validate
            final_selectors = {}
            for field, selectors in selectors_config.items():
                unique_selectors = list(set(selectors))
                if unique_selectors:
                    # Validate selectors on current page
                    validated = await self._validate_product_selectors(unique_selectors)
                    if validated:
                        final_selectors[field] = validated[:3]  # Top 3 working selectors
            
            if final_selectors:
                log.info(f"✅ Product selectors discovered: {list(final_selectors.keys())}")
                return final_selectors
            
            # Fallback to heuristic discovery
            log.info("🔄 Falling back to heuristic product discovery...")
            return await self._heuristic_product_discovery()
            
        except Exception as e:
            log.error(f"Vision product discovery failed: {e}")
            return await self._heuristic_product_discovery()
    
    async def discover_navigation_patterns(self) -> Dict[str, Any]:
        """
        Discover navigation patterns and pagination
        
        Returns:
            dict: Navigation configuration
        """
        try:
            log.info("🧭 Discovering navigation patterns...")
            
            screenshot_data = await self._capture_page_screenshot()
            
            if screenshot_data:
                nav_config = await self._analyze_navigation(screenshot_data)
                
                if nav_config:
                    return nav_config
            
            # Fallback to standard patterns
            return {
                "pagination": {
                    "pattern": "?page={page_num}",
                    "next_selectors": ["a.next", ".pagination .next", "a[rel='next']"],
                    "prev_selectors": ["a.prev", ".pagination .prev", "a[rel='prev']"]
                },
                "categories": {
                    "selectors": [".category-item a", ".nav-item a", ".menu-item a"]
                }
            }
            
        except Exception as e:
            log.error(f"Navigation discovery failed: {e}")
            return {}
    
    async def _capture_page_screenshot(self) -> Optional[str]:
        """Capture and encode page screenshot for vision analysis"""
        try:
            # Take full page screenshot
            screenshot_path = f"temp_vision_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=screenshot_path, full_page=True)
            
            # Encode as base64
            with open(screenshot_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Clean up temp file
            os.remove(screenshot_path)
            
            return encoded_string
            
        except Exception as e:
            log.error(f"Screenshot capture failed: {e}")
            return None
    
    async def _analyze_login_form(self, screenshot_data: str) -> Optional[Dict[str, str]]:
        """Analyze screenshot for login form elements"""
        try:
            prompt = """
            Analyze this webpage screenshot to identify login form elements. 
            
            Please identify CSS selectors for:
            1. Email/username input field
            2. Password input field  
            3. Login/submit button
            4. Login page URL (if this is not the login page, suggest where to find it)
            
            Respond in JSON format:
            {
                "email_selector": "CSS selector for email field",
                "password_selector": "CSS selector for password field", 
                "submit_selector": "CSS selector for submit button",
                "login_url": "URL or path to login page",
                "confidence": "high/medium/low"
            }
            
            If no login form is visible, set confidence to "low" and suggest likely locations.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON response with robust error handling
            try:
                # Try to extract JSON from response (may have explanatory text)
                if '{' in result and '}' in result:
                    start = result.find('{')
                    end = result.rfind('}') + 1
                    json_str = result[start:end]
                    config = json.loads(json_str)
                else:
                    log.warning("No JSON found in Vision API response, using fallback")
                    return None
            except json.JSONDecodeError as e:
                log.warning(f"Failed to parse Vision API JSON: {e}, using fallback")
                return None
            
            if config.get("confidence") in ["high", "medium"]:
                return config
            
            return None
            
        except Exception as e:
            log.error(f"Vision login analysis failed: {e}")
            return None
    
    async def _analyze_product_page_multimodal(self, screenshot_data: str, pruned_html: str) -> Optional[Dict[str, Any]]:
        """Analyze product page using static core selectors plus optional dynamic additions"""
        try:
            # Load system config for dynamic additional selectors and hints
            additional_product_instructions = ""
            additional_navigation_instructions = ""
            additional_json_fields = []
            user_hints = ""
            
            try:
                with open("config/system_config.json", "r") as f:
                    system_config = json.load(f)
                
                # Get extraction targets for additional selectors
                extraction_config = system_config.get("ai_selector_extraction", {})
                extraction_targets = extraction_config.get("extraction_targets", {})
                product_data_targets = extraction_targets.get("product_data", [])
                navigation_targets = extraction_targets.get("navigation", [])
                
                # Check for discovery assistance hints for product/navigation discovery
                discovery_config = system_config.get("ai_features", {}).get("discovery_assistance", {})
                if discovery_config.get("enabled"):
                    product_navigation_hint = discovery_config.get("prompt_injection", {}).get("product_navigation_discovery_hints", "")
                    if product_navigation_hint:
                        user_hints = f"\n\n# USER-PROVIDED HINTS\n{product_navigation_hint}\n"
                
                # Add optional product selectors (beyond core static ones)
                additional_product_selectors = []
                for target in product_data_targets:
                    if target not in ["price", "title", "ean", "barcode"]:  # Skip core static selectors
                        additional_product_selectors.append(target)
                        additional_json_fields.append(f'"{target}_selector_relative": "<selector>"')
                
                if additional_product_selectors:
                    additional_product_instructions = "\n   OPTIONAL ADDITIONAL SELECTORS:\n"
                    for target in additional_product_selectors:
                        if target == "image":
                            additional_product_instructions += "   - The main image (src attribute) of the product.\n"
                        elif target == "description":
                            additional_product_instructions += "   - The product's description or brief summary.\n"
                        elif target == "out_of_stock":
                            additional_product_instructions += "   - Out of stock indicator/badge (if products show stock status).\n"
                        else:
                            additional_product_instructions += f"   - The product's {target} indicator/element.\n"
                
                # Add optional navigation selectors (beyond core static ones)
                # Core static navigation: next_page, category_links, breadcrumbs
                core_navigation = ["next_page", "category_links", "breadcrumbs"]
                additional_navigation_selectors = []
                
                # Check all extraction target categories for additional selectors
                all_navigation_targets = (navigation_targets + 
                                        extraction_targets.get("pagination", []) + 
                                        extraction_targets.get("filtering", []))
                
                for target in all_navigation_targets:
                    if target not in core_navigation and target not in additional_navigation_selectors:
                        additional_navigation_selectors.append(target)
                        additional_json_fields.append(f'"{target}_selector": "<selector>"')
                
                if additional_navigation_selectors:
                    additional_navigation_instructions = "\n   OPTIONAL ADDITIONAL NAVIGATION:\n"
                    for target in additional_navigation_selectors:
                        if target == "previous_page":
                            additional_navigation_instructions += "   - Previous page navigation element.\n"
                        elif target == "page_numbers":
                            additional_navigation_instructions += "   - Page number navigation elements.\n"
                        elif target == "price_filter":
                            additional_navigation_instructions += "   - Price filter controls (range, ascending/descending).\n"
                        elif target == "products_per_page":
                            additional_navigation_instructions += "   - Products per page selector/dropdown.\n"
                        elif target == "category_filter":
                            additional_navigation_instructions += "   - Category filter/dropdown selector.\n"
                        elif target == "search_box":
                            additional_navigation_instructions += "   - Search input box for products.\n"
                        else:
                            additional_navigation_instructions += f"   - {target.replace('_', ' ').title()} selector.\n"
                
            except Exception as e:
                log.warning(f"Could not load additional selectors from config: {e}. Using core selectors only.")
            
            # Build JSON output format
            core_json_fields = [
                '"product_container_selector": "<selector>"',
                '"title_selector_relative": "<selector>"',
                '"price_selector_relative": "<selector>"',
                '"url_selector_relative": "<selector>"',
                '"ean_selector_relative": "<selector>"'
            ]
            
            # Core navigation fields
            core_navigation_fields = [
                '"next_page_selector": "<selector>"',
                '"category_links_selector": "<selector>"',
                '"breadcrumbs_selector": "<selector>"'
            ]
            
            all_json_fields = core_json_fields + core_navigation_fields + additional_json_fields
            json_output = "{\n  " + ',\n  '.join(all_json_fields) + "\n}"
            
            # Static core selectors with optional additions
            prompt = f"""# ROLE AND OBJECTIVE
You are an expert web scraping engineer. Your task is to analyze a product category page (provided as a screenshot and pruned HTML) to identify all CSS selectors needed for automated data extraction and navigation.

# INSTRUCTIONS
1. **Product Container:** Identify the single, repeating CSS selector for the main container that encapsulates each individual product on the grid or list.

2. **CORE Product Selectors (REQUIRED):** Within the context of that container, identify the *relative* CSS selectors for:
   - The product's title/name.
   - The product's price.
   - The unique URL (href attribute) for the product's detail page.
   - The product's EAN/barcode (if visible on product listings).{additional_product_instructions}

3. **CORE Navigation (REQUIRED):** Identify selectors for:
   - Next Page navigation element (button/link with "Next", ">", ">>").
   - Category links/navigation menu on the page.
   - Breadcrumbs navigation (if present).{additional_navigation_instructions}

# OUTPUT FORMAT
Your response MUST be a single, valid JSON object and nothing else.
{json_output}{user_hints}"""
            
            # Load system config for AI assistance injection
            try:
                with open("config/system_config.json", "r") as f:
                    system_config = json.load(f)
                assistance_config = system_config.get("ai_features", {}).get("ai_assistance", {}).get("components", {}).get("product_extraction", {})
                if assistance_config.get("enabled"):
                    # Check for any hint in the discovery_assistance section for backwards compatibility
                    discovery_config = system_config.get("ai_features", {}).get("discovery_assistance", {})
                    if discovery_config.get("enabled"):
                        product_hint = discovery_config.get("prompt_injection", {}).get("product_selectors", "")
                        pagination_hint = discovery_config.get("prompt_injection", {}).get("pagination_selectors", "")
                        combined_hint = ""
                        if product_hint:
                            combined_hint += f"Product selectors hint: {product_hint}"
                        if pagination_hint:
                            combined_hint += f"\nPagination selectors hint: {pagination_hint}"
                        if combined_hint:
                            prompt += f"\n\n# USER-PROVIDED HINT\n{combined_hint}"
                            log.info("🧠 Injecting user-provided hint into product discovery prompt.")
            except Exception as e:
                log.warning(f"Could not load or apply AI assistance hint: {e}")
            
            # Make multimodal API call
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "text", "text": f"\n\nPRUNED HTML CONTENT:\n{pruned_html}"},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{screenshot_data}"}
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content.strip()
            log.debug(f"🎯 AI response received: {content[:100]}...")
            
            # Parse JSON response
            try:
                selectors = json.loads(content)
                log.info(f"✅ Product and pagination selectors extracted: {selectors}")
                return selectors
            except json.JSONDecodeError as e:
                log.error(f"❌ Failed to parse AI response as JSON: {e}")
                log.debug(f"Raw response: {content}")
                return None
                
        except Exception as e:
            log.error(f"❌ Multimodal product analysis failed: {e}")
            return None
    
    async def _analyze_product_page(self, screenshot_data: str) -> Optional[Dict[str, List[str]]]:
        """Legacy method - Analyze screenshot for product listing elements"""
        try:
            prompt = """
            Analyze this e-commerce product listing page to identify CSS selectors for product data extraction.
            
            Please identify CSS selectors for:
            1. Product container/item wrapper
            2. Product title/name
            3. Product price
            4. Product URL/link
            5. Product image
            6. EAN/barcode (if visible)
            7. Login required price indicators
            
            Respond in JSON format:
            {
                "product_item": ["selector1", "selector2"],
                "title": ["selector1", "selector2"], 
                "price": ["selector1", "selector2"],
                "url": ["selector1", "selector2"],
                "image": ["selector1", "selector2"],
                "ean": ["selector1", "selector2"],
                "price_login_required": ["selector1", "selector2"],
                "confidence": "high/medium/low"
            }
            
            Provide multiple selector options for each field when possible.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON response with robust error handling
            try:
                # Try to extract JSON from response (may have explanatory text)
                if '{' in result and '}' in result:
                    start = result.find('{')
                    end = result.rfind('}') + 1
                    json_str = result[start:end]
                    config = json.loads(json_str)
                else:
                    log.warning("No JSON found in Vision API response, using fallback")
                    return {}
            except json.JSONDecodeError as e:
                log.warning(f"Failed to parse Vision API JSON: {e}, using fallback")
                return {}
            
            if config.get("confidence") in ["high", "medium"]:
                # Remove confidence from selectors
                config.pop("confidence", None)
                return config
            
            return None
            
        except Exception as e:
            log.error(f"Vision product analysis failed: {e}")
            return None
    
    async def _analyze_navigation(self, screenshot_data: str) -> Optional[Dict[str, Any]]:
        """Analyze screenshot for navigation patterns"""
        try:
            prompt = """
            Analyze this webpage to identify navigation patterns.
            
            Please identify:
            1. Pagination elements (next/previous buttons, page numbers)
            2. Category navigation links
            3. Search functionality
            4. URL patterns for pagination
            
            Respond in JSON format:
            {
                "pagination": {
                    "next_selectors": ["selector1", "selector2"],
                    "prev_selectors": ["selector1", "selector2"],
                    "pattern": "URL pattern like ?page={page_num}"
                },
                "categories": {
                    "selectors": ["selector1", "selector2"]
                },
                "search": {
                    "input_selector": "search input selector",
                    "submit_selector": "search submit selector"
                }
            }
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON response with robust error handling
            try:
                # Try to extract JSON from response (may have explanatory text)
                if '{' in result and '}' in result:
                    start = result.find('{')
                    end = result.rfind('}') + 1
                    json_str = result[start:end]
                    return json.loads(json_str)
                else:
                    log.warning("No JSON found in Vision API response, using fallback")
                    return {}
            except json.JSONDecodeError as e:
                log.warning(f"Failed to parse Vision API JSON: {e}, using fallback")
                return {}
            
        except Exception as e:
            log.error(f"Vision navigation analysis failed: {e}")
            return None
    
    async def _validate_login_selectors(self, config: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Validate discovered login selectors work on the page"""
        try:
            log.info("🔍 Validating login selectors...")
            
            validated = {}
            
            # Check email field
            email_selector = config.get("email_selector")
            if email_selector:
                try:
                    element = await self.page.query_selector(email_selector)
                    if element and await element.is_visible():
                        validated["email_selector"] = email_selector
                        log.info(f"✅ Email selector validated: {email_selector}")
                except:
                    pass
            
            # Check password field
            password_selector = config.get("password_selector")
            if password_selector:
                try:
                    element = await self.page.query_selector(password_selector)
                    if element and await element.is_visible():
                        validated["password_selector"] = password_selector
                        log.info(f"✅ Password selector validated: {password_selector}")
                except:
                    pass
            
            # Check submit button
            submit_selector = config.get("submit_selector")
            if submit_selector:
                try:
                    element = await self.page.query_selector(submit_selector)
                    if element and await element.is_visible():
                        validated["submit_selector"] = submit_selector
                        log.info(f"✅ Submit selector validated: {submit_selector}")
                except:
                    pass
            
            # Add login URL
            if config.get("login_url"):
                validated["login_url"] = config["login_url"]
            
            # Need at least email and password to be valid
            if "email_selector" in validated and "password_selector" in validated:
                return validated
            
            return None
            
        except Exception as e:
            log.error(f"Selector validation failed: {e}")
            return None
    
    async def _validate_product_and_pagination_selectors(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate discovered product and pagination selectors work on the page"""
        try:
            log.info("🔍 Validating product and pagination selectors...")
            
            validated = {}
            
            # Check product container
            container_selector = config.get("product_container_selector")
            if container_selector:
                try:
                    elements = await self.page.query_selector_all(container_selector)
                    visible_count = sum(1 for e in elements[:10] if await e.is_visible())
                    if visible_count >= 2:  # At least 2 products found
                        validated["product_container_selector"] = container_selector
                        log.info(f"✅ Product container selector validated: {container_selector} ({visible_count} elements)")
                except:
                    pass
            
            # Check relative selectors if container is valid
            if "product_container_selector" in validated:
                for selector_key in ["title_selector_relative", "price_selector_relative", "url_selector_relative", "image_selector_relative"]:
                    relative_selector = config.get(selector_key)
                    if relative_selector:
                        try:
                            # Test the relative selector within the container
                            container_elements = await self.page.query_selector_all(validated["product_container_selector"])
                            if container_elements:
                                test_element = await container_elements[0].query_selector(relative_selector)
                                if test_element:
                                    validated[selector_key] = relative_selector
                                    log.info(f"✅ Relative selector validated: {selector_key} = {relative_selector}")
                        except:
                            pass
            
            # Check pagination
            pagination_config = config.get("pagination", {})
            if pagination_config:
                next_selector = pagination_config.get("next_page_selector")
                if next_selector:
                    try:
                        element = await self.page.query_selector(next_selector)
                        if element and await element.is_visible():
                            validated["pagination"] = {"next_page_selector": next_selector}
                            log.info(f"✅ Pagination selector validated: {next_selector}")
                    except:
                        pass
            
            # Need at least container and one relative selector to be valid
            if "product_container_selector" in validated and any(key.endswith("_relative") for key in validated.keys()):
                return validated
            
            return None
            
        except Exception as e:
            log.error(f"Product and pagination selector validation failed: {e}")
            return None
    
    async def _validate_product_selectors(self, selectors: List[str]) -> List[str]:
        """Legacy method - Validate product selectors work on current page"""
        try:
            validated = []
            
            for selector in selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    
                    # Check if selector finds multiple visible elements (product list)
                    visible_count = 0
                    for element in elements[:5]:  # Check first 5
                        if await element.is_visible():
                            visible_count += 1
                    
                    if visible_count >= 2:  # At least 2 products found
                        validated.append(selector)
                        log.info(f"✅ Product selector validated: {selector} ({visible_count} elements)")
                
                except:
                    continue
            
            return validated
            
        except Exception as e:
            log.error(f"Product selector validation failed: {e}")
            return []
    
    async def _heuristic_login_discovery(self) -> Optional[Dict[str, str]]:
        """Fallback heuristic login discovery"""
        try:
            log.info("🔄 Running heuristic login discovery...")
            
            # Common login selectors
            email_selectors = [
                "input[type='email']",
                "input[name*='email']", 
                "input[id*='email']",
                "input[name*='username']",
                "#email",
                "#username"
            ]
            
            password_selectors = [
                "input[type='password']",
                "input[name*='password']",
                "#password",
                "#pass"
            ]
            
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Login')",
                "button:has-text('Sign In')",
                ".login-button"
            ]
            
            config = {}
            
            # Find working email selector
            for selector in email_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        config["email_selector"] = selector
                        break
                except:
                    continue
            
            # Find working password selector
            for selector in password_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        config["password_selector"] = selector
                        break
                except:
                    continue
            
            # Find working submit selector
            for selector in submit_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        config["submit_selector"] = selector
                        break
                except:
                    continue
            
            if "email_selector" in config and "password_selector" in config:
                config["login_url"] = self.page.url
                config["discovery_method"] = "heuristic"
                log.info("✅ Heuristic login discovery successful")
                return config
            
            return None
            
        except Exception as e:
            log.error(f"Heuristic login discovery failed: {e}")
            return None
    
    async def _heuristic_product_discovery(self) -> Optional[Dict[str, List[str]]]:
        """Fallback heuristic product discovery"""
        try:
            log.info("🔄 Running heuristic product discovery...")
            
            selectors = {
                "product_item": [
                    ".product-item",
                    ".product",
                    "article",
                    ".item",
                    ".grid-item"
                ],
                "title": [
                    ".product-title",
                    ".title",
                    "h2 a",
                    "h3 a",
                    ".product-name"
                ],
                "price": [
                    ".price",
                    ".cost",
                    "[data-price]",
                    ".price-current",
                    ".amount"
                ],
                "url": [
                    "a.product-link",
                    ".product-item a",
                    "h2 a",
                    "a[href*='product']"
                ],
                "image": [
                    "img.product-image",
                    ".product-item img",
                    "img"
                ]
            }
            
            # Validate selectors
            validated_selectors = {}
            for field, candidates in selectors.items():
                validated = await self._validate_product_selectors(candidates)
                if validated:
                    validated_selectors[field] = validated[:2]  # Top 2
            
            if validated_selectors:
                log.info("✅ Heuristic product discovery successful")
                return validated_selectors
            
            return None
            
        except Exception as e:
            log.error(f"Heuristic product discovery failed: {e}")
            return None

# Standalone functions for integration
async def discover_supplier_login(page: Page) -> Optional[Dict[str, str]]:
    """
    Standalone function to discover login elements
    
    Args:
        page: Playwright page object
        
    Returns:
        dict: Login configuration or None
    """
    try:
        engine = VisionDiscoveryEngine(page)
        return await engine.discover_login_elements()
    except Exception as e:
        log.error(f"Standalone login discovery failed: {e}")
        return None

async def discover_supplier_products(page: Page, sample_pages: int = 3) -> Optional[Dict[str, List[str]]]:
    """
    Standalone function to discover product selectors
    
    Args:
        page: Playwright page object
        sample_pages: Number of pages to analyze
        
    Returns:
        dict: Product selectors configuration or None
    """
    try:
        engine = VisionDiscoveryEngine(page)
        return await engine.discover_product_selectors(sample_pages)
    except Exception as e:
        log.error(f"Standalone product discovery failed: {e}")
        return None

async def discover_complete_supplier(page: Page) -> Dict[str, Any]:
    """
    Complete supplier discovery - login + products + navigation
    
    Args:
        page: Playwright page object
        
    Returns:
        dict: Complete supplier configuration
    """
    try:
        log.info("🔍 Starting complete supplier discovery...")
        
        engine = VisionDiscoveryEngine(page)
        
        # Discover all components
        login_config = await engine.discover_login_elements()
        product_config = await engine.discover_product_selectors()
        nav_config = await engine.discover_navigation_patterns()
        
        # Combine results
        complete_config = {
            "supplier_url": page.url,
            "discovery_timestamp": datetime.now().isoformat(),
            "login": login_config,
            "products": product_config,
            "navigation": nav_config,
            "success": bool(login_config or product_config)
        }
        
        log.info(f"✅ Complete discovery finished: {complete_config['success']}")
        return complete_config
        
    except Exception as e:
        log.error(f"Complete supplier discovery failed: {e}")
        return {
            "supplier_url": page.url,
            "discovery_timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test the vision discovery engine
    async def test_discovery():
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Test with current page
        result = await discover_complete_supplier(page)
        
        log.info(f"✅ Discovery test result: {result}")
        
        # Save result
        with open("vision_discovery_test.json", "w") as f:
            json.dump(result, f, indent=2)
    
    asyncio.run(test_discovery())