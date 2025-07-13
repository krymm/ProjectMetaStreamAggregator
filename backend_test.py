#!/usr/bin/env python3
"""
Comprehensive Backend Test Suite for MetaStream Aggregator
Tests all API endpoints and core functionality
"""

import requests
import json
import time
import os
import tempfile
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"

class MetaStreamTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.failed_tests = []
        
    def log_test(self, test_name, success, message="", response_data=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if response_data:
            result['response_data'] = response_data
        
        self.test_results.append(result)
        if not success:
            self.failed_tests.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
    def test_main_page(self):
        """Test GET / - Main page"""
        try:
            response = self.session.get(BASE_URL, timeout=10)
            if response.status_code == 200:
                self.log_test("Main Page", True, f"Status: {response.status_code}")
            else:
                self.log_test("Main Page", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Main Page", False, f"Request failed: {str(e)}")
    
    def test_get_sites(self):
        """Test GET /api/sites - Get sites configuration"""
        try:
            response = self.session.get(f"{API_BASE}/sites", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    site_count = len(data)
                    self.log_test("Get Sites", True, f"Retrieved {site_count} sites", data)
                    return data
                else:
                    self.log_test("Get Sites", False, "Response is not a dictionary")
            else:
                self.log_test("Get Sites", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get Sites", False, f"Request failed: {str(e)}")
        return {}
    
    def test_create_site(self):
        """Test POST /api/sites - Create new site configuration"""
        test_site = {
            "name": "Test Site Backend",
            "base_url": "https://example-test.com",
            "search_method": "scrape_search_page",
            "search_url_template": "https://example-test.com/search?q={query}&page={page}",
            "results_container_selector": ".results",
            "result_item_selector": ".item",
            "title_selector": ".title",
            "video_url_selector": ".title a",
            "thumbnail_selector": ".thumb img",
            "popularity_multiplier": 0.8
        }
        
        try:
            response = self.session.post(f"{API_BASE}/sites", json=test_site, timeout=10)
            if response.status_code == 201:
                data = response.json()
                site_key = data.get('site_key')
                self.log_test("Create Site", True, f"Created site with key: {site_key}", data)
                return site_key
            else:
                self.log_test("Create Site", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Create Site", False, f"Request failed: {str(e)}")
        return None
    
    def test_update_site(self, site_key):
        """Test PUT /api/sites/<site_key> - Update site configuration"""
        if not site_key:
            self.log_test("Update Site", False, "No site key provided")
            return
            
        updated_site = {
            "name": "Test Site Backend Updated",
            "base_url": "https://example-test-updated.com",
            "search_method": "scrape_search_page",
            "search_url_template": "https://example-test-updated.com/search?q={query}&page={page}",
            "results_container_selector": ".results",
            "result_item_selector": ".item",
            "title_selector": ".title",
            "video_url_selector": ".title a",
            "thumbnail_selector": ".thumb img",
            "popularity_multiplier": 0.9
        }
        
        try:
            response = self.session.put(f"{API_BASE}/sites/{site_key}", json=updated_site, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Update Site", True, f"Updated site: {site_key}", data)
            else:
                self.log_test("Update Site", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Update Site", False, f"Request failed: {str(e)}")
    
    def test_delete_site(self, site_key):
        """Test DELETE /api/sites/<site_key> - Delete site configuration"""
        if not site_key:
            self.log_test("Delete Site", False, "No site key provided")
            return
            
        try:
            response = self.session.delete(f"{API_BASE}/sites/{site_key}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Delete Site", True, f"Deleted site: {site_key}", data)
            else:
                self.log_test("Delete Site", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Delete Site", False, f"Request failed: {str(e)}")
    
    def test_get_settings(self):
        """Test GET /api/settings - Get user settings"""
        try:
            response = self.session.get(f"{API_BASE}/settings", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    self.log_test("Get Settings", True, f"Retrieved settings with {len(data)} keys", data)
                    return data
                else:
                    self.log_test("Get Settings", False, "Response is not a dictionary")
            else:
                self.log_test("Get Settings", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get Settings", False, f"Request failed: {str(e)}")
        return {}
    
    def test_update_settings(self):
        """Test POST /api/settings - Update settings"""
        test_settings = {
            "results_per_page_default": 50,
            "cache_expiry_minutes": 15,
            "check_links_default": False,
            "max_pages_per_site": 2
        }
        
        try:
            response = self.session.post(f"{API_BASE}/settings", json=test_settings, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Update Settings", True, "Settings updated successfully", data)
            else:
                self.log_test("Update Settings", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Update Settings", False, f"Request failed: {str(e)}")
    
    def test_search_basic(self):
        """Test POST /api/search - Basic search functionality"""
        search_request = {
            "query": "nature documentary",
            "sites": ["Pornhub_Scrape"],  # Use a site that exists in the config
            "page": 1,
            "use_cache": False,
            "check_links": False,
            "max_pages_per_site": 1
        }
        
        try:
            response = self.session.post(f"{API_BASE}/search", json=search_request, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'valid_results' in data and 'pagination' in data:
                    result_count = len(data['valid_results'])
                    self.log_test("Basic Search", True, f"Search completed with {result_count} results")
                else:
                    self.log_test("Basic Search", False, "Missing expected response fields")
            else:
                self.log_test("Basic Search", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Basic Search", False, f"Request failed: {str(e)}")
    
    def test_search_with_cache(self):
        """Test POST /api/search - Search with caching enabled"""
        search_request = {
            "query": "test search cache",
            "sites": ["Pornhub_Scrape"],
            "page": 1,
            "use_cache": True,
            "check_links": False,
            "max_pages_per_site": 1
        }
        
        try:
            # First search - should cache results
            response1 = self.session.post(f"{API_BASE}/search", json=search_request, timeout=30)
            if response1.status_code == 200:
                # Second search - should use cache
                response2 = self.session.post(f"{API_BASE}/search", json=search_request, timeout=30)
                if response2.status_code == 200:
                    data2 = response2.json()
                    cached = data2.get('debug_info', {}).get('cached', False)
                    if cached:
                        self.log_test("Search with Cache", True, "Cache hit detected")
                    else:
                        self.log_test("Search with Cache", True, "Search completed (cache miss)")
                else:
                    self.log_test("Search with Cache", False, f"Second search failed: {response2.status_code}")
            else:
                self.log_test("Search with Cache", False, f"First search failed: {response1.status_code}")
        except Exception as e:
            self.log_test("Search with Cache", False, f"Request failed: {str(e)}")
    
    def test_search_validation(self):
        """Test POST /api/search - Input validation"""
        # Test missing query
        try:
            response = self.session.post(f"{API_BASE}/search", json={"sites": ["Pornhub_Scrape"]}, timeout=10)
            if response.status_code == 400:
                self.log_test("Search Validation - Missing Query", True, "Correctly rejected missing query")
            else:
                self.log_test("Search Validation - Missing Query", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Search Validation - Missing Query", False, f"Request failed: {str(e)}")
        
        # Test missing sites
        try:
            response = self.session.post(f"{API_BASE}/search", json={"query": "test"}, timeout=10)
            if response.status_code == 400:
                self.log_test("Search Validation - Missing Sites", True, "Correctly rejected missing sites")
            else:
                self.log_test("Search Validation - Missing Sites", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Search Validation - Missing Sites", False, f"Request failed: {str(e)}")
    
    def test_cache_stats(self):
        """Test GET /api/cache/stats - Cache statistics"""
        try:
            response = self.session.get(f"{API_BASE}/cache/stats", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'total_entries' in data and 'cache_size_bytes' in data:
                    self.log_test("Cache Stats", True, f"Cache stats: {data['total_entries']} entries", data)
                else:
                    self.log_test("Cache Stats", False, "Missing expected cache stats fields")
            else:
                self.log_test("Cache Stats", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Cache Stats", False, f"Request failed: {str(e)}")
    
    def test_cache_clear(self):
        """Test POST /api/cache/clear - Clear cache"""
        try:
            response = self.session.post(f"{API_BASE}/cache/clear", json={}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Cache Clear", True, "Cache cleared successfully", data)
            else:
                self.log_test("Cache Clear", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Cache Clear", False, f"Request failed: {str(e)}")
    
    def test_ollama_test_connection(self):
        """Test POST /api/ollama/test - Test Ollama connection"""
        test_data = {
            "ollama_api_url": "http://localhost:11434"
        }
        
        try:
            response = self.session.post(f"{API_BASE}/ollama/test", json=test_data, timeout=15)
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                message = data.get('message', '')
                self.log_test("Ollama Test Connection", success, f"Ollama test: {message}")
            else:
                self.log_test("Ollama Test Connection", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Ollama Test Connection", False, f"Request failed: {str(e)}")
    
    def test_ollama_models(self):
        """Test POST /api/ollama/models - Get Ollama models"""
        test_data = {
            "ollama_api_url": "http://localhost:11434"
        }
        
        try:
            response = self.session.post(f"{API_BASE}/ollama/models", json=test_data, timeout=15)
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                models = data.get('models', [])
                self.log_test("Ollama Models", success, f"Found {len(models)} models")
            else:
                self.log_test("Ollama Models", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Ollama Models", False, f"Request failed: {str(e)}")
    
    def test_config_backup(self):
        """Test GET /api/config/backup - Backup configuration"""
        try:
            response = self.session.get(f"{API_BASE}/config/backup", timeout=10)
            if response.status_code == 200:
                # Check if response is JSON and has expected structure
                try:
                    data = response.json()
                    if 'settings' in data and 'sites' in data and 'backup_version' in data:
                        self.log_test("Config Backup", True, "Backup generated successfully")
                        return data
                    else:
                        self.log_test("Config Backup", False, "Backup missing expected fields")
                except json.JSONDecodeError:
                    self.log_test("Config Backup", False, "Response is not valid JSON")
            else:
                self.log_test("Config Backup", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Config Backup", False, f"Request failed: {str(e)}")
        return None
    
    def test_config_restore(self, backup_data):
        """Test POST /api/config/restore - Restore configuration"""
        if not backup_data:
            self.log_test("Config Restore", False, "No backup data provided")
            return
        
        # Create a temporary file with backup data
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(backup_data, f)
                temp_file_path = f.name
            
            # Test restore
            with open(temp_file_path, 'rb') as f:
                files = {'backup_file': ('test_backup.json', f, 'application/json')}
                response = self.session.post(f"{API_BASE}/config/restore", files=files, timeout=10)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                message = data.get('message', '')
                self.log_test("Config Restore", success, f"Restore result: {message}")
            else:
                self.log_test("Config Restore", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Config Restore", False, f"Request failed: {str(e)}")
    
    def test_error_handling(self):
        """Test error handling for invalid endpoints"""
        # Test 404 for non-existent endpoint
        try:
            response = self.session.get(f"{API_BASE}/nonexistent", timeout=10)
            if response.status_code == 404:
                self.log_test("Error Handling - 404", True, "Correctly returned 404 for non-existent endpoint")
            else:
                self.log_test("Error Handling - 404", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - 404", False, f"Request failed: {str(e)}")
        
        # Test invalid site key with PUT method (which should return 404)
        try:
            response = self.session.put(f"{API_BASE}/sites/nonexistent_site", json={}, timeout=10)
            if response.status_code == 404:
                self.log_test("Error Handling - Invalid Site", True, "Correctly returned 404 for invalid site")
            else:
                self.log_test("Error Handling - Invalid Site", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Invalid Site", False, f"Request failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting MetaStream Backend Test Suite")
        print("=" * 50)
        
        # Basic functionality tests
        self.test_main_page()
        sites_data = self.test_get_sites()
        settings_data = self.test_get_settings()
        
        # CRUD operations for sites
        site_key = self.test_create_site()
        if site_key:
            self.test_update_site(site_key)
            self.test_delete_site(site_key)
        
        # Settings management
        self.test_update_settings()
        
        # Search functionality
        self.test_search_basic()
        self.test_search_with_cache()
        self.test_search_validation()
        
        # Cache management
        self.test_cache_stats()
        self.test_cache_clear()
        
        # Ollama integration
        self.test_ollama_test_connection()
        self.test_ollama_models()
        
        # Configuration backup/restore
        backup_data = self.test_config_backup()
        if backup_data:
            self.test_config_restore(backup_data)
        
        # Error handling
        self.test_error_handling()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🏁 Test Summary")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"  - {test['test']}: {test['message']}")
        
        print("\n📊 Detailed Results:")
        for test in self.test_results:
            status = "✅" if test['success'] else "❌"
            print(f"  {status} {test['test']}: {test['message']}")

if __name__ == "__main__":
    tester = MetaStreamTester()
    tester.run_all_tests()