# site_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import random
import re
import logging
from urllib.parse import urljoin, quote_plus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Make sure you have Google API client installed ---
# pip install --upgrade google-api-python-client
# You might need specific authentication setup based on your Google Cloud Project config
try:
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("Google API Client library not found. Google site search will not work.")
    logger.warning("Install using: pip install --upgrade google-api-python-client")

# --- User Agent ---
# Use a realistic User-Agent Header to avoid immediate blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_attribute_or_text(element, selector, attribute=None):
    """ Safely extracts text or an attribute from a sub element using a selector. """
    try:
        target = element.select_one(selector)
        if target:
            if attribute:
                return target.get(attribute, '').strip()
            return target.get_text(strip=True)
    except Exception as e:
        # Log this error for debugging selector issues
        logger.debug(f"Selector Error for '{selector}': {e}")
        pass
    return ''

def parse_duration(duration_str):
    """
    Parse a duration string into seconds.
    
    Examples:
    - "10:30" -> 630
    - "1:30:45" -> 5445
    - "5m 30s" -> 330
    """
    if not duration_str:
        return None
    
    # Try HH:MM:SS or MM:SS format
    if ":" in duration_str:
        parts = duration_str.split(":")
        if len(parts) == 3:  # HH:MM:SS
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            except ValueError:
                pass
        elif len(parts) == 2:  # MM:SS
            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            except ValueError:
                pass
    
    # Try Xm Ys format
    minute_match = re.search(r'(\d+)m', duration_str)
    second_match = re.search(r'(\d+)s', duration_str)
    
    total_seconds = 0
    
    if minute_match:
        try:
            total_seconds += int(minute_match.group(1)) * 60
        except ValueError:
            pass
    
    if second_match:
        try:
            total_seconds += int(second_match.group(1))
        except ValueError:
            pass
    
    if total_seconds > 0:
        return total_seconds
    
    return None

def parse_rating(rating_str):
    """
    Parse a rating string into a normalized 0-1 scale.
    
    Examples:
    - "95%" -> 0.95
    - "4.5/5" -> 0.9
    - "8.7/10" -> 0.87
    """
    if not rating_str:
        return None
    
    # Try percentage
    percent_match = re.search(r'(\d+(?:\.\d+)?)%', rating_str)
    if percent_match:
        try:
            return float(percent_match.group(1)) / 100.0
        except ValueError:
            pass
    
    # Try X/Y format
    ratio_match = re.search(r'(\d+(?:\.\d+)?)[/\\](\d+(?:\.\d+)?)', rating_str)
    if ratio_match:
        try:
            numerator = float(ratio_match.group(1))
            denominator = float(ratio_match.group(2))
            if denominator > 0:
                return numerator / denominator
        except ValueError:
            pass
    
    # Try just a number (assume out of 5)
    number_match = re.search(r'^(\d+(?:\.\d+)?)$', rating_str.strip())
    if number_match:
        try:
            value = float(number_match.group(1))
            # Assume it's out of 5 unless it's clearly higher
            if value <= 5:
                return value / 5.0
            elif value <= 10:
                return value / 10.0
            elif value <= 100:
                return value / 100.0
        except ValueError:
            pass
    
    # Try extracting first number as a fallback
    number_match = re.search(r'(\d+(?:\.\d+)?)', rating_str)
    if number_match:
        try:
            value = float(number_match.group(1))
            # Make educated guess about scale
            if value <= 5:
                return value / 5.0
            elif value <= 10:
                return value / 10.0
            elif value <= 100:
                return value / 100.0
        except ValueError:
            pass
    
    return None

