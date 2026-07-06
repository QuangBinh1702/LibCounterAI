import urllib.request
import json
import sys
import time

URL = "http://localhost:8000/api/health"
MAX_RETRIES = 15
RETRY_INTERVAL = 2.0

print(f"Starting health validation check against {URL}...")

for attempt in range(1, MAX_RETRIES + 1):
    try:
        req = urllib.request.Request(URL)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"Received response: {data}")
                
                # Validate response structure
                if data.get("status") == "healthy" and "services" in data:
                    print("Health check validation PASSED successfully!")
                    sys.exit(0)
                else:
                    print("Health check response invalid structure.")
            else:
                print(f"Health check returned status code: {response.status}")
    except Exception as e:
        print(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
    
    time.sleep(RETRY_INTERVAL)

print("Health check validation FAILED after max retries.")
sys.exit(1)
