# MetaStream Aggregator - Site Configuration Guide

This document provides detailed instructions on how to configure sites in the MetaStream Aggregator application.

## Overview

The `sites.json` file contains configurations for all the sites that the application can search. Each site requires specific selectors and settings that tell the application how to extract data from search results.

## File Structure

The `sites.json` file is a JSON object where each key is the site's unique identifier (which should match the `name` field inside the object).

Example:
```json
{
  "ExampleSite1": {
    "name": "ExampleSite1",
    "base_url": "https://www.example1.com",
    ...
  },
  "ExampleSite2": {
    "name": "ExampleSite2",
    "base_url": "https://www.example2.com",
    ...
  }
}
```

## Configuration Fields

### Basic Fields

| Field | Description | Required |
|-------|-------------|----------|
| `name` | The display name of the site. Should match the key in the JSON object. | Yes |
| `base_url` | The base URL of the website. | Yes |
| `search_method` | The method used to search this site. One of: `scrape_search_page`, `google_site_search`, `bing_search`, `duckduckgo_search`, or `api`. | Yes |
| `search_url_template` | The URL template for searching. Use `{query}` as a placeholder for the search term and `{page}` for the page number. | Yes for `scrape_search_page` |
| `popularity_multiplier` | A multiplier that affects ranking. Values > 1 boost results from this site, values < 1 reduce their prominence. Default is 1.0. | No |

### CSS Selectors for Scraping

These fields are required if `search_method` is `scrape_search_page`:

| Field | Description | Required |
|-------|-------------|----------|
| `results_container_selector` | CSS selector for the container that holds all search result items. | Yes |
| `result_item_selector` | CSS selector for individual result items within the container. | Yes |
| `title_selector` | CSS selector for the title text of a result item. | Yes |
| `video_url_selector` | CSS selector for the link to the video, with `[href]` to extract the URL attribute. | Yes |
| `thumbnail_selector` | CSS selector for the thumbnail image, with `[src]` to extract the image URL. | Yes |
| `duration_selector` | CSS selector for the duration text. | No |
| `rating_selector` | CSS selector for the rating text/element. | No |
| `views_selector` | CSS selector for the view count text. | No |
| `author_selector` | CSS selector for the content author/uploader. | No |
| `next_page_selector` | CSS selector for the "next page" link, with `[href]` to extract the URL. | No |

### Search API Specific Fields

These fields are used for various API-based search methods:

#### Google Site Search

When `search_method` is `google_site_search`:

| Field | Description | Required |
|-------|-------------|----------|
| `site_restriction` | The domain to restrict the Google search to (e.g., `example.com`). | Yes |

The application will use the Google API key and search engine ID from the global settings.

#### Bing Search

When `search_method` is `bing_search`:

| Field | Description | Required |
|-------|-------------|----------|
| `site_restriction` | The domain to restrict the Bing search to (e.g., `example.com`). | Yes |

The application will use the Bing API key from the global settings.

#### DuckDuckGo Search

When `search_method` is `duckduckgo_search`:

| Field | Description | Required |
|-------|-------------|----------|
| `site_restriction` | The domain to restrict the DuckDuckGo search to (e.g., `example.com`). | Yes |

#### API Method

When `search_method` is `api`:

| Field | Description | Required |
|-------|-------------|----------|
| `api_url_template` | The API endpoint template. Use `{query}` and `{page}` as placeholders. | Yes |
| `api_key_param` | The name of the parameter where the API key should be inserted. | No |
| `api_response_path` | JSON path to the search results in the API response (e.g., `results.videos`). | Yes |
| `api_title_field` | Name of the field containing the title in each result. | Yes |
| `api_url_field` | Name of the field containing the video URL in each result. | Yes |
| `api_thumbnail_field` | Name of the field containing the thumbnail URL in each result. | Yes |
| `api_duration_field` | Name of the field containing the duration in each result. | No |
| `api_rating_field` | Name of the field containing the rating in each result. | No |
| `api_views_field` | Name of the field containing the view count in each result. | No |
| `api_author_field` | Name of the field containing the author in each result. | No |

## How to Find CSS Selectors

To find the correct CSS selectors for a website, follow these steps:

1. Open the website in Chrome or Firefox
2. Navigate to a search results page
3. Right-click on an element (e.g., a video title) and select "Inspect" or "Inspect Element"
4. In the developer tools that open, examine the HTML structure
5. Create a CSS selector that uniquely identifies the element

Common CSS selector patterns:
- `div.class-name` - Select divs with a specific class
- `.class-name` - Select any element with a specific class
- `div#id-name` - Select a div with a specific ID
- `div.parent-class div.child-class` - Select nested elements
- `a[href]` - Select links and extract the href attribute
- `img[src]` - Select images and extract the src attribute

## Example Site Configurations

### Direct Scraping Example

```json
"ExampleSitePorn": {
  "name": "ExampleSitePorn",
  "base_url": "https://www.examplesiteporn.com",
  "search_method": "scrape_search_page",
  "search_url_template": "https://www.examplesiteporn.com/search?q={query}&page={page}",
  "results_container_selector": "div.video-list",
  "result_item_selector": "div.video-item",
  "title_selector": "span.title",
  "video_url_selector": "a.video-link[href]",
  "thumbnail_selector": "img.thumb[src]",
  "duration_selector": "span.duration",
  "rating_selector": "div.rating",
  "views_selector": "span.views",
  "author_selector": "div.uploader",
  "next_page_selector": "a.next-page[href]",
  "popularity_multiplier": 1.0
}
```

### Google Search Example

```json
"GoogleSearchExample": {
  "name": "GoogleSearchExample",
  "base_url": "https://www.exampletube.com",
  "search_method": "google_site_search",
  "site_restriction": "exampletube.com",
  "popularity_multiplier": 0.8
}
```

### Bing Search Example

```json
"BingSearchExample": {
  "name": "BingSearchExample",
  "base_url": "https://www.examplevideos.com",
  "search_method": "bing_search",
  "site_restriction": "examplevideos.com",
  "popularity_multiplier": 0.9
}
```

### DuckDuckGo Search Example

```json
"DuckDuckGoExample": {
  "name": "DuckDuckGoExample",
  "base_url": "https://www.exampleadult.com",
  "search_method": "duckduckgo_search",
  "site_restriction": "exampleadult.com",
  "popularity_multiplier": 1.2
}
```

## Troubleshooting

If your site configuration isn't working as expected:

1. **Verify the search URL**: Make sure your `search_url_template` works by manually replacing `{query}` and `{page}` and testing in a browser
2. **Check your selectors**: Use the browser developer tools to confirm your selectors match the expected elements
3. **Look for dynamic content**: Some sites load content dynamically with JavaScript, which can be more difficult to scrape
4. **Check for rate limiting**: Some sites may block frequent requests
5. **Review the application logs**: Check the server console for specific error messages

For API search methods, ensure you have the correct API keys configured in `settings.json`.

## Tips for Optimal Configuration

1. **Start simple**: Begin with just the required fields
2. **Test iteratively**: Add one site at a time and test thoroughly before adding more
3. **Adjust popularity_multiplier**: Use this to balance results between popular and niche sites
4. **Consider search method**: For sites with complex JavaScript, API-based search methods often work better than direct scraping
5. **Balance performance**: Each additional site increases search time, so be selective