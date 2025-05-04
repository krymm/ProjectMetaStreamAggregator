# MetaStream Aggregator Testing Checklist

## Search Functionality

### Basic Search
- [x] Search with single site
- [x] Search with multiple sites
- [x] Search with all sites
- [x] Search with empty query (should show error)
- [x] Search with no sites selected (should show error)

### Pagination
- [x] Navigate to next page
- [x] Navigate to previous page
- [x] Navigate to specific page number
- [x] First page edge case (previous button disabled)
- [x] Last page edge case (next button disabled)
- [x] Single page result set (no pagination needed)

### Result Display
- [x] Results displayed correctly with thumbnails
- [x] Duration shown properly if available
- [x] Rating shown properly if available
- [x] Correct site attribution
- [x] Broken links shown in separate section

## Ranking Algorithm

- [x] Results properly ranked by relevance
- [x] Site ratings factored into ranking
- [x] View counts factored into ranking
- [x] Site multiplier applied correctly 
- [x] Ordering changes when scoring weights are adjusted

## Duplicate Detection

- [x] Identical videos from different sites grouped properly
- [x] Primary/alternate designation is correct (highest score as primary)
- [x] Can access alternates through UI
- [x] Alternates show correct site attribution

## Player Management

- [x] Send video to Player 1-4
- [x] Close individual players
- [x] Close all players
- [x] Player list updated correctly when players change
- [x] Minimize/expand player section
- [x] Auto-expand player area when loading a video

## Settings

- [x] Settings modal opens/closes properly
- [x] Save settings works
- [x] Reset to defaults works
- [x] API keys masked in UI but saved correctly
- [x] Settings persist after page reload
- [x] Changing results per page works

## Cache Management

- [x] Cache statistics displayed correctly
- [x] Clear all cache works
- [x] Clear specific search cache works
- [x] Cache expiry works as configured
- [x] Cached results are properly marked as cached

## Error Handling

- [x] Graceful handling of failed site scrapes
- [x] Proper error messaging for API issues
- [x] Handling of network disconnection
- [x] Recovery from invalid site configurations
- [x] Browser console free of JavaScript errors

## Browser Compatibility

- [x] Works in Chrome
- [x] Works in Firefox
- [x] Works in Safari
- [x] Works in Edge
- [x] Responsive design on different screen sizes

## Performance

- [x] Reasonable load time for searches
- [x] UI remains responsive during search operations
- [x] Memory usage stays reasonable for large result sets
- [x] Proper loading indicators shown during operations