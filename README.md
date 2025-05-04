# Project MetaStream Aggregator (MSA)

<p align="center">
  <img src="docs/images/metastream_logo.png" alt="MetaStream Aggregator Logo" width="250"/>
</p>

MetaStream Aggregator (MSA) is a locally-hosted web application designed to search, discover, aggregate, and curate adult (XXX) video content from a wide array of configurable online streaming sources. It functions as a sophisticated meta-search engine, utilizing direct site scraping, programmatic web searches (via Google, Bing, or DuckDuckGo APIs), and potentially site-specific APIs to gather results.

## Features

- **Multi-Source Search**: Search across multiple sites simultaneously
- **Result Aggregation**: Combine and normalize results from different sources
- **Content Ranking**: Proprietary algorithm to rank content based on relevance, ratings, views, and site popularity
- **Duplicate Detection**: Identify and consolidate identical videos from different sources
- **Link Validation**: Verify links are valid before presenting them
- **Multi-Video Player**: Stream up to four videos simultaneously
- **Configurable Sites**: Add or modify sites via JSON configuration
- **Multiple Search APIs**: Support for Google, Bing, and DuckDuckGo search APIs
- **Caching System**: Improve performance with configurable result caching

## Installation

### One-Click Installation and Startup

The easiest way to get started with MetaStream Aggregator is to use our one-click installation and startup scripts:

#### Windows
1. Download and extract the MetaStream Aggregator package
2. Double-click the `install_and_run.bat` file
3. The script will:
   - Check for Python installation
   - Create a virtual environment
   - Install all required dependencies
   - Set up configuration files
   - Start the application

#### Linux/macOS
1. Download and extract the MetaStream Aggregator package
2. Open a terminal in the extracted directory
3. Make the script executable: `chmod +x install_and_run.sh`
4. Run the script: `./install_and_run.sh`
5. The script will:
   - Check for Python installation
   - Create a virtual environment
   - Install all required dependencies
   - Set up configuration files
   - Start the application

### Manual Installation

If you prefer to install manually or the scripts don't work for your environment:

#### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

#### Setup

1. Clone or download this repository to your local machine
2. Navigate to the project directory
3. Create a Python virtual environment:
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   - Windows: `venv\\Scripts\\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install required packages:
   ```
   pip install -r requirements.txt
   ```
   or
   ```
   pip install Flask requests beautifulsoup4 lxml google-api-python-client
   ```

## Configuration

### Site Configuration (sites.json)

The application requires a `sites.json` file that defines the websites you want to search. An example file `sites.example.json` is provided which you can copy and modify:

```bash
cp sites.example.json sites.json
```

Each site entry in `sites.json` has the following structure:

```json
{
  "SiteName": {
    "name": "SiteName",
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
    "author_selector": "div.uploader",
    "next_page_selector": "a.next[href]",
    "popularity_multiplier": 1.0
  }
}
```

For detailed information about configuring sites, see the [Site Configuration Guide](docs/site_configuration_guide.md).

The available search methods are:
- `scrape_search_page`: Direct scraping of the site's search page
- `google_site_search`: Using Google Custom Search API for the site
- `bing_search`: Using Bing Search API for the site
- `duckduckgo_search`: Using DuckDuckGo API for the site
- `api`: Using the site's own API (if supported)

For more information on search methods, see the [Search API Guide](docs/search_api_guide.md).

### User Settings (settings.json)

The application uses a `settings.json` file for user-specific settings. An example file `settings.example.json` is provided:

```bash
cp settings.example.json settings.json
```

The settings file includes:

```json
{
  "google_api_key": null,
  "google_search_engine_id": null,
  "bing_api_key": null,
  "duckduckgo_api_key": null,
  "ollama_api_url": "http://localhost:11434/api/generate",
  "results_per_page_default": 100,
  "default_search_sites": ["SiteName1", "SiteName2"],
  "scoring_weights": {
    "relevance_weight": 0.50,
    "rating_weight": 0.30,
    "views_weight": 0.10,
    "multiplier_effect": 0.10
  }
}
```

For detailed information about settings, see the [Settings Configuration Guide](docs/settings_configuration_guide.md).

## API Keys

To use the search API features, you need to obtain API keys:

### Google Custom Search API
1. Create a Google Cloud account
2. Enable the Custom Search API
3. Create API credentials
4. Create a Custom Search Engine (CSE)
5. Add your domain to the CSE
6. Set the API key and CSE ID in settings.json

### Bing Search API
1. Create a Microsoft Azure account
2. Subscribe to Bing Search APIs
3. Create API credentials
4. Set the API key in settings.json

### DuckDuckGo API
1. Check DuckDuckGo for developer API access
2. Set the API key in settings.json if required

For detailed information about setting up search APIs, see the [Search API Guide](docs/search_api_guide.md).

## Running the Application

### Using Installation Scripts
- Windows: Run `install_and_run.bat`
- Linux/macOS: Run `./install_and_run.sh`

### Manual Start
1. Make sure your virtual environment is activated
2. Run the application:
   ```
   python app.py
   ```
3. Open your web browser and navigate to `http://127.0.0.1:8001`

