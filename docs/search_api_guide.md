# MetaStream Aggregator - Search API Options Guide

This document provides detailed information about the different search API options available in the MetaStream Aggregator application and how to configure them.

## Overview

MetaStream Aggregator supports multiple search methods to gather content from various sources:

1. **Direct Scraping**: Directly accessing and parsing search results pages
2. **Google Custom Search**: Using Google's Custom Search Engine API
3. **Bing Search**: Using Microsoft's Bing Search API
4. **DuckDuckGo Search**: Using DuckDuckGo's search capabilities

Each method has advantages and disadvantages in terms of setup complexity, cost, and effectiveness.

## Comparison of Search Methods

| Search Method | Setup Complexity | Cost | Rate Limits | Result Quality | Best For |
|---------------|------------------|------|-------------|----------------|----------|
| Direct Scraping | High | Free | Site-dependent | High | Sites with stable, simple HTML structure |
| Google CSE | Medium | Paid (1000 free queries/day) | 100 queries/second | High | Most sites, especially complex ones |
| Bing Search | Medium | Paid (free tier available) | Tier-dependent | High | Most sites, good alternative to Google |
| DuckDuckGo | Low | Free | Unofficial API limits | Medium | Basic searches on supported sites |

## 1. Direct Scraping

### How It Works

Direct scraping involves:
1. Constructing a search URL for the target site
2. Requesting the page HTML
3. Parsing the HTML using CSS selectors to extract information

### Configuration

In `sites.json`, use the following configuration:

```json
"ExampleSite": {
  "name": "ExampleSite",
  "base_url": "https://www.example.com",
  "search_method": "scrape_search_page",
  "search_url_template": "https://www.example.com/search?q={query}&page={page}",
  "results_container_selector": "div.search-results",
  "result_item_selector": "div.video-item",
  "title_selector": "h3.title",
  "video_url_selector": "a.video-link[href]",
  "thumbnail_selector": "img.thumb[src]",
  "duration_selector": "span.duration",
  "rating_selector": "div.rating",
  "views_selector": "span.views",
  "next_page_selector": "a.next-page[href]",
  "popularity_multiplier": 1.0
}
```

### Advantages

- No API keys required
- No query limits (except those imposed by the site)
- Full control over parsing

### Disadvantages

- Site structure can change, breaking selectors
- Some sites use complex JavaScript to render content, making scraping difficult
- Some sites implement anti-scraping measures
- Requires detailed knowledge of site HTML structure

### Tips for Direct Scraping

1. Test your selectors using browser developer tools first
2. Add proper headers to mimic a real browser:
   ```python
   headers = {
       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
       'Accept-Language': 'en-US,en;q=0.9',
       'Referer': 'https://www.example.com/'
   }
   ```
3. Implement rate limiting to avoid IP bans
4. Consider using a rotation of proxies for high-volume scraping

## 2. Google Custom Search

### How It Works

Google Custom Search Engine (CSE) allows you to:
1. Create a custom search engine targeting specific sites
2. Query it using Google's API
3. Get structured results including titles, URLs, and snippets

### Configuration

