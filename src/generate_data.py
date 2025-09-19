import argparse
import json
import os
import sys
import logging
from typing import Dict, Any, List, Tuple

from bgg import get_collection, get_things, search_games
from similarity import compute_similarity_edges, compute_cross_similarities

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate JSON data for the web app (nodes.json, edges.json, recs.json).")
    parser.add_argument("--username", required=True, help="BGG username")
    parser.add_argument("--edge-threshold", type=float, default=0.35, help="Similarity threshold [0..1]")
    parser.add_argument("--out-dir", default="data", help="Output directory for JSON files")
    parser.add_argument("--skip-recs", action="store_true", help="Skip generating recommendations")
    parser.add_argument("--rec-search-terms", nargs="+", 
                       default=["strategy", "euro", "engine building", "worker placement", "deck building"],
                       help="Search terms for finding recommendation candidates")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    log.info(f"Fetching collection for '{args.username}'...")
    collection = get_collection(args.username)
    if not collection:
        log.error("No items returned. Ensure the username is correct and collection is public.")
        sys.exit(1)

    ids = [item["id"] for item in collection]
    log.info(f"Found {len(ids)} owned games. Fetching details...")
    details = get_things(ids)

    # Fill missing names from collection, if needed
    for item in collection:
        gid = item["id"]
        if gid in details and not details[gid].get("name"):
            details[gid]["name"] = item.get("name")

    log.info("Computing similarities...")
    edges_list = compute_similarity_edges(details, edge_threshold=args.edge_threshold)
    log.info(f"Built {len(edges_list)} edges with threshold {args.edge_threshold}.")

    # Serialize nodes and edges for the frontend
    nodes = []
    for gid, g in details.items():
        nodes.append({
            "id": gid,
            "label": g.get("name"),
            "name": g.get("name"),
            "mechanics": [m.get("name") for m in g.get("mechanics", [])],
            "categories": [c.get("name") for c in g.get("categories", [])],
            "averageweight": g.get("averageweight"),
            "averagerating": g.get("averagerating"),
            "playingtime": g.get("playingtime"),
            "minplayers": g.get("minplayers"),
            "maxplayers": g.get("maxplayers"),
            "bggUrl": f"https://boardgamegeek.com/boardgame/{gid}",
        })

    edges = [{"source": a, "target": b, "weight": w} for a, b, w in edges_list]

    nodes_path = os.path.join(args.out_dir, "nodes.json")
    edges_path = os.path.join(args.out_dir, "edges.json")
    with open(nodes_path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    with open(edges_path, "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)

    log.info(f"Wrote {nodes_path}")
    log.info(f"Wrote {edges_path}")

    # Generate recommendations if not skipped
    if not args.skip_recs:
        log.info("Generating recommendations...")
        recommendations = generate_recommendations(details, args.rec_search_terms)
        
        recs_path = os.path.join(args.out_dir, "recs.json")
        with open(recs_path, "w", encoding="utf-8") as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)
        
        log.info(f"Wrote {recs_path}")
    else:
        log.info("Skipping recommendations generation")


def generate_recommendations(owned_games: Dict[str, Dict[str, Any]], 
                           search_terms: List[str],
                           candidates_per_term: int = 15,
                           max_candidates: int = 100) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate game recommendations by searching for candidates and computing similarities.
    """
    log.info(f"Searching for recommendation candidates using {len(search_terms)} search terms...")
    
    # Collect candidate games from search terms
    candidate_games = {}
    owned_ids = set(owned_games.keys())
    
    for term in search_terms:
        log.info(f"Searching for: {term}")
        search_results = search_games(term, limit=candidates_per_term)
        
        for result in search_results:
            candidate_id = result["id"]
            # Skip games already owned
            if candidate_id not in owned_ids:
                candidate_games[candidate_id] = {
                    "id": candidate_id,
                    "name": result["name"],
                    "year": result.get("year")
                }
    
    log.info(f"Found {len(candidate_games)} unique candidate games")
    
    # Limit candidates to avoid too many API calls
    if len(candidate_games) > max_candidates:
        log.info(f"Limiting to {max_candidates} candidates")
        candidate_ids = list(candidate_games.keys())[:max_candidates]
        candidate_games = {cid: candidate_games[cid] for cid in candidate_ids}
    
    # Fetch detailed information for candidates
    if candidate_games:
        log.info("Fetching detailed information for candidates...")
        candidate_details = get_things(list(candidate_games.keys()))
        
        # Compute cross-similarities between owned games and candidates
        recommendations = compute_cross_similarities(owned_games, candidate_details, top_k=5)
        
        return recommendations
    else:
        log.warning("No candidate games found")
        return {}

if __name__ == "__main__":
    main()