"""
BoardGameGeek XML API interface module.
This module provides functions to fetch collection and game details from the BGG API.
"""

import requests
import xmltodict
import time
import logging
from typing import List, Dict, Any

log = logging.getLogger(__name__)

def get_collection(username: str) -> List[Dict[str, Any]]:
    """
    Fetch a user's BoardGameGeek collection.
    
    Args:
        username: BGG username
        
    Returns:
        List of games in the collection with basic info
    """
    url = f"https://www.boardgamegeek.com/xmlapi2/collection?username={username}&own=1"
    
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            log.info(f"Fetching collection for {username} (attempt {attempt + 1})")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 202:
                # BGG API returns 202 when data is being processed, need to wait and retry
                log.info("BGG API returned 202, waiting and retrying...")
                time.sleep(retry_delay * (attempt + 1))
                continue
                
            if response.status_code != 200:
                log.error(f"HTTP {response.status_code}: {response.text}")
                if attempt == max_retries - 1:
                    return []
                time.sleep(retry_delay)
                continue
                
            # Parse XML response
            data = xmltodict.parse(response.content)
            
            if 'items' not in data or 'item' not in data['items']:
                log.warning("No items found in collection")
                return []
                
            items = data['items']['item']
            if not isinstance(items, list):
                items = [items]  # Single item case
                
            collection = []
            for item in items:
                game_id = int(item['@objectid'])
                name = item.get('name', {}).get('#text', 'Unknown')
                
                collection.append({
                    'id': game_id,
                    'name': name
                })
                
            log.info(f"Found {len(collection)} games in collection")
            return collection
            
        except requests.exceptions.RequestException as e:
            log.error(f"Request failed: {e}")
            if attempt == max_retries - 1:
                return []
            time.sleep(retry_delay)
            
    return []

def get_things(game_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Fetch detailed information for a list of games.
    
    Args:
        game_ids: List of BGG game IDs
        
    Returns:
        Dictionary mapping game ID to game details
    """
    if not game_ids:
        return {}
        
    # BGG API can handle up to 20 games at once, so batch the requests
    batch_size = 20
    all_details = {}
    
    for i in range(0, len(game_ids), batch_size):
        batch = game_ids[i:i + batch_size]
        batch_details = _fetch_game_batch(batch)
        all_details.update(batch_details)
        
        # Rate limiting - be nice to BGG API
        time.sleep(1)
        
    return all_details

def _fetch_game_batch(game_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Fetch details for a batch of games."""
    ids_str = ','.join(map(str, game_ids))
    url = f"https://www.boardgamegeek.com/xmlapi2/thing?id={ids_str}&stats=1"
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            log.info(f"Fetching details for {len(game_ids)} games (attempt {attempt + 1})")
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                log.error(f"HTTP {response.status_code}: {response.text}")
                if attempt == max_retries - 1:
                    return {}
                time.sleep(retry_delay)
                continue
                
            # Parse XML response
            data = xmltodict.parse(response.content)
            
            if 'items' not in data or 'item' not in data['items']:
                log.warning("No items found in response")
                return {}
                
            items = data['items']['item']
            if not isinstance(items, list):
                items = [items]  # Single item case
                
            details = {}
            for item in items:
                game_id = int(item['@id'])
                
                # Extract game name
                names = item.get('name', [])
                if not isinstance(names, list):
                    names = [names]
                primary_name = next((n.get('#text') for n in names if n.get('@type') == 'primary'), 'Unknown')
                
                # Extract mechanics
                mechanics = []
                links = item.get('link', [])
                if not isinstance(links, list):
                    links = [links]
                for link in links:
                    if link.get('@type') == 'boardgamemechanic':
                        mechanics.append({'name': link.get('@value', '')})
                
                # Extract categories  
                categories = []
                for link in links:
                    if link.get('@type') == 'boardgamecategory':
                        categories.append({'name': link.get('@value', '')})
                
                # Extract statistics
                stats = item.get('statistics', {}).get('ratings', {})
                
                details[game_id] = {
                    'name': primary_name,
                    'mechanics': mechanics,
                    'categories': categories,
                    'averageweight': float(stats.get('averageweight', {}).get('@value', 0)) or None,
                    'averagerating': float(stats.get('average', {}).get('@value', 0)) or None,
                    'playingtime': int(item.get('playingtime', {}).get('@value', 0)) or None,
                    'minplayers': int(item.get('minplayers', {}).get('@value', 0)) or None,
                    'maxplayers': int(item.get('maxplayers', {}).get('@value', 0)) or None,
                }
                
            log.info(f"Successfully parsed {len(details)} games")
            return details
            
        except requests.exceptions.RequestException as e:
            log.error(f"Request failed: {e}")
            if attempt == max_retries - 1:
                return {}
            time.sleep(retry_delay)
        except Exception as e:
            log.error(f"Parsing failed: {e}")
            if attempt == max_retries - 1:
                return {}
            time.sleep(retry_delay)
            
    return {}