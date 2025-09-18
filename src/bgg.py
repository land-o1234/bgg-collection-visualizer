"""
BGG (BoardGameGeek) XML API client.
Fetches collection and game details from BGG XML API.
"""
import time
import logging
from typing import List, Dict, Any, Optional
import requests
import xmltodict

log = logging.getLogger(__name__)

BGG_API_BASE = "https://boardgamegeek.com/xmlapi2"
RETRY_DELAY = 1.5  # seconds between retries
MAX_RETRIES = 3


def _request_with_retry(url: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    """Make a request to BGG API with retry logic for rate limiting."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                # Parse XML to dict
                data = xmltodict.parse(response.content)
                return data
            elif response.status_code == 202:
                # BGG returns 202 when data is being processed, retry after delay
                log.info(f"BGG processing request, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                log.warning(f"BGG API returned status {response.status_code}, retrying...")
                time.sleep(RETRY_DELAY)
                continue
                
        except requests.RequestException as e:
            log.warning(f"Request failed: {e}, retrying...")
            time.sleep(RETRY_DELAY)
            continue
    
    log.error(f"Failed to fetch from {url} after {MAX_RETRIES} attempts")
    return None


def get_collection(username: str) -> List[Dict[str, Any]]:
    """
    Fetch a user's owned board game collection from BGG.
    Returns list of items with id, name, and other basic info.
    Filters out expansions and includes only owned games.
    """
    log.info(f"Fetching collection for user: {username}")
    
    url = f"{BGG_API_BASE}/collection"
    params = {
        "username": username,
        "own": "1",  # Only owned items
        "excludesubtype": "boardgameexpansion",  # Exclude expansions
        "stats": "1"  # Include stats
    }
    
    data = _request_with_retry(url, params)
    if not data:
        return []
    
    # Extract items from response
    items_data = data.get("items", {})
    if not items_data:
        return []
    
    # Handle single item vs multiple items
    items = items_data.get("item", [])
    if not isinstance(items, list):
        items = [items]
    
    # Extract relevant fields
    collection = []
    for item in items:
        if not item:
            continue
            
        # Get basic info
        game_id = item.get("@objectid")
        name = item.get("name", {})
        if isinstance(name, dict):
            name = name.get("#text", "")
        
        if game_id:
            collection.append({
                "id": game_id,
                "name": name,
                "year": item.get("yearpublished", {}).get("#text") if isinstance(item.get("yearpublished"), dict) else item.get("yearpublished"),
                "thumbnail": item.get("thumbnail", {}).get("#text") if isinstance(item.get("thumbnail"), dict) else item.get("thumbnail")
            })
    
    log.info(f"Found {len(collection)} owned games for {username}")
    return collection


def get_things(game_ids: List[str], batch_size: int = 20) -> Dict[str, Dict[str, Any]]:
    """
    Fetch detailed information for a list of game IDs from BGG.
    Returns dict mapping game_id -> game details.
    Processes in batches to avoid overwhelming the API.
    """
    if not game_ids:
        return {}
    
    log.info(f"Fetching details for {len(game_ids)} games...")
    
    all_details = {}
    
    # Process in batches
    for i in range(0, len(game_ids), batch_size):
        batch = game_ids[i:i + batch_size]
        log.info(f"Processing batch {i//batch_size + 1}/{(len(game_ids) + batch_size - 1)//batch_size} ({len(batch)} games)")
        
        url = f"{BGG_API_BASE}/thing"
        params = {
            "id": ",".join(str(gid) for gid in batch),
            "stats": "1"
        }
        
        data = _request_with_retry(url, params)
        if not data:
            log.warning(f"Failed to fetch batch starting at index {i}")
            continue
        
        # Extract items
        items_data = data.get("items", {})
        if not items_data:
            continue
            
        items = items_data.get("item", [])
        if not isinstance(items, list):
            items = [items]
        
        # Process each game in the batch
        for item in items:
            if not item:
                continue
                
            game_id = item.get("@id")
            if not game_id:
                continue
            
            # Extract game details
            game_details = _extract_game_details(item)
            all_details[game_id] = game_details
        
        # Small delay between batches to be nice to BGG
        if i + batch_size < len(game_ids):
            time.sleep(0.5)
    
    log.info(f"Successfully fetched details for {len(all_details)} games")
    return all_details


def _extract_game_details(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and normalize game details from BGG API response."""
    
    def safe_get_text(obj, fallback=None):
        """Safely extract text from BGG API objects."""
        if isinstance(obj, dict):
            return obj.get("#text", fallback)
        return obj or fallback
    
    def safe_get_float(obj, fallback=0.0):
        """Safely convert to float."""
        try:
            if isinstance(obj, dict):
                val = obj.get("#text")
            else:
                val = obj
            return float(val) if val is not None else fallback
        except (ValueError, TypeError):
            return fallback
    
    def safe_get_int(obj, fallback=0):
        """Safely convert to int."""
        try:
            if isinstance(obj, dict):
                val = obj.get("#text")
            else:
                val = obj
            return int(val) if val is not None else fallback
        except (ValueError, TypeError):
            return fallback
    
    # Basic info
    details = {
        "id": item.get("@id"),
        "name": "",
        "description": "",
        "year": None,
        "minplayers": None,
        "maxplayers": None,
        "playingtime": None,
        "minage": None,
        "averagerating": None,
        "averageweight": None,
        "mechanics": [],
        "categories": [],
        "families": [],
        "designers": [],
        "publishers": []
    }
    
    # Name (primary name)
    names = item.get("name", [])
    if not isinstance(names, list):
        names = [names] if names else []
    
    for name in names:
        if isinstance(name, dict) and name.get("@type") == "primary":
            details["name"] = safe_get_text(name.get("@value"))
            break
    
    # If no primary name found, use first name
    if not details["name"] and names:
        first_name = names[0]
        if isinstance(first_name, dict):
            details["name"] = safe_get_text(first_name.get("@value"))
    
    # Description
    description = item.get("description")
    details["description"] = safe_get_text(description, "")
    
    # Year published
    year = item.get("yearpublished")
    details["year"] = safe_get_int(year)
    
    # Player counts and time
    details["minplayers"] = safe_get_int(item.get("minplayers"))
    details["maxplayers"] = safe_get_int(item.get("maxplayers"))
    details["playingtime"] = safe_get_int(item.get("playingtime"))
    details["minage"] = safe_get_int(item.get("minage"))
    
    # Ratings
    statistics = item.get("statistics", {})
    ratings = statistics.get("ratings", {}) if statistics else {}
    
    details["averagerating"] = safe_get_float(ratings.get("average"))
    details["averageweight"] = safe_get_float(ratings.get("averageweight"))
    
    # Links (mechanics, categories, etc.)
    links = item.get("link", [])
    if not isinstance(links, list):
        links = [links] if links else []
    
    for link in links:
        if not isinstance(link, dict):
            continue
            
        link_type = link.get("@type", "")
        link_value = link.get("@value", "")
        link_id = link.get("@id", "")
        
        link_obj = {"id": link_id, "name": link_value}
        
        if link_type == "boardgamemechanic":
            details["mechanics"].append(link_obj)
        elif link_type == "boardgamecategory":
            details["categories"].append(link_obj)
        elif link_type == "boardgamefamily":
            details["families"].append(link_obj)
        elif link_type == "boardgamedesigner":
            details["designers"].append(link_obj)
        elif link_type == "boardgamepublisher":
            details["publishers"].append(link_obj)
    
    return details


def search_games(query: str, limit: int = 25) -> List[Dict[str, Any]]:
    """
    Search for games by name on BGG.
    Returns list of games with basic info.
    """
    log.info(f"Searching BGG for: {query}")
    
    url = f"{BGG_API_BASE}/search"
    params = {
        "query": query,
        "type": "boardgame",
        "exact": "0"
    }
    
    data = _request_with_retry(url, params)
    if not data:
        return []
    
    items_data = data.get("items", {})
    if not items_data:
        return []
    
    items = items_data.get("item", [])
    if not isinstance(items, list):
        items = [items]
    
    results = []
    for item in items[:limit]:
        if not item:
            continue
            
        game_id = item.get("@id")
        name = item.get("name", {})
        if isinstance(name, dict):
            name = name.get("@value", "")
        year = item.get("yearpublished", {})
        if isinstance(year, dict):
            year = year.get("@value")
        
        if game_id and name:
            results.append({
                "id": game_id,
                "name": name,
                "year": year
            })
    
    log.info(f"Found {len(results)} games matching '{query}'")
    return results