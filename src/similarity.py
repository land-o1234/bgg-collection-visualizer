"""
Game similarity computation module.
This module computes similarity between games based on their mechanics, categories, and other attributes.
"""

import numpy as np
from typing import Dict, List, Tuple, Any
import logging

log = logging.getLogger(__name__)

def compute_similarity_edges(games: Dict[int, Dict[str, Any]], edge_threshold: float = 0.35) -> List[Tuple[int, int, float]]:
    """
    Compute similarity edges between games based on their attributes.
    
    Args:
        games: Dictionary mapping game ID to game details
        edge_threshold: Minimum similarity score to create an edge
        
    Returns:
        List of tuples (game_id_1, game_id_2, similarity_score)
    """
    game_ids = list(games.keys())
    edges = []
    
    log.info(f"Computing similarities for {len(game_ids)} games with threshold {edge_threshold}")
    
    for i, game1_id in enumerate(game_ids):
        for j, game2_id in enumerate(game_ids[i+1:], i+1):
            similarity = _compute_game_similarity(games[game1_id], games[game2_id])
            
            if similarity >= edge_threshold:
                edges.append((game1_id, game2_id, similarity))
    
    log.info(f"Created {len(edges)} similarity edges")
    return edges

def _compute_game_similarity(game1: Dict[str, Any], game2: Dict[str, Any]) -> float:
    """
    Compute similarity score between two games based on multiple factors.
    
    Returns a score between 0 and 1 where 1 is most similar.
    """
    scores = []
    weights = []
    
    # Mechanics similarity (high weight)
    mechanics_sim = _jaccard_similarity(
        [m.get('name', '') for m in game1.get('mechanics', [])],
        [m.get('name', '') for m in game2.get('mechanics', [])]
    )
    scores.append(mechanics_sim)
    weights.append(0.4)
    
    # Categories similarity (high weight)  
    categories_sim = _jaccard_similarity(
        [c.get('name', '') for c in game1.get('categories', [])],
        [c.get('name', '') for c in game2.get('categories', [])]
    )
    scores.append(categories_sim)
    weights.append(0.3)
    
    # Player count similarity
    player_sim = _player_count_similarity(game1, game2)
    scores.append(player_sim)
    weights.append(0.1)
    
    # Playing time similarity
    time_sim = _playing_time_similarity(game1, game2)
    scores.append(time_sim)
    weights.append(0.1)
    
    # Weight/complexity similarity
    weight_sim = _weight_similarity(game1, game2)
    scores.append(weight_sim)
    weights.append(0.1)
    
    # Compute weighted average
    weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
    return weighted_score

def _jaccard_similarity(set1: List[str], set2: List[str]) -> float:
    """Compute Jaccard similarity between two lists of strings."""
    set1 = set(item.lower().strip() for item in set1 if item)
    set2 = set(item.lower().strip() for item in set2 if item)
    
    if not set1 and not set2:
        return 1.0  # Both empty
    if not set1 or not set2:
        return 0.0  # One empty
        
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def _player_count_similarity(game1: Dict[str, Any], game2: Dict[str, Any]) -> float:
    """Compute similarity based on player count ranges."""
    min1 = game1.get('minplayers') or 1
    max1 = game1.get('maxplayers') or 1
    min2 = game2.get('minplayers') or 1  
    max2 = game2.get('maxplayers') or 1
    
    # Calculate overlap in player count ranges
    overlap_start = max(min1, min2)
    overlap_end = min(max1, max2)
    
    if overlap_start <= overlap_end:
        overlap = overlap_end - overlap_start + 1
        range1 = max1 - min1 + 1
        range2 = max2 - min2 + 1
        union = range1 + range2 - overlap
        return overlap / union if union > 0 else 0.0
    else:
        return 0.0  # No overlap

def _playing_time_similarity(game1: Dict[str, Any], game2: Dict[str, Any]) -> float:
    """Compute similarity based on playing time."""
    time1 = game1.get('playingtime')
    time2 = game2.get('playingtime')
    
    if not time1 or not time2:
        return 0.5  # Unknown times get neutral score
        
    # Use logarithmic scale to handle wide range of playing times
    log_time1 = np.log(max(1, time1))
    log_time2 = np.log(max(1, time2))
    
    # Similarity decreases as log difference increases
    max_diff = np.log(300)  # ~5 hours max reasonable difference
    diff = abs(log_time1 - log_time2)
    
    return max(0.0, 1.0 - (diff / max_diff))

def _weight_similarity(game1: Dict[str, Any], game2: Dict[str, Any]) -> float:
    """Compute similarity based on game weight (complexity)."""
    weight1 = game1.get('averageweight')
    weight2 = game2.get('averageweight')
    
    if not weight1 or not weight2:
        return 0.5  # Unknown weights get neutral score
        
    # Weight is on 1-5 scale, so max difference is 4
    diff = abs(weight1 - weight2)
    return max(0.0, 1.0 - (diff / 4.0))