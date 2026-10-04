import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
import math
import time
from unittest.mock import patch, MagicMock
from requests.exceptions import Timeout, RequestException

from src.api.weather import (
    get_current_weather,
    WeatherError,
    _WEATHER_CACHE,
    WEATHER_CACHE_TTL_SECONDS
)

class TestWeatherOffline(unittest.TestCase):
    def setUp(self):
        # Clear cache before each test
        _WEATHER_CACHE.clear()
        
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_valid_clear_weather(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 60},
            "wind": {"speed": 4.5},
            "visibility": 10000
        }
        mock_get.return_value = mock_response
        
        result = get_current_weather(23.0, 90.0)
        self.assertEqual(result["condition"], "Clear")
        self.assertEqual(result["description"], "clear sky")
        self.assertEqual(result["temperature_c"], 25.0)
        self.assertEqual(result["feels_like_c"], 26.0)
        self.assertEqual(result["humidity_percent"], 60.0)
        self.assertEqual(result["wind_speed_mps"], 4.5)
        self.assertEqual(result["visibility_m"], 10000.0)
        self.assertEqual(result["rain_1h_mm"], 0.0)
        self.assertEqual(result["snow_1h_mm"], 0.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_valid_rain_weather(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weather": [{"main": "Rain", "description": "light rain"}],
            "main": {"temp": 22.0},
            "rain": {"1h": 2.5}
        }
        mock_get.return_value = mock_response
        
        result = get_current_weather(23.0, 90.0)
        self.assertEqual(result["condition"], "Rain")
        self.assertEqual(result["rain_1h_mm"], 2.5)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_valid_snow_weather(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weather": [{"main": "Snow", "description": "light snow"}],
            "main": {"temp": -5.0},
            "snow": {"1h": 1.2}
        }
        mock_get.return_value = mock_response
        
        result = get_current_weather(23.0, 90.0)
        self.assertEqual(result["condition"], "Snow")
        self.assertEqual(result["snow_1h_mm"], 1.2)
        
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_missing_visibility(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weather": [{"main": "Clouds"}],
            "main": {"temp": 22.0}
        }
        mock_get.return_value = mock_response
        
        result = get_current_weather(23.0, 90.0)
        self.assertIsNone(result["visibility_m"])

    def test_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            get_current_weather(-100.0, 90.0)
        with self.assertRaises(ValueError):
            get_current_weather(23.0, 200.0)
        with self.assertRaises(TypeError):
            get_current_weather(None, 90.0)
        with self.assertRaises(TypeError):
            get_current_weather("23.0", 90.0)
        with self.assertRaises(TypeError):
            get_current_weather(True, 90.0)
        with self.assertRaises(ValueError):
            get_current_weather(math.nan, 90.0)
        with self.assertRaises(ValueError):
            get_current_weather(math.inf, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_empty_json_object(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Received empty JSON object"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_non_object_json(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Response is not a JSON object"):
            get_current_weather(23.0, 90.0)
            
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_missing_weather_list(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"main": {"temp": 22.0}}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Missing or empty weather list"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_empty_weather_list(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"weather": [], "main": {"temp": 22.0}}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Missing or empty weather list"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_missing_main(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"weather": [{"main": "Clear"}]}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Missing main weather section"):
            get_current_weather(23.0, 90.0)
            
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_missing_temperature(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"weather": [{"main": "Clear"}], "main": {"humidity": 50}}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Missing temperature in response"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_malformed_temperature(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"weather": [{"main": "Clear"}], "main": {"temp": "hot"}}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Malformed temperature or humidity"):
            get_current_weather(23.0, 90.0)
            
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_malformed_humidity(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"weather": [{"main": "Clear"}], "main": {"temp": 25.0, "humidity": "none"}}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Malformed temperature or humidity"):
            get_current_weather(23.0, 90.0)
            
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_malformed_wind_speed(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"weather": [{"main": "Clear"}], "main": {"temp": 25.0}, "wind": {"speed": "fast"}}
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Malformed wind speed"):
            get_current_weather(23.0, 90.0)
            
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_timeout(self, mock_get, mock_api_key):
        mock_get.side_effect = Timeout("Timeout")
        
        with self.assertRaisesRegex(WeatherError, "timed out"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_connection_failure(self, mock_get, mock_api_key):
        mock_get.side_effect = RequestException("Connection Error")
        
        with self.assertRaisesRegex(WeatherError, "Network or HTTP error"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_http_error(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = RequestException("500 Server Error")
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Network or HTTP error"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_authentication_failure_401(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "OpenWeather authentication failed"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_rate_limit_429(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "OpenWeather rate limit exceeded"):
            get_current_weather(23.0, 90.0)
            
    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_invalid_json(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with self.assertRaisesRegex(WeatherError, "Invalid JSON from OpenWeather"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather.os.environ.get')
    def test_missing_api_key(self, mock_env_get):
        mock_env_get.return_value = ""
        
        with self.assertRaisesRegex(WeatherError, "OpenWeather API key is not configured"):
            get_current_weather(23.0, 90.0)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_cache_hit(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weather": [{"main": "Clear"}],
            "main": {"temp": 25.0}
        }
        mock_get.return_value = mock_response
        
        # First call hits API
        res1 = get_current_weather(23.1234, 90.1234)
        mock_get.assert_called_once()
        
        # Second call with same rounded coords hits cache
        res2 = get_current_weather(23.12341, 90.12344)
        mock_get.assert_called_once()  # Call count remains 1
        
        self.assertEqual(res1, res2)

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_expired_cache(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weather": [{"main": "Clear"}],
            "main": {"temp": 25.0}
        }
        mock_get.return_value = mock_response
        
        # Insert expired cache entry
        cache_key = (23.1234, 90.1234)
        _WEATHER_CACHE[cache_key] = (time.time() - WEATHER_CACHE_TTL_SECONDS - 10, {"old": "data"})
        
        # Call should hit API because cache is expired
        get_current_weather(23.1234, 90.1234)
        mock_get.assert_called_once()

    @patch('src.api.weather._get_api_key', return_value="fake_key")
    @patch('src.api.weather.requests.get')
    def test_cache_mutation_safety(self, mock_get, mock_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weather": [{"main": "Clear"}],
            "main": {"temp": 25.0}
        }
        mock_get.return_value = mock_response
        
        res1 = get_current_weather(23.0, 90.0)
        
        # Mutate the returned dictionary
        res1["temperature_c"] = 999.0
        
        # Second call gets from cache
        res2 = get_current_weather(23.0, 90.0)
        
        # Cache should remain unmutated (25.0, not 999.0)
        self.assertEqual(res2["temperature_c"], 25.0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
