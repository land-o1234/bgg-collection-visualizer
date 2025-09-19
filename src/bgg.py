"""
BGG (BoardGameGeek) XML API client.
Fetches collection and game details from BGG XML API.
"""
import time
import logging
from typing import List, Dict, Any, Optional
import requests
import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

BGG_API_BASE = "https://boardgamegeek.com/xmlapi2"
RETRY_DELAY = 1.5  # initial delay between retries (exponential backoff)
MAX_RETRIES = 3
SEARCH_MAX_RETRIES = 5  # search endpoint needs more retries
REQUEST_TIMEOUT = 60  # increased timeout for better reliability


def _request_with_retry(url: str, params: Dict[str, Any] = None, max_retries: int = None) -> Optional[ET.Element]:
    """Make a request to BGG API with retry logic for rate limiting and timeouts."""
    if max_retries is None:
        max_retries = MAX_RETRIES
    
    for attempt in range(max_retries):
        delay = RETRY_DELAY * (2 ** attempt)  # exponential backoff
        
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                # Parse XML
                root = ET.fromstring(response.content)
                return root
            elif response.status_code == 202:
                # BGG returns 202 when data is being processed, retry after delay
                log.info(f"BGG processing request, retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                log.warning(f"BGG API returned status {response.status_code}, retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
                
        except requests.exceptions.Timeout as e:
            log.warning(f"Request timed out after {REQUEST_TIMEOUT}s (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                log.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
        except requests.RequestException as e:
            log.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                log.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
        except ET.ParseError as e:
            log.warning(f"XML parse failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                log.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
    
    log.error(f"Failed to fetch from {url} after {max_retries} attempts")
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
    
    root = _request_with_retry(url, params)
    if root is None:
        return []
    
    # Extract items from response
    collection = []
    for item in root.findall("item"):
        game_id = item.get("objectid")
        name_elem = item.find("name")
        name = name_elem.text if name_elem is not None else ""
        
        year_elem = item.find("yearpublished")
        year = year_elem.text if year_elem is not None else None
        
        thumbnail_elem = item.find("thumbnail")
        thumbnail = thumbnail_elem.text if thumbnail_elem is not None else None
        
        if game_id:
            collection.append({
                "id": game_id,
                "name": name,
                "year": year,
                "thumbnail": thumbnail
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
        
        root = _request_with_retry(url, params)
        if root is None:
            log.warning(f"Failed to fetch batch starting at index {i}")
            continue
        
        # Process each game in the batch
        for item in root.findall("item"):
            game_id = item.get("id")
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


def _extract_game_details(item: ET.Element) -> Dict[str, Any]:
    """Extract and normalize game details from BGG API response."""
    
    def safe_get_int(text: str, fallback: int = 0) -> int:
        """Safely convert text to int."""
        try:
            return int(text) if text else fallback
        except (ValueError, TypeError):
            return fallback
    
    def safe_get_float(text: str, fallback: float = 0.0) -> float:
        """Safely convert text to float."""
        try:
            return float(text) if text else fallback
        except (ValueError, TypeError):
            return fallback
    
    # Basic info
    details = {
        "id": item.get("id"),
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
    
    # Name (find primary name first)
    names = item.findall("name")
    for name in names:
        if name.get("type") == "primary":
            details["name"] = name.get("value", "")
            break
    
    # If no primary name found, use first name
    if not details["name"] and names:
        details["name"] = names[0].get("value", "")
    
    # Description
    description = item.find("description")
    details["description"] = description.text if description is not None else ""
    
    # Year published
    year = item.find("yearpublished")
    details["year"] = safe_get_int(year.get("value")) if year is not None else None
    
    # Player counts and time
    minplayers = item.find("minplayers")
    details["minplayers"] = safe_get_int(minplayers.get("value")) if minplayers is not None else None
    
    maxplayers = item.find("maxplayers")
    details["maxplayers"] = safe_get_int(maxplayers.get("value")) if maxplayers is not None else None
    
    playingtime = item.find("playingtime")
    details["playingtime"] = safe_get_int(playingtime.get("value")) if playingtime is not None else None
    
    minage = item.find("minage")
    details["minage"] = safe_get_int(minage.get("value")) if minage is not None else None
    
    # Ratings from statistics
    statistics = item.find("statistics")
    if statistics is not None:
        ratings = statistics.find("ratings")
        if ratings is not None:
            # Average rating
            average = ratings.find("average")
            details["averagerating"] = safe_get_float(average.get("value")) if average is not None else None
            
            # Average weight
            averageweight = ratings.find("averageweight")
            details["averageweight"] = safe_get_float(averageweight.get("value")) if averageweight is not None else None
    
    # Links (mechanics, categories, etc.)
    links = item.findall("link")
    for link in links:
        link_type = link.get("type", "")
        link_value = link.get("value", "")
        link_id = link.get("id", "")
        
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
    Uses increased retry count since search endpoint is particularly slow.
    """
    log.info(f"Searching BGG for: {query}")
    
    url = f"{BGG_API_BASE}/search"
    params = {
        "query": query,
        "type": "boardgame",
        "exact": "0"
    }
    
    # Use increased retry count for search endpoint
    root = _request_with_retry(url, params, max_retries=SEARCH_MAX_RETRIES)
    if root is None:
        return []
    
    results = []
    items = root.findall("item")
    
    for item in items[:limit]:
        game_id = item.get("id")
        name = item.find("name")
        name_text = name.get("value") if name is not None else ""
        
        year = item.find("yearpublished")
        year_text = year.get("value") if year is not None else None
        
        if game_id and name_text:
            results.append({
                "id": game_id,
                "name": name_text,
                "year": year_text
            })
    
    log.info(f"Found {len(results)} games matching '{query}'")
    return results