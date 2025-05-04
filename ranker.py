# ranker.py
import re
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Basic stop words (customize as needed)
STOP_WORDS = set(['a', 'an', 'the', 'and', 'or', 'in', 'on', 'of', 'to', 'xxx', 'porn', 'sex'])

# Default scoring weights
DEFAULT_WEIGHTS = {
    'relevance_weight': 0.50,
    'rating_weight': 0.30,
    'views_weight': 0.10,
    'multiplier_effect': 0.10
}

def normalize_title(title):
    """ Basic normalization for title comparison. """
    if not title: return ""
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title) # Remove punctuation
    title = ' '.join(word for word in title.split() if word not in STOP_WORDS)
    return title.strip()

def calculate_relevance(title, description_snippet, query):
    """ Simple keyword-based relevance scoring. """
    score = 0
    query_terms = set(normalize_title(query).split())
    if not query_terms: return 0.0

    normalized_title = normalize_title(title)
    normalized_desc = normalize_title(description_snippet) if description_snippet else ""

    # Score based on title match (higher weight)
    title_words = set(normalized_title.split())
    common_in_title = len(query_terms.intersection(title_words))
    score += common_in_title * 2.0 # Give more weight to title matches

    # Exact phrase matching in title (additional bonus)
    if query.lower() in title.lower():
        score += 1.0
    
    # Score based on snippet match (lower weight)
    desc_words = set(normalized_desc.split())
    common_in_desc = len(query_terms.intersection(desc_words))
    score += common_in_desc * 1.0

    # Title word count - prefer concise titles that still match query
    title_length = len(title_words)
    if title_length > 0:
        title_conciseness = min(1.0, 10.0 / title_length)  # Higher score for shorter titles
        score += title_conciseness * 0.5  # Small bonus for concise titles

    # Normalize score (crudely) based on number of query terms
    return score / len(query_terms) if query_terms else 0.0

def handle_duplicates(results):
    """
    Group and process duplicate results based on title and duration.
    
    Args:
        results (list): List of result items
        
    Returns:
        list: Deduplicated results with alternates
    """
    # Group potential duplicates by normalized title
    duplicates = defaultdict(list)
    processed = []
    duration_tolerance = 5  # seconds
    
    # First pass - group by title
    for result in results:
        norm_title = normalize_title(result.get('title', ''))
        
        if norm_title:
            duplicates[norm_title].append(result)
        else:
            processed.append(result)  # Can't deduplicate without a title
    
    # Process each group
    final_results = []
    processed_urls = set()
    
    for norm_title, group in duplicates.items():
        if not group:
            continue
            
        # Sort by score
        group.sort(key=lambda x: x.get('calc_score', 0), reverse=True)
        
        # Further group by duration if available
        duration_groups = defaultdict(list)
        
        for item in group:
            duration = item.get('duration_sec')
            
            if duration is not None:
                # Group by duration range
                duration_key = duration // duration_tolerance
                duration_groups[duration_key].append(item)
            else:
                # If no duration, keep in its own group
                duration_groups[f"no_duration_{len(duration_groups)}"].append(item)
        
        # Process each duration group
        for items in duration_groups.values():
            if not items:
                continue
                
            # Sort by score within duration group
            items.sort(key=lambda x: x.get('calc_score', 0), reverse=True)
            
            primary = items[0]
            if primary.get('url') in processed_urls:
                continue  # Already processed this URL as primary
            
            # Add as primary result
            primary['alternates'] = []
            processed_urls.add(primary.get('url'))
            
            # Add alternates
            for alt in items[1:]:
                alt_url = alt.get('url')
                if alt_url != primary.get('url') and alt_url not in processed_urls:
                    primary['alternates'].append({
                        'site': alt.get('site'),
                        'url': alt_url,
                        'title': alt.get('title')
                    })
                    processed_urls.add(alt_url)  # Mark as processed
            
            final_results.append(primary)
    
    # Combine with non-duplicates
    final_results.extend(processed)
    
    return final_results

def rank_and_process(raw_results, sites_config, query, scoring_weights=None):
    """ Processes raw results: Calculate scores, handles duplicates. """
    if not scoring_weights:
        scoring_weights = DEFAULT_WEIGHTS
    else:
        # Ensure all weights are present, use defaults for missing ones
        for key, value in DEFAULT_WEIGHTS.items():
            if key not in scoring_weights:
                scoring_weights[key] = value
    
    # Extract weights
    relevance_weight = float(scoring_weights.get('relevance_weight', 0.50))
    rating_weight = float(scoring_weights.get('rating_weight', 0.30))
    views_weight = float(scoring_weights.get('views_weight', 0.10))
    multiplier_effect = float(scoring_weights.get('multiplier_effect', 0.10))
    
    logger.info(f"Using scoring weights: relevance={relevance_weight}, rating={rating_weight}, "
               f"views={views_weight}, multiplier_effect={multiplier_effect}")

    # Find max views for normalization
    max_views = 1  # Avoid division by zero
    for result in raw_results:
        if result.get('views') is not None and isinstance(result['views'], (int, float)):
                max_views = max(max_views, result['views'])

    # Calculate scores for each result
    scored_results = []
    for result in raw_results:
        site_name = result.get('site')
        site_cfg = sites_config.get(site_name, {})
        multiplier = site_cfg.get('popularity_multiplier', 1.0)

        # --- Calculate Relevance ---
        relevance = calculate_relevance(
            result.get('title'),
            result.get('description_snippet'), # Use description from Google Search if available
            query
        )

        # --- Normalize Rating and Views ---
        # Ensure site_rating is 0-1 if present
        normalized_rating = result.get('site_rating', 0.0) # Assume 0 if missing or parsing failed
        
        # Basic view normalization (use log scale to prevent outliers from dominating)
        views = result.get('views', 0)
        if views and max_views > 1:
            import math
            log_views = math.log(views + 1)  # Add 1 to avoid log(0)
            log_max = math.log(max_views + 1)
            normalized_views = log_views / log_max if log_max > 0 else 0
        else:
            normalized_views = 0.0

        # --- Scoring Formula ---
        score = ((relevance * relevance_weight) +
                (normalized_rating * rating_weight) +
                (normalized_views * views_weight)
                ) * (1 + (multiplier-1) * multiplier_effect)

        # Store intermediate scores
        result['relevance_score'] = relevance
        result['calc_score'] = score
        
        scored_results.append(result)

    # Handle duplicates
    deduplicated_results = handle_duplicates(scored_results)
    
    # Final sorting by score
    deduplicated_results.sort(key=lambda x: x.get('calc_score', 0), reverse=True)

    return deduplicated_results