import sys
from pathlib import Path
import unittest
from unittest.mock import patch

# Path fix for local project imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.journey_planner import plan_journey

MOCK_SHAHBAG_COORDS = {"latitude": 23.738, "longitude": 90.395}
MOCK_MOTIJHEEL_COORDS = {"latitude": 23.729, "longitude": 90.418}


def mock_parse_travel_query_happy_path(query):
    return {
        "origin": "Shahbag",
        "destination": "Motijheel",
        "budget": None,
        "deadline_minutes": None,
        "preference": None
    }

def mock_geocode_place_happy_path(place_name):
    if "shahbag" in place_name.lower():
        return {"query": place_name, "display_name": "Shahbag, Dhaka", **MOCK_SHAHBAG_COORDS}
    if "motijheel" in place_name.lower():
        return {"query": place_name, "display_name": "Motijheel, Dhaka", **MOCK_MOTIJHEEL_COORDS}
    return None

def mock_get_current_weather_happy_path(lat, lon):
    return {
        "latitude": lat,
        "longitude": lon,
        "condition": "Clear",
        "temperature_c": 30.0,
    }


class TestMapGeometryOffline(unittest.TestCase):
    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_map_payload_present_and_valid(self, mock_weather, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        mock_geo.side_effect = mock_geocode_place_happy_path
        mock_weather.side_effect = mock_get_current_weather_happy_path

        result = plan_journey("Shahbag to Motijheel")
        
        self.assertGreater(len(result["recommendations"]), 0)
        
        for rec in result["recommendations"]:
            # Check map key exists
            self.assertIn("map", rec)
            map_data = rec["map"]
            
            # Check origin
            self.assertIn("origin", map_data)
            self.assertEqual(map_data["origin"]["lat"], MOCK_SHAHBAG_COORDS["latitude"])
            self.assertEqual(map_data["origin"]["lon"], MOCK_SHAHBAG_COORDS["longitude"])
            self.assertEqual(map_data["origin"]["name"], "Shahbag")
            
            # Check destination
            self.assertIn("destination", map_data)
            self.assertEqual(map_data["destination"]["lat"], MOCK_MOTIJHEEL_COORDS["latitude"])
            self.assertEqual(map_data["destination"]["lon"], MOCK_MOTIJHEEL_COORDS["longitude"])
            self.assertEqual(map_data["destination"]["name"], "Motijheel")
            
            # Check legs
            self.assertIn("legs", map_data)
            self.assertGreater(len(map_data["legs"]), 0)
            
            for leg in map_data["legs"]:
                self.assertIn("mode", leg)
                self.assertIn("frm", leg)
                self.assertIn("to", leg)
                
                # Verify coordinates
                self.assertIsInstance(leg["frm"]["lat"], float)
                self.assertIsInstance(leg["frm"]["lon"], float)
                self.assertIsInstance(leg["to"]["lat"], float)
                self.assertIsInstance(leg["to"]["lon"], float)
                
                # Lat/Lon boundaries
                self.assertTrue(-90 <= leg["frm"]["lat"] <= 90)
                self.assertTrue(-180 <= leg["frm"]["lon"] <= 180)
                self.assertTrue(-90 <= leg["to"]["lat"] <= 90)
                self.assertTrue(-180 <= leg["to"]["lon"] <= 180)

if __name__ == "__main__":
    unittest.main(verbosity=2)
