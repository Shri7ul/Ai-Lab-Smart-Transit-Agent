import sys
from pathlib import Path

# Path fix for local project imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.journey_planner import plan_journey, JourneyPlanningError
from src.api.geocoding import GeocodingError

def run_live_test():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    print("==================================================")
    print("PHASE 11 LIVE API SMOKE TEST")
    print("==================================================")
    
    query = "Shahbag to Motijheel"
    print(f"Testing Query: '{query}'")
    
    try:
        result = plan_journey(query, verbose=True)
        print("\n[SUCCESS] Pipeline completed successfully!")
        
        print("\nSummary:")
        print(f"Origin:      {result['origin']['geocoding']['display_name']}")
        print(f"Destination: {result['destination']['geocoding']['display_name']}")
        if result["weather_available"]:
            print(f"Weather:     {result['weather']['condition']} ({result['weather']['temperature_c']}°C)")
        else:
            print(f"Weather:     UNAVAILABLE ({result['weather_warning']})")
            
        print(f"Candidates:  {result['candidate_count']}")
        print(f"Feasible:    {result['feasible_count']}")
        print(f"Rejected:    {result['rejected_count']}")
        
    except JourneyPlanningError as e:
        print(f"\n[FAILURE] Journey Planning Error: {e}")
    except Exception as e:
        print(f"\n[UNEXPECTED FAILURE] {e}")

if __name__ == "__main__":
    run_live_test()
