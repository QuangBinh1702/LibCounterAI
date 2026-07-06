# AI Processing Pipeline - LibCounterAI

Tài liệu này đặc tả quy trình và các cấu phần kỹ thuật của pipeline AI xử lý video stream để đếm người và nhận diện khuôn mặt trên server.

## 1. Pipeline Tổng Quát

Luồng xử lý diễn ra theo trình tự tuần tự qua các block chức năng sau:

```text
Video Stream (Webcam / RTSP / File)
      ↓
Frame Decoupling / Sampling (Đọc khung hình)
      ↓
Person Detection (YOLO) -> Tìm bounding box của người
      ↓
Person Tracking (ByteTrack) -> Gán và duy trì track_id qua các frame
      ↓
Line Crossing Detection -> Kiểm tra track di chuyển qua line ảo
      ↓ (Nếu đi qua line ảo - tạo ENTRY/EXIT event)
Face Detection & Alignment (SCRFD / FaceAnalysis) trong bounding box của người
      ↓
Face Embedding Extraction (InsightFace) -> Tạo vector đặc trưng 512-dim
      ↓
Known Matching (So sánh vector với Known templates - similarity >= known_threshold)
      ↓ (Nếu khớp: gán person_id. Nếu không khớp: chuyển sang bước sau)
Unknown Re-identification (So sánh vector với Unknown templates - similarity >= unknown_threshold)
      ↓ (Nếu khớp: gán unknown_id cũ. Nếu không khớp: tạo unknown_id mới)
Session Management -> Tạo mới hoặc đóng phiên ra/vào
      ↓
Database / WebSocket Realtime Event Update
```

## 2. Các cấu phần chính

### 2.1. Đọc và lấy mẫu khung hình (Frame Ingestion & Sampling)
- Sử dụng **OpenCV** hoặc **FFmpeg** để giải mã luồng video.
- Đối với video demo, tốc độ xử lý FPS cần đạt 10-15 FPS. Đối với production, tốc độ xử lý cần đạt 20-30 FPS.
- Áp dụng kỹ thuật frame-skipping (ví dụ chỉ lấy mẫu 1/2 hoặc 1/3 số frame đối với các tác vụ phụ như Face Detection nếu không có chuyển động mạnh) để giảm tải cho CPU/GPU.

### 2.2. Phát hiện người (Person Detection)
- Model đề xuất: **YOLO11n** hoặc **YOLOv8n** (bản nano để tối ưu hóa tốc độ).
- Chỉ lọc đối tượng có nhãn `person` (class index 0 trong bộ nhãn COCO).
- Ngưỡng tin cậy phát hiện người: mặc định `person_detection_confidence = 0.5`.

### 2.3. Theo dõi đối tượng (Person Tracking)
- Thuật toán đề xuất: **ByteTrack** hoặc **BoT-SORT**.
- Mục tiêu: Duy trì một `track_id` duy nhất cho một đối tượng di chuyển từ khi đi vào tầm nhìn của camera cho đến khi đi ra ngoài hoặc cắt qua line.
- Cơ chế xử lý mất dấu ngắn hạn (`track_lost_timeout_seconds`): Cố gắng giữ lại thông tin tracking của đối tượng trong vòng 2-5 giây nếu đối tượng bị che khuất tạm thời hoặc mất dấu do chất lượng ánh sáng.

### 2.4. Phát hiện cắt vạch ảo (Line Crossing Detection)
- Quản trị viên vẽ một đường thẳng ảo (Line) trên giao diện cấu hình camera.
- Xác định hướng: Vạch ảo chia khung hình thành 2 vùng (Inside và Outside).
- Thuật toán kiểm tra giao cắt giữa đoạn thẳng nối từ vị trí trước/sau của đối tượng tracking (trọng tâm bounding box hoặc điểm chân người) với vạch ảo.
  - Đi từ Outside → Inside: **ENTRY**.
  - Đi từ Inside → Outside: **EXIT**.
- Cơ chế Debounce: Mỗi khi đối tượng cắt vạch thành công, kích hoạt cơ chế khóa sự kiện (`line_crossing_debounce_seconds = 5s-10s`) cho `track_id` đó để tránh việc đối tượng đứng sát vạch dao động tạo nhiều sự kiện lặp lại.

### 2.5. Phát hiện, căn chỉnh và trích xuất đặc trưng khuôn mặt (Face Pipeline)
- Chỉ chạy face detection và extraction khi đối tượng di chuyển đến gần vùng vạch ảo hoặc khi bắt đầu nhận diện hướng đi để tối ưu hiệu năng.
- **SCRFD** (phần detect khuôn mặt tích hợp trong InsightFace): Phát hiện khuôn mặt và định vị 5 điểm mốc (landmarks - mắt, mũi, miệng).
- **Face Alignment**: Thực hiện phép biến đổi hình học (Affine Transformation) dựa trên 5 landmarks để căn chỉnh khuôn mặt về dạng thẳng đứng tiêu chuẩn.
- **InsightFace (Model ArcFace / ResNet)**: Trích xuất vector đặc trưng khuôn mặt 512 chiều (face embedding).

### 2.6. Khớp danh tính (Face Matching)
- Sử dụng phép so khớp **Cosine Similarity** giữa vector đặc trưng trích xuất được và các vector trong CSDL.
- **Ngưỡng so sánh**:
  - `known_recognition_threshold = 0.6` (giá trị đề xuất khởi đầu).
  - `unknown_recognition_threshold = 0.55` (giá trị đề xuất khởi đầu).
- Nếu không khớp người quen, tiến hành so khớp với CSDL người lạ hiện hoạt. Nếu vẫn không khớp, sinh mới một `unknown_id` và lưu embedding vào bảng `unknown_identities` kèm thời gian hết hạn (`expire_at`).
