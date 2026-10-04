import unittest
from unittest.mock import patch, MagicMock
from flask import session
import os
import sys

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.flask_app import create_app
from src.api.auth import AuthenticationError, AuthConfigurationError

class TestPhase13AuthOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set required env vars for testing
        os.environ['SUPABASE_URL'] = 'https://mock.supabase.co'
        os.environ['SUPABASE_ANON_KEY'] = 'mock-anon-key'
        os.environ['FLASK_SECRET_KEY'] = 'test-secret'
        
        cls.app = create_app()
        cls.app.testing = True
        cls.client = cls.app.test_client()

    def setUp(self):
        # Create a fresh client for each test so sessions are isolated
        self.client = self.app.test_client()

    # --- Pages ---
    
    def test_1_get_root_unauthenticated(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Travel Smarter Across Dhaka", response.data)

    def test_2_get_planner_unauthenticated_redirects(self):
        response = self.client.get("/planner")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/'))

    # --- API Validation ---
    
    def test_11_missing_email_rejected(self):
        response = self.client.post("/api/auth/login", json={"password": "password123"})
        self.assertEqual(response.status_code, 400)
        
    def test_12_missing_password_rejected(self):
        response = self.client.post("/api/auth/login", json={"email": "test@example.com"})
        self.assertEqual(response.status_code, 400)
        
    def test_13_signup_short_password_rejected(self):
        response = self.client.post("/api/auth/signup", json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "short"
        })
        self.assertEqual(response.status_code, 400)

    # --- Auth Actions (Mocked) ---
    
    @patch('src.api.auth.requests.post')
    def test_3_4_valid_mocked_signup(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session": {"access_token": "mock-token"},
            "user": {
                "id": "mock-id",
                "email": "test@example.com",
                "user_metadata": {"full_name": "Test User"}
            }
        }
        mock_post.return_value = mock_response
        
        response = self.client.post("/api/auth/signup", json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['user']['full_name'], "Test User") # 4. stores full_name
        self.assertNotIn('password', str(response.data)) # 19. no password in response
        
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('authenticated'))

    @patch('src.api.auth.requests.post')
    def test_5_signup_requires_email_confirmation(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session": None, # Supabase returns null session if confirmation required
            "user": {
                "id": "mock-id",
                "email": "test@example.com",
                "user_metadata": {"full_name": "Test User"}
            }
        }
        mock_post.return_value = mock_response
        
        response = self.client.post("/api/auth/signup", json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertFalse(data['authenticated'])
        self.assertTrue(data['requires_email_confirmation'])
        
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get('authenticated'))

    @patch('src.api.auth.requests.post')
    def test_6_7_8_18_valid_mocked_login(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user": {
                "id": "mock-id",
                "email": "test@example.com",
                "user_metadata": {"full_name": "Test User"}
            }
        }
        mock_post.return_value = mock_response
        
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['authenticated'])
        
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('authenticated')) # 7. successful login creates session
            
        # 8. /planner accessible after login
        planner_resp = self.client.get("/planner")
        self.assertEqual(planner_resp.status_code, 200)
        self.assertIn(b"Test User", planner_resp.data)
        
        # 18. authenticated GET / redirects to /planner
        root_resp = self.client.get("/")
        self.assertEqual(root_resp.status_code, 302)
        self.assertTrue(root_resp.headers['Location'].endswith('/planner'))

    @patch('src.api.auth.requests.post')
    def test_9_10_20_wrong_credentials(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error_description": "Invalid login credentials"}
        mock_post.return_value = mock_response
        
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        
        self.assertEqual(response.status_code, 401) # 9. wrong credentials -> 401
        data = response.get_json()
        self.assertFalse(data['success'])
        
        # 20. provider raw error is not leaked (we return "Invalid email or password.")
        self.assertEqual(data['error']['message'], "Invalid email or password.")
        self.assertNotIn("Invalid login credentials", str(data))
        
        # 10. wrong credentials do not create session
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get('authenticated'))

    # --- Auth Status and Logout ---
    
    def test_15_auth_me_logged_out(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data['authenticated'])

    @patch('src.api.auth.requests.post')
    def test_14_16_17_auth_me_and_logout(self, mock_post):
        # Setup login
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user": {
                "id": "mock-id",
                "email": "test@example.com",
                "user_metadata": {"full_name": "Test User"}
            }
        }
        mock_post.return_value = mock_response
        self.client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
        
        # 14. /api/auth/me logged in
        me_resp = self.client.get("/api/auth/me")
        self.assertEqual(me_resp.status_code, 200)
        self.assertTrue(me_resp.get_json()['authenticated'])
        
        # Logout
        logout_resp = self.client.post("/api/auth/logout")
        self.assertEqual(logout_resp.status_code, 200)
        self.assertTrue(logout_resp.get_json()['success'])
        
        # 16. logout clears session
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get('authenticated'))
            
        # 17. /planner inaccessible after logout
        planner_resp = self.client.get("/planner")
        self.assertEqual(planner_resp.status_code, 302)

    # --- Forgot & Reset Password Validation ---

    def test_23_forgot_password_missing_email(self):
        response = self.client.post("/api/auth/forgot-password", json={})
        self.assertEqual(response.status_code, 400)

    def test_24_forgot_password_invalid_email(self):
        response = self.client.post("/api/auth/forgot-password", json={"email": "invalid"})
        self.assertEqual(response.status_code, 400)

    @patch('src.api.auth.requests.post')
    def test_25_forgot_password_valid(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        response = self.client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn("If an account exists", data['message'])
        
        # Verify provider endpoint and headers
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith("/auth/v1/recover?redirect_to=http://127.0.0.1:5000/"))
        self.assertEqual(kwargs['headers']['apikey'], 'mock-anon-key')
        self.assertNotIn('Authorization', kwargs['headers'])

    @patch('src.api.auth.requests.post')
    def test_26_forgot_password_not_found_safe(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404 # user not found
        mock_post.return_value = mock_response

        response = self.client.post("/api/auth/forgot-password", json={"email": "notfound@example.com"})
        self.assertEqual(response.status_code, 200) # Still 200 to not leak
        data = response.get_json()
        self.assertIn("If an account exists", data['message'])

    @patch('src.api.auth.requests.post')
    def test_27_forgot_password_rate_limit(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        response = self.client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
        self.assertEqual(response.status_code, 429)

    def test_28_reset_password_missing_password(self):
        response = self.client.post("/api/auth/reset-password", json={"recovery_access_token": "token"})
        self.assertEqual(response.status_code, 400)

    def test_29_reset_password_short_password(self):
        response = self.client.post("/api/auth/reset-password", json={"new_password": "short", "recovery_access_token": "token"})
        self.assertEqual(response.status_code, 400)

    def test_30_reset_password_missing_token(self):
        response = self.client.post("/api/auth/reset-password", json={"new_password": "password123"})
        self.assertEqual(response.status_code, 400)

    @patch('src.api.auth.requests.put')
    def test_31_reset_password_valid(self, mock_put):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response

        response = self.client.post("/api/auth/reset-password", json={
            "new_password": "newpassword123",
            "recovery_access_token": "valid-token"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

        mock_put.assert_called_once()
        args, kwargs = mock_put.call_args
        self.assertTrue(args[0].endswith("/auth/v1/user"))
        self.assertEqual(kwargs['headers']['apikey'], 'mock-anon-key')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer valid-token')

    @patch('src.api.auth.requests.put')
    def test_32_reset_password_invalid_token(self, mock_put):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_put.return_value = mock_response

        response = self.client.post("/api/auth/reset-password", json={
            "new_password": "newpassword123",
            "recovery_access_token": "invalid-token"
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Reset link is invalid", data['error']['message'])

    # --- Existing Functionality ---
    
    def test_21_health_works(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'ok')
        
    def test_22_api_plan_behavior_unchanged(self):
        # Missing query -> 400
        response = self.client.post("/api/plan", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error']['message'], "query is required and must be a non-empty string.")

if __name__ == '__main__':
    print("=" * 50)
    print("Running validate_phase13_auth_offline.py")
    print("=" * 50)
    result = unittest.main(verbosity=2, exit=False)
    if result.result.wasSuccessful():
        print("\nPASS\n")
        sys.exit(0)
    else:
        print("\nFAIL\n")
        sys.exit(1)
