import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sys
from src.api.weather import get_current_weather

def test_live_weather(lat, lon, label):
    print(f"\n--- Testing Live Weather for {label} (lat={lat}, lon={lon}) ---")
    try:
        result = get_current_weather(lat, lon)
        
        # Verify result exists and is dictionary
        assert isinstance(result, dict), "Result must be a dictionary"
        
        # Verify coordinates
        assert isinstance(result["latitude"], float)
        assert isinstance(result["longitude"], float)
        
        # Verify types of output fields
        assert isinstance(result["condition"], str)
        assert isinstance(result["description"], str)
        
        assert isinstance(result["temperature_c"], (int, float))
        assert isinstance(result["feels_like_c"], (int, float))
        assert isinstance(result["humidity_percent"], (int, float))
        assert isinstance(result["wind_speed_mps"], (int, float))
        
        if result["visibility_m"] is not None:
            assert isinstance(result["visibility_m"], (int, float))
            
        assert isinstance(result["rain_1h_mm"], (int, float))
        assert isinstance(result["snow_1h_mm"], (int, float))
        
        print("Live data structure successfully validated:")
        print(f"Condition: {result['condition']} ({result['description']})")
        print(f"Temp: {result['temperature_c']} C")
        print(f"Humidity: {result['humidity_percent']}%")
        print(f"Wind: {result['wind_speed_mps']} m/s")
        print("[PASS] Valid live response.")
        
    except Exception as e:
        print(f"[FAIL] Error during live request: {e}")
        sys.exit(1)

def main():
    print("Running Phase 8 Live Smoke Tests (Limited API Calls)...")
    
    # United International University
    uiu_lat = 23.7989022
    uiu_lon = 90.4495995
    test_live_weather(uiu_lat, uiu_lon, "United International University")
    
    # University of Dhaka / Shahbag
    du_lat = 23.7312443
    du_lon = 90.3915283
    test_live_weather(du_lat, du_lon, "University of Dhaka / Shahbag")

    print("\nPhase 8 Live Validation PASSED.")

if __name__ == "__main__":
    main()
