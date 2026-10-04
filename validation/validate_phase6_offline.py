import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from unittest.mock import patch, Mock
import requests
from src.api.geocoding import geocode_place, GeocodingError, _GEOCODE_CACHE

class TestGeocodingOffline(unittest.TestCase):
    def setUp(self):
        # Clear cache before each test
        _GEOCODE_CACHE.clear()

    @patch("src.api.geocoding.requests.get")
    def test_valid_successful_response(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{
            "lat": "23.7340",
            "lon": "90.3928",
            "display_name": "Shahbag, Dhaka, Bangladesh"
        }]
        mock_get.return_value = mock_response

        result = geocode_place("Shahbag")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["query"], "Shahbag")
        self.assertEqual(result["latitude"], 23.7340)
        self.assertEqual(result["longitude"], 90.3928)
        self.assertEqual(result["display_name"], "Shahbag, Dhaka, Bangladesh")

    @patch("src.api.geocoding.requests.get")
    def test_empty_result_list(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = geocode_place("NowhereCity")
        self.assertIsNone(result)

    @patch("src.api.geocoding.requests.get")
    def test_malformed_response_not_list(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Not a list"}
        mock_get.return_value = mock_response

        with self.assertRaisesRegex(GeocodingError, "expected a JSON array"):
            geocode_place("Test")

    @patch("src.api.geocoding.requests.get")
    def test_missing_latitude(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{
            "lon": "90.3928",
            "display_name": "Test Place"
        }]
        mock_get.return_value = mock_response

        with self.assertRaisesRegex(GeocodingError, "Malformed geocoding response data"):
            geocode_place("Test")

    @patch("src.api.geocoding.requests.get")
    def test_invalid_coordinate_string(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{
            "lat": "not_a_number",
            "lon": "90.3928",
            "display_name": "Test Place"
        }]
        mock_get.return_value = mock_response

        with self.assertRaisesRegex(GeocodingError, "Malformed geocoding response data"):
            geocode_place("Test")

    @patch("src.api.geocoding.requests.get")
    def test_timeout_handling(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with self.assertRaisesRegex(GeocodingError, "timed out"):
            geocode_place("Test")

    @patch("src.api.geocoding.requests.get")
    def test_connection_failure_handling(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        with self.assertRaisesRegex(GeocodingError, "network/HTTP error"):
            geocode_place("Test")

    def test_empty_input(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty or whitespace"):
            geocode_place("")

    def test_whitespace_input(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty or whitespace"):
            geocode_place("   ")

    def test_none_input(self):
        with self.assertRaisesRegex(TypeError, "must be a string"):
            geocode_place(None)

    def test_numeric_input(self):
        with self.assertRaisesRegex(TypeError, "must be a string"):
            geocode_place(123)

    @patch("src.api.geocoding.requests.get")
    def test_cache_behavior(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{
            "lat": "23.7340",
            "lon": "90.3928",
            "display_name": "Shahbag, Dhaka, Bangladesh"
        }]
        mock_get.return_value = mock_response

        # First call, hits the mock API
        result1 = geocode_place("  SHAHBAG  ")
        self.assertEqual(mock_get.call_count, 1)

        # Second call, hits the cache (no additional API call)
        result2 = geocode_place("shahbag")
        self.assertEqual(mock_get.call_count, 1)

        self.assertEqual(result1, result2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
