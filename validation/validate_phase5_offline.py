import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json

from src.api.gemini_query import (
    _parse_gemini_response,
    parse_travel_query,
)


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(
            f"{message}\nExpected: {expected}\nActual: {actual}"
        )


def run_phase5_offline_validation():
    print("Starting Phase 5 Offline Validation...\n")

    # --------------------------------------------------
    # TEST 1 — Valid complete JSON
    # --------------------------------------------------
    print("TEST 1 - Valid complete JSON")

    raw = """
    {
        "origin": "UIU",
        "destination": "DU",
        "budget": 100,
        "deadline_minutes": 45,
        "preference": "less_walking"
    }
    """

    result = _parse_gemini_response(raw)

    assert_equal(result["origin"], "UIU", "Origin mismatch")
    assert_equal(result["destination"], "DU", "Destination mismatch")
    assert_equal(result["budget"], 100.0, "Budget mismatch")
    assert_equal(
        result["deadline_minutes"],
        45.0,
        "Deadline mismatch",
    )
    assert_equal(
        result["preference"],
        "less_walking",
        "Preference mismatch",
    )

    print("PASS\n")

    # --------------------------------------------------
    # TEST 2 — Missing optional fields
    # --------------------------------------------------
    print("TEST 2 - Missing optional fields")

    raw = """
    {
        "origin": "UIU",
        "destination": "DU"
    }
    """

    result = _parse_gemini_response(raw)

    assert_equal(result["budget"], None, "Budget should be None")
    assert_equal(
        result["deadline_minutes"],
        None,
        "Deadline should be None",
    )
    assert_equal(
        result["preference"],
        None,
        "Preference should be None",
    )

    print("PASS\n")

    # --------------------------------------------------
    # TEST 3 — Markdown fenced JSON
    # --------------------------------------------------
    print("TEST 3 - Markdown fenced JSON")

    raw = """```json
{
    "origin": "Uttara",
    "destination": "Motijheel",
    "budget": 80,
    "deadline_minutes": null,
    "preference": null
}
```"""

    result = _parse_gemini_response(raw)

    assert_equal(result["origin"], "Uttara", "Origin mismatch")
    assert_equal(
        result["destination"],
        "Motijheel",
        "Destination mismatch",
    )
    assert_equal(result["budget"], 80.0, "Budget mismatch")

    print("PASS\n")

    # --------------------------------------------------
    # TEST 4 — Extra hallucinated field
    # --------------------------------------------------
    print("TEST 4 - Extra field ignored")

    raw = """
    {
        "origin": "UIU",
        "destination": "DU",
        "budget": 100,
        "deadline_minutes": 45,
        "preference": null,
        "vehicle": "bus",
        "fake_field": "something"
    }
    """

    result = _parse_gemini_response(raw)

    expected_keys = {
        "origin",
        "destination",
        "budget",
        "deadline_minutes",
        "departure_time",
        "arrival_deadline",
        "preference",
        "preferences",
    }

    assert_equal(
        set(result.keys()),
        expected_keys,
        "Unexpected fields were returned",
    )

    print("PASS\n")

    # --------------------------------------------------
    # TEST 5 — Invalid preference
    # --------------------------------------------------
    print("TEST 5 - Invalid preference")

    raw = """
    {
        "origin": "UIU",
        "destination": "DU",
        "budget": 100,
        "deadline_minutes": 45,
        "preference": "luxury_route"
    }
    """

    result = _parse_gemini_response(raw)

    assert_equal(
        result["preference"],
        None,
        "Invalid preference should become None",
    )

    print("PASS\n")

    # --------------------------------------------------
    # TEST 6 — Wrong data types
    # --------------------------------------------------
    print("TEST 6 - Wrong data types")

    raw = """
    {
        "origin": 123,
        "destination": ["DU"],
        "budget": "100 taka",
        "deadline_minutes": "45 minutes",
        "preference": 123
    }
    """

    result = _parse_gemini_response(raw)

    assert_equal(result["origin"], None, "Invalid origin not rejected")
    assert_equal(
        result["destination"],
        None,
        "Invalid destination not rejected",
    )
    assert_equal(result["budget"], 100.0, "Invalid budget not correctly extracted")
    assert_equal(
        result["deadline_minutes"],
        45.0,
        "Invalid deadline not correctly extracted",
    )
    assert_equal(
        result["preference"],
        None,
        "Invalid preference not rejected",
    )

    print("PASS\n")

    # --------------------------------------------------
    # TEST 7 — Absolute clock deadline represented safely
    # --------------------------------------------------
    print("TEST 7 - Absolute clock deadline")

    raw = """
    {
        "origin": "UIU",
        "destination": "DU",
        "budget": null,
        "deadline_minutes": null,
        "preference": null
    }
    """

    result = _parse_gemini_response(raw)

    assert_equal(
        result["deadline_minutes"],
        None,
        "Absolute clock deadline must not become duration",
    )

    print("PASS\n")

    # --------------------------------------------------
    # TEST 8 — Malformed JSON
    # --------------------------------------------------
    print("TEST 8 - Malformed JSON")

    try:
        _parse_gemini_response(
            '{"origin": "UIU", "destination": "DU"'
        )
        raise AssertionError("Malformed JSON was not rejected")

    except ValueError:
        print("PASS\n")

    # --------------------------------------------------
    # TEST 9 — Empty Gemini response
    # --------------------------------------------------
    print("TEST 9 - Empty Gemini response")

    try:
        _parse_gemini_response("   ")
        raise AssertionError("Empty response was not rejected")

    except ValueError:
        print("PASS\n")

    # --------------------------------------------------
    # TEST 10 — JSON must be an object
    # --------------------------------------------------
    print("TEST 10 - Non-object JSON")

    try:
        _parse_gemini_response('["UIU", "DU"]')
        raise AssertionError("JSON array was not rejected")

    except ValueError:
        print("PASS\n")

    # --------------------------------------------------
    # TEST 11 — Empty user query
    # No API call should happen
    # --------------------------------------------------
    print("TEST 11 - Empty user query")

    try:
        parse_travel_query("")
        raise AssertionError("Empty query was not rejected")

    except ValueError:
        print("PASS\n")

    # --------------------------------------------------
    # TEST 12 — Whitespace-only query
    # --------------------------------------------------
    print("TEST 12 - Whitespace-only query")

    try:
        parse_travel_query("     ")
        raise AssertionError("Whitespace query was not rejected")

    except ValueError:
        print("PASS\n")

    # --------------------------------------------------
    # TEST 13 — None input
    # --------------------------------------------------
    print("TEST 13 - None input")

    try:
        parse_travel_query(None)  # type: ignore[arg-type]
        raise AssertionError("None input was not rejected")

    except TypeError:
        print("PASS\n")

    # --------------------------------------------------
    # TEST 14 — Numeric input
    # --------------------------------------------------
    print("TEST 14 - Numeric input")

    try:
        parse_travel_query(123)  # type: ignore[arg-type]
        raise AssertionError("Numeric input was not rejected")

    except TypeError:
        print("PASS\n")

    print("=" * 50)
    print("PHASE 5 OFFLINE VALIDATION PASSED")
    print("=" * 50)


if __name__ == "__main__":
    run_phase5_offline_validation()