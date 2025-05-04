/**
 * ui-manager.js - Handles UI interactions for MetaStream Aggregator
 * Manages DOM updates, event handling, and UI state
 */

class UIManager {
    constructor() {
        // UI state
        this.resultsLayout = 'grid'; // 'grid' or 'list'
        this.settingsVisible = false;
        this.cacheModalVisible = false;
        this.helpModalVisible = false;
        this.brokenResultsExpanded = false;
        
        // DOM elements cache
        this.elements = {};
        
        // Initialize
        this.cacheElements();
        this.loadPreferences();
        this.applyInitialState();
    }
    
    /**
     * Cache DOM elements for faster access
     */
    cacheElements() {
        // Search elements
        this.elements.searchInput = document.getElementById('search-input');
        this.elements.searchButton = document.getElementById('search-button');
        this.elements.resetButton = document.getElementById('reset-button');
        this.elements.siteListContainer = document.getElementById('site-list-container');
        this.elements.selectAllButton = document.getElementById('select-all-sites');
        this.elements.selectNoneButton = document.getElementById('select-none-sites');
        this.elements.useCacheCheckbox = document.getElementById('use-cache');
        this.elements.checkLinksCheckbox = document.getElementById('check-links');
        
        // Results elements
        this.elements.resultsContainer = document.getElementById('results-container');
        this.elements.brokenResultsContainer = document.getElementById('broken-results-container');
        this.elements.brokenCount = document.getElementById('broken-count');
        this.elements.brokenToggle = document.querySelector('.broken-section h2');
        this.elements.paginationContainer = document.getElementById('pagination-container');
        this.elements.summaryContainer = document.getElementById('summary-container');
        this.elements.loadingIndicator = document.getElementById('loading-indicator');
        
        // Player elements
        this.elements.playerArea = document.querySelector('.player-area');
        this.elements.minimizePlayersButton = document.getElementById('minimize-players');
        this.elements.closeAllPlayersButton = document.getElementById('close-all-players');
        this.elements.activePlayersList = document.getElementById('active-players-list');
        
        // Modal elements
        this.elements.settingsButton = document.getElementById('settings-button');
        this.elements.settingsModal = document.getElementById('settings-modal');
        this.elements.closeSettings = document.getElementById('close-settings');
        this.elements.settingsForm = document.getElementById('settings-form');
        this.elements.resetDefaultSettingsButton = document.getElementById('reset-default-settings');
        this.elements.resultsLayoutSelect = document.getElementById('results-layout');
        
        this.elements.cacheButton = document.getElementById('cache-button');
        this.elements.cacheModal = document.getElementById('cache-modal');
        this.elements.closeCache = document.getElementById('close-cache');
        this.elements.cacheStatsContainer = document.getElementById('cache-stats');
        this.elements.clearAllCacheButton = document.getElementById('clear-all-cache');
        this.elements.clearCurrentSearchCacheButton = document.getElementById('clear-current-search-cache');
        
        // Help elements
        this.elements.helpModal = document.getElementById('help-modal');
        this.elements.closeHelp = document.getElementById('close-help');
    }
    
    /**
     * Load user preferences from localStorage
     */
    loadPreferences() {
        // Load results layout preference
        const savedLayout = localStorage.getItem('resultsLayout');
        if (savedLayout) {
            this.resultsLayout = savedLayout;
            if (this.elements.resultsLayoutSelect) {
                this.elements.resultsLayoutSelect.value = savedLayout;
            }
        }
        
        // Load broken results expanded state
        const brokenExpanded = localStorage.getItem('brokenResultsExpanded');
        if (brokenExpanded) {
            this.brokenResultsExpanded = brokenExpanded === 'true';
        }
    }
    
    /**
     * Apply initial UI state based on loaded preferences
     */
    applyInitialState() {
        // Apply results layout
        if (this.resultsLayout === 'list') {
            this.elements.resultsContainer.classList.add('list-view');
        } else {
            this.elements.resultsContainer.classList.remove('list-view');
        }
        
        // Apply broken results expanded state
        if (this.brokenResultsExpanded) {
            this.elements.brokenToggle.classList.remove('collapsed');
            this.elements.brokenResultsContainer.classList.remove('collapsed');
        } else {
            this.elements.brokenToggle.classList.add('collapsed');
            this.elements.brokenResultsContainer.classList.add('collapsed');
        }
        
        // Apply player area minimized state based on PlayerManager
        if (window.playerManager && window.playerManager.isMinimized()) {
            this.elements.playerArea.classList.add('minimized');
            this.elements.minimizePlayersButton.textContent = 'Expand';
        }
    }
    
    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Search events
        this.elements.searchButton.addEventListener('click', () => {
            this.handleSearch();
        });
        
