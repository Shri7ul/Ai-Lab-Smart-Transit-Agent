import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.flask_app import create_app
from src.services.journey_planner import _get_weights_for_multiple_preferences, plan_journey
from src.api.gemini_query import parse_travel_query, _clean_number

class TestPhase15NLPRanking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_weights_less_walking_only(self):
        w = _get_weights_for_multiple_preferences(["less_walking"])
        self.assertAlmostEqual(w["walking"], 0.85)
        self.assertAlmostEqual(w["time"], 0.05)

    def test_02_weights_fewer_transfers_only(self):
        w = _get_weights_for_multiple_preferences(["fewer_transfers"])
        self.assertAlmostEqual(w["transfers"], 0.85)

    def test_03_weights_fastest_only(self):
        w = _get_weights_for_multiple_preferences(["fastest"])
        self.assertAlmostEqual(w["time"], 0.85)

    def test_04_weights_lowest_cost_only(self):
        w = _get_weights_for_multiple_preferences(["lowest_cost"])
        self.assertAlmostEqual(w["cost"], 0.85)

    def test_05_weights_two_prefs(self):
        w = _get_weights_for_multiple_preferences(["less_walking", "fewer_transfers"])
        self.assertAlmostEqual(w["walking"], 0.50)
        self.assertAlmostEqual(w["transfers"], 0.40)
        self.assertAlmostEqual(w["time"], 0.05)

    def test_06_weights_three_prefs(self):
        w = _get_weights_for_multiple_preferences(["fastest", "less_walking", "fewer_transfers"])
        self.assertAlmostEqual(w["time"], 0.45)
        self.assertAlmostEqual(w["walking"], 0.30)
        self.assertAlmostEqual(w["transfers"], 0.20)
        
    def test_07_bangla_budget_parses(self):
        self.assertEqual(_clean_number("১০০"), 100.0)
        self.assertEqual(_clean_number("১০০ টাকা"), 100.0)

    @patch('src.services.journey_planner.k_shortest_routes')
    @patch('src.services.journey_planner.geocode_place')
    @patch('src.services.journey_planner.find_nearest_stops')
    @patch('src.services.journey_planner.get_default_graph')
    @patch('src.services.journey_planner.get_current_weather')
    def test_08_budget_hard_constraint(self, mock_weather, mock_graph, mock_stops, mock_geo, mock_routes):
        mock_geo.return_value = {"latitude": 23.0, "longitude": 90.0}
        mock_stops.return_value = [{"stop_id": "stop1", "distance_km": 0, "walking_time_min": 0, "stop_name": "S", "lat": 0, "lon": 0}]
        mock_graph.return_value = (MagicMock(), MagicMock())
        mock_weather.return_value = None
        
        # Route 1: cost 120 (too high)
        # Route 2: cost 80 (feasible)
        r1 = MagicMock()
        r1.total_cost = 120
        r1.total_time = 20
        r1.num_transfers = 0
        r1.walking_distance = 0.5
        r1.to_dict.return_value = {"cost_bdt": 120, "time_min": 20, "transfers": 0, "walk_km": 0.5}
        
        r2 = MagicMock()
        r2.total_cost = 80
        r2.total_time = 30
        r2.num_transfers = 1
        r2.walking_distance = 0.2
        r2.to_dict.return_value = {"cost_bdt": 80, "time_min": 30, "transfers": 1, "walk_km": 0.2}

        mock_routes.return_value = [r1, r2]
        
        with patch('src.services.journey_planner.parse_travel_query') as mock_parse:
            mock_parse.return_value = {
                "origin": "O", "destination": "D", "budget": 100, 
                "deadline_minutes": None, "preferences": []
            }
            result = plan_journey("query")
            self.assertEqual(len(result["recommendations"]), 1)
            self.assertEqual(result["recommendations"][0]["cost_bdt"], 80)
            
    @patch('src.services.journey_planner.k_shortest_routes')
    @patch('src.services.journey_planner.geocode_place')
    @patch('src.services.journey_planner.find_nearest_stops')
    @patch('src.services.journey_planner.get_default_graph')
    @patch('src.services.journey_planner.get_current_weather')
    def test_09_deadline_without_departure_uses_dhaka_time(self, mock_weather, mock_graph, mock_stops, mock_geo, mock_routes):
        mock_geo.return_value = {"latitude": 23.0, "longitude": 90.0}
        mock_stops.return_value = [{"stop_id": "stop1", "distance_km": 0, "walking_time_min": 0, "stop_name": "S", "lat": 0, "lon": 0}]
        mock_graph.return_value = (MagicMock(), MagicMock())
        mock_weather.return_value = None
        
        # Current Dhaka time
        dhaka_tz = ZoneInfo("Asia/Dhaka")
        now = datetime.now(dhaka_tz)
        
        # Deadline 25 mins from now
        deadline = now + timedelta(minutes=25)
        
        r1 = MagicMock()
        r1.total_time = 18 # feasible
        r1.total_cost = 10
        r1.num_transfers = 0
        r1.walking_distance = 0
        r1.to_dict.return_value = {"cost_bdt": 10, "time_min": 18, "transfers": 0, "walk_km": 0}
        
        r2 = MagicMock()
        r2.total_time = 27 # infeasible
        r2.total_cost = 10
        r2.num_transfers = 0
        r2.walking_distance = 0
        r2.to_dict.return_value = {"cost_bdt": 10, "time_min": 27, "transfers": 0, "walk_km": 0}
        
        mock_routes.return_value = [r1, r2]

        with patch('src.services.journey_planner.parse_travel_query') as mock_parse:
            mock_parse.return_value = {
                "origin": "O", "destination": "D", "budget": None, 
                "deadline_minutes": None, "departure_time": None,
                "arrival_deadline": deadline.isoformat(),
                "preferences": []
            }
            result = plan_journey("query")
            self.assertEqual(len(result["recommendations"]), 1)
            self.assertEqual(len(result["late_routes"]), 1)
            self.assertEqual(result["recommendations"][0]["time_min"], 18)
            self.assertEqual(result["late_routes"][0]["time_min"], 27)
            self.assertTrue(all(r.get("on_time") is not False for r in result["recommendations"]))

    @patch('src.services.journey_planner.get_default_graph')
    @patch('src.services.journey_planner.find_nearest_stops')
    @patch('src.services.journey_planner.k_shortest_routes')
    @patch('src.services.journey_planner.geocode_place')
    def test_10_budget_hard_filter(self, mock_geo, mock_routes, mock_nearest, mock_graph):
        mock_geo.return_value = {"latitude": 0, "longitude": 0}
        mock_graph.return_value = (MagicMock(), MagicMock())
        mock_nearest.return_value = [{"stop_id": "s1", "walking_time_min": 0, "distance_km": 0.0}]
        
        r1 = MagicMock()
        r1.total_cost = 49
        r1.total_time = 10
        r1.num_transfers = 0
        r1.walking_distance = 0
        r1.mode_sequence = []
        r1.to_dict.return_value = {"cost_bdt": 49, "time_min": 10, "transfers": 0, "walk_km": 0}
        
        r2 = MagicMock()
        r2.total_cost = 50
        r2.total_time = 10
        r2.num_transfers = 0
        r2.walking_distance = 0
        r2.mode_sequence = []
        r2.to_dict.return_value = {"cost_bdt": 50, "time_min": 10, "transfers": 0, "walk_km": 0}
        
        r3 = MagicMock()
        r3.total_cost = 51
        r3.total_time = 10
        r3.num_transfers = 0
        r3.walking_distance = 0
        r3.mode_sequence = []
        r3.to_dict.return_value = {"cost_bdt": 51, "time_min": 10, "transfers": 0, "walk_km": 0}
        
        mock_routes.return_value = [r1, r2, r3]

        with patch('src.services.journey_planner.parse_travel_query') as mock_parse:
            mock_parse.return_value = {
                "origin": "O", "destination": "D", "budget": 50.0, 
                "deadline_minutes": None, "departure_time": None,
                "arrival_deadline": None,
                "preferences": []
            }
            result = plan_journey("query")
            self.assertEqual(len(result["recommendations"]), 2)
            # Both 49 and 50 are within budget, 51 is rejected.
            costs = [r["cost_bdt"] for r in result["recommendations"]]
            self.assertIn(49, costs)
            self.assertIn(50, costs)
            self.assertNotIn(51, costs)

    @patch('src.services.journey_planner.get_default_graph')
    @patch('src.services.journey_planner.find_nearest_stops')
    @patch('src.services.journey_planner.k_shortest_routes')
    @patch('src.services.journey_planner.geocode_place')
    def test_11_combined_hard_constraints(self, mock_geo, mock_routes, mock_nearest, mock_graph):
        mock_geo.return_value = {"latitude": 0, "longitude": 0}
        mock_graph.return_value = (MagicMock(), MagicMock())
        mock_nearest.return_value = [{"stop_id": "s1", "walking_time_min": 0, "distance_km": 0.0}]
        
        # Budget: 50, Deadline: 9:00 AM, Departure: 8:00 AM -> 60 min allowed.
        # Prefs: less_walking, fewer_transfers
        
        r_a = MagicMock() # feasible
        r_a.total_cost = 40
        r_a.total_time = 45 # arrives 8:45
        r_a.walking_distance = 0.8
        r_a.num_transfers = 0
        r_a.mode_sequence = []
        r_a.to_dict.return_value = {"cost_bdt": 40, "time_min": 45, "transfers": 0, "walk_km": 0.8}
        
        r_b = MagicMock() # rejected by budget
        r_b.total_cost = 60
        r_b.total_time = 30 # arrives 8:30
        r_b.walking_distance = 0.1
        r_b.num_transfers = 0
        r_b.mode_sequence = []
        r_b.to_dict.return_value = {"cost_bdt": 60, "time_min": 30, "transfers": 0, "walk_km": 0.1}
        
        r_c = MagicMock() # rejected by deadline
        r_c.total_cost = 30
        r_c.total_time = 65 # arrives 9:05
        r_c.walking_distance = 0.2
        r_c.num_transfers = 0
        r_c.mode_sequence = []
        r_c.to_dict.return_value = {"cost_bdt": 30, "time_min": 65, "transfers": 0, "walk_km": 0.2}
        
        r_d = MagicMock() # feasible
        r_d.total_cost = 45
        r_d.total_time = 50 # arrives 8:50
        r_d.walking_distance = 0.4
        r_d.num_transfers = 1
        r_d.mode_sequence = []
        r_d.to_dict.return_value = {"cost_bdt": 45, "time_min": 50, "transfers": 1, "walk_km": 0.4}
        
        mock_routes.return_value = [r_a, r_b, r_c, r_d]

        # Use an exact fixed datetime for predictability
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=6))
        departure = datetime(2023, 1, 1, 8, 0, tzinfo=tz)
        deadline = datetime(2023, 1, 1, 9, 0, tzinfo=tz)

        with patch('src.services.journey_planner.parse_travel_query') as mock_parse:
            mock_parse.return_value = {
                "origin": "O", "destination": "D", "budget": 50.0, 
                "deadline_minutes": None, "departure_time": departure.isoformat(),
                "arrival_deadline": deadline.isoformat(),
                "preferences": ["less_walking", "fewer_transfers"]
            }
            result = plan_journey("query")
            self.assertEqual(len(result["recommendations"]), 2)
            
            # Check exactly A and D are in recommendations
            costs = [r["cost_bdt"] for r in result["recommendations"]]
            self.assertIn(40, costs)
            self.assertIn(45, costs)
            
            # Check C is in late_routes
            self.assertEqual(len(result["late_routes"]), 1)
            self.assertEqual(result["late_routes"][0]["cost_bdt"], 30)
            
            # Check B is in rejected
            rejected_costs = [r["cost_bdt"] for r in result["rejected_routes"]]
            self.assertIn(60, rejected_costs)

if __name__ == '__main__':
    unittest.main()
