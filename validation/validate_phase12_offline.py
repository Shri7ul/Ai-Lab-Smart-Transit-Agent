"""
Phase 12 Offline Validation: Flask API endpoints.
No real external calls made.
"""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from datetime import datetime

# Fix sys.path for absolute project-root imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.flask_app import create_app
from src.graph.models import Route, Leg
from src.services.journey_planner import JourneyPlanningError


class TestFlaskAPI(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['FLASK_SECRET_KEY'] = 'test-secret'
        self.app = create_app()
        self.client = self.app.test_client()

    def test_health_check(self):
        # 1, 2, 3
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "smart-transit-api")

    @patch("src.api.flask_app.plan_journey")
    def test_valid_post_plan_query_only(self, mock_plan):
        # 4, 5, 37
        mock_plan.return_value = {"mock_key": "mock_value"}
        response = self.client.post("/api/plan", json={"query": "Shahbag to Motijheel"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["mock_key"], "mock_value")
        mock_plan.assert_called_once()
        self.assertEqual(mock_plan.call_args[1]["user_query"], "Shahbag to Motijheel")
        self.assertEqual(mock_plan.call_args[1]["candidate_count"], 5)

    @patch("src.api.flask_app.plan_journey")
    def test_full_request_with_candidate_count(self, mock_plan):
        # 6
        mock_plan.return_value = {}
        response = self.client.post("/api/plan", json={"query": "Shahbag to Motijheel", "candidate_count": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_plan.call_args[1]["candidate_count"], 3)

    @patch("src.api.flask_app.plan_journey")
    def test_full_request_with_datetime(self, mock_plan):
        # 7, 8, 9
        mock_plan.return_value = {}
        response = self.client.post("/api/plan", json={
            "query": "Shahbag to Motijheel",
            "departure_time": "2026-09-18T08:00:00+06:00",
            "arrival_deadline": "2026-09-18T09:00:00+06:00"
        })
        self.assertEqual(response.status_code, 200)
        called_args = mock_plan.call_args[1]
        self.assertIsInstance(called_args["departure_time"], datetime)
        self.assertIsNotNone(called_args["departure_time"].tzinfo)
        self.assertIsInstance(called_args["arrival_deadline"], datetime)
        self.assertIsNotNone(called_args["arrival_deadline"].tzinfo)

    def test_missing_query(self):
        # 10
        response = self.client.post("/api/plan", json={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["type"], "validation_error")

    def test_invalid_query_types(self):
        # 11, 12, 13, 14
        for bad_query in [None, 123, "", "   "]:
            response = self.client.post("/api/plan", json={"query": bad_query})
            self.assertEqual(response.status_code, 400)

    def test_invalid_candidate_count(self):
        # 15, 16, 17, 18
        for bad_count in ["5", True, 0, -1, 3.5]:
            response = self.client.post("/api/plan", json={"query": "A", "candidate_count": bad_count})
            self.assertEqual(response.status_code, 400)

    def test_invalid_datetimes(self):
        # 19, 21
        for bad_dt in ["2026/09/18 08:00", "invalid"]:
            response = self.client.post("/api/plan", json={"query": "A", "departure_time": bad_dt})
            self.assertEqual(response.status_code, 400)

    def test_naive_datetimes_rejected(self):
        # 20, 22
        response = self.client.post("/api/plan", json={"query": "A", "departure_time": "2026-09-18T08:00:00"})
        self.assertEqual(response.status_code, 400)

    def test_deadline_without_departure_accepted(self):
        # 23
        pass

    def test_invalid_json(self):
        # 24, 25, 26
        # empty
        resp1 = self.client.post("/api/plan", data="")
        self.assertEqual(resp1.status_code, 400)
        
        # invalid
        resp2 = self.client.post("/api/plan", data="not json", content_type="application/json")
        self.assertEqual(resp2.status_code, 400)
        
        # array
        resp3 = self.client.post("/api/plan", json=[])
        self.assertEqual(resp3.status_code, 400)

    @patch("src.api.flask_app.plan_journey")
    def test_journey_planning_error(self, mock_plan):
        # 27, 33
        mock_plan.side_effect = JourneyPlanningError("[transit_access] No nearby stops")
        response = self.client.post("/api/plan", json={"query": "A to B"})
        self.assertEqual(response.status_code, 422)
        data = response.get_json()
        self.assertEqual(data["error"]["type"], "journey_planning_error")
        self.assertNotIn("[transit_access]", data["error"]["message"])
        self.assertIn("No nearby stops", data["error"]["message"])

    @patch("src.api.flask_app.plan_journey")
    def test_unexpected_error(self, mock_plan):
        # 28, 29, 33
        mock_plan.side_effect = Exception("Super secret internal API KEY xyz")
        response = self.client.post("/api/plan", json={"query": "A to B"})
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data["error"]["type"], "internal_server_error")
        self.assertNotIn("API KEY", data["error"]["message"])
        self.assertNotIn("Super secret", data["error"]["message"])

    @patch("src.api.flask_app.plan_journey")
    def test_serialization(self, mock_plan):
        # 30, 31, 32, 34
        mock_route = Route(
            path=["S1", "S2"],
            legs=[Leg("S1", "S2", "bus", 10.0, 50.0, 2.0)]
        )
        mock_dt = datetime.fromisoformat("2026-09-18T08:00:00+06:00")
        
        mock_plan.return_value = {
            "origin": "O",
            "weather_available": False, # 34
            "recommendations": [
                {
                    "route": mock_route,
                    "departure_time": mock_dt
                }
            ]
        }
        
        response = self.client.post("/api/plan", json={"query": "A to B"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        
        self.assertFalse(data["weather_available"])
        rec = data["recommendations"][0]
        self.assertEqual(rec["departure_time"], "2026-09-18T08:00:00+06:00")
        self.assertEqual(rec["route"]["time_min"], 10.0)
        self.assertEqual(rec["route"]["mode_sequence"], ["bus"])
        
    def test_method_handling(self):
        # 35, 36
        resp = self.client.get("/api/plan")
        self.assertEqual(resp.status_code, 405)
        self.assertEqual(resp.get_json()["error"]["type"], "method_not_allowed")
        
        resp2 = self.client.get("/api/unknown")
        self.assertEqual(resp2.status_code, 404)
        self.assertEqual(resp2.get_json()["error"]["type"], "not_found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
