#!/usr/bin/env python3
"""
Debugging Tool for MetaStream Aggregator

This script provides debugging tools for the MSA application,
including configuration validation, site scraper testing, and
endpoint testing.
"""

import argparse
import json
import os
import sys
import re
import logging
import time
import traceback
from typing import Dict, List, Any, Tuple, Optional
import importlib.util

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MSA-Debug")

class MSADebugger:
    """Debug tool for MetaStream Aggregator."""
    
    def __init__(self):
        """Initialize the debugger."""
        self.reports = {}
        self.modules = {}
        
        # Try to load MSA modules
        self._load_modules()
    
    def _load_modules(self):
        """Try to import MSA modules for advanced debugging."""
        module_names = [
            "config_manager",
            "site_scraper",
            "ranker",
            "link_checker",
            "cache_manager"
        ]
        
        for module_name in module_names:
            try:
                spec = importlib.util.find_spec(module_name)
                if spec:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.modules[module_name] = module
                    logger.info(f"Loaded module: {module_name}")
                else:
                    logger.warning(f"Module not found: {module_name}")
            except Exception as e:
                logger.error(f"Error loading module {module_name}: {e}")
    
    def debug_config(self):
        """Debug configuration files."""
        logger.info("Debugging configuration files...")
        
        config_files = [
            {"name": "sites.json", "required": True},
            {"name": "settings.json", "required": False, "default": "settings.example.json"}
        ]
        
        config_report = {
            "files_checked": [],
            "issues": [],
            "recommendations": []
        }
        
        for config_file in config_files:
            file_name = config_file["name"]
            file_path = os.path.abspath(file_name)
            
            file_report = {
                "name": file_name,
                "exists": os.path.exists(file_path),
                "size_bytes": 0,
                "valid_json": False,
                "structure_valid": False,
                "content_summary": {},
                "issues": []
            }
            
            if file_report["exists"]:
                try:
                    file_stat = os.stat(file_path)
                    file_report["size_bytes"] = file_stat.st_size
                    file_report["modified"] = time.ctime(file_stat.st_mtime)
                    
                    # Check if file is valid JSON
                    with open(file_path, 'r') as f:
                        content = json.load(f)
                        file_report["valid_json"] = True
                        
                        # Check structure based on file type
                        if file_name == "sites.json":
                            file_report["structure_valid"] = isinstance(content, dict)
                            
                            if file_report["structure_valid"]:
                                file_report["content_summary"] = {
                                    "site_count": len(content),
                                    "site_names": list(content.keys()),
                                    "search_methods": {}
                                }
                                
                                # Check each site configuration
                                for site_name, site_config in content.items():
                                    if not isinstance(site_config, dict):
                                        file_report["issues"].append(f"Site '{site_name}' is not a dictionary")
                                        continue
                                        
                                    # Track search methods
                                    search_method = site_config.get("search_method", "unknown")
                                    if search_method not in file_report["content_summary"]["search_methods"]:
                                        file_report["content_summary"]["search_methods"][search_method] = 0
                                    file_report["content_summary"]["search_methods"][search_method] += 1
                                    
                                    # Check for required fields
                                    required_fields = ["name", "base_url", "search_method"]
                                    for field in required_fields:
                                        if field not in site_config:
                                            file_report["issues"].append(f"Site '{site_name}' is missing required field: {field}")
                                    
                                    # Check URL template for scrape method
                                    if search_method == "scrape_search_page":
                                        if "search_url_template" not in site_config:
                                            file_report["issues"].append(f"Site '{site_name}' uses scrape_search_page but missing search_url_template")
                                        elif "{query}" not in site_config.get("search_url_template", ""):
                                            file_report["issues"].append(f"Site '{site_name}' search_url_template is missing {{query}} placeholder")
                            else:
                                file_report["issues"].append("sites.json must be a dictionary/object")
                                config_report["recommendations"].append("Check sites.json structure, it should be a dictionary of site configurations")
                                
                        elif file_name == "settings.json":
                            file_report["structure_valid"] = isinstance(content, dict)
                            
                            if file_report["structure_valid"]:
                                # Check for essential settings
                                essential_settings = ["results_per_page_default", "cache_expiry_minutes"]
                                missing_settings = [s for s in essential_settings if s not in content]
                                
                                if missing_settings:
                                    file_report["issues"].append(f"Missing essential settings: {', '.join(missing_settings)}")
                                    config_report["recommendations"].append(f"Add missing settings to settings.json: {', '.join(missing_settings)}")
                                
                                # Check scoring weights
                                if "scoring_weights" in content:
                                    weights = content["scoring_weights"]
                                    if not isinstance(weights, dict):
                                        file_report["issues"].append("scoring_weights is not a dictionary")
                                    else:
                                        expected_weights = ["relevance_weight", "rating_weight", "views_weight", "multiplier_effect"]
                                        missing_weights = [w for w in expected_weights if w not in weights]
                                        
                                        if missing_weights:
                                            file_report["issues"].append(f"Missing scoring weights: {', '.join(missing_weights)}")
                                
                                # Check API keys for configured search methods
                                if "config_manager" in self.modules:
                                    sites_config = self.modules["config_manager"].load_sites_config()
                                    
                                    # Check Google API config
                                    needs_google = any(site.get("search_method") == "google_site_search" for site in sites_config.values())
                                    has_google = bool(content.get("google_api_key")) and bool(content.get("google_search_engine_id"))
                                    
                                    if needs_google and not has_google:
                                        file_report["issues"].append("Google Search is configured for sites but API key/CSE ID is missing")
                                        config_report["recommendations"].append("Add Google API key and Search Engine ID to settings.json")
                                    
                                    # Check Bing API config
                                    needs_bing = any(site.get("search_method") == "bing_site_search" for site in sites_config.values())
                                    has_bing = bool(content.get("bing_api_key"))
                                    
                                    if needs_bing and not has_bing:
                                        file_report["issues"].append("Bing Search is configured for sites but API key is missing")
                                        config_report["recommendations"].append("Add Bing API key to settings.json")
                            else:
                                file_report["issues"].append("settings.json must be a dictionary/object")
                                config_report["recommendations"].append("Check settings.json structure, it should be a dictionary of settings")
                                
                except json.JSONDecodeError as e:
                    file_report["issues"].append(f"Invalid JSON: {e}")
                    config_report["recommendations"].append(f"Fix JSON syntax in {file_name}: {e}")
                except Exception as e:
                    file_report["issues"].append(f"Error reading file: {e}")
            elif config_file["required"]:
                file_report["issues"].append("Required configuration file is missing")
                
                # Check if there's a default/example file
                if "default" in config_file:
                    default_file = config_file["default"]
                    if os.path.exists(default_file):
                        config_report["recommendations"].append(f"Copy {default_file} to {file_name} and customize it")
                    else:
                        config_report["recommendations"].append(f"Create {file_name} configuration file")
                else:
                    config_report["recommendations"].append(f"Create {file_name} configuration file")
            
            config_report["files_checked"].append(file_report)
            
            # Add issues to the main report
            for issue in file_report["issues"]:
                config_report["issues"].append(f"{file_name}: {issue}")
        
        self.reports["config"] = config_report
        return config_report
    
    def debug_scraper(self, site_name=None, query="test"):
        """
        Debug the site scraper for a specific site or all sites.
        
        Args:
            site_name: Site to test (None for all sites)
            query: Test query to use
        """
        logger.info(f"Testing site scraper with query '{query}'...")
        
        # Load config manager module
        if "config_manager" not in self.modules or "site_scraper" not in self.modules:
            logger.error("Required modules not loaded. Cannot test scraper.")
            return None
        
        config_manager = self.modules["config_manager"]
        site_scraper = self.modules["site_scraper"]
        
        # Load site configurations
        try:
            sites_config = config_manager.load_sites_config()
        except Exception as e:
            logger.error(f"Error loading site configurations: {e}")
            return None
        
        # Filter sites if a specific site was requested
        if site_name and site_name in sites_config:
            test_sites = {site_name: sites_config[site_name]}
        else:
            test_sites = sites_config
        
        scraper_report = {
            "query": query,
            "sites_tested": [],
            "issues": [],
            "recommendations": []
        }
        
        # Test each site
        for site_name, site_config in test_sites.items():
            site_report = {
                "name": site_name,
                "search_method": site_config.get("search_method", "unknown"),
                "result_count": 0,
                "success": False,
                "duration_seconds": 0,
                "issues": [],
                "sample_results": []
            }
            
            try:
                logger.info(f"Testing scraper for site: {site_name}")
                
                start_time = time.time()
                
                # Execute search based on search method
                search_method = site_config.get("search_method", "scrape_search_page")
                if search_method == "scrape_search_page":
                    results = site_scraper.scrape_search_page(site_config, query)
                elif search_method == "google_site_search":
                    # Need API key and CSE ID from settings
                    settings = config_manager.load_settings()
                    api_key = settings.get("google_api_key")
                    cse_id = settings.get("google_search_engine_id")
                    
                    if not api_key or not cse_id:
                        site_report["issues"].append("Missing Google API key or CSE ID in settings")
                    else:
                        results = site_scraper.execute_google_search(
                            site_name, 
                            site_config.get("base_url", ""), 
                            query, 
                            api_key, 
                            cse_id
                        )
                elif search_method == "bing_site_search":
                    # Need API key from settings
                    settings = config_manager.load_settings()
                    api_key = settings.get("bing_api_key")
                    
                    if not api_key:
                        site_report["issues"].append("Missing Bing API key in settings")
                    else:
                        results = site_scraper.execute_bing_search(
                            site_name,
                            site_config.get("base_url", ""),
                            query,
                            api_key
                        )
                elif search_method == "duckduckgo_site_search":
                    results = site_scraper.execute_duckduckgo_search(
                        site_name,
                        site_config.get("base_url", ""),
                        query,
                        None  # DuckDuckGo doesn't require API key
                    )
                else:
                    site_report["issues"].append(f"Unsupported search method: {search_method}")
                    results = []
                
                duration = time.time() - start_time
                
                site_report["duration_seconds"] = round(duration, 2)
                site_report["result_count"] = len(results)
                site_report["success"] = True
                
                # Get sample results for debugging
                if results:
                    sample_count = min(3, len(results))
                    site_report["sample_results"] = results[:sample_count]
                else:
                    site_report["issues"].append("No results found")
                
                # Check for common issues in results
                if results:
                    # Check for missing thumbnails
                    missing_thumbs = sum(1 for r in results if not r.get("thumbnail"))
                    if missing_thumbs > 0:
                        issue_pct = (missing_thumbs / len(results)) * 100
                        if issue_pct > 50:
                            site_report["issues"].append(f"High percentage of results ({issue_pct:.1f}%) missing thumbnails")
                    
                    # Check for missing durations
                    missing_durations = sum(1 for r in results if not r.get("duration_str"))
                    if missing_durations > 0:
                        issue_pct = (missing_durations / len(results)) * 100
                        if issue_pct > 50:
                            site_report["issues"].append(f"High percentage of results ({issue_pct:.1f}%) missing durations")
                    
                    # Check for unparsed durations
                    unparsed_durations = sum(1 for r in results if r.get("duration_str") and not r.get("duration_sec"))
                    if unparsed_durations > 0:
                        issue_pct = (unparsed_durations / len(results)) * 100
                        if issue_pct > 50:
                            site_report["issues"].append(f"High percentage of results ({issue_pct:.1f}%) with unparsed durations")
                    
                    # Check for potentially invalid URLs
                    invalid_urls = sum(1 for r in results if not r.get("url") or not r.get("url").startswith("http"))
                    if invalid_urls > 0:
                        site_report["issues"].append(f"{invalid_urls} results have invalid or missing URLs")
                
            except Exception as e:
                site_report["issues"].append(f"Error: {str(e)}")
                site_report["traceback"] = traceback.format_exc()
                scraper_report["recommendations"].append(f"Fix scraper for {site_name}: {str(e)}")
            
            scraper_report["sites_tested"].append(site_report)
            
            # Add site issues to the main report
            for issue in site_report["issues"]:
                scraper_report["issues"].append(f"{site_name}: {issue}")
        
        self.reports["scraper"] = scraper_report
        return scraper_report
    
    def debug_ranking(self, query="test", sample_size=10):
        """
        Debug the ranking system with sample results.
        
        Args:
            query: Test query to use
            sample_size: Number of sample results to generate
        """
        logger.info(f"Testing ranking with query '{query}'...")
        
        # Load required modules
        if "ranker" not in self.modules or "config_manager" not in self.modules:
            logger.error("Required modules not loaded. Cannot test ranking.")
            return None
        
        ranker = self.modules["ranker"]
        config_manager = self.modules["config_manager"]
        
        ranking_report = {
            "query": query,
            "results_tested": sample_size,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Load site configurations for popularity multipliers
            sites_config = config_manager.load_sites_config()
            
            # Load scoring weights from settings
            settings = config_manager.load_settings()
            scoring_weights = settings.get("scoring_weights", {})
            
            # Generate sample results with varying attributes
            sample_results = []
            
            for i in range(sample_size):
                # Create results with different characteristics
                relevance_level = i % 3  # 0 = low, 1 = medium, 2 = high
                rating_level = (i // 3) % 3  # 0 = low, 1 = medium, 2 = high
                views_level = i % 5  # 0-4, more variety
                site_index = i % len(sites_config) if sites_config else 0
                
                # Get a site name from the configurations
                site_name = list(sites_config.keys())[site_index] if sites_config else f"site_{site_index}"
                
                # Create result with varying attributes
                result = {
                    "title": f"Test Result {i+1}" + (" relevant " + query if relevance_level > 0 else ""),
                    "url": f"https://example.com/video/{i+1}",
                    "thumbnail": f"https://example.com/thumb/{i+1}.jpg",
                    "duration_str": f"{i % 10 + 1}:{i % 60:02d}",
                    "duration_sec": (i % 10 + 1) * 60 + (i % 60),
                    "rating_str": f"{(rating_level + 1) * 3}/10",
                    "site_rating": (rating_level + 1) * 0.3,  # 0.3, 0.6, 0.9
                    "views_str": f"{(views_level + 1) * 1000}",
                    "views": (views_level + 1) * 1000,
                    "site": site_name,
                    "source_method": "test",
                    "description_snippet": f"This is a test result with {'high' if relevance_level > 1 else 'medium' if relevance_level > 0 else 'low'} relevance to {query}"
                }
                
                sample_results.append(result)
            
            # Process results through the ranker
            start_time = time.time()
            ranked_results = ranker.rank_and_process(sample_results, sites_config, query, scoring_weights)
            duration = time.time() - start_time
            
            ranking_report["duration_seconds"] = round(duration, 4)
            ranking_report["success"] = True
            ranking_report["ranked_count"] = len(ranked_results)
            
            # Analyze ranking results
            ranking_report["rankings"] = []
            
            for i, result in enumerate(ranked_results):
                ranking_report["rankings"].append({
                    "position": i + 1,
                    "title": result.get("title"),
                    "score": result.get("calc_score"),
                    "relevance_score": result.get("relevance_score"),
                    "site_rating": result.get("site_rating"),
                    "views": result.get("views"),
                    "site": result.get("site"),
                    "has_alternates": bool(result.get("alternates"))
                })
            
            # Check for duplicate detection
            duplicate_groups = {}
            
            for result in ranked_results:
                if "alternates" in result and result["alternates"]:
                    duplicate_groups[result["title"]] = {
                        "primary": result["url"],
                        "alternates": [alt["url"] for alt in result["alternates"]]
                    }
            
            ranking_report["duplicate_groups"] = duplicate_groups
            ranking_report["duplicate_count"] = len(duplicate_groups)
            
            # Check for issues
            if len(ranked_results) < len(sample_results) and len(duplicate_groups) == 0:
                ranking_report["issues"].append("Results count reduced but no duplicates identified")
            
            if len(ranked_results) > 0:
                # Check if scores are properly calculated
                for result in ranked_results:
                    if "calc_score" not in result:
                        ranking_report["issues"].append("Missing calculated score in ranked results")
                        break
            else:
                ranking_report["issues"].append("No results after ranking")
            
        except Exception as e:
            ranking_report["issues"].append(f"Error: {str(e)}")
            ranking_report["traceback"] = traceback.format_exc()
            ranking_report["success"] = False
        
        self.reports["ranking"] = ranking_report
        return ranking_report
    
    def debug_link_checker(self, url_count=5):
        """
        Debug the link checker with sample URLs.
        
        Args:
            url_count: Number of URLs to check
        """
        logger.info(f"Testing link checker with {url_count} URLs...")
        
        # Load required modules
        if "link_checker" not in self.modules:
            logger.error("Required modules not loaded. Cannot test link checker.")
            return None
        
        link_checker = self.modules["link_checker"]
        
        link_report = {
            "urls_tested": url_count,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Generate test URLs (mix of valid and invalid)
            test_urls = [
                {"url": "https://www.google.com", "title": "Google", "site": "test", "expected": True},
                {"url": "https://www.bing.com", "title": "Bing", "site": "test", "expected": True},
                {"url": "https://www.example.com", "title": "Example", "site": "test", "expected": True},
                {"url": "https://thisurldoesnotexistforsure12345.com", "title": "Invalid Domain", "site": "test", "expected": False},
                {"url": "https://www.google.com/notarealpage12345", "title": "404 Page", "site": "test", "expected": False}
            ]
            
            # Limit to requested count
            test_urls = test_urls[:url_count]
            
            # Add actual URLs to report
            link_report["test_urls"] = [url["url"] for url in test_urls]
            
            # Test link checker
            start_time = time.time()
            valid_results, broken_results = link_checker.check_links_concurrently(test_urls)
            duration = time.time() - start_time
            
            link_report["duration_seconds"] = round(duration, 2)
            link_report["valid_count"] = len(valid_results)
            link_report["broken_count"] = len(broken_results)
            link_report["success"] = True
            
            # Check results against expectations
            correct_count = 0
            for url_data in test_urls:
                url = url_data["url"]
                expected = url_data["expected"]
                
                # Find in results
                found_valid = any(r.get("url") == url for r in valid_results)
                found_broken = any(r.get("url") == url for r in broken_results)
                
                # Determine if classification matches expectation
                if (expected and found_valid) or (not expected and found_broken):
                    correct_count += 1
                else:
                    link_report["issues"].append(f"URL {url} was {'valid' if found_valid else 'broken'} but expected {'valid' if expected else 'broken'}")
            
            link_report["accuracy"] = round(correct_count / len(test_urls) * 100, 1)
            
            if link_report["accuracy"] < 80:
                link_report["issues"].append(f"Link checker accuracy is low: {link_report['accuracy']}%")
                link_report["recommendations"].append("Review link_checker.py implementation")
            
        except Exception as e:
            link_report["issues"].append(f"Error: {str(e)}")
            link_report["traceback"] = traceback.format_exc()
            link_report["success"] = False
            link_report["recommendations"].append("Fix link checker implementation")
        
        self.reports["link_checker"] = link_report
        return link_report
    
    def debug_cache_manager(self):
        """Debug the cache manager."""
        logger.info("Testing cache manager...")
        
        # Load required modules
        if "cache_manager" not in self.modules:
            logger.error("Required modules not loaded. Cannot test cache manager.")
            return None
        
        cache_manager = self.modules["cache_manager"]
        
        cache_report = {
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Create a test cache instance
            test_cache = cache_manager.SearchCache(expiry_minutes=1)
            
            # Test setting a value
            start_time = time.time()
            test_cache.set("test_query", ["test_site"], 1, {"test": "data"})
            set_duration = time.time() - start_time
            
            # Test getting the value
            start_time = time.time()
            cached_data = test_cache.get("test_query", ["test_site"], 1)
            get_duration = time.time() - start_time
            
            # Test if cachee works
            cache_hit = cached_data is not None
            
            # Test expiry by manipulating expiry time
            test_cache.expiry_seconds = 0  # Set to expire immediately
            time.sleep(0.1)  # Brief delay
            expired_data = test_cache.get("test_query", ["test_site"], 1)
            expiry_works = expired_data is None
            
            # Test clearing cache
            test_cache.expiry_seconds = 60  # Reset to normal
            test_cache.set("test_query", ["test_site"], 1, {"test": "data"})
            test_cache.clear("test_query", ["test_site"])
            cleared_data = test_cache.get("test_query", ["test_site"], 1)
            clear_works = cleared_data is None
            
            # Get stats
            stats = test_cache.get_stats()
            
            # Build report
            cache_report["set_duration_seconds"] = round(set_duration, 6)
            cache_report["get_duration_seconds"] = round(get_duration, 6)
            cache_report["cache_hit"] = cache_hit
            cache_report["expiry_works"] = expiry_works
            cache_report["clear_works"] = clear_works
            cache_report["stats"] = stats
            cache_report["success"] = cache_hit and expiry_works and clear_works
            
            # Check for issues
            if not cache_hit:
                cache_report["issues"].append("Cache miss for recently cached data")
                cache_report["recommendations"].append("Check cache implementation")
            
            if not expiry_works:
                cache_report["issues"].append("Cache expiry not working correctly")
                cache_report["recommendations"].append("Review cache expiry logic")
            
            if not clear_works:
                cache_report["issues"].append("Cache clearing not working correctly")
                cache_report["recommendations"].append("Review cache clearing logic")
            
        except Exception as e:
            cache_report["issues"].append(f"Error: {str(e)}")
            cache_report["traceback"] = traceback.format_exc()
            cache_report["success"] = False
            cache_report["recommendations"].append("Fix cache manager implementation")
        
        self.reports["cache_manager"] = cache_report
        return cache_report
    
    def debug_all(self):
        """Run all debugging tests."""
        logger.info("Running all debugging tests...")
        
        # Check configuration
        self.debug_config()
        
        # Test site scraper
        self.debug_scraper()
        
        # Test ranking
        self.debug_ranking()
        
        # Test link checker
        self.debug_link_checker()
        
        # Test cache manager
        self.debug_cache_manager()
        
        # Generate summary report
        summary = {
            "components_tested": len(self.reports),
            "total_issues": sum(len(report.get("issues", [])) for report in self.reports.values()),
            "component_status": {},
            "issues_by_component": {},
            "recommendations": []
        }
        
        for component, report in self.reports.items():
            summary["component_status"][component] = "success" if report.get("success", report.get("issues", [])) else "failed"
            summary["issues_by_component"][component] = len(report.get("issues", []))
            
            # Add recommendations
            if "recommendations" in report:
                summary["recommendations"].extend(report["recommendations"])
        
        self.reports["summary"] = summary
        
        # Save all reports to file
        self.save_reports("debug_report.json")
        
        return summary
    
    def save_reports(self, filename="debug_report.json"):
        """
        Save all debugging reports to a JSON file.
        
        Args:
            filename: Output filename
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.reports, f, indent=2)
            logger.info(f"Debug reports saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving reports: {e}")
            return False
    
    def display_summary(self):
        """Display a summary of debugging results."""
        if not self.reports:
            print("No debugging has been performed yet.")
            return
            
        if "summary" not in self.reports:
            print("No summary report available. Run debug_all() first.")
            return
            
        summary = self.reports["summary"]
        
        print("\n==== MetaStream Debugger Summary ====\n")
        print(f"Components tested: {summary['components_tested']}")
        print(f"Total issues found: {summary['total_issues']}")
        
        print("\nComponent Status:")
        for component, status in summary["component_status"].items():
            print(f"  {component}: {status} ({summary['issues_by_component'][component]} issues)")
        
        if summary["recommendations"]:
            print("\nRecommendations:")
            for i, rec in enumerate(summary["recommendations"], 1):
                print(f"  {i}. {rec}")
        
        print("\nFull report saved to debug_report.json")
        print("\n=====================================")

def main():
    """Parse arguments and run the debugger."""
    parser = argparse.ArgumentParser(description="Debug tool for MetaStream Aggregator")
    parser.add_argument("--component", choices=["config", "scraper", "ranking", "link-checker", "cache", "all"],
                        default="all", help="Component to debug")
    parser.add_argument("--query", default="test", help="Test query to use")
    parser.add_argument("--site", help="Specific site to test (for scraper)")
    args = parser.parse_args()
    
    # Change to the directory containing the code
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    debugger = MSADebugger()
    
    if args.component == "config":
        debugger.debug_config()
    elif args.component == "scraper":
        debugger.debug_scraper(args.site, args.query)
    elif args.component == "ranking":
        debugger.debug_ranking(args.query)
    elif args.component == "link-checker":
        debugger.debug_link_checker()
    elif args.component == "cache":
        debugger.debug_cache_manager()
    else:  # "all"
        debugger.debug_all()
    
    debugger.display_summary()
    return 0

if __name__ == "__main__":
    sys.exit(main())