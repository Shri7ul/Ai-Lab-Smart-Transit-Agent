import os
import math
import time
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables (e.g. OPENWEATHER_API_KEY)
load_dotenv()

OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_CACHE_TTL_SECONDS = 300
REQUEST_TIMEOUT_SEC = 10.0

# In-memory cache for weather results: { (lat_round, lon_round): (timestamp, result_dict) }
_WEATHER_CACHE: Dict[tuple, tuple] = {}

class WeatherError(Exception):
    """Custom exception for all weather-related failures."""
    pass

def _get_api_key() -> str:
    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not key:
        raise WeatherError("OpenWeather API key is not configured in the environment.")
    return key

def _validate_coordinates(latitude: Any, longitude: Any):
    if latitude is None or longitude is None:
        raise TypeError("Coordinates cannot be None.")
        
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        raise TypeError("Coordinates cannot be booleans.")
        
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise TypeError("Coordinates must be numeric.")
        
    if math.isnan(latitude) or math.isnan(longitude) or math.isinf(latitude) or math.isinf(longitude):
        raise ValueError("Coordinates cannot be NaN or infinite.")
        
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        raise ValueError("Coordinates are out of standard geographic bounds.")

def _fetch_from_api(lat: float, lon: float) -> Dict[str, Any]:
    api_key = _get_api_key()
    
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        response = requests.get(OPENWEATHER_API_URL, params=params, timeout=REQUEST_TIMEOUT_SEC)
        
        if response.status_code == 401:
            raise WeatherError("OpenWeather authentication failed.")
        elif response.status_code == 429:
            raise WeatherError("OpenWeather rate limit exceeded.")
        
        response.raise_for_status()
        
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Response is not a JSON object.")
            
        return data
        
    except requests.exceptions.Timeout as e:
        raise WeatherError("Request to OpenWeather timed out.") from e
    except requests.exceptions.RequestException as e:
        raise WeatherError(f"Network or HTTP error during OpenWeather request: {e}") from e
    except ValueError as e:
        raise WeatherError(f"Invalid JSON from OpenWeather: {e}") from e

def _parse_normalized_weather(data: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
    if not data:
        raise WeatherError("Received empty JSON object from OpenWeather.")
        
    weather_list = data.get("weather")
    if not weather_list or not isinstance(weather_list, list) or len(weather_list) == 0:
        raise WeatherError("Missing or empty weather list in response.")
        
    main_section = data.get("main")
    if not main_section or not isinstance(main_section, dict):
        raise WeatherError("Missing main weather section in response.")
        
    if "temp" not in main_section:
        raise WeatherError("Missing temperature in response.")
        
    try:
        temp_c = float(main_section["temp"])
        feels_like_c = float(main_section.get("feels_like", temp_c))
        humidity = float(main_section.get("humidity", 0))
    except (TypeError, ValueError) as e:
        raise WeatherError(f"Malformed temperature or humidity data: {e}") from e
        
    wind_section = data.get("wind", {})
    try:
        wind_speed_mps = float(wind_section.get("speed", 0.0))
    except (TypeError, ValueError) as e:
        raise WeatherError(f"Malformed wind speed data: {e}") from e
        
    # Extract condition and description safely
    condition = str(weather_list[0].get("main", "Unknown"))
    description = str(weather_list[0].get("description", "unknown"))
    
    # Visibility
    visibility = data.get("visibility")
    if visibility is not None:
        try:
            visibility = float(visibility)
        except (TypeError, ValueError):
            visibility = None
            
    # Rain and Snow
    rain_section = data.get("rain", {})
    snow_section = data.get("snow", {})
    
    try:
        rain_1h = float(rain_section.get("1h", 0.0))
    except (TypeError, ValueError):
        rain_1h = 0.0
        
    try:
        snow_1h = float(snow_section.get("1h", 0.0))
    except (TypeError, ValueError):
        snow_1h = 0.0
        
    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "condition": condition,
        "description": description,
        "temperature_c": temp_c,
        "feels_like_c": feels_like_c,
        "humidity_percent": humidity,
        "wind_speed_mps": wind_speed_mps,
        "visibility_m": visibility,
        "rain_1h_mm": rain_1h,
        "snow_1h_mm": snow_1h
    }

def get_current_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetches and normalizes the current weather for a given location.
    
    Args:
        latitude: float, coordinate latitude
        longitude: float, coordinate longitude
        
    Returns:
        A normalized dictionary of weather conditions.
    """
    _validate_coordinates(latitude, longitude)
    
    # Generate cache key rounding to 4 decimal places (~11 meters resolution)
    cache_key = (round(latitude, 4), round(longitude, 4))
    
    current_time = time.time()
    
    # Check cache
    if cache_key in _WEATHER_CACHE:
        timestamp, cached_result = _WEATHER_CACHE[cache_key]
        if current_time - timestamp < WEATHER_CACHE_TTL_SECONDS:
            return cached_result.copy()
            
    # Fetch from API
    raw_data = _fetch_from_api(latitude, longitude)
    
    # Normalize
    normalized_result = _parse_normalized_weather(raw_data, latitude, longitude)
    
    # Store in cache
    _WEATHER_CACHE[cache_key] = (current_time, normalized_result)
    
    return normalized_result.copy()