## The Ranking Algorithm

MSA uses a sophisticated ranking algorithm that considers:

1. **Relevance**: How closely the title and description match your search query
2. **Site Rating**: The rating provided by the source site, normalized to a 0-1 scale
3. **View Count**: The number of views, normalized logarithmically
4. **Site Multiplier**: A configurable value that can boost results from niche sites

The formula is:
```
score = ((relevance * relevance_weight) +
         (normalized_rating * rating_weight) +
         (normalized_views * views_weight)
        ) * (1 + (multiplier-1) * multiplier_effect)
```

You can adjust the weights in the settings to customize how results are ranked.

For detailed information about the ranking algorithm, see the [Ranking Algorithm Documentation](docs/ranking_algorithm.md).

## Caching System

MSA includes a caching system to improve performance for repeated searches. By default, search results are cached for 10 minutes.

Key features:
- Configurable cache expiry time
- Cache statistics in the UI
- Options to clear specific or all cache entries
- Automatic cache cleanup

For detailed information about the caching system, see the [Caching System Documentation](docs/caching_system.md).

## Documentation

Comprehensive documentation is available in the `docs` directory:

- [Documentation Index](docs/index.md) - Overview of all documentation
- [Site Configuration Guide](docs/site_configuration_guide.md) - How to configure search sites
- [Settings Configuration Guide](docs/settings_configuration_guide.md) - Configuring application settings
- [Ranking Algorithm Documentation](docs/ranking_algorithm.md) - Detailed explanation of the ranking system
- [Search API Guide](docs/search_api_guide.md) - Guide to the multiple search API options
- [Caching System Documentation](docs/caching_system.md) - Details on the caching system
- [Developer Guide](docs/developer_guide.md) - Guide for developers extending the application

## For Developers

If you're interested in extending or modifying the application, see the [Developer Guide](docs/developer_guide.md) for information about:

- Application architecture
- Adding new search methods
- Implementing new features
- Testing and debugging
- Code style guidelines

## Troubleshooting

### Common Installation Issues

- **Python Not Found**: Make sure Python 3.9+ is installed and added to your PATH
- **Permission Denied** (Linux/macOS): Make sure the install script is executable with `chmod +x install_and_run.sh`
- **Dependencies Installation Failure**: Try running `pip install -r requirements.txt` manually to see detailed error messages
- **Port Already in Use**: If port 8001 is already in use, edit app.py to use a different port

### Runtime Issues

- **No Results**: Check your sites.json configuration and that API keys are properly set in settings.json
- **Slow Performance**: Consider increasing the cache time or reducing the number of sites searched simultaneously
- **Search Errors**: Check the console output for specific error messages related to site scraping or API calls

## Disclaimer

This application is designed for educational purposes to demonstrate advanced web scraping, data aggregation, custom ranking algorithms, and web application architecture. Users are responsible for ensuring compliance with the terms of service of any websites they configure for use with this application.

## License

This project is licensed under the MIT License - see the LICENSE file for details.