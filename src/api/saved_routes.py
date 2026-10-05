import os
import requests
from typing import Dict, Any, List

class SavedRoutesConfigurationError(Exception):
    pass

class SavedRoutesError(Exception):
    pass

def get_supabase_headers() -> Dict[str, str]:
    supabase_url = os.getenv("SUPABASE_URL")
    secret_key = os.getenv("SUPABASE_SECRET_KEY")
    
    if not supabase_url or not secret_key:
        raise SavedRoutesConfigurationError("SUPABASE_URL or SUPABASE_SECRET_KEY is missing.")
        
    return {
        "apikey": secret_key,
        "Content-Type": "application/json"
    }

def sanitize_route_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw_data, dict):
        return {}
    
    allowed_keys = [
        "cost_bdt", "time_min", "transfers", "walk_km",
        "mode_sequence", "departure_time", "arrival_time", "rank",
        "cost", "time", "walking", "modes"
    ]
    
    sanitized = {}
    for k in allowed_keys:
        if k in raw_data:
            val = raw_data[k]
            if isinstance(val, (int, float, str, type(None))):
                sanitized[k] = val
                
    return sanitized

def get_saved_routes(user_id: str) -> List[Dict[str, Any]]:
    headers = get_supabase_headers()
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/saved_routes?user_id=eq.{user_id}&order=created_at.desc"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException:
        raise SavedRoutesError("Saved routes are temporarily unavailable. Please try again.")
        
    if response.status_code != 200:
        raise SavedRoutesError("Saved routes are temporarily unavailable. Please try again.")
        
    return response.json()

def save_route(user_id: str, origin: str, destination: str, route_data: Dict[str, Any]) -> Dict[str, Any]:
    headers = get_supabase_headers()
    headers["Prefer"] = "return=representation"
    
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/saved_routes"
    
    # Simple duplicate check
    query_url = f"{url}?user_id=eq.{user_id}&origin=eq.{origin}&destination=eq.{destination}&select=id,route_data"
    
    try:
        existing_resp = requests.get(query_url, headers=headers, timeout=10)
        if existing_resp.status_code == 200:
            existing_routes = existing_resp.json()
            for r in existing_routes:
                existing_rd = r.get("route_data", {})
                
                # Simple fingerprint matching
                if (existing_rd.get("time") == route_data.get("time") and 
                    existing_rd.get("modes") == route_data.get("modes")):
                    return {"success": True, "already_saved": True, "data": r}
                    
        payload = {
            "user_id": user_id,
            "origin": origin,
            "destination": destination,
            "route_data": route_data
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
    except requests.exceptions.RequestException:
        raise SavedRoutesError("Saved routes are temporarily unavailable. Please try again.")
        
    if response.status_code not in (200, 201):
        raise SavedRoutesError("Saved routes are temporarily unavailable. Please try again.")
        
    data = response.json()
    return {"success": True, "already_saved": False, "data": data[0] if data else {}}

def delete_saved_route(route_id: str, user_id: str) -> bool:
    headers = get_supabase_headers()
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/saved_routes?id=eq.{route_id}&user_id=eq.{user_id}"
    
    headers["Prefer"] = "return=representation"
    
    try:
        response = requests.delete(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException:
        raise SavedRoutesError("Saved routes are temporarily unavailable. Please try again.")
    
    if response.status_code not in (200, 204):
        return False
        
    # If returned 200 with empty array, it means no rows matched
    try:
        data = response.json()
    except ValueError:
        return False
        
    if not data:
        return False
        
    return True
