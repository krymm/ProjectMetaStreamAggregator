# app.py
from flask import Flask, request, jsonify, render_template, Response
import json
import time
import concurrent.futures
import logging
import requests
import traceback

# Import custom modules
import config_manager
import site_scraper
import ranker
import link_checker
import cache_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("metastream.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MetaStream")

# --- Initialization ---
app = Flask(__name__)

# Load configurations at startup
try:
    logger.info("Loading configuration files...")
    SITES_CONFIG = config_manager.load_sites_config()
    USER_SETTINGS = config_manager.load_settings()

    # Initialize cache
    logger.info("Initializing cache...")
    SEARCH_CACHE = cache_manager.SearchCache(
        expiry_minutes=USER_SETTINGS.get('cache_expiry_minutes', 10)
    )
except Exception as e:
    logger.critical(f"Error during initialization: {e}")
    logger.critical(f"Traceback: {traceback.format_exc()}")
    # Continue with empty configs if there's an error
    SITES_CONFIG = {}
    USER_SETTINGS = config_manager.DEFAULT_SETTINGS.copy()
    SEARCH_CACHE = cache_manager.SearchCache()

# --- Routes ---
@app.route('/')
def index():
    """ Serves the main HTML page. """
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return jsonify({"error": f"Error rendering index page: {str(e)}"}), 500

