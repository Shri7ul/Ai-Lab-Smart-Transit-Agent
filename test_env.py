import os
from dotenv import load_dotenv

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")
weather_key = os.getenv("OPENWEATHER_API_KEY")
nominatim_url = os.getenv("NOMINATIM_API_URL")

print("Gemini API:", "Loaded" if gemini_key else "Not Loaded")
print("Weather API:", "Loaded" if weather_key else "Not Loaded")
print("Nominatim URL:", nominatim_url)