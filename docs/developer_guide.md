# MetaStream Aggregator - Developer Guide

This guide provides information for developers who want to extend or modify the MetaStream Aggregator application.

## Application Architecture

MetaStream Aggregator follows a client-server architecture:

1. **Backend** (Python/Flask): Handles data retrieval, processing, and API endpoints
2. **Frontend** (HTML/CSS/JavaScript): Provides the user interface and interactions

### Directory Structure

```
MetaStream/
├── app.py                  # Main Flask application
├── config_manager.py       # Configuration loading and validation
├── site_scraper.py         # Website scraping functionality
├── ranker.py               # Result ranking algorithm
├── link_checker.py         # Link validation
├── cache_manager.py        # Search result caching
├── templates/              # HTML templates
│   └── index.html          # Main application page
├── static/                 # Static assets
│   ├── css/                # Stylesheets
│   │   └── style.css       # Main CSS file
│   ├── js/                 # JavaScript files
│   │   ├── app.js          # Main application logic
│   │   ├── player-manager.js  # Video player management
│   │   ├── search-manager.js  # Search functionality
│   │   └── ui-manager.js      # UI interactions
│   └── images/             # Image assets
├── sites.json              # Site configurations
├── settings.json           # User settings
├── search_cache/           # Cache storage directory
└── docs/                   # Documentation
```

## Backend Components

### app.py

The main Flask application that:
- Initializes the application and loads configurations
- Defines API routes
- Orchestrates the search process

Key API endpoints:
- `/api/search` - Process search requests
- `/api/sites` - Get available sites
- `/api/settings` - Get/update settings
- `/api/cache/stats` - Get cache statistics
- `/api/cache/clear` - Clear cache entries

### config_manager.py

Handles loading and validation of configuration files:
- `sites.json` - Site configurations
- `settings.json` - User settings

### site_scraper.py

Implements various search methods:
- Direct website scraping with BeautifulSoup
- Google Custom Search API integration
- Bing Search API integration
- DuckDuckGo search integration

### ranker.py

Implements the ranking algorithm:
- Calculates relevance scores
- Normalizes ratings and view counts
- Detects and handles duplicates
- Sorts and processes results

### link_checker.py

Verifies the validity of search result links:
- Concurrent link checking
- HEAD request with GET fallback
- Content-type validation

### cache_manager.py

Manages the caching system:
- Storing search results
- Retrieving cached results
- Expiring old cache entries
- Providing cache statistics

## Frontend Components

### index.html

The main HTML template that defines:
- Application layout
- Search interface
- Results display
- Video player
- Settings modal

### style.css

Contains all styling for the application:
- Layout (grid/flexbox)
- Component styling
- Responsive design
- Animations

### JavaScript Files

Organized by functionality:

- **app.js**: Core application logic
  - Initialization
  - Event handlers
  - API communication

- **search-manager.js**: Search functionality
  - Form handling
  - Results processing
  - Pagination

- **player-manager.js**: Video player features
  - Player initialization
  - Video loading
  - Player UI

- **ui-manager.js**: General UI interactions
  - Settings modal
  - Dark/light mode
  - Responsive adjustments

## Key Flows

### Search Flow

1. User enters query and selects sites
2. Frontend sends request to `/api/search`
3. Backend checks cache for matching results
4. If not cached, backend searches selected sites concurrently
5. Results are ranked and duplicates detected
6. Link validity is checked (if enabled)
7. Results are returned and cached
8. Frontend displays results with pagination

### Settings Flow

1. User opens settings modal
2. Frontend loads current settings from `/api/settings`
3. User makes changes and submits
4. Frontend sends updated settings to `/api/settings`
5. Backend validates and saves settings
6. Settings take effect immediately

## Extending the Application

### Adding a New Search Method

To add a new search method (e.g., for a specific API):

