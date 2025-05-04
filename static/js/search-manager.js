/**
 * search-manager.js - Handles search logic for MetaStream Aggregator
 * Manages search requests, result processing, and state management
 */

class SearchManager {
    constructor() {
        // Search state
        this.currentQuery = '';
        this.currentSites = [];
        this.currentPage = 1;
        this.lastSearchId = 0;
        this.searchInProgress = false;
        this.searchHistory = [];
        this.maxHistoryItems = 10;
        
        // Search options
        this.useCache = true;
        this.checkLinks = true;
        this.maxPagesPerSite = 1;
        
        // Results state
        this.totalResults = 0;
        this.totalPages = 0;
        this.resultsPerPage = 100;
        
        // Event subscriptions
        this.eventSubscribers = {
            'searchStarted': [],
            'searchCompleted': [],
            'searchFailed': [],
            'searchCancelled': [],
            'resultsUpdated': []
        };
    }
    
    /**
     * Subscribe to search events
     * @param {string} eventName - Event name to subscribe to
     * @param {function} callback - Function to call when event occurs
     */
    on(eventName, callback) {
        if (this.eventSubscribers[eventName]) {
            this.eventSubscribers[eventName].push(callback);
        }
    }
    
    /**
     * Trigger an event
     * @param {string} eventName - Event name to trigger
     * @param {object} data - Data to pass to event handlers
     */
    trigger(eventName, data) {
        if (this.eventSubscribers[eventName]) {
            this.eventSubscribers[eventName].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${eventName} event handler:`, error);
                }
            });
        }
    }
    
    /**
     * Perform a search with the given parameters
     * @param {string} query - Search query
     * @param {Array} sites - Array of site names to search
     * @param {number} page - Page number
     * @param {object} options - Additional search options
     * @returns {Promise} - Promise that resolves with search results
     */
    async search(query, sites, page = 1, options = {}) {
        // Validate input
        if (!query || !query.trim()) {
            throw new Error('Search query is required');
        }
        
        if (!sites || sites.length === 0) {
            throw new Error('At least one site must be selected');
        }
        
        // Set current search parameters
        this.currentQuery = query.trim();
        this.currentSites = [...sites];
        this.currentPage = page;
        
        // Override default options if provided
        if (options.useCache !== undefined) this.useCache = options.useCache;
        if (options.checkLinks !== undefined) this.checkLinks = options.checkLinks;
        if (options.maxPagesPerSite !== undefined) this.maxPagesPerSite = options.maxPagesPerSite;
        
        // Generate a unique ID for this search
        const searchId = ++this.lastSearchId;
        
        // Add to search history
        this.addToSearchHistory(query, sites);
        
        // Mark search as in progress
        this.searchInProgress = true;
        
        // Trigger search started event
        this.trigger('searchStarted', {
            query: this.currentQuery,
            sites: this.currentSites,
            page: this.currentPage,
            searchId
        });
        
        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: this.currentQuery,
                    sites: this.currentSites,
                    page: this.currentPage,
                    use_cache: this.useCache,
                    check_links: this.checkLinks,
                    max_pages_per_site: this.maxPagesPerSite
                })
            });
            
            // If another search was initiated while this one was in progress, ignore results
            if (searchId !== this.lastSearchId) {
                this.trigger('searchCancelled', { searchId });
                return null;
            }
            
            if (!response.ok) {
                throw new Error(`Search failed: ${response.status} ${response.statusText}`);
            }
            
            const searchResults = await response.json();
            
            // If another search was initiated while this one was in progress, ignore results
            if (searchId !== this.lastSearchId) {
                this.trigger('searchCancelled', { searchId });
                return null;
            }
            
            // Update state with results
            if (searchResults.pagination) {
                this.totalResults = searchResults.pagination.total_valid_results;
                this.totalPages = searchResults.pagination.total_pages;
                this.resultsPerPage = searchResults.pagination.results_per_page;
            }
            
            // Mark search as completed
            this.searchInProgress = false;
            
            // Trigger search completed event
            this.trigger('searchCompleted', {
                query: this.currentQuery,
                sites: this.currentSites,
                page: this.currentPage,
                searchId,
                results: searchResults
            });
            
            // Also trigger resultsUpdated event with the new results
            this.trigger('resultsUpdated', {
                results: searchResults.valid_results || [],
                brokenResults: searchResults.broken_results || [],
                pagination: searchResults.pagination,
                searchInfo: searchResults
            });
            
            return searchResults;
            
        } catch (error) {
            // Mark search as completed (but failed)
            this.searchInProgress = false;
            
            // Trigger search failed event
            this.trigger('searchFailed', {
                query: this.currentQuery,
                sites: this.currentSites,
                page: this.currentPage,
                searchId,
                error: error.message
            });
            
            throw error;
        }
    }
    
    /**
     * Change to a different page of results for the current search
     * @param {number} page - Page number to switch to
     * @returns {Promise} - Promise that resolves with search results
     */
    async goToPage(page) {
        if (page < 1 || page > this.totalPages) {
            throw new Error(`Invalid page number: ${page}. Valid range is 1-${this.totalPages}`);
        }
        
        return this.search(this.currentQuery, this.currentSites, page, {
            useCache: this.useCache,
            checkLinks: this.checkLinks,
            maxPagesPerSite: this.maxPagesPerSite
        });
    }
    
    /**
     * Add a search to the search history
     * @param {string} query - Search query
     * @param {Array} sites - Array of site names
     */
    addToSearchHistory(query, sites) {
        // Add new search to beginning of history
        this.searchHistory.unshift({
            query,
            sites: [...sites],
            timestamp: new Date().toISOString()
        });
        
        // Limit history size
        if (this.searchHistory.length > this.maxHistoryItems) {
            this.searchHistory = this.searchHistory.slice(0, this.maxHistoryItems);
        }
        
        // Save to localStorage
        try {
            localStorage.setItem('searchHistory', JSON.stringify(this.searchHistory));
        } catch (e) {
            console.warn('Failed to save search history to localStorage:', e);
        }
    }
    
    /**
     * Load search history from localStorage
     */
    loadSearchHistory() {
        try {
            const savedHistory = localStorage.getItem('searchHistory');
            if (savedHistory) {
                this.searchHistory = JSON.parse(savedHistory);
            }
        } catch (e) {
            console.warn('Failed to load search history from localStorage:', e);
        }
    }
    
    /**
     * Clear search history
     */
    clearSearchHistory() {
        this.searchHistory = [];
        try {
            localStorage.removeItem('searchHistory');
        } catch (e) {
            console.warn('Failed to clear search history from localStorage:', e);
        }
    }
    
    /**
     * Get the current search state
     * @returns {object} - Current search state
     */
    getSearchState() {
        return {
            query: this.currentQuery,
            sites: [...this.currentSites],
            page: this.currentPage,
            totalResults: this.totalResults,
            totalPages: this.totalPages,
            resultsPerPage: this.resultsPerPage,
            searchInProgress: this.searchInProgress,
            useCache: this.useCache,
            checkLinks: this.checkLinks,
            maxPagesPerSite: this.maxPagesPerSite
        };
    }
    
    /**
     * Check if there's an active search
     * @returns {boolean} - True if a search is active
     */
    hasActiveSearch() {
        return this.currentQuery !== '' && this.currentSites.length > 0;
    }
    
    /**
     * Reset the search state
     */
    reset() {
        this.currentQuery = '';
        this.currentSites = [];
        this.currentPage = 1;
        this.totalResults = 0;
        this.totalPages = 0;
        this.searchInProgress = false;
        
        // Trigger resultsUpdated event with empty results
        this.trigger('resultsUpdated', {
            results: [],
            brokenResults: [],
            pagination: null,
            searchInfo: null
        });
    }
}

// Create and export a singleton instance
const searchManager = new SearchManager();
searchManager.loadSearchHistory();

// Load into global scope for simple access
window.searchManager = searchManager;