@app.route('/api/sites', methods=['GET'])
def get_sites():
    """ Returns the list of configured site names and base URLs. """
    try:
        site_list = [{'name': name, 'base_url': conf.get('base_url')}
                    for name, conf in SITES_CONFIG.items()]
        return jsonify(site_list)
    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        return jsonify({"error": f"Error getting sites: {str(e)}"}), 500

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Returns current settings."""
    try:
        # Add APIs configured flag for frontend
        settings_copy = USER_SETTINGS.copy()
        apis_configured = {
            'google': bool(USER_SETTINGS.get('google_api_key') and USER_SETTINGS.get('google_search_engine_id')),
            'bing': bool(USER_SETTINGS.get('bing_api_key')),
            'duckduckgo': True  # DuckDuckGo doesn't require API key
        }
        settings_copy['apis_configured'] = apis_configured
        
        # Mask sensitive keys before sending
        for key in ['google_api_key', 'bing_api_key', 'duckduckgo_api_key']:
            if key in settings_copy and settings_copy[key]:
                settings_copy[key] = '********'
                
        return jsonify(settings_copy)
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({"error": f"Error getting settings: {str(e)}"}), 500

@app.route('/api/settings/default', methods=['GET'])
def get_default_settings():
    """Returns default settings."""
    try:
        return jsonify(config_manager.load_default_settings())
    except Exception as e:
        logger.error(f"Error getting default settings: {e}")
        return jsonify({"error": f"Error getting default settings: {str(e)}"}), 500

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """ Updates and saves user settings. """
    try:
        new_settings_data = request.json
        if not new_settings_data:
            return jsonify({"error": "No settings data provided"}), 400

        # Update in-memory settings
        USER_SETTINGS.update(new_settings_data)
        
        # Update cache expiry if it was changed
        if 'cache_expiry_minutes' in new_settings_data:
            SEARCH_CACHE.expiry_seconds = new_settings_data['cache_expiry_minutes'] * 60

        # Save to file
        if config_manager.save_settings(USER_SETTINGS):
            return jsonify({"message": "Settings saved successfully", "settings": USER_SETTINGS})
        else:
            # Failed to save, maybe revert in-memory update or warn user
            return jsonify({"error": "Failed to save settings to file"}), 500
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Error updating settings: {str(e)}"}), 500

def perform_search_operation(query, selected_sites, page, use_cache, check_links, max_pages_per_site):
    """
    Core search orchestration logic extracted from the API route
    
    Args:
        query (str): Search query
        selected_sites (list): List of site names to search
        page (int): Page number for pagination
        use_cache (bool): Whether to use cache
        check_links (bool): Whether to check links
        max_pages_per_site (int): Maximum number of pages to scrape per site
        
    Returns:
        dict: Search results
    """
    start_time = time.time()
    debug_info = {}

    # Check cache first if enabled
    if use_cache:
        cached_results = SEARCH_CACHE.get(query, selected_sites, page)
        if cached_results:
            logger.info(f"Using cached results for query: {query}, sites: {selected_sites}, page: {page}")
            cached_results['debug_info']['cached'] = True
            cached_results['debug_info']['time_taken_s'] = round(time.time() - start_time, 2)
            return cached_results

    all_raw_results = []
    selected_configs = {name: SITES_CONFIG[name] for name in selected_sites if name in SITES_CONFIG}
    site_errors = {}

    # --- 1. Execute Searches Concurrently ---
    search_futures = []
    # Use threading because scraping/API calls involve waiting (I/O bound)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_configs) or 1) as executor:
        future_to_site = {}  # Track which future corresponds to which site
        
        for site_name, config in selected_configs.items():
            method = config.get('search_method', 'scrape_search_page')

            if method == 'scrape_search_page':
                future = executor.submit(
                    site_scraper.scrape_search_page, 
                    config, 
                    query, 
                    page=1, 
                    max_pages_per_site=max_pages_per_site
                )
                search_futures.append(future)
                future_to_site[future] = site_name
                
            elif method == 'google_site_search':
                api_key = USER_SETTINGS.get('google_api_key')
                cse_id = USER_SETTINGS.get('google_search_engine_id')
                base_url = config.get("base_url")
                if api_key and cse_id and base_url:
                    future = executor.submit(
                        site_scraper.execute_google_search, 
                        site_name, 
                        base_url, 
                        query, 
                        api_key, 
                        cse_id
                    )
                    search_futures.append(future)
                    future_to_site[future] = site_name
                else:
                    logger.warning(f"Skipping Google search for {site_name}: Missing API Key, CSE ID or Base URL")
                    site_errors[site_name] = "Missing Google API configuration"
                    
            elif method == 'bing_site_search':
                api_key = USER_SETTINGS.get('bing_api_key')
                base_url = config.get("base_url")
                if api_key and base_url:
                    future = executor.submit(
                        site_scraper.execute_bing_search,
                        site_name,
                        base_url,
                        query,
                        api_key
                    )
                    search_futures.append(future)
                    future_to_site[future] = site_name
                else:
                    logger.warning(f"Skipping Bing search for {site_name}: Missing API Key or Base URL")
                    site_errors[site_name] = "Missing Bing API configuration"
                    
            elif method == 'duckduckgo_site_search':
                api_key = USER_SETTINGS.get('duckduckgo_api_key')
                base_url = config.get("base_url")
                if base_url:
                    future = executor.submit(
                        site_scraper.execute_duckduckgo_search,
                        site_name,
                        base_url,
                        query,
                        api_key
                    )
                    search_futures.append(future)
                    future_to_site[future] = site_name
                else:
                    logger.warning(f"Skipping DuckDuckGo search for {site_name}: Missing Base URL")
                    site_errors[site_name] = "Missing base URL"
                    
            elif method == 'api':
                future = executor.submit(site_scraper.call_site_api, config, query)
                search_futures.append(future)
                future_to_site[future] = site_name

        # Collect results as they complete
        for future in concurrent.futures.as_completed(search_futures):
            site_name = future_to_site.get(future, "unknown")
            try:
                results = future.result()
                if results:
                    all_raw_results.extend(results)
                    logger.info(f"Got {len(results)} results from {site_name}")
                else:
                    logger.warning(f"No results from {site_name}")
                    site_errors[site_name] = "No results returned"
            except Exception as exc:
                # Log error with context
                logger.error(f"Search failed for {site_name}: {exc}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                site_errors[site_name] = str(exc)

    logger.info(f"Found {len(all_raw_results)} raw results across {len(selected_configs)} sites")
    debug_info["raw_results_count"] = len(all_raw_results)
    debug_info["site_errors"] = site_errors

    # --- 2. Rank & Process (Includes Deduplication) ---
    # Get scoring weights from settings
    scoring_weights = USER_SETTINGS.get('scoring_weights', {})
    
    # Pass the original query for relevance calculation
    ranked_processed_results = ranker.rank_and_process(
        all_raw_results, 
        SITES_CONFIG, 
        query, 
        scoring_weights
    )
    logger.info(f"{len(ranked_processed_results)} results after ranking & deduplication")
    debug_info["ranked_count"] = len(ranked_processed_results)

    # --- 3. Check Links Concurrently (if enabled) ---
    if check_links:
        valid_results, broken_results = link_checker.check_links_concurrently(ranked_processed_results)
        logger.info(f"{len(valid_results)} valid links, {len(broken_results)} broken links")
        debug_info["valid_links_count"] = len(valid_results)
        debug_info["broken_links_count"] = len(broken_results)
    else:
        # Skip link checking if disabled
        valid_results = ranked_processed_results
        broken_results = []
        logger.info(f"Skipped link checking as per user request")
        debug_info["valid_links_count"] = len(valid_results)
        debug_info["broken_links_count"] = 0

    # --- 4. Paginate Combined, Valid Results ---
    results_per_page = USER_SETTINGS.get('results_per_page_default', 100)
    try:
        requested_per_page = request.json.get('resultsPerPage')
        if requested_per_page:
            results_per_page = int(requested_per_page)
    except (ValueError, AttributeError):
        pass # Use Default

    start_index = (page - 1) * results_per_page
    end_index = start_index + results_per_page
    paginated_valid = valid_results[start_index:end_index]

    total_valid = len(valid_results)
    total_pages = (total_valid + results_per_page - 1) // results_per_page if total_valid > 0 else 1

    end_time = time.time()
    search_time = end_time - start_time
    logger.info(f'Search request completed in {search_time:.2f} seconds')
    debug_info["time_taken_s"] = round(search_time, 2)
    debug_info["cached"] = False

    # --- Prepare Response ---
    search_response = {
        "query": query,
        "search_sites": selected_sites,
        "valid_results": paginated_valid,
        "broken_results": broken_results, # Return all broken for now, paginate in JS if needed
        "pagination": {
            "current_page": page,
            "results_per_page": results_per_page,
            "total_valid_results": total_valid,
            "total_broken_results": len(broken_results),
            "total_pages": total_pages
        },
        "debug_info": debug_info
    }
    
    # Cache successful results if caching is enabled
    if use_cache:
        SEARCH_CACHE.set(query, selected_sites, page, search_response)
        logger.info(f"Cached search results for query: {query}, sites: {selected_sites}, page: {page}")
    
    return search_response

@app.route('/api/search', methods=['POST'])
def perform_search():
    """ Handles the search request, orchestrates scraping, ranking, checking. """
    try:
        data = request.json
        query = data.get('query')
        selected_site_names = data.get('sites', [])
        page = data.get('page', 1)
        
        # Get search options from request or defaults
        use_cache = data.get('use_cache', True)
        check_links = data.get('check_links', USER_SETTINGS.get('check_links_default', True))
        max_pages_per_site = data.get(
            'max_pages_per_site', 
            USER_SETTINGS.get('max_pages_per_site', 1)
        )

        if not query or not query.strip():
            return jsonify({"error": "Query is required"}), 400
            
        if not selected_site_names:
            return jsonify({"error": "At least one site must be selected"}), 400
        
        # Log the search request
        logger.info(f"Search request: query='{query}', sites={selected_site_names}, page={page}, use_cache={use_cache}, check_links={check_links}")
        
        # Delegate to the core search function
        search_results = perform_search_operation(
            query, 
            selected_site_names, 
            page, 
            use_cache, 
            check_links, 
            max_pages_per_site
        )
        
        return jsonify(search_results)
        
    except Exception as e:
        logger.error(f"Error during search: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": f"Search failed: {str(e)}",
            "error_type": type(e).__name__
        }), 500

@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics."""
    try:
        stats = SEARCH_CACHE.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({"error": f"Error getting cache stats: {str(e)}"}), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache."""
    try:
        data = request.json or {}
        query = data.get('query')
        sites = data.get('sites')
        
        if query and sites:
            # Clear specific cache
            count = SEARCH_CACHE.clear(query, sites)
            logger.info(f"Cleared cache for query '{query}' ({count} entries)")
            return jsonify({"message": f"Cache cleared for query '{query}' ({count} entries)"})
        else:
            # Clear all cache
            count = SEARCH_CACHE.clear()
            logger.info(f"Cleared all cache ({count} entries)")
            return jsonify({"message": f"All cache cleared ({count} entries)"})
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({"error": f"Error clearing cache: {str(e)}"}), 500

# --- Ollama Integration Endpoint ---
@app.route('/api/ollama/process', methods=['POST'])
def ollama_process():
    try:
        data = request.json
        prompt = data.get('prompt')
        model = data.get('model', 'llama3')
        ollama_url = USER_SETTINGS.get('ollama_api_url')

        if not prompt or not ollama_url:
            return jsonify({"error": "Prompt and Ollama URL are required"}), 400

        logger.info(f"Ollama request: model={model}, prompt_length={len(prompt)}")
            
        ollama_data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False # Get full response at once
        })
        headers = {'Content-Type': 'application/json'}
        response = requests.post(ollama_url, data=ollama_data, headers=headers, timeout=60) # Long timeout
        response.raise_for_status()
        ollama_response = response.json()
        
        logger.info(f"Ollama response received, length: {len(ollama_response.get('response', ''))}")
        return jsonify(ollama_response) # Return Ollama's response structure

    except requests.exceptions.RequestException as e:
         logger.error(f"Error connecting to Ollama at {ollama_url}: {e}")
         return jsonify({"error": f"Could not connect to Ollama: {e}"}), 503 # service unavailable
    except Exception as e:
         logger.error(f"Error processing Ollama request: {e}")
         logger.error(f"Traceback: {traceback.format_exc()}")
         return jsonify({"error": f"Failed to process request with Ollama: {e}"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

# --- Run the App ---
if __name__ == '__main__':
    logger.info("Starting Flask Server...")
    logger.info(f"Sites Configured: {len(SITES_CONFIG)}")
    logger.info(f"Google API Key Loaded: {'Yes' if USER_SETTINGS.get('google_api_key') else 'No'}")
    logger.info(f"Google CSE ID Loaded: {'Yes' if USER_SETTINGS.get('google_search_engine_id') else 'No'}")
    logger.info(f"Bing API Key Loaded: {'Yes' if USER_SETTINGS.get('bing_api_key') else 'No'}")
    logger.info(f"DuckDuckGo API Configured: {'Yes' if USER_SETTINGS.get('duckduckgo_api_key') else 'No'}")
    # Run on any IP address to allow external access
    # Use debug=False to avoid conflicts with imported code.py
    # Use threaded=True to handle concurrent requests from the browser better
    app.run(host='0.0.0.0', port=8001, debug=False, threaded=True) # Use allowed port for Scout environment