First, set up the API:
1. Create a [Google Cloud](https://console.cloud.google.com/) account
2. Enable the Custom Search API
3. Create API credentials to get your API key
4. Go to the [Programmable Search Engine](https://programmablesearchengine.google.com/about/) site
5. Create a search engine and get your CSE ID
6. Add your target sites to the search engine

In `settings.json`, add your credentials:

```json
{
  "google_api_key": "YOUR_API_KEY",
  "google_search_engine_id": "YOUR_CSE_ID",
  ...
}
```

In `sites.json`, configure sites to use Google search:

```json
"GoogleSearchExample": {
  "name": "GoogleSearchExample",
  "base_url": "https://www.example.com",
  "search_method": "google_site_search",
  "site_restriction": "example.com",
  "popularity_multiplier": 0.8
}
```

### Advantages

- High-quality results
- Works well with sites that use complex JavaScript
- Structured data with consistent format
- Handles pagination automatically

### Disadvantages

- Limited free quota (1,000 queries per day)
- Paid beyond that ($5 per 1,000 queries)
- May not index all content on some sites
- Limited to 10 results per query (can use pagination for more)

### API Quotas and Pricing

- **Free tier**: 100 search queries per day
- **Paid tier**: $5 per 1,000 queries
- **Maximum**: 10,000 queries per day

## 3. Bing Search API

### How It Works

Microsoft's Bing Search API allows you to:
1. Query Bing's index with site-specific restrictions
2. Receive structured results with titles, URLs, and descriptions

### Configuration

First, set up the API:
1. Create a [Microsoft Azure](https://portal.azure.com/) account
2. Subscribe to Bing Search API v7
3. Create a resource and get your API key

In `settings.json`, add your credentials:

```json
{
  "bing_api_key": "YOUR_BING_API_KEY",
  ...
}
```

In `sites.json`, configure sites to use Bing search:

```json
"BingSearchExample": {
  "name": "BingSearchExample",
  "base_url": "https://www.example.com",
  "search_method": "bing_search",
  "site_restriction": "example.com",
  "popularity_multiplier": 0.9
}
```

### Advantages

- High-quality results
- Good alternative to Google
- More flexible pricing tiers
- Can return up to 50 results per query

### Disadvantages

- Requires credit card for Azure account
- May not have as comprehensive indexing as Google for some sites
- Results format differs from Google

### API Quotas and Pricing

- **Free tier**: 1,000 transactions per month (3 transactions per second)
- **Basic tier**: Starting at $3 per 1,000 transactions
- **Standard tier**: Starting at $3 per 1,000 transactions with higher rate limits

## 4. DuckDuckGo Search

### How It Works

DuckDuckGo doesn't offer an official API, but MetaStream uses unofficial methods to:
1. Query DuckDuckGo with site-specific restrictions
2. Parse the results to extract titles, URLs, and descriptions

### Configuration

In `sites.json`, configure sites to use DuckDuckGo search:

```json
"DuckDuckGoExample": {
  "name": "DuckDuckGoExample",
  "base_url": "https://www.example.com",
  "search_method": "duckduckgo_search",
  "site_restriction": "example.com",
  "popularity_multiplier": 1.2
}
```

No API key is required for the basic implementation.

### Advantages

- Free to use
- No API keys required
- No strict rate limiting
- Privacy-focused

### Disadvantages

- Unofficial API may break with DuckDuckGo updates
- Less comprehensive indexing than Google or Bing for some sites
- Rate limiting may be applied after excessive use
- Limited advanced search features

## Implementing Multiple Search Methods

For best results, consider implementing a combination of search methods:

1. **Primary**: Use direct scraping for sites with simple, stable HTML structure
2. **Secondary**: Use Google CSE or Bing for sites with complex JavaScript or anti-scraping measures
3. **Fallback**: Use DuckDuckGo when API quotas for Google/Bing are exhausted

### Example Multi-Method Configuration

In `sites.json`:

```json
{
  "Site1Direct": {
    "name": "Site1Direct",
    "search_method": "scrape_search_page",
    ...
  },
  "Site1Google": {
    "name": "Site1Google",
    "search_method": "google_site_search",
    "site_restriction": "site1.com",
    ...
  },
  "Site2Bing": {
    "name": "Site2Bing",
    "search_method": "bing_search",
    "site_restriction": "site2.com",
    ...
  },
  "Site3DDG": {
    "name": "Site3DDG",
    "search_method": "duckduckgo_search",
    "site_restriction": "site3.com",
    ...
  }
}
```

## Troubleshooting Search API Issues

### Google CSE Issues

- **403 Forbidden**: Check your API key and ensure billing is enabled
- **Quota exceeded**: Check your usage in Google Cloud Console
- **Invalid CSE ID**: Verify your Search Engine ID in Programmable Search settings

### Bing API Issues

- **401 Unauthorized**: Check your API key
- **403 Forbidden**: Subscription issue or quota exceeded
- **429 Too Many Requests**: Rate limit exceeded, implement backoff

### DuckDuckGo Issues

- **No results**: Check site restriction format
- **Errors or timeout**: Possible rate limiting, implement delay between requests

### Direct Scraping Issues

- **No results found**: Check your CSS selectors
- **Access denied**: Site may be blocking your requests
- **Timeout**: Site may be slow or blocking your requests

## Performance Optimization

To optimize search performance:

1. **Prioritize sites**: Search the most relevant sites first
2. **Use caching**: Enable the cache to avoid repeated searches
3. **Implement concurrency**: MetaStream searches multiple sites concurrently
4. **Limit page depth**: Set reasonable `max_pages_per_site` values

## Security and Privacy Considerations

When using search APIs:

1. **Protect API keys**: Don't expose your API keys in client-side code
2. **Respect rate limits**: Implement proper throttling to avoid bans
3. **Log responsibly**: Don't log sensitive search queries
4. **Respect ToS**: Ensure your usage complies with each search provider's terms of service