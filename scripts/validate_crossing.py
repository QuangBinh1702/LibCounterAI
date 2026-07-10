import os
import sys
import time
import subprocess
import urllib.request
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(CWD, ".venv", "Scripts", "python.exe")
APP_MAIN = os.path.join(CWD, "app", "main.py")
TEST_IMAGE = os.path.join(CWD, "test_crossing_frame.jpg")

print("Starting validation test for line crossing...")

# --- 1. Unit test geometry module directly ---
try:
    sys.path.insert(0, os.path.join(CWD, "app"))
    from geometry import intersects, get_crossing_direction
    
    # Define directed virtual line going right: (100, 280) -> (200, 280)
    line_start = (100, 280)
    line_end = (200, 280)
    
    # Trajectory crossing downwards: (150, 250) -> (150, 310)
    traj_start_1 = (150, 250)
    traj_end_1 = (150, 310)
    
    assert intersects(line_start, line_end, traj_start_1, traj_end_1) == True, "Geometry intersection failed"
    dir_1 = get_crossing_direction(line_start, line_end, traj_start_1, traj_end_1)
    assert dir_1 == 1, f"Expected crossing direction 1, got {dir_1}"
    
    # Trajectory not crossing: (150, 250) -> (150, 270)
    traj_start_2 = (150, 250)
    traj_end_2 = (150, 270)
    assert intersects(line_start, line_end, traj_start_2, traj_end_2) == False, "Geometry false intersection failed"

    vertical_line_start = (320, 40)
    vertical_line_end = (320, 600)
    horizontal_traj_start = (260, 300)
    horizontal_traj_end = (340, 300)
    assert intersects(vertical_line_start, vertical_line_end, horizontal_traj_start, horizontal_traj_end) == True, "Vertical line intersection failed"
    dir_2 = get_crossing_direction(vertical_line_start, vertical_line_end, horizontal_traj_start, horizontal_traj_end)
    assert dir_2 == -1, f"Expected vertical crossing direction -1, got {dir_2}"
    
    print("Geometry unit tests passed successfully.")
except Exception as e:
    print(f"Geometry unit test failed: {e}")
    sys.exit(1)


# --- 2. Integration test via API ---
try:
    import cv2
    import numpy as np
    # Create 640x640 gray image
    img = np.ones((640, 640, 3), dtype=np.uint8) * 128
    cv2.imwrite(TEST_IMAGE, img)
except Exception as e:
    print(f"Error creating test image: {e}")
    sys.exit(1)

# Start FastAPI server
server_process = None
try:
    print("Launching FastAPI server...")
    server_process = subprocess.Popen(
        [VENV_PYTHON, APP_MAIN],
        cwd=CWD,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )
except Exception as e:
    print(f"Failed to start server: {e}")
    if os.path.exists(TEST_IMAGE):
        os.remove(TEST_IMAGE)
    sys.exit(1)

# Wait for server to start up
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
    print("Server failed to start in time.")
    server_process.terminate()
    if os.path.exists(TEST_IMAGE):
        os.remove(TEST_IMAGE)
    sys.exit(1)

# Helper function to send multipart process-frame request
def send_frame(mock_dets_str, line_config_str, session_id):
    with open(TEST_IMAGE, "rb") as f:
        image_bytes = f.read()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = []
    
    # File
    body.append(f"--{boundary}".encode('utf-8'))
    body.append(b'Content-Disposition: form-data; name="file"; filename="test_crossing_frame.jpg"')
    body.append(b'Content-Type: image/jpeg')
    body.append(b'')
    body.append(image_bytes)
    
    # Session ID
    body.append(f"--{boundary}".encode('utf-8'))
    body.append(b'Content-Disposition: form-data; name="session_id"')
    body.append(b'')
    body.append(session_id.encode('utf-8'))
    
    # Line Config
    if line_config_str:
        body.append(f"--{boundary}".encode('utf-8'))
        body.append(b'Content-Disposition: form-data; name="line_config"')
        body.append(b'')
        body.append(line_config_str.encode('utf-8'))
        
    # Mock Detections
    if mock_dets_str:
        body.append(f"--{boundary}".encode('utf-8'))
        body.append(b'Content-Disposition: form-data; name="mock_detections"')
        body.append(b'')
        body.append(mock_dets_str.encode('utf-8'))
        
    body.append(f"--{boundary}--".encode('utf-8'))
    body.append(b'')
    
    payload = b'\r\n'.join(body)
    
    req = urllib.request.Request(process_url, data=payload)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.add_header('Content-Length', str(len(payload)))
    
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status == 200:
            return json.loads(response.read().decode())
    return None

validation_passed = False
try:
    session_id = f"session_{int(time.time())}"
    line_config_str = "[[100, 280], [200, 280]]"
    
    # Frame 1: Person above the line. Bottom center is at (150, 250)
    mock_dets_1 = "[[100, 50, 200, 250, 0.9]]"
    print("Sending Frame 1 (Person above line)...")
    res_1 = send_frame(mock_dets_1, line_config_str, session_id)
    print(f"Frame 1 Response: {res_1}")
    
    # Frame 2: Person below the line. Bottom center is at (150, 310)
    # The bottom center path is (150, 250) -> (150, 310) which cuts the line [[100, 280], [200, 280]]
    mock_dets_2 = "[[100, 110, 200, 310, 0.9]]"
    print("Sending Frame 2 (Person below line)...")
    res_2 = send_frame(mock_dets_2, line_config_str, session_id)
    print(f"Frame 2 Response: {res_2}")
    
    # Assertions
    tracks_2 = res_2.get("tracks", [])
    crossing_events_2 = res_2.get("crossing_events", [])
    
    assert len(tracks_2) == 1, "Expected 1 tracked person"
    assert len(crossing_events_2) == 1, f"Expected 1 crossing event, got {len(crossing_events_2)}"
    
    event = crossing_events_2[0]
    assert event.get("direction") == "ENTRY", f"Expected direction ENTRY, got {event.get('direction')}"

    vertical_session_id = f"vertical_session_{int(time.time())}"
    vertical_line_config_str = "[[320, 40], [320, 600]]"

    # For vertical lines the tracker uses bbox center, not feet, so side-to-side walking is counted.
    mock_dets_3 = "[[180, 100, 340, 500, 0.9]]"
    print("Sending Frame 3 (Person left of vertical line)...")
    res_3 = send_frame(mock_dets_3, vertical_line_config_str, vertical_session_id)
    print(f"Frame 3 Response: {res_3}")

    mock_dets_4 = "[[260, 100, 420, 500, 0.9]]"
    print("Sending Frame 4 (Person crossed vertical line)...")
    res_4 = send_frame(mock_dets_4, vertical_line_config_str, vertical_session_id)
    print(f"Frame 4 Response: {res_4}")

    crossing_events_4 = res_4.get("crossing_events", [])
    assert len(crossing_events_4) == 1, f"Expected 1 vertical crossing event, got {len(crossing_events_4)}"
    assert crossing_events_4[0].get("direction") == "EXIT", f"Expected vertical direction EXIT, got {crossing_events_4[0].get('direction')}"
    
    print("Line crossing integration tests PASSED successfully!")
    validation_passed = True

except Exception as e:
    print(f"Error during API crossing test: {e}")
    validation_passed = False

# Clean up
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
