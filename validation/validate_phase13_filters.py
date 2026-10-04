import unittest
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.flask_app import create_app

class TestPhase13Filters(unittest.TestCase):
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

    def test_01_no_number_of_routes(self):
        self.assertNotIn('name="routeCount"', self.html_content)
        self.assertNotIn("Number of Routes", self.html_content)

    def test_02_no_quick_preferences_in_form(self):
        self.assertNotIn("QUICK PREFERENCES", self.html_content)
        
    def test_03_filter_results_hidden_by_default(self):
        self.assertIn('id="result-filter-bar"', self.html_content)
        self.assertIn('d-none', self.html_content.split('id="result-filter-bar"')[0].split('<div')[-1])

    def test_04_filter_results_appears_after_search(self):
        self.assertIn('filterBar.classList.remove(\'d-none\')', self.js_content)
        
    def test_05_fastest_filter_logic(self):
        self.assertIn('if (filterName === \'Fastest\' && r.time_min != null) val = r.time_min;', self.js_content)

    def test_06_lowest_cost_filter_logic(self):
        self.assertIn('if (filterName === \'Lowest Cost\' && r.cost_bdt != null) val = r.cost_bdt;', self.js_content)

    def test_07_less_walking_filter_logic(self):
        self.assertIn('if (filterName === \'Less Walking\' && r.walk_km != null) val = r.walk_km;', self.js_content)

    def test_08_fewer_transfers_filter_logic(self):
        self.assertIn('if (filterName === \'Fewer Transfers\' && r.transfers != null) val = r.transfers;', self.js_content)

    def test_09_ties_supported(self):
        self.assertIn('if (val === minVal && minVal !== Infinity)', self.js_content)

    def test_10_no_fetch_on_filter(self):
        # We manually inspect that fetch is not inside toggleResultFilter
        toggle_func = self.js_content.split('function toggleResultFilter')[1].split('function')[0]
        self.assertNotIn('fetch(', toggle_func)

    def test_12_only_one_filter_active(self):
        self.assertIn('btn.classList.remove(\'active\')', self.js_content)
        self.assertIn('btn.classList.add(\'active\')', self.js_content)

    def test_13_click_active_clears(self):
        self.assertIn('if (btn.classList.contains(\'active\'))', self.js_content)

    def test_17_new_search_clears_filters(self):
        self.assertIn('btn.classList.remove(\'active\')', self.js_content.split('function submitJourneyRequest')[1])

    def test_18_failed_search_hides_filter_bar(self):
        self.assertIn('filterBar.classList.add(\'d-none\')', self.js_content)

if __name__ == '__main__':
    unittest.main()
