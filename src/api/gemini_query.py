import json
import os
from typing import Literal, TypedDict, cast

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError


load_dotenv()


MODEL_NAME = "gemini-3.8-flash"

Preference = Literal[
    "fastest",
    "lowest_cost",
    "cheapest", # legacy
    "less_walking",
    "fewer_transfers",
    "balanced",
]


class TravelQueryResult(TypedDict):
    origin: str | None
    destination: str | None
    budget: float | None
    deadline_minutes: float | None
    departure_time: str | None
    arrival_deadline: str | None
    preference: Preference | None
    preferences: list[Preference]


ALLOWED_PREFERENCES = {
    "fastest",
    "lowest_cost",
    "cheapest",
    "less_walking",
    "fewer_transfers",
    "balanced",
}


SYSTEM_PROMPT = """
You are a smart transit query parser.

Extract travel information from the user's input.

The user may write in English, Bangla, or mixed Bangla-English.

Return a strict JSON object with EXACTLY these fields:

{
    "origin": string | null,
    "destination": string | null,
    "budget": number | null,
    "deadline_minutes": number | null,
    "departure_time": string | null,
    "arrival_deadline": string | null,
    "preference": string | null,
    "preferences": list[string]
}

Rules:

1. origin
   - Starting place stated by the user.
   - TRANSLATE Bangla place names to English (e.g. "শাহবাগ" -> "Shahbag").
   - Return null if missing.

2. destination
   - Destination stated by the user.
   - TRANSLATE Bangla place names to English (e.g. "মতিঝিল" -> "Motijheel").
   - Return null if missing.

3. budget
   - Maximum travel budget in BDT.
   - Return a number only.
   - Examples:
     "100 taka" -> 100
     "100 টাকা" -> 100
     "১০০ টাকা" -> 100
     "৳120" -> 120
   - Return null if no budget is given.
   - Do not invent a budget.

4. deadline_minutes
   - Maximum allowed journey duration in minutes.
   - Examples:
     "45 minutes" -> 45
     "45 মিনিট" -> 45
     "1 hour" -> 60
     "1 hour 30 minutes" -> 90
     "1 ঘণ্টা 30 মিনিট" -> 90
   - IMPORTANT:
     Absolute clock deadlines such as:
     "before 9 AM"
     "সকাল ৯টার আগে"
     must NOT be converted into duration.
   - If only an absolute clock deadline is provided,
     return null for deadline_minutes.

5. departure_time
   - Absolute local clock time of departure in ISO 8601 format (e.g. "YYYY-MM-DDTHH:mm:ss+06:00").
   - E.g. "at 8 AM" -> ISO for today's 08:00 (assume Dhaka timezone +06:00 if not specified).
   - Return null if missing.

6. arrival_deadline
   - Absolute local clock time of deadline in ISO 8601 format.
   - E.g. "before 9 AM" -> ISO for today's 09:00 (assume Dhaka timezone +06:00 if not specified).
   - If user says a range "8 AM to 9 AM" or "৮টা থেকে ৯টার মধ্যে": departure_time=08:00, arrival_deadline=09:00.
   - If it is an overnight range "11:30 PM to 1 AM": departure_time=23:30 (Day 1), arrival_deadline=01:00 (Day 2).
   - Return null if missing.

7. preferences
   List of requested preferences, ordered by user priority (most important first).
   Must be a subset of: ["fastest", "lowest_cost", "less_walking", "fewer_transfers", "balanced"]

   Examples:
   "দ্রুত যেতে চাই" -> ["fastest"]
   "সবচেয়ে কম খরচের route চাই" -> ["lowest_cost"]
   "কম হাঁটতে চাই এবং কম ট্রান্সফার চাই" -> ["less_walking", "fewer_transfers"]
   "কম হাঁটা সবচেয়ে গুরুত্বপূর্ণ, তারপর কম ট্রান্সফার" -> ["less_walking", "fewer_transfers"]
   "কম খরচ এবং কম ট্রান্সফার চাই" -> ["lowest_cost", "fewer_transfers"]

   If no preference is explicitly stated, return an empty array [].
   (For backward compatibility, also populate the single 'preference' string with the first item, or null).

IMPORTANT:
- Never invent missing information.
- Return ONLY raw valid JSON.
- Do not use Markdown code fences.
- Do not write explanations before or after the JSON.
"""


