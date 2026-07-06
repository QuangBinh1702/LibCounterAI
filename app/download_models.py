import os
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS = {
    "yolov8n.onnx": [
        "https://github.com/Hyuto/yolov8-onnxruntime-web/raw/master/public/model/yolov8n.onnx",
        "https://github.com/Hyuto/yolov8-onnxruntime-web/raw/main/public/model/yolov8n.onnx"
    ],
    "face_detection_yunet_2023mar.onnx": [
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ],
    "face_recognition_sface_2021dec.onnx": [
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ]
}

def download_file(url, dest_path):
    print(f"Attempting to download from {url} to {dest_path}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content_length = response.getheader('content-length')
            total_size = int(content_length) if content_length else 0
            downloaded = 0
            
            with open(dest_path, 'wb') as out_file:
                while True:
                    chunk = response.read(1024 * 1024) # 1MB chunk
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        print(f"Downloaded {downloaded / (1024*1024):.2f}MB / {total_size / (1024*1024):.2f}MB ({percent:.1f}%)")
                    else:
                        print(f"Downloaded {downloaded / (1024*1024):.2f}MB")
                        
        print(f"Successfully downloaded and saved to {dest_path}")
        return True
    except Exception as e:
        print(f"Error downloading: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

def download_all_models():
    for model_name, urls in MODELS.items():
        dest_path = os.path.join(APP_DIR, model_name)
        if os.path.exists(dest_path):
            print(f"Model {model_name} already exists.")
            continue
            
        success = False
        for url in urls:
            if download_file(url, dest_path):
                success = True
                break
        if not success:
            print(f"Failed to download model {model_name} from all URLs.")
            return False
    return True

if __name__ == "__main__":
    download_all_models()
