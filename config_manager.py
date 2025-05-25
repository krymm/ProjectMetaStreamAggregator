# config_manager.py
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_CONFIG_PATH = os.path.join(CONFIG_DIR, 'sites.json')
SITES_EXAMPLE_PATH = os.path.join(CONFIG_DIR, 'sites.example.json')
SETTINGS_PATH = os.path.join(CONFIG_DIR, 'settings.json')
SETTINGS_EXAMPLE_PATH = os.path.join(CONFIG_DIR, 'settings.example.json')

DEFAULT_SETTINGS = {
    "google_api_key": None,
    "google_search_engine_id": None,
    "bing_api_key": None,
    "duckduckgo_api_key": None,
    "ollama_api_url": "http://localhost:11434/api/generate", # Default includes /api/generate
    "ollama_model": "llama3", # Default model
    "results_per_page_default": 100,
    "max_pages_per_site": 1,
    "check_links_default": True,
    "cache_expiry_minutes": 10,
    "default_search_sites": [],
    "results_layout": "grid",
    "scoring_weights": {
        "relevance_weight": 0.50,
        "rating_weight": 0.30,
        "views_weight": 0.10,
        "multiplier_effect": 0.10
    }
}

EXAMPLE_SITES = {
    "example_site1": {
        "name": "Example Site 1",
        "base_url": "https://example.com",
        "search_method": "scrape_search_page",
        "search_url_template": "https://example.com/search?q={query}&page={page}",
        "results_container_selector": ".search-results",
        "result_item_selector": ".result-item",
        "title_selector": ".video-title",
        "video_url_selector": ".video-title a",
        "thumbnail_selector": ".thumb img",
        "duration_selector": ".duration",
        "rating_selector": ".rating",
        "views_selector": ".views",
        "author_selector": ".author",
        "next_page_selector": ".pagination .next",
        "popularity_multiplier": 1.0
    },
    "example_site2": {
        "name": "Example Site 2",
        "base_url": "https://example2.com",
        "search_method": "google_site_search",
        "results_container_selector": ".video-list",
        "result_item_selector": ".video-item",
        "title_selector": ".video-title",
        "video_url_selector": ".video-title a",
        "thumbnail_selector": ".thumb img",
        "duration_selector": ".duration",
        "rating_selector": ".rating",
        "views_selector": ".views",
        "author_selector": ".author",
        "popularity_multiplier": 0.8
    },
    "example_site3": {
        "name": "Example Site 3",
        "base_url": "https://example3.com",
        "search_method": "bing_site_search",
        "results_container_selector": ".search-results",
        "result_item_selector": ".result-item",
        "title_selector": ".title",
        "video_url_selector": ".title a",
        "thumbnail_selector": ".thumbnail img",
        "duration_selector": ".duration",
        "rating_selector": ".rating",
        "views_selector": ".views",
        "author_selector": ".author",
        "popularity_multiplier": 0.9
    },
    "example_site4": {
        "name": "Example Site 4",
        "base_url": "https://example4.com",
        "search_method": "duckduckgo_site_search",
        "results_container_selector": ".search-results",
        "result_item_selector": ".result-item",
        "title_selector": ".title",
        "video_url_selector": ".title a",
        "thumbnail_selector": ".thumbnail img",
        "duration_selector": ".duration",
        "rating_selector": ".rating",
        "views_selector": ".views",
        "author_selector": ".author",
        "popularity_multiplier": 0.85
    }
}

def create_example_files():
    """Create example configuration files if they don't exist."""
    # Create sites.example.json if it doesn't exist
    if not os.path.exists(SITES_EXAMPLE_PATH):
        try:
            with open(SITES_EXAMPLE_PATH, 'w') as f:
                json.dump(EXAMPLE_SITES, f, indent=2)
            logger.info(f"Created {SITES_EXAMPLE_PATH}")
        except Exception as e:
            logger.error(f"Error creating {SITES_EXAMPLE_PATH}: {e}")
    
    # Create settings.example.json if it doesn't exist
    if not os.path.exists(SETTINGS_EXAMPLE_PATH):
        try:
            with open(SETTINGS_EXAMPLE_PATH, 'w') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)
            logger.info(f"Created {SETTINGS_EXAMPLE_PATH}")
        except Exception as e:
            logger.error(f"Error creating {SETTINGS_EXAMPLE_PATH}: {e}")

