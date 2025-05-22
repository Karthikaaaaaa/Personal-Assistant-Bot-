import os
from dotenv import load_dotenv
import google.generativeai as genai

def load_config():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API key not found in .env file")
    genai.configure(api_key=api_key)
    return {
        "api_key": api_key,
        "model_name": "gemini-2.0-flash"
    }