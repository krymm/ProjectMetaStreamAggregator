// static/js/site-config-manager.js

document.addEventListener('DOMContentLoaded', () => {
    // Main entry point for site config management UI
    const manageSitesBtn = document.getElementById('manageSitesBtn');
    const siteConfigView = document.getElementById('siteConfigView');

    if (manageSitesBtn && siteConfigView) {
        manageSitesBtn.addEventListener('click', () => {
            siteConfigView.style.display = siteConfigView.style.display === 'block' ? 'none' : 'block';
            if (siteConfigView.style.display === 'block') {
                loadAndDisplaySites();
            }
        });
    } else {
        console.warn("Site config management UI elements (manageSitesBtn or siteConfigView) not found.");
        return;
    }

    initializeSiteConfigView();
});

let currentSites = {}; // To store loaded site configurations { site_key: config_object }

function initializeSiteConfigView() {
    const view = document.getElementById('siteConfigView');
    if (!view) return;

    const closeBtn = view.querySelector('#closeSiteConfigViewBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            view.style.display = 'none';
            const formContainer = document.getElementById('siteFormContainer');
            if (formContainer) {
                formContainer.innerHTML = ''; // Clear form when closing view
                formContainer.style.display = 'none';
            }
        });
    }

    const addNewSiteBtn = view.querySelector('#addNewSiteBtn');
    if (addNewSiteBtn) {
        addNewSiteBtn.addEventListener('click', () => {
            openSiteForm();
        });
    }
}

async function loadAndDisplaySites() {
    const sitesListContainer = document.getElementById('sitesListContainer');
    if (!sitesListContainer) {
        console.error("sitesListContainer not found.");
        return;
    }
    sitesListContainer.innerHTML = '<p>Loading sites...</p>';

    try {
        const response = await fetch('/api/sites');
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP error ${response.status}` }));
            throw new Error(errorData.error || `Failed to fetch sites: ${response.status} ${response.statusText}`);
        }
        currentSites = await response.json();
        renderSitesList(currentSites, sitesListContainer);
    } catch (error) {
        console.error("Error loading sites:", error);
        sitesListContainer.innerHTML = `<p class="error-message">Error loading sites: ${error.message}</p>`;
        showNotification(`Error loading sites: ${error.message}`, 'error');
    }
}

function renderSitesList(sites, container) {
    container.innerHTML = '';

    if (Object.keys(sites).length === 0) {
        container.innerHTML = '<p>No sites configured yet. Click "Add New Site" to begin.</p>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'sites-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Name (Key)</th>
                <th>Base URL</th>
                <th>Search Method</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;
    const tbody = table.querySelector('tbody');

    for (const siteKey in sites) {
        const site = sites[siteKey];
        const tr = document.createElement('tr');
        tr.className = 'site-item';
        tr.innerHTML = `
            <td><strong>${site.name || 'Unnamed Site'}</strong><br><small>(${siteKey})</small></td>
            <td>${site.base_url || ''}</td>
            <td>${site.search_method || 'N/A'}</td>
            <td class="site-actions">
                <button class="edit-site-btn" data-sitekey="${siteKey}">Edit</button>
                <button class="delete-site-btn" data-sitekey="${siteKey}" data-sitename="${site.name || siteKey}">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    }
    container.appendChild(table);

    container.querySelectorAll('.edit-site-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const siteKey = e.target.dataset.sitekey;
            openSiteForm(currentSites[siteKey], siteKey);
        });
    });

    container.querySelectorAll('.delete-site-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const siteKey = e.target.dataset.sitekey;
            const siteName = e.target.dataset.sitename;
            if (confirm(`Are you sure you want to delete site: ${siteName} (${siteKey})?`)) {
                deleteSite(siteKey);
            }
        });
    });
}

