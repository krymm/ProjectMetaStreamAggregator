// app.js - Main JavaScript file for MetaStream Aggregator
// This file initializes the application components and provides global utilities

// Global error handler to catch unhandled errors
window.addEventListener('error', function(event) {
    console.error('Unhandled error:', event.error);
    
    // Notify user of error if it's not just a missing element
    if (event.error && !event.error.message.includes('null')) {
        // Show error message if loading indicator is not visible (to avoid interrupting searches)
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator && loadingIndicator.classList.contains('hidden')) {
            alert(`An error occurred: ${event.error.message}`);
        }
    }
    
    // Prevent default browser error handling
    event.preventDefault();
});

// Global promise rejection handler
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    
    // Show error message if loading indicator is not visible (to avoid interrupting searches)
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator && loadingIndicator.classList.contains('hidden')) {
        alert(`An error occurred: ${event.reason.message || 'Unknown error'}`);
    }
    
    // Prevent default browser error handling
    event.preventDefault();
});

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('MetaStream Aggregator initializing...');
    
    // Import modules
    loadScript('/static/js/search-manager.js')
        .then(() => loadScript('/static/js/player-manager.js'))
        .then(() => loadScript('/static/js/ui-manager.js'))
        .then(() => {
            console.log('All modules loaded successfully');
            
            // Initialize components
            initializeApplication();
        })
        .catch(error => {
            console.error('Error loading application modules:', error);
            alert('Failed to initialize the application. Please check console for details.');
        });
});

/**
 * Load a JavaScript file dynamically
 * @param {string} src - Script source URL
 * @returns {Promise} - Promise that resolves when script is loaded
 */
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
        document.head.appendChild(script);
    });
}

/**
 * Initialize the application
 */
function initializeApplication() {
    // Check if all required components are loaded
    if (!window.searchManager || !window.playerManager || !window.uiManager) {
        console.error('Required components not loaded');
        alert('Failed to initialize the application. Missing required components.');
        return;
    }
    
    // Register inter-component event handlers
    registerComponentEvents();
    
    // Initialize UI components that require JavaScript
    initializeUI();
    
    // Load any saved state
    restoreApplicationState();
    
    console.log('MetaStream Aggregator initialized successfully');
}

/**
 * Register event handlers between components
 */
function registerComponentEvents() {
    // Example of cross-component event registration
    // searchManager.on('searchCompleted', (data) => {
    //     // Handle search completion
    // });
}

/**
 * Initialize UI components that require JavaScript
 */
function initializeUI() {
    // Initialize tooltips or other UI enhancements
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Only handle shortcuts if not typing in an input field
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // CTRL+F to focus search box
        if (event.ctrlKey && event.key === 'f') {
            event.preventDefault();
            document.getElementById('search-input').focus();
        }
        
        // CTRL+SHIFT+S to open settings
        if (event.ctrlKey && event.shiftKey && event.key === 'S') {
            event.preventDefault();
            window.uiManager.openSettingsModal();
        }
        
        // ESC to close modals
        if (event.key === 'Escape') {
            if (window.uiManager.settingsVisible) {
                window.uiManager.closeSettingsModal();
            }
            if (window.uiManager.cacheModalVisible) {
                window.uiManager.closeCacheModal();
            }
            if (window.uiManager.helpModalVisible) {
                window.uiManager.closeHelpModal();
            }
        }
    });
}

/**
 * Restore application state from saved preferences
 */
function restoreApplicationState() {
    // Already handled by each component's initialization
}

/**
 * Global utility to format a date
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date string
 */
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    
    return date.toLocaleString();
}

/**
 * Global utility to format a file size
 * @param {number} bytes - Size in bytes
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted size string
 */
function formatFileSize(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Global utility to escape HTML to prevent XSS
 * @param {string} unsafeText - Text that might contain HTML
 * @returns {string} - Escaped safe text
 */
function escapeHtml(unsafeText) {
    if (!unsafeText) return '';
    
    const div = document.createElement('div');
    div.textContent = unsafeText;
    return div.innerHTML;
}

/**
 * Global utility to debounce a function
 * @param {function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {function} - Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise} - Promise that resolves when text is copied
 */
function copyToClipboard(text) {
    return navigator.clipboard.writeText(text)
        .then(() => true)
        .catch(err => {
            console.error('Could not copy text: ', err);
            return false;
        });
}