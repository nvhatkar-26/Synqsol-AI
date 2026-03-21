import os
from google import genai
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

def list_supported_models():
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        return

    # Initialize Client
    client = genai.Client(api_key=api_key)

    print("--- Fetching Supported Models for your API Key ---\n")

    try:
        # Use the correct attribute 'supported_actions' for the new SDK
        for model in client.models.list():
            # Standard models support 'generate_content'
            if "generate_content" in model.supported_actions:
                print(f"MODEL ID: {model.name}")
                print(f"DISPLAY NAME: {model.display_name}")
                print("-" * 30)
                
    except Exception as e:
        print(f"An error occurred: {e}")
        print("\nDEBUG TIP: If it still fails, try printing 'dir(model)' to see available attributes.")

if __name__ == "__main__":
    list_supported_models()