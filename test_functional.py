#!/usr/bin/env python3
"""
Functional test script for MetaStream Aggregator

This script tests the core functionality of the MSA application by making 
direct API calls to test various features and edge cases.
"""

import requests
import json
import time
import argparse
import os
import logging
import concurrent.futures
import copy
from typing import Dict, List, Any, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("functional_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MSA-Functional-Test")

# Default settings
BASE_URL = "http://127.0.0.1:8001"
DEFAULT_TIMEOUT = 60  # Seconds
TEST_DATA_FILE = "test_data.json"

class MSAFunctionalTester:
    """Class to run functional tests against the MSA application."""
    
    def __init__(self, base_url: str = BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        """Initialize the tester with the base URL and timeout."""
        self.base_url = base_url
        self.timeout = timeout
        self.test_data = self._load_test_data()
        self.original_settings = None
        self.original_sites = None
        
        # Track test results
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    def _load_test_data(self) -> Dict:
        """Load test data from the JSON file."""
        try:
            with open(TEST_DATA_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Test data file '{TEST_DATA_FILE}' not found.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in test data file '{TEST_DATA_FILE}'.")
            return {}
    
    def _make_request(self, method: str, endpoint: str, json_data: Dict = None, 
                     params: Dict = None, expected_status: int = 200) -> Tuple[bool, Dict]:
        """
        Make a request to the API and check the status code.
        
        Args:
            method: HTTP method to use (get, post, etc.)
            endpoint: API endpoint path
            json_data: JSON data to send in the request body
            params: URL parameters to include
            expected_status: Expected HTTP status code
            
        Returns:
            Tuple of (success, response_data)
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = None
            if method.lower() == 'get':
                response = requests.get(url, params=params, timeout=self.timeout)
            elif method.lower() == 'post':
                response = requests.post(url, json=json_data, timeout=self.timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return False, {}
            
            if response.status_code != expected_status:
                logger.error(f"Request to {url} returned status {response.status_code}, expected {expected_status}")
                return False, {}
            
            # For non-JSON responses (e.g., HTML), return the text content
            if 'application/json' not in response.headers.get('Content-Type', ''):
                return True, {'text': response.text}
                
            return True, response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return False, {}
        except json.JSONDecodeError:
            logger.error(f"Response from {url} is not valid JSON")
            return False, {}
    
    def _backup_settings_and_sites(self):
        """Backup current settings and site configurations."""
        logger.info("Backing up current settings and site configurations...")
        
        # Get current settings
        success, settings = self._make_request('get', '/api/settings')
        if success:
            self.original_settings = settings
            logger.info("Successfully backed up settings")
        else:
            logger.error("Failed to backup settings")
        
        # Get current sites
        success, sites = self._make_request('get', '/api/sites')
        if success:
            self.original_sites = sites
            logger.info("Successfully backed up site configurations")
        else:
            logger.error("Failed to backup site configurations")
    
    def _restore_settings_and_sites(self):
        """Restore original settings and site configurations."""
        logger.info("Restoring original settings and site configurations...")
        
        # Restore settings
        if self.original_settings:
            success, _ = self._make_request('post', '/api/settings', json_data=self.original_settings)
            if success:
                logger.info("Successfully restored settings")
            else:
                logger.error("Failed to restore settings")
        
        # Note: We don't restore sites because they're read-only via the API
        # You would need to manually restore the sites.json file
    
    def run_all_tests(self):
        """Run all functional tests."""
        logger.info("Starting MSA functional tests...")
        
        # Backup current settings
        self._backup_settings_and_sites()
        
        try:
            # Run test groups
            self.test_api_connectivity()
            self.test_basic_search()
            self.test_pagination()
            self.test_cache_management()
            self.test_error_handling()
            self.test_scoring_weights()
            
        finally:
            # Restore original settings
            self._restore_settings_and_sites()
        
        # Report results
        logger.info(f"Test Results: Passed: {self.passed_tests}, Failed: {self.failed_tests}, Skipped: {self.skipped_tests}")
        
        return self.failed_tests == 0
    
    def test_api_connectivity(self):
        """Test basic API connectivity to confirm the server is running."""
        logger.info("Testing API connectivity...")
        
        # Test index page
        success, _ = self._make_request('get', '/')
        self._record_test_result("Index Page Access", success)
        
        # Test settings API
        success, _ = self._make_request('get', '/api/settings')
        self._record_test_result("Settings API Access", success)
        
        # Test sites API
        success, _ = self._make_request('get', '/api/sites')
        self._record_test_result("Sites API Access", success)
        
        # Test cache stats API
        success, _ = self._make_request('get', '/api/cache/stats')
        self._record_test_result("Cache Stats API Access", success)
    
    def test_basic_search(self):
        """Test basic search functionality with various queries and site combinations."""
        logger.info("Testing basic search functionality...")
        
        # Get available sites first
        success, sites_response = self._make_request('get', '/api/sites')
        if not success or not sites_response:
            logger.error("Failed to get sites, skipping search tests")
            self.skipped_tests += 1
            return
        
        available_sites = [site['name'] for site in sites_response]
        logger.info(f"Available sites: {available_sites}")
        
        # Test with different queries and site combinations
        for query_data in self.test_data.get('search_queries', [])[:3]:  # Limit to first 3 for speed
            query = query_data['query']
            if not query:  # Skip empty query
                continue
                
            for site_combo in self.test_data.get('site_combinations', [])[:3]:  # Limit to first 3
                sites = [site for site in site_combo['sites'] if site in available_sites]
                if not sites:  # Skip if no valid sites
                    continue
                    
                test_name = f"Search: '{query}' on {', '.join(sites)}"
                logger.info(f"Running test: {test_name}")
                
                # Execute search
                success, search_results = self._make_request(
                    'post', 
                    '/api/search', 
                    json_data={
                        'query': query,
                        'sites': sites,
                        'page': 1,
                        'use_cache': False,  # Disable cache to ensure fresh results
                        'check_links': False  # Disable link checking for faster tests
                    }
                )
                
                # Validate search results structure
                if success:
                    valid_structure = (
                        isinstance(search_results, dict) and
                        'valid_results' in search_results and
                        'pagination' in search_results
                    )
                    if valid_structure:
                        results_count = len(search_results['valid_results'])
                        logger.info(f"Search returned {results_count} results")
                    else:
                        logger.error(f"Search results have invalid structure")
                        success = False
                
                self._record_test_result(test_name, success)
    
    def test_pagination(self):
        """Test pagination functionality."""
        logger.info("Testing pagination functionality...")
        
        # Get available sites
        success, sites_response = self._make_request('get', '/api/sites')
        if not success or not sites_response:
            logger.error("Failed to get sites, skipping pagination tests")
            self.skipped_tests += 1
            return
            
        available_sites = [site['name'] for site in sites_response]
        if not available_sites:
            logger.error("No sites available, skipping pagination tests")
            self.skipped_tests += 1
            return
            
        # Use a query likely to return multiple pages of results
        query = "test"
        sites = [available_sites[0]]  # Use the first site
        
        # Set results per page to a small number to ensure multiple pages
        success, _ = self._make_request(
            'post',
            '/api/settings',
            json_data={'results_per_page_default': 5}
        )
        if not success:
            logger.error("Failed to set results per page, skipping pagination tests")
            self.skipped_tests += 1
            return
            
        # Execute initial search
        success, search_results = self._make_request(
            'post', 
            '/api/search', 
            json_data={
                'query': query,
                'sites': sites,
                'page': 1,
                'use_cache': False,
                'check_links': False
            }
        )
        
        if not success or not search_results:
            logger.error("Initial search failed, skipping pagination tests")
            self.skipped_tests += 1
            return
            
        # Check if we have multiple pages
        pagination = search_results.get('pagination', {})
        total_pages = pagination.get('total_pages', 0)
        
        if total_pages <= 1:
            logger.warning("Search returned only one page, pagination tests limited")
            
        # Test going to page 2 if available
        if total_pages >= 2:
            success, page2_results = self._make_request(
                'post', 
                '/api/search', 
                json_data={
                    'query': query,
                    'sites': sites,
                    'page': 2,
                    'use_cache': False,
                    'check_links': False
                }
            )
            
            if success:
                # Verify it's actually page 2
                page_num = page2_results.get('pagination', {}).get('current_page', 0)
                correct_page = page_num == 2
                if not correct_page:
                    logger.error(f"Requested page 2 but got page {page_num}")
                    success = False
            
            self._record_test_result("Pagination: Navigate to Page 2", success)
            
        # Test last page if there are more than 2 pages
        if total_pages > 2:
            success, last_page_results = self._make_request(
                'post', 
                '/api/search', 
                json_data={
                    'query': query,
                    'sites': sites,
                    'page': total_pages,
                    'use_cache': False,
                    'check_links': False
                }
            )
            
            self._record_test_result("Pagination: Navigate to Last Page", success)
            
        # Test invalid page number (beyond total)
        success, invalid_page_results = self._make_request(
            'post', 
            '/api/search', 
            json_data={
                'query': query,
                'sites': sites,
                'page': total_pages + 1,
                'use_cache': False,
                'check_links': False
            }
        )
        
        # This should still return results (usually the last page)
        self._record_test_result("Pagination: Invalid Page Handling", success)
    
    def test_cache_management(self):
        """Test cache management functionality."""
        logger.info("Testing cache management...")
        
        # Test cache stats
        success, cache_stats = self._make_request('get', '/api/cache/stats')
        self._record_test_result("Cache Stats API", success)
        
        if success:
            logger.info(f"Current cache stats: {cache_stats}")
            
            # Clear all cache
            success, clear_result = self._make_request('post', '/api/cache/clear', json_data={})
            self._record_test_result("Clear All Cache", success)
            
            if success:
                # Verify cache was cleared
                success, new_stats = self._make_request('get', '/api/cache/stats')
                if success:
                    cache_cleared = new_stats.get('active_entries', -1) == 0
                    self._record_test_result("Cache Clearing Verification", cache_cleared)
                    
                # Test cached search
                # First, get sites
                success, sites_response = self._make_request('get', '/api/sites')
                if success and sites_response:
                    available_sites = [site['name'] for site in sites_response]
                    if available_sites:
                        # Perform a search with caching enabled
                        search_data = {
                            'query': 'cache test',
                            'sites': [available_sites[0]],
                            'use_cache': True,
                            'check_links': False
                        }
                        
                        # First search should not be cached
                        start_time = time.time()
                        success, first_search = self._make_request(
                            'post', 
                            '/api/search', 
                            json_data=search_data
                        )
                        first_search_time = time.time() - start_time
                        
                        logger.info(f"First search took {first_search_time:.2f} seconds")
                        
                        # Second search should use cache and be faster
                        start_time = time.time()
                        success, second_search = self._make_request(
                            'post', 
                            '/api/search', 
                            json_data=search_data
                        )
                        second_search_time = time.time() - start_time
                        
                        logger.info(f"Second search took {second_search_time:.2f} seconds")
                        
                        # Verify cached status in debug info
                        is_cached = second_search.get('debug_info', {}).get('cached', False)
                        faster_search = second_search_time < first_search_time
                        
                        self._record_test_result("Cache Hit Detection", is_cached)
                        self._record_test_result("Cached Search Speed Improvement", faster_search)
                        
                        # Test clearing specific cache
                        success, clear_result = self._make_request(
                            'post', 
                            '/api/cache/clear', 
                            json_data={
                                'query': 'cache test',
                                'sites': [available_sites[0]]
                            }
                        )
                        self._record_test_result("Clear Specific Cache", success)
                    else:
                        logger.warning("No sites available, skipping cache search tests")
                        self.skipped_tests += 1
    
    def test_error_handling(self):
        """Test error handling for various invalid inputs."""
        logger.info("Testing error handling...")
        
        # Test empty query
        success, response = self._make_request(
            'post', 
            '/api/search', 
            json_data={
                'query': '',
                'sites': ['example_site1']
            },
            expected_status=400  # Expect 400 Bad Request
        )
        correct_error = success and 'error' in response
        self._record_test_result("Error Handling: Empty Query", correct_error)
        
        # Test no sites selected
        success, response = self._make_request(
            'post', 
            '/api/search', 
            json_data={
                'query': 'test',
                'sites': []
            },
            expected_status=400  # Expect 400 Bad Request
        )
        correct_error = success and 'error' in response
        self._record_test_result("Error Handling: No Sites Selected", correct_error)
        
        # Test invalid settings data
        success, response = self._make_request(
            'post', 
            '/api/settings', 
            json_data=None,
            expected_status=400  # Expect 400 Bad Request
        )
        correct_error = success and 'error' in response
        self._record_test_result("Error Handling: Invalid Settings Data", correct_error)
    
    def test_scoring_weights(self):
        """Test different scoring weight configurations."""
        logger.info("Testing scoring weight configurations...")
        
        # Get available sites
        success, sites_response = self._make_request('get', '/api/sites')
        if not success or not sites_response:
            logger.error("Failed to get sites, skipping scoring weight tests")
            self.skipped_tests += 1
            return
            
        available_sites = [site['name'] for site in sites_response]
        if not available_sites:
            logger.error("No sites available, skipping scoring weight tests")
            self.skipped_tests += 1
            return
        
        # Test with different weight configurations
        query = "test"
        sites = [available_sites[0]]
        
        baseline_scores = None
        
        # First, get baseline scores with default weights
        success, baseline_search = self._make_request(
            'post', 
            '/api/search', 
            json_data={
                'query': query,
                'sites': sites,
                'use_cache': False,
                'check_links': False
            }
        )
        
        if success and baseline_search.get('valid_results'):
            baseline_scores = [result.get('calc_score', 0) for result in baseline_search['valid_results']]
            logger.info(f"Baseline scores: {baseline_scores[:5]} (showing first 5)")
            
            # Test each weight configuration
            for weight_test in self.test_data.get('scoring_weight_tests', [])[:2]:  # Limit to first 2
                weights = weight_test['weights']
                test_name = f"Scoring Weights: {weight_test['name']}"
                
                # Update scoring weights
                settings_update = {'scoring_weights': weights}
                success, _ = self._make_request('post', '/api/settings', json_data=settings_update)
                
                if not success:
                    logger.error(f"Failed to update scoring weights for {test_name}")
                    self._record_test_result(test_name, False)
                    continue
                
                # Perform search with new weights
                success, weighted_search = self._make_request(
                    'post', 
                    '/api/search', 
                    json_data={
                        'query': query,
                        'sites': sites,
                        'use_cache': False,
                        'check_links': False
                    }
                )
                
                if success and weighted_search.get('valid_results'):
                    weighted_scores = [result.get('calc_score', 0) for result in weighted_search['valid_results']]
                    logger.info(f"{test_name} scores: {weighted_scores[:5]} (showing first 5)")
                    
                    # Check if scores are different from baseline (should be with different weights)
                    if len(weighted_scores) > 0 and len(baseline_scores) > 0:
                        scores_different = weighted_scores[0] != baseline_scores[0]
                        self._record_test_result(test_name, scores_different)
                    else:
                        logger.warning(f"Not enough results to compare scores for {test_name}")
                        self._record_test_result(test_name, False)
                else:
                    logger.error(f"Search failed for {test_name}")
                    self._record_test_result(test_name, False)
        else:
            logger.error("Baseline search failed, skipping scoring weight tests")
            self.skipped_tests += 1
    
    def _record_test_result(self, test_name, success):
        """Record the result of a test."""
        if success:
            logger.info(f"✓ PASS: {test_name}")
            self.passed_tests += 1
        else:
            logger.error(f"✗ FAIL: {test_name}")
            self.failed_tests += 1

def main():
    """Main function to parse args and run tests."""
    parser = argparse.ArgumentParser(description="Run functional tests for MetaStream Aggregator")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the MSA application")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    args = parser.parse_args()
    
    tester = MSAFunctionalTester(base_url=args.url, timeout=args.timeout)
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    main()