function openSiteForm(siteData = null, siteKey = null) {
    const formContainer = document.getElementById('siteFormContainer');
    if (!formContainer) {
        console.error("siteFormContainer not found!");
        return;
    }

    formContainer.innerHTML = createSiteFormHTML(siteData, siteKey);
    formContainer.style.display = 'block';

    const siteForm = formContainer.querySelector('#siteConfigForm');
    const searchMethodSelect = siteForm.querySelector('#search_method');

    function toggleConditionalFields() {
        const selectedMethod = searchMethodSelect.value;
        siteForm.querySelectorAll('.conditional-fields').forEach(section => section.style.display = 'none');
        if (selectedMethod === 'scrape_search_page') {
            siteForm.querySelector('#scrapeFields').style.display = 'block';
        } else if (selectedMethod === 'api') {
            siteForm.querySelector('#apiFields').style.display = 'block';
        }
        // Always show video page detail selectors as they can be used by fetch_extended_details for any site type
        siteForm.querySelector('#videoPageDetailSelectors').style.display = 'block';
    }

    if (searchMethodSelect) {
         searchMethodSelect.addEventListener('change', toggleConditionalFields);
         toggleConditionalFields();
    }

    const overrideWeightsCheckbox = siteForm.querySelector('#override_global_scoring_weights');
    const perSiteWeightsSection = siteForm.querySelector('#perSiteScoringWeights');
    if (overrideWeightsCheckbox && perSiteWeightsSection) {
        overrideWeightsCheckbox.addEventListener('change', () => {
            perSiteWeightsSection.style.display = overrideWeightsCheckbox.checked ? 'block' : 'none';
        });
        perSiteWeightsSection.style.display = overrideWeightsCheckbox.checked ? 'block' : 'none';
    }

    siteForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(siteForm);
        const config = {};

        config.name = formData.get('name');
        config.base_url = formData.get('base_url');
        config.search_method = formData.get('search_method');
        config.popularity_multiplier = parseFloat(formData.get('popularity_multiplier')) || 1.0;

        if (config.search_method === 'scrape_search_page') {
            config.search_url_template = formData.get('search_url_template') || null;
            config.results_container_selector = formData.get('results_container_selector') || null;
            config.result_item_selector = formData.get('result_item_selector') || null;
            config.title_selector = formData.get('title_selector') || null;
            config.video_url_selector = formData.get('video_url_selector') || null;
            config.thumbnail_selector = formData.get('thumbnail_selector') || null;
            config.next_page_selector = formData.get('next_page_selector') || null;
        } else if (config.search_method === 'api') {
            config.api_url_template = formData.get('api_url_template') || null;
            config.api_key = formData.get('api_key') || null;
            config.api_key_param = formData.get('api_key_param') || null;
            config.api_title_field = formData.get('api_title_field') || null;
            config.api_url_field = formData.get('api_url_field') || null;
            config.api_thumbnail_field = formData.get('api_thumbnail_field') || null;
            config.api_duration_field = formData.get('api_duration_field') || null;
            config.api_rating_field = formData.get('api_rating_field') || null;
            config.api_views_field = formData.get('api_views_field') || null;
            config.api_author_field = formData.get('api_author_field') || null;
        }

        // Video Page Detail Selectors (shared keys with scrape_search_page for fetch_extended_details)
        // These will overwrite if scrape_search_page was selected but user wants different ones for detail page
        config.title_selector = formData.get('video_page_title_selector') || config.title_selector; // Keep search page if video page blank
        config.duration_selector = formData.get('video_page_duration_selector') || config.duration_selector;
        config.rating_selector = formData.get('video_page_rating_selector') || config.rating_selector;
        config.views_selector = formData.get('video_page_views_selector') || config.views_selector;
        config.author_selector = formData.get('video_page_author_selector') || config.author_selector;


        if (formData.get('override_global_scoring_weights') === 'on') {
            const relevanceWeight = parseFloat(formData.get('relevance_weight'));
            const ratingWeight = parseFloat(formData.get('rating_weight'));
            const viewsWeight = parseFloat(formData.get('views_weight'));
            const multiplierEffect = parseFloat(formData.get('multiplier_effect'));

            // Basic validation for weights summing to 1 (for the main 3)
            if (Math.abs((relevanceWeight + ratingWeight + viewsWeight) - 1.0) > 0.01 && (relevanceWeight + ratingWeight + viewsWeight !== 0) ) { // allow all zero to mean "use global"
                 showNotification('Error: Relevance, Rating, and Views weights for per-site scoring must sum to 1.0 (or all be 0 to use global).', 'error');
                 return; // Prevent submission
            }

            config.scoring_weights = {
                relevance_weight: relevanceWeight,
                rating_weight: ratingWeight,
                views_weight: viewsWeight,
                multiplier_effect: multiplierEffect,
            };
        } else {
            config.scoring_weights = null;
        }

        for (const key in config) {
            if (config[key] === '') { // Treat empty strings for optional fields as null
                 if (key.includes('_selector') || key.includes('_template') || key.includes('_field') || key.includes('api_key') || key.includes('api_key_param')) {
                    config[key] = null;
                }
            }
        }

        let url = '/api/sites';
        let method = 'POST';

        if (siteKey) {
            url = `/api/sites/${siteKey}`;
            method = 'PUT';
        }

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const result = await response.json();

            if (!response.ok) {
                const errorMsg = result.messages ? result.messages.join(', ') : (result.error || `HTTP error ${response.status}`);
                throw new Error(errorMsg);
            }

            showNotification(`Site ${siteKey ? 'updated' : 'added'} successfully: ${config.name}`, 'success');
            formContainer.style.display = 'none';
            formContainer.innerHTML = '';
            loadAndDisplaySites();
        } catch (error) {
            console.error(`Error ${siteKey ? 'updating' : 'adding'} site:`, error);
            showNotification(`Error: ${error.message}`, 'error');
        }
    });

    const cancelBtn = formContainer.querySelector('.cancel-site-form');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            formContainer.style.display = 'none';
            formContainer.innerHTML = '';
        });
    }
}

