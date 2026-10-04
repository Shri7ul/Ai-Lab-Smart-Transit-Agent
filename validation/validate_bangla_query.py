import sys
import os
import unittest
from unittest.mock import patch, MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.api.gemini_query import parse_travel_query, _parse_gemini_response, _clean_number

class TestBanglaQuery(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "mock_key"

    def test_clean_bangla_digits(self):
        self.assertEqual(_clean_number("১০০"), 100.0)
        self.assertEqual(_clean_number("৫০"), 50.0)
        self.assertIsNone(_clean_number("১০০ টাকা"))
        self.assertEqual(_clean_number("100"), 100.0)
        self.assertIsNone(_clean_number("100 taka"))
        self.assertEqual(_clean_number("100.5"), 100.5)

    @patch('src.api.gemini_query.genai.Client')
    def test_english_query(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.output_text = '{"origin": "Shahbag", "destination": "Motijheel", "budget": null, "deadline_minutes": null, "preference": null}'
        mock_client.interactions.create.return_value = mock_response

        res = parse_travel_query("Shahbag to Motijheel")
        self.assertEqual(res["origin"], "Shahbag")
        self.assertEqual(res["destination"], "Motijheel")

    @patch('src.api.gemini_query.genai.Client')
    def test_banglish_query(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.output_text = '{"origin": "Shahbag", "destination": "Motijheel", "budget": 100, "deadline_minutes": null, "preference": "less_walking"}'
        mock_client.interactions.create.return_value = mock_response

        res = parse_travel_query("Ami Shahbag theke Motijheel jete chai, amar budget 100 taka ar kom hatte chai.")
        self.assertEqual(res["origin"], "Shahbag")
        self.assertEqual(res["destination"], "Motijheel")
        self.assertEqual(res["budget"], 100)
        self.assertEqual(res["preference"], "less_walking")

    @patch('src.api.gemini_query.genai.Client')
    def test_bangla_query(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.output_text = '{"origin": "Shahbag", "destination": "Motijheel", "budget": "১০০", "deadline_minutes": null, "preference": "less walking"}'
        mock_client.interactions.create.return_value = mock_response

        res = parse_travel_query("আমি শাহবাগ থেকে মতিঝিল যেতে চাই। আমার বাজেট ১০০ টাকা এবং আমি যতটা সম্ভব কম হাঁটতে চাই।")
        self.assertEqual(res["origin"], "Shahbag")
        self.assertEqual(res["destination"], "Motijheel")
        self.assertEqual(res["budget"], 100.0)
        self.assertEqual(res["preference"], "less_walking")

    @patch('src.api.gemini_query.genai.Client')
    def test_mixed_query(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.output_text = '{"origin": "Shahbag", "destination": "Motijheel", "budget": "100", "deadline_minutes": null, "preference": "less_walking"}'
        mock_client.interactions.create.return_value = mock_response

        res = parse_travel_query("আমি Shahbag থেকে Motijheel যাব, budget 100 taka, walking কম চাই.")
        self.assertEqual(res["origin"], "Shahbag")
        self.assertEqual(res["destination"], "Motijheel")
        self.assertEqual(res["budget"], 100.0)
        self.assertEqual(res["preference"], "less_walking")

    @patch('src.api.gemini_query.genai.Client')
    def test_malformed_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.output_text = 'This is not json'
        mock_client.interactions.create.return_value = mock_response

        with self.assertRaisesRegex(ValueError, "Gemini returned invalid JSON"):
            parse_travel_query("Shahbag to Motijheel")

    @patch('src.api.gemini_query.genai.Client')
    def test_timeout(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.interactions.create.side_effect = Exception("Timeout")

        with self.assertRaisesRegex(RuntimeError, "Gemini query parsing request failed or timed out."):
            parse_travel_query("Shahbag to Motijheel")

if __name__ == '__main__':
    unittest.main()
