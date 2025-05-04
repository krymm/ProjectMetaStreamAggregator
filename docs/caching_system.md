# MetaStream Aggregator - Caching System Documentation

This document provides detailed information about the caching system used in the MetaStream Aggregator application.

## Overview

The caching system in MetaStream Aggregator temporarily stores search results to improve performance and reduce load on source sites. When a search is repeated with the same parameters, the application can retrieve results from the cache instead of performing the search again.

## How Caching Works

### Cache Keys

Each cache entry is identified by a unique key composed of:
- The search query
- The list of sites being searched
- The page number

This ensures that each unique search combination has its own cache entry.

### Cache Storage

By default, cache data is stored in the `search_cache` directory within the application folder. Each cache entry is saved as a separate JSON file, with the filename derived from the cache key.

### Cache Lifecycle

1. **Creation**: When a search is performed, results are cached if `use_cache` is set to `true`
2. **Retrieval**: When the same search is requested again, cached results are returned if available and not expired
3. **Expiration**: Cache entries expire after the time specified in `cache_expiry_minutes` (default: 10 minutes)
4. **Deletion**: Expired cache entries are automatically cleaned up periodically or can be manually cleared

## Configuration

The caching system is configured through the `settings.json` file:

```json
{
  "cache_expiry_minutes": 10,
  ...
}
```

### Available Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `cache_expiry_minutes` | How long cached results remain valid (in minutes) | 10 |

## Using the Cache

### From the User Interface

The web UI provides controls for cache management:

1. **Cache Toggle**: When performing a search, you can check/uncheck the "Use Cache" option
2. **Cache Statistics**: The UI displays current cache statistics (entries, size)
3. **Clear Cache**: Buttons are provided to clear the entire cache or just specific entries

### From the API

The search API accepts a `use_cache` parameter:

```json
{
  "query": "example search",
  "sites": ["ExampleSite1", "ExampleSite2"],
  "page": 1,
  "use_cache": true
}
```

Set `use_cache` to `false` to always perform a fresh search.

## Cache API Endpoints

The application provides several API endpoints for cache management:

### Get Cache Statistics

```
GET /api/cache/stats
```

Response:
```json
{
  "total_entries": 15,
  "active_entries": 10,
  "expired_entries": 5,
  "cache_size_kb": 256.5
}
```

### Clear All Cache

```
POST /api/cache/clear
```

Request: Empty JSON object `{}`

Response:
```json
{
  "success": true,
  "cleared_entries": 15
}
```

### Clear Specific Cache Entry

```
POST /api/cache/clear
```

Request:
```json
{
  "query": "example search",
  "sites": ["ExampleSite1", "ExampleSite2"]
}
```

Response:
```json
{
  "success": true,
  "cleared_entries": 1
}
```

## Benefits of Caching

1. **Improved Performance**: Cached searches are typically 10-100x faster than fresh searches
2. **Reduced Bandwidth**: Fewer requests to source sites
3. **Lower API Costs**: Fewer calls to paid APIs like Google CSE or Bing
4. **Reduced Risk of IP Blocking**: Fewer repeated requests to source sites

## Technical Implementation

The cache system is implemented in `cache_manager.py` with these key components:

### Cache Key Generation

```python
def generate_cache_key(query, sites, page=1):
    """Generate a unique cache key based on search parameters."""
    # Sort sites to ensure consistent keys regardless of order
    sorted_sites = sorted(sites)
    
    # Create a string representation of key components
    key_parts = [
        f"q={query.lower().strip()}",
        f"sites={'_'.join(sorted_sites)}",
        f"page={page}"
    ]
    
    # Join with delimiter and hash for filename safety
    key_str = "-".join(key_parts)
    hashed_key = hashlib.md5(key_str.encode()).hexdigest()
    
    return hashed_key
```

### Cache Entry Structure

Each cache entry contains:

```json
{
  "query": "original search query",
  "sites": ["Site1", "Site2"],
  "page": 1,
  "timestamp": 1619712584.321,
  "expires": 1619713184.321,
  "results": {
    "valid_results": [...],
    "broken_results": [...],
    "pagination": {...}
  }
}
```

### Cache Checking

```python
def get_cached_results(query, sites, page=1):
    """Retrieve results from cache if available and not expired."""
    cache_key = generate_cache_key(query, sites, page)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache has expired
        current_time = time.time()
        if current_time > cache_data.get('expires', 0):
            logger.info(f"Cache expired for query: {query}, sites: {sites}, page: {page}")
            return None
        
        logger.info(f"Cache hit for query: {query}, sites: {sites}, page: {page}")
        return cache_data.get('results')
    
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
        return None
```

## Performance Characteristics

### Memory Usage

The cache system uses file-based storage rather than in-memory storage to:
- Handle large result sets efficiently
- Persist cache between application restarts
- Avoid excessive memory usage

### Disk Space

Cache size depends on:
- Number of unique searches
- Size of search results
- Cache expiration time

Typical cache entries range from 10KB to 500KB per search, depending on the number of results.

### Cleanup Process

The application periodically cleans up expired cache entries to prevent disk space issues:

```python
def cleanup_expired_cache():
    """Remove expired cache entries from disk."""
    current_time = time.time()
    removed_count = 0
    
    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith('.json'):
            continue
            
        cache_file = os.path.join(CACHE_DIR, filename)
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache has expired
            if current_time > cache_data.get('expires', 0):
                os.remove(cache_file)
                removed_count += 1
                
        except Exception as e:
            logger.error(f"Error cleaning up cache file {filename}: {e}")
    
    return removed_count
```

## Best Practices

### When to Use Caching

- **Enable caching** for:
  - Common searches that are performed repeatedly
  - Searches across multiple sites
  - Development and testing
  
- **Disable caching** for:
  - Searches where fresh results are critical
  - When troubleshooting site configuration issues

### Optimizing Cache Performance

1. **Tune expiry time**: Adjust `cache_expiry_minutes` based on how frequently site content changes
2. **Clear selectively**: Use specific cache clearing rather than clearing all cache
3. **Monitor disk usage**: Check cache size periodically if running the application for extended periods

## Troubleshooting

### Cache Not Working

- Check if `use_cache` is set to `true` in your search requests
- Verify that the `cache_expiry_minutes` value is reasonable (not too short)
- Ensure the application has write permissions to the `search_cache` directory

### Cache Files Corrupted

If cache files become corrupted, you can:
1. Clear all cache through the UI
2. Manually delete all files in the `search_cache` directory
3. Restart the application

### Excessive Disk Usage

If the cache is consuming too much disk space:
1. Reduce the `cache_expiry_minutes` setting
2. Clear the cache more frequently
3. Implement a maximum cache size limit (requires code modification)