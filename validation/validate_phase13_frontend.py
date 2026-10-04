import unittest
import os
import re
import sys
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.flask_app import create_app

class TestPhase13Frontend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        cls.client = app.test_client()

        # Load planner.js content
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        js_path = os.path.join(base_dir, 'static', 'js', 'planner.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            cls.js_content = f.read()
            
        html_path = os.path.join(base_dir, 'templates', 'planner.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            cls.html_content = f.read()

    def test_01_transit_lines_endpoint_exists(self):
        response = self.client.get('/api/transit-lines')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        self.assertTrue(response.get_json()['success'])
        
    def test_02_planner_js_fetches_transit_lines(self):
        self.assertIn("fetch('/api/transit-lines')", self.js_content)

    def test_03_planner_js_no_local_storage_for_saved_routes(self):
        self.assertNotIn("localStorage.getItem(SAVED_ROUTES_KEY)", self.js_content)
        self.assertNotIn("localStorage.setItem(SAVED_ROUTES_KEY", self.js_content)

    def test_04_planner_js_formats_eta(self):
        self.assertIn("estimated_arrival_time", self.js_content)
        self.assertIn("departure_time", self.js_content)
        self.assertIn("toLocaleTimeString", self.js_content)
        
    def test_05_no_static_transit_lines_in_html(self):
        self.assertNotIn("Active • High Speed", self.html_content)
        self.assertNotIn("Azimpur – Motijheel Express Bus", self.html_content)

    def test_06_no_static_saved_routes_in_html(self):
        self.assertNotIn("id=\"saved-item-route-uttara\"", self.html_content)
        self.assertNotIn("id=\"saved-item-route-3\"", self.html_content)

    @patch('src.api.flask_app.plan_journey')
    def test_07_api_plan_returns_eta_fields(self, mock_plan):
        mock_plan.return_value = {
            "origin": {"geocoding": {"display_name": "Shahbag"}},
            "destination": {"geocoding": {"display_name": "Motijheel"}},
            "recommendations": [
                {
                    "rank": 1,
                    "mode_sequence": "walk -> metro",
                    "time_min": 25,
                    "cost_bdt": 40,
                    "transfers": 1,
                    "walk_km": 0.5,
                    "departure_time": "2025-05-18T08:15:00Z",
                    "estimated_arrival_time": "2025-05-18T08:40:00Z"
                }
            ]
        }
        response = self.client.post('/api/plan', json={"query": "Shahbag to Motijheel"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()['data']
        self.assertEqual(data['recommendations'][0]['departure_time'], "2025-05-18T08:15:00Z")

    def test_08_no_static_demo_results_in_html(self):
        self.assertNotIn("32°C Cloudy", self.html_content)
        self.assertNotIn("Rain expected", self.html_content)
        self.assertNotIn("MRT Line 6 is recommended", self.html_content)
        self.assertNotIn("Azimpur-Motijheel Express", self.html_content)
        self.assertNotIn("Feeder Bus", self.html_content)
        self.assertNotIn("35 min", self.html_content)
        self.assertNotIn("৳40", self.html_content)
        
    def test_09_planner_js_dynamic_badges(self):
        self.assertIn("fastestIdx =", self.js_content)
        self.assertIn("lowestCostIdx =", self.js_content)
        self.assertIn("lessWalkingIdx =", self.js_content)

if __name__ == '__main__':
    unittest.main()