1. Modify `site_scraper.py`:
   ```python
   def search_with_new_method(site, query, page=1):
       """
       Search using the new method.
       
       Args:
           site: Site configuration dictionary
           query: Search query string
           page: Page number
           
       Returns:
           List of result dictionaries
       """
       # Implementation here
       ...
       
       # Return results in standard format
       return [
           {
               'title': '...',
               'url': '...',
               'thumbnail': '...',
               'duration_str': '...',
               'site': site['name'],
               'site_rating': 0.8,  # Normalized to 0-1
               'views': 10000,
               'author': '...'
           },
           # More results...
       ]
   ```

2. Update the `scrape_site` function to handle the new method:
   ```python
   def scrape_site(site, query, page=1):
       # ...
       if search_method == 'new_method':
           return search_with_new_method(site, query, page)
       # ...
   ```

3. Update the site configuration schema in the documentation

### Adding a New Feature

To add a new feature:

1. **Backend changes**: If the feature requires new data or functionality, add appropriate methods and API endpoints

2. **Frontend changes**: 
   - Add UI elements to `index.html`
   - Add styling to `style.css`
   - Implement interaction logic in JavaScript files
   - Connect to backend API if needed

3. **Configuration changes**: If the feature requires configuration, update:
   - `settings.json` and `settings.example.json`
   - `config_manager.py` to handle the new settings

4. **Documentation**: Update relevant documentation files

### Example: Adding Rating Filtering

Here's how you might add a feature to filter results by minimum rating:

1. Backend changes in `app.py`:
   ```python
   @app.route('/api/search', methods=['POST'])
   def search():
       # ...
       min_rating = data.get('min_rating', 0)  # New parameter
       
       # After ranking but before pagination
       if min_rating > 0:
           valid_results = [r for r in valid_results 
                           if r.get('site_rating', 0) >= min_rating]
       # ...
   ```

2. Frontend changes in `index.html`:
   ```html
   <div class="filter-controls">
     <label for="min-rating">Minimum Rating:</label>
     <select id="min-rating">
       <option value="0">Any Rating</option>
       <option value="0.6">60% or higher</option>
       <option value="0.7">70% or higher</option>
       <option value="0.8">80% or higher</option>
       <option value="0.9">90% or higher</option>
     </select>
   </div>
   ```

3. JavaScript changes in `search-manager.js`:
   ```javascript
   function sendSearchRequest() {
       // ...
       const minRating = parseFloat(document.getElementById('min-rating').value);
       
       const searchData = {
           query: query,
           sites: selectedSites,
           page: currentPage,
           use_cache: useCache,
           check_links: checkLinks,
           min_rating: minRating  // New parameter
       };
       // ...
   }
   ```

4. Update documentation to explain the new feature

## Testing

For testing changes:

1. **Unit tests**: Located in the `tests` directory, run with pytest
2. **Integration tests**: End-to-end API tests in `test_integration.py`
3. **Manual testing**: Use the UI to test changes across different browsers

## Performance Considerations

When modifying the code:

1. **Concurrency**: Keep the concurrent processing model for site scraping
2. **Caching**: Leverage the caching system for repeated operations
3. **Memory usage**: Be mindful of memory consumption, especially with large result sets
4. **User experience**: Keep the UI responsive with proper loading indicators

## Code Style Guidelines

1. **Python**:
   - Follow PEP 8 guidelines
   - Use docstrings for functions and classes
   - Type hints encouraged

2. **JavaScript**:
   - Follow modern ES6+ practices
   - Use camelCase for variables and functions
   - Prefer const/let over var

3. **HTML/CSS**:
   - Use semantic HTML5 elements
   - Follow BEM methodology for CSS classes
   - Ensure responsive design

## Debugging

Tools for debugging:

1. **Backend logging**: Check the Flask development server output
2. **Frontend console**: Use browser developer tools
3. **Network tab**: Inspect API requests/responses
4. **Debug tool**: Use `debug_tool.py` to diagnose issues

## Contribution Workflow

1. **Fork** the repository
2. Create a **feature branch**
3. Implement your changes
4. **Test** thoroughly
5. Submit a **pull request**
6. Provide detailed description of changes

## Versioning

The project follows semantic versioning:
- **Major** version: Breaking changes
- **Minor** version: New features, backward-compatible
- **Patch** version: Bug fixes, backward-compatible