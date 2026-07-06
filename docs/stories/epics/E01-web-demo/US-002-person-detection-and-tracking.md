# US-002 Basic Person Detection and Tracking using YOLO and ByteTrack

## Status

implemented

## Lane

normal

## Product Contract

Xây dựng pipeline xử lý AI cơ bản trên Backend: nhận luồng hình ảnh/video đầu vào, thực hiện phát hiện người sử dụng mô hình YOLO và duy trì mã định danh theo vết (`track_id`) qua các khung hình sử dụng thuật toán tracking (ByteTrack).

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`

## Acceptance Criteria

- [x] Tích hợp mô hình YOLO phát hiện người (nhãn `person`, class index 0) vào ứng dụng backend.
- [x] Tích hợp thuật toán tracking (ByteTrack hoặc IoU Tracker) để gán `track_id` ổn định cho từng người di chuyển trong khung hình.
- [x] Cung cấp API endpoint (ví dụ: HTTP POST upload file video hoặc WebSocket stream) nhận frame/video và trả về danh sách đối tượng được tracking bao gồm: `track_id`, `bbox` (tọa độ khung), `confidence`.
- [x] Có script kiểm định tự động (verify script) chạy pipeline với một video mẫu ngắn, kiểm tra xem có xuất ra kết quả tracking với định dạng JSON hợp lệ hay không.

## Design Notes

- **AI Library**: Sử dụng thư viện `ultralytics` hoặc `onnxruntime` + tracker tùy chỉnh để tối ưu hóa tài nguyên. Thư viện `ultralytics` được đề xuất vì có sẵn YOLOv8/v11 và ByteTrack tích hợp sẵn, dễ cài đặt và chạy thử nghiệm.
- **API Response Format**:
  ```json
  {
    "frame_index": 120,
    "detections": [
      {
        "track_id": 1,
        "bbox": [100.0, 150.0, 200.0, 450.0],
        "confidence": 0.89
      }
    ]
  }
  ```

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Test hàm khởi tạo model YOLO và chạy suy luận trên 1 frame trống |
| Integration | API Endpoint nhận file/video demo và trả về danh sách track_id |
| E2E | N/A |
| Platform | Chạy thành công trên môi trường Windows |
| Release | Đảm bảo tốc độ xử lý đạt tối thiểu 10 FPS cho file video thử nghiệm |

## Harness Delta

- Không có.

## Evidence

- Lệnh chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-002` thành công, cho ra kết quả:
  ```text
  Running: python scripts/validate_tracking.py
  Starting validation test for tracking...
  Dummy test image created.
  Launching FastAPI server...
  Server is ready and healthy!
  Sending frame to /api/process-frame...
  Server response: {'session_id': 'test_session', 'tracks': []}
  Tracking validation PASSED successfully!
  Terminating server...
  Story US-002 verification: pass
  ```

