# site_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import random
import re
import logging
from urllib.parse import urljoin, quote_plus, urlparse

# Import for fetching site configurations
from config_manager import load_sites_config

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


def fetch_extended_details(item_url, site_config_for_item_page, source_site_name):
    """
    Fetches extended details (duration, rating, views, author) from a specific item URL.

    Args:
        item_url (str): The URL of the page to scrape.
        site_config_for_item_page (dict): The site configuration containing selectors for the item_url's domain.
        source_site_name (str): The name of the site that originally provided this URL (e.g., Google, Bing).

    Returns:
        dict: A dictionary with 'duration_sec', 'site_rating', 'views', 'author'.
              Values are None if not found or if an error occurs.
    """
    details = {
        'duration_str': None, 'duration_sec': None,
        'rating_str': None, 'site_rating': None,
        'views_str': None, 'views': None,
        'author': None
    }

    if not site_config_for_item_page:
        logger.debug(f"No site_config provided for {item_url}, cannot fetch extended details.")
        return details

    # Ensure selectors exist in the provided config
    duration_selector = site_config_for_item_page.get('duration_selector')
    rating_selector = site_config_for_item_page.get('rating_selector')
    views_selector = site_config_for_item_page.get('views_selector')
    author_selector = site_config_for_item_page.get('author_selector')

    if not any([duration_selector, rating_selector, views_selector, author_selector]):
        logger.debug(f"No relevant selectors found in site_config for {site_config_for_item_page.get('name', 'unknown config')} when fetching details for {item_url}")
        return details

    logger.info(f"Fetching extended details for: {item_url} (source: {source_site_name}, using config: {site_config_for_item_page.get('name')})")

    try:
        time.sleep(random.uniform(0.5, 1.5)) # Basic politeness delay
        response = requests.get(item_url, headers=HEADERS, timeout=15) # Shorter timeout for individual pages
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # No need to select a container, selectors should be for the whole page
        # or relative to a known structure if site_config is specific enough.

        if duration_selector:
            duration_str = get_attribute_or_text(soup, duration_selector)
            if duration_str:
                details['duration_str'] = duration_str
                details['duration_sec'] = parse_duration(duration_str)

        if rating_selector:
            rating_str = get_attribute_or_text(soup, rating_selector)
            if rating_str:
                details['rating_str'] = rating_str
                details['site_rating'] = parse_rating(rating_str)

        if views_selector:
            views_str = get_attribute_or_text(soup, views_selector)
            if views_str:
                details['views_str'] = views_str
                details['views'] = parse_views(views_str)

        if author_selector:
            author = get_attribute_or_text(soup, author_selector)
            if author:
                details['author'] = author

        logger.debug(f"Fetched details for {item_url}: {details}")

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching extended details from {item_url} (source: {source_site_name})")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error fetching extended details from {item_url} (source: {source_site_name}): {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching extended details from {item_url} (source: {source_site_name}): {e}")
        # Optionally, re-raise if debugging is needed for unexpected parsing errors
        # raise

    return details