function createSiteFormHTML(siteData = {}, siteKey = null) {
    const isEditing = siteKey !== null;
    const s = siteData || {};

    const val = (field, def = '') => s[field] !== undefined && s[field] !== null ? s[field] : def;
    const sel = (field, optionValue) => val(field) === optionValue ? 'selected' : '';
    const checked = (field) => val(field) ? 'checked' : '';

    const sw = s.scoring_weights || {};
    const swVal = (field, def = '') => {
        const globalDefaults = { relevance_weight: 0.5, rating_weight: 0.3, views_weight: 0.1, multiplier_effect: 0.1 };
        return sw[field] !== undefined && sw[field] !== null ? sw[field] : globalDefaults[field] || def;
    };

    const formTitle = isEditing ? `Edit Site: ${s.name || siteKey}` : 'Add New Site';
    // For new sites, siteKey is null. Backend POST /api/sites generates key from 'name'.
    // For PUT /api/sites/<site_key>, siteKey is from the list item.

    // Helper for required fields in HTML
    const req = (fieldName) => {
        const scrapeRequired = ['search_url_template', 'results_container_selector', 'result_item_selector', 'title_selector', 'video_url_selector', 'thumbnail_selector'];
        const apiRequired = ['api_url_template', 'api_title_field', 'api_url_field'];
        if (document.getElementById('search_method')?.value === 'scrape_search_page' && scrapeRequired.includes(fieldName)) return 'required';
        if (document.getElementById('search_method')?.value === 'api' && apiRequired.includes(fieldName)) return 'required';
        return '';
    };


    return `
        <form id="siteConfigForm">
            <h3>${formTitle}</h3>

            <div class="form-group">
                <label for="name">Display Name:*</label>
                <input type="text" id="name" name="name" value="${val('name')}" required>
            </div>
            <div class="form-group">
                <label for="base_url">Base URL (e.g., https://www.example.com):*</label>
                <input type="url" id="base_url" name="base_url" value="${val('base_url')}" required placeholder="https://www.example.com">
            </div>
            <div class="form-group">
                <label for="search_method">Search Method:*</label>
                <select id="search_method" name="search_method" required>
                    <option value="" ${sel('search_method', '')}>-- Select Method --</option>
                    <option value="scrape_search_page" ${sel('search_method', 'scrape_search_page')}>Direct Scrape</option>
                    <option value="google_site_search" ${sel('search_method', 'google_site_search')}>Google Site Search</option>
                    <option value="bing_search" ${sel('search_method', 'bing_search')}>Bing Search</option>
                    <option value="duckduckgo_search" ${sel('search_method', 'duckduckgo_search')}>DuckDuckGo Search</option>
                    <option value="api" ${sel('search_method', 'api')}>Custom API</option>
                </select>
            </div>
            <div class="form-group">
                <label for="popularity_multiplier">Popularity Multiplier (0.1-5.0):*</label>
                <input type="number" id="popularity_multiplier" name="popularity_multiplier" value="${val('popularity_multiplier', 1.0)}" min="0.1" max="5" step="0.1" required>
            </div>

            <div id="scrapeFields" class="conditional-fields form-section" style="display:none;">
                <h4>Direct Scrape Settings (for Search Results Page)</h4>
                <div class="form-group"><label for="search_url_template">Search URL Template ({query}, {page}):*</label><input type="text" id="search_url_template" name="search_url_template" value="${val('search_url_template')}" placeholder="https://site.com/search?q={query}&p={page}"></div>
                <div class="form-group"><label for="results_container_selector">Results Container Selector:*</label><input type="text" id="results_container_selector" name="results_container_selector" value="${val('results_container_selector')}" placeholder="div.video-list"></div>
                <div class="form-group"><label for="result_item_selector">Result Item Selector:*</label><input type="text" id="result_item_selector" name="result_item_selector" value="${val('result_item_selector')}" placeholder="article.video-item"></div>
                <div class="form-group"><label for="title_selector">Title Selector (within item):*</label><input type="text" id="title_selector" name="title_selector" value="${val('title_selector')}" placeholder="h3.title a"></div>
                <div class="form-group"><label for="video_url_selector">Video URL Selector (within item, extracts href):*</label><input type="text" id="video_url_selector" name="video_url_selector" value="${val('video_url_selector')}" placeholder="a.watch-link[href]"></div>
                <div class="form-group"><label for="thumbnail_selector">Thumbnail URL Selector (within item, extracts src):*</label><input type="text" id="thumbnail_selector" name="thumbnail_selector" value="${val('thumbnail_selector')}" placeholder="img.thumb[src]"></div>
                <div class="form-group"><label for="next_page_selector">Next Page Link Selector (Optional, extracts href):</label><input type="text" id="next_page_selector" name="next_page_selector" value="${val('next_page_selector')}" placeholder="a.next_page[href]"></div>
            </div>

            <div id="apiFields" class="conditional-fields form-section" style="display:none;">
                <h4>Custom API Settings</h4>
                <div class="form-group"><label for="api_url_template">API URL Template ({query}, {api_key}):*</label><input type="text" id="api_url_template" name="api_url_template" value="${val('api_url_template')}" placeholder="https://api.site.com/search?term={query}"></div>
                <div class="form-group"><label for="api_key">API Key (Optional):</label><input type="password" id="api_key" name="api_key" value="${val('api_key')}"></div>
                <div class="form-group"><label for="api_key_param">API Key Param Name/Location (Optional, e.g., 'Authorization', 'X-Api-Key', or 'url' if key is in template):</label><input type="text" id="api_key_param" name="api_key_param" value="${val('api_key_param')}"></div>
                <div class="form-group"><label for="api_title_field">Title Field Path (e.g., item.title):*</label><input type="text" id="api_title_field" name="api_title_field" value="${val('api_title_field')}" placeholder="video.title"></div>
                <div class="form-group"><label for="api_url_field">URL Field Path:*</label><input type="text" id="api_url_field" name="api_url_field" value="${val('api_url_field')}" placeholder="video.url"></div>
                <div class="form-group"><label for="api_thumbnail_field">Thumbnail Field Path (Optional):</label><input type="text" id="api_thumbnail_field" name="api_thumbnail_field" value="${val('api_thumbnail_field')}"></div>
                <div class="form-group"><label for="api_duration_field">Duration Field Path (Optional):</label><input type="text" id="api_duration_field" name="api_duration_field" value="${val('api_duration_field')}"></div>
                <div class="form-group"><label for="api_rating_field">Rating Field Path (Optional):</label><input type="text" id="api_rating_field" name="api_rating_field" value="${val('api_rating_field')}"></div>
                <div class="form-group"><label for="api_views_field">Views Field Path (Optional):</label><input type="text" id="api_views_field" name="api_views_field" value="${val('api_views_field')}"></div>
                <div class="form-group"><label for="api_author_field">Author Field Path (Optional):</label><input type="text" id="api_author_field" name="api_author_field" value="${val('api_author_field')}"></div>
            </div>

            <div id="videoPageDetailSelectors" class="conditional-fields form-section" style="display:none;">
                <h4>Video Page Detail Selectors (Optional - for all methods)</h4>
                <p class="form-hint"><small>These selectors are used to get more info from the actual video page if a search result URL (from any method) matches this site's base URL. They will use/override the general selectors if filled.</small></p>
                <div class="form-group"><label for="video_page_title_selector">Title Selector (on video page):</label><input type="text" id="video_page_title_selector" name="video_page_title_selector" value="${val('title_selector')}"></div>
                <div class="form-group"><label for="video_page_duration_selector">Duration Selector (on video page):</label><input type="text" id="video_page_duration_selector" name="video_page_duration_selector" value="${val('duration_selector')}"></div>
                <div class="form-group"><label for="video_page_rating_selector">Rating Selector (on video page):</label><input type="text" id="video_page_rating_selector" name="video_page_rating_selector" value="${val('rating_selector')}"></div>
                <div class="form-group"><label for="video_page_views_selector">Views Selector (on video page):</label><input type="text" id="video_page_views_selector" name="video_page_views_selector" value="${val('views_selector')}"></div>
                <div class="form-group"><label for="video_page_author_selector">Author Selector (on video page):</label><input type="text" id="video_page_author_selector" name="video_page_author_selector" value="${val('author_selector')}"></div>
            </div>

            <div class="form-group form-section">
                 <input type="checkbox" id="override_global_scoring_weights" name="override_global_scoring_weights" ${s.scoring_weights ? 'checked' : ''}>
                 <label for="override_global_scoring_weights">Override Global Scoring Weights for this Site?</label>
            </div>
            <div id="perSiteScoringWeights" class="form-section" style="display:${s.scoring_weights ? 'block' : 'none'};">
                <h4>Per-Site Scoring Weights</h4>
                <div class="form-group"><label for="relevance_weight">Relevance Weight (0-1):</label><input type="number" id="relevance_weight" name="relevance_weight" value="${swVal('relevance_weight', 0.5)}" min="0" max="1" step="0.01"></div>
                <div class="form-group"><label for="rating_weight">Rating Weight (0-1):</label><input type="number" id="rating_weight" name="rating_weight" value="${swVal('rating_weight', 0.3)}" min="0" max="1" step="0.01"></div>
                <div class="form-group"><label for="views_weight">Views Weight (0-1):</label><input type="number" id="views_weight" name="views_weight" value="${swVal('views_weight', 0.1)}" min="0" max="1" step="0.01"></div>
                <div class="form-group"><label for="multiplier_effect">Multiplier Effect (0-1):</label><input type="number" id="multiplier_effect" name="multiplier_effect" value="${swVal('multiplier_effect', 0.1)}" min="0" max="1" step="0.01"></div>
                <p class="form-hint"><small>Relevance, Rating, and Views weights should ideally sum to 1.0 if overriding.</small></p>
            </div>

            <div class="form-actions">
                <button type="submit" class="save-site-btn">${isEditing ? 'Update Site' : 'Add Site'}</button>
                <button type="button" class="cancel-site-form">Cancel</button>
            </div>
            <p class="form-hint"><small>* Required field for the selected search method or basic info.</small></p>
        </form>
    `;
}


