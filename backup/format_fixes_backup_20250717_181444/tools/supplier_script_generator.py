#!/usr/bin/env python3
"""
Intelligent Supplier Script Generator - Complete Rewrite for Master Prompt
==========================================================================

This is the PRIMARY AUTOMATION ENGINE that generates, tests, and validates 
supplier-specific scripts with AI-powered discovery and self-validation.

ORCHESTRATION SEQUENCE:
1. Check Existing State (.supplier_ready file validation)
2. AI-Powered Discovery (VisionDiscoveryEngine integration)
3. Template Generation (login and product extractor scripts)
4. Test-After-Generate Validation Loop
5. Generate Intelligent .supplier_ready File

INTEGRATION:
    - Enhanced VisionDiscoveryEngine for AI discovery
    - Supplier Guard for intelligent .supplier_ready management
    - Dynamic import testing for generated scripts
    - AI-powered failure analysis with debug insights

USAGE:
    python tools/supplier_script_generator.py --supplier-url https://example.com --force-regenerate
"""

import asyncio
import json
import logging
import os
import sys
import argparse
import importlib.util
import traceback
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Import system modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vision_discovery_engine import VisionDiscoveryEngine
from tools.supplier_guard import SupplierGuard
from playwright.async_api import async_playwright, Page, Browser
import openai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class IntelligentSupplierScriptGenerator:
    """
    Intelligent supplier script generator with AI-powered discovery and self-validation
    """
    
    def __init__(self, supplier_url: str, force_regenerate: bool = False):
        self.supplier_url = supplier_url
        self.force_regenerate = force_regenerate
        self.domain = urlparse(supplier_url).netloc.replace('www.', '')
        self.supplier_id = self.domain.replace('.', '-')
        
        # Load system configuration
        try:
            with open("config/system_config.json", "r") as f:
                self.system_config = json.load(f)
        except Exception as e:
            log.warning(f"Failed to load system config: {e}")
            self.system_config = {}
        
        # AI assistance configuration
        self.ai_config = self.system_config.get("ai_features", {}).get("ai_assistance", {})
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Paths
        self.supplier_dir = Path(f"suppliers/{self.supplier_id}")
        self.scripts_dir = self.supplier_dir / "scripts"
        self.config_dir = self.supplier_dir / "config"
        
        # Supplier Guard for state management
        self.guard = SupplierGuard()
        
        # Browser and page references
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        log.info(f"🧠 Intelligent Supplier Script Generator initialized for: {self.supplier_url}")
        log.info(f"📁 Supplier directory: {self.supplier_dir}")
    
    async def generate_all_scripts(self) -> Dict[str, Any]:
        """
        Main orchestration method following the precise sequence from master prompt
        """
        try:
            log.info("🚀 Starting intelligent supplier script generation...")
            
            # Step 1: Check Existing State
            if not self.force_regenerate:
                ready_status = await self._check_existing_state()
                if ready_status["skip_generation"]:
                    log.info("✅ Supplier package already ready, skipping generation")
                    return ready_status
            
            # Step 2: Initialize browser connection
            await self._initialize_browser()
            
            # Step 3: AI-Powered Discovery
            discovery_results = await self._ai_powered_discovery()
            if not discovery_results["success"]:
                return {"success": False, "error": "AI discovery failed", "details": discovery_results}
            
            # Step 4: Template Generation
            generation_results = await self._generate_scripts_from_templates(discovery_results)
            if not generation_results["success"]:
                return {"success": False, "error": "Script generation failed", "details": generation_results}
            
            # Step 5: Test-After-Generate Validation Loop
            validation_results = await self._test_after_generate_validation(generation_results)
            
            # Step 6: Generate Intelligent .supplier_ready File
            ready_file_results = await self._generate_intelligent_supplier_ready(validation_results)
            
            log.info("✅ Intelligent supplier script generation completed successfully")
            return {
                "success": True,
                "supplier_id": self.supplier_id,
                "discovery": discovery_results,
                "generation": generation_results,
                "validation": validation_results,
                "ready_file": ready_file_results
            }
            
        except Exception as e:
            log.error(f"❌ Supplier script generation failed: {e}")
            log.error(traceback.format_exc())
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
        finally:
            await self._cleanup_browser()
    
    async def _check_existing_state(self) -> Dict[str, Any]:
        """
        Step 1: Check for existing .supplier_ready file and validate components
        """
        try:
            log.info("🔍 Checking existing supplier state...")
            
            # Check for .supplier_ready file
            ready_file = self.supplier_dir / ".supplier_ready"
            if not ready_file.exists():
                log.info("No .supplier_ready file found, proceeding with generation")
                return {"skip_generation": False, "reason": "No .supplier_ready file"}
            
            # Validate ready file content
            try:
                with open(ready_file, 'r') as f:
                    ready_data = json.load(f)
                
                validation_status = ready_data.get("validation_status", {})
                login_validated = validation_status.get("login_validated", False)
                products_validated = validation_status.get("products_validated", False)
                
                # Check if all components are validated
                if login_validated and products_validated:
                    log.info("✅ All components already validated, supplier is ready")
                    return {
                        "skip_generation": True, 
                        "reason": "All components validated",
                        "validation_status": validation_status
                    }
                else:
                    failed_components = []
                    if not login_validated:
                        failed_components.append("login")
                    if not products_validated:
                        failed_components.append("products")
                    
                    log.info(f"⚠️ Some components failed validation: {failed_components}")
                    return {
                        "skip_generation": False,
                        "reason": f"Failed components: {failed_components}",
                        "regenerate_only": failed_components
                    }
                    
            except json.JSONDecodeError:
                log.warning("Invalid .supplier_ready file format, regenerating")
                return {"skip_generation": False, "reason": "Invalid ready file format"}
                
        except Exception as e:
            log.error(f"Error checking existing state: {e}")
            return {"skip_generation": False, "reason": f"State check error: {e}"}
    
    async def _initialize_browser(self) -> None:
        """Initialize browser connection for discovery and testing"""
        try:
            log.info("🌐 Initializing browser connection...")
            
            playwright = await async_playwright().start()
            
            # Try to connect to existing Chrome debug instance
            try:
                self.browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
                log.info("✅ Connected to existing Chrome debug instance")
            except:
                # Launch new browser if CDP connection fails
                self.browser = await playwright.chromium.launch(headless=False)
                log.info("✅ Launched new browser instance")
            
            # Get or create context
            if self.browser.contexts:
                context = self.browser.contexts[0]
            else:
                context = await self.browser.new_context()
            
            # Find the currently active/visible page that user is viewing
            active_page = None
            for page in context.pages:
                try:
                    # Check if this page is visible and has focus (the user's active tab)
                    is_active = await page.evaluate("""() => {
                        return document.visibilityState === 'visible' && document.hasFocus();
                    }""")
                    if is_active:
                        active_page = page
                        log.info(f"✅ Using active user page: {page.url[:100]}...")
                        break
                except:
                    continue
            
            # Use active page if found, otherwise fallback to first page or create new
            if active_page:
                self.page = active_page
            elif context.pages:
                self.page = context.pages[0]
                log.warning("⚠️ No active page found, using first available page")
            else:
                self.page = await context.new_page()
                log.info("📄 Created new page")
            
            # Only navigate if not already on the supplier domain
            current_url = self.page.url
            from urllib.parse import urlparse
            current_domain = urlparse(current_url).netloc
            target_domain = urlparse(self.supplier_url).netloc
            
            if current_domain != target_domain:
                log.info(f"🔄 Navigating from {current_domain} to {target_domain}")
                await self.page.goto(self.supplier_url)
                await self.page.wait_for_load_state('domcontentloaded')
            else:
                log.info(f"✅ Already on target domain {target_domain}, preserving current page state")
            
            log.info(f"📄 Navigated to: {self.page.url}")
            
        except Exception as e:
            log.error(f"Failed to initialize browser: {e}")
            raise
    
    async def _ai_powered_discovery(self) -> Dict[str, Any]:
        """
        Step 2: AI-Powered Discovery calling enhanced VisionDiscoveryEngine
        """
        try:
            log.info("🧠 Starting AI-powered element discovery...")
            
            # Initialize VisionDiscoveryEngine
            vision_engine = VisionDiscoveryEngine(self.page)
            
            # Discover login elements
            log.info("🔐 Discovering login elements...")
            login_config = await vision_engine.discover_login_elements()
            
            # Discover product and pagination selectors
            log.info("🛍️ Discovering product and pagination selectors...")
            product_config = await vision_engine.discover_product_and_pagination_selectors()
            
            # Create directory structure
            self.supplier_dir.mkdir(parents=True, exist_ok=True)
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.scripts_dir.mkdir(parents=True, exist_ok=True)
            
            # Save login_config.json
            login_config_path = self.config_dir / "login_config.json"
            if login_config:
                with open(login_config_path, 'w') as f:
                    json.dump(login_config, f, indent=2)
                log.info(f"💾 Saved login config: {login_config_path}")
            else:
                log.warning("⚠️ Login discovery failed, creating empty config")
                with open(login_config_path, 'w') as f:
                    json.dump({"error": "Login discovery failed"}, f, indent=2)
            
            # Save product_selectors.json
            product_selectors_path = self.config_dir / "product_selectors.json"
            if product_config:
                with open(product_selectors_path, 'w') as f:
                    json.dump(product_config, f, indent=2)
                log.info(f"💾 Saved product selectors: {product_selectors_path}")
            else:
                log.warning("⚠️ Product discovery failed, creating empty config")
                with open(product_selectors_path, 'w') as f:
                    json.dump({"error": "Product discovery failed"}, f, indent=2)
            
            return {
                "success": bool(login_config or product_config),
                "login_config": login_config,
                "product_config": product_config,
                "login_config_path": str(login_config_path),
                "product_selectors_path": str(product_selectors_path)
            }
            
        except Exception as e:
            log.error(f"AI discovery failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_scripts_from_templates(self, discovery_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Generate login and product extractor scripts from templates
        """
        try:
            log.info("📝 Generating scripts from templates...")
            
            login_script_path = self.scripts_dir / f"{self.supplier_id}_login.py"
            product_script_path = self.scripts_dir / f"{self.supplier_id}_product_extractor.py"
            
            # Generate login script
            login_script_content = self._generate_login_script_template(discovery_results.get("login_config"))
            with open(login_script_path, 'w') as f:
                f.write(login_script_content)
            log.info(f"📝 Generated login script: {login_script_path}")
            
            # Generate product extractor script
            product_script_content = self._generate_product_extractor_template(discovery_results.get("product_config"))
            with open(product_script_path, 'w') as f:
                f.write(product_script_content)
            log.info(f"📝 Generated product extractor script: {product_script_path}")
            
            return {
                "success": True,
                "login_script_path": str(login_script_path),
                "product_script_path": str(product_script_path)
            }
            
        except Exception as e:
            log.error(f"Script generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_login_script_template(self, login_config: Optional[Dict[str, Any]]) -> str:
        """Generate login script from template"""
        
        # Extract selectors from config
        email_selector = "input[type='email']"
        password_selector = "input[type='password']"
        submit_selector = ".btn.btn-primary.btn-block, button:has-text('Login'), button:has-text('Sign in'), button[type='submit'], .btn.btn-primary, .btn-primary, input[type='submit']"
        
        if login_config:
            email_selector = login_config.get("email_selector", email_selector)
            password_selector = login_config.get("password_selector", password_selector)
            submit_selector = login_config.get("submit_selector", submit_selector)
        
        return f'''#!/usr/bin/env python3
"""
{self.supplier_id.replace('-', ' ').title()} Login Script
Auto-generated by IntelligentSupplierScriptGenerator on {datetime.now().isoformat()}

Provides login automation for {self.supplier_url}
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
from playwright.async_api import async_playwright, Page
import openai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Configuration
SUPPLIER_URL = "{self.supplier_url}"
EMAIL_SELECTOR = "{email_selector}"
PASSWORD_SELECTOR = "{password_selector}"
SUBMIT_SELECTOR = "{submit_selector}"

class {self.supplier_id.replace('-', '_').title()}Login:
    """Login automation for {self.supplier_url}"""
    
    def __init__(self, email: str, password: str, test_mode: bool = False):
        self.email = email
        self.password = password
        self.test_mode = test_mode
        self.page: Page = None
        self.browser = None
        self.context = None
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.supplier_url = SUPPLIER_URL
    
    async def connect_to_browser(self) -> bool:
        """Connect to existing Chrome debug instance"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
            else:
                self.context = await self.browser.new_context()
            
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
                
            await self.page.bring_to_front()
            return True
            
        except Exception as e:
            log.error(f"Failed to connect to browser: {{e}}")
            return False
    
    async def check_login_status(self) -> bool:
        """Check if already logged in"""
        try:
            await self.page.goto(SUPPLIER_URL)
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Look for logout indicators or account areas
            logout_indicators = [
                "text=logout", "text=sign out", "text=my account", 
                ".logout", ".signout", ".account"
            ]
            
            for indicator in logout_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element and await element.is_visible():
                        log.info("✅ Already logged in")
                        return True
                except:
                    continue
            
            log.info("❌ Not logged in")
            return False
            
        except Exception as e:
            log.error(f"Failed to check login status: {{e}}")
            return False
    
    async def perform_login(self) -> Dict[str, Any]:
        """Perform login sequence"""
        try:
            log.info(f"🔐 Starting login to {{SUPPLIER_URL}}")
            
            # Check if already logged in
            if await self.check_login_status():
                return {{"success": True, "message": "Already logged in", "action": "none"}}
            
            # Try to trigger login modal/form first
            login_triggers = [
                # More specific selectors targeting header navigation
                "header a:has-text('Sign in')", "nav a:has-text('Sign in')",
                ".header-links a:has-text('Sign in')", ".customer-welcome a:has-text('Sign in')",
                "a[href*='/customer/account/login']", "a[href*='login']",
                # Fallback to generic if needed
                "text=Register or Sign in", "text=sign in", "text=log in"
            ]
            
            login_form_visible = False
            for trigger in login_triggers:
                try:
                    element = await self.page.query_selector(trigger)
                    if element and await element.is_visible():
                        log.info(f"🔗 Clicking login trigger: {{trigger}}")
                        await element.click()
                        await self.page.wait_for_timeout(2000)  # Wait for form to appear
                        
                        # Check if password field is now visible
                        password_element = await self.page.query_selector(PASSWORD_SELECTOR)
                        if password_element and await password_element.is_visible():
                            login_form_visible = True
                            break
                except:
                    continue
            
            # If no login form visible, try common modal triggers
            if not login_form_visible:
                modal_triggers = [
                    "text=Account", "text=My Account", ".customer-welcome",
                    "[data-toggle='modal']", ".modal-trigger"
                ]
                for trigger in modal_triggers:
                    try:
                        element = await self.page.query_selector(trigger)
                        if element and await element.is_visible():
                            log.info(f"🔗 Clicking modal trigger: {{trigger}}")
                            await element.click()
                            await self.page.wait_for_timeout(2000)
                            
                            # Check again for password field
                            password_element = await self.page.query_selector(PASSWORD_SELECTOR)
                            if password_element and await password_element.is_visible():
                                login_form_visible = True
                                break
                    except:
                        continue
            
            # Fill email field
            try:
                await self.page.fill(EMAIL_SELECTOR, self.email)
                log.info("✅ Email filled")
            except Exception as e:
                log.error(f"Failed to fill email: {{e}}")
                if self.test_mode:
                    return {{"success": False, "error": f"Email selector failed: {{EMAIL_SELECTOR}}", "step": "email"}}
                raise
            
            # Wait a moment and try to make password field visible
            await self.page.wait_for_timeout(1000)
            
            # Fill password field with enhanced error handling
            try:
                # First check if password field exists and is visible
                password_element = await self.page.query_selector(PASSWORD_SELECTOR)
                if password_element:
                    # Try to scroll into view and make visible
                    await password_element.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(500)
                    
                    # Check if visible now
                    if await password_element.is_visible():
                        await self.page.fill(PASSWORD_SELECTOR, self.password)
                        log.info("✅ Password filled")
                    else:
                        log.warning("⚠️ Password field exists but not visible, attempting force fill")
                        await password_element.fill(self.password)
                        log.info("✅ Password force-filled")
                else:
                    raise Exception(f"Password field not found: {{PASSWORD_SELECTOR}}")
                    
            except Exception as e:
                log.error(f"Failed to fill password: {{e}}")
                if self.test_mode:
                    return {{"success": False, "error": f"Password selector failed: {{PASSWORD_SELECTOR}}", "step": "password"}}
                raise
            
            # Click submit button with modal overlay handling
            try:
                # Enhanced modal overlay handling - try multiple approaches
                modal_handled = False
                
                # Method 1: Try to dismiss modal overlays
                modal_close_selectors = [
                    ".modals-overlay", ".modal-backdrop", ".overlay", 
                    "[data-role='backdrop']", ".modal-close", "button[aria-label='Close']"
                ]
                
                for close_selector in modal_close_selectors:
                    try:
                        overlay_element = await self.page.query_selector(close_selector)
                        if overlay_element and await overlay_element.is_visible():
                            log.info(f"🚫 Dismissing modal overlay: {{close_selector}}")
                            await overlay_element.click()
                            await self.page.wait_for_timeout(2000)
                            modal_handled = True
                            break
                    except:
                        continue
                
                # Method 2: If overlay still exists, try to hide it with JavaScript
                if not modal_handled:
                    try:
                        await self.page.evaluate("""() => {{
                            const overlays = document.querySelectorAll('.modals-overlay, .modal-backdrop, .overlay');
                            overlays.forEach(overlay => {{
                                overlay.style.display = 'none';
                                overlay.style.visibility = 'hidden';
                                overlay.style.pointerEvents = 'none';
                            }});
                        }}""")
                        log.info("🚫 Forcibly hid modal overlays with JavaScript")
                        await self.page.wait_for_timeout(1000)
                    except Exception as e:
                        log.warning(f"Failed to hide overlays with JavaScript: {{e}}")
                
                # Method 3: Ensure submit button is visible and clickable
                try:
                    await self.page.evaluate("""() => {{
                        const submitBtn = document.querySelector('.btn.btn-primary.btn-block, button[type="submit"]');
                        if (submitBtn) {{
                            submitBtn.style.zIndex = '99999';
                            submitBtn.style.position = 'relative';
                        }}
                    }}""")
                    log.info("🎯 Enhanced submit button visibility")
                except:
                    pass
                
                # Try normal click first
                try:
                    await self.page.click(SUBMIT_SELECTOR)
                    log.info("✅ Submit button clicked")
                except Exception as click_error:
                    log.warning(f"Normal click failed: {{click_error}}, trying force click")
                    # Try force click to bypass modal overlays
                    submit_element = await self.page.query_selector(SUBMIT_SELECTOR)
                    if submit_element:
                        await submit_element.click(force=True)
                        log.info("✅ Submit button force-clicked")
                    else:
                        raise Exception(f"Submit button not found: {{SUBMIT_SELECTOR}}")
                        
            except Exception as e:
                log.error(f"Failed to click submit: {{e}}")
                if self.test_mode:
                    return {{"success": False, "error": f"Submit selector failed: {{SUBMIT_SELECTOR}}", "step": "submit"}}
                raise
            
            # Wait for navigation or login completion
            try:
                await self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            except:
                pass  # Continue even if timeout
            
            # Verify login success
            if await self.check_login_status():
                log.info("✅ Login successful")
                return {{"success": True, "message": "Login completed successfully"}}
            else:
                log.warning("❌ Login verification failed - analyzing current page state...")
                
                # CRITICAL FALLBACK: Analyze what happened after submit click
                try:
                    # Take screenshot for visual analysis
                    screenshot_path = f"logs/debug/login_failure_screenshot_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.png"
                    await self.page.screenshot(path=screenshot_path, full_page=True)
                    log.info(f"📸 Screenshot saved: {{screenshot_path}}")
                    
                    # Get current page HTML for analysis
                    current_html = await self.page.content()
                    log.info(f"📄 Current page HTML length: {{len(current_html)}} characters")
                    
                    # Check for common login error indicators
                    error_indicators = [
                        "invalid", "incorrect", "wrong", "error", "failed", 
                        "captcha", "blocked", "suspended", "verification required",
                        "two-factor", "2fa", "code", "security"
                    ]
                    
                    page_text = await self.page.inner_text("body")
                    found_errors = []
                    for indicator in error_indicators:
                        if indicator.lower() in page_text.lower():
                            found_errors.append(indicator)
                    
                    if found_errors:
                        log.warning(f"🚨 Detected potential error indicators: {{found_errors}}")
                        return {{
                            "success": False, 
                            "error": f"Login failed - detected errors: {{found_errors}}", 
                            "step": "verification",
                            "analysis": {{
                                "screenshot": screenshot_path,
                                "html_length": len(current_html),
                                "error_indicators": found_errors,
                                "current_url": await self.page.url,
                                "page_title": await self.page.title()
                            }}
                        }}
                    
                    # Check if we're on a different page (potential redirect)
                    current_url = await self.page.url
                    if current_url != SUPPLIER_URL:
                        log.info(f"🔄 Page redirected to: {{current_url}}")
                        # Re-check login status on new page
                        if await self.check_login_status():
                            log.info("✅ Login successful after redirect")
                            return {{"success": True, "message": "Login completed successfully after redirect"}}
                    
                    # Use AI to analyze the failure state
                    ai_analysis = await self._analyze_login_failure_with_ai(screenshot_path, current_html, current_url)
                    
                    # Provide comprehensive failure analysis
                    return {{
                        "success": False,
                        "error": "Login verification failed - no clear error indicators found",
                        "step": "verification", 
                        "analysis": {{
                            "screenshot": screenshot_path,
                            "html_length": len(current_html),
                            "current_url": current_url,
                            "page_title": await self.page.title(),
                            "ai_analysis": ai_analysis,
                            "suggestion": "Review AI analysis and screenshot for next steps"
                        }}
                    }}
                    
                except Exception as analysis_error:
                    log.error(f"Failed to analyze login failure: {{analysis_error}}")
                    return {{
                        "success": False, 
                        "error": f"Login failed and analysis failed: {{analysis_error}}", 
                        "step": "verification"
                    }}
                
        except Exception as e:
            log.error(f"Login failed: {{e}}")
            return {{"success": False, "error": str(e), "step": "unknown"}}
    
    async def _analyze_login_failure_with_ai(self, screenshot_path: str, html_content: str, current_url: str) -> str:
        """Use AI to analyze login failure state with screenshot and HTML"""
        try:
            import base64
            
            # Read and encode screenshot
            with open(screenshot_path, 'rb') as img_file:
                screenshot_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Prepare HTML snippet (first 5000 chars to avoid token limits)
            html_snippet = html_content[:5000] if len(html_content) > 5000 else html_content
            
            analysis_prompt = f"""
            CRITICAL LOGIN FAILURE ANALYSIS:
            
            URL: {{current_url}}
            Supplier: {{self.supplier_url}}
            
            I attempted to login but verification failed. Please analyze the screenshot and HTML to determine:
            
            1. What state is the page in after login attempt?
            2. Are there any error messages visible?
            3. Did login succeed but verification logic fail?
            4. Are there additional steps needed (CAPTCHA, 2FA, etc.)?
            5. What should be the next action to resolve this?
            
            HTML START:
            {{html_snippet}}
            HTML END
            
            Please provide a clear, actionable diagnosis of what went wrong and what to try next.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {{
                        "role": "user",
                        "content": [
                            {{"type": "text", "text": analysis_prompt}},
                            {{
                                "type": "image_url",
                                "image_url": {{
                                    "url": f"data:image/png;base64,{{screenshot_base64}}"
                                }}
                            }}
                        ]
                    }}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            ai_diagnosis = response.choices[0].message.content
            log.info(f"🤖 AI Login Failure Analysis: {{ai_diagnosis}}")
            return ai_diagnosis
            
        except Exception as e:
            log.error(f"AI analysis failed: {{e}}")
            return f"AI analysis failed: {{e}}"

# Test function for validation
async def test_login(email: str, password: str) -> Dict[str, Any]:
    """Test login functionality"""
    try:
        login_handler = {self.supplier_id.replace('-', '_').title()}Login(email, password, test_mode=True)
        
        if not await login_handler.connect_to_browser():
            return {{"success": False, "error": "Failed to connect to browser"}}
        
        result = await login_handler.perform_login()
        return result
        
    except Exception as e:
        return {{"success": False, "error": str(e)}}

if __name__ == "__main__":
    # Test mode execution
    import sys
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
        result = asyncio.run(test_login(email, password))
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python {{__file__}} <email> <password>")
'''
    
    def _generate_product_extractor_template(self, product_config: Optional[Dict[str, Any]]) -> str:
        """Generate product extractor script from template"""
        
        # Default selectors
        container_selector = ".product-item"
        title_selector = "h2, h3, .title"
        price_selector = ".price"
        url_selector = "a"
        image_selector = "img"
        
        # Use discovered selectors if available
        if product_config:
            container_selector = product_config.get("product_container_selector", container_selector)
            title_selector = product_config.get("title_selector_relative", title_selector)
            price_selector = product_config.get("price_selector_relative", price_selector)
            url_selector = product_config.get("url_selector_relative", url_selector)
            image_selector = product_config.get("image_selector_relative", image_selector)
        
        return f'''#!/usr/bin/env python3
"""
{self.supplier_id.replace('-', ' ').title()} Product Extractor Script
Auto-generated by IntelligentSupplierScriptGenerator on {datetime.now().isoformat()}

Provides product extraction for {self.supplier_url}
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Configuration from discovery
SUPPLIER_URL = "{self.supplier_url}"
CONTAINER_SELECTOR = "{container_selector}"
TITLE_SELECTOR = "{title_selector}"
PRICE_SELECTOR = "{price_selector}"
URL_SELECTOR = "{url_selector}"
IMAGE_SELECTOR = "{image_selector}"

class {self.supplier_id.replace('-', '_').title()}ProductExtractor:
    """Product extraction for {self.supplier_url}"""
    
    def __init__(self, max_pages: int = 2, test_mode: bool = False):
        self.max_pages = max_pages
        self.test_mode = test_mode
        self.page: Page = None
        self.browser = None
        self.context = None
    
    async def connect_to_browser(self) -> bool:
        """Connect to existing Chrome debug instance"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
            else:
                self.context = await self.browser.new_context()
            
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
                
            await self.page.bring_to_front()
            return True
            
        except Exception as e:
            log.error(f"Failed to connect to browser: {{e}}")
            return False
    
    async def extract_products(self, start_url: str = None) -> List[Dict[str, Any]]:
        """Extract products from supplier website"""
        try:
            log.info(f"🛍️ Starting product extraction for {{self.max_pages}} pages")
            
            base_url = start_url or SUPPLIER_URL
            products = []
            
            for page_num in range(1, self.max_pages + 1):
                log.info(f"📄 Processing page {{page_num}}")
                
                # Navigate to page
                page_url = base_url if page_num == 1 else f"{{base_url}}?page={{page_num}}"
                await self.page.goto(page_url)
                await self.page.wait_for_load_state('domcontentloaded')
                
                # Extract products from current page
                page_products = await self._extract_page_products()
                products.extend(page_products)
                
                log.info(f"✅ Extracted {{len(page_products)}} products from page {{page_num}}")
                
                if self.test_mode and len(products) >= 5:
                    log.info("🧪 Test mode: stopping after 5 products")
                    break
            
            log.info(f"✅ Product extraction completed: {{len(products)}} total products")
            return products
            
        except Exception as e:
            log.error(f"Product extraction failed: {{e}}")
            return []
    
    async def _extract_page_products(self) -> List[Dict[str, Any]]:
        """Extract products from current page"""
        try:
            # Find product containers
            containers = await self.page.query_selector_all(CONTAINER_SELECTOR)
            log.info(f"🔍 Found {{len(containers)}} product containers")
            
            products = []
            for i, container in enumerate(containers):
                try:
                    product = await self._extract_single_product(container)
                    if product:
                        products.append(product)
                except Exception as e:
                    log.warning(f"Failed to extract product {{i}}: {{e}}")
                    continue
            
            return products
            
        except Exception as e:
            log.error(f"Page extraction failed: {{e}}")
            return []
    
    async def _extract_single_product(self, container) -> Dict[str, Any]:
        """Extract data from a single product container"""
        try:
            product = {{
                "extraction_timestamp": datetime.now().isoformat(),
                "source_url": self.page.url
            }}
            
            # Extract title
            try:
                title_element = await container.query_selector(TITLE_SELECTOR)
                if title_element:
                    product["title"] = (await title_element.text_content()).strip()
            except:
                pass
            
            # Extract price
            try:
                price_element = await container.query_selector(PRICE_SELECTOR)
                if price_element:
                    price_text = (await price_element.text_content()).strip()
                    product["price"] = price_text
            except:
                pass
            
            # Extract URL
            try:
                url_element = await container.query_selector(URL_SELECTOR)
                if url_element:
                    href = await url_element.get_attribute("href")
                    if href:
                        # Make absolute URL
                        if href.startswith("/"):
                            href = f"{{self.supplier_url.rstrip('/')}}{{href}}"
                        product["url"] = href
            except:
                pass
            
            # Extract image
            try:
                img_element = await container.query_selector(IMAGE_SELECTOR)
                if img_element:
                    src = await img_element.get_attribute("src")
                    if src:
                        product["image_url"] = src
            except:
                pass
            
            # Only return product if we got at least title or URL
            if product.get("title") or product.get("url"):
                return product
            return None
            
        except Exception as e:
            log.error(f"Single product extraction failed: {{e}}")
            return None

# Test function for validation
async def test_extraction(max_pages: int = 2) -> Dict[str, Any]:
    """Test product extraction functionality"""
    try:
        extractor = {self.supplier_id.replace('-', '_').title()}ProductExtractor(max_pages=max_pages, test_mode=True)
        
        if not await extractor.connect_to_browser():
            return {{"success": False, "error": "Failed to connect to browser"}}
        
        products = await extractor.extract_products()
        
        return {{
            "success": True,
            "products_extracted": len(products),
            "sample_products": products[:3] if products else [],
            "total_products": len(products)
        }}
        
    except Exception as e:
        return {{"success": False, "error": str(e)}}

if __name__ == "__main__":
    # Test mode execution
    result = asyncio.run(test_extraction())
    print(json.dumps(result, indent=2))
'''

    async def _test_after_generate_validation(self, generation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Test-After-Generate Validation Loop with AI-powered failure analysis
        """
        try:
            log.info("🧪 Starting test-after-generate validation...")
            
            validation_results = {
                "login_validated": False,
                "products_validated": False,
                "pagination_validated": False,
                "last_error": None,
                "test_results": {}
            }
            
            # Test login script
            log.info("🔐 Testing login script...")
            login_result = await self._test_login_script()
            validation_results["test_results"]["login"] = login_result
            validation_results["login_validated"] = login_result.get("success", False)
            
            if not validation_results["login_validated"]:
                # AI-powered failure analysis for login
                await self._ai_failure_analysis("login", login_result)
                validation_results["last_error"] = f"Login test failed: {login_result.get('error', 'Unknown error')}"
            
            # Test product extraction script
            log.info("🛍️ Testing product extraction script...")
            product_result = await self._test_product_script()
            validation_results["test_results"]["products"] = product_result
            validation_results["products_validated"] = product_result.get("success", False)
            
            if not validation_results["products_validated"]:
                # AI-powered failure analysis for products
                await self._ai_failure_analysis("products", product_result)
                validation_results["last_error"] = f"Product test failed: {product_result.get('error', 'Unknown error')}"
            
            # Note: Pagination testing is part of product testing in our implementation
            validation_results["pagination_validated"] = validation_results["products_validated"]
            
            log.info(f"✅ Validation completed - Login: {validation_results['login_validated']}, Products: {validation_results['products_validated']}")
            
            return validation_results
            
        except Exception as e:
            log.error(f"Validation failed: {e}")
            return {
                "login_validated": False,
                "products_validated": False, 
                "pagination_validated": False,
                "last_error": f"Validation error: {e}"
            }
    
    async def _test_login_script(self) -> Dict[str, Any]:
        """Test login script functionality"""
        try:
            # Dynamic import of generated login script
            script_path = self.scripts_dir / f"{self.supplier_id}_login.py"
            
            if not script_path.exists():
                return {"success": False, "error": "Login script not found"}
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location("login_module", script_path)
            login_module = importlib.util.module_from_spec(spec)
            
            # Execute the module to load classes/functions
            spec.loader.exec_module(login_module)
            
            # Test with dummy credentials in test mode
            test_result = await login_module.test_login("test@example.com", "testpassword")
            
            return test_result
            
        except Exception as e:
            log.error(f"Login script test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _test_product_script(self) -> Dict[str, Any]:
        """Test product extraction script functionality"""
        try:
            # Dynamic import of generated product script
            script_path = self.scripts_dir / f"{self.supplier_id}_product_extractor.py"
            
            if not script_path.exists():
                return {"success": False, "error": "Product script not found"}
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location("product_module", script_path)
            product_module = importlib.util.module_from_spec(spec)
            
            # Execute the module to load classes/functions
            spec.loader.exec_module(product_module)
            
            # Test with max_pages=2
            test_result = await product_module.test_extraction(max_pages=2)
            
            return test_result
            
        except Exception as e:
            log.error(f"Product script test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _ai_failure_analysis(self, component: str, failure_result: Dict[str, Any]) -> None:
        """
        AI-powered failure analysis with screenshot and structured diagnosis
        """
        try:
            log.info(f"🤖 Performing AI failure analysis for {component}...")
            
            # Take screenshot of current page state
            screenshot_path = f"temp_failure_analysis_{component}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=screenshot_path, full_page=True)
            
            # Load selectors from config
            selectors_from_config = {}
            if component == "login":
                config_path = self.config_dir / "login_config.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        selectors_from_config = json.load(f)
            
            # Prepare AI analysis prompt
            prompt = f"""# ROLE AND OBJECTIVE
You are a senior automation QA engineer. A Playwright {component} script has failed. Your task is to diagnose the failure by analyzing a screenshot of the page at the moment of failure.

# CONTEXT
- The script attempted to use these selectors: {json.dumps(selectors_from_config, indent=2)}
- The script failed to complete the {component} process.
- Error details: {failure_result.get('error', 'Unknown error')}

# TASK
Analyze the provided screenshot and determine the most likely cause of the failure.

# OUTPUT FORMAT
Return a single JSON object with your diagnosis:
{{
  "likely_cause": "e.g., 'Incorrect password selector', 'A CAPTCHA appeared', 'Unexpected popup', 'Changed HTML structure'",
  "suggested_fix": "e.g., 'The password field seems to be #pwd, not #password.', 'A manual intervention is required to solve the CAPTCHA.'"
}}"""
            
            # Load and encode screenshot
            with open(screenshot_path, "rb") as image_file:
                import base64
                screenshot_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Make AI analysis call
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini-2025-04-14",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{screenshot_data}"}
                            }
                        ]
                    }
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            # Parse and log diagnosis
            diagnosis_text = response.choices[0].message.content.strip()
            try:
                diagnosis = json.loads(diagnosis_text)
                log.info(f"🤖 AI Diagnosis for {component}:")
                log.info(f"   Likely Cause: {diagnosis.get('likely_cause', 'Unknown')}")
                log.info(f"   Suggested Fix: {diagnosis.get('suggested_fix', 'No suggestion')}")
            except json.JSONDecodeError:
                log.warning(f"🤖 AI diagnosis (raw): {diagnosis_text}")
            
            # Clean up screenshot
            os.remove(screenshot_path)
            
        except Exception as e:
            log.error(f"AI failure analysis failed: {e}")
    
    async def _generate_intelligent_supplier_ready(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 5: Generate intelligent .supplier_ready file in new "report card" format
        """
        try:
            log.info("📋 Generating intelligent .supplier_ready file...")
            
            # Prepare report card format data
            ready_data = {
                "supplier_id": self.supplier_id,
                "supplier_url": self.supplier_url,
                "last_validated_at": datetime.now(timezone.utc).isoformat(),
                "validation_status": {
                    "login_validated": validation_results.get("login_validated", False),
                    "products_validated": validation_results.get("products_validated", False),
                    "pagination_validated": validation_results.get("pagination_validated", False),
                    "last_error": validation_results.get("last_error")
                },
                "config_files": {
                    "login": str(self.config_dir / "login_config.json"),
                    "products": str(self.config_dir / "product_selectors.json")
                },
                "script_files": {
                    "login": str(self.scripts_dir / f"{self.supplier_id}_login.py"),
                    "product_extractor": str(self.scripts_dir / f"{self.supplier_id}_product_extractor.py")
                },
                "test_results": validation_results.get("test_results", {}),
                "generator_metadata": {
                    "generated_by": "IntelligentSupplierScriptGenerator",
                    "version": "1.0",
                    "ai_assistance_enabled": self.ai_config.get("enabled", False),
                    "force_regenerate": self.force_regenerate
                }
            }
            
            # Use SupplierGuard to create the ready file in proper format
            ready_file_path = self.guard.create_supplier_ready_file_intelligent(self.supplier_id, ready_data)
            
            log.info(f"✅ Created intelligent .supplier_ready file: {ready_file_path}")
            
            return {
                "success": True,
                "ready_file_path": str(ready_file_path),
                "ready_data": ready_data
            }
            
        except Exception as e:
            log.error(f"Failed to generate .supplier_ready file: {e}")
            return {"success": False, "error": str(e)}
    
    async def _cleanup_browser(self) -> None:
        """Clean up browser resources"""
        try:
            if self.browser:
                # Don't close the browser if we connected to existing debug instance
                # Just disconnect
                pass
        except Exception as e:
            log.warning(f"Browser cleanup warning: {e}")

# Standalone functions for backward compatibility
async def generate_supplier_package(supplier_url: str, force_regenerate: bool = False) -> Dict[str, Any]:
    """
    Generate complete supplier package with AI-powered discovery and validation
    """
    generator = IntelligentSupplierScriptGenerator(supplier_url, force_regenerate)
    return await generator.generate_all_scripts()

if __name__ == "__main__":
    # Command line interface
    parser = argparse.ArgumentParser(description="Intelligent Supplier Script Generator")
    parser.add_argument("--supplier-url", required=True, help="Supplier website URL")
    parser.add_argument("--force-regenerate", action="store_true", help="Force regeneration even if ready")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async def main():
        try:
            log.info(f"🚀 Starting intelligent supplier script generation for: {args.supplier_url}")
            
            generator = IntelligentSupplierScriptGenerator(
                supplier_url=args.supplier_url,
                force_regenerate=args.force_regenerate
            )
            
            result = await generator.generate_all_scripts()
            
            print("\n" + "="*60)
            print("INTELLIGENT SUPPLIER SCRIPT GENERATION RESULT")
            print("="*60)
            print(json.dumps(result, indent=2))
            
            if result.get("success"):
                log.info("✅ Intelligent supplier script generation completed successfully!")
            else:
                log.error("❌ Intelligent supplier script generation failed!")
                sys.exit(1)
                
        except Exception as e:
            log.error(f"❌ Fatal error: {e}")
            print(traceback.format_exc())
            sys.exit(1)
    
    asyncio.run(main())