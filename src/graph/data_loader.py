"""Data loader and basic validation for transit data."""
import json
import pandas as pd
from pathlib import Path

# Resolve data path relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

def load_json(filepath: Path) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_stops(stops: list):
    seen_ids = set()
    for stop in stops:
        if "id" not in stop or "name" not in stop or "latitude" not in stop or "longitude" not in stop or "mode" not in stop:
            raise ValueError(f"Missing required fields in stop: {stop}")
        if stop["id"] in seen_ids:
            raise ValueError(f"Duplicate stop ID: {stop['id']}")
        seen_ids.add(stop["id"])
        
        if not (-90 <= float(stop["latitude"]) <= 90) or not (-180 <= float(stop["longitude"]) <= 180):
            raise ValueError(f"Invalid coordinates for stop: {stop['id']}")

def validate_edges(edges: list, valid_stop_ids: set):
    for edge in edges:
        if "source" not in edge or "target" not in edge or "mode" not in edge:
            raise ValueError(f"Missing required routing fields in edge: {edge}")
        if "time" not in edge or "cost" not in edge or "distance" not in edge:
             raise ValueError(f"Missing required metric fields in edge: {edge}")
             
        if edge["source"] not in valid_stop_ids:
            raise ValueError(f"Edge references unknown source stop: {edge['source']}")
        if edge["target"] not in valid_stop_ids:
            raise ValueError(f"Edge references unknown target stop: {edge['target']}")
            
        if float(edge["time"]) < 0 or float(edge["cost"]) < 0 or float(edge["distance"]) < 0:
            raise ValueError(f"Negative weight found in edge: {edge}")

def load_transit_data():
    """Load and validate all JSON datasets, returning DataFrames for stops and transit edges."""
    stops_file = DATA_DIR / "stops.json"
    bus_file = DATA_DIR / "bus_edges.json"
    metro_file = DATA_DIR / "metro_edges.json"
    
    stops_data = load_json(stops_file)
    bus_data = load_json(bus_file)
    metro_data = load_json(metro_file)
    
    validate_stops(stops_data)
    
    valid_ids = {stop["id"] for stop in stops_data}
    validate_edges(bus_data, valid_ids)
    validate_edges(metro_data, valid_ids)
    
    # Convert stops to DataFrame matching Phase 1 format
    stops_df = pd.DataFrame(stops_data)
    stops_df = stops_df.rename(columns={"id": "stop_id", "name": "stop_name", "latitude": "lat", "longitude": "lon"})
    
    # Convert edges to DataFrame matching Phase 1 format
    all_edges_data = bus_data + metro_data
    transit_edges_df = pd.DataFrame(all_edges_data)
    transit_edges_df = transit_edges_df.rename(columns={"source": "from", "target": "to", "time": "travel_time"})
    
    return stops_df, transit_edges_df
