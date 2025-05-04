# MetaStream Aggregator - Settings Configuration Guide

This document provides detailed instructions on how to configure user settings in the MetaStream Aggregator application.

## Overview

The `settings.json` file contains user-specific settings that control the behavior of the application, including API keys, search preferences, and ranking algorithm weights.

## File Location

The settings file should be placed in the root directory of the application:

```
/path/to/MetaStream/settings.json
```

A template file `settings.example.json` is provided which you can copy and modify:

```bash
cp settings.example.json settings.json
```

## Configuration Fields

### API Keys and Endpoints

| Field | Description | Required |
|-------|-------------|----------|
| `google_api_key` | Google API key for Custom Search Engine. | Required for Google search |
| `google_search_engine_id` | Google Custom Search Engine ID. | Required for Google search |
| `bing_api_key` | Bing Search API key. | Required for Bing search |
| `duckduckgo_api_key` | DuckDuckGo API key (if required by their API). | Optional |
| `ollama_api_url` | URL for the Ollama API if using local AI models. | Optional |

### Search Preferences

| Field | Description | Default |
|-------|-------------|---------|
| `results_per_page_default` | Number of results to display per page. | 100 |
| `max_pages_per_site` | Maximum number of pages to scrape from each site. | 1 |
| `check_links_default` | Whether to verify link validity by default. | true |
| `cache_expiry_minutes` | How long to keep search results in cache. | 10 |
| `default_search_sites` | Array of site names to search by default. | [] |
| `results_layout` | Layout style for results ("grid" or "list"). | "grid" |

### Scoring Algorithm Weights

The `scoring_weights` object controls how different factors are weighted in the ranking algorithm:

| Field | Description | Default |
|-------|-------------|---------|
| `relevance_weight` | Weight given to query relevance. | 0.50 |
| `rating_weight` | Weight given to site ratings. | 0.30 |
| `views_weight` | Weight given to view counts. | 0.10 |
| `multiplier_effect` | How strongly the site multiplier affects scores. | 0.10 |

All weights should add up to 1.0 for proper normalization.

## Example Configuration

```json
{
  "google_api_key": "your_google_api_key_here",
  "google_search_engine_id": "your_search_engine_id_here",
  "bing_api_key": "your_bing_api_key_here",
  "duckduckgo_api_key": null,
  "ollama_api_url": "http://localhost:11434/api/generate",
  "results_per_page_default": 100,
  "max_pages_per_site": 2,
  "check_links_default": true,
  "cache_expiry_minutes": 30,
  "default_search_sites": ["ExampleSite1", "ExampleSite2"],
  "results_layout": "grid",
  "scoring_weights": {
    "relevance_weight": 0.50,
    "rating_weight": 0.30,
    "views_weight": 0.10,
    "multiplier_effect": 0.10
  }
}
```

## Obtaining API Keys

### Google Custom Search API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the "Custom Search API" from the Library
4. Create credentials to get an API key
5. Go to the [Custom Search Engine](https://cse.google.com/cse/all) page
6. Click "Add" to create a new search engine
7. Add sites you want to search
8. Get your Search Engine ID from the "Setup" > "Basics" page
9. Add the API key and Search Engine ID to settings.json

### Bing Search API

1. Visit the [Azure Portal](https://portal.azure.com/)
2. Create a new resource > AI + Machine Learning > Bing Search
3. Select your pricing tier (free tier is available with limitations)
4. Create and deploy the service
5. Go to "Keys and Endpoint" in your resource
6. Copy one of the keys
7. Add the key to settings.json

### DuckDuckGo API

DuckDuckGo offers different APIs with varying requirements. Check the [DuckDuckGo Developer documentation](https://duckduckgo.com/duckduckgo-help-pages/privacy/web-tracking-protections/) for the most current information on their APIs and any key requirements.

## Scoring Weights Configuration

The ranking algorithm uses a weighted formula to calculate the relevance score for each result:

```
score = ((relevance * relevance_weight) +
         (normalized_rating * rating_weight) +
         (normalized_views * views_weight)
        ) * (1 + (multiplier-1) * multiplier_effect)
```

You can adjust these weights to prioritize different aspects:

- Emphasize **relevance** for results that match your query better
- Emphasize **ratings** for higher-quality results
- Emphasize **views** for more popular results
- Increase **multiplier_effect** to give more weight to niche sites with high popularity_multiplier values

## Caching Configuration

The application caches search results to improve performance for repeated searches:

- `cache_expiry_minutes`: Controls how long results stay in the cache before being refreshed
  - Lower values ensure more fresh results but increase server load
  - Higher values improve performance but may show outdated results

The cache can be cleared manually through the UI or by deleting cache files in the `search_cache` directory.

## Advanced Configuration

### Custom Result Layouts

The `results_layout` setting supports two modes:

- `grid`: Shows results in a grid format with larger thumbnails (good for visual browsing)
- `list`: Shows results in a vertical list with more detailed information

### Multiple Page Scraping

The `max_pages_per_site` setting controls how deep the scraper goes on each site:

- Set to `1` for basic searches and fastest results
- Set to higher values (2-5) to gather more comprehensive results
- Be aware that higher values increase search time significantly

## Troubleshooting

If your settings aren't being applied:

1. Verify your `settings.json` is valid JSON (no missing commas, improperly closed brackets, etc.)
2. Make sure the file is in the correct location
3. Check that file permissions allow the application to read it
4. Look for error messages in the application logs
5. Try restarting the application after making changes

For API-related issues:

1. Verify your API keys are correct
2. Check if you've exceeded API rate limits or quotas
3. Ensure your search engine is properly configured (for Google CSE)
4. Check if the API service is experiencing downtime