def execute_google_search(site_name, base_url, query, api_key, cse_id):
    """ Executes a Google Custom Search for a specific site."""
    results = []
    if not GOOGLE_API_AVAILABLE or not api_key or not cse_id:
        logger.error("Error: Google API dependencies or credentials missing for Google Search.")
        return results

    # Load all site configurations to find matching selectors for result URLs
    all_site_configs = load_sites_config()

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        # Using the passed 'base_url' to restrict search, along with the query
        # This 'base_url' is the URL of the site we want to search *on* using Google.
        search_term = f"site:{base_url} {query}"
        logger.info(f"Google Searching on '{base_url}' for query '{query}' (Original site context: '{site_name}')")

        res = service.cse().list(q=search_term, cx=cse_id, num=10).execute() # Max 10 per query
        raw_items = res.get('items', [])

        for item in raw_items:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet')
            thumbnail = None
            pagemap = item.get('pagemap', {})
            if 'cse_thumbnail' in pagemap:
                thumbnail = pagemap['cse_thumbnail'][0].get('src')
            elif 'cse_image' in pagemap:
                thumbnail = pagemap['cse_image'][0].get('src')

            if title and link:
                # Determine if this link belongs to a configured site to fetch extended details
                item_domain = urlparse(link).netloc
                site_config_for_item_page = None
                for config_name, s_config in all_site_configs.items():
                    # Ensure s_config['base_url'] has a domain part for comparison
                    config_base_url_parsed = urlparse(s_config.get('base_url', ''))
                    if config_base_url_parsed.netloc and config_base_url_parsed.netloc in item_domain:
                        site_config_for_item_page = s_config
                        logger.debug(f"Found matching config '{s_config.get('name')}' for URL '{link}' based on domain '{item_domain}'")
                        break

                extended_details = {}
                if site_config_for_item_page:
                    # Fetch extended details ONLY if the result URL is from a known site with selectors
                    if link.startswith(site_config_for_item_page.get('base_url', '')):
                        extended_details = fetch_extended_details(link, site_config_for_item_page, "Google CSE")
                    else:
                        logger.debug(f"URL '{link}' domain matches '{site_config_for_item_page.get('name')}' but base_url does not. Skipping extended details.")
                else:
                    # This occurs if the search result (link) is not for a site defined in our sites.json
                    # or if the site it belongs to doesn't have detailed selectors.
                    logger.debug(f"No specific site_config found for URL '{link}' (domain: {item_domain}). Cannot fetch extended details.")

                results.append({
                    'title': title,
                    'url': link,
                    'thumbnail': thumbnail or '',
                    'description_snippet': snippet,
                    'duration_str': extended_details.get('duration_str'),
                    'duration_sec': extended_details.get('duration_sec'),
                    'rating_str': extended_details.get('rating_str'),
                    'site_rating': extended_details.get('site_rating'),
                    'views_str': extended_details.get('views_str'),
                    'views': extended_details.get('views'),
                    'author': extended_details.get('author'),
                    # 'site' should be the name of the site where the content was found,
                    # which might be different from 'site_name' if Google returns a result from another site.
                    # For now, we use the matched site_config's name or fall back to site_name.
                    'site': site_config_for_item_page.get('name') if site_config_for_item_page else site_name,
                    'source_method': 'google_cse'
                })
            else:
                logger.warning(f"Skipping Google CSE item - missing title or link. Item: {str(item)[:100]}")


    except Exception as e:
        logger.error(f"Error executing Google Search for site '{site_name}' (targeting base_url '{base_url}'): {e}")

    return results

def execute_bing_search(site_name, base_url, query, api_key):
    """ Executes a Bing Search API for a specific site."""
    results = []
    if not api_key:
        logger.error("Error: Bing API key is missing for Bing Search.")
        return results

    all_site_configs = load_sites_config()

    try:
        search_url = "https://api.bing.microsoft.com/v7.0/search"
        search_term = f"site:{base_url} {query}" # Target search within the specified base_url
        
        request_headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "User-Agent": HEADERS["User-Agent"]
        }
        params = {"q": search_term, "count": 50, "responseFilter": "Webpages"}

        logger.info(f"Bing Searching on '{base_url}' for query '{query}' (Original site context: '{site_name}')")
        response = requests.get(search_url, headers=request_headers, params=params, timeout=20)
        response.raise_for_status()
        
        search_data = response.json()
        
        if 'webPages' in search_data and 'value' in search_data['webPages']:
            raw_items = search_data['webPages']['value']
            
            for item in raw_items:
                title = item.get('name')
                link = item.get('url')
                snippet = item.get('snippet')
                # Bing API does not provide thumbnails directly in the main response.
                # Some results might have 'deepLinks' or other structures that could hint at images,
                # but it's not as direct as Google's pagemap.
                thumbnail = item.get('thumbnailUrl') # Check if BCP API ever returns this (unlikely for generic web search)

                if title and link:
                    item_domain = urlparse(link).netloc
                    site_config_for_item_page = None
                    for config_name, s_config in all_site_configs.items():
                        config_base_url_parsed = urlparse(s_config.get('base_url', ''))
                        if config_base_url_parsed.netloc and config_base_url_parsed.netloc in item_domain:
                            site_config_for_item_page = s_config
                            logger.debug(f"Found matching config '{s_config.get('name')}' for URL '{link}' (Bing result)")
                            break

                    extended_details = {}
                    if site_config_for_item_page:
                        if link.startswith(site_config_for_item_page.get('base_url', '')):
                             extended_details = fetch_extended_details(link, site_config_for_item_page, "Bing Search")
                        else:
                            logger.debug(f"URL '{link}' domain matches '{site_config_for_item_page.get('name')}' but base_url does not. Skipping extended details.")
                    else:
                        logger.debug(f"No specific site_config found for Bing result URL '{link}'. Cannot fetch extended details.")

                    results.append({
                        'title': title,
                        'url': link,
                        'thumbnail': thumbnail or '', # Use if available, else empty
                        'description_snippet': snippet,
                        'duration_str': extended_details.get('duration_str'),
                        'duration_sec': extended_details.get('duration_sec'),
                        'rating_str': extended_details.get('rating_str'),
                        'site_rating': extended_details.get('site_rating'),
                        'views_str': extended_details.get('views_str'),
                        'views': extended_details.get('views'),
                        'author': extended_details.get('author'),
                        'site': site_config_for_item_page.get('name') if site_config_for_item_page else site_name,
                        'source_method': 'bing_search'
                    })
                else:
                    logger.warning(f"Skipping Bing Search item - missing title or link. Item: {str(item)[:100]}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Bing Search API for site '{site_name}': {e}")
    except Exception as e:
        logger.error(f"Error executing Bing Search for site '{site_name}' (targeting base_url '{base_url}'): {e}")

    return results