def load_sites_config():
    """Loads site configurations from sites.json."""
    # Create example files if they don't exist
    create_example_files()
    
    try:
        with open(SITES_CONFIG_PATH, 'r') as f:
            sites_config = json.load(f)
            
            # Basic validation
            if not isinstance(sites_config, dict):
                logger.warning(f"{SITES_CONFIG_PATH} is not properly formatted (not a dictionary). Using empty config.")
                return {}
                
            # Validate each site configuration 
            for site_name, site_config in list(sites_config.items()):
                if not isinstance(site_config, dict):
                    logger.warning(f"Site config for '{site_name}' is not a dictionary. Skipping.")
                    del sites_config[site_name]
                    continue
                    
                required_fields = ['name', 'base_url', 'search_method']
                missing_fields = [field for field in required_fields if field not in site_config]
                
                if missing_fields:
                    logger.warning(f"Site config for '{site_name}' is missing required fields: {missing_fields}. Skipping.")
                    del sites_config[site_name]
                    continue
                    
                # Check search method and required fields
                search_method = site_config.get('search_method')
                if search_method == 'scrape_search_page' and 'search_url_template' not in site_config:
                    logger.warning(f"Site config for '{site_name}' uses scrape_search_page but missing search_url_template. Skipping.")
                    del sites_config[site_name]
                    continue
                    
            return sites_config
            
    except FileNotFoundError:
        logger.warning(f"{SITES_CONFIG_PATH} not found. Please create this file based on {SITES_EXAMPLE_PATH}.")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding {SITES_CONFIG_PATH}. Check JSON syntax.")
        return {}

def load_settings():
    """Loads user settings, merging with defaults."""
    # Create example files if they don't exist
    create_example_files()
    
    settings = DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_PATH, 'r') as f:
            user_settings = json.load(f)
            
            # Basic validation
            if not isinstance(user_settings, dict):
                logger.warning(f"{SETTINGS_PATH} is not properly formatted (not a dictionary). Using defaults.")
                return settings
                
            # Special handling for API keys - if they exist in the file but are empty strings,
            # don't override the defaults (which might be None)
            for key in ['google_api_key', 'google_search_engine_id', 'bing_api_key', 'duckduckgo_api_key', 'ollama_api_url']:
                if key in user_settings and user_settings[key] == "":
                    del user_settings[key]
            
            # Special handling for nested dictionaries like scoring_weights
            if 'scoring_weights' in user_settings and isinstance(user_settings['scoring_weights'], dict):
                # Update default weights with user weights instead of replacing completely
                settings['scoring_weights'].update(user_settings['scoring_weights'])
                # Remove from user_settings to avoid overwriting the merged dictionary below
                del user_settings['scoring_weights']
                
            # Update settings with user values
            settings.update(user_settings)
            
    except FileNotFoundError:
        logger.warning(f"{SETTINGS_PATH} not found. Using default settings.")
        # Optionally save default settings file here if it doesn't exist
        save_settings(settings)
    except json.JSONDecodeError:
        logger.error(f"Error decoding {SETTINGS_PATH}. Using default settings.")
    
    return settings

def save_settings(settings_data):
    """Saves user settings to settings.json."""
    try:
        # Mask sensitive information for logging
        masked_data = settings_data.copy()
        for key in ['google_api_key', 'google_search_engine_id', 'bing_api_key', 'duckduckgo_api_key']:
            if key in masked_data and masked_data[key]:
                masked_data[key] = '********'
        logger.info(f"Saving settings: {masked_data}")
        
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings_data, f, indent=2)
        logger.info(f"Settings saved to {SETTINGS_PATH}")
        return True
    except IOError as e:
        logger.error(f"Error saving settings to {SETTINGS_PATH}: {e}")
        return False

def load_default_settings():
    """Returns the default settings without any user customizations."""
    return DEFAULT_SETTINGS.copy()

def save_sites_config(sites_data):
    """Saves the complete sites configuration to sites.json.

    Args:
        sites_data (dict): A dictionary containing all site configurations.
    
    Returns:
        bool: True if saving was successful, False otherwise.
    """
    try:
        # Basic validation: ensure sites_data is a dictionary
        if not isinstance(sites_data, dict):
            logger.error("Invalid sites_data format: must be a dictionary.")
            return False
            
        # Further validation could be added here to check structure of each site_config in sites_data
        # For example, ensuring each site has 'name', 'base_url', etc.
        # This would be similar to the validation in load_sites_config.

        with open(SITES_CONFIG_PATH, 'w') as f:
            json.dump(sites_data, f, indent=2)
        logger.info(f"Sites configuration saved to {SITES_CONFIG_PATH}")
        return True
    except IOError as e:
        logger.error(f"Error saving sites configuration to {SITES_CONFIG_PATH}: {e}")
        return False
    except Exception as e: # Catch any other unexpected errors e.g. during JSON serialization
        logger.error(f"Unexpected error saving sites configuration: {e}")
        return False