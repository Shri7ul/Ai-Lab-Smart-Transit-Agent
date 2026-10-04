import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

response = client.interactions.create(
    model="gemini-3.8-flash",
    input="Return only this text: Gemini API Connected"
)

print(response.output_text)