import sys
from pathlib import Path
import unittest

# Fix sys.path for absolute project-root imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.flask_app import create_app

class TestPhase13Step1(unittest.TestCase):
    @classmethod
    def setUp(self):
        import os
        os.environ['FLASK_SECRET_KEY'] = 'test-secret'
        self.app = create_app()
        self.client = self.app.test_client()

    def test_01_index_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_02_auth_html_returned(self):
        response = self.client.get("/")
        self.assertIn("text/html", response.headers.get("Content-Type", ""))

    def test_03_auth_contains_smart_transit(self):
        response = self.client.get("/")
        self.assertIn(b"SmartTransit", response.data)

    def test_04_auth_contains_login(self):
        response = self.client.get("/")
        self.assertIn(b"Log In", response.data)

    def test_05_auth_contains_signup(self):
        response = self.client.get("/")
        self.assertIn(b"Sign Up", response.data)

    def test_06_planner_returns_200(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
        response = self.client.get("/planner")
        self.assertEqual(response.status_code, 200)

    def test_07_planner_contains_smart_transit(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
        response = self.client.get("/planner")
        self.assertIn(b"Smart Transit", response.data)

    def test_08_planner_contains_find_best_routes(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
        response = self.client.get("/planner")
        self.assertIn(b"Find Best Routes", response.data)

    def test_09_planner_contains_plan_trip(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
        # We look for the Plan Trip nav button or header
        response = self.client.get("/planner")
        self.assertIn(b"PLAN TRIP", response.data.upper())

    def test_10_planner_contains_transit_lines(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
        response = self.client.get("/planner")
        self.assertIn(b"TRANSIT LINES", response.data.upper())

    def test_11_planner_contains_saved(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
        response = self.client.get("/planner")
        self.assertIn(b"SAVED", response.data.upper())

    def test_12_health_check_returns_200(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    def test_13_static_css_auth_works(self):
        response = self.client.get("/static/css/auth.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.headers.get("Content-Type", ""))

    def test_14_static_css_planner_works(self):
        response = self.client.get("/static/css/planner.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.headers.get("Content-Type", ""))

    def test_15_static_js_auth_works(self):
        response = self.client.get("/static/js/auth.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.headers.get("Content-Type", "").lower())

    def test_16_static_js_planner_works(self):
        response = self.client.get("/static/js/planner.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.headers.get("Content-Type", "").lower())

    def test_17_phase12_api_unaffected(self):
        # Quick validation error test to ensure POST /api/plan is still routing and validating
        response = self.client.post("/api/plan", json={})
        self.assertEqual(response.status_code, 400)
        
if __name__ == '__main__':
    unittest.main(verbosity=2)