def _normalize_bangla_digits(text: str) -> str:
    """Normalize Bengali numerals to standard Western numerals."""
    return text.translate(str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789'))


def _clean_text(value: object) -> str | None:
    """Return a cleaned string or None."""
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    return cleaned if cleaned else None


def _clean_number(value: object) -> float | None:
    """Return a non-negative numeric value or None."""
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        if number >= 0:
            return number
            
    if isinstance(value, str):
        cleaned = _normalize_bangla_digits(value).replace(',', '').strip()
        # Extract the first valid number sequence from the string
        import re
        match = re.search(r'\d+(\.\d+)?', cleaned)
        if match:
            number = float(match.group(0))
            if number >= 0:
                return number
                
    return None


def _strip_markdown_fences(text: str) -> str:
    """Remove accidental Markdown code fences from model output."""
    cleaned = text.strip()

    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()

    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _parse_gemini_response(output_text: str) -> TravelQueryResult:
    """
    Parse and validate Gemini JSON output.

    This function performs no API call, so it can be tested locally.
    """
    text = _strip_markdown_fences(output_text)

    if not text:
        raise ValueError("Gemini returned an empty response.")

    try:
        parsed_json = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned invalid JSON.") from exc

    if not isinstance(parsed_json, dict):
        raise ValueError("Gemini response must be a JSON object.")

    # Validate essential keys explicitly to prevent silent malformed responses
    if "origin" not in parsed_json and "destination" not in parsed_json:
        # Though the fields can be null, missing them entirely from a dict means the model failed structure
        pass

    result: TravelQueryResult = {
        "origin": _clean_text(parsed_json.get("origin")),
        "destination": _clean_text(parsed_json.get("destination")),
        "budget": _clean_number(parsed_json.get("budget")),
        "deadline_minutes": _clean_number(
            parsed_json.get("deadline_minutes")
        ),
        "departure_time": _clean_text(parsed_json.get("departure_time")),
        "arrival_deadline": _clean_text(parsed_json.get("arrival_deadline")),
        "preference": None,
        "preferences": [],
    }

    # Extract multiple preferences
    prefs = parsed_json.get("preferences", [])
    if isinstance(prefs, list):
        for p in prefs:
            if isinstance(p, str):
                normalized = p.strip().lower().replace(" ", "_")
                if normalized == "cheapest":
                    normalized = "lowest_cost"
                if normalized in ALLOWED_PREFERENCES and normalized not in result["preferences"]:
                    result["preferences"].append(cast(Preference, normalized))

    # Backward compatibility for single preference
    preference = parsed_json.get("preference")
    if isinstance(preference, str):
        normalized = preference.strip().lower().replace(" ", "_")
        if normalized == "cheapest":
            normalized = "lowest_cost"
        if normalized in ALLOWED_PREFERENCES:
            result["preference"] = cast(Preference, normalized)
            if normalized not in result["preferences"]:
                result["preferences"].insert(0, cast(Preference, normalized))
                
    if not result["preference"] and result["preferences"]:
        result["preference"] = result["preferences"][0]

    return result


def parse_travel_query(user_query: str) -> TravelQueryResult:
    """
    Convert a natural-language travel query into structured data
    using the Gemini API.
    """
    if not isinstance(user_query, str):
        raise TypeError("User query must be a string.")

    query = user_query.strip()

    if not query:
        raise ValueError("User query cannot be empty.")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is missing."
        )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=3,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            )
        ),
    )

    full_prompt = f"""
{SYSTEM_PROMPT}

User query:
{query}
"""

    try:
        response = client.interactions.create(
            model=MODEL_NAME,
            input=full_prompt,
            timeout=60.0,
        )
    except Exception as exc:
        err_msg = str(exc)
        class_name = type(exc).__name__
        if "429" in err_msg or "RateLimitError" in class_name:
            raise RuntimeError("Gemini rate limit exceeded. Please retry later.") from exc
        raise RuntimeError("Gemini query parsing request failed or timed out.") from exc

    output_text = response.output_text

    if not isinstance(output_text, str) or not output_text.strip():
        raise ValueError("Gemini returned an empty response.")

    return _parse_gemini_response(output_text)


if __name__ == "__main__":
    query = input("Enter travel query: ")

    try:
        result = parse_travel_query(query)

        print("\nParsed Query:")
        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False,
            )
        )

    except (TypeError, ValueError, RuntimeError) as exc:
        print(f"\nError: {exc}")