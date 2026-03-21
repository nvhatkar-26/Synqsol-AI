import requests

def run_test():
    print("Testing Synqsol...")
    try:
        # 1. Get Questions
        qs = requests.get("http://127.0.0.1:8000/questions").json()
        
        # 2. Submit
        data = {"user_id": "Neha", "answers": [{"trait": q["trait"], "answer": "Agree"} for q in qs]}
        resp = requests.post("http://127.0.0.1:8000/generate-report", json=data)
        
        if resp.status_code == 200:
            print("SUCCESS: Report generated!")
        else:
            print("FAILED: Server returned error.")
    except Exception as e:
        print(f"FAILED: Connection Error. Is main.py running? {e}")

if __name__ == "__main__":
    run_test()