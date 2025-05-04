#!/usr/bin/env python3
"""
Performance test script for MetaStream Aggregator

This script tests the performance of the MSA application by measuring
response times, memory usage, and throughput under various loads.
"""

import requests
import json
import time
import argparse
import logging
import statistics
import concurrent.futures
import psutil
import os
import sys
import gc
from typing import Dict, List, Tuple, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("performance_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MSA-Performance-Test")

# Default settings
BASE_URL = "http://127.0.0.1:8001"
DEFAULT_TIMEOUT = 60  # Seconds
TEST_DATA_FILE = "test_data.json"

class PerformanceTester:
    """Performance tester for MSA application."""
    
    def __init__(self, base_url: str = BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the tester.
        
        Args:
            base_url: Base URL of the MSA application
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.test_data = self._load_test_data()
        self.results = {
            "api_latency": {},
            "search_performance": {},
            "memory_usage": [],
            "throughput": {}
        }
        
        # Get process for memory monitoring if running locally
        self.process = self._get_process()
    
    def _load_test_data(self) -> Dict:
        """Load test data from JSON file."""
        try:
            with open(TEST_DATA_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Test data file '{TEST_DATA_FILE}' not found.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in test data file '{TEST_DATA_FILE}'.")
            return {}
    
    def _get_process(self) -> Optional[psutil.Process]:
        """
        Get the process object for the Flask application.
        
        Returns:
            Process object or None if not found
        """
        try:
            # Get current process (assuming the Flask app is running in the same process tree)
            current_pid = os.getpid()
            current_process = psutil.Process(current_pid)
            
            # Check if we're running the Flask app directly (debug mode)
            if "python" in current_process.name().lower() and "app.py" in " ".join(current_process.cmdline()):
                return current_process
            
            # Otherwise, try to find the Flask process
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if "python" in proc.name().lower() and any("app.py" in cmd for cmd in proc.cmdline()):
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            logger.warning("Could not find Flask process for memory monitoring")
            return None
            
        except Exception as e:
            logger.error(f"Error getting process: {e}")
            return None
    
    def _make_request(self, method: str, endpoint: str, json_data: Dict = None, 
                     params: Dict = None) -> Tuple[bool, Dict, float]:
        """
        Make a request to the API and measure response time.
        
        Args:
            method: HTTP method to use (get, post, etc.)
            endpoint: API endpoint path
            json_data: JSON data to send in the request body
            params: URL parameters to include
            
        Returns:
            Tuple of (success, response_data, response_time_seconds)
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            response = None
            
            if method.lower() == 'get':
                response = requests.get(url, params=params, timeout=self.timeout)
            elif method.lower() == 'post':
                response = requests.post(url, json=json_data, timeout=self.timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return False, {}, 0
                
            response_time = time.time() - start_time
            
            if response.status_code >= 400:
                logger.error(f"Request to {url} returned status {response.status_code}")
                return False, {}, response_time
            
            # For non-JSON responses (e.g., HTML), return the text content
            if 'application/json' not in response.headers.get('Content-Type', ''):
                return True, {'text': response.text}, response_time
                
            return True, response.json(), response_time
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return False, {}, time.time() - start_time
        except json.JSONDecodeError:
            logger.error(f"Response from {url} is not valid JSON")
            return False, {}, time.time() - start_time
    
    def run_all_tests(self, iterations: int = 3):
        """
        Run all performance tests.
        
        Args:
            iterations: Number of times to repeat each test
        """
        logger.info(f"Starting performance tests with {iterations} iterations...")
        
        # Run API latency tests
        self.test_api_latency(iterations)
        
        # Run search performance tests
        self.test_search_performance(iterations)
        
        # Run memory usage tests
        self.test_memory_usage()
        
        # Run throughput tests
        self.test_throughput()
        
        # Generate report
        self.generate_report()
        
        return True
    
    def test_api_latency(self, iterations: int = 3):
        """
        Test API latency for various endpoints.
        
        Args:
            iterations: Number of times to repeat each test
        """
        logger.info("Testing API latency...")
        
        # Define endpoints to test
        endpoints = [
            {"name": "Index Page", "method": "get", "path": "/"},
            {"name": "Sites API", "method": "get", "path": "/api/sites"},
            {"name": "Settings API", "method": "get", "path": "/api/settings"},
            {"name": "Cache Stats API", "method": "get", "path": "/api/cache/stats"}
        ]
        
        for endpoint in endpoints:
            name = endpoint["name"]
            method = endpoint["method"]
            path = endpoint["path"]
            
            times = []
            success_count = 0
            
            logger.info(f"Testing latency for {name}...")
            
            for i in range(iterations):
                # Force garbage collection before each test to minimize interference
                gc.collect()
                
                success, _, response_time = self._make_request(method, path)
                
                if success:
                    times.append(response_time)
                    success_count += 1
                
                # Small delay between requests
                time.sleep(0.5)
            
            # Calculate statistics
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                median_time = statistics.median(times)
                std_dev = statistics.stdev(times) if len(times) > 1 else 0
                
                logger.info(f"{name} latency stats: Avg={avg_time:.4f}s, Min={min_time:.4f}s, Max={max_time:.4f}s, Median={median_time:.4f}s")
                
                self.results["api_latency"][name] = {
                    "avg_time": avg_time,
                    "min_time": min_time,
                    "max_time": max_time,
                    "median_time": median_time,
                    "std_dev": std_dev,
                    "success_rate": success_count / iterations
                }
            else:
                logger.warning(f"No successful requests for {name}")
    
    def test_search_performance(self, iterations: int = 3):
        """
        Test search performance with different queries and site combinations.
        
        Args:
            iterations: Number of times to repeat each test
        """
        logger.info("Testing search performance...")
        
        # Get available sites
        success, sites_response, _ = self._make_request('get', '/api/sites')
        if not success or not sites_response:
            logger.error("Failed to get sites, skipping search performance tests")
            return
            
        available_sites = [site['name'] for site in sites_response]
        if not available_sites:
            logger.error("No sites available, skipping search performance tests")
            return
            
        # Get test queries
        test_queries = self.test_data.get('search_queries', [])
        if not test_queries:
            # Use default queries if none in test data
            test_queries = [
                {"name": "Short Query", "query": "test"},
                {"name": "Medium Query", "query": "test video search"},
                {"name": "Long Query", "query": "this is a longer query with multiple words to test search performance"}
            ]
        
        # Test different combinations
        for query_data in test_queries[:3]:  # Limit to first 3 for speed
            query = query_data['query']
            if not query:  # Skip empty query
                continue
                
            # Test with single site
            self._test_search_scenario(
                f"Single Site - {query_data['name']}",
                query,
                [available_sites[0]],
                iterations
            )
            
            # Test with multiple sites if available
            if len(available_sites) >= 2:
                self._test_search_scenario(
                    f"Multiple Sites - {query_data['name']}",
                    query,
                    available_sites[:2],
                    iterations
                )
            
            # Test with all sites
            self._test_search_scenario(
                f"All Sites - {query_data['name']}",
                query,
                available_sites,
                iterations
            )
    
    def _test_search_scenario(self, name: str, query: str, sites: List[str], iterations: int):
        """
        Test a specific search scenario.
        
        Args:
            name: Test name
            query: Search query
            sites: List of sites to search
            iterations: Number of iterations
        """
        logger.info(f"Testing search scenario: {name}")
        
        times = []
        success_count = 0
        result_counts = []
        
        for i in range(iterations):
            # Force garbage collection before each test
            gc.collect()
            
            # Test with cache disabled to measure true search performance
            success, search_results, response_time = self._make_request(
                'post', 
                '/api/search', 
                json_data={
                    'query': query,
                    'sites': sites,
                    'use_cache': False,
                    'check_links': False  # Disable link checking for faster tests
                }
            )
            
            if success:
                times.append(response_time)
                success_count += 1
                
                # Record result count
                if 'valid_results' in search_results:
                    result_counts.append(len(search_results['valid_results']))
            
            # Longer delay between searches to avoid rate limiting
            time.sleep(2)
        
        # Calculate statistics
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            
            avg_results = statistics.mean(result_counts) if result_counts else 0
            
            logger.info(f"{name} search performance: Avg={avg_time:.4f}s, Min={min_time:.4f}s, Max={max_time:.4f}s, Median={median_time:.4f}s, Avg Results={avg_results:.1f}")
            
            self.results["search_performance"][name] = {
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "median_time": median_time,
                "std_dev": std_dev,
                "avg_results": avg_results,
                "success_rate": success_count / iterations
            }
        else:
            logger.warning(f"No successful searches for {name}")
    
    def test_memory_usage(self, duration: int = 30, interval: int = 5):
        """
        Test memory usage over time.
        
        Args:
            duration: Duration of the test in seconds
            interval: Interval between measurements in seconds
        """
        if not self.process:
            logger.warning("Process not found, skipping memory usage test")
            return
            
        logger.info(f"Testing memory usage over {duration} seconds...")
        
        try:
            measurements = []
            start_time = time.time()
            end_time = start_time + duration
            
            while time.time() < end_time:
                # Get memory usage
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
                
                measurements.append({
                    "timestamp": time.time() - start_time,
                    "memory_mb": memory_mb
                })
                
                logger.debug(f"Memory usage: {memory_mb:.2f} MB")
                
                # Wait for next measurement
                time.sleep(interval)
            
            # Calculate statistics
            memory_values = [m["memory_mb"] for m in measurements]
            
            if memory_values:
                avg_memory = statistics.mean(memory_values)
                min_memory = min(memory_values)
                max_memory = max(memory_values)
                
                logger.info(f"Memory usage stats: Avg={avg_memory:.2f} MB, Min={min_memory:.2f} MB, Max={max_memory:.2f} MB")
                
                self.results["memory_usage"] = {
                    "measurements": measurements,
                    "avg_memory": avg_memory,
                    "min_memory": min_memory,
                    "max_memory": max_memory
                }
            else:
                logger.warning("No memory measurements collected")
                
        except Exception as e:
            logger.error(f"Error monitoring memory usage: {e}")
    
    def test_throughput(self, duration: int = 10, max_workers: int = 5):
        """
        Test throughput with concurrent requests.
        
        Args:
            duration: Duration of the test in seconds
            max_workers: Maximum number of concurrent workers
        """
        logger.info(f"Testing throughput with {max_workers} concurrent workers for {duration} seconds...")
        
        # Get available sites
        success, sites_response, _ = self._make_request('get', '/api/sites')
        if not success or not sites_response:
            logger.error("Failed to get sites, skipping throughput tests")
            return
            
        available_sites = [site['name'] for site in sites_response]
        if not available_sites:
            logger.error("No sites available, skipping throughput tests")
            return
            
        # Simple search query for throughput testing
        query = "test"
        sites = [available_sites[0]]  # Use first site only for throughput test
        
        # Prepare search payload
        search_data = {
            'query': query,
            'sites': sites,
            'use_cache': True,  # Use cache to avoid overloading external services
            'check_links': False  # Disable link checking for speed
        }
        
        # Track results
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        # Function for worker to execute
        def perform_search():
            nonlocal successful_requests, failed_requests
            
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/api/search",
                    json=search_data,
                    timeout=self.timeout
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    successful_requests += 1
                    response_times.append(response_time)
                else:
                    failed_requests += 1
                    logger.warning(f"Request failed with status {response.status_code}")
                    
            except Exception as e:
                failed_requests += 1
                logger.warning(f"Request failed: {e}")
        
        # Run concurrent workers
        start_time = time.time()
        end_time = start_time + duration
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while time.time() < end_time:
                # Submit a new task for each worker
                futures = [executor.submit(perform_search) for _ in range(max_workers)]
                
                # Wait for all tasks to complete
                concurrent.futures.wait(futures)
                
                # Small delay before next batch
                time.sleep(0.1)
        
        # Calculate statistics
        total_time = time.time() - start_time
        total_requests = successful_requests + failed_requests
        requests_per_second = successful_requests / total_time
        
        logger.info(f"Throughput results: {successful_requests} successful requests in {total_time:.2f} seconds")
        logger.info(f"Throughput: {requests_per_second:.2f} requests/second")
        logger.info(f"Success rate: {(successful_requests / total_requests * 100):.2f}% ({successful_requests}/{total_requests})")
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            logger.info(f"Response time stats: Avg={avg_time:.4f}s, Min={min_time:.4f}s, Max={max_time:.4f}s")
            
            self.results["throughput"] = {
                "total_time": total_time,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "requests_per_second": requests_per_second,
                "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
                "avg_response_time": avg_time,
                "min_response_time": min_time,
                "max_response_time": max_time
            }
        else:
            logger.warning("No successful requests during throughput test")
    
    def generate_report(self):
        """Generate a performance report."""
        report_path = "performance_report.json"
        
        try:
            with open(report_path, 'w') as f:
                json.dump(self.results, f, indent=2)
                
            logger.info(f"Performance report saved to {report_path}")
            
            # Print summary to console
            print("\n===== PERFORMANCE TEST SUMMARY =====")
            
            # API Latency
            print("\nAPI Latency (seconds):")
            for endpoint, stats in self.results["api_latency"].items():
                print(f"  {endpoint}: Avg={stats['avg_time']:.4f}s, Min={stats['min_time']:.4f}s, Max={stats['max_time']:.4f}s")
            
            # Search Performance
            print("\nSearch Performance (seconds):")
            for scenario, stats in self.results["search_performance"].items():
                print(f"  {scenario}: Avg={stats['avg_time']:.4f}s, Avg Results={stats['avg_results']:.1f}")
            
            # Memory Usage
            if "avg_memory" in self.results["memory_usage"]:
                mem_stats = self.results["memory_usage"]
                print(f"\nMemory Usage: Avg={mem_stats['avg_memory']:.2f} MB, Min={mem_stats['min_memory']:.2f} MB, Max={mem_stats['max_memory']:.2f} MB")
            
            # Throughput
            if self.results["throughput"]:
                throughput = self.results["throughput"]
                print(f"\nThroughput: {throughput['requests_per_second']:.2f} requests/second")
                print(f"Success Rate: {(throughput['success_rate'] * 100):.2f}% ({throughput['successful_requests']}/{throughput['successful_requests'] + throughput['failed_requests']})")
                print(f"Avg Response Time: {throughput['avg_response_time']:.4f} seconds")
            
            print("\n====================================")
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")

def main():
    """Parse arguments and run the tester."""
    parser = argparse.ArgumentParser(description="Test performance of MSA application")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the MSA application")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations for each test")
    args = parser.parse_args()
    
    tester = PerformanceTester(base_url=args.url, timeout=args.timeout)
    success = tester.run_all_tests(iterations=args.iterations)
    
    return 0 if success else 1

if __name__ == "__main__":
    main()