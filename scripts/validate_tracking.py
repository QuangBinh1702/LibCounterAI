import os
import sys
import time
import subprocess
import urllib.request
import json

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(CWD, ".venv", "Scripts", "python.exe")
APP_MAIN = os.path.join(CWD, "app", "main.py")
TEST_IMAGE = os.path.join(CWD, "test_frame.jpg")

print("Starting validation test for tracking...")

# 1. Create a dummy image file for upload
try:
    import cv2
    import numpy as np
    # Create a 640x640 gray image
    img = np.ones((640, 640, 3), dtype=np.uint8) * 128
    # Draw a rectangle to simulate a person if needed, but a blank is fine to test pipeline
    cv2.imwrite(TEST_IMAGE, img)
    print("Dummy test image created.")
except Exception as e:
    print(f"Error creating dummy image: {e}")
    sys.exit(1)

# 2. Start the FastAPI server
server_process = None
try:
    print("Launching FastAPI server...")
    server_process = subprocess.Popen(
        [VENV_PYTHON, APP_MAIN],
        cwd=CWD,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
except Exception as e:
    print(f"Failed to start server: {e}")
    if os.path.exists(TEST_IMAGE):
        os.remove(TEST_IMAGE)
    sys.exit(1)

# 3. Wait for server to start up
health_url = "http://localhost:8000/api/health"
process_url = "http://localhost:8000/api/process-frame"
max_attempts = 15
ready = False

for attempt in range(1, max_attempts + 1):
    try:
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                print("Server is ready and healthy!")
                ready = True
                break
    except Exception:
        pass
    print(f"Waiting for server (attempt {attempt}/{max_attempts})...")
    time.sleep(2.0)

if not ready:
    print("Server failed to start in time. Output:")
    stdout, stderr = server_process.communicate(timeout=2)
    print(f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}")
    server_process.terminate()
    if os.path.exists(TEST_IMAGE):
        os.remove(TEST_IMAGE)
    sys.exit(1)

# 4. Perform the process-frame request (Multipart Form Upload)
# Since urllib.request is a bit verbose for multipart/form-data, we will construct it manually
try:
    with open(TEST_IMAGE, "rb") as f:
        image_bytes = f.read()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    # Construct multipart request body
    body = []
    
    # File field
    body.append(f"--{boundary}".encode('utf-8'))
    body.append(b'Content-Disposition: form-data; name="file"; filename="test_frame.jpg"')
    body.append(b'Content-Type: image/jpeg')
    body.append(b'')
    body.append(image_bytes)
    
    # session_id field
    body.append(f"--{boundary}".encode('utf-8'))
    body.append(b'Content-Disposition: form-data; name="session_id"')
    body.append(b'')
    body.append(b'test_session')
    
    body.append(f"--{boundary}--".encode('utf-8'))
    body.append(b'')
    
    payload = b'\r\n'.join(body)
    
    req = urllib.request.Request(process_url, data=payload)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.add_header('Content-Length', str(len(payload)))
    
    print("Sending frame to /api/process-frame...")
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status == 200:
            result = json.loads(response.read().decode())
            print(f"Server response: {result}")
            
            # Assertions
            if result.get("session_id") == "test_session" and "tracks" in result:
                print("Tracking validation PASSED successfully!")
                validation_passed = True
            else:
                print("Response failed schema assertions.")
                validation_passed = False
        else:
            print(f"Server returned status {response.status}")
            validation_passed = False
except Exception as e:
    print(f"Error during API request: {e}")
    validation_passed = False

# 5. Clean up
print("Terminating server...")
server_process.terminate()
try:
    server_process.wait(timeout=5)
except subprocess.TimeoutExpired:
    server_process.kill()

if os.path.exists(TEST_IMAGE):
    os.remove(TEST_IMAGE)

if validation_passed:
    sys.exit(0)
else:
    sys.exit(1)
