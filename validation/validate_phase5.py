import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import time
from src.api.gemini_query import parse_travel_query

def assert_semantic_match(actual, expected_key, expected_val, test_name):
    val = actual.get(expected_key)
    if val != expected_val:
        print(f"[{test_name}] Mismatch on '{expected_key}': expected {expected_val}, got {val}")
        return False
    return True

def safe_parse(query: str):
    """Parses with retries and delays to avoid rate limits."""
    # Proactively sleep 15 seconds to avoid hitting the 5 RPM limit
    time.sleep(15)
    for i in range(5):
        try:
            return parse_travel_query(query)
        except RuntimeError as e:
            if "429" in str(e) or "too_many_requests" in str(e).lower() or "quota" in str(e).lower():
                print(f"Rate limited. Sleeping for 65 seconds... (Attempt {i+1}/5)")
                time.sleep(65)
            else:
                raise e
    raise RuntimeError("Failed after 5 retries due to rate limits.")

def run_phase5_validation():
    print("Testing Gemini Query Parser...")
    
    # Check if API key exists before starting
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY is not set.")
        return

    failures = 0

    # TEST A
    print("\n--- TEST A (Bangla full query) ---")
    q_A = "UIU থেকে DU যাব, আমার বাজেট 100 টাকা এবং 45 মিনিটের মধ্যে পৌঁছাতে চাই"
    res_A = safe_parse(q_A)
    print(res_A)
    if not (assert_semantic_match(res_A, "origin", "UIU", "TEST A") and
            assert_semantic_match(res_A, "destination", "DU", "TEST A") and
            assert_semantic_match(res_A, "budget", 100.0, "TEST A") and
            assert_semantic_match(res_A, "deadline_minutes", 45.0, "TEST A") and
            assert_semantic_match(res_A, "preference", None, "TEST A")):
        failures += 1

    # TEST B
    print("\n--- TEST B (English) ---")
    q_B = "I want to go from Uttara to Motijheel within 80 taka."
    res_B = safe_parse(q_B)
    print(res_B)
    if not (assert_semantic_match(res_B, "origin", "Uttara", "TEST B") and
            assert_semantic_match(res_B, "destination", "Motijheel", "TEST B") and
            assert_semantic_match(res_B, "budget", 80.0, "TEST B") and
            assert_semantic_match(res_B, "deadline_minutes", None, "TEST B") and
            assert_semantic_match(res_B, "preference", None, "TEST B")):
        failures += 1

    # TEST C
    print("\n--- TEST C (Mixed language + preference) ---")
    q_C = "Shahbag থেকে Farmgate যাব, 30 minutes এর মধ্যে, কম হাঁটতে চাই"
    res_C = safe_parse(q_C)
    print(res_C)
    if not (assert_semantic_match(res_C, "origin", "Shahbag", "TEST C") and
            assert_semantic_match(res_C, "destination", "Farmgate", "TEST C") and
            assert_semantic_match(res_C, "budget", None, "TEST C") and
            assert_semantic_match(res_C, "deadline_minutes", 30.0, "TEST C") and
            assert_semantic_match(res_C, "preference", "less_walking", "TEST C")):
        failures += 1

    # TEST D
    print("\n--- TEST D (Minimal query) ---")
    q_D = "UIU থেকে DU যাব"
    res_D = safe_parse(q_D)
    print(res_D)
    if not (assert_semantic_match(res_D, "origin", "UIU", "TEST D") and
            assert_semantic_match(res_D, "destination", "DU", "TEST D") and
            assert_semantic_match(res_D, "budget", None, "TEST D") and
            assert_semantic_match(res_D, "deadline_minutes", None, "TEST D") and
            assert_semantic_match(res_D, "preference", None, "TEST D")):
        failures += 1

    # TEST E
    print("\n--- TEST E (Cheapest) ---")
    q_E = "I need the cheapest route from Uttara to Shahbag under 70 taka."
    res_E = safe_parse(q_E)
    print(res_E)
    if not (assert_semantic_match(res_E, "origin", "Uttara", "TEST E") and
            assert_semantic_match(res_E, "destination", "Shahbag", "TEST E") and
            assert_semantic_match(res_E, "budget", 70.0, "TEST E") and
            assert_semantic_match(res_E, "preference", "cheapest", "TEST E")):
        failures += 1

    # TEST F
    print("\n--- TEST F (Fastest) ---")
    q_F = "Farmgate থেকে Motijheel দ্রুত যেতে চাই"
    res_F = safe_parse(q_F)
    print(res_F)
    if not (assert_semantic_match(res_F, "origin", "Farmgate", "TEST F") and
            assert_semantic_match(res_F, "destination", "Motijheel", "TEST F") and
            assert_semantic_match(res_F, "preference", "fastest", "TEST F")):
        failures += 1

    # TEST G
    print("\n--- TEST G (Fewer transfers) ---")
    q_G = "I want to travel from Banani to Motijheel with fewer transfers."
    res_G = safe_parse(q_G)
    print(res_G)
    if not (assert_semantic_match(res_G, "preference", "fewer_transfers", "TEST G")):
        failures += 1

    # TEST H
    print("\n--- TEST H (Bangla numerals) ---")
    q_H = "UIU থেকে DU যাব, বাজেট ১০০ টাকা"
    res_H = safe_parse(q_H)
    print(res_H)
    if not (assert_semantic_match(res_H, "budget", 100.0, "TEST H")):
        failures += 1

    # TEST I
    print("\n--- TEST I (Duration conversion) ---")
    q_I = "Uttara থেকে Motijheel 1 hour 30 minutes এর মধ্যে যেতে চাই"
    res_I = safe_parse(q_I)
    print(res_I)
    if not (assert_semantic_match(res_I, "deadline_minutes", 90.0, "TEST I")):
        failures += 1

    # TEST J
    print("\n--- TEST J (Absolute clock deadline) ---")
    q_J = "UIU থেকে DU সকাল 9টার আগে পৌঁছাতে চাই"
    res_J = safe_parse(q_J)
    print(res_J)
    if not (assert_semantic_match(res_J, "deadline_minutes", None, "TEST J")):
        failures += 1

    # TEST K
    print("\n--- TEST K (Empty query) ---")
    try:
        parse_travel_query("   ")
        print("TEST K failed! Did not raise ValueError for empty query.")
        failures += 1
    except ValueError as e:
        print(f"TEST K Passed: Caught empty query exception: {e}")

    print(f"\nPhase 5 Validation complete with {failures} failures.")
    assert failures == 0, f"Phase 5 failed {failures} tests."
    print("Phase 5 Validation PASSED")

if __name__ == "__main__":
    run_phase5_validation()
