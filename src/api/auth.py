import os
import requests
from typing import Dict, Any

class AuthConfigurationError(Exception):
    pass

class AuthenticationError(Exception):
    pass

def _get_supabase_config():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        raise AuthConfigurationError("Supabase configuration is missing.")
    return supabase_url.rstrip("/"), supabase_key

def request_password_reset(email: str, redirect_to: str) -> Dict[str, Any]:
    url, key = _get_supabase_config()
    headers = {
        "apikey": key,
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "gotrue_meta_security": {}
    }
    try:
        response = requests.post(
            f"{url}/auth/v1/recover?redirect_to={redirect_to}", 
            json=payload, 
            headers=headers, 
            timeout=10
        )
    except requests.RequestException:
        raise AuthenticationError("Unable to connect to authentication provider.")
        
    if response.status_code == 429:
        raise AuthenticationError("Too many requests. Please try again later.")
        
    if response.status_code not in (200, 204):
        # Do not leak account existence or specific provider errors.
        pass
        
    return {"success": True}

def reset_password_with_token(new_password: str, access_token: str) -> Dict[str, Any]:
    url, key = _get_supabase_config()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "password": new_password
    }
    try:
        response = requests.put(f"{url}/auth/v1/user", json=payload, headers=headers, timeout=10)
    except requests.RequestException:
        raise AuthenticationError("Unable to connect to authentication provider.")
        
    if response.status_code != 200:
        raise AuthenticationError("Reset link is invalid or has expired.")
        
    return {"success": True}

def signup_user(email: str, password: str, full_name: str) -> Dict[str, Any]:
    url, key = _get_supabase_config()
    headers = {
        "apikey": key,
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "password": password,
        "data": {
            "full_name": full_name
        }
    }
    try:
        response = requests.post(f"{url}/auth/v1/signup", json=payload, headers=headers, timeout=10)
    except requests.RequestException:
        raise AuthenticationError("Unable to connect to authentication provider.")
        
    if response.status_code != 200:
        safe_msg = "Unable to create your account right now. Please try again."
        if response.status_code == 429:
            safe_msg = "Too many signup attempts. Please try again later."
        else:
            try:
                err_data = response.json()
                msg = (err_data.get("msg") or err_data.get("message") or err_data.get("error_description") or "").lower()
                
                if "already registered" in msg or "already in use" in msg or "already exists" in msg:
                    safe_msg = "An account with this email already exists."
                elif "password" in msg:
                    safe_msg = "Password must be at least 8 characters."
                elif "format" in msg or "invalid email" in msg:
                    safe_msg = "Please enter a valid email address."
            except Exception:
                pass
            
        raise AuthenticationError(safe_msg)
        
    data = response.json()
    
    # Supabase might return empty session if email confirmation is required
    session = data.get("session")
    user = data.get("user", {})
    metadata = user.get("user_metadata", {})
    
    if not session:
        return {
            "authenticated": False,
            "requires_email_confirmation": True,
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "full_name": metadata.get("full_name", full_name)
            }
        }
    
    return {
        "authenticated": True,
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "full_name": metadata.get("full_name", full_name)
        }
    }

def login_user(email: str, password: str) -> Dict[str, Any]:
    url, key = _get_supabase_config()
    headers = {
        "apikey": key,
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "password": password
    }
    try:
        response = requests.post(f"{url}/auth/v1/token?grant_type=password", json=payload, headers=headers, timeout=10)
    except requests.RequestException:
        raise AuthenticationError("Unable to connect to authentication provider.")
        
    if response.status_code != 200:
        safe_msg = "Unable to sign in right now. Please try again."
        if response.status_code == 429:
            safe_msg = "Too many login attempts. Please try again later."
        elif response.status_code == 400:
            try:
                err_data = response.json()
                msg = (err_data.get("msg") or err_data.get("message") or err_data.get("error_description") or "").lower()
                if "email not confirmed" in msg or "unconfirmed" in msg:
                    safe_msg = "Please confirm your email before logging in."
                elif "invalid login credentials" in msg:
                    safe_msg = "Invalid email or password."
            except Exception:
                pass
        raise AuthenticationError(safe_msg)
        
    data = response.json()
    user = data.get("user", {})
    metadata = user.get("user_metadata", {})
    
    return {
        "authenticated": True,
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "full_name": metadata.get("full_name")
        }
    }
