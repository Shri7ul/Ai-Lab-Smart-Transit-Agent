import sys
from pathlib import Path

# Fix sys.path for absolute project-root imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import patch
from src.api.flask_app import create_app

def main():
    print("==================================================")
    print("PHASE 12 SEMI-LIVE VALIDATION (Mocked Gemini Only)")
    print("==================================================")
    
    app = create_app()
    client = app.test_client()
    
    mocked_query_result = {
        "origin": "Shahbag",
        "destination": "Motijheel",
        "budget": None,
        "deadline_minutes": None,
        "preference": None
    }
    
    # We mock Gemini in the exact module it is imported into by journey_planner
    with patch("src.services.journey_planner.parse_travel_query") as mock_parse:
        mock_parse.return_value = mocked_query_result
        
        response = client.post("/api/plan", json={
            "query": "Shahbag to Motijheel",
            "candidate_count": 3
        })
        
        try:
            print(f"HTTP Status: {response.status_code}")
            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}. Response: {response.get_json()}"
            
            data = response.get_json()
            print("Success Field:", data["success"])
            assert data["success"] is True, "Expected success == True"
            
            payload = data["data"]
            print("Data Exists:", payload is not None)
            assert payload is not None, "Data payload missing"
            
            print("Recommendations Found:", len(payload["recommendations"]))
            assert len(payload["recommendations"]) > 0, "No recommendations found"
            
            import networkx as nx
            from datetime import datetime
            
            def check_safe(obj):
                if isinstance(obj, nx.Graph): raise ValueError("Graph object leaked!")
                if isinstance(obj, datetime): raise ValueError("Datetime object leaked!")
                if isinstance(obj, dict):
                    for v in obj.values(): check_safe(v)
                elif isinstance(obj, list):
                    for v in obj: check_safe(v)
            
            check_safe(data)
            print("Response is JSON serializable and leak-free.")
            print(f"Gemini Mock Called: {mock_parse.called}")
            
        except Exception as e:
            print(f"FAILED: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()
