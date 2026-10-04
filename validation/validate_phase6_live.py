import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
from src.api.geocoding import geocode_place, GeocodingError

def run_phase6_live_validation():
    print("Testing Nominatim Geocoding (Live Mode)...\n")
    
    places = [
        "Shahbag, Dhaka",
        "Uttara, Dhaka",
        "Motijheel, Dhaka"
    ]
    
    failures = 0
    
    for place in places:
        try:
            print(f"Geocoding: '{place}'")
            # Proactively sleep 1.5s to respect Nominatim usage policy (1 request/sec max)
            time.sleep(1.5)
            
            result = geocode_place(place)
            
            if result is None:
                print(f"  [FAIL] Result is None (no location found).")
                failures += 1
                continue
                
            lat = result.get("latitude")
            lon = result.get("longitude")
            
            display_name_safe = str(result.get('display_name')).encode('ascii', 'replace').decode('ascii')
            print(f"  Result: lat={lat}, lon={lon}, display_name='{display_name_safe}'")
            
            if not isinstance(lat, float) or not isinstance(lon, float):
                print("  [FAIL] lat/lon are not floats.")
                failures += 1
                continue
                
            if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                print("  [FAIL] coordinates out of bounds.")
                failures += 1
                continue
                
            print("  [PASS]")
            
        except GeocodingError as e:
            print(f"  [FAIL] Geocoding API Error: {e}")
            failures += 1
        except Exception as e:
            print(f"  [FAIL] Unexpected Error: {e}")
            failures += 1
            
    print(f"\nPhase 6 Live Validation complete. Failures: {failures}")
    assert failures == 0, f"Live validation failed {failures} tests."
    print("Phase 6 Live Validation PASSED")

if __name__ == "__main__":
    run_phase6_live_validation()
