# link_checker.py
import requests
import concurrent.futures
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use same headers as scraper possibly
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_single_link(result_item):
    """ Checks the validity of a single video URL using HEAD request with fallback to GET. """
    url = result_item.get('url')
    if not url:
        logger.warning(f"Skipping check for item with no URL: {result_item.get('title')}")
        return result_item, False # Invalid if no URL

    # First try with HEAD request (faster, less bandwidth)
    try:
        # Timeout is crucial here, default can be long
        response = requests.head(url, headers=HEADERS, timeout=8, allow_redirects=True)
        
        # Check for success status codes (2xx or sometimes 3xx if followed)
        if 200 <= response.status_code < 400:
            # Check content-type if header is present
            cont_type = response.headers.get('Content-Type','').lower()
            if 'video' in cont_type or 'html' in cont_type or 'application' in cont_type:
                logger.debug(f"Link valid (HEAD): {url}")
                return result_item, True
            else:
                logger.warning(f"Link has non-video/html Content-Type: '{cont_type}', falling back to GET: {url}")
                # Fall back to GET request for additional verification
                return fallback_get_request(url, result_item)
        
        elif response.status_code in (403, 405):  # Forbidden or Method Not Allowed
            logger.warning(f"HEAD request blocked for {url}, falling back to GET")
            return fallback_get_request(url, result_item)
        
        else:
            logger.warning(f"Link check failed (HEAD): {url} (Status: {response.status_code})")
            return result_item, False

    except requests.exceptions.Timeout:
        logger.warning(f"Link check timeout (HEAD): {url}, falling back to GET")
        return fallback_get_request(url, result_item)
    
    except requests.exceptions.RequestException as e:
        # For connection errors, redirects that fail, etc., try GET as fallback
        logger.warning(f"Link check error (HEAD): {url} ({e}), falling back to GET")
        return fallback_get_request(url, result_item)

def fallback_get_request(url, result_item):
    """
    Perform a GET request with stream=True as a fallback when HEAD fails.
    This avoids downloading the full content of the page.
    """
    try:
        # Use stream=True to avoid downloading the entire content
        response = requests.get(
            url, 
            headers=HEADERS, 
            timeout=10, 
            stream=True, 
            allow_redirects=True
        )
        
        # Close the connection immediately to avoid downloading content
        response.close()
        
        if 200 <= response.status_code < 400:
            logger.debug(f"Link valid (GET fallback): {url}")
            return result_item, True
        else:
            logger.warning(f"Link check failed (GET fallback): {url} (Status: {response.status_code})")
            return result_item, False
    
    except Exception as e:
        logger.warning(f"Link check error (GET fallback): {url} ({e})")
        return result_item, False

def check_links_concurrently(results_list):
    """ Checks link validity for a list of results using concurrent threads. """
    valid_results = []
    broken_results = []
    
    if not results_list:
        logger.info("No results to check links for")
        return valid_results, broken_results

    # Use ThreadPoolExecutor for I/O-bound tasks like network requests
    # Adjust max_workers based on your system and network limits
    max_workers = min(20, len(results_list))  # Cap at 20 workers
    
    logger.info(f"Checking {len(results_list)} links with {max_workers} workers")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all checks to the executor
        future_to_result = {executor.submit(check_single_link, item): item for item in results_list}

        for future in concurrent.futures.as_completed(future_to_result):
            original_item = future_to_result[future]
            try:
                result_item, is_valid = future.result()
                if is_valid:
                    valid_results.append(result_item)
                else:
                    broken_results.append(result_item)
            except Exception as exc:
                logger.error(f'Link check generated an exception for {original_item.get("url")}: {exc}')
                broken_results.append(original_item) # Treat exceptions as broken links

    logger.info(f"Link checking complete: {len(valid_results)} valid, {len(broken_results)} broken")
    
    # Make sure the valid results remain sorted by score
    valid_results.sort(key=lambda x: x.get('calc_score', 0), reverse=True)

    return valid_results, broken_results