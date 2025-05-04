/**
 * player-manager.js - Handles video player management for MetaStream Aggregator
 * Manages player state, video loading, and playback
 */

class PlayerManager {
    constructor(numPlayers = 4) {
        // Initialize player state
        this.players = {};
        this.numPlayers = numPlayers;
        
        // Create player state for each slot
        for (let i = 1; i <= numPlayers; i++) {
            this.players[`player-${i}`] = {
                id: `player-${i}`,
                active: false,
                url: null,
                title: null,
                source: null,
                loadTime: null
            };
        }
        
        this.minimized = false;
        
        // Event subscriptions
        this.eventSubscribers = {
            'playerLoaded': [],
            'playerClosed': [],
            'allPlayersClosed': [],
            'playerAreaToggled': []
        };
        
        // Initialize from localStorage if available
        this.loadState();
    }
    
    /**
     * Subscribe to player events
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
     * Load a video into a player slot
     * @param {string} playerId - Player ID (e.g., 'player-1')
     * @param {string} url - URL of the video to load
     * @param {string} title - Title of the video
     * @param {string} source - Source of the video (e.g., site name)
     * @returns {boolean} - True if successful, false if failed
     */
    loadVideo(playerId, url, title, source = null) {
        if (!playerId || !url) {
            return false;
        }
        
        // Check if the player exists
        if (!this.players[playerId]) {
            console.error(`Player ${playerId} does not exist`);
            return false;
        }
        
        // Get the iframe element
        const iframe = document.getElementById(playerId);
        if (!iframe) {
            console.error(`Player iframe ${playerId} not found in DOM`);
            return false;
        }
        
        // Update the iframe src
        try {
            iframe.src = url;
            
            // Update player state
            this.players[playerId] = {
                id: playerId,
                active: true,
                url: url,
                title: title || 'Untitled Video',
                source: source,
                loadTime: new Date().toISOString()
            };
            
            // Save state to localStorage
            this.saveState();
            
            // Trigger event
            this.trigger('playerLoaded', {
                playerId,
                player: this.players[playerId]
            });
            
            return true;
        } catch (error) {
            console.error(`Error loading video into ${playerId}:`, error);
            return false;
        }
    }
    
    /**
     * Close/clear a player slot
     * @param {string} playerId - Player ID to close
     * @returns {boolean} - True if successful, false if failed
     */
    closePlayer(playerId) {
        if (!playerId) {
            return false;
        }
        
        // Check if the player exists
        if (!this.players[playerId]) {
            console.error(`Player ${playerId} does not exist`);
            return false;
        }
        
        // Get the iframe element
        const iframe = document.getElementById(playerId);
        if (!iframe) {
            console.error(`Player iframe ${playerId} not found in DOM`);
            return false;
        }
        
        // Clear the iframe src
        try {
            iframe.src = 'about:blank';
            
            const wasActive = this.players[playerId].active;
            
            // Update player state
            this.players[playerId] = {
                id: playerId,
                active: false,
                url: null,
                title: null,
                source: null,
                loadTime: null
            };
            
            // Save state to localStorage
            this.saveState();
            
            // Check if all players are now closed
            const allClosed = this.areAllPlayersClosed();
            
            // Trigger events
            if (wasActive) {
                this.trigger('playerClosed', { playerId });
                
                if (allClosed) {
                    this.trigger('allPlayersClosed');
                }
            }
            
            return true;
        } catch (error) {
            console.error(`Error closing player ${playerId}:`, error);
            return false;
        }
    }
    
    /**
     * Close all player slots
     * @returns {boolean} - True if successful, false if any player failed to close
     */
    closeAllPlayers() {
        let allSuccessful = true;
        
        // Get list of active players to avoid triggering events for already closed players
        const activePlayers = Object.keys(this.players).filter(id => this.players[id].active);
        
        // Close each player
        for (const playerId of Object.keys(this.players)) {
            if (!this.closePlayer(playerId)) {
                allSuccessful = false;
            }
        }
        
        // Trigger allPlayersClosed event if there were any active players
        if (activePlayers.length > 0) {
            this.trigger('allPlayersClosed');
        }
        
        return allSuccessful;
    }
    
