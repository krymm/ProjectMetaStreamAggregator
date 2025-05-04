#!/usr/bin/env python3
"""
Mobile compatibility test script for MetaStream Aggregator

This script tests the responsive design of the MSA application using
Selenium WebDriver to simulate different screen sizes and devices.

Requires:
- selenium
- chromedriver or geckodriver
"""

import time
import argparse
import logging
import os
from typing import Dict, List, Tuple, Any

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium is not installed. Run 'pip install selenium' to use this script.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mobile_testing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MSA-Mobile-Test")

# Default settings
BASE_URL = "http://127.0.0.1:8001"
SCREENSHOT_DIR = "mobile_test_screenshots"
DEFAULT_TIMEOUT = 10  # Seconds

# Define device configurations to test
DEVICE_CONFIGS = [
    {
        "name": "Desktop",
        "width": 1920,
        "height": 1080,
        "user_agent": None  # Use default
    },
    {
        "name": "Laptop",
        "width": 1366,
        "height": 768,
        "user_agent": None  # Use default
    },
    {
        "name": "Tablet",
        "width": 768,
        "height": 1024,
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    },
    {
        "name": "Mobile",
        "width": 375,
        "height": 812,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    }
]

class MobileCompatibilityTester:
    """Tests mobile compatibility of MSA application."""
    
    def __init__(self, base_url: str = BASE_URL, browser: str = "chrome", headless: bool = True):
        """
        Initialize the tester.
        
        Args:
            base_url: Base URL of the MSA application
            browser: Browser to use (chrome or firefox)
            headless: Whether to run in headless mode
        """
        self.base_url = base_url
        self.browser_name = browser.lower()
        self.headless = headless
        self.driver = None
        self.current_device = None
        
        # Create screenshot directory if it doesn't exist
        if not os.path.exists(SCREENSHOT_DIR):
            os.makedirs(SCREENSHOT_DIR)
            
        # Initialize WebDriver
        if SELENIUM_AVAILABLE:
            self._init_webdriver()
        else:
            logger.error("Selenium not available. Cannot continue.")
    
    def _init_webdriver(self):
        """Initialize the WebDriver based on selected browser."""
        try:
            if self.browser_name == "chrome":
                options = ChromeOptions()
                if self.headless:
                    options.add_argument("--headless=new")
                options.add_argument("--window-size=1920,1080")  # Default size
                self.driver = webdriver.Chrome(options=options)
                
            elif self.browser_name == "firefox":
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                self.driver = webdriver.Firefox(options=options)
                
            else:
                logger.error(f"Unsupported browser: {self.browser_name}")
                return
                
            # Set default timeout
            self.driver.implicitly_wait(DEFAULT_TIMEOUT)
            logger.info(f"Initialized {self.browser_name} WebDriver")
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            self.driver = None
    
    def run_all_tests(self):
        """Run all mobile compatibility tests."""
        if not self.driver:
            logger.error("WebDriver not initialized. Cannot run tests.")
            return False
            
        try:
            # Run tests for each device configuration
            for device in DEVICE_CONFIGS:
                self.current_device = device
                self._configure_for_device(device)
                self._test_device_compatibility()
                
            logger.info("All mobile compatibility tests completed")
            return True
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
            
        finally:
            # Close the browser
            self._cleanup()
    
    def _configure_for_device(self, device: Dict):
        """
        Configure WebDriver for the specified device.
        
        Args:
            device: Device configuration dictionary
        """
        logger.info(f"Configuring for device: {device['name']} ({device['width']}x{device['height']})")
        
        # Set window size
        self.driver.set_window_size(device['width'], device['height'])
        
        # Set user agent if specified
        if device['user_agent'] and self.browser_name == "chrome":
            # For Chrome, we need to create a CDP session to set user agent
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": device['user_agent']
            })
    
    def _test_device_compatibility(self):
        """Test application compatibility on the current device configuration."""
        device_name = self.current_device['name']
        logger.info(f"Testing {device_name} compatibility")
        
        # List of UI elements to check
        ui_elements = [
            {"name": "Search Input", "selector": By.ID, "value": "search-input"},
            {"name": "Search Button", "selector": By.ID, "value": "search-button"},
            {"name": "Site List Container", "selector": By.ID, "value": "site-list-container"},
            {"name": "Settings Button", "selector": By.ID, "value": "settings-button"}
        ]
        
        try:
            # Navigate to the home page
            self.driver.get(self.base_url)
            logger.info(f"Navigated to {self.base_url}")
            
            # Take screenshot of the home page
            self._take_screenshot(f"home_{device_name.lower()}")
            
            # Check visibility of important UI elements
            for element in ui_elements:
                self._check_element_visibility(element)
            
            # Test search functionality
            self._test_search_functionality()
            
            # Test settings modal
            self._test_settings_modal()
            
            # Test responsive navigation
            self._test_responsive_navigation()
            
        except Exception as e:
            logger.error(f"Error testing {device_name} compatibility: {e}")
    
    def _check_element_visibility(self, element: Dict):
        """
        Check if a UI element is visible and usable.
        
        Args:
            element: Element definition dictionary
        """
        name = element["name"]
        selector = element["selector"]
        value = element["value"]
        
        try:
            # Wait for the element to be visible
            wait = WebDriverWait(self.driver, DEFAULT_TIMEOUT)
            el = wait.until(EC.visibility_of_element_located((selector, value)))
            
            # Check if element is displayed
            if el.is_displayed():
                logger.info(f"✓ {name} is visible on {self.current_device['name']}")
            else:
                logger.warning(f"✗ {name} is not visible on {self.current_device['name']}")
            
            # Check if element is clickable (not obscured)
            wait.until(EC.element_to_be_clickable((selector, value)))
            logger.info(f"✓ {name} is clickable on {self.current_device['name']}")
            
        except TimeoutException:
            logger.warning(f"✗ {name} not found or not visible on {self.current_device['name']}")
        except Exception as e:
            logger.error(f"Error checking {name}: {e}")
    
    def _test_search_functionality(self):
        """Test basic search functionality."""
        device_name = self.current_device['name']
        
        try:
            # Enter a test query
            search_input = self.driver.find_element(By.ID, "search-input")
            search_input.clear()
            search_input.send_keys("test")
            
            # Select a site
            site_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, ".site-checkbox")
            if site_checkboxes:
                site_checkboxes[0].click()
            else:
                logger.warning(f"No site checkboxes found on {device_name}")
                return
            
            # Click search button
            search_button = self.driver.find_element(By.ID, "search-button")
            search_button.click()
            
            # Wait for loading indicator to appear and then disappear
            try:
                loading = WebDriverWait(self.driver, 3).until(
                    EC.visibility_of_element_located((By.ID, "loading-indicator"))
                )
                WebDriverWait(self.driver, 30).until(
                    EC.invisibility_of_element(loading)
                )
            except TimeoutException:
                # Loading indicator might be brief or not appear
                pass
            
            # Wait for results or error message
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, ".result-item")) > 0 or
                             len(d.find_elements(By.CSS_SELECTOR, ".no-results")) > 0
                )
                
                # Take screenshot of search results
                self._take_screenshot(f"search_results_{device_name.lower()}")
                
                # Check results are displayed properly
                results = self.driver.find_elements(By.CSS_SELECTOR, ".result-item")
                if results:
                    logger.info(f"✓ Search results displayed on {device_name}")
                else:
                    # Check for "no results" message
                    no_results = self.driver.find_elements(By.CSS_SELECTOR, ".no-results")
                    if no_results:
                        logger.info(f"✓ 'No results' message displayed on {device_name}")
                    else:
                        logger.warning(f"✗ No search results or error message on {device_name}")
                
            except TimeoutException:
                logger.warning(f"✗ Search results did not load within timeout on {device_name}")
                self._take_screenshot(f"search_timeout_{device_name.lower()}")
            
        except Exception as e:
            logger.error(f"Error testing search on {device_name}: {e}")
            self._take_screenshot(f"search_error_{device_name.lower()}")
    
    def _test_settings_modal(self):
        """Test the settings modal displays correctly."""
        device_name = self.current_device['name']
        
        try:
            # Click settings button
            settings_button = self.driver.find_element(By.ID, "settings-button")
            settings_button.click()
            
            # Wait for settings modal to appear
            try:
                settings_modal = WebDriverWait(self.driver, DEFAULT_TIMEOUT).until(
                    lambda d: d.find_element(By.ID, "settings-modal") and
                              d.find_element(By.ID, "settings-modal").is_displayed()
                )
                
                logger.info(f"✓ Settings modal displayed on {device_name}")
                
                # Take screenshot of settings modal
                self._take_screenshot(f"settings_modal_{device_name.lower()}")
                
                # Check form fields are accessible
                settings_form = self.driver.find_element(By.ID, "settings-form")
                form_fields = settings_form.find_elements(By.CSS_SELECTOR, "input, select")
                
                if form_fields:
                    logger.info(f"✓ Settings form fields accessible on {device_name}")
                else:
                    logger.warning(f"✗ No settings form fields found on {device_name}")
                
                # Close the settings modal
                close_button = self.driver.find_element(By.ID, "close-settings")
                close_button.click()
                
                # Verify modal is closed
                WebDriverWait(self.driver, DEFAULT_TIMEOUT).until(
                    lambda d: not d.find_element(By.ID, "settings-modal").is_displayed()
                )
                logger.info(f"✓ Settings modal closes properly on {device_name}")
                
            except TimeoutException:
                logger.warning(f"✗ Settings modal did not appear or close properly on {device_name}")
                self._take_screenshot(f"settings_modal_error_{device_name.lower()}")
            
        except Exception as e:
            logger.error(f"Error testing settings modal on {device_name}: {e}")
    
    def _test_responsive_navigation(self):
        """Test responsive navigation behavior."""
        device_name = self.current_device['name']
        width = self.current_device['width']
        
        # Responsive layout checks depend on screen width
        if width < 768:  # Mobile layout
            try:
                # Check that the layout is properly stacked (search panel above results)
                search_panel = self.driver.find_element(By.CLASS_NAME, "search-panel")
                results_area = self.driver.find_element(By.CLASS_NAME, "results-area")
                
                search_rect = search_panel.rect
                results_rect = results_area.rect
                
                if search_rect['y'] < results_rect['y']:
                    logger.info(f"✓ Mobile layout correctly stacked on {device_name}")
                else:
                    logger.warning(f"✗ Mobile layout not correctly stacked on {device_name}")
                
                # Check that elements are properly sized for the viewport
                viewport_width = self.driver.execute_script("return window.innerWidth")
                element_width = search_panel.rect['width']
                
                if abs(viewport_width - element_width) < 20:  # Allow small margin
                    logger.info(f"✓ Elements properly sized for viewport on {device_name}")
                else:
                    logger.warning(f"✗ Elements not properly sized for viewport on {device_name}")
                
            except Exception as e:
                logger.error(f"Error checking responsive layout on {device_name}: {e}")
    
    def _take_screenshot(self, name: str):
        """
        Take a screenshot of the current browser window.
        
        Args:
            name: Base name for the screenshot file
        """
        if not self.driver:
            return
            
        try:
            screenshot_path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
    
    def _cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")

def main():
    """Parse arguments and run the tester."""
    parser = argparse.ArgumentParser(description="Test mobile compatibility of MSA application")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the MSA application")
    parser.add_argument("--browser", default="chrome", choices=["chrome", "firefox"], 
                        help="Browser to use for testing")
    parser.add_argument("--no-headless", action="store_true", 
                        help="Run browser in visible mode (not headless)")
    args = parser.parse_args()
    
    if not SELENIUM_AVAILABLE:
        print("Error: Selenium is required for this script.")
        print("Install it with: pip install selenium")
        return 1
    
    tester = MobileCompatibilityTester(
        base_url=args.url,
        browser=args.browser,
        headless=not args.no_headless
    )
    
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    main()