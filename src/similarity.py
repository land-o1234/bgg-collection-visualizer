"""
Similarity computation for board games.
Computes pairwise similarity scores based on mechanics, categories, and numeric features.
"""
import logging
import math
from typing import Dict, Any, List, Tuple, Set

log = logging.getLogger(__name__)


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 and not set2:
        return 1.0  # Both empty sets are identical
    if not set1 or not set2:
        return 0.0  # One empty, one non-empty
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0
    
    # Compute dot product and magnitudes
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    # Handle zero vectors
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def normalize_numeric_features(games: Dict[str, Dict[str, Any]]) -> Dict[str, List[float]]:
    """
    Extract and normalize numeric features for all games.
    Returns dict mapping game_id -> normalized feature vector.
    """
    feature_names = ["averagerating", "averageweight", "playingtime", "minplayers", "maxplayers", "minage", "year"]
    
    # Extract all values for normalization
    all_values = {name: [] for name in feature_names}
    game_features = {}
    
    for game_id, game in games.items():
        features = []
        for feature in feature_names:
            value = game.get(feature)
            # Convert to float, default to 0 if missing/invalid
            try:
                value = float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                value = 0.0
            features.append(value)
            all_values[feature].append(value)
        
        game_features[game_id] = features
    
    # Compute mean and std for normalization (avoid division by zero)
    means = []
    stds = []
    for feature in feature_names:
        values = all_values[feature]
        mean = sum(values) / len(values) if values else 0.0
        variance = sum((x - mean) ** 2 for x in values) / len(values) if values else 0.0
        std = math.sqrt(variance) if variance > 0 else 1.0
        means.append(mean)
        stds.append(std)
    
    # Normalize all features
    normalized_features = {}
    for game_id, features in game_features.items():
        normalized = [(features[i] - means[i]) / stds[i] for i in range(len(features))]
        normalized_features[game_id] = normalized
    
    return normalized_features


def compute_game_similarity(game1: Dict[str, Any], game2: Dict[str, Any], 
                          normalized_features1: List[float], normalized_features2: List[float],
                          mechanics_weight: float = 0.4, 
                          categories_weight: float = 0.25, 
                          numeric_weight: float = 0.2,
                          designers_weight: float = 0.1,
                          publishers_weight: float = 0.05) -> float:
    """
    Compute similarity between two games using weighted combination of:
    - Jaccard similarity of mechanics (40%)
    - Jaccard similarity of categories (25%) 
    - Cosine similarity of normalized numeric features (20%)
    - Jaccard similarity of designers (10%)
    - Jaccard similarity of publishers (5%)
    """
    
    # Extract mechanics and categories as sets of names
    mechanics1 = set(m.get("name", "") for m in game1.get("mechanics", []) if m.get("name"))
    mechanics2 = set(m.get("name", "") for m in game2.get("mechanics", []) if m.get("name"))
    
    categories1 = set(c.get("name", "") for c in game1.get("categories", []) if c.get("name"))
    categories2 = set(c.get("name", "") for c in game2.get("categories", []) if c.get("name"))
    
    # Extract designers and publishers
    designers1 = set(d.get("name", "") for d in game1.get("designers", []) if d.get("name"))
    designers2 = set(d.get("name", "") for d in game2.get("designers", []) if d.get("name"))
    
    publishers1 = set(p.get("name", "") for p in game1.get("publishers", []) if p.get("name"))
    publishers2 = set(p.get("name", "") for p in game2.get("publishers", []) if p.get("name"))
    
    # Compute component similarities
    mechanics_sim = jaccard_similarity(mechanics1, mechanics2)
    categories_sim = jaccard_similarity(categories1, categories2)
    numeric_sim = cosine_similarity(normalized_features1, normalized_features2)
    designers_sim = jaccard_similarity(designers1, designers2)
    publishers_sim = jaccard_similarity(publishers1, publishers2)
    
    # Weighted combination
    total_weight = mechanics_weight + categories_weight + numeric_weight + designers_weight + publishers_weight
    similarity = (
        mechanics_weight * mechanics_sim + 
        categories_weight * categories_sim + 
        numeric_weight * numeric_sim +
        designers_weight * designers_sim +
        publishers_weight * publishers_sim
    ) / total_weight
    
    return similarity