def execute_duckduckgo_search(site_name, base_url, query, api_key=None):
    """ 
    Executes a DuckDuckGo search for a specific site.
    Note: DuckDuckGo doesn't offer an official API, so this uses their HTML search page.
    The api_key parameter is for consistency but not used by DDG.
    """
    results = []
    all_site_configs = load_sites_config()
    
    try:
        search_ddg_url = "https://html.duckduckgo.com/html/" # Use the HTML version
        # search_ddg_url = "https://duckduckgo.com/" # Standard version, might be more fragile
        
        search_term = f"site:{base_url} {query}"
        
        request_params = {"q": search_term, "kl": "us-en"} # Region/language
        request_headers = HEADERS.copy()
        # DDG can be sensitive to headers, mimic a common browser
        request_headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://duckduckgo.com/'
        })
        
        logger.info(f"DuckDuckGo Searching on '{base_url}' for query '{query}' (Original site context: '{site_name}')")
        time.sleep(random.uniform(1.0, 3.0)) # DDG can be quick to block scrapers
        
        # DDG uses POST for html endpoint sometimes, or GET for main
        # Using GET for html endpoint as it's simpler and often works.
        # response = requests.post(search_ddg_url, headers=request_headers, data=request_params, timeout=20)
        response = requests.get(search_ddg_url, headers=request_headers, params=request_params, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # DDG selectors can change, these are common for the HTML version
        # result_elements = soup.select('div.results > div.result') # More specific path
        result_elements = soup.select('div.web-result') # Common as of late 2023/early 2024 for html version

        if not result_elements: # Fallback for older structure or changes
            result_elements = soup.select('.result')

        for element in result_elements:
            try:
                title_element = element.select_one('.result__title a, .web-result-title a')
                link_element = title_element # Link is usually the same element
                snippet_element = element.select_one('.result__snippet, .web-result-snippet')

                if not title_element or not link_element:
                    logger.debug("DDG item skipped: missing title or link element.")
                    continue
                    
                title = title_element.get_text(strip=True)
                raw_link = link_element.get('href')
                
                if not raw_link:
                    logger.debug(f"DDG item '{title}' skipped: missing href in link element.")
                    continue

                # Handle DDG's redirect links (if any, html version tends to have direct links)
                link = raw_link
                if 'duckduckgo.com/l/' in raw_link:
                    parsed_ddg_url = urlparse(raw_link)
                    query_params = urllib.parse.parse_qs(parsed_ddg_url.query)
                    if 'uddg' in query_params and query_params['uddg'][0]:
                        link = query_params['uddg'][0]
                    else:
                        logger.warning(f"Could not extract final URL from DDG redirect: {raw_link}")
                        # continue # Or try to use the raw_link if it seems plausible

                snippet = snippet_element.get_text(strip=True) if snippet_element else ''
                thumbnail = '' # DDG HTML search doesn't provide thumbnails

                # Filter: Ensure the link is actually from the target site (base_url)
                # This is crucial because DDG's "site:" operator can sometimes be leaky.
                parsed_link_domain = urlparse(link).netloc
                parsed_base_url_domain = urlparse(base_url).netloc
                if not parsed_link_domain or parsed_base_url_domain not in parsed_link_domain :
                    logger.debug(f"DDG result '{title}' ({link}) skipped: domain '{parsed_link_domain}' not within target site '{parsed_base_url_domain}'.")
                    continue
                
                if title and link:
                    item_domain = urlparse(link).netloc # Re-parse for safety after potential rewrite
                    site_config_for_item_page = None
                    for config_name, s_config in all_site_configs.items():
                        config_base_url_parsed = urlparse(s_config.get('base_url', ''))
                        if config_base_url_parsed.netloc and config_base_url_parsed.netloc in item_domain:
                            site_config_for_item_page = s_config
                            logger.debug(f"Found matching config '{s_config.get('name')}' for URL '{link}' (DDG result)")
                            break
                    
                    extended_details = {}
                    if site_config_for_item_page:
                        if link.startswith(site_config_for_item_page.get('base_url', '')):
                            extended_details = fetch_extended_details(link, site_config_for_item_page, "DuckDuckGo Search")
                        else:
                            logger.debug(f"URL '{link}' domain matches '{site_config_for_item_page.get('name')}' but base_url does not. Skipping extended details.")
                    else:
                        logger.debug(f"No specific site_config found for DDG result URL '{link}'. Cannot fetch extended details.")

                    results.append({
                        'title': title,
                        'url': link,
                        'thumbnail': thumbnail,
                        'description_snippet': snippet,
                        'duration_str': extended_details.get('duration_str'),
                        'duration_sec': extended_details.get('duration_sec'),
                        'rating_str': extended_details.get('rating_str'),
                        'site_rating': extended_details.get('site_rating'),
                        'views_str': extended_details.get('views_str'),
                        'views': extended_details.get('views'),
                        'author': extended_details.get('author'),
                        'site': site_config_for_item_page.get('name') if site_config_for_item_page else site_name,
                        'source_method': 'duckduckgo_search'
                    })
                else: # Should be caught by earlier checks
                    logger.warning(f"Skipping DDG item - missing title or link. Item content: {element.get_text()[:100]}")

            except Exception as e: # Catch errors processing a single DDG result item
                logger.warning(f"Error processing a DuckDuckGo result item: {e}. Item: {element.get_text()[:100]}")
                continue

    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to DuckDuckGo for site '{site_name}': {e}")
    except Exception as e: # Catch broader errors like parsing the whole page
        logger.error(f"Error executing DuckDuckGo Search for site '{site_name}' (targeting base_url '{base_url}'): {e}")

    return results

def call_site_api(site_config, query):
    """
    Generic handler for sites that use an API for searching.
    Logs a warning and returns an empty list as specific API implementation is needed.
    """
    site_name = site_config.get('name', 'Unknown Site')
    logger.warning(
        f"API search for '{site_name}' using generic handler. "
        f"Site-specific implementation in 'call_site_api' is required for proper results. "
        f"Attempting a best-effort generic API call."
    )

    results = []

    # --- 1. Check site_config for essential API details ---
    api_url_template = site_config.get('api_url_template')
    api_key = site_config.get('api_key')  # Optional, depending on API
    api_key_param = site_config.get('api_key_param') # Optional, param name for API key

    if not api_url_template:
        logger.error(f"API configuration error for '{site_name}': 'api_url_template' is missing.")
        return results # Return empty list

    # --- 2. Construct request ---
    # Replace placeholders in the URL template
    # Common placeholders: {query}, {api_key} (if api_key_param is not used directly in headers)
    # More complex placeholder replacement might be needed for specific APIs
    try:
        search_url = api_url_template.format(query=quote_plus(query), api_key=api_key or '')
    except KeyError as e:
        logger.error(f"Missing placeholder {e} in 'api_url_template' for '{site_name}'. Query: {query}")
        return results

    # Prepare headers - some APIs require the key in headers
    request_headers = HEADERS.copy()
    if api_key and api_key_param and api_key_param.lower() != 'url': # if api_key_param is not 'url', assume header
        request_headers[api_key_param] = api_key
    elif api_key and not api_key_param: # Default to a common header if param name not specified
        request_headers['Authorization'] = f"Bearer {api_key}"


    # --- 3. Make request using 'requests' library ---
    logger.info(f"Calling API for '{site_name}': {search_url}")
    try:
        time.sleep(random.uniform(0.5, 1.5)) # Politeness delay
        response = requests.get(search_url, headers=request_headers, timeout=20)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # --- 4. Parse JSON response (assuming JSON) ---
        try:
            api_data = response.json()
        except ValueError: # Includes JSONDecodeError
            logger.error(f"Failed to parse JSON response from '{site_name}' API: {response.text[:200]}")
            return results # Return empty if parsing fails

        # --- 5. Map API response fields to your common result format ---
        # This is a best-effort generic mapping. Users MUST customize this per API.
        # Common patterns: items in a list, often under a key like 'items', 'results', 'data'

        # Try to find a list of items in the response
        possible_item_keys = ['items', 'results', 'data', 'videos', 'entries', 'hits']
        item_list = None
        if isinstance(api_data, list):
            item_list = api_data
        elif isinstance(api_data, dict):
            for key in possible_item_keys:
                if key in api_data and isinstance(api_data[key], list):
                    item_list = api_data[key]
                    break
            if not item_list: # If no common key found, try to grab the first list found in the dict values
                for value in api_data.values():
                    if isinstance(value, list):
                        item_list = value
                        logger.warning(f"Found item list under an unexpected key for '{site_name}'. Please verify mapping.")
                        break

        if not item_list:
            logger.warning(f"Could not find a list of items in API response from '{site_name}'. Response: {str(api_data)[:200]}")
            return results

        for item in item_list:
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dictionary item in API response from '{site_name}': {str(item)[:100]}")
                continue

            # Best-effort mapping (these will likely need to be adjusted per site)
            # Users will configure these mappings in sites.json via e.g., "api_title_field": "video.title"
            title = item.get(site_config.get('api_title_field', 'title')) or \
                    item.get('name') or \
                    item.get('video_title')

            url = item.get(site_config.get('api_url_field', 'url')) or \
                  item.get('link') or \
                  item.get('video_url')

            thumbnail = item.get(site_config.get('api_thumbnail_field', 'thumbnail')) or \
                        item.get('thumbnail_url') or \
                        item.get('image') or \
                        item.get('preview_image')

            duration_str = str(item.get(site_config.get('api_duration_field', 'duration'), ''))
            rating_str = str(item.get(site_config.get('api_rating_field', 'rating'), ''))
            views_str = str(item.get(site_config.get('api_views_field', 'views'), ''))
            author = item.get(site_config.get('api_author_field', 'author')) or \
                     item.get('uploader') or \
                     item.get('channel_name')

            if not title or not url:
                logger.warning(f"Skipping API item from '{site_name}' due to missing title or URL. Item: {str(item)[:100]}")
                continue

            # Ensure URL is absolute
            if isinstance(url, str) and not url.startswith(('http://', 'https://')):
                url = urljoin(site_config.get('base_url', ''), url)
            if isinstance(thumbnail, str) and not thumbnail.startswith(('http://', 'https://')):
                thumbnail = urljoin(site_config.get('base_url', ''), thumbnail)


            results.append({
                'title': title,
                'url': url,
                'thumbnail': thumbnail or '',
                'duration_str': duration_str,
                'duration_sec': parse_duration(duration_str),
                'rating_str': rating_str,
                'site_rating': parse_rating(rating_str),
                'views_str': views_str,
                'views': parse_views(views_str),
                'author': author or '',
                'site': site_name,
                'source_method': 'api'
            })

    except requests.exceptions.Timeout:
        logger.error(f"API request timeout for '{site_name}': {search_url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error for '{site_name}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error during API call for '{site_name}': {e}")

    if not results:
        logger.info(f"No results processed from API for '{site_name}' with query '{query}'. This may be due to missing site-specific field mappings in config or an empty API response.")

    return results