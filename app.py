"""
Main entry point for running the Smart Transit local Flask server.
"""
import os
from src.api.flask_app import create_app

app = create_app()

if __name__ == "__main__":
    # Use config-driven debug, default to False if not set
    debug_mode = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true")
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)