async function deleteSite(siteKey) {
    try {
        const response = await fetch(`/api/sites/${siteKey}`, { method: 'DELETE' });
        // Try to parse JSON, but handle cases where response might be empty or not JSON
        let result = {};
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            result = await response.json();
        } else {
            // If not JSON, use text and construct a result-like object for consistency
            const textResponse = await response.text();
            result = { message: textResponse || (response.ok ? `Site ${siteKey} deleted.` : `Failed to delete ${siteKey}.`) };
        }

        if (!response.ok) {
            const errorMsg = result.error || result.message || `HTTP error ${response.status}`;
            throw new Error(errorMsg);
        }
        showNotification(result.message || `Site ${siteKey} deleted successfully.`, 'success');
        loadAndDisplaySites();
    } catch (error) {
        console.error("Error deleting site:", error);
        showNotification(`Error deleting site: ${error.message}`, 'error');
    }
}

function showNotification(message, type = 'info') {
    const notificationArea = document.getElementById('notificationArea');
    if (!notificationArea) {
        console.log(`Notification (${type}): ${message}`);
        alert(`(${type.toUpperCase()}) ${message}`);
        return;
    }
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Simple clear previous notifications of the same type before adding new one
    const existingOfType = notificationArea.querySelector(`.notification-${type}`);
    if(existingOfType && (type === 'error' || type === 'success')) { // Only replace error/success
        existingOfType.remove();
    }

    notificationArea.appendChild(notification);
    setTimeout(() => {
        if (notification.parentNode === notificationArea) { // Check if still child
            notification.remove();
        }
    }, type === 'error' ? 8000 : 5000);
}
