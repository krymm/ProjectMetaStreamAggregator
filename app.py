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
    """ Returns the full sites configuration. """
    try:
        # SITES_CONFIG is already loaded from config_manager.load_sites_config() at startup
        # and potentially updated by other CRUD operations.
        # For consistency, we can reload it here, or trust the in-memory version.
        # Reloading ensures it's always the freshest from disk if external changes were possible,
        # but for a single-process app, the in-memory SITES_CONFIG should be authoritative.
        # Let's return the current in-memory SITES_CONFIG.
        return jsonify(SITES_CONFIG)
    except Exception as e:
        logger.error(f"Error getting sites config: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Error getting sites configuration: {str(e)}"}), 500

def generate_site_key(site_name):
    """Generates a safe key from a site name."""
    # Convert to lowercase, replace spaces with underscores, remove unsafe characters
    key = site_name.lower().replace(' ', '_')
    key = ''.join(c for c in key if c.isalnum() or c == '_')
    # Ensure key is not empty after sanitization
    if not key:
        key = "unnamed_site" 
    
    # Ensure uniqueness if this key already exists
    original_key = key
    counter = 1
    while key in SITES_CONFIG:
        key = f"{original_key}_{counter}"
        counter += 1
    return key

def validate_site_config_data(site_data, is_new_site=True):
    """
    Validates site configuration data.
    Returns a list of error messages, or an empty list if valid.
    """
    errors = []
    required_fields = ['name', 'base_url', 'search_method']
    for field in required_fields:
        if field not in site_data or not site_data[field]:
            errors.append(f"Missing required field: '{field}'.")

    if 'name' in site_data and not isinstance(site_data['name'], str):
        errors.append("'name' must be a string.")
    if 'base_url' in site_data and not isinstance(site_data['base_url'], str): # Basic URL format check could be added
        errors.append("'base_url' must be a string.")
    
    search_method = site_data.get('search_method')
    if search_method:
        if not isinstance(search_method, str):
            errors.append("'search_method' must be a string.")
        elif search_method == 'scrape_search_page' and not site_data.get('search_url_template'):
            errors.append("If 'search_method' is 'scrape_search_page', then 'search_url_template' is required.")
        # Add more search_method specific validations if needed

    # Check for duplicate names if it's a new site or if the name is being changed on an update
    # For simplicity in this example, we'll only check for new sites.
    # Update logic (PUT) would need to handle name changes more carefully.
    if is_new_site and 'name' in site_data:
        if any(existing_site['name'] == site_data['name'] for existing_site in SITES_CONFIG.values()):
            errors.append(f"Site name '{site_data['name']}' already exists.")
            
    # Example of type check for optional fields
    if 'popularity_multiplier' in site_data and site_data['popularity_multiplier'] is not None:
        if not isinstance(site_data['popularity_multiplier'], (int, float)):
            errors.append("'popularity_multiplier' must be a number.")
        elif not (0 <= site_data['popularity_multiplier'] <= 5): # Example range
             errors.append("'popularity_multiplier' must be between 0 and 5.")


    # Validate scoring_weights structure if present
    if 'scoring_weights' in site_data and site_data['scoring_weights'] is not None:
        if not isinstance(site_data['scoring_weights'], dict):
            errors.append("'scoring_weights' must be an object (dictionary).")
        else:
            for weight_key, weight_val in site_data['scoring_weights'].items():
                if not isinstance(weight_val, (int, float)):
                    errors.append(f"Scoring weight '{weight_key}' must be a number.")
                elif not (0 <= weight_val <= 1): # Weights usually are 0-1
                    errors.append(f"Scoring weight '{weight_key}' must be between 0 and 1.")
    
    return errors