def parse_views(views_str):
    """
    Parse a view count string into an integer.
    
    Examples:
    - "1.2M" -> 1200000
    - "10K" -> 10000
    - "1,234,567" -> 1234567
    """
    if not views_str:
        return None
    
    # Remove commas
    views_str = views_str.replace(',', '')
    
    # Try K/M/B format
    if 'K' in views_str or 'k' in views_str:
        try:
            value = float(re.search(r'(\d+(?:\.\d+)?)', views_str).group(1))
            return int(value * 1000)
        except (ValueError, AttributeError):
            pass
    
    if 'M' in views_str or 'm' in views_str:
        try:
            value = float(re.search(r'(\d+(?:\.\d+)?)', views_str).group(1))
            return int(value * 1000000)
        except (ValueError, AttributeError):
            pass
    
    if 'B' in views_str or 'b' in views_str:
        try:
            value = float(re.search(r'(\d+(?:\.\d+)?)', views_str).group(1))
            return int(value * 1000000000)
        except (ValueError, AttributeError):
            pass
    
    # Try just a number
    try:
        return int(float(views_str))
    except ValueError:
        pass
    
    # Try extracting first number
    number_match = re.search(r'(\d+(?:\.\d+)?)', views_str)
    if number_match:
        try:
            return int(float(number_match.group(1)))
        except ValueError:
            pass
    
    return None

def scrape_search_page(site_config, query, page=1, max_pages_per_site=1):
    """ Scrapes a search results page for a given site config and query."""
    results = []
    
    if not site_config.get('search_url_template'):
        logger.error(f"Error: Misconfigured site '{site_config.get('name')}': missing 'search_url_template'")
        return results # Empty list if misconfigured

    search_url = site_config['search_url_template'].format(query=quote_plus(query), page=page)
    logger.info(f"Scraping: {search_url}")

    try:
        time.sleep(random.uniform(0.5, 2.0)) # Basic politeness delay
        response = requests.get(search_url, headers=HEADERS, timeout=20) # Increased timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.text, 'html.parser') # Use lxml if available ('lxml')

        container = soup.select_one(site_config.get('results_container_selector', 'body')) # Default to body if no container
        if not container:
             logger.warning(f"Results container selector '{site_config.get('results_container_selector')}' not found on {search_url}")
             return results # If container not found, likely no results or wrong selector

        items = container.select(site_config['result_item_selector'])
        if not items:
            logger.warning(f"No items found using selector '{site_config['result_item_selector']}' within container on {search_url}")

        for item in items:
            title = get_attribute_or_text(item, site_config['title_selector'])
            video_url_raw = get_attribute_or_text(item, site_config['video_url_selector'], 'href')
            thumb_url_raw = get_attribute_or_text(item, site_config.get('thumbnail_selector'), 'src')
            duration_str = get_attribute_or_text(item, site_config.get('duration_selector')) # Optional
            rating_str = get_attribute_or_text(item, site_config.get('rating_selector'))  # Optional
            views_str = get_attribute_or_text(item, site_config.get('views_selector'))    # Optional
            author = get_attribute_or_text(item, site_config.get('author_selector'))  # Optional

            if title and video_url_raw: # Minimum required information
                video_url = urljoin(site_config['base_url'], video_url_raw)
                thumb_url = urljoin(site_config['base_url'], thumb_url_raw) if thumb_url_raw else ''

                # Parse duration, rating, and views
                duration_sec = parse_duration(duration_str)
                site_rating = parse_rating(rating_str)
                views = parse_views(views_str)

                results.append({
                    'title': title,
                    'url': video_url,
                    'thumbnail': thumb_url,
                    'duration_str': duration_str,
                    'duration_sec': duration_sec, # In seconds for comparison
                    'rating_str': rating_str,
                    'site_rating': site_rating,   # Normalized rating (0-1)
                    'views_str': views_str,
                    'views': views,          # Numeric views
                    'author': author,
                    'site': site_config['name'],
                    'source_method': 'scrape'
                })
            else:
                 logger.warning(f"Skipping item - missing title or URL. Check selectors for '{site_config['name']}'. Title: '{title}', URL: '{video_url_raw}' ")

        # Handle pagination if max_pages_per_site > 1
        if max_pages_per_site > 1 and page < max_pages_per_site:
            # Check for next page link
            next_page_selector = site_config.get('next_page_selector')
            if next_page_selector:
                next_page_link = get_attribute_or_text(soup, next_page_selector, 'href')
                if next_page_link:
                    next_page_url = urljoin(site_config['base_url'], next_page_link)
                    # Recursively scrape next page
                    logger.info(f"Following next page: {next_page_url}")
                    next_page_results = scrape_search_page(
                        site_config, 
                        query, 
                        page + 1, 
                        max_pages_per_site
                    )
                    results.extend(next_page_results)
                else:
                    # Try to construct next page URL if no next page link found
                    if '{page}' in site_config['search_url_template']:
                        next_page_results = scrape_search_page(
                            site_config, 
                            query, 
                            page + 1, 
                            max_pages_per_site
                        )
                        results.extend(next_page_results)

    # Proper error handling is crucial here!
    except requests.exceptions.Timeout:
        logger.error(f"Error: Timeout scraping {search_url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error scraping {search_url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scraping {site_config['name']}: {e}") # Catch other potential errors

    return results

