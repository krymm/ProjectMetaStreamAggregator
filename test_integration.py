#!/usr/bin/env python3
"""
Integration test script for MetaStream Aggregator

Tests the connection between frontend and backend by making API requests
to each endpoint and validating the responses.
"""

import requests
import json
import time
import sys
import os

# Base URL for the API
BASE_URL = "http://127.0.0.1:5678"

def print_header(message):
    """Print a formatted header message."""
    print("\n" + "=" * 80)
    print(f" {message} ".center(80, "="))
    print("=" * 80)

def print_result(success, message):
    """Print test result."""
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
    return success

def check_server_running():
    """Check if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def test_settings_api():
    """Test the settings API endpoints."""
    print_header("Testing Settings API")
    
    all_tests_passed = True
    
    # Test GET /api/settings
    try:
        response = requests.get(f"{BASE_URL}/api/settings")
        success = response.status_code == 200
        all_tests_passed &= print_result(success, "GET /api/settings returns 200")
        
        # Validate response format
        settings = response.json()
        success = isinstance(settings, dict) and 'apis_configured' in settings
        all_tests_passed &= print_result(success, "Settings response has correct format")
    except Exception as e:
        all_tests_passed &= print_result(False, f"GET /api/settings error: {e}")
    
    # Test GET /api/settings/default
    try:
        response = requests.get(f"{BASE_URL}/api/settings/default")
        success = response.status_code == 200
        all_tests_passed &= print_result(success, "GET /api/settings/default returns 200")
        
        # Validate response format
        default_settings = response.json()
        success = isinstance(default_settings, dict) and 'results_per_page_default' in default_settings
        all_tests_passed &= print_result(success, "Default settings response has correct format")
    except Exception as e:
        all_tests_passed &= print_result(False, f"GET /api/settings/default error: {e}")
    
    # Test POST /api/settings with valid data
    try:
        # Get current settings
        current_settings = requests.get(f"{BASE_URL}/api/settings").json()
        
        # Create test settings update
        test_settings = {
            'results_per_page_default': 50,  # Different from default
            'cache_expiry_minutes': 20
        }
        
        response = requests.post(
            f"{BASE_URL}/api/settings",
            json=test_settings,
            headers={'Content-Type': 'application/json'}
        )
        success = response.status_code == 200
        all_tests_passed &= print_result(success, "POST /api/settings with valid data returns 200")
        
        # Verify settings were updated
        updated_settings = requests.get(f"{BASE_URL}/api/settings").json()
        success = updated_settings['results_per_page_default'] == 50
        all_tests_passed &= print_result(success, "Settings were successfully updated")
        
        # Reset settings back to original
        original_settings = {
            'results_per_page_default': current_settings.get('results_per_page_default', 100),
            'cache_expiry_minutes': current_settings.get('cache_expiry_minutes', 10)
        }
        
        requests.post(
            f"{BASE_URL}/api/settings",
            json=original_settings,
            headers={'Content-Type': 'application/json'}
        )
        
    except Exception as e:
        all_tests_passed &= print_result(False, f"POST /api/settings error: {e}")
    
    return all_tests_passed

def test_sites_api():
    """Test the sites API endpoints."""
    print_header("Testing Sites API")
    
    all_tests_passed = True
    
    # Test GET /api/sites
    try:
        response = requests.get(f"{BASE_URL}/api/sites")
        success = response.status_code == 200
        all_tests_passed &= print_result(success, "GET /api/sites returns 200")
        
        # Validate response format
        sites = response.json()
        success = isinstance(sites, list)
        all_tests_passed &= print_result(success, "Sites response is a list")
        
        # Check for expected site properties
        if sites:
            success = all(['name' in site and 'base_url' in site for site in sites])
            all_tests_passed &= print_result(success, "Each site has expected properties")
        else:
            print_result(True, "No sites configured (this is okay for testing)")
    except Exception as e:
        all_tests_passed &= print_result(False, f"GET /api/sites error: {e}")
    
    return all_tests_passed

def test_search_api():
    """Test the search API endpoint."""
    print_header("Testing Search API")
    
    all_tests_passed = True
    
    # First check if there are any configured sites
    try:
        sites_response = requests.get(f"{BASE_URL}/api/sites")
        sites = sites_response.json()
        
        if not sites:
            print_result(True, "No sites configured, skipping search test")
            return True
        
        # Test POST /api/search with valid data
        test_query = "test"
        test_sites = [sites[0]['name']]  # Use the first site
        
        search_data = {
            'query': test_query,
            'sites': test_sites,
            'page': 1,
            'use_cache': False,  # Disable cache for testing
            'check_links': False  # Disable link checking for faster test
        }
        
        response = requests.post(
            f"{BASE_URL}/api/search",
            json=search_data,
            headers={'Content-Type': 'application/json'}
        )
        
        success = response.status_code == 200
        all_tests_passed &= print_result(success, "POST /api/search returns 200")
        
        # Validate response format
        if success:
            search_results = response.json()
            
            # Check if expected fields are present
            expected_fields = ['query', 'search_sites', 'valid_results', 'broken_results', 'pagination', 'debug_info']
            for field in expected_fields:
                field_exists = field in search_results
                all_tests_passed &= print_result(field_exists, f"Search response contains {field} field")
            
            # Pagination format check
            pagination_fields = ['current_page', 'results_per_page', 'total_valid_results', 'total_pages']
            if 'pagination' in search_results:
                for field in pagination_fields:
                    field_exists = field in search_results['pagination']
                    all_tests_passed &= print_result(field_exists, f"Pagination contains {field} field")
        
        # Test with invalid data (missing query)
        invalid_data = {
            'sites': test_sites,
            'page': 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/search",
            json=invalid_data,
            headers={'Content-Type': 'application/json'}
        )
        
        success = response.status_code == 400
        all_tests_passed &= print_result(success, "POST /api/search with missing query returns 400")
        
        # Test with invalid data (missing sites)
        invalid_data = {
            'query': test_query,
            'page': 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/search",
            json=invalid_data,
            headers={'Content-Type': 'application/json'}
        )
        
        success = response.status_code == 400
        all_tests_passed &= print_result(success, "POST /api/search with missing sites returns 400")
        
    except Exception as e:
        all_tests_passed &= print_result(False, f"Search API error: {e}")
    
    return all_tests_passed

def test_cache_api():
    """Test the cache API endpoints."""
    print_header("Testing Cache API")
    
    all_tests_passed = True
    
    # Test GET /api/cache/stats
    try:
        response = requests.get(f"{BASE_URL}/api/cache/stats")
        success = response.status_code == 200
        all_tests_passed &= print_result(success, "GET /api/cache/stats returns 200")
        
        # Validate response format
        stats = response.json()
        expected_fields = ['total_entries', 'active_entries', 'expired_entries', 'cache_size_kb']
        for field in expected_fields:
            field_exists = field in stats
            all_tests_passed &= print_result(field_exists, f"Cache stats contains {field} field")
    except Exception as e:
        all_tests_passed &= print_result(False, f"GET /api/cache/stats error: {e}")
    
    # Test POST /api/cache/clear
    try:
        response = requests.post(
            f"{BASE_URL}/api/cache/clear",
            json={},
            headers={'Content-Type': 'application/json'}
        )
        success = response.status_code == 200
        all_tests_passed &= print_result(success, "POST /api/cache/clear returns 200")
        
        # Verify cache was cleared
        stats = requests.get(f"{BASE_URL}/api/cache/stats").json()
        success = stats['active_entries'] == 0
        all_tests_passed &= print_result(success, "Cache was successfully cleared")
    except Exception as e:
        all_tests_passed &= print_result(False, f"POST /api/cache/clear error: {e}")
    
    return all_tests_passed

def main():
    """Run all integration tests."""
    print_header("MetaStream Aggregator Integration Tests")
    
    # Check if server is running
    if not check_server_running():
        print("❌ Server is not running. Please start the server at http://127.0.0.1:5678 first.")
        return False
    
    print_result(True, "Server is running")
    
    # Run all tests
    settings_passed = test_settings_api()
    sites_passed = test_sites_api()
    cache_passed = test_cache_api()
    search_passed = test_search_api()
    
    # Summarize results
    print_header("Test Results Summary")
    print_result(settings_passed, "Settings API Tests")
    print_result(sites_passed, "Sites API Tests")
    print_result(cache_passed, "Cache API Tests")
    print_result(search_passed, "Search API Tests")
    
    all_passed = settings_passed and sites_passed and cache_passed and search_passed
    print_header("Final Result")
    print_result(all_passed, "All Integration Tests")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)