@app.route('/api/sites', methods=['POST'])
def create_site():
    """Creates a new site configuration."""
    global SITES_CONFIG # Ensure we are modifying the global variable
    try:
        new_site_data = request.json
        if not new_site_data:
            return jsonify({"error": "No data provided for new site."}), 400

        validation_errors = validate_site_config_data(new_site_data, is_new_site=True)
        if validation_errors:
            return jsonify({"error": "Validation failed.", "messages": validation_errors}), 400

        site_name = new_site_data['name']
        site_key = generate_site_key(site_name)
        
        # Ensure the final generated key is truly unique (should be handled by generate_site_key, but double check)
        if site_key in SITES_CONFIG:
             # This case should ideally not be hit if generate_site_key works perfectly
            return jsonify({"error": f"Site key '{site_key}' conflict. Try a different name."}), 409 

        # Add the new site to the in-memory configuration
        SITES_CONFIG[site_key] = new_site_data
        
        # Save the entire updated SITES_CONFIG to sites.json
        if config_manager.save_sites_config(SITES_CONFIG):
            logger.info(f"Site '{site_name}' created with key '{site_key}'.")
            # Return the newly created site data along with its key
            return jsonify({"message": "Site created successfully.", "site_key": site_key, "site_data": new_site_data}), 201
        else:
            # If saving failed, attempt to roll back the in-memory change
            SITES_CONFIG.pop(site_key, None)
            logger.error("Failed to save sites configuration after creating new site.")
            return jsonify({"error": "Failed to save sites configuration."}), 500

    except Exception as e:
        logger.error(f"Error creating new site: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/sites/<string:site_key>', methods=['PUT'])
def update_site(site_key):
    """Updates an existing site configuration."""
    global SITES_CONFIG
    try:
        if site_key not in SITES_CONFIG:
            return jsonify({"error": "Site not found."}), 404

        updated_site_data = request.json
        if not updated_site_data:
            return jsonify({"error": "No data provided for site update."}), 400

        # Validate the updated data. is_new_site=False because we are updating.
        # The name validation needs to be slightly different for updates:
        # The name in updated_site_data should not clash with any *other* existing site's name.
        original_name = SITES_CONFIG[site_key].get('name')
        new_name = updated_site_data.get('name')

        # Perform standard validation on the fields provided
        validation_errors = validate_site_config_data(updated_site_data, is_new_site=False) # Standard checks
        
        # Additional check for name uniqueness if name is being changed
        if new_name and new_name != original_name:
            for key, config in SITES_CONFIG.items():
                if key != site_key and config.get('name') == new_name:
                    validation_errors.append(f"Site name '{new_name}' already exists for another site.")
                    break
        
        if validation_errors:
            return jsonify({"error": "Validation failed.", "messages": validation_errors}), 400
        
        # Preserve the original site key, even if the name inside the config changes.
        # Update the in-memory configuration
        SITES_CONFIG[site_key].update(updated_site_data) # Merge update
        # Or full replace: SITES_CONFIG[site_key] = updated_site_data 
        # Full replace is often cleaner if all fields are expected in the PUT payload.
        # Let's assume full replacement for now, but ensure 'name' is part of payload.
        if 'name' not in updated_site_data : # If name is critical and not in payload
             updated_site_data['name'] = original_name # Keep original name if not provided in update
        SITES_CONFIG[site_key] = updated_site_data


        if config_manager.save_sites_config(SITES_CONFIG):
            logger.info(f"Site '{site_key}' updated successfully.")
            return jsonify({"message": "Site updated successfully.", "site_key": site_key, "site_data": SITES_CONFIG[site_key]})
        else:
            # This is tricky: if save fails, we should ideally roll back SITES_CONFIG.
            # For simplicity, we're not fully rolling back here, but a real app might need to.
            # Reloading from disk would be one way to achieve a rollback.
            logger.error("Failed to save sites configuration after updating site.")
            # Attempt to reload from disk to revert in-memory changes
            SITES_CONFIG = config_manager.load_sites_config()
            return jsonify({"error": "Failed to save sites configuration. In-memory changes may have been reverted."}), 500

    except Exception as e:
        logger.error(f"Error updating site '{site_key}': {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/sites/<string:site_key>', methods=['DELETE'])
def delete_site(site_key):
    """Deletes an existing site configuration."""
    global SITES_CONFIG
    try:
        if site_key not in SITES_CONFIG:
            return jsonify({"error": "Site not found."}), 404

        deleted_site_name = SITES_CONFIG[site_key].get('name', site_key) # For logging
        
        # Remove the site from the in-memory configuration
        SITES_CONFIG.pop(site_key)
        
        if config_manager.save_sites_config(SITES_CONFIG):
            logger.info(f"Site '{deleted_site_name}' (key: {site_key}) deleted successfully.")
            # 204 No Content is often used for successful DELETE with no body
            # However, returning a JSON message can be more informative for clients.
            return jsonify({"message": f"Site '{deleted_site_name}' deleted successfully."})
        else:
            # If saving failed, this is problematic. Attempt to reload to revert.
            logger.error("Failed to save sites configuration after deleting site.")
            SITES_CONFIG = config_manager.load_sites_config() # Revert in-memory change
            return jsonify({"error": "Failed to save sites configuration. Deletion may not be persisted."}), 500

    except Exception as e:
        logger.error(f"Error deleting site '{site_key}': {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

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

@app.route('/api/ollama/test', methods=['POST'])
def ollama_test_connection():
    """Tests the connection to a given Ollama API URL."""
    try:
        data = request.json
        ollama_api_url_base = data.get('ollama_api_url')

        if not ollama_api_url_base:
            return jsonify({"success": False, "message": "Missing 'ollama_api_url' in request."}), 400

        # Ensure the base URL doesn't end with /api/generate or other API paths
        if ollama_api_url_base.endswith('/api/generate'):
            ollama_api_url_base = ollama_api_url_base[:-len('/api/generate')]
        elif ollama_api_url_base.endswith('/api/tags'):
            ollama_api_url_base = ollama_api_url_base[:-len('/api/tags')]
        
        # Remove trailing slash if any, before appending /api/tags
        if ollama_api_url_base.endswith('/'):
            ollama_api_url_base = ollama_api_url_base[:-1]
            
        test_url = f"{ollama_api_url_base}/api/tags"
        logger.info(f"Testing Ollama connection to: {test_url}")

        try:
            # Use a timeout for the request (e.g., 10 seconds)
            response = requests.get(test_url, timeout=10)
            
            # Check if the request was successful (status code 200)
            # Ollama's /api/tags should return 200 even if no models are present (empty list)
            if response.status_code == 200:
                try:
                    # Further check if the response is valid JSON and has a 'models' key (expected for /api/tags)
                    response_json = response.json()
                    if "models" in response_json and isinstance(response_json["models"], list):
                         logger.info(f"Ollama connection to {test_url} successful. Found {len(response_json['models'])} models.")
                         return jsonify({"success": True, "message": "Ollama connection successful. Found models."})
                    else:
                        logger.warning(f"Ollama connection to {test_url} successful but response format is unexpected: {response.text[:200]}")
                        return jsonify({"success": True, "message": "Ollama connection successful but response format for /api/tags is not as expected."})
                except ValueError: # Includes JSONDecodeError
                    logger.warning(f"Ollama connection to {test_url} successful but response is not valid JSON: {response.text[:200]}")
                    return jsonify({"success": True, "message": "Ollama connection successful but response is not valid JSON."})
            else:
                logger.warning(f"Ollama connection to {test_url} failed. Status code: {response.status_code}, Response: {response.text[:200]}")
                return jsonify({"success": False, "message": f"Ollama connection failed. Status code: {response.status_code}. Response: {response.text[:100]}"})

        except requests.exceptions.Timeout:
            logger.error(f"Ollama connection to {test_url} timed out.")
            return jsonify({"success": False, "message": "Ollama connection timed out."})
        except requests.exceptions.ConnectionError:
            logger.error(f"Ollama connection to {test_url} refused or failed.")
            return jsonify({"success": False, "message": "Ollama connection refused or failed. Check if Ollama is running and accessible."})
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama connection test to {test_url} failed with an error: {e}")
            return jsonify({"success": False, "message": f"Ollama connection failed: {str(e)}"})

    except Exception as e:
        logger.error(f"Error in /api/ollama/test endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "message": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/ollama/models', methods=['POST'])
def ollama_get_models():
    """Fetches available models from a given Ollama API URL."""
    try:
        data = request.json
        ollama_api_url_base = data.get('ollama_api_url')

        if not ollama_api_url_base:
            return jsonify({"success": False, "message": "Missing 'ollama_api_url' in request.", "models": []}), 400

        # Sanitize the base URL (remove common API paths and trailing slashes)
        if ollama_api_url_base.endswith('/api/generate'):
            ollama_api_url_base = ollama_api_url_base[:-len('/api/generate')]
        elif ollama_api_url_base.endswith('/api/tags'):
            ollama_api_url_base = ollama_api_url_base[:-len('/api/tags')]
        
        if ollama_api_url_base.endswith('/'):
            ollama_api_url_base = ollama_api_url_base[:-1]
            
        tags_url = f"{ollama_api_url_base}/api/tags"
        logger.info(f"Fetching Ollama models from: {tags_url}")

        try:
            response = requests.get(tags_url, timeout=15) # Increased timeout slightly for model listing

            if response.status_code == 200:
                try:
                    response_json = response.json()
                    if "models" in response_json and isinstance(response_json["models"], list):
                        model_names = [model.get("name") for model in response_json["models"] if model.get("name")]
                        logger.info(f"Successfully fetched {len(model_names)} models from {tags_url}.")
                        return jsonify({"success": True, "models": model_names})
                    else:
                        logger.warning(f"Fetched models from {tags_url}, but response format is unexpected: {response.text[:200]}")
                        return jsonify({"success": False, "message": "Model list format unexpected.", "models": []})
                except ValueError: # Includes JSONDecodeError
                    logger.warning(f"Response from {tags_url} is not valid JSON: {response.text[:200]}")
                    return jsonify({"success": False, "message": "Invalid JSON response from Ollama.", "models": []})
            else:
                logger.warning(f"Failed to fetch models from {tags_url}. Status: {response.status_code}, Response: {response.text[:200]}")
                return jsonify({
                    "success": False, 
                    "message": f"Ollama API request failed. Status: {response.status_code}. Details: {response.text[:100]}",
                    "models": []
                })

        except requests.exceptions.Timeout:
            logger.error(f"Timeout when fetching models from {tags_url}.")
            return jsonify({"success": False, "message": "Request to Ollama timed out.", "models": []})
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error when fetching models from {tags_url}.")
            return jsonify({"success": False, "message": "Could not connect to Ollama. Check URL and if Ollama is running.", "models": []})
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when fetching models from {tags_url}: {e}")
            return jsonify({"success": False, "message": f"Failed to fetch models: {str(e)}", "models": []})

    except Exception as e:
        logger.error(f"Error in /api/ollama/models endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "message": f"An unexpected error occurred: {str(e)}", "models": []}), 500

# --- Backup and Restore Endpoints ---
from datetime import datetime # For timestamp in backup

@app.route('/api/config/backup', methods=['GET'])
def backup_configuration():
    """Creates a downloadable JSON backup of current settings and sites configuration."""
    try:
        # Load the most current configurations directly from manager functions
        # This ensures we're backing up what's persisted, not just in-memory state if it could differ.
        current_settings = config_manager.load_settings()
        current_sites = config_manager.load_sites_config()

        backup_data = {
            "backup_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "settings": current_settings,
            "sites": current_sites
        }

        response_json = json.dumps(backup_data, indent=2)
        
        # Create a filename with a timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"metastream_backup_{timestamp_str}.json"

        return Response(
            response_json,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error generating configuration backup: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to generate backup: {str(e)}"}), 500

@app.route('/api/config/restore', methods=['POST'])
def restore_configuration():
    """Restores settings and sites configuration from an uploaded JSON backup file."""
    global USER_SETTINGS, SITES_CONFIG # To update in-memory configs after restore
    
    if 'backup_file' not in request.files:
        return jsonify({"success": False, "message": "No backup file provided."}), 400

    file = request.files['backup_file']

    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file."}), 400

    if file and file.filename.endswith('.json'):
        try:
            # Read file content
            file_content = file.read().decode('utf-8')
            restored_data = json.loads(file_content)

            # Validate structure
            if not isinstance(restored_data, dict):
                raise ValueError("Backup data is not a valid JSON object.")
            
            if "settings" not in restored_data or not isinstance(restored_data["settings"], dict):
                raise ValueError("Backup data is missing 'settings' or it's not a valid object.")
            
            if "sites" not in restored_data or not isinstance(restored_data["sites"], dict):
                raise ValueError("Backup data is missing 'sites' or it's not a valid object.")

            # Optional: Check backup_version if you implement versioning
            # backup_version = restored_data.get("backup_version")
            # if backup_version != "1.0": # Example version check
            #     raise ValueError(f"Unsupported backup version: {backup_version}. Expected 1.0.")

            restored_settings = restored_data["settings"]
            restored_sites = restored_data["sites"]

            # At this point, you might want to perform more detailed validation on the content
            # of restored_settings and restored_sites to ensure they are well-formed.
            # For example, using parts of validate_site_config_data for each site in restored_sites.
            # For simplicity, this example proceeds directly to saving if basic structure is okay.

            # Save restored configurations
            settings_saved = config_manager.save_settings(restored_settings)
            sites_saved = config_manager.save_sites_config(restored_sites)

            if not settings_saved or not sites_saved:
                # This is a critical error state. The files might be partially written or inconsistent.
                # A more robust solution might try to roll back or restore from a temporary pre-restore backup.
                logger.error("Critical error: Failed to save one or both configuration files during restore.")
                # Attempt to reload original configs to minimize inconsistent state in memory
                USER_SETTINGS = config_manager.load_settings() 
                SITES_CONFIG = config_manager.load_sites_config()
                return jsonify({"success": False, "message": "Failed to save restored configurations. System state might be inconsistent."}), 500
            
            # Reload configurations into memory
            USER_SETTINGS = config_manager.load_settings()
            SITES_CONFIG = config_manager.load_sites_config()
            
            # Update cache expiry if it was changed in restored settings
            if 'cache_expiry_minutes' in USER_SETTINGS:
                 SEARCH_CACHE.expiry_seconds = USER_SETTINGS['cache_expiry_minutes'] * 60

            logger.info("Configuration successfully restored from backup.")
            return jsonify({"success": True, "message": "Configuration restored successfully. Please refresh the page if UI elements do not update immediately."})

        except json.JSONDecodeError:
            logger.error("Error decoding JSON from backup file.")
            return jsonify({"success": False, "message": "Invalid JSON format in backup file."}), 400
        except ValueError as ve: # Catch our custom validation errors
            logger.error(f"Validation error in backup file: {ve}")
            return jsonify({"success": False, "message": f"Invalid backup file structure: {str(ve)}"}), 400
        except Exception as e:
            logger.error(f"Error restoring configuration: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({"success": False, "message": f"Failed to restore configuration: {str(e)}"}), 500
    else:
        return jsonify({"success": False, "message": "Invalid file type. Please upload a .json file."}), 400

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