#!/usr/bin/env python3
"""
Code validation script for MetaStream Aggregator

This script checks for common issues in the codebase and validates
configuration files to help identify potential bugs.
"""

import os
import json
import re
import sys
import importlib
import logging
from typing import Dict, List, Tuple, Any, Set

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("code_validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MSA-Code-Validator")

# Constants
CONFIG_FILES = [
    "sites.json",
    "settings.json"
]

PYTHON_FILES = [
    "app.py",
    "site_scraper.py",
    "ranker.py",
    "link_checker.py",
    "config_manager.py",
    "cache_manager.py"
]

JS_FILES = [
    "static/js/app.js",
    "static/js/search-manager.js",
    "static/js/player-manager.js",
    "static/js/ui-manager.js"
]

CSS_FILES = [
    "static/css/style.css"
]

HTML_FILES = [
    "templates/index.html"
]

class CodeValidator:
    """Validates code and configuration files for common issues."""
    
    def __init__(self):
        """Initialize the validator."""
        self.issues_found = 0
        self.files_checked = 0
        self.current_file = ""
    
    def validate_all(self) -> bool:
        """Run all validation checks and return success status."""
        logger.info("Starting code validation...")
        
        # Validate config files
        for config_file in CONFIG_FILES:
            self.validate_json_file(config_file)
            
        # Check Python files
        for py_file in PYTHON_FILES:
            self.validate_python_file(py_file)
            
        # Check JavaScript files
        for js_file in JS_FILES:
            self.validate_js_file(js_file)
            
        # Check CSS files
        for css_file in CSS_FILES:
            self.validate_css_file(css_file)
            
        # Check HTML files
        for html_file in HTML_FILES:
            self.validate_html_file(html_file)
        
        # Validate cross-file dependencies
        self.validate_dependencies()
        
        # Check for inconsistent configurations
        self.validate_configuration_consistency()
        
        # Report results
        if self.issues_found > 0:
            logger.warning(f"Validation completed with {self.issues_found} issues in {self.files_checked} files.")
            return False
        else:
            logger.info(f"Validation completed successfully! {self.files_checked} files checked with no issues.")
            return True
    
    def report_issue(self, message: str, line_num: int = None) -> None:
        """
        Report an issue found during validation.
        
        Args:
            message: Description of the issue
            line_num: Line number where the issue was found (optional)
        """
        location = f"{self.current_file}"
        if line_num is not None:
            location += f" (line {line_num})"
            
        logger.warning(f"ISSUE: {location}: {message}")
        self.issues_found += 1
    
    def validate_json_file(self, filename: str) -> None:
        """
        Validate a JSON configuration file.
        
        Args:
            filename: Path to the JSON file
        """
        self.current_file = filename
        
        if not os.path.exists(filename):
            logger.info(f"Skipping {filename} (file not found)")
            return
            
        self.files_checked += 1
        logger.info(f"Validating JSON file: {filename}")
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Check if it's a dictionary
            if not isinstance(data, dict):
                self.report_issue("JSON file does not contain a dictionary/object")
                return
                
            # Specific checks for sites.json
            if filename.endswith("sites.json"):
                self._validate_sites_config(data)
                
            # Specific checks for settings.json
            elif filename.endswith("settings.json"):
                self._validate_settings_config(data)
                
        except json.JSONDecodeError as e:
            self.report_issue(f"Invalid JSON: {e}")
        except Exception as e:
            self.report_issue(f"Error validating file: {e}")
    
    def _validate_sites_config(self, sites_data: Dict) -> None:
        """
        Validate site configuration data.
        
        Args:
            sites_data: The site configuration dictionary
        """
        # Check each site configuration
        for site_id, config in sites_data.items():
            if not isinstance(config, dict):
                self.report_issue(f"Site '{site_id}' configuration is not a dictionary")
                continue
                
            # Check required fields
            required_fields = ['name', 'base_url', 'search_method']
            for field in required_fields:
                if field not in config:
                    self.report_issue(f"Site '{site_id}' is missing required field: {field}")
            
            # Check search method and required fields
            search_method = config.get('search_method')
            if search_method == 'scrape_search_page':
                if 'search_url_template' not in config:
                    self.report_issue(f"Site '{site_id}' uses scrape_search_page but is missing search_url_template")
                
                # Check URL template format
                url_template = config.get('search_url_template', '')
                if url_template and '{query}' not in url_template:
                    self.report_issue(f"Site '{site_id}' search_url_template is missing {{query}} placeholder")
                
                # Check essential selectors
                essential_selectors = [
                    'results_container_selector',
                    'result_item_selector',
                    'title_selector',
                    'video_url_selector'
                ]
                for selector in essential_selectors:
                    if selector not in config:
                        self.report_issue(f"Site '{site_id}' is missing essential selector: {selector}")
            
            elif search_method in ['google_site_search', 'bing_site_search', 'duckduckgo_site_search']:
                # These methods require base_url but no other specific fields
                if not config.get('base_url'):
                    self.report_issue(f"Site '{site_id}' uses {search_method} but is missing base_url")
            
            elif search_method == 'api':
                # API method might need specific fields defined in the future
                pass
            
            else:
                self.report_issue(f"Site '{site_id}' has unknown search_method: {search_method}")
    
    def _validate_settings_config(self, settings_data: Dict) -> None:
        """
        Validate settings configuration data.
        
        Args:
            settings_data: The settings configuration dictionary
        """
        # Check essential settings
        essential_settings = [
            'results_per_page_default',
            'cache_expiry_minutes'
        ]
        for setting in essential_settings:
            if setting not in settings_data:
                self.report_issue(f"Settings is missing essential field: {setting}")
        
        # Check types for numeric settings
        numeric_settings = [
            'results_per_page_default',
            'cache_expiry_minutes',
            'max_pages_per_site'
        ]
        for setting in numeric_settings:
            if setting in settings_data and not isinstance(settings_data[setting], (int, float)):
                self.report_issue(f"Setting '{setting}' should be a number but is {type(settings_data[setting]).__name__}")
        
        # Check scoring weights
        if 'scoring_weights' in settings_data:
            weights = settings_data['scoring_weights']
            if not isinstance(weights, dict):
                self.report_issue("scoring_weights should be a dictionary")
            else:
                expected_weights = [
                    'relevance_weight',
                    'rating_weight',
                    'views_weight',
                    'multiplier_effect'
                ]
                for weight in expected_weights:
                    if weight not in weights:
                        self.report_issue(f"scoring_weights is missing {weight}")
                    elif not isinstance(weights[weight], (int, float)):
                        self.report_issue(f"scoring_weight.{weight} should be a number")
                
                # Check if weights sum to approximately 1.0
                weight_sum = sum(float(weights.get(w, 0)) for w in expected_weights)
                if not 0.99 <= weight_sum <= 1.01:  # Allow small rounding errors
                    self.report_issue(f"scoring_weights sum to {weight_sum}, not 1.0")
    
    def validate_python_file(self, filename: str) -> None:
        """
        Validate a Python source file.
        
        Args:
            filename: Path to the Python file
        """
        self.current_file = filename
        
        if not os.path.exists(filename):
            logger.info(f"Skipping {filename} (file not found)")
            return
            
        self.files_checked += 1
        logger.info(f"Validating Python file: {filename}")
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for syntax errors
            try:
                compile(content, filename, 'exec')
            except SyntaxError as e:
                self.report_issue(f"Syntax error: {e}", e.lineno)
                return
            
            # Check for common issues
            for i, line in enumerate(lines, 1):
                # Check for hardcoded credentials
                if re.search(r'(api_key|password|secret|token)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                    if not any(ignore in line for ignore in ['os.environ.get', 'USER_SETTINGS.get']):
                        self.report_issue("Possible hardcoded credential", i)
                
                # Check for print statements (should use logging)
                if re.match(r'\s*print\(', line) and 'debug' not in filename:
                    self.report_issue("Using print() instead of logger", i)
                
                # Check for bare except clauses
                if re.search(r'except\s*:', line):
                    self.report_issue("Bare except clause", i)
                
                # Check for possible SQL injection
                if re.search(r'execute\([^)]*\+|execute\([^)]*%', line):
                    self.report_issue("Possible SQL injection vulnerability", i)
                
                # Check for potential resource leaks
                if 'open(' in line and 'with' not in line:
                    self.report_issue("File opened without 'with' statement (potential resource leak)", i)
            
            # Try to import the module to check for import errors
            if filename.endswith('.py'):
                module_name = os.path.splitext(os.path.basename(filename))[0]
                try:
                    if module_name in sys.modules:
                        # Module already imported, reload it
                        importlib.reload(sys.modules[module_name])
                    else:
                        # Import the module
                        importlib.import_module(module_name)
                except ImportError as e:
                    self.report_issue(f"Import error: {e}")
                except Exception as e:
                    self.report_issue(f"Module error: {e}")
        
        except Exception as e:
            self.report_issue(f"Error validating file: {e}")
    
    def validate_js_file(self, filename: str) -> None:
        """
        Validate a JavaScript file.
        
        Args:
            filename: Path to the JavaScript file
        """
        self.current_file = filename
        
        if not os.path.exists(filename):
            logger.info(f"Skipping {filename} (file not found)")
            return
            
        self.files_checked += 1
        logger.info(f"Validating JavaScript file: {filename}")
        
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                # Check for console.log statements (should be removed in production)
                if re.search(r'console\.log\(', line):
                    self.report_issue("console.log() statement", i)
                
                # Check for hardcoded API endpoints (should be configurable)
                if re.search(r'fetch\(["\']https?://', line):
                    self.report_issue("Hardcoded API endpoint URL", i)
                
                # Check for potential XSS vulnerabilities
                if re.search(r'innerHTML\s*=', line) and not re.search(r'innerHTML\s*=.*escapeHtml', line):
                    self.report_issue("Potential XSS vulnerability (unescaped innerHTML)", i)
                
                # Check for alert/confirm/prompt (usually bad UX)
                if re.search(r'(alert|confirm|prompt)\(', line) and 'debug' not in filename:
                    self.report_issue("Using alert/confirm/prompt instead of custom UI", i)
                
                # Check for eval (security risk)
                if re.search(r'eval\(', line):
                    self.report_issue("Using eval() (security risk)", i)
        
        except Exception as e:
            self.report_issue(f"Error validating file: {e}")
    
    def validate_css_file(self, filename: str) -> None:
        """
        Validate a CSS file.
        
        Args:
            filename: Path to the CSS file
        """
        self.current_file = filename
        
        if not os.path.exists(filename):
            logger.info(f"Skipping {filename} (file not found)")
            return
            
        self.files_checked += 1
        logger.info(f"Validating CSS file: {filename}")
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            # Check for common CSS issues
            
            # Check for vendor prefixes consistency
            prefixes = re.findall(r'(-webkit-|-moz-|-ms-|-o-)[a-zA-Z-]+', content)
            prefix_set = set([p.split('-')[1] for p in prefixes if p.split('-')[1]])
            if len(prefix_set) > 0 and len(prefix_set) < 4:
                missing = set(['webkit', 'moz', 'ms', 'o']) - prefix_set
                self.report_issue(f"Inconsistent vendor prefixes, missing: {', '.join(missing)}")
            
            # Check for !important overrides (often indicates CSS specificity issues)
            important_count = len(re.findall(r'!important', content))
            if important_count > 5:
                self.report_issue(f"Excessive use of !important ({important_count} times)")
            
            # Check for potential z-index issues
            z_indexes = re.findall(r'z-index:\s*(\d+)', content)
            if z_indexes and int(max(z_indexes)) > 9999:
                self.report_issue(f"Very high z-index value: {max(z_indexes)}")
        
        except Exception as e:
            self.report_issue(f"Error validating file: {e}")
    
    def validate_html_file(self, filename: str) -> None:
        """
        Validate an HTML file.
        
        Args:
            filename: Path to the HTML file
        """
        self.current_file = filename
        
        if not os.path.exists(filename):
            logger.info(f"Skipping {filename} (file not found)")
            return
            
        self.files_checked += 1
        logger.info(f"Validating HTML file: {filename}")
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for various HTML issues
            
            # Check for unclosed tags
            opened_tags = []
            for i, line in enumerate(lines, 1):
                # This is a simplistic check and doesn't handle all HTML syntax
                opens = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*>', line)
                closes = re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', line)
                self_closing = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*/>', line)
                
                # Remove self-closing tags from opens
                for tag in self_closing:
                    if tag in opens:
                        opens.remove(tag)
                
                # Add opens to stack
                opened_tags.extend(opens)
                
                # Remove closes from stack
                for close in closes:
                    if opened_tags and opened_tags[-1] == close:
                        opened_tags.pop()
                    else:
                        self.report_issue(f"Mismatched closing tag: {close}", i)
            
            if opened_tags:
                self.report_issue(f"Unclosed tags: {', '.join(opened_tags)}")
            
            # Check for inline styles (should use CSS classes)
            inline_styles = re.findall(r'style=["\'][^"\']+["\']', content)
            if len(inline_styles) > 5:
                self.report_issue(f"Excessive use of inline styles ({len(inline_styles)} times)")
            
            # Check for inline JavaScript (should use external files)
            if re.search(r'<script>(?!{{\s*url_for)', content):
                self.report_issue("Inline JavaScript detected")
            
            # Check for accessibility issues
            for i, line in enumerate(lines, 1):
                # Images should have alt attributes
                if '<img' in line and 'alt=' not in line:
                    self.report_issue("Image missing alt attribute", i)
                
                # Form controls should have labels
                if re.search(r'<input[^>]*type=["\'](?:text|checkbox|radio)["\'][^>]*>', line) and 'id=' not in line:
                    self.report_issue("Form control without ID (might be missing associated label)", i)
        
        except Exception as e:
            self.report_issue(f"Error validating file: {e}")
    
    def validate_dependencies(self) -> None:
        """Validate dependencies between different files."""
        logger.info("Validating cross-file dependencies...")
        
        # Check that all Python files import the necessary modules
        python_modules = [os.path.splitext(os.path.basename(f))[0] for f in PYTHON_FILES]
        
        for filename in PYTHON_FILES:
            if not os.path.exists(filename):
                continue
                
            self.current_file = filename
            
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                
                # Check for app.py dependencies
                if filename == 'app.py':
                    required_imports = ['config_manager', 'site_scraper', 'ranker', 'link_checker', 'cache_manager']
                    for module in required_imports:
                        if f"import {module}" not in content:
                            self.report_issue(f"Missing import for required module: {module}")
                
                # Check for site_scraper.py dependencies
                elif filename == 'site_scraper.py':
                    if 'googleapiclient.discovery import build' not in content:
                        self.report_issue("Missing import for Google API client")
            
            except Exception as e:
                self.report_issue(f"Error checking dependencies: {e}")
        
        # Check that all JavaScript files define their required functions
        for filename in JS_FILES:
            if not os.path.exists(filename):
                continue
                
            self.current_file = filename
            
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                
                # Check that search-manager.js defines the expected class/object
                if filename.endswith('search-manager.js'):
                    if 'class SearchManager' not in content or 'window.searchManager =' not in content:
                        self.report_issue("search-manager.js doesn't define or expose SearchManager")
                
                # Check that player-manager.js defines the expected class/object
                elif filename.endswith('player-manager.js'):
                    if 'class PlayerManager' not in content or 'window.playerManager =' not in content:
                        self.report_issue("player-manager.js doesn't define or expose PlayerManager")
                
                # Check that ui-manager.js defines the expected class/object
                elif filename.endswith('ui-manager.js'):
                    if 'class UIManager' not in content or 'window.uiManager =' not in content:
                        self.report_issue("ui-manager.js doesn't define or expose UIManager")
            
            except Exception as e:
                self.report_issue(f"Error checking dependencies: {e}")
    
    def validate_configuration_consistency(self) -> None:
        """Validate consistency between different configuration files."""
        logger.info("Validating configuration consistency...")
        
        # Check if sites.json and settings.json exist
        if not (os.path.exists('sites.json') and os.path.exists('settings.json')):
            logger.info("Skipping configuration consistency check (files not found)")
            return
        
        try:
            # Load sites.json
            with open('sites.json', 'r') as f:
                sites_data = json.load(f)
            
            # Load settings.json
            with open('settings.json', 'r') as f:
                settings_data = json.load(f)
            
            # Check that default_search_sites in settings refers to valid sites
            default_sites = settings_data.get('default_search_sites', [])
            for site in default_sites:
                if site not in sites_data:
                    self.current_file = "settings.json"
                    self.report_issue(f"default_search_sites contains invalid site: {site}")
            
            # Check that search methods in sites are compatible with API keys in settings
            self.current_file = "sites.json"
            for site_id, config in sites_data.items():
                method = config.get('search_method')
                
                if method == 'google_site_search' and not settings_data.get('google_api_key'):
                    self.report_issue(f"Site '{site_id}' uses Google search but no API key is configured")
                
                elif method == 'bing_site_search' and not settings_data.get('bing_api_key'):
                    self.report_issue(f"Site '{site_id}' uses Bing search but no API key is configured")
        
        except Exception as e:
            self.current_file = "configuration"
            self.report_issue(f"Error checking configuration consistency: {e}")

def main():
    """Main function to run the code validator."""
    # Change to the directory containing the code
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    validator = CodeValidator()
    success = validator.validate_all()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())