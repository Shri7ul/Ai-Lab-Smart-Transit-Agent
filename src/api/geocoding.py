import os
import requests
from typing import Dict, Any, Optional

# In-memory lightweight cache
_GEOCODE_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}

USER_AGENT = "SmartTransit-UIU-AcademicProject/1.0"
DEFAULT_TIMEOUT = 10.0

class GeocodingError(Exception):
    """Application-level exception for geocoding failures."""
    pass

def _normalize_query(place_name: str) -> str:
    """Normalize query for caching."""
    return place_name.strip().casefold()

def geocode_place(place_name: str) -> Optional[Dict[str, Any]]:
    """
    Forward geocodes a textual place name into geographic coordinates using Nominatim.
    Returns a structured dict or None if the place is not found.
    Uses a lightweight in-memory cache to avoid repeated API calls.
    """
    if place_name is None or not isinstance(place_name, str):
        raise TypeError("Place name must be a string.")
    
    clean_name = place_name.strip()
    if not clean_name:
        raise ValueError("Place name cannot be empty or whitespace.")
        
    cache_key = _normalize_query(clean_name)
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]
        
    api_url = os.getenv("NOMINATIM_API_URL", "https://nominatim.openstreetmap.org")
    endpoint = f"{api_url.rstrip('/')}/search"
    
    params = {
        "q": clean_name,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "bd"
    }
    
    headers = {
        "User-Agent": USER_AGENT
    }
    
    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout as e:
        raise GeocodingError(f"Nominatim request timed out: {e}") from e
    except requests.exceptions.RequestException as e:
        raise GeocodingError(f"Nominatim network/HTTP error: {e}") from e
    except ValueError as e:
        raise GeocodingError(f"Invalid JSON response from Nominatim: {e}") from e

    if not isinstance(data, list):
        raise GeocodingError("Unexpected response structure: expected a JSON array.")

    if not data:
        # No results found
        _GEOCODE_CACHE[cache_key] = None
        return None
        
    result = data[0]
    
    try:
        lat = float(result["lat"])
        lon = float(result["lon"])
        display_name = result["display_name"]
    except (KeyError, ValueError, TypeError) as e:
        raise GeocodingError(f"Malformed geocoding response data: {e}") from e
        
    # Boundary check for standard coordinate values
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise GeocodingError(f"Invalid coordinate bounds returned: lat={lat}, lon={lon}")

    structured_result = {
        "query": clean_name,
        "display_name": display_name,
        "latitude": lat,
        "longitude": lon
    }
    
    _GEOCODE_CACHE[cache_key] = structured_result
    return structured_result