def execute_google_search(site_name, base_url, query, api_key, cse_id):
    """ Executes a Google Custom Search for a specific site."""
    results = []
    if not GOOGLE_API_AVAILABLE or not api_key or not cse_id:
        logger.error("Error: Google API dependencies or credentials missing.")
        return results

    try:
        # Build a service object for interacting with the API. Visit
        # the Google APIs Console to create a project and API key.
        # https://cloud.google.com/docs/authentication/api-keys
        # https://developers.google.com/custom-search/v1/overview
        service = build("customsearch", "v1", developerKey=api_key)

        # Example: fetch first 10 results which is the limit per query for free tier
        search_term = f"site:{base_url} {query}" # Construct site-specific query
        logger.info(f"Google Searching: '{search_term}'")
        res = service.cse().list(
            q=search_term,
            cx=cse_id,
            num=10 # Max 10 per query
        ).execute()

        items = res.get('items', [])
        for item in items:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet') # Can use snippet for relevance boosting
            # Attempt to get thumbnail from pagemap if available
            thumbnail = None
            pagemap = item.get('pagemap', {})
            if 'cse_thumbnail' in pagemap:
                thumbnail = pagemap['cse_thumbnail'][0].get('src')
            elif 'cse_image' in pagemap:
                 thumbnail = pagemap['cse_image'][0].get('src')

            if title and link:
                 results.append({
                    'title': title,
                    'url': link,
                    'thumbnail': thumbnail  or '',  # May be null
                    'description_snippet': snippet, # Store for potential later use (relevance)
                     # Fill other fields with defaults or leave blank
                    'duration_str': None, 'duration_sec': None,
                    'rating_str': None, 'site_rating': None,
                    'views_str': None, 'views': None,
                    'author': None,
                    'site': site_name, # Associate result with original target site
                    'source_method': 'google_cse'
                })

    except Exception as e:
        logger.error(f"Error executing Google Search for site '{site_name}': {e}")
        # Common errors: Invalid API key, CSE ID, quota limit exceeded

    return results

