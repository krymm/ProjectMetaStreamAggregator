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
        
        // Default Search Sites
        this.elements.defaultSitesListContainer = document.getElementById('default-sites-list-container');

        // Ollama Test
        this.elements.testOllamaConnectionButton = document.getElementById('test-ollama-connection');
        this.elements.ollamaTestStatus = document.getElementById('ollama-test-status');

        // Ollama Models
        this.elements.ollamaModelSelect = document.getElementById('ollama-model-select');
        this.elements.refreshOllamaModelsButton = document.getElementById('refresh-ollama-models');
        this.elements.ollamaModelsStatus = document.getElementById('ollama-models-status');

        // Site Configuration Management Elements
        this.elements.siteConfigSelect = document.getElementById('site-config-select');
        this.elements.siteConfigAddNewBtn = document.getElementById('site-config-add-new-btn');
        this.elements.siteConfigDeleteBtn = document.getElementById('site-config-delete-btn');
        this.elements.siteConfigForm = document.getElementById('site-config-form');
        this.elements.siteConfigOriginalKey = document.getElementById('site-config-original-key');
        this.elements.siteConfigSaveBtn = document.getElementById('site-config-save-btn'); // Already in form, but good to have direct ref if needed
        this.elements.siteConfigStatus = document.getElementById('site-config-status');
        
        // Individual form fields for site config (add more as needed for specific logic like visibility)
        this.elements.siteConfigSearchMethod = document.getElementById('site-config-search-method');
        this.elements.siteConfigName = document.getElementById('site-config-name');

        // Site Config Field Groups
        this.elements.siteConfigCommonSelectorsGroup = document.getElementById('site-config-common-selectors-group');
        this.elements.siteConfigScrapeSpecificGroup = document.getElementById('site-config-scrape-specific-group');
        this.elements.siteConfigApiSpecificGroup = document.getElementById('site-config-api-specific-group');
        this.elements.siteConfigSearchEngineInfoGroup = document.getElementById('site-config-search-engine-info-group');

        // Backup and Restore Elements
        this.elements.backupConfigBtn = document.getElementById('backup-config-btn');
        this.elements.restoreConfigFile = document.getElementById('restore-config-file');
        this.elements.restoreConfigUploadBtn = document.getElementById('restore-config-upload-btn');
        this.elements.restoreConfigStatus = document.getElementById('restore-config-status');
    }

    toggleSiteFormFieldVisibility(searchMethod) {
        // Helper to show/hide an element or group of elements
        const setVisible = (element, isVisible) => {
            if (element) {
                if (Array.isArray(element)) {
                    element.forEach(el => el.style.display = isVisible ? '' : 'none');
                } else {
                    element.style.display = isVisible ? '' : 'none';
                }
            }
        };

        // Hide all optional groups initially
        setVisible(this.elements.siteConfigCommonSelectorsGroup, false);
        setVisible(this.elements.siteConfigScrapeSpecificGroup, false);
        setVisible(this.elements.siteConfigApiSpecificGroup, false);
        setVisible(this.elements.siteConfigSearchEngineInfoGroup, false);

        // Show groups based on search method
        if (searchMethod === 'scrape_search_page') {
            setVisible(this.elements.siteConfigCommonSelectorsGroup, true);
            setVisible(this.elements.siteConfigScrapeSpecificGroup, true);
        } else if (searchMethod === 'api') {
            setVisible(this.elements.siteConfigCommonSelectorsGroup, true); // Common selectors might be used as fallbacks
            setVisible(this.elements.siteConfigApiSpecificGroup, true);
        } else if (['google_site_search', 'bing_site_search', 'duckduckgo_site_search'].includes(searchMethod)) {
            setVisible(this.elements.siteConfigCommonSelectorsGroup, true); // For extended detail scraping
            setVisible(this.elements.siteConfigSearchEngineInfoGroup, true);
        }
        // If no specific group matches, all optional groups remain hidden. Only basic fields will show.
    }

    async loadSitesForEditing() {
        if (!this.elements.siteConfigSelect) return;

        try {
            const response = await fetch('/api/sites');
            if (!response.ok) {
                throw new Error(`Failed to load sites: ${response.status}`);
            }
            this.currentSiteConfigs = await response.json(); // Store for later use
            
            this.elements.siteConfigSelect.innerHTML = '<option value="">-- Select a Site to Edit or Add New --</option>'; // Default option
            
            for (const key in this.currentSiteConfigs) {
                const site = this.currentSiteConfigs[key];
                const option = document.createElement('option');
                option.value = key;
                option.textContent = site.name || key; // Use name, fallback to key
                this.elements.siteConfigSelect.appendChild(option);
            }

            // Reset form and button states
            this.resetSiteConfigForm(); // Clear form fields
            this.elements.siteConfigDeleteBtn.disabled = true;
            if (this.elements.siteConfigStatus) this.elements.siteConfigStatus.textContent = '';

        } catch (error) {
            console.error('Error loading sites for editing:', error);
            if (this.elements.siteConfigStatus) {
                this.elements.siteConfigStatus.textContent = `Error loading sites: ${error.message}`;
                this.elements.siteConfigStatus.className = 'status-message error';
            }
            this.elements.siteConfigSelect.innerHTML = '<option value="">Error loading sites</option>';
            this.currentSiteConfigs = {}; // Reset
        }
    }

    resetSiteConfigForm() {
        if (this.elements.siteConfigForm) {
            this.elements.siteConfigForm.reset(); // Resets all form fields
        }
        if (this.elements.siteConfigOriginalKey) {
            this.elements.siteConfigOriginalKey.value = ''; // Clear hidden key
        }
        if (this.elements.siteConfigName) { // Example: enable name field for add mode
            this.elements.siteConfigName.disabled = false; 
        }
        // Set a default search method and trigger visibility update
        const defaultSearchMethod = 'scrape_search_page';
        if (this.elements.siteConfigSearchMethod) {
            this.elements.siteConfigSearchMethod.value = defaultSearchMethod;
        }
        this.toggleSiteFormFieldVisibility(defaultSearchMethod);
        if (this.elements.siteConfigStatus) this.elements.siteConfigStatus.textContent = '';
        if (this.elements.siteConfigDeleteBtn) this.elements.siteConfigDeleteBtn.disabled = true;
        if (this.elements.siteConfigSaveBtn) this.elements.siteConfigSaveBtn.textContent = 'Save Site Configuration';

        // Set default popularity multiplier
        const popularityInput = document.getElementById('site-config-popularity');
        if (popularityInput) popularityInput.value = '1.0';

        // Clear all API mapping fields
        const apiMappingFields = ['api_title_field', 'api_url_field', 'api_thumbnail_field', 'api_duration_field', 'api_rating_field', 'api_views_field', 'api_author_field'];
        apiMappingFields.forEach(fieldId => {
            const fieldElement = document.getElementById(`site-config-${fieldId}`);
            if (fieldElement) fieldElement.value = '';
        });
         // Clear API specific fields
        const apiSpecificFields = ['api_url_template', 'api_key', 'api_key_param', 'api_results_path'];
        apiSpecificFields.forEach(fieldId => {
            const fieldElement = document.getElementById(`site-config-${fieldId}`);
            if (fieldElement) fieldElement.value = '';
        });

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

    async handleRefreshOllamaModels() {
        const ollamaUrlInput = document.getElementById('ollama-api-url');
        const ollamaUrl = ollamaUrlInput ? ollamaUrlInput.value.trim() : null;

        if (!this.elements.ollamaModelsStatus || !this.elements.ollamaModelSelect) {
            console.error("Ollama models status or select element not found in cacheElements.");
            return;
        }

        if (!ollamaUrl) {
            this.elements.ollamaModelsStatus.textContent = 'Please enter an Ollama API URL first.';
            this.elements.ollamaModelsStatus.className = 'test-status error';
            this.populateOllamaModelsDropdown([], null); // Clear dropdown
            return;
        }

        this.elements.ollamaModelsStatus.textContent = 'Refreshing models...';
        this.elements.ollamaModelsStatus.className = 'test-status testing';

        try {
            const response = await fetch('/api/ollama/models', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ ollama_api_url: ollamaUrl }),
            });

            const result = await response.json();

            if (result.success) {
                // Use this.currentOllamaModel if available (set in openSettingsModal), 
                // otherwise, try to preserve the current selection in the dropdown.
                const modelToSelect = this.currentOllamaModel || this.elements.ollamaModelSelect.value;
                this.populateOllamaModelsDropdown(result.models, modelToSelect);
                this.elements.ollamaModelsStatus.textContent = result.models.length > 0 ? 'Models refreshed.' : 'No models found at this URL.';
                this.elements.ollamaModelsStatus.className = result.models.length > 0 ? 'test-status success' : 'test-status info';
                // Clear this.currentOllamaModel after it has been used to populate the dropdown
                if (this.currentOllamaModel) {
                    this.currentOllamaModel = null; 
                }
            } else {
                this.elements.ollamaModelsStatus.textContent = result.message || 'Failed to refresh models.';
                this.elements.ollamaModelsStatus.className = 'test-status error';
                this.populateOllamaModelsDropdown([], null); // Clear dropdown on failure
            }
        } catch (error) {
            console.error('Error refreshing Ollama models:', error);
            this.elements.ollamaModelsStatus.textContent = 'Failed to refresh models. Check network or console.';
            this.elements.ollamaModelsStatus.className = 'test-status error';
            this.populateOllamaModelsDropdown([], null); // Clear dropdown on error
        }
    }

    populateOllamaModelsDropdown(models, selectedModel) {
        if (!this.elements.ollamaModelSelect) {
            console.error("Ollama model select element not found in cacheElements.");
            return;
        }
        this.elements.ollamaModelSelect.innerHTML = ''; // Clear existing options

        if (models && models.length > 0) {
            models.forEach(modelName => {
                const option = document.createElement('option');
                option.value = modelName;
                option.textContent = modelName;
                if (modelName === selectedModel) {
                    option.selected = true;
                }
                this.elements.ollamaModelSelect.appendChild(option);
            });
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No models found (Refresh or check URL)';
            this.elements.ollamaModelSelect.appendChild(option);
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

        // Ollama Test Connection Button
        if (this.elements.testOllamaConnectionButton) {
            this.elements.testOllamaConnectionButton.addEventListener('click', () => {
                this.handleTestOllamaConnection();
            });
        }

        // Ollama Refresh Models Button
        if (this.elements.refreshOllamaModelsButton) {
            this.elements.refreshOllamaModelsButton.addEventListener('click', () => {
                this.handleRefreshOllamaModels();
            });
        }

        // Site Configuration Select Change
        if (this.elements.siteConfigSelect) {
            this.elements.siteConfigSelect.addEventListener('change', (e) => {
                const selectedSiteKey = e.target.value;
                if (selectedSiteKey && this.currentSiteConfigs && this.currentSiteConfigs[selectedSiteKey]) {
                    this.populateSiteConfigForm(this.currentSiteConfigs[selectedSiteKey], selectedSiteKey);
                    this.elements.siteConfigDeleteBtn.disabled = false;
                    if (this.elements.siteConfigName) this.elements.siteConfigName.disabled = false; 
                    if (this.elements.siteConfigSaveBtn) this.elements.siteConfigSaveBtn.textContent = 'Update Selected Site';
                } else {
                    this.resetSiteConfigForm(); 
                    this.elements.siteConfigDeleteBtn.disabled = true;
                    if (this.elements.siteConfigSaveBtn) this.elements.siteConfigSaveBtn.textContent = 'Save New Site';
                }
            });
        }

        // Site Configuration Search Method Change
        if (this.elements.siteConfigSearchMethod) {
            this.elements.siteConfigSearchMethod.addEventListener('change', (e) => {
                this.toggleSiteFormFieldVisibility(e.target.value);
            });
        }

        // Site Configuration "Add New Site" Button
        if (this.elements.siteConfigAddNewBtn) {
            this.elements.siteConfigAddNewBtn.addEventListener('click', () => {
                this.elements.siteConfigSelect.value = ''; // Deselect any selected site
                this.resetSiteConfigForm(); // Clear form and set default visibility
                if (this.elements.siteConfigName) this.elements.siteConfigName.focus();
                if (this.elements.siteConfigStatus) this.elements.siteConfigStatus.textContent = 'Adding new site. Fill in the details below.';
                this.elements.siteConfigStatus.className = 'status-message info';
                this.elements.siteConfigDeleteBtn.disabled = true;
                if (this.elements.siteConfigSaveBtn) this.elements.siteConfigSaveBtn.textContent = 'Save New Site';
            });
        }

        // Site Configuration "Delete Selected Site" Button
        if (this.elements.siteConfigDeleteBtn) {
            this.elements.siteConfigDeleteBtn.addEventListener('click', async () => {
                const siteKey = this.elements.siteConfigOriginalKey.value;
                if (!siteKey) {
                    if (this.elements.siteConfigStatus) {
                        this.elements.siteConfigStatus.textContent = 'No site selected to delete.';
                        this.elements.siteConfigStatus.className = 'status-message error';
                    }
                    return;
                }

                const siteNameToDelete = this.currentSiteConfigs[siteKey]?.name || siteKey;
                if (!confirm(`Are you sure you want to delete the site: "${siteNameToDelete}"? This action cannot be undone.`)) {
                    return;
                }

                if (this.elements.siteConfigStatus) {
                    this.elements.siteConfigStatus.textContent = `Deleting ${siteNameToDelete}...`;
                    this.elements.siteConfigStatus.className = 'status-message info';
                }

                try {
                    const response = await fetch(`/api/sites/${siteKey}`, { method: 'DELETE' });
                    const result = await response.json(); // Expect JSON response even for DELETE

                    if (response.ok) {
                        if (this.elements.siteConfigStatus) {
                            this.elements.siteConfigStatus.textContent = result.message || `Site "${siteNameToDelete}" deleted successfully.`;
                            this.elements.siteConfigStatus.className = 'status-message success';
                        }
                        await this.loadSitesForEditing(); // Reload dropdown and reset form
                        if (window.app && typeof window.app.loadAndDisplaySites === 'function') {
                            window.app.loadAndDisplaySites(); // Refresh main site list
                        }
                    } else {
                        throw new Error(result.error || `Failed to delete site (status ${response.status})`);
                    }
                } catch (error) {
                    console.error('Error deleting site:', error);
                    if (this.elements.siteConfigStatus) {
                        this.elements.siteConfigStatus.textContent = `Error deleting site: ${error.message}`;
                        this.elements.siteConfigStatus.className = 'status-message error';
                    }
                }
            });
        }

        // Site Configuration Form Submit (Save/Update)
        if (this.elements.siteConfigForm) {
            this.elements.siteConfigForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(this.elements.siteConfigForm);
                const siteData = {};
                const originalSiteKey = this.elements.siteConfigOriginalKey.value;

                // Populate siteData from formData
                for (let [key, value] of formData.entries()) {
                    if (key === 'original_site_key') continue; // Skip this internal field

                    // Convert popularity_multiplier to float, clear if empty
                    if (key === 'popularity_multiplier') {
                        value = value.trim() === '' ? null : parseFloat(value);
                    }
                    // For other numeric fields, you might add similar parsing if they can be empty
                    // For optional text fields, send null if empty, or just let backend handle empty strings if preferred
                    if (typeof value === 'string' && value.trim() === '' && !['name', 'base_url', 'search_method'].includes(key) ) { // Keep required fields as is for backend validation
                        siteData[key] = null; // Send null for empty optional fields
                    } else {
                         siteData[key] = value;
                    }
                }
                
                // Ensure required fields are not accidentally nulled if form validation fails on frontend
                if (!siteData.name) siteData.name = ''; // Let backend validate required
                if (!siteData.base_url) siteData.base_url = '';
                if (!siteData.search_method) siteData.search_method = 'scrape_search_page';


                const isUpdating = originalSiteKey && originalSiteKey !== '';
                const url = isUpdating ? `/api/sites/${originalSiteKey}` : '/api/sites';
                const method = isUpdating ? 'PUT' : 'POST';

                if (this.elements.siteConfigStatus) {
                    this.elements.siteConfigStatus.textContent = `${isUpdating ? 'Updating' : 'Creating'} site...`;
                    this.elements.siteConfigStatus.className = 'status-message info';
                }
                
                try {
                    const response = await fetch(url, {
                        method: method,
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(siteData)
                    });
                    const result = await response.json();

                    if (response.ok) {
                        if (this.elements.siteConfigStatus) {
                            this.elements.siteConfigStatus.textContent = result.message || `Site ${isUpdating ? 'updated' : 'created'} successfully.`;
                            this.elements.siteConfigStatus.className = 'status-message success';
                        }
                        await this.loadSitesForEditing(); // Reload sites list
                        // If creating new, select it. If updating, re-select it.
                        const newSiteKey = result.site_key || originalSiteKey;
                        if (newSiteKey && this.elements.siteConfigSelect) {
                             this.elements.siteConfigSelect.value = newSiteKey;
                             // Manually trigger change to re-populate form if needed, or call populate directly
                             this.populateSiteConfigForm(this.currentSiteConfigs[newSiteKey], newSiteKey);
                             this.elements.siteConfigDeleteBtn.disabled = false;
                        }
                        if (window.app && typeof window.app.loadAndDisplaySites === 'function') {
                             window.app.loadAndDisplaySites(); // Refresh main site list
                        }
                    } else {
                        let errorMessage = result.error || `Failed to ${isUpdating ? 'update' : 'create'} site.`;
                        if (result.messages && Array.isArray(result.messages)) {
                            errorMessage += ` Details: ${result.messages.join('; ')}`;
                        }
                        throw new Error(errorMessage);
                    }
                } catch (error) {
                    console.error(`Error ${isUpdating ? 'updating' : 'creating'} site:`, error);
                    if (this.elements.siteConfigStatus) {
                        this.elements.siteConfigStatus.textContent = `Error: ${error.message}`;
                        this.elements.siteConfigStatus.className = 'status-message error';
                    }
                }
            });
        }

        // Backup and Restore Event Listeners
        if (this.elements.backupConfigBtn) {
            this.elements.backupConfigBtn.addEventListener('click', () => {
                this.handleBackupConfig();
            });
        }
        if (this.elements.restoreConfigUploadBtn) {
            this.elements.restoreConfigUploadBtn.addEventListener('click', () => {
                this.handleRestoreConfig();
            });
        }
        
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

    async handleTestOllamaConnection() {
        const ollamaUrlInput = document.getElementById('ollama-api-url'); // Assuming this is the correct ID from cacheElements
        const ollamaUrl = ollamaUrlInput.value.trim();
        
        if (!this.elements.ollamaTestStatus) {
            console.error("Ollama test status element not found in cacheElements.");
            return;
        }

        if (!ollamaUrl) {
            this.elements.ollamaTestStatus.textContent = 'Please enter an Ollama API URL.';
            this.elements.ollamaTestStatus.className = 'test-status error'; // Add error class
            return;
        }

        this.elements.ollamaTestStatus.textContent = 'Testing...';
        this.elements.ollamaTestStatus.className = 'test-status testing'; // Add testing class

        try {
            const response = await fetch('/api/ollama/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ ollama_api_url: ollamaUrl }),
            });

            const result = await response.json();

            if (result.success) {
                this.elements.ollamaTestStatus.textContent = result.message || 'Connection successful!';
                this.elements.ollamaTestStatus.className = 'test-status success';
            } else {
                this.elements.ollamaTestStatus.textContent = result.message || 'Connection failed.';
                this.elements.ollamaTestStatus.className = 'test-status error';
            }
        } catch (error) {
            console.error('Error testing Ollama connection:', error);
            this.elements.ollamaTestStatus.textContent = 'Failed to test connection. Check network or console.';
            this.elements.ollamaTestStatus.className = 'test-status error';
        }
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

    handleBackupConfig() {
        // Simply redirecting to the backup URL will trigger the download
        if (this.elements.restoreConfigStatus) { // Use restoreConfigStatus for messages related to backup/restore section
            this.elements.restoreConfigStatus.textContent = 'Preparing backup file for download...';
            this.elements.restoreConfigStatus.className = 'status-message info';
        }
        
        window.location.href = '/api/config/backup';

        // Clear the message after a short delay, as there's no direct success/error callback for file downloads this way.
        setTimeout(() => {
            if (this.elements.restoreConfigStatus && this.elements.restoreConfigStatus.textContent === 'Preparing backup file for download...') {
                this.elements.restoreConfigStatus.textContent = 'If download did not start, check server logs.';
                this.elements.restoreConfigStatus.className = 'status-message info';
            }
        }, 5000); // 5 seconds
    }

    async handleRestoreConfig() {
        if (!this.elements.restoreConfigFile || !this.elements.restoreConfigStatus) {
            console.error("Restore elements not found in cache.");
            return;
        }

        const file = this.elements.restoreConfigFile.files[0];
        this.elements.restoreConfigStatus.textContent = ''; // Clear previous status
        this.elements.restoreConfigStatus.className = 'status-message';


        if (!file) {
            this.elements.restoreConfigStatus.textContent = 'Please select a backup file to restore.';
            this.elements.restoreConfigStatus.className = 'status-message error';
            return;
        }

        if (!file.name.endsWith('.json')) {
            this.elements.restoreConfigStatus.textContent = 'Invalid file type. Please select a .json backup file.';
            this.elements.restoreConfigStatus.className = 'status-message error';
            return;
        }

        this.elements.restoreConfigStatus.textContent = 'Restoring configuration...';
        this.elements.restoreConfigStatus.className = 'status-message info';

        const formData = new FormData();
        formData.append('backup_file', file);

        try {
            const response = await fetch('/api/config/restore', {
                method: 'POST',
                body: formData,
                // 'Content-Type' header is automatically set by browser for FormData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.elements.restoreConfigStatus.textContent = result.message || 'Configuration restored successfully! Please close and reopen settings, or refresh the page.';
                this.elements.restoreConfigStatus.className = 'status-message success';
                
                // Suggest refreshing or automatically re-initialize settings related UI
                // For now, just a message. A more advanced approach would be to re-fetch settings
                // and update all relevant UI parts, or even trigger a full app state reload.
                alert(result.message + "\n\nThe application settings will now be reloaded. You may need to reopen the settings panel.");
                
                // Close and reopen settings modal to reflect changes (or parts of it)
                // This is a simple way to refresh the settings displayed.
                this.closeSettingsModal(); 
                // Re-fetch and apply settings globally (if App class handles this)
                if (window.app && typeof window.app.loadSettings === 'function') {
                    await window.app.loadSettings(); // Assuming app.js has a method to reload settings
                }
                 // Re-load site configurations for editing, as they might have changed
                await this.loadSitesForEditing();
                // Reload site list on main page
                if (window.app && typeof window.app.loadAndDisplaySites === 'function') {
                    window.app.loadAndDisplaySites();
                }


            } else {
                throw new Error(result.message || `Failed to restore configuration (status ${response.status})`);
            }
        } catch (error) {
            console.error('Error restoring configuration:', error);
            this.elements.restoreConfigStatus.textContent = `Error: ${error.message}`;
            this.elements.restoreConfigStatus.className = 'status-message error';
        } finally {
            // Clear the file input regardless of outcome
            this.elements.restoreConfigFile.value = '';
        }
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
            const ollamaApiUrlField = document.getElementById('ollama-api-url');
            if (ollamaApiUrlField) {
                ollamaApiUrlField.value = settings.ollama_api_url || '';
            }
            
            if (this.elements.ollamaTestStatus) { // Clear previous test status
                this.elements.ollamaTestStatus.textContent = '';
                this.elements.ollamaTestStatus.className = 'test-status'; // Reset class
            }
            if (this.elements.ollamaModelsStatus) { // Clear previous models status
                this.elements.ollamaModelsStatus.textContent = '';
                this.elements.ollamaModelsStatus.className = 'test-status';
            }

            // Store current model from settings to attempt to preserve selection after refresh
            this.currentOllamaModel = settings.ollama_model || null; 
            // Fetch and populate models. This will use this.currentOllamaModel for selection.
            this.handleRefreshOllamaModels(); 

            // --- Populate Default Search Sites ---
            // (This part was already correctly implemented in a previous step)


            // --- Site Configuration Section ---
            this.loadSitesForEditing(); // Load sites into the dropdown
            // Initial state for site config form (usually hidden/disabled until selection or "Add New")
            this.resetSiteConfigForm(); // Ensure form is clear and visibility is default
            if(this.elements.siteConfigDeleteBtn) this.elements.siteConfigDeleteBtn.disabled = true;
            if(this.elements.siteConfigForm) this.elements.siteConfigForm.style.display = 'block'; // Or some initial state
            if(this.elements.siteConfigStatus) this.elements.siteConfigStatus.textContent = 'Select a site to edit or click "Add New Site".';

            // --- Backup and Restore Section ---
            if (this.elements.restoreConfigStatus) {
                this.elements.restoreConfigStatus.textContent = '';
                this.elements.restoreConfigStatus.className = 'status-message';
            }
            if (this.elements.restoreConfigFile) {
                this.elements.restoreConfigFile.value = ''; // Clear selected file
            }


            // --- Populate Default Search Sites ---
            try {
                const sitesResponse = await fetch('/api/sites');
                if (!sitesResponse.ok) {
                    throw new Error(`Failed to load sites list: ${sitesResponse.status}`);
                }
                const availableSites = await sitesResponse.json();
                
                this.elements.defaultSitesListContainer.innerHTML = ''; // Clear previous checkboxes

                if (availableSites && availableSites.length > 0) {
                    const currentDefaultSites = settings.default_search_sites || [];
                    availableSites.forEach(site => {
                        const checkboxId = `default-site-${site.name.replace(/\s+/g, '-')}`; // Sanitize name for ID
                        const checkbox = document.createElement('input');
                        checkbox.type = 'checkbox';
                        checkbox.id = checkboxId;
                        checkbox.name = 'default_search_sites'; // Group checkboxes
                        checkbox.value = site.name;
                        
                        if (currentDefaultSites.includes(site.name)) {
                            checkbox.checked = true;
                        }

                        const label = document.createElement('label');
                        label.htmlFor = checkboxId;
                        label.textContent = site.name;

                        const div = document.createElement('div');
                        div.classList.add('checkbox-item'); // For styling if needed
                        div.appendChild(checkbox);
                        div.appendChild(label);
                        this.elements.defaultSitesListContainer.appendChild(div);
                    });
                } else {
                    this.elements.defaultSitesListContainer.innerHTML = '<p>No sites available or error fetching sites.</p>';
                }
            } catch (sitesError) {
                console.error('Error loading available sites for settings:', sitesError);
                this.elements.defaultSitesListContainer.innerHTML = '<p>Error loading sites list. Please try again.</p>';
            }
            // --- End Populate Default Search Sites ---
            
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
            // Skip default_search_sites, will be handled separately
            if (key === 'default_search_sites') continue; 
            
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

        // Collect selected default_search_sites specifically as an array
        const defaultSitesCheckboxes = document.querySelectorAll('#settings-form input[name="default_search_sites"]:checked');
        settingsData.default_search_sites = Array.from(defaultSitesCheckboxes).map(cb => cb.value);
        
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
            const ollamaApiUrlFieldDefault = document.getElementById('ollama-api-url');
            if (ollamaApiUrlFieldDefault) {
                 ollamaApiUrlFieldDefault.value = defaultSettings.ollama_api_url || '';
            }
           

            // Set the default model in the dropdown
            // The dropdown should be populated by handleRefreshOllamaModels if the URL is valid
            if (this.elements.ollamaModelSelect) {
                 this.elements.ollamaModelSelect.value = defaultSettings.ollama_model || '';
            }
            // Store the default model to be selected after refresh
            this.currentOllamaModel = defaultSettings.ollama_model || null; // Store before refresh
            
            // Refresh models based on potentially changed (default) URL
            // This will populate the dropdown and attempt to select this.currentOllamaModel
            this.handleRefreshOllamaModels().then(() => {
                // After models are populated and potentially selected by handleRefreshOllamaModels,
                // ensure the default model is explicitly set if it wasn't selected by the refresh logic
                // (e.g., if URL was empty and refresh didn't run, or if model wasn't in list)
                if (this.elements.ollamaModelSelect) {
                     // If currentOllamaModel was used by refresh, it's now null.
                     // If refresh didn't run (e.g. no URL), we still want to set the default model name.
                    this.elements.ollamaModelSelect.value = defaultSettings.ollama_model || '';
                }
            });


            // Update default_search_sites checkboxes
            // This assumes that openSettingsModal has already been called at least once to populate the checkboxes
            // or that the site list is relatively static and checkboxes are already in the DOM.
            // If defaultSitesListContainer is empty, this won't do anything, which is acceptable
            // as openSettingsModal will populate it correctly when next opened.
            const defaultSites = defaultSettings.default_search_sites || [];
            const checkboxes = this.elements.defaultSitesListContainer.querySelectorAll('input[name="default_search_sites"]');
            if (checkboxes.length > 0) { // Only try to update if checkboxes are present
                checkboxes.forEach(checkbox => {
                    checkbox.checked = defaultSites.includes(checkbox.value);
                });
            } else {
                // If checkboxes are not yet populated (e.g., settings modal never opened),
                // this part will be handled when openSettingsModal is next called, as it uses
                // the global settings which would be updated after a save.
                // For reset, we are just changing the form values, not saving yet.
                console.warn("Default sites checkboxes not found during reset. They will be populated when settings modal is opened.");
            }
            
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