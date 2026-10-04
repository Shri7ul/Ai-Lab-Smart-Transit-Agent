import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from flask import session

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.api.flask_app import create_app
from src.api.saved_routes import SavedRoutesConfigurationError, SavedRoutesError

class TestSavedRoutes(unittest.TestCase):
    def setUp(self):
        os.environ["FLASK_SECRET_KEY"] = "test-secret"
        os.environ["SUPABASE_URL"] = "http://mock-supabase"
        os.environ["SUPABASE_SECRET_KEY"] = "mock-secret"
        
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_get_requires_auth(self):
        resp = self.client.get('/api/saved-routes')
        self.assertEqual(resp.status_code, 401)
        
    def test_post_requires_auth(self):
        resp = self.client.post('/api/saved-routes', json={})
        self.assertEqual(resp.status_code, 401)
        
    def test_delete_requires_auth(self):
        resp = self.client.delete('/api/saved-routes/123')
        self.assertEqual(resp.status_code, 401)

    @patch('src.api.flask_app.get_saved_routes')
    def test_get_uses_session_user_id(self, mock_get):
        mock_get.return_value = [{"id": "r1", "origin": "A", "destination": "B", "route_data": {}, "created_at": "now"}]
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True
            sess["user"] = {"id": "user1"}
            
        resp = self.client.get('/api/saved-routes')
        self.assertEqual(resp.status_code, 200)
        mock_get.assert_called_once_with("user1")
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)

    @patch('src.api.flask_app.save_route')
    def test_post_sanitizes_route_data(self, mock_save):
        mock_save.return_value = {"success": True, "already_saved": False, "data": {"id": "r1"}}
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True
            sess["user"] = {"id": "user1"}
            
        resp = self.client.post('/api/saved-routes', json={
            "origin": "A",
            "destination": "B",
            "route_data": {
                "cost_bdt": 10,
                "secret_key": "bad"
            }
        })
        self.assertEqual(resp.status_code, 200)
        mock_save.assert_called_once()
        args = mock_save.call_args[0]
        self.assertEqual(args[0], "user1")
        self.assertEqual(args[1], "A")
        self.assertEqual(args[2], "B")
        
        saved_route_data = args[3]
        self.assertIn("cost_bdt", saved_route_data)
        self.assertNotIn("secret_key", saved_route_data)

    @patch('src.api.flask_app.delete_saved_route')
    def test_delete_route(self, mock_delete):
        mock_delete.return_value = True
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True
            sess["user"] = {"id": "user1"}
            
        resp = self.client.delete('/api/saved-routes/123')
        self.assertEqual(resp.status_code, 200)
        mock_delete.assert_called_once_with("123", "user1")
        
    @patch('src.api.flask_app.delete_saved_route')
    def test_delete_route_not_found(self, mock_delete):
        mock_delete.return_value = False
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True
            sess["user"] = {"id": "user1"}
            
        resp = self.client.delete('/api/saved-routes/123')
        self.assertEqual(resp.status_code, 404)

if __name__ == '__main__':
    unittest.main()
