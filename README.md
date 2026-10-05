# Smart Transit Dhaka

An AI-assisted multimodal journey planning prototype for selected locations in Dhaka that combines natural-language understanding, graph-based routing, constraint filtering, multi-criteria ranking, weather information, interactive maps, authentication, and saved journeys.

## Overview
Smart Transit provides a unified interface for planning multimodal public transport trips across Dhaka. Users can simply type their query in English, Bangla, or Banglish (e.g. "I want to go from Shahbag to Motijheel under 50 taka"). The system understands the intent, calculates feasible routes over a custom dataset, and presents the best options on an interactive map.

## Core Features
- **Natural Language Understanding**: Understands journey intent (origin, destination, budget, time, preferences) in English and Bangla via Gemini.
- **Multimodal Graph Routing**: Calculates routes across metro (MRT Line 6) and bus transit networks.
- **Hard Constraints**: Strict elimination of routes that exceed user-specified budget or arrival deadlines.
- **Multi-Preference Ranking**: Normalized weighted scoring for finding the fastest, cheapest, or least-walking routes.
- **Interactive Leaflet Map**: Visualizes the origin, destination, and calculated paths.
- **Weather Context**: Integrates OpenWeather API to display current conditions and lightly penalize walking during adverse weather.
- **Authentication & Saved Routes**: Powered by Supabase to allow users to sign up and save favorite routes persistently across sessions.

## System Architecture
The application pipeline acts dynamically over a custom multimodal transit dataset:
1. **Frontend**: Receives user query.
2. **Flask API**: Orchestrates the journey planner.
3. **Gemini NLP**: Interprets user intent.
4. **Nominatim**: Geocodes textual places to coordinates.
5. **Local Routing**: A* shortest path / k-shortest path on local dataset.
6. **Hard Constraints**: Filters out candidates violating strict budget or deadline rules.
7. **Multi-Preference Ranking**: Scores feasible candidates based on normalized multi-criteria weighting.
8. **ETA**: Evaluates absolute clock deadlines.
9. **Weather**: Adds dynamic context.
10. **Supabase**: Handles persistence.

*(See `docs/architecture.md` for a full breakdown).*

## Dataset & Real-Time Limitations
**IMPORTANT**: Smart Transit is an AI-assisted routing prototype.
- **Static Dataset**: The route graph is static/custom, not real-time.
- **Dynamic Calculation**: The system calculates routes dynamically *over* that static graph.
- **No Live Tracking**: It does **not** provide live traffic, live bus location, live metro scheduling, or real-time GPS navigation.
- **Estimated Times**: ETAs are based on estimated historical route durations.

## Installation & Setup

1. Clone this repository or open the project folder.
2. Install Python requirements:
   ```bash
   py -m pip install -r requirements.txt
   ```
3. Copy the environment template and fill in your keys:
   ```bash
   cp .env.example .env
   ```
4. Start the Flask application:
   ```bash
   py -m flask --app app run --host=0.0.0.0 --port=5000
   ```

## Environment Variables
See `.env.example` for the required keys.

## Testing
To run the deterministic automated test suite:
```bash
python validation/run_all.py
```

## Security
- `SUPABASE_SECRET_KEY` and other sensitive API keys must remain safely on the backend environment.
- The Flask backend securely binds saved routes to the verified `user_id`.

## Future Work
- Integration with GTFS/GTFS-Realtime for actual transit agency schedules.
- Live vehicle GPS tracking.
- Traffic-aware routing and offline geocoding cache.