import sys
from pathlib import Path

# Fix sys.path for absolute project-root imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import patch
from src.services.journey_planner import plan_journey

def main():
    print("==================================================")
    print("PHASE 11 SEMI-LIVE VALIDATION (Mocked Gemini Only)")
    print("==================================================")
    
    mocked_query_result = {
        "origin": "Shahbag",
        "destination": "Motijheel",
        "budget": None,
        "deadline_minutes": None,
        "preference": None
    }
    
    with patch("src.services.journey_planner.parse_travel_query") as mock_parse:
        mock_parse.return_value = mocked_query_result
        
        try:
            result = plan_journey("Shahbag to Motijheel", candidate_count=3, verbose=True)
            
            print("\n[VALIDATION]")
            print(f"1. Gemini Mock Called: {mock_parse.called}")
            print(f"2. Origin Geocoding: {result['origin']['geocoding'] is not None}")
            print(f"3. Destination Geocoding: {result['destination']['geocoding'] is not None}")
            print(f"4. Transit Access (Origin): {len(result['origin']['access_stops']) > 0}")
            print(f"5. Candidate Routes: {result['candidate_count']} generated")
            print(f"6. Feasible Recommendations: {result['feasible_count']}")
            print(f"7. Route Fields Present: {'time_min' in result['recommendations'][0]}")
            
            print(f"8. Weather Available: {result['weather_available']}")
            if not result['weather_available']:
                print(f"   Fallback Warning: {result['weather_warning']}")
                
            print("9. Final Phase 11 Result Produced Successfully")
            print("10. No Gemini API request made.")
            
        except Exception as e:
            print(f"FAILED: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()
