import os
from google import genai
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

def list_supported_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return

    client = genai.Client(api_key=api_key)
    print("--- Fetching ALL Models ---")

    try:
        # Get the list and convert to a standard Python list immediately
        models = list(client.models.list())
        
        if not models:
            print("No models found. Check if your API Key is active in Google AI Studio.")
            return

        for model in models:
            # Print everything so we can find the exact string needed
            print(f"ID: {model.name} | Display: {model.display_name}")
                
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    list_supported_models()