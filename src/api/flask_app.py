"""
Flask API application factory and endpoints (Phase 12 & 13).
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any

from flask import Flask, request, jsonify, Response, render_template, session, redirect, url_for

from src.api.serialization import serialize_result
from src.services.journey_planner import plan_journey, JourneyPlanningError
from src.api.auth import signup_user, login_user, request_password_reset, reset_password_with_token, AuthenticationError, AuthConfigurationError
from src.api.saved_routes import get_saved_routes, save_route, delete_saved_route, sanitize_route_data, SavedRoutesError, SavedRoutesConfigurationError
from src.graph.data_loader import load_transit_data


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware.")
        return dt
    except ValueError as exc:
        raise ValueError(f"Invalid datetime format: {exc}")


def _error_response(message: str, error_type: str, status_code: int) -> tuple[Response, int]:
    return jsonify({
        "success": False,
        "error": {
            "type": error_type,
            "message": message
        }
    }), status_code


def create_app() -> Flask:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    app = Flask(__name__, 
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))
    
    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        raise AuthConfigurationError("FLASK_SECRET_KEY environment variable is missing.")
    app.secret_key = secret

    # Configure logging to prevent messy tracebacks in API responses
    # but still keep them in stdout/stderr for developers.
    logging.basicConfig(level=logging.INFO)

    @app.route("/", methods=["GET"])
    def index():
        if session.get("authenticated"):
            return redirect(url_for("planner_page"))
        return render_template("auth.html")

    @app.route("/planner", methods=["GET"])
    def planner_page():
        if not session.get("authenticated"):
            return redirect(url_for("index"))
        return render_template("planner.html", user=session.get("user"))

    @app.route("/api/auth/signup", methods=["POST"])
    def auth_signup():
        if not request.is_json:
            return _error_response("Request body must be JSON.", "validation_error", 400)
        
        data = request.get_json(silent=True) or {}
        full_name = data.get("full_name")
        email = data.get("email")
        password = data.get("password")
        
        if not full_name or not isinstance(full_name, str) or not full_name.strip():
            return _error_response("full_name is required and must be a non-empty string.", "validation_error", 400)
        if not email or not isinstance(email, str) or "@" not in email:
            return _error_response("email is required and must be a valid email.", "validation_error", 400)
        if not password or not isinstance(password, str) or len(password) < 8:
            return _error_response("password is required and must be at least 8 characters.", "validation_error", 400)
            
        try:
            result = signup_user(email, password, full_name.strip())
            if result.get("authenticated"):
                session["authenticated"] = True
                session["user"] = result["user"]
                return jsonify({
                    "success": True,
                    "authenticated": True,
                    "user": result["user"]
                }), 200
            else:
                return jsonify({
                    "success": True,
                    "authenticated": False,
                    "requires_email_confirmation": result.get("requires_email_confirmation"),
                    "message": "Check your email to confirm your account."
                }), 200
        except AuthenticationError as exc:
            return _error_response(str(exc), "authentication_error", 400)
        except AuthConfigurationError as exc:
            return _error_response("Auth misconfigured on server.", "server_error", 500)

    @app.route("/api/auth/login", methods=["POST"])
    def auth_login() -> tuple[Response, int]:
        if not request.is_json:
            return _error_response("Request body must be JSON.", "validation_error", 400)
            
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return _error_response("email and password are required.", "validation_error", 400)
            
        try:
            result = login_user(email, password)
            if result.get("authenticated"):
                session["authenticated"] = True
                session["user"] = result["user"]
                return jsonify({
                    "success": True,
                    "authenticated": True,
                    "user": result["user"]
                }), 200
            else:
                return _error_response("Invalid email or password.", "authentication_error", 401)
        except AuthenticationError as exc:
            return _error_response("Invalid email or password.", "authentication_error", 401)
        except AuthConfigurationError as exc:
            return _error_response("Auth misconfigured on server.", "server_error", 500)

    @app.route("/api/auth/forgot-password", methods=["POST"])
    def auth_forgot_password() -> tuple[Response, int]:
        if not request.is_json:
            return _error_response("Request body must be JSON.", "validation_error", 400)
            
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        
        if not email or not isinstance(email, str) or "@" not in email:
            return _error_response("email is required and must be a valid email.", "validation_error", 400)
            
        try:
            # We redirect to the same page, possibly with a marker.
            # Local dev typical redirect URL:
            redirect_to = "http://127.0.0.1:5000/"
            request_password_reset(email, redirect_to)
            # Must not reveal whether account exists or not
            return jsonify({
                "success": True,
                "message": "If an account exists for this email, a password reset link has been sent."
            }), 200
        except AuthenticationError as exc:
            # e.g., Rate limits or generic safe message
            msg = str(exc)
            if "Too many requests" in msg:
                return _error_response(msg, "rate_limit_error", 429)
            return jsonify({
                "success": True,
                "message": "If an account exists for this email, a password reset link has been sent."
            }), 200
        except AuthConfigurationError as exc:
            return _error_response("Auth misconfigured on server.", "server_error", 500)

    @app.route("/api/auth/reset-password", methods=["POST"])
    def auth_reset_password() -> tuple[Response, int]:
        if not request.is_json:
            return _error_response("Request body must be JSON.", "validation_error", 400)
            
        data = request.get_json(silent=True) or {}
        new_password = data.get("new_password")
        recovery_access_token = data.get("recovery_access_token")
        
        if not new_password or not isinstance(new_password, str) or len(new_password) < 8:
            return _error_response("new_password is required and must be at least 8 characters.", "validation_error", 400)
            
        if not recovery_access_token or not isinstance(recovery_access_token, str):
            return _error_response("recovery_access_token is required.", "validation_error", 400)
            
        try:
            reset_password_with_token(new_password, recovery_access_token)
            return jsonify({
                "success": True,
                "message": "Password updated successfully."
            }), 200
        except AuthenticationError as exc:
            return _error_response(str(exc), "authentication_error", 400)
        except AuthConfigurationError as exc:
            return _error_response("Auth misconfigured on server.", "server_error", 500)

    @app.route("/api/auth/me", methods=["GET"])
    def auth_me():
        if session.get("authenticated"):
            return jsonify({
                "authenticated": True,
                "user": session.get("user")
            }), 200
        else:
            return jsonify({"authenticated": False}), 401

    @app.route("/api/auth/logout", methods=["POST"])
    def auth_logout():
        session.clear()
        return jsonify({"success": True}), 200

    @app.route("/api/saved-routes", methods=["GET"])
    def api_get_saved_routes():
        if not session.get("authenticated") or not session.get("user"):
            return _error_response("Unauthorized", "authentication_error", 401)
            
        user_id = session["user"].get("id")
        if not user_id:
            return _error_response("Unauthorized", "authentication_error", 401)
            
        try:
            routes = get_saved_routes(user_id)
            return jsonify({
                "success": True,
                "data": routes
            }), 200
        except SavedRoutesConfigurationError:
            return _error_response("Saved Routes misconfigured on server.", "server_error", 500)
        except SavedRoutesError as exc:
            app.logger.error(f"Saved Routes GET Error: {exc}")
            return _error_response("Failed to fetch saved routes.", "server_error", 500)

    @app.route("/api/saved-routes", methods=["POST"])
    def api_post_saved_routes():
        if not session.get("authenticated") or not session.get("user"):
            return _error_response("Unauthorized", "authentication_error", 401)
            
        user_id = session["user"].get("id")
        if not user_id:
            return _error_response("Unauthorized", "authentication_error", 401)
            
        if not request.is_json:
            return _error_response("Request body must be JSON.", "validation_error", 400)
            
        data = request.get_json(silent=True) or {}
        origin = data.get("origin")
        destination = data.get("destination")
        raw_route_data = data.get("route_data")
        
        if not origin or not isinstance(origin, str):
            return _error_response("origin is required and must be a string.", "validation_error", 400)
        if not destination or not isinstance(destination, str):
            return _error_response("destination is required and must be a string.", "validation_error", 400)
        if not raw_route_data or not isinstance(raw_route_data, dict):
            return _error_response("route_data is required and must be an object.", "validation_error", 400)
            
        clean_route_data = sanitize_route_data(raw_route_data)
        
        try:
            result = save_route(user_id, origin, destination, clean_route_data)
            return jsonify(result), 200
        except SavedRoutesConfigurationError:
            return _error_response("Saved Routes misconfigured on server.", "server_error", 500)
        except SavedRoutesError as exc:
            app.logger.error(f"Saved Routes POST Error: {exc}")
            return _error_response("Failed to save route.", "server_error", 500)

    @app.route("/api/saved-routes/<route_id>", methods=["DELETE"])
    def api_delete_saved_route(route_id):
        if not session.get("authenticated") or not session.get("user"):
            return _error_response("Unauthorized", "authentication_error", 401)
            
        user_id = session["user"].get("id")
        if not user_id:
            return _error_response("Unauthorized", "authentication_error", 401)
            
        if not route_id or not isinstance(route_id, str):
            return _error_response("Invalid route ID.", "validation_error", 400)
            
        try:
            success = delete_saved_route(route_id, user_id)
            if success:
                return jsonify({"success": True}), 200
            else:
                return _error_response("Route not found or unauthorized.", "not_found", 404)
        except SavedRoutesConfigurationError:
            return _error_response("Saved Routes misconfigured on server.", "server_error", 500)
        except SavedRoutesError as exc:
            app.logger.error(f"Saved Routes DELETE Error: {exc}")
            return _error_response("Failed to delete route.", "server_error", 500)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "ok",
            "service": "smart-transit-api"
        }), 200

    @app.route("/api/plan", methods=["POST"])
    def plan():
        # Handle non-JSON or empty body
        if not request.is_json:
            return _error_response("Request body must be JSON.", "validation_error", 400)
            
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return _error_response("JSON body must be an object.", "validation_error", 400)
            
        user_query = data.get("query")
        candidate_count = data.get("candidate_count", 5)
        departure_time_str = data.get("departure_time")
        arrival_deadline_str = data.get("arrival_deadline")

        # Basic validations
        if not user_query or not isinstance(user_query, str) or not user_query.strip():
            return _error_response("query is required and must be a non-empty string.", "validation_error", 400)
            
        if not isinstance(candidate_count, int) or isinstance(candidate_count, bool) or candidate_count < 1:
            return _error_response("candidate_count must be an integer >= 1.", "validation_error", 400)

        # Datetime parsing
        try:
            departure_time = _parse_datetime(departure_time_str)
            arrival_deadline = _parse_datetime(arrival_deadline_str)
        except ValueError as exc:
            return _error_response(str(exc), "validation_error", 400)
            
        if arrival_deadline is not None and departure_time is None:
            return _error_response("arrival_deadline requires departure_time.", "validation_error", 400)

        # Execute journey planning
        try:
            raw_result = plan_journey(
                user_query=user_query,
                departure_time=departure_time,
                arrival_deadline=arrival_deadline,
                candidate_count=candidate_count,
                verbose=False
            )
            
            return jsonify({
                "success": True,
                "data": serialize_result(raw_result)
            }), 200
            
        except JourneyPlanningError as exc:
            msg = str(exc)
            
            # 429 / Rate Limit
            if msg.startswith("[query_understanding] Gemini rate limit exceeded"):
                return _error_response("AI journey planning service is temporarily rate-limited. Please try again later.", "rate_limit_error", 429)
                
            # Generic NLP error
            if msg.startswith("[query_understanding]"):
                app.logger.error(f"Internal Query Understanding Error: {msg}")
                return _error_response("AI journey planning service is temporarily unavailable. Please try again.", "journey_planning_error", 422)
                
            # Geocoding error
            if msg.startswith("[geocoding]"):
                return _error_response("We couldn't locate one of the places in your journey. Try a more specific location.", "journey_planning_error", 422)
                
            # Transit access error
            if msg.startswith("[transit_access] No transit stop found near"):
                return _error_response("We couldn't find a nearby transit connection for your starting location. Try a more specific nearby landmark or another supported area.", "journey_planning_error", 422)

            # Clean other prefixes from internal modules
            import re
            clean_msg = re.sub(r"^\[.*?\]\s*", "", msg)
            return _error_response(clean_msg, "journey_planning_error", 422)

    @app.route("/api/transit-lines", methods=["GET"])
    def get_transit_lines():
        try:
            stops_df, edges_df = load_transit_data()
            
            # Simple aggregation to create "Lines" from edges data
            # Real lines are typically sequences, but here we just list the modes and line names available.
            # In data_loader.py: transit_edges_df has columns like "from", "to", "mode", "time", "cost", "distance"
            # It might also have "line" or similar if the raw JSON has it, but let's safely group by mode.
            
            lines_summary = []
            
            # Let's see if we can just safely group by 'mode' for a very high level summary
            unique_modes = edges_df['mode'].unique()
            for mode in unique_modes:
                mode_edges = edges_df[edges_df['mode'] == mode]
                lines_summary.append({
                    "id": str(mode).lower(),
                    "name": str(mode).title() + " Line",
                    "mode": str(mode),
                    "stop_count": len(set(mode_edges['from']).union(set(mode_edges['to'])))
                })
                
            return jsonify({
                "success": True,
                "data": lines_summary
            }), 200
        except Exception as e:
            app.logger.error(f"Error loading transit lines: {e}", exc_info=True)
            return _error_response("Failed to load transit directory.", "internal_server_error", 500)

    # Global Error Handlers to ensure consistent JSON formatting
    @app.errorhandler(404)
    def not_found(error):
        return _error_response("Endpoint not found.", "not_found", 404)

    @app.errorhandler(405)
    def method_not_allowed(error):
        return _error_response("Method not allowed.", "method_not_allowed", 405)

    @app.errorhandler(500)
    def internal_error(error):
        # We don't expose traceback or raw error text to the client
        app.logger.error(f"Internal Server Error: {error}")
        return _error_response("An unexpected server error occurred.", "internal_server_error", 500)
        
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Catch-all for unhandled exceptions (not caught by 500 handler explicitly)
        app.logger.error(f"Unhandled Exception: {e}", exc_info=True)
        return _error_response("An unexpected server error occurred.", "internal_server_error", 500)

    return app
