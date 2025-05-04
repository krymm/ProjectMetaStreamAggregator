# cache_manager.py
import time
import json
import hashlib
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchCache:
    """Simple time-based caching system for search results."""
    
    def __init__(self, cache_dir='cache', expiry_minutes=10):
        """Initialize the cache with a directory and expiry time.
        
        Args:
            cache_dir (str): Directory to store cache files
            expiry_minutes (int): Cache expiry time in minutes
        """
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), cache_dir)
        self.expiry_seconds = expiry_minutes * 60
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
                logger.info(f"Created cache directory: {self.cache_dir}")
            except Exception as e:
                logger.error(f"Error creating cache directory: {e}")
    
    def _get_cache_key(self, query, sites, page=1):
        """Generate a unique cache key based on query parameters.
        
        Args:
            query (str): Search query
            sites (list): List of site names to search
            page (int): Result page number
            
        Returns:
            str: MD5 hash to use as cache key
        """
        # Sort sites to ensure consistent keys regardless of order
        sorted_sites = sorted(sites)
        # Create a string representation of the search parameters
        key_data = f"{query}|{','.join(sorted_sites)}|{page}"
        # Generate an MD5 hash
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, cache_key):
        """Get full path to the cache file for a given key.
        
        Args:
            cache_key (str): Cache key (MD5 hash)
            
        Returns:
            str: Full file path
        """
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def get(self, query, sites, page=1):
        """Retrieve cached search results if available and not expired.
        
        Args:
            query (str): Search query
            sites (list): List of site names to search
            page (int): Result page number
            
        Returns:
            dict or None: Cached search results or None if not found/expired
        """
        cache_key = self._get_cache_key(query, sites, page)
        cache_path = self._get_cache_path(cache_key)
        
        # Check if cache file exists
        if not os.path.exists(cache_path):
            return None
        
        try:
            # Read the cache file
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache has expired
            cache_time = cache_data.get('cache_time', 0)
            current_time = time.time()
            
            if current_time - cache_time > self.expiry_seconds:
                logger.info(f"Cache expired for query: {query}, sites: {sites}, page: {page}")
                return None
            
            # Log cache hit
            logger.info(f"Cache hit for query: {query}, sites: {sites}, page: {page}")
            return cache_data.get('results')
            
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None
    
    def set(self, query, sites, page, results):
        """Save search results to cache.
        
        Args:
            query (str): Search query
            sites (list): List of site names to search
            page (int): Result page number
            results (dict): Search results to cache
        """
        cache_key = self._get_cache_key(query, sites, page)
        cache_path = self._get_cache_path(cache_key)
        
        # Add caching metadata
        cache_data = {
            'cache_time': time.time(),
            'query': query,
            'sites': sites,
            'page': page,
            'cached_at': datetime.now().isoformat(),
            'results': results
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            logger.info(f"Cached results for query: {query}, sites: {sites}, page: {page}")
        except Exception as e:
            logger.error(f"Error writing to cache: {e}")
    
    def clear(self, query=None, sites=None):
        """Clear specific cache entries or all cache if no parameters provided.
        
        Args:
            query (str, optional): Search query to clear
            sites (list, optional): List of site names to clear
        """
        if query is None and sites is None:
            # Clear all cache
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, filename))
                logger.info("Cleared all cache entries")
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
        else:
            # Clear specific cache entries
            if query and sites:
                cache_key = self._get_cache_key(query, sites)
                cache_path = self._get_cache_path(cache_key)
                if os.path.exists(cache_path):
                    try:
                        os.remove(cache_path)
                        logger.info(f"Cleared cache for query: {query}, sites: {sites}")
                    except Exception as e:
                        logger.error(f"Error clearing specific cache: {e}")
    
    def get_stats(self):
        """Get statistics about the current cache state.
        
        Returns:
            dict: Cache statistics
        """
        stats = {
            'total_entries': 0,
            'expired_entries': 0,
            'active_entries': 0,
            'cache_size_bytes': 0
        }
        
        try:
            current_time = time.time()
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    stats['total_entries'] += 1
                    stats['cache_size_bytes'] += os.path.getsize(file_path)
                    
                    # Check if entry is expired
                    try:
                        with open(file_path, 'r') as f:
                            cache_data = json.load(f)
                        cache_time = cache_data.get('cache_time', 0)
                        
                        if current_time - cache_time > self.expiry_seconds:
                            stats['expired_entries'] += 1
                        else:
                            stats['active_entries'] +=.1
                    except:
                        # Count as expired if can't read
                        stats['expired_entries'] += 1
            
            # Convert to KB for easier reading
            stats['cache_size_kb'] = round(stats['cache_size_bytes'] / 1024, 2)
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
        
        return stats