    /**
     * Get a list of active players
     * @returns {Array} - Array of active player objects
     */
    getActivePlayers() {
        return Object.values(this.players).filter(player => player.active);
    }
    
    /**
     * Check if a specific player is active
     * @param {string} playerId - Player ID to check
     * @returns {boolean} - True if the player is active
     */
    isPlayerActive(playerId) {
        return this.players[playerId] && this.players[playerId].active;
    }
    
    /**
     * Check if any players are active
     * @returns {boolean} - True if any player is active
     */
    hasActivePlayers() {
        return Object.values(this.players).some(player => player.active);
    }
    
    /**
     * Check if all players are closed
     * @returns {boolean} - True if all players are closed/inactive
     */
    areAllPlayersClosed() {
        return !this.hasActivePlayers();
    }
    
    /**
     * Get the number of active players
     * @returns {number} - Number of active players
     */
    getActivePlayerCount() {
        return this.getActivePlayers().length;
    }
    
    /**
     * Get the first available player slot ID
     * @returns {string|null} - Player ID of the first available slot, or null if all slots are taken
     */
    getFirstAvailablePlayerSlot() {
        for (const playerId of Object.keys(this.players)) {
            if (!this.players[playerId].active) {
                return playerId;
            }
        }
        return null;
    }
    
    /**
     * Toggle the minimized state of the player area
     * @returns {boolean} - New minimized state
     */
    toggleMinimized() {
        this.minimized = !this.minimized;
        
        // Save state to localStorage
        this.saveState();
        
        // Trigger event
        this.trigger('playerAreaToggled', { minimized: this.minimized });
        
        return this.minimized;
    }
    
    /**
     * Set the minimized state of the player area
     * @param {boolean} minimized - Whether the player area should be minimized
     */
    setMinimized(minimized) {
        if (this.minimized !== minimized) {
            this.minimized = minimized;
            
            // Save state to localStorage
            this.saveState();
            
            // Trigger event
            this.trigger('playerAreaToggled', { minimized: this.minimized });
        }
    }
    
    /**
     * Check if the player area is minimized
     * @returns {boolean} - True if the player area is minimized
     */
    isMinimized() {
        return this.minimized;
    }
    
    /**
     * Save the current player state to localStorage
     */
    saveState() {
        try {
            const state = {
                players: this.players,
                minimized: this.minimized
            };
            localStorage.setItem('playerState', JSON.stringify(state));
        } catch (e) {
            console.warn('Failed to save player state to localStorage:', e);
        }
    }
    
    /**
     * Load the player state from localStorage
     */
    loadState() {
        try {
            const savedState = localStorage.getItem('playerState');
            if (savedState) {
                const state = JSON.parse(savedState);
                
                // Restore minimized state
                this.minimized = state.minimized || false;
                
                // Restore player states, but don't actually load the videos yet
                // This prevents auto-playing videos on page load
                // Just update our internal state
                if (state.players) {
                    for (const playerId of Object.keys(state.players)) {
                        // Only update state for players that exist in our current configuration
                        if (this.players[playerId]) {
                            this.players[playerId] = state.players[playerId];
                            
                            // Mark as inactive since we're not auto-loading
                            this.players[playerId].active = false;
                            
                            // Make sure the iframe is cleared
                            const iframe = document.getElementById(playerId);
                            if (iframe) {
                                iframe.src = 'about:blank';
                            }
                        }
                    }
                }
                
                // Trigger events for UI updates
                this.trigger('playerAreaToggled', { minimized: this.minimized });
            }
        } catch (e) {
            console.warn('Failed to load player state from localStorage:', e);
        }
    }
    
    /**
     * Clear the player state in localStorage
     */
    clearSavedState() {
        try {
            localStorage.removeItem('playerState');
        } catch (e) {
            console.warn('Failed to clear player state from localStorage:', e);
        }
    }
}

// Create and export a singleton instance
const playerManager = new PlayerManager(4);

// Load into global scope for simple access
window.playerManager = playerManager;