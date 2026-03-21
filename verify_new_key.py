import os
from google import genai
from dotenv import load_dotenv

# 1. Load the new key from your .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: No API key found in .env. Please check the file name and content.")
else:
    # 2. Initialize the client
    client = genai.Client(api_key=api_key)

    print(f"--- Testing New Key: {api_key[:4]}...{api_key[-4:]} ---")

    try:
        # 3. Direct attempt to generate content
        # We skip 'list_models' and go straight to the goal
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents="Hello Synqsol! Are you online?"
        )
        
        print("\nSUCCESS!")
        print(f"Gemini Response: {response.text}")
        print("\nYour Synqsol Agent is now ready to generate reports.")

    except Exception as e:
        print("\nStill encountering an issue.")
        print(f"Error Details: {e}")
        print("\nCHECKLIST:")
        print("1. Did you enable 'Generative Language API' in Google AI Studio?")
        print("2. Is your internet connection stable (no firewall/VPN blocking Google APIs)?")