        this.elements.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleSearch();
            }
        });
        
        this.elements.resetButton.addEventListener('click', () => {
            this.resetSearch();
        });
        
        // Site selection
        this.elements.selectAllButton.addEventListener('click', () => {
            this.selectAllSites();
        });
        
        this.elements.selectNoneButton.addEventListener('click', () => {
            this.selectNoSites();
        });
        
        // Pagination
        this.elements.paginationContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('pagination-link') && !e.target.classList.contains('disabled')) {
                e.preventDefault();
                this.handlePaginationClick(e.target);
            }
        });
        
        // Results interaction (delegated)
        this.elements.resultsContainer.addEventListener('click', (e) => {
            // Handle player buttons
            if (e.target.classList.contains('player-button')) {
                const playerId = e.target.dataset.playerId;
                const videoUrl = e.target.dataset.url;
                const videoTitle = e.target.dataset.title;
                const videoSource = e.target.dataset.source;
                
                this.handleSendToPlayer(playerId, videoUrl, videoTitle, videoSource);
            }
            
            // Handle alternates toggle
            if (e.target.classList.contains('alternates-toggle')) {
                this.toggleAlternates(e.target);
            }
        });
        
        // Player controls
        this.elements.minimizePlayersButton.addEventListener('click', () => {
            this.togglePlayerArea();
        });
        
        this.elements.closeAllPlayersButton.addEventListener('click', () => {
            this.closeAllPlayers();
        });
        
        // Player close buttons (delegated)
        document.querySelectorAll('.player-slot').forEach(slot => {
            slot.addEventListener('click', (e) => {
                if (e.target.classList.contains('close-player')) {
                    const playerId = e.target.dataset.playerId;
                    this.closePlayer(playerId);
                }
            });
        });
        
        // Broken results toggle
        this.elements.brokenToggle.addEventListener('click', () => {
            this.toggleBrokenResults();
        });
        
        // Settings modal
        this.elements.settingsButton.addEventListener('click', () => {
            this.openSettingsModal();
        });
        
        this.elements.closeSettings.addEventListener('click', () => {
            this.closeSettingsModal();
        });
        
        // Cache modal
        this.elements.cacheButton.addEventListener('click', () => {
            this.openCacheModal();
        });
        
        this.elements.closeCache.addEventListener('click', () => {
            this.closeCacheModal();
        });
        
        // Help modal
        if (this.elements.closeHelp) {
            this.elements.closeHelp.addEventListener('click', () => {
                this.closeHelpModal();
            });
        }
        
        // Close modals when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === this.elements.settingsModal) {
                this.closeSettingsModal();
            } else if (e.target === this.elements.cacheModal) {
                this.closeCacheModal();
            } else if (e.target === this.elements.helpModal) {
                this.closeHelpModal();
            }
        });
        
        // Settings form
        this.elements.settingsForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveSettings();
        });
        
        this.elements.resetDefaultSettingsButton.addEventListener('click', () => {
            this.resetToDefaultSettings();
        });
        
        // Results layout change
        if (this.elements.resultsLayoutSelect) {
            this.elements.resultsLayoutSelect.addEventListener('change', (e) => {
                this.changeResultsLayout(e.target.value);
            });
        }
        
        // Cache actions
        this.elements.clearAllCacheButton.addEventListener('click', () => {
            this.clearAllCache();
        });
        
        this.elements.clearCurrentSearchCacheButton.addEventListener('click', () => {
            this.clearCurrentSearchCache();
        });
        
        // Subscribe to SearchManager events
        if (window.searchManager) {
            window.searchManager.on('searchStarted', (data) => {
                this.showLoading();
            });
            
            window.searchManager.on('searchCompleted', (data) => {
                this.hideLoading();
            });
            
            window.searchManager.on('searchFailed', (data) => {
                this.hideLoading();
                this.showError(data.error);
            });
            
            window.searchManager.on('resultsUpdated', (data) => {
                this.displayResults(data.results, data.brokenResults, data.pagination, data.searchInfo);
            });
        }
        
        // Subscribe to PlayerManager events
        if (window.playerManager) {
            window.playerManager.on('playerLoaded', (data) => {
                this.updatePlayersList();
            });
            
            window.playerManager.on('playerClosed', (data) => {
                this.updatePlayersList();
            });
            
            window.playerManager.on('allPlayersClosed', () => {
                this.updatePlayersList();
            });
            
            window.playerManager.on('playerAreaToggled', (data) => {
                this.updatePlayerAreaMinimized(data.minimized);
            });
        }
    }
    
    /**
     * Handle search submission
     */
    handleSearch() {
        if (!this.elements.searchInput.value.trim()) {
            alert('Please enter a search query');
            return;
        }
        
        const selectedSites = this.getSelectedSites();
        if (selectedSites.length === 0) {
            alert('Please select at least one site to search');
            return;
        }
        
        // Get search options
        const useCache = this.elements.useCacheCheckbox.checked;
        const checkLinks = this.elements.checkLinksCheckbox.checked;
        
        // Execute search through SearchManager
        if (window.searchManager) {
            window.searchManager.search(
                this.elements.searchInput.value.trim(),
                selectedSites,
                1, // Start on page 1
                { useCache, checkLinks }
            ).catch(error => {
                console.error('Search error:', error);
                // Error handling is done through SearchManager events
            });
        }
    }
    
    /**
     * Reset search form and results
     */
    resetSearch() {
        this.elements.searchInput.value = '';
        document.querySelectorAll('.site-checkbox').forEach(cb => {
            cb.checked = false;
        });
        
        this.elements.resultsContainer.innerHTML = '';
        this.elements.brokenResultsContainer.innerHTML = '';
        this.elements.paginationContainer.innerHTML = '';
        this.elements.summaryContainer.innerHTML = '';
        
        // Reset search state in SearchManager
        if (window.searchManager) {
            window.searchManager.reset();
        }
        
        // Update clear current search button state
        this.updateClearCurrentSearchButtonState();
    }
    
    /**
     * Handle pagination clicks
     * @param {HTMLElement} clickedElement - The pagination link that was clicked
     */
    handlePaginationClick(clickedElement) {
        if (!window.searchManager) return;
        
        const pageAction = clickedElement.dataset.page;
        const currentPage = window.searchManager.currentPage;
        let targetPage;
        
        // Determine which page to navigate to
        if (pageAction === 'prev') {
            if (currentPage > 1) {
                targetPage = currentPage - 1;
            } else {
                return; // Already on first page
            }
        } else if (pageAction === 'next') {
            if (currentPage < window.searchManager.totalPages) {
                targetPage = currentPage + 1;
            } else {
                return; // Already on last page
            }
        } else {
            // Direct page number
            targetPage = parseInt(pageAction, 10);
        }
        
        // Navigate to the page
        if (targetPage) {
            window.searchManager.goToPage(targetPage).catch(error => {
                console.error('Pagination error:', error);
            });
            
            // Scroll to top of results
            document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
        }
    }
    
    /**
     * Handle sending a video to a player
     * @param {string} playerId - Player ID
     * @param {string} url - Video URL
     * @param {string} title - Video title
     * @param {string} source - Video source site
     */
    handleSendToPlayer(playerId, url, title, source) {
        if (!window.playerManager) return;
        
        window.playerManager.loadVideo(playerId, url, title, source);
        
        // Expand player area if minimized
        if (window.playerManager.isMinimized()) {
            window.playerManager.toggleMinimized();
            this.updatePlayerAreaMinimized(false);
        }
    }
    
    /**
     * Toggle alternates section visibility
     * @param {HTMLElement} toggleElement - The toggle element that was clicked
     */
    toggleAlternates(toggleElement) {
        const alternatesList = toggleElement.nextElementSibling;
        if (!alternatesList) return;
        
        alternatesList.classList.toggle('visible');
        toggleElement.textContent = alternatesList.classList.contains('visible') ? 
            'Hide Alternates' : 'Show Alternates';
    }
    
    /**
     * Toggle player area minimized state
     */
    togglePlayerArea() {
        if (!window.playerManager) return;
        
        const minimized = window.playerManager.toggleMinimized();
        this.updatePlayerAreaMinimized(minimized);
    }
    
    /**
     * Update player area UI based on minimized state
     * @param {boolean} minimized - Whether the player area is minimized
     */
    updatePlayerAreaMinimized(minimized) {
        if (minimized) {
            this.elements.playerArea.classList.add('minimized');
            this.elements.minimizePlayersButton.textContent = 'Expand';
        } else {
            this.elements.playerArea.classList.remove('minimized');
            this.elements.minimizePlayersButton.textContent = 'Minimize';
        }
    }
    
    /**
     * Close a specific player
     * @param {string} playerId - Player ID to close
     */
    closePlayer(playerId) {
        if (!window.playerManager) return;
        
        window.playerManager.closePlayer(playerId);
    }
    
    /**
     * Close all active players
     */
    closeAllPlayers() {
        if (!window.playerManager) return;
        
        window.playerManager.closeAllPlayers();
    }
    
    /**
     * Toggle broken results section visibility
     */
    toggleBrokenResults() {
        this.brokenResultsExpanded = !this.brokenResultsExpanded;
        
        if (this.brokenResultsExpanded) {
            this.elements.brokenToggle.classList.remove('collapsed');
            this.elements.brokenResultsContainer.classList.remove('collapsed');
        } else {
            this.elements.brokenToggle.classList.add('collapsed');
            this.elements.brokenResultsContainer.classList.add('collapsed');
        }
        
        // Save preference to localStorage
        localStorage.setItem('brokenResultsExpanded', this.brokenResultsExpanded);
    }
    
    /**
     * Open settings modal
     */
    async openSettingsModal() {
        try {
            const response = await fetch('/api/settings');
            if (!response.ok) {
                throw new Error(`Failed to load settings: ${response.status}`);
            }
            
            const settings = await response.json();
            
            // Populate form fields - API keys
            document.getElementById('google-api-key').value = settings.google_api_key === '********' ? '' : (settings.google_api_key || '');
            document.getElementById('google-search-engine-id').value = settings.google_search_engine_id || '';
            document.getElementById('bing-api-key').value = settings.bing_api_key === '********' ? '' : (settings.bing_api_key || '');
            document.getElementById('duckduckgo-api-key').value = settings.duckduckgo_api_key === '********' ? '' : (settings.duckduckgo_api_key || '');
            
            // Display options
            document.getElementById('results-per-page').value = settings.results_per_page_default || 100;
            if (document.getElementById('results-layout')) {
                document.getElementById('results-layout').value = this.resultsLayout;
            }
            
            // Cache options
            document.getElementById('cache-expiry-minutes').value = settings.cache_expiry_minutes || 10;
            
            // Search options
            document.getElementById('max-pages-per-site').value = settings.max_pages_per_site || 1;
            document.getElementById('check-links-default').value = settings.check_links_default ? 'true' : 'false';
            
            // Populate scoring weights
            const weights = settings.scoring_weights || {};
            document.getElementById('relevance-weight').value = weights.relevance_weight || 0.5;
            document.getElementById('rating-weight').value = weights.rating_weight || 0.3;
            document.getElementById('views-weight').value = weights.views_weight || 0.1;
            document.getElementById('multiplier-effect').value = weights.multiplier_effect || 0.1;
            
            // Advanced options
            document.getElementById('ollama-api-url').value = settings.ollama_api_url || '';
            
            // Show modal
            this.elements.settingsModal.style.display = 'block';
            this.settingsVisible = true;
            
        } catch (error) {
            console.error('Error loading settings:', error);
            alert(`Error loading settings: ${error.message}`);
        }
    }
    
    /**
     * Close settings modal
     */
    closeSettingsModal() {
        this.elements.settingsModal.style.display = 'none';
        this.settingsVisible = false;
    }
    
    /**
     * Save settings from form
     */
    async saveSettings() {
        // Collect form data
        const formData = new FormData(this.elements.settingsForm);
        const settingsData = {};
        
        // Create nested structure for scoring weights
        const scoringWeights = {};
        
        for (const [key, value] of formData.entries()) {
            if (key.startsWith('scoring_weights.')) {
                const weightKey = key.split('.')[1];
                scoringWeights[weightKey] = parseFloat(value);
            } else if (key === 'check_links_default') {
                // Convert 'true'/'false' string to boolean
                settingsData[key] = value === 'true';
            } else {
                // Don't send empty API keys (they will delete existing values)
                if ((key.includes('api_key') || key.includes('search_engine_id')) && !value) {
                    continue;
                }
                
                // Convert numeric values to numbers
                if (key === 'results_per_page_default' || key === 'cache_expiry_minutes' || key === 'max_pages_per_site') {
                    settingsData[key] = parseInt(value, 10);
                } else {
                    settingsData[key] = value;
                }
            }
        }
        
        // Add scoring weights to settings
        settingsData.scoring_weights = scoringWeights;
        
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settingsData)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to save settings: ${response.status}`);
            }
            
            const result = await response.json();
            alert('Settings saved successfully!');
            this.closeSettingsModal();
            
            // Update checkbox states to match new settings
            if (settingsData.check_links_default !== undefined) {
                this.elements.checkLinksCheckbox.checked = settingsData.check_links_default;
            }
            
        } catch (error) {
            console.error('Error saving settings:', error);
            alert(`Error saving settings: ${error.message}`);
        }
    }
    
    /**
     * Reset settings to application defaults
     */
    async resetToDefaultSettings() {
        try {
            const response = await fetch('/api/settings/default');
            if (!response.ok) {
                throw new Error(`Failed to load default settings: ${response.status}`);
            }
            
            const defaultSettings = await response.json();
            
            // Populate form with default values - API keys
            document.getElementById('google-api-key').value = '';
            document.getElementById('google-search-engine-id').value = '';
            document.getElementById('bing-api-key').value = '';
            document.getElementById('duckduckgo-api-key').value = '';
            
            // Display options
            document.getElementById('results-per-page').value = defaultSettings.results_per_page_default || 100;
            
            // Cache options
            document.getElementById('cache-expiry-minutes').value = defaultSettings.cache_expiry_minutes || 10;
            
            // Search options
            document.getElementById('max-pages-per-site').value = defaultSettings.max_pages_per_site || 1;
            document.getElementById('check-links-default').value = defaultSettings.check_links_default ? 'true' : 'false';
            
            // Populate scoring weights
            const weights = defaultSettings.scoring_weights || {};
            document.getElementById('relevance-weight').value = weights.relevance_weight || 0.5;
            document.getElementById('rating-weight').value = weights.rating_weight || 0.3;
            document.getElementById('views-weight').value = weights.views_weight || 0.1;
            document.getElementById('multiplier-effect').value = weights.multiplier_effect || 0.1;
            
            // Advanced options
            document.getElementById('ollama-api-url').value = defaultSettings.ollama_api_url || '';
            
        } catch (error) {
            console.error('Error loading default settings:', error);
            alert(`Error loading default settings: ${error.message}`);
        }
    }
    
    /**
     * Open cache management modal
     */
    async openCacheModal() {
        try {
            const response = await fetch('/api/cache/stats');
            if (!response.ok) {
                throw new Error(`Failed to load cache stats: ${response.status}`);
            }
            
            const stats = await response.json();
            
            // Display cache stats
            this.elements.cacheStatsContainer.innerHTML = `
                <div class="cache-stat-item">
                    <span class="stat-label">Total Entries:</span>
                    <span class="stat-value">${stats.total_entries}</span>
                </div>
                <div class="cache-stat-item">
                    <span class="stat-label">Active Entries:</span>
                    <span class="stat-value">${stats.active_entries}</span>
                </div>
                <div class="cache-stat-item">
                    <span class="stat-label">Expired Entries:</span>
                    <span class="stat-value">${stats.expired_entries}</span>
                </div>
                <div class="cache-stat-item">
                    <span class="stat-label">Cache Size:</span>
                    <span class="stat-value">${stats.cache_size_kb} KB</span>
                </div>
            `;
            
            // Update clear current search button state
            this.updateClearCurrentSearchButtonState();
            
            // Show modal
            this.elements.cacheModal.style.display = 'block';
            this.cacheModalVisible = true;
            
        } catch (error) {
            console.error('Error loading cache stats:', error);
            alert(`Error loading cache stats: ${error.message}`);
        }
    }
    
    /**
     * Close cache management modal
     */
    closeCacheModal() {
        this.elements.cacheModal.style.display = 'none';
        this.cacheModalVisible = false;
    }
    
    /**
     * Close help/about modal
     */
    closeHelpModal() {
        if (this.elements.helpModal) {
            this.elements.helpModal.style.display = 'none';
            this.helpModalVisible = false;
        }
    }
    
    /**
     * Clear all cache entries
     */
    async clearAllCache() {
        try {
            const response = await fetch('/api/cache/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            if (!response.ok) {
                throw new Error(`Failed to clear cache: ${response.status}`);
            }
            
            // Refresh cache stats
            await this.refreshCacheStats();
            
            alert('All cache entries cleared successfully');
            
        } catch (error) {
            console.error('Error clearing cache:', error);
            alert(`Error clearing cache: ${error.message}`);
        }
    }
    
    /**
     * Clear cache for current search
     */
    async clearCurrentSearchCache() {
        if (!window.searchManager || !window.searchManager.hasActiveSearch()) {
            alert('No active search to clear from cache');
            return;
        }
        
        try {
            const query = window.searchManager.currentQuery;
            const sites = window.searchManager.currentSites;
            
            const response = await fetch('/api/cache/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query,
                    sites
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to clear cache: ${response.status}`);
            }
            
            // Refresh cache stats
            await this.refreshCacheStats();
            
            alert(`Cache cleared for query "${query}"`);
            
        } catch (error) {
            console.error('Error clearing cache:', error);
            alert(`Error clearing cache: ${error.message}`);
        }
    }
    
    /**
     * Refresh cache statistics
     */
    async refreshCacheStats() {
        try {
            const response = await fetch('/api/cache/stats');
            if (!response.ok) {
                throw new Error(`Failed to load cache stats: ${response.status}`);
            }
            
            const stats = await response.json();
            
            // Update cache stats
            this.elements.cacheStatsContainer.innerHTML = `
                <div class="cache-stat-item">
                    <span class="stat-label">Total Entries:</span>
                    <span class="stat-value">${stats.total_entries}</span>
                </div>
                <div class="cache-stat-item">
                    <span class="stat-label">Active Entries:</span>
                    <span class="stat-value">${stats.active_entries}</span>
                </div>
                <div class="cache-stat-item">
                    <span class="stat-label">Expired Entries:</span>
                    <span class="stat-value">${stats.expired_entries}</span>
                </div>
                <div class="cache-stat-item">
                    <span class="stat-label">Cache Size:</span>
                    <span class="stat-value">${stats.cache_size_kb} KB</span>
                </div>
            `;
        } catch (error) {
            console.error('Error refreshing cache stats:', error);
        }
    }
    
    /**
     * Update clear current search cache button state
     */
    updateClearCurrentSearchButtonState() {
        const hasActiveSearch = window.searchManager && window.searchManager.hasActiveSearch();
        
        if (hasActiveSearch) {
            this.elements.clearCurrentSearchCacheButton.disabled = false;
            this.elements.clearCurrentSearchCacheButton.textContent = 
                `Clear Cache for "${window.searchManager.currentQuery}"`;
        } else {
            this.elements.clearCurrentSearchCacheButton.disabled = true;
            this.elements.clearCurrentSearchCacheButton.textContent = 'Clear Current Search Cache';
        }
    }
    
    /**
     * Change results layout (grid or list)
     * @param {string} layout - Layout type ('grid' or 'list')
     */
    changeResultsLayout(layout) {
        if (layout !== 'grid' && layout !== 'list') {
            return;
        }
        
        this.resultsLayout = layout;
        localStorage.setItem('resultsLayout', layout);
        
        if (layout === 'list') {
            this.elements.resultsContainer.classList.add('list-view');
        } else {
            this.elements.resultsContainer.classList.remove('list-view');
        }
    }
    
    /**
     * Select all sites
     */
    selectAllSites() {
        document.querySelectorAll('.site-checkbox').forEach(cb => {
            cb.checked = true;
        });
    }
    
    /**
     * Deselect all sites
     */
    selectNoSites() {
        document.querySelectorAll('.site-checkbox').forEach(cb => {
            cb.checked = false;
        });
    }
    
    /**
     * Get selected sites
     * @returns {Array} - Array of selected site names
     */
    getSelectedSites() {
        return Array.from(document.querySelectorAll('.site-checkbox:checked'))
            .map(checkbox => checkbox.value);
    }
    
    /**
     * Show loading indicator
     */
    showLoading() {
        this.elements.loadingIndicator.classList.remove('hidden');
    }
    
    /**
     * Hide loading indicator
     */
    hideLoading() {
        this.elements.loadingIndicator.classList.add('hidden');
    }
    
    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    showError(message) {
        alert(`Error: ${message}`);
    }
    
    /**
     * Display search results
     * @param {Array} results - Valid search results
     * @param {Array} brokenResults - Broken link results
     * @param {object} pagination - Pagination information
     * @param {object} searchInfo - Additional search info
     */
    displayResults(results, brokenResults, pagination, searchInfo) {
        // Apply correct layout
        if (this.resultsLayout === 'list') {
            this.elements.resultsContainer.classList.add('list-view');
        } else {
            this.elements.resultsContainer.classList.remove('list-view');
        }
        
        // Clear existing results
        this.elements.resultsContainer.innerHTML = '';
        this.elements.brokenResultsContainer.innerHTML = '';
        
        // Display valid results
        if (!results || results.length === 0) {
            this.elements.resultsContainer.innerHTML = '<p class="no-results">No results found matching your query.</p>';
        } else {
            results.forEach(result => {
                this.elements.resultsContainer.appendChild(this.createResultItemElement(result));
            });
        }
        
        // Display broken results
        if (!brokenResults || brokenResults.length === 0) {
            this.elements.brokenResultsContainer.innerHTML = '<p class="no-broken">No broken links found.</p>';
            this.elements.brokenCount.textContent = '';
        } else {
            this.elements.brokenCount.textContent = `(${brokenResults.length})`;
            brokenResults.forEach(result => {
                this.elements.brokenResultsContainer.appendChild(this.createBrokenItemElement(result));
            });
        }
        
        // Update pagination
        this.renderPagination(pagination);
        
        // Update summary
        this.updateSearchSummary(searchInfo);
    }
    
    /**
     * Create HTML for a single result item
     * @param {object} item - Result item data
     * @returns {HTMLElement} - Result item element
     */
    createResultItemElement(item) {
        const resultItem = document.createElement('div');
        resultItem.className = 'result-item';
        
        // Default thumbnail if none provided
        const thumbnail = item.thumbnail || '/static/images/no-thumbnail.png';
        
        // Calculate score percentage for display (if available)
        const scorePercentage = item.calc_score ? 
            Math.round(item.calc_score * 100) : '';
        
        // Main structure
        resultItem.innerHTML = `
            <div class="thumbnail-container">
                <img src="${thumbnail}" alt="${item.title || 'Video thumbnail'}" loading="lazy">
                ${item.duration_str ? `<div class="duration-badge">${item.duration_str}</div>` : ''}
            </div>
            <div class="info-container">
                <h4 class="result-title">${item.title || 'Untitled Video'}</h4>
                <div class="meta-info">
                    <span class="site-name">${item.site || 'Unknown Site'}</span>
                    <span class="rating">
                        ${item.rating_str ? `${item.rating_str}` : ''}
                        ${scorePercentage ? ` • Score: ${scorePercentage}%` : ''}
                    </span>
                </div>
                <div class="buttons-container">
                    <a href="${item.url}" target="_blank" class="button small">Open New Tab</a>
                    <button class="button small button-player player-button" 
                        data-player-id="player-1" 
                        data-url="${item.url}"
                        data-title="${item.title}"
                        data-source="${item.site}">Player 1</button>
                    <button class="button small button-player player-button" 
                        data-player-id="player-2" 
                        data-url="${item.url}"
                        data-title="${item.title}"
                        data-source="${item.site}">Player 2</button>
                    <button class="button small button-player player-button" 
                        data-player-id="player-3" 
                        data-url="${item.url}"
                        data-title="${item.title}"
                        data-source="${item.site}">Player 3</button>
                    <button class="button small button-player player-button" 
                        data-player-id="player-4" 
                        data-url="${item.url}"
                        data-title="${item.title}"
                        data-source="${item.site}">Player 4</button>
                </div>
            </div>
        `;
        
        // Add alternates section if exists
        if (item.alternates && item.alternates.length > 0) {
            const alternatesContainer = document.createElement('div');
            alternatesContainer.className = 'alternates-container';
            
            const alternatesToggle = document.createElement('div');
            alternatesToggle.className = 'alternates-toggle';
            alternatesToggle.textContent = 'Show Alternates';
            
            const alternatesList = document.createElement('div');
            alternatesList.className = 'alternates-list';
            
            item.alternates.forEach(alt => {
                alternatesList.innerHTML += `
                    <a class="alternate-link" href="${alt.url}" target="_blank">${alt.site}: ${alt.title}</a>
                `;
            });
            
            alternatesContainer.appendChild(alternatesToggle);
            alternatesContainer.appendChild(alternatesList);
            resultItem.querySelector('.info-container').appendChild(alternatesContainer);
        }
        
        return resultItem;
    }
    
    /**
     * Create HTML for a broken link item
     * @param {object} item - Broken link item data
     * @returns {HTMLElement} - Broken item element
     */
    createBrokenItemElement(item) {
        const brokenItem = document.createElement('div');
        brokenItem.className = 'broken-item';
        brokenItem.innerHTML = `
            <div class="broken-title">${item.title || 'Untitled Video'}</div>
            <div class="broken-url">${item.url}</div>
            <div class="broken-site">${item.site || 'Unknown Site'}</div>
        `;
        return brokenItem;
    }
    
    /**
     * Render pagination controls
     * @param {object} pagination - Pagination information
     */
    renderPagination(pagination) {
        if (!pagination) {
            this.elements.paginationContainer.innerHTML = '';
            return;
        }
        
        const {current_page, total_pages, total_valid_results, results_per_page} = pagination;
        
        this.elements.paginationContainer.innerHTML = '';
        
        if (total_pages <= 1) {
            return; // No pagination needed for 1 or fewer pages
        }
        
        // Previous button
        const prevButton = document.createElement('a');
        prevButton.className = `pagination-link ${current_page <= 1 ? 'disabled' : ''}`;
        prevButton.dataset.page = 'prev';
        prevButton.textContent = '« Previous';
        this.elements.paginationContainer.appendChild(prevButton);
        
        // Page numbers (limit to avoid too many page links)
        const maxPagesToShow = 7;
        let startPage = Math.max(1, current_page - 3);
        let endPage = Math.min(total_pages, startPage + maxPagesToShow - 1);
        
        // Adjust startPage if we're near the end
        if (endPage - startPage < maxPagesToShow - 1) {
            startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }
        
        // First page link if not already included
        if (startPage > 1) {
            const firstPageLink = document.createElement('a');
            firstPageLink.className = 'pagination-link';
            firstPageLink.dataset.page = '1';
            firstPageLink.textContent = '1';
            this.elements.paginationContainer.appendChild(firstPageLink);
            
            // Ellipsis if there's a gap
            if (startPage > 2) {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'pagination-ellipsis';
                ellipsis.textContent = '...';
                this.elements.paginationContainer.appendChild(ellipsis);
            }
        }
        
        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            const pageLink = document.createElement('a');
            pageLink.className = `pagination-link ${i === current_page ? 'active' : ''}`;
            pageLink.dataset.page = i.toString();
            pageLink.textContent = i.toString();
            this.elements.paginationContainer.appendChild(pageLink);
        }
        
        // Last page link if not already included
        if (endPage < total_pages) {
            // Ellipsis if there's a gap
            if (endPage < total_pages - 1) {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'pagination-ellipsis';
                ellipsis.textContent = '...';
                this.elements.paginationContainer.appendChild(ellipsis);
            }
            
            const lastPageLink = document.createElement('a');
            lastPageLink.className = 'pagination-link';
            lastPageLink.dataset.page = total_pages.toString();
            lastPageLink.textContent = total_pages.toString();
            this.elements.paginationContainer.appendChild(lastPageLink);
        }
        
        // Next button
        const nextButton = document.createElement('a');
        nextButton.className = `pagination-link ${current_page >= total_pages ? 'disabled' : ''}`;
        nextButton.dataset.page = 'next';
        nextButton.textContent = 'Next »';
        this.elements.paginationContainer.appendChild(nextButton);
    }
    
    /**
     * Update search results summary
     * @param {object} searchInfo - Search information
     */
    updateSearchSummary(searchInfo) {
        if (!searchInfo || !searchInfo.pagination) {
            this.elements.summaryContainer.innerHTML = '';
            return;
        }
        
        const {pagination, query, search_sites, debug_info} = searchInfo;
        
        // Format site names for display (limit to first 3 if there are many)
        const sitesText = search_sites.length > 3 ? 
            `${search_sites.slice(0, 3).join(', ')} and ${search_sites.length - 3} more sites` : 
            search_sites.join(', ');
        
        // Show cached indicator if results came from cache
        const cachedText = debug_info.cached ? 
            '<span class="cached-result">Results from cache</span>' : '';
        
        this.elements.summaryContainer.innerHTML = `
            <h3>Search Results</h3>
            <p>Found ${pagination.total_valid_results} results for "${query}" from ${sitesText}. ${cachedText}</p>
            <p class="search-time">Search completed in ${debug_info.time_taken_s} seconds.</p>
            <p class="page-info">Showing page ${pagination.current_page} of ${pagination.total_pages}.</p>
        `;
    }
    
    /**
     * Update the list of active players
     */
    updatePlayersList() {
        if (!window.playerManager) {
            this.elements.activePlayersList.innerHTML = '<p>Player manager not available</p>';
            return;
        }
        
        const activePlayers = window.playerManager.getActivePlayers();
        
        if (activePlayers.length === 0) {
            this.elements.activePlayersList.innerHTML = 
                '<p>No active players. Use "Send to Player" buttons to load videos.</p>';
            return;
        }
        
        this.elements.activePlayersList.innerHTML = '';
        
        activePlayers.forEach(player => {
            const playerItem = document.createElement('div');
            playerItem.className = 'active-player-item';
            
            // Extract player number from ID
            const playerNumber = player.id.split('-')[1];
            
            playerItem.innerHTML = `
                <span class="player-number">#${playerNumber}</span>
                <span class="player-title">${player.title || 'Untitled Video'}</span>
                <button class="button small" onclick="uiManager.closePlayer('${player.id}')">Close</button>
            `;
            
            this.elements.activePlayersList.appendChild(playerItem);
        });
    }
}

// Create and export a singleton instance
const uiManager = new UIManager();

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    uiManager.setupEventListeners();
});

// Make available globally
window.uiManager = uiManager;