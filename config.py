import os
from dotenv import load_dotenv

load_dotenv()

# This pulls the key from the .env file safely
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"