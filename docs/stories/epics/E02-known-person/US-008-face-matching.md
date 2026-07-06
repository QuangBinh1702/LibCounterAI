# US-008 Real-time Face Matching and Event Logging

## Status

implemented

## Lane

normal

## Product Contract

Tích hợp chức năng so khớp khuôn mặt thời gian thực vào luồng xử lý frame. Với mỗi person track được phát hiện, trích xuất khuôn mặt, so sánh embedding vector 128-d qua Cosine Similarity để định danh danh tính. Khi có sự kiện cắt qua vạch ảo (Line Crossing), ghi nhận sự kiện (Event) kèm thông tin định danh và khởi tạo/cập nhật phiên truy cập (VisitSession) trong CSDL SQLite.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`
- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Tích hợp bộ so khớp khuôn mặt thời gian thực trong endpoint `/api/process-frame`:
  - Cắt vùng ảnh người (`person_crop`) từ frame theo bounding box của track.
  - Sử dụng `FacePipeline` để phát hiện khuôn mặt và trích xuất vector embedding 128-d.
  - So sánh Cosine Similarity với tất cả các templates đã lưu trong bảng `face_templates`.
  - Nếu độ tương đồng cao nhất $\ge$ 0.6, gán danh tính là `KNOWN` kèm tên người dùng; ngược lại gán là `UNKNOWN`.
- [x] Áp dụng kỹ thuật tối ưu **Identity Caching per Track ID**:
  - Khi một `track_id` đã được định danh thành công (KNOWN), cache lại danh tính này trong `IoUTracker` để bỏ qua việc chạy face detection/extraction ở các frame tiếp theo của cùng một đối tượng, giúp duy trì FPS cao.
  - Giải phóng bộ nhớ cache khi track hết hiệu lực (lost).
- [x] Tích hợp ghi nhận cơ sở dữ liệu khi có sự kiện Line Crossing:
  - Lưu bản ghi `Event` với loại sự kiện (ENTRY/EXIT) và danh tính người đi qua (KNOWN/UNKNOWN).
  - Quản lý vòng đời `VisitSession`:
    - Khi có sự kiện `ENTRY` của người quen: Tạo phiên truy cập mới có trạng thái `ACTIVE`.
    - Khi có sự kiện `EXIT` của người quen: Tìm phiên truy cập `ACTIVE` tương ứng, cập nhật thời điểm ra, tính toán `duration_seconds`, và chuyển trạng thái sang `CLOSED`.
- [x] Viết script kiểm định `scripts/validate_matching.py` giả lập đăng ký người quen, gửi liên tiếp các frame mô phỏng di chuyển cắt qua vạch ảo, kiểm tra độ tương đồng Cosine Similarity, và kiểm chứng các bảng ghi `Event` và `VisitSession` được ghi nhận chính xác trong CSDL.

## Design Notes

- **Cosine Similarity Calculation**:
  - Tính toán độ tương đồng Cosine bằng công thức chuẩn: $S_c(A, B) = \frac{A \cdot B}{\|A\|\|B\|}$ để đảm bảo độ chính xác ngay cả khi vector chưa được chuẩn hóa đơn vị.
- **Visit Session State Management**:
  - Phiên truy cập được đóng lại khi người dùng đi ra ngoài (sự kiện `EXIT`), đồng thời tự động cập nhật tổng thời gian lưu lại.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Script `validate_matching.py` chạy qua chuỗi frame mô phỏng và xác minh DB |
| E2E | N/A |
| Platform | Chạy thành công trên môi trường Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-008` thành công:
  ```text
  Running: python scripts/validate_matching.py
  Starting face matching and identification validation tests...
  Copied face test fixture to D:\taggo\LibCounterAI\lena_matching.jpg
  YOLOv8 ONNX Detector loaded successfully.
  FacePipeline ONNX Models loaded successfully.

  --- A. Enrolling Test Person ---
  Test person enrolled successfully.

  --- B. Processing Frame 1 (Face Detection and Matching) ---
  [API] Processing frame: detections=[[0, 0, 512, 400, 0.95]], line_config=[[0, 450], [512, 450]]
  [API] Frame processed: tracks=[{'track_id': 1, 'bbox': [0.0, 0.0, 512.0, 400.0], 'confidence': 0.95, 'person_id': 1, 'person_name': 'Nguyen Van A', 'identity_type': 'KNOWN', 'similarity_score': 0.9694865942001343}], crossing_events=[]
  Frame 1 status: 200
  Frame 1 response: {'session_id': 'session_match_test', 'tracks': [{'track_id': 1, 'bbox': [0.0, 0.0, 512.0, 400.0], 'confidence': 0.95, 'person_id': 1, 'person_name': 'Nguyen Van A', 'identity_type': 'KNOWN', 'similarity_score': 0.9694865942001343}], 'crossing_events': []}

  --- C. Processing Frame 2 (Line Crossing Event Log) ---
  [API] Processing frame: detections=[[0, 0, 512, 480, 0.95]], line_config=[[0, 450], [512, 450]]
  [DB Log] Event logged: ENTRY for track 1 (KNOWN)
  [API] Frame processed: tracks=[{'track_id': 1, 'bbox': [0.0, 0.0, 512.0, 480.0], 'confidence': 0.95, 'person_id': 1, 'person_name': 'Nguyen Van A', 'identity_type': 'KNOWN', 'similarity_score': 0.9694865942001343}], crossing_events=[{'track_id': 1, 'direction': 'ENTRY', 'timestamp': 1783329101.4023654}]
  Frame 2 status: 200
  Frame 2 response: {'session_id': 'session_match_test', 'tracks': [{'track_id': 1, 'bbox': [0.0, 0.0, 512.0, 480.0], 'confidence': 0.95, 'person_id': 1, 'person_name': 'Nguyen Van A', 'identity_type': 'KNOWN', 'similarity_score': 0.9694865942001343}], 'crossing_events': [{'track_id': 1, 'direction': 'ENTRY', 'timestamp': 1783329101.4023654}]}

  --- D. Verifying Database Event Logging ---
  Verified: Event logged successfully in database.
  Verified: VisitSession initialized successfully in database.

  --- E. Processing Frame 3 (Simulate EXIT and Close Session) ---
  [API] Processing frame: detections=[[0, 0, 512, 400, 0.95]], line_config=[[0, 450], [512, 450]]
  [DB Log] Event logged: EXIT for track 1 (KNOWN)
  [API] Frame processed: tracks=[{'track_id': 1, 'bbox': [0.0, 0.0, 512.0, 400.0], 'confidence': 0.95, 'person_id': 1, 'person_name': 'Nguyen Van A', 'identity_type': 'KNOWN', 'similarity_score': 0.9694865942001343}], crossing_events=[{'track_id': 1, 'direction': 'EXIT', 'timestamp': 1783329101.4191396}]
  Frame 3 status: 200
  Frame 3 response: {'session_id': 'session_match_test', 'tracks': [{'track_id': 1, 'bbox': [0.0, 0.0, 512.0, 400.0], 'confidence': 0.95, 'person_id': 1, 'person_name': 'Nguyen Van A', 'identity_type': 'KNOWN', 'similarity_score': 0.9694865942001343}], 'crossing_events': [{'track_id': 1, 'direction': 'EXIT', 'timestamp': 1783329101.4191396}]}
  Verified: VisitSession closed successfully in database (duration=0s).

  All face matching and identification validation tests PASSED successfully!
  Cleaning up database records for member_code: SV777777
  Story US-008 verification: pass
  ```

- 2026-07-06: `scripts/validate_matching.py` now uses
  `tests/fixtures/lena.jpg` through `scripts/validation_assets.py`, so the
  verification no longer requires internet access at runtime.
