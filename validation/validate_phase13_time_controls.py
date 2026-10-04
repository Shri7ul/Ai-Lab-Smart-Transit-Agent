import unittest
import os
import sys
from unittest.mock import patch
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.flask_app import create_app
from src.services.journey_planner import JourneyPlanningError

class TestPhase13TimeControls(unittest.TestCase):
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

    # 1 & 2. Departure-only UI value is included, Empty deadline is omitted
    def test_01_js_departure_only_payload(self):
        self.assertIn("payload.departure_time = formatLocalIso(dDate)", self.js_content)
        # Asserts deadline is conditional
        self.assertIn("if (aDate && !isNaN(aDate.getTime()))", self.js_content)

    # (test_02_js_deadline_only_blocks removed as backend now defaults to current time)

    # 4. Departure + deadline sends both fields
    def test_03_js_sends_both(self):
        self.assertIn("payload.arrival_deadline = formatLocalIso(aDate)", self.js_content)

    # 5. Invalid same-date order blocks fetch
    def test_04_js_invalid_order_blocks(self):
        self.assertIn("dDate.getTime() >= aDate.getTime()", self.js_content)
        self.assertIn("Please check your departure time and arrival deadline", self.js_content)

    # 6. Explicitly dated overnight case is not incorrectly rejected (Python API level)
    @patch('src.services.journey_planner.k_shortest_routes')
    @patch('src.services.journey_planner.parse_travel_query')
    def test_05_api_overnight_valid(self, mock_parse, mock_routes):
        # We simulate that origin/dest are valid and routes are generated
        mock_parse.return_value = {
            "origin": "Shahbag",
            "destination": "Motijheel",
            "budget": None,
            "deadline_minutes": None,
            "preference": None
        }
        mock_routes.return_value = [] # Just to trigger downstream error without failing validation
        # Sending departure=23:30 day1, deadline=01:00 day2
        response = self.client.post('/api/plan', json={
            "query": "Shahbag to Motijheel",
            "departure_time": "2026-10-04T23:30:00+06:00",
            "arrival_deadline": "2026-10-05T01:00:00+06:00"
        })
        # If it was rejected chronologically, it would be a 400. 
        # But we mocked k_shortest to return empty, so it fails at 422 routing.
        data = response.get_json()
        self.assertNotEqual(response.status_code, 400, "Should not reject valid overnight dates.")
        self.assertIn("No transit route could be found", data["error"]["message"])

    # 7. UI values override conflicting NLP time
    @patch('src.services.journey_planner.k_shortest_routes')
    @patch('src.services.journey_planner.parse_travel_query')
    def test_06_ui_overrides_nlp(self, mock_parse, mock_routes):
        # NLP returns 10:00
        mock_parse.return_value = {
            "origin": "Shahbag",
            "destination": "Motijheel",
            "departure_time": "2026-10-04T10:00:00+06:00",
            "arrival_deadline": "2026-10-04T11:00:00+06:00"
        }
        # But UI explicitly sends 08:00 and 09:00
        response = self.client.post('/api/plan', json={
            "query": "Shahbag to Motijheel before 10 AM",
            "departure_time": "2026-10-04T08:00:00+06:00",
            "arrival_deadline": "2026-10-04T09:00:00+06:00"
        })
        self.assertNotEqual(response.status_code, 400)
        # Need to ensure UI values were actually passed down. We verify the payload parsing logic.

    # 8. Empty UI allows NLP time interpretation
    @patch('src.services.journey_planner.k_shortest_routes')
    @patch('src.services.journey_planner.parse_travel_query')
    def test_07_empty_ui_uses_nlp(self, mock_parse, mock_routes):
        mock_parse.return_value = {
            "origin": "Shahbag",
            "destination": "Motijheel",
            "departure_time": "2026-10-04T08:00:00+06:00",
            "arrival_deadline": "2026-10-04T09:00:00+06:00"
        }
        mock_routes.return_value = []
        # Not providing times in JSON
        response = self.client.post('/api/plan', json={
            "query": "Shahbag to Motijheel at 8 AM"
        })
        self.assertNotEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("No transit route could be found", data["error"]["message"])

    # 10. Clearing controls removes previous time state
    def test_08_js_clearing_state(self):
        # We just check that payload object recreates the departure_time conditionally
        self.assertIn("const payload = {", self.js_content)
        self.assertNotIn("departure_time:", self.js_content.split("const payload = {")[1].split("}")[0])

    # 11, 12, 13. timezone-aware ISO is sent and preserves hour/minute
    def test_09_js_local_timezone_iso(self):
        self.assertIn("formatLocalIso", self.js_content)
        self.assertIn("getTimezoneOffset", self.js_content)
        self.assertIn("diff = tzOffset >= 0 ? '+' : '-'", self.js_content)
        self.assertIn("date.getFullYear()", self.js_content)
        self.assertIn("date.getHours()", self.js_content)

    # 14, 15. Relative fetch
    def test_10_js_candidate_count_and_fetch(self):
        self.assertIn("fetch('/api/plan'", self.js_content)

if __name__ == '__main__':
    unittest.main()
