import urllib.request
import json
import os
import subprocess
import sys
import time

URL = "http://localhost:8000/api/health"
MAX_RETRIES = 15
RETRY_INTERVAL = 2.0
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
server_process = None

print(f"Starting health validation check against {URL}...")

def try_health_request():
    try:
        req = urllib.request.Request(URL)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"Received response: {data}")
                
                # Validate response structure
                if data.get("status") == "healthy" and "services" in data:
                    print("Health check validation PASSED successfully!")
                    return True
                else:
                    print("Health check response invalid structure.")
            else:
                print(f"Health check returned status code: {response.status}")
    except Exception as e:
        print(f"Health request failed: {e}")
    return False


try:
    if not try_health_request():
        print("Health endpoint is not already running; launching FastAPI server...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=APP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    
    for attempt in range(1, MAX_RETRIES + 1):
        if try_health_request():
            sys.exit(0)
        print(f"Attempt {attempt}/{MAX_RETRIES} failed.")
        time.sleep(RETRY_INTERVAL)

    print("Health check validation FAILED after max retries.")
    if server_process and server_process.stdout:
        print("Server output:")
        print(server_process.stdout.read())
    sys.exit(1)
finally:
    if server_process:
        print("Terminating server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