def compute_similarity_edges(games: Dict[str, Dict[str, Any]], 
                           edge_threshold: float = 0.35,
                           mechanics_weight: float = 0.4,
                           categories_weight: float = 0.25, 
                           numeric_weight: float = 0.2,
                           designers_weight: float = 0.1,
                           publishers_weight: float = 0.05) -> List[Tuple[str, str, float]]:
    """
    Compute pairwise similarities between all games and return edges above threshold.
    Returns list of (game_id1, game_id2, similarity_score) tuples.
    """
    game_ids = list(games.keys())
    n_games = len(game_ids)
    
    log.info(f"Computing similarities for {n_games} games...")
    
    # Normalize numeric features once
    normalized_features = normalize_numeric_features(games)
    
    edges = []
    comparisons = 0
    total_comparisons = n_games * (n_games - 1) // 2
    
    # Compute pairwise similarities
    for i in range(n_games):
        for j in range(i + 1, n_games):
            id1, id2 = game_ids[i], game_ids[j]
            
            similarity = compute_game_similarity(
                games[id1], games[id2],
                normalized_features[id1], normalized_features[id2],
                mechanics_weight, categories_weight, numeric_weight, designers_weight, publishers_weight
            )
            
            if similarity >= edge_threshold:
                edges.append((id1, id2, similarity))
            
            comparisons += 1
            
            # Progress logging for large collections
            if comparisons % 1000 == 0:
                log.info(f"Computed {comparisons}/{total_comparisons} similarities ({comparisons/total_comparisons*100:.1f}%)")
    
    # Sort by similarity score descending
    edges.sort(key=lambda x: x[2], reverse=True)
    
    log.info(f"Found {len(edges)} edges above threshold {edge_threshold}")
    return edges


def compute_cross_similarities(owned_games: Dict[str, Dict[str, Any]], 
                              candidate_games: Dict[str, Dict[str, Any]],
                              top_k: int = 5,
                              mechanics_weight: float = 0.4,
                              categories_weight: float = 0.25,
                              numeric_weight: float = 0.2,
                              designers_weight: float = 0.1,
                              publishers_weight: float = 0.05) -> Dict[str, List[Dict[str, Any]]]:
    """
    Compute similarities between owned games and candidate recommendation games.
    Returns dict mapping owned_game_id -> list of top recommended games with scores.
    """
    log.info(f"Computing cross-similarities between {len(owned_games)} owned and {len(candidate_games)} candidate games...")
    
    # Combine all games for feature normalization
    all_games = {**owned_games, **candidate_games}
    normalized_features = normalize_numeric_features(all_games)
    
    recommendations = {}
    
    for owned_id, owned_game in owned_games.items():
        candidates_with_scores = []
        
        for candidate_id, candidate_game in candidate_games.items():
            # Skip if candidate is already owned
            if candidate_id in owned_games:
                continue
                
            similarity = compute_game_similarity(
                owned_game, candidate_game,
                normalized_features[owned_id], normalized_features[candidate_id],
                mechanics_weight, categories_weight, numeric_weight, designers_weight, publishers_weight
            )
            
            candidates_with_scores.append({
                "id": candidate_id,
                "name": candidate_game.get("name", ""),
                "score": similarity,
                "bggUrl": f"https://boardgamegeek.com/boardgame/{candidate_id}"
            })
        
        # Sort by similarity and take top k
        candidates_with_scores.sort(key=lambda x: x["score"], reverse=True)
        recommendations[owned_id] = candidates_with_scores[:top_k]
    
    log.info(f"Generated recommendations for {len(recommendations)} owned games")
    return recommendations


def find_similar_owned_games(target_game: Dict[str, Any], 
                           owned_games: Dict[str, Dict[str, Any]],
                           top_k: int = 10,
                           mechanics_weight: float = 0.4,
                           categories_weight: float = 0.25,
                           numeric_weight: float = 0.2,
                           designers_weight: float = 0.1,
                           publishers_weight: float = 0.05) -> List[Dict[str, Any]]:
    """
    Find owned games most similar to a target game.
    Used for finding games similar to candidates for recommendation scoring.
    """
    all_games = {**owned_games, "target": target_game}
    normalized_features = normalize_numeric_features(all_games)
    
    similarities = []
    for owned_id, owned_game in owned_games.items():
        similarity = compute_game_similarity(
            target_game, owned_game,
            normalized_features["target"], normalized_features[owned_id],
            mechanics_weight, categories_weight, numeric_weight, designers_weight, publishers_weight
        )
        
        similarities.append({
            "id": owned_id,
            "name": owned_game.get("name", ""),
            "score": similarity
        })
    
    similarities.sort(key=lambda x: x["score"], reverse=True)
    return similarities[:top_k]