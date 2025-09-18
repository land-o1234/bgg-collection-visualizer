import argparse
import json
import os
import sys
import logging
from typing import Dict, Any, List, Tuple

from bgg import get_collection, get_things
from similarity import compute_similarity_edges

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate JSON data for the web app (nodes.json, edges.json).")
    parser.add_argument("--username", required=True, help="BGG username")
    parser.add_argument("--edge-threshold", type=float, default=0.35, help="Similarity threshold [0..1]")
    parser.add_argument("--out-dir", default="data", help="Output directory for JSON files")
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

if __name__ == "__main__":
    main()