def execute_bing_search(site_name, base_url, query, api_key):
    """ Executes a Bing Search API for a specific site."""
    results = []
    if not api_key:
        logger.error("Error: Bing API key is missing.")
        return results

    try:
        # Bing Search API endpoint
        search_url = "https://api.bing.microsoft.com/v7.0/search"

        # Construct site-specific query
        search_term = f"site:{base_url} {query}"
        
        # Set headers
        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "User-Agent": HEADERS["User-Agent"]
        }
        
        # Set parameters
        params = {
            "q": search_term,
            "count": 50,  # Request 50 results (may get fewer)
            "responseFilter": "Webpages"
        }

        logger.info(f"Bing Searching: '{search_term}'")
        response = requests.get(search_url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        
        search_data = response.json()
        
        if 'webPages' in search_data and 'value' in search_data['webPages']:
            items = search_data['webPages']['value']
            
            for item in items:
                title = item.get('name')
                link = item.get('url')
                snippet = item.get('snippet')
                
                # Bing does not provide thumbnails directly, would need to fetch from the page itself
                thumbnail = ''
                
                if title and link:
                    results.append({
                        'title': title,
                        'url': link,
                        'thumbnail': thumbnail,
                        'description_snippet': snippet,
                        'duration_str': None, 'duration_sec': None,
                        'rating_str': None, 'site_rating': None,
                        'views_str': None, 'views': None,
                        'author': None,
                        'site': site_name,
                        'source_method': 'bing_search'
                    })

    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Bing Search API: {e}")
    except Exception as e:
        logger.error(f"Error executing Bing Search for site '{site_name}': {e}")

    return results

def execute_duckduckgo_search(site_name, base_url, query, api_key=None):
    """ 
    Executes a DuckDuckGo search for a specific site.
    Note: DuckDuckGo doesn't offer an official API, so this uses their search page.
    The api_key parameter is included for consistency but not used.
    """
    results = []
    
    try:
        # DuckDuckGo search URL
        search_url = "https://duckduckgo.com/html/"
        
        # Construct site-specific query
        search_term = f"site:{base_url} {query}"
        
        # Set parameters for the search
        params = {
            "q": search_term,
            "kl": "us-en"  # Region/language setting
        }
        
        # Add random parameters to help avoid blocking
        headers = HEADERS.copy()
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        headers['Accept-Language'] = 'en-US,en;q=0.5'
        
        logger.info(f"DuckDuckGo Searching: '{search_term}'")
        
        # Add a delay to avoid rate limiting
        time.sleep(random.uniform(1.0, 3.0))
        
        # Send the request
        response = requests.post(search_url, headers=headers, data=params, timeout=20)
        response.raise_for_status()
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract search results
        result_elements = soup.select('.result')
        
        for element in result_elements:
            try:
                # Extract title and link
                title_element = element.select_one('.result__title a')
                if not title_element:
                    continue
                    
                title = title_element.get_text(strip=True)
                link = title_element.get('href')
                
                # Extract snippet
                snippet_element = element.select_one('.result__snippet')
                snippet = snippet_element.get_text(strip=True) if snippet_element else ''
                
                # DuckDuckGo search results don't include thumbnails
                thumbnail = ''
                
                if title and link:
                    # DuckDuckGo uses redirect links, we need to extract the actual URL
                    if link.startswith('/'):
                        continue  # Skip internal links
                        
                    # Handle redirects in DDG search results
                    if 'duckduckgo.com/l/' in link:
                        # Try to extract the real URL from the redirect parameter
                        import urllib.parse
                        parsed_url = urllib.parse.urlparse(link)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        if 'uddg' in query_params:
                            link = query_params['uddg'][0]
                    
                    # Skip if the link is not from the target site
                    if not link.startswith(base_url) and not f".{base_url.split('//')[1]}" in link:
                        continue
                    
                    results.append({
                        'title': title,
                        'url': link,
                        'thumbnail': thumbnail,
                        'description_snippet': snippet,
                        'duration_str': None, 'duration_sec': None,
                        'rating_str': None, 'site_rating': None,
                        'views_str': None, 'views': None,
                        'author': None,
                        'site': site_name,
                        'source_method': 'duckduckgo_search'
                    })
            except Exception as e:
                logger.warning(f"Error processing DuckDuckGo result: {e}")
                continue

    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to DuckDuckGo: {e}")
    except Exception as e:
        logger.error(f"Error executing DuckDuckGo Search for site '{site_name}': {e}")

    return results

# Placeholder for potential site-specific API integrations if they exist
def call_site_api(site_config, query):
    """ Placeholder for interacting with a site's specific API (if one exists). """
    logger.info(f"Notice: API integration for '{site_config.get('name')}' not implemented.")
    # --- Implementation would vary drastically based on the specific API ---
    # 1. Check site_config for api_endpoint, api_key (if needed)
    # 2. Construct request (GET/POST query params, headers, authentication)
    # 3. Make request using 'requests' library
    # 4. Parse JSON response (or XML)
    # 5. Map API response fields to your common result format (title, url, etc.)
    # 6. Handle API errors (rate limits, auth failures, etc.)
    return [] # Return empty list if not implemented