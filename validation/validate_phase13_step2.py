import unittest
import os
import re
import sys
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.flask_app import create_app

class TestPhase13Step2(unittest.TestCase):
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

    def test_01_planner_loads_authenticated(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['user'] = {'email': 'test@example.com'}
        response = self.client.get('/planner')
        self.assertEqual(response.status_code, 200)

    def test_02_api_plan_route_exists(self):
        # Sending an empty request to see if route exists (will fail validation but not 404)
        response = self.client.post('/api/plan', json={})
        self.assertNotEqual(response.status_code, 404)

    @patch('src.api.flask_app.plan_journey')
    def test_03_valid_mocked_plan_request_accepted(self, mock_plan):
        # mock plan_journey output
        mock_plan.return_value = {
            "origin": {"geocoding": {"display_name": "Shahbag"}},
            "destination": {"geocoding": {"display_name": "Motijheel"}},
            "recommendations": []
        }
        response = self.client.post('/api/plan', json={"query": "Shahbag to Motijheel"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        self.assertTrue(response.get_json()['success'])
        self.assertIn('recommendations', response.get_json()['data'])

    def test_04_query_is_required(self):
        response = self.client.post('/api/plan', json={"candidate_count": 3})
        self.assertEqual(response.status_code, 400)

    def test_05_empty_query_rejected(self):
        response = self.client.post('/api/plan', json={"query": "   "})
        self.assertEqual(response.status_code, 400)

    @patch('src.api.flask_app.plan_journey')
    def test_06_candidate_count_supported(self, mock_plan):
        mock_plan.return_value = {"recommendations": []}
        response = self.client.post('/api/plan', json={"query": "test", "candidate_count": 7})
        self.assertEqual(response.status_code, 200)
        
    @patch('src.api.flask_app.plan_journey')
    def test_07_departure_time_contract_unchanged(self, mock_plan):
        mock_plan.return_value = {"recommendations": []}
        response = self.client.post('/api/plan', json={"query": "test", "departure_time": "2025-05-18T08:15:00Z"})
        self.assertEqual(response.status_code, 200)

    @patch('src.api.flask_app.plan_journey')
    def test_08_arrival_deadline_contract_unchanged(self, mock_plan):
        mock_plan.return_value = {"recommendations": []}
        # Arrival deadline requires departure time
        response = self.client.post('/api/plan', json={"query": "test", "departure_time": "2025-05-18T08:15:00Z", "arrival_deadline": "2025-05-18T09:00:00Z"})
        self.assertEqual(response.status_code, 200)

    @patch('src.api.flask_app.plan_journey')
    def test_09_api_returns_json(self, mock_plan):
        mock_plan.return_value = {"recommendations": []}
        response = self.client.post('/api/plan', json={"query": "test"})
        self.assertTrue(response.is_json)

    def test_10_safe_error_structure_preserved(self):
        response = self.client.post('/api/plan', json={})
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('message', data['error'])

    def test_11_planner_js_references_relative_url(self):
        self.assertIn("fetch('/api/plan'", self.js_content)

    def test_12_planner_js_does_not_hardcode_localhost(self):
        self.assertNotIn("localhost", self.js_content)
        self.assertNotIn("127.0.0.1", self.js_content)

    def test_13_planner_js_does_not_hardcode_lan_ip(self):
        self.assertNotIn("192.168.", self.js_content)

    def test_14_planner_js_has_real_post_request(self):
        self.assertIn("method: 'POST'", self.js_content)

    def test_15_planner_js_sends_application_json(self):
        self.assertIn("'Content-Type': 'application/json'", self.js_content)
        self.assertIn("JSON.stringify(payload)", self.js_content)

    def test_16_loading_state_exists(self):
        self.assertIn("loadingBox.classList.remove('d-none')", self.js_content)
        self.assertIn("Finding Routes...", self.js_content)

    def test_17_duplicate_submit_prevention_exists(self):
        self.assertIn("btn.disabled = true", self.js_content)

    def test_18_network_error_handling_exists(self):
        self.assertIn("Unable to reach the journey planning service", self.js_content)

    def test_19_fake_setTimeout_simulation_removed(self):
        # We removed simulateAiPlanner completely
        self.assertNotIn("function simulateAiPlanner()", self.js_content)

    def test_20_no_external_api_key_exists(self):
        self.assertNotIn("AIza", self.js_content) # Common google/gemini key start
        self.assertNotIn("appid=", self.js_content)

    def test_21_no_gemini_direct_frontend_call(self):
        self.assertNotIn("generativelanguage.googleapis.com", self.js_content)

    def test_22_no_openweather_direct_frontend_call(self):
        self.assertNotIn("api.openweathermap.org", self.js_content)

    def test_23_no_nominatim_direct_frontend_call(self):
        self.assertNotIn("nominatim.openstreetmap.org", self.js_content)

    def test_24_frontend_uses_recommendations_key(self):
        self.assertIn("respData.recommendations", self.js_content)

    def test_25_frontend_handles_object_names(self):
        self.assertIn("locObj.geocoding.display_name", self.js_content)
        self.assertIn("locObj.geocoding.query", self.js_content)
        self.assertNotIn("[object Object]", self.js_content)

    def test_26_frontend_uses_real_recommendation_count(self):
        self.assertIn("recommendations.length", self.js_content)
        self.assertNotIn("0 routes found", self.js_content) # no hardcoded 0 routes found text

    def test_27_no_hardcoded_weather_or_traffic(self):
        self.assertNotIn("32° C", self.html_content)
        self.assertNotIn("AQI", self.html_content)
        self.assertNotIn("gridlock", self.html_content)

    def test_28_map_area_is_neutral(self):
        self.assertIn("Route visualization will appear here", self.html_content)
        self.assertIn("Weather information will appear", self.html_content)

    def test_29_existing_auth_endpoints_remain_unchanged(self):
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 200)

    def test_30_api_health_remains_unchanged(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'ok')

if __name__ == '__main__':
    unittest.main()
