import sys
from pathlib import Path

# Path fix for local project imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math

from src.graph.models import Route, Leg
from src.algorithms.eta import (
    estimate_arrival_time,
    check_arrival_deadline,
    evaluate_routes_for_deadline,
    DHAKA_TIMEZONE
)
from src.algorithms.constraints import filter_routes_by_constraints
from src.algorithms.weather_ranking import rank_routes_with_weather

def build_mock_route(time_min: float) -> Route:
    route = Route(path=["A", "B"])
    # to make route.total_time work, it sums leg.time
    route.legs = [Leg("A", "B", "bus", time=time_min, cost=10.0, distance=5.0)]
    return route

class TestETAOffline(unittest.TestCase):
    def setUp(self):
        self.r_40 = build_mock_route(40.0)
        self.r_0 = build_mock_route(0.0)
        self.r_large = build_mock_route(1500.0)
        
        self.dep = datetime(2026, 9, 18, 8, 0, tzinfo=DHAKA_TIMEZONE)
        
    def test_standard_eta(self):
        arr = estimate_arrival_time(self.r_40, self.dep)
        self.assertEqual(arr, datetime(2026, 9, 18, 8, 40, tzinfo=DHAKA_TIMEZONE))
        
    def test_zero_minute_route(self):
        arr = estimate_arrival_time(self.r_0, self.dep)
        self.assertEqual(arr, self.dep)
        
    def test_exact_deadline_boundary(self):
        deadline = datetime(2026, 9, 18, 8, 40, tzinfo=DHAKA_TIMEZONE)
        res = check_arrival_deadline(self.r_40, self.dep, deadline)
        self.assertTrue(res["on_time"])
        self.assertEqual(res["minutes_early"], 0.0)
        self.assertEqual(res["minutes_late"], 0.0)
        
    def test_early_arrival(self):
        deadline = datetime(2026, 9, 18, 9, 0, tzinfo=DHAKA_TIMEZONE)
        res = check_arrival_deadline(self.r_40, self.dep, deadline)
        self.assertTrue(res["on_time"])
        self.assertEqual(res["minutes_early"], 20.0)
        self.assertEqual(res["minutes_late"], 0.0)

    def test_late_arrival(self):
        deadline = datetime(2026, 9, 18, 8, 30, tzinfo=DHAKA_TIMEZONE)
        res = check_arrival_deadline(self.r_40, self.dep, deadline)
        self.assertFalse(res["on_time"])
        self.assertEqual(res["minutes_early"], 0.0)
        self.assertEqual(res["minutes_late"], 10.0)
        
    def test_overnight_midnight_crossing(self):
        dep_night = datetime(2026, 9, 18, 23, 50, tzinfo=DHAKA_TIMEZONE)
        arr = estimate_arrival_time(self.r_40, dep_night)
        self.assertEqual(arr, datetime(2026, 9, 19, 0, 30, tzinfo=DHAKA_TIMEZONE))
        
    def test_multi_day_duration(self):
        arr = estimate_arrival_time(self.r_large, self.dep) # 1500 mins = 25 hours
        self.assertEqual(arr, datetime(2026, 9, 19, 9, 0, tzinfo=DHAKA_TIMEZONE))
        
    def test_different_aware_timezone_comparison(self):
        # departure in dhaka (UTC+6)
        # deadline in tokyo (UTC+9). 08:40 Dhaka == 11:40 Tokyo. 
        # Deadline 12:00 Tokyo -> 09:00 Dhaka -> should be early by 20 minutes.
        tokyo_tz = ZoneInfo("Asia/Tokyo")
        deadline_tokyo = datetime(2026, 9, 18, 12, 0, tzinfo=tokyo_tz)
        res = check_arrival_deadline(self.r_40, self.dep, deadline_tokyo)
        self.assertTrue(res["on_time"])
        self.assertEqual(res["minutes_early"], 20.0)
        
    def test_naive_departure_rejected(self):
        naive_dep = datetime(2026, 9, 18, 8, 0)
        with self.assertRaises(ValueError):
            estimate_arrival_time(self.r_40, naive_dep)
            
    def test_naive_deadline_rejected(self):
        naive_deadline = datetime(2026, 9, 18, 9, 0)
        with self.assertRaises(ValueError):
            check_arrival_deadline(self.r_40, self.dep, naive_deadline)
            
    def test_none_departure_rejected(self):
        with self.assertRaises(ValueError):
            estimate_arrival_time(self.r_40, None)
            
    def test_string_departure_rejected(self):
        with self.assertRaises(TypeError):
            estimate_arrival_time(self.r_40, "2026-09-18 08:00")
            
    def test_malformed_route_duration_rejected(self):
        r_bad = build_mock_route(40)
        r_bad.legs[0].time = "40 mins"
        with self.assertRaises(TypeError):
            estimate_arrival_time(r_bad, self.dep)
            
    def test_negative_duration_rejected(self):
        r_neg = build_mock_route(-10.0)
        with self.assertRaises(ValueError):
            estimate_arrival_time(r_neg, self.dep)
            
    def test_nan_duration_rejected(self):
        r_nan = build_mock_route(float('nan'))
        with self.assertRaises(ValueError):
            estimate_arrival_time(r_nan, self.dep)
            
    def test_infinite_duration_rejected(self):
        r_inf = build_mock_route(float('inf'))
        with self.assertRaises(ValueError):
            estimate_arrival_time(r_inf, self.dep)
            
    def test_bool_duration_rejected(self):
        class MockRoute(Route):
            @property
            def total_time(self):
                return True
                
        r_bool = MockRoute(path=["A", "B"])
        with self.assertRaises(TypeError):
            estimate_arrival_time(r_bool, self.dep)
            
    def test_no_deadline_eta_works(self):
        res = check_arrival_deadline(self.r_40, self.dep)
        self.assertEqual(res["estimated_arrival_time"], datetime(2026, 9, 18, 8, 40, tzinfo=DHAKA_TIMEZONE))
        self.assertIsNone(res["on_time"])
        self.assertIsNone(res["minutes_early"])
        self.assertIsNone(res["minutes_late"])
        
    def test_multiple_route_deadline_evaluation(self):
        routes = [self.r_40, self.r_0, self.r_large]
        deadline = datetime(2026, 9, 18, 9, 0, tzinfo=DHAKA_TIMEZONE)
        res_list = evaluate_routes_for_deadline(routes, self.dep, deadline)
        self.assertEqual(len(res_list), 3)
        self.assertTrue(res_list[0]["on_time"]) # 40m -> on time
        self.assertTrue(res_list[1]["on_time"]) # 0m -> on time
        self.assertFalse(res_list[2]["on_time"]) # 1500m -> late
        
    def test_phase4_duration_vs_phase10_deadline(self):
        # max_time=40, route=39
        r = build_mock_route(39.0)
        
        # Phase 4 constraint (journey duration)
        p4 = filter_routes_by_constraints([r], max_time=40.0)
        self.assertEqual(len(p4["feasible"]), 1)
        
        # Phase 10 absolute deadline
        dep = datetime(2026, 9, 18, 8, 30, tzinfo=DHAKA_TIMEZONE)
        deadline = datetime(2026, 9, 18, 9, 0, tzinfo=DHAKA_TIMEZONE)
        p10 = check_arrival_deadline(r, dep, deadline)
        
        # Route arrives at 09:09 > 09:00 -> late
        self.assertFalse(p10["on_time"])

    def test_weather_ranking_does_not_mutate_duration(self):
        # Simulate Phase 9 interaction
        r = build_mock_route(40.0)
        weather = {"condition": "Thunderstorm"}
        rank_routes_with_weather([r], weather)
        
        # Route duration must remain unchanged
        self.assertEqual(r.total_time, 40.0)
        arr = estimate_arrival_time(r, self.dep)
        self.assertEqual(arr, datetime(2026, 9, 18, 8, 40, tzinfo=DHAKA_TIMEZONE))

    def test_original_object_not_mutated(self):
        r = build_mock_route(40.0)
        check_arrival_deadline(r, self.dep)
        self.assertEqual(r.total_time, 40.0)
        
    def test_input_datetimes_not_mutated(self):
        dep_copy = datetime(2026, 9, 18, 8, 0, tzinfo=DHAKA_TIMEZONE)
        deadline = datetime(2026, 9, 18, 9, 0, tzinfo=DHAKA_TIMEZONE)
        deadline_copy = datetime(2026, 9, 18, 9, 0, tzinfo=DHAKA_TIMEZONE)
        
        check_arrival_deadline(self.r_40, self.dep, deadline)
        self.assertEqual(self.dep, dep_copy)
        self.assertEqual(deadline, deadline_copy)
        
    def test_deterministic_repeated_calculation(self):
        r = build_mock_route(40.0)
        arr1 = estimate_arrival_time(r, self.dep)
        arr2 = estimate_arrival_time(r, self.dep)
        self.assertEqual(arr1, arr2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
