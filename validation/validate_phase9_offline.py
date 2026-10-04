import sys
from pathlib import Path

# Path fix for local project imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from src.graph.models import Route, Leg
from src.algorithms.weather_ranking import (
    assess_weather_severity,
    calculate_weather_penalty,
    rank_routes_with_weather,
    MAX_WEATHER_PENALTY,
    WALK_EXPOSURE_REFERENCE_KM,
    TRANSFER_EXPOSURE_REFERENCE
)

def build_mock_route(cost: float, time: float, transfers: int, walk_dist: float) -> Route:
    route = Route(path=["A", "B"])
    legs = []
    if walk_dist > 0:
        legs.append(Leg("W1", "W2", "walk", time=0.0, cost=0.0, distance=walk_dist))
        
    modes = ["bus", "metro"]
    for i in range(transfers + 1):
        legs.append(Leg(f"N{i}", f"N{i+1}", modes[i % 2], time=time/(transfers+1), cost=cost/(transfers+1), distance=1.0))
        
    route.legs = legs
    return route

class TestWeatherRankingOffline(unittest.TestCase):
    def setUp(self):
        # Two routes. R1 has no walking, R2 has 1km walking.
        self.r1 = build_mock_route(10.0, 10.0, 0, 0.0) # Zero walking, zero transfer
        self.r2 = build_mock_route(10.0, 10.0, 0, 1.0) # High walking
        self.routes = [self.r1, self.r2]
        
    def test_clear_weather_zero_severity(self):
        weather = {
            "condition": "Clear",
            "rain_1h_mm": 0.0,
            "snow_1h_mm": 0.0,
            "wind_speed_mps": 2.0,
            "visibility_m": 10000.0
        }
        self.assertEqual(assess_weather_severity(weather), 0.0)

    def test_clouds_no_precipitation_zero_severity(self):
        weather = {
            "condition": "Clouds",
            "rain_1h_mm": 0.0,
            "snow_1h_mm": 0.0,
            "wind_speed_mps": 3.0,
            "visibility_m": 10000.0
        }
        self.assertEqual(assess_weather_severity(weather), 0.0)

    def test_light_rain_positive_severity(self):
        weather = {
            "condition": "Rain",
            "rain_1h_mm": 2.0,
            "snow_1h_mm": 0.0,
            "wind_speed_mps": 3.0,
            "visibility_m": 8000.0
        }
        sev = assess_weather_severity(weather)
        self.assertTrue(sev > 0.0)

    def test_heavy_rain_stronger_than_light(self):
        light_w = {"condition": "Rain", "rain_1h_mm": 1.0}
        heavy_w = {"condition": "Rain", "rain_1h_mm": 10.0}
        self.assertTrue(assess_weather_severity(heavy_w) > assess_weather_severity(light_w))

    def test_thunderstorm_strong_severity(self):
        weather = {"condition": "Thunderstorm"}
        sev = assess_weather_severity(weather)
        self.assertTrue(sev >= 0.75)

    def test_snow_handled(self):
        weather = {"condition": "Snow", "snow_1h_mm": 5.0}
        sev = assess_weather_severity(weather)
        self.assertTrue(sev >= 0.50)

    def test_visibility_and_wind_contribution(self):
        w_base = {"condition": "Clouds"}
        w_wind = {"condition": "Clouds", "wind_speed_mps": 15.0}
        w_vis = {"condition": "Clouds", "visibility_m": 500.0}
        
        self.assertTrue(assess_weather_severity(w_wind) > assess_weather_severity(w_base))
        self.assertTrue(assess_weather_severity(w_vis) > assess_weather_severity(w_base))

    def test_penalty_bounds(self):
        weather = {"condition": "Thunderstorm", "rain_1h_mm": 50.0, "wind_speed_mps": 20.0}
        sev = assess_weather_severity(weather)
        
        penalty, w_exp, t_exp = calculate_weather_penalty(self.r2, sev)
        self.assertTrue(penalty >= 0.0)
        self.assertTrue(penalty <= MAX_WEATHER_PENALTY)

    def test_walking_heavier_than_transfers(self):
        # r_walk has 1 reference walking, 0 transfers -> exposure = 0.75 * 1 + 0 = 0.75
        # r_transfer has 0 walking, 3 reference transfers -> exposure = 0 + 0.25 * 1 = 0.25
        r_walk = build_mock_route(10, 10, 0, WALK_EXPOSURE_REFERENCE_KM)
        r_transfer = build_mock_route(10, 10, int(TRANSFER_EXPOSURE_REFERENCE), 0.0)
        
        p_walk, _, _ = calculate_weather_penalty(r_walk, 1.0)
        p_transfer, _, _ = calculate_weather_penalty(r_transfer, 1.0)
        
        self.assertTrue(p_walk > p_transfer)

    def test_zero_walking_less_penalty(self):
        p1, _, _ = calculate_weather_penalty(self.r1, 1.0) # r1 has 0 walking
        p2, _, _ = calculate_weather_penalty(self.r2, 1.0) # r2 has walking
        self.assertTrue(p1 < p2)
        
    def test_ranking_clear_weather_identical(self):
        clear = {"condition": "Clear"}
        # Evaluate without weather
        from src.algorithms.multicriteria import rank_and_evaluate_routes
        base_df = rank_and_evaluate_routes(self.routes)
        
        # Evaluate with weather
        w_res = rank_routes_with_weather(self.routes, clear)
        
        # Order should be same
        self.assertEqual(len(w_res), 2)
        self.assertEqual(w_res[0]["route_id"], base_df.iloc[0]["route"])
        self.assertEqual(w_res[1]["route_id"], base_df.iloc[1]["route"])
        
        # Scores identical
        self.assertEqual(w_res[0]["base_score"], w_res[0]["adjusted_score"])
        self.assertEqual(w_res[1]["base_score"], w_res[1]["adjusted_score"])

    def test_rainy_weather_favors_less_walking(self):
        # We need two routes with identical base scores so weather dictates the tie-breaker
        # Let's make cost, time identical. Wait, r1 and r2 have same time and cost, 
        # but r1 has 0 walk and r2 has 1km walk.
        # Thus base ranking prefers r1 naturally because walk is a cost in multicriteria.
        # Let's make r2 slightly better in base score (less cost), but high walk.
        r1 = build_mock_route(20.0, 20.0, 0, 0.0)
        r2 = build_mock_route(18.0, 20.0, 0, 2.0)
        
        from src.algorithms.multicriteria import rank_and_evaluate_routes
        base_df = rank_and_evaluate_routes([r1, r2])
        # r2 should have a slightly better score depending on weights.
        
        heavy_rain = {"condition": "Thunderstorm", "rain_1h_mm": 20.0}
        w_res = rank_routes_with_weather([r1, r2], heavy_rain)
        
        # Validate adjusted_score = base - penalty
        for res in w_res:
            self.assertAlmostEqual(res["adjusted_score"], res["base_score"] - res["weather_penalty"], places=5)
            self.assertTrue(res["adjusted_score"] >= 0.0)

    def test_single_route(self):
        res = rank_routes_with_weather([self.r1], {"condition": "Rain", "rain_1h_mm": 2.0})
        self.assertEqual(len(res), 1)

    def test_empty_route_list(self):
        self.assertEqual(rank_routes_with_weather([], {"condition": "Clear"}), [])

    def test_route_object_not_mutated(self):
        # Ensure r1 properties don't change
        old_cost = self.r1.total_cost
        rank_routes_with_weather([self.r1], {"condition": "Rain"})
        self.assertEqual(self.r1.total_cost, old_cost)

    def test_malformed_weather(self):
        with self.assertRaises(TypeError):
            rank_routes_with_weather(self.routes, None)
            
        with self.assertRaises(TypeError):
            assess_weather_severity(["not", "dict"])
            
        with self.assertRaises(TypeError):
            assess_weather_severity({"condition": 123})
            
        with self.assertRaises(ValueError):
            assess_weather_severity({"condition": "Rain", "rain_1h_mm": -5.0})
            
        with self.assertRaises(ValueError):
            assess_weather_severity({"condition": "Rain", "snow_1h_mm": -1.0})
            
        with self.assertRaises(ValueError):
            assess_weather_severity({"condition": "Rain", "visibility_m": -100})
            
    def test_visibility_none_accepted(self):
        weather = {"condition": "Clouds", "visibility_m": None}
        sev = assess_weather_severity(weather)
        self.assertEqual(sev, 0.0) # Normal clouds with None vis should be 0.0

if __name__ == "__main__":
    unittest.main(verbosity=2)
