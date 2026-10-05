import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(override=True)

from src.api.auth import signup_user, AuthenticationError

def diagnose_signup():
    try:
        result = signup_user("test-new-user@example.com", "password1234", "Test User")
        print("Success:", result)
    except AuthenticationError as e:
        print("AuthenticationError:", e)
    except Exception as e:
        print("Exception:", type(e), e)

if __name__ == "__main__":
    diagnose_signup()
