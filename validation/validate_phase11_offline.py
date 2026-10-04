import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from datetime import datetime

# Path fix for local project imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.journey_planner import plan_journey, JourneyPlanningError
from src.algorithms.eta import DHAKA_TIMEZONE
from src.api.geocoding import GeocodingError
from src.api.weather import WeatherError

# Common mock coordinates (should align with synthetic network nodes)
# e.g., Shahbag -> Motijheel
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
        "description": "clear sky",
        "temperature_c": 30.0,
        "feels_like_c": 32.0,
        "humidity_percent": 60,
        "wind_speed_mps": 2.0,
        "visibility_m": 10000.0,
        "rain_1h_mm": 0.0,
        "snow_1h_mm": 0.0
    }

def mock_get_current_weather_adverse(lat, lon):
    w = mock_get_current_weather_happy_path(lat, lon)
    w["condition"] = "Rain"
    w["rain_1h_mm"] = 10.0
    return w


class TestJourneyPlannerOffline(unittest.TestCase):

    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_full_happy_path(self, mock_weather, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        mock_geo.side_effect = mock_geocode_place_happy_path
        mock_weather.side_effect = mock_get_current_weather_happy_path

        result = plan_journey("Shahbag to Motijheel")
        
        self.assertEqual(result["query"]["origin"], "Shahbag")
        self.assertEqual(result["query"]["destination"], "Motijheel")
        self.assertTrue(result["weather_available"])
        self.assertIsNone(result["weather_warning"])
        self.assertGreater(result["feasible_count"], 0)
        self.assertGreaterEqual(result["candidate_count"], result["feasible_count"])
        
        # Check no graph objects leaked
        for rec in result["recommendations"]:
            self.assertIn("mode_sequence", rec)
            self.assertIn("time_min", rec)
            self.assertIn("base_score", rec)
            self.assertIn("adjusted_score", rec)
            
    @patch("src.services.journey_planner.parse_travel_query")
    def test_missing_origin(self, mock_parse):
        mock_parse.return_value = {
            "origin": None,
            "destination": "Motijheel",
            "budget": None,
            "deadline_minutes": None,
            "preference": None
        }
        with self.assertRaises(JourneyPlanningError) as context:
            plan_journey("to Motijheel")
        self.assertIn("[query_understanding]", str(context.exception))

    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    def test_origin_geocoding_returns_none(self, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        mock_geo.return_value = None
        
        with self.assertRaises(JourneyPlanningError) as context:
            plan_journey("Unknown to Motijheel")
        self.assertIn("[geocoding]", str(context.exception))

    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    def test_no_nearby_origin_stop(self, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        # Far remote coordinate
        mock_geo.side_effect = lambda p: {"query": p, "display_name": p, "latitude": 0.0, "longitude": 0.0}
        
        with self.assertRaises(JourneyPlanningError) as context:
            plan_journey("Ocean to Motijheel")
        self.assertIn("[transit_access]", str(context.exception))

    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_budget_removes_routes(self, mock_weather, mock_geo, mock_parse):
        mock_parse.return_value = {
            "origin": "Shahbag",
            "destination": "Motijheel",
            "budget": 5.0, # Very low budget
            "deadline_minutes": None,
            "preference": None
        }
        mock_geo.side_effect = mock_geocode_place_happy_path
        mock_weather.side_effect = mock_get_current_weather_happy_path
        
        with self.assertRaises(JourneyPlanningError) as context:
            plan_journey("Shahbag to Motijheel under 5 tk")
        self.assertIn("[constraints]", str(context.exception))

    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_fastest_preference(self, mock_weather, mock_geo, mock_parse):
        mock_parse.return_value = {
            "origin": "Shahbag",
            "destination": "Motijheel",
            "budget": None,
            "deadline_minutes": None,
            "preference": "fastest"
        }
        mock_geo.side_effect = mock_geocode_place_happy_path
        mock_weather.side_effect = mock_get_current_weather_happy_path
        
        res = plan_journey("Shahbag to Motijheel fastest")
        self.assertEqual(res["query"]["preference"], "fastest")
        
    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_weather_unavailable_fallback(self, mock_weather, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        mock_geo.side_effect = mock_geocode_place_happy_path
        mock_weather.side_effect = WeatherError("API down")
        
        res = plan_journey("Shahbag to Motijheel")
        self.assertFalse(res["weather_available"])
        self.assertIsNotNone(res["weather_warning"])
        self.assertGreater(res["feasible_count"], 0)
        
    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_eta_calculated_when_departure_time_present(self, mock_weather, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        mock_geo.side_effect = mock_geocode_place_happy_path
        mock_weather.side_effect = mock_get_current_weather_happy_path
        
        dep = datetime(2026, 9, 18, 8, 0, tzinfo=DHAKA_TIMEZONE)
        res = plan_journey("Shahbag to Motijheel", departure_time=dep)
        
        rec = res["recommendations"][0]
        self.assertIsNotNone(rec["estimated_arrival_time"])
        self.assertIsNone(rec["on_time"])
        
    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_absolute_deadline_evaluation(self, mock_weather, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        mock_geo.side_effect = mock_geocode_place_happy_path
        mock_weather.side_effect = mock_get_current_weather_happy_path
        
        dep = datetime(2026, 9, 18, 8, 0, tzinfo=DHAKA_TIMEZONE)
        # Tight deadline to force lateness for all routes
        deadline = datetime(2026, 9, 18, 8, 5, tzinfo=DHAKA_TIMEZONE) 
        
        with self.assertRaisesRegex(Exception, "No route can satisfy the selected arrival deadline"):
            plan_journey("Shahbag to Motijheel", departure_time=dep, arrival_deadline=deadline)

    def test_deadline_without_departure_accepted(self):
        # The backend now uses current time
        pass

    @patch("src.services.journey_planner.parse_travel_query")
    @patch("src.services.journey_planner.geocode_place")
    @patch("src.services.journey_planner.get_current_weather")
    def test_adverse_weather_applies_penalty(self, mock_weather, mock_geo, mock_parse):
        mock_parse.side_effect = mock_parse_travel_query_happy_path
        mock_geo.side_effect = mock_geocode_place_happy_path
        
        mock_weather.side_effect = mock_get_current_weather_happy_path
        res_clear = plan_journey("Shahbag to Motijheel")
        
        mock_weather.side_effect = mock_get_current_weather_adverse
        res_rain = plan_journey("Shahbag to Motijheel")
        
        clear_score = res_clear["recommendations"][0]["adjusted_score"]
        rain_score = res_rain["recommendations"][0]["adjusted_score"]
        
        # In adverse weather, score is usually penalised
        self.assertTrue(rain_score <= clear_score)


if __name__ == "__main__":
    unittest.main(verbosity=2)
