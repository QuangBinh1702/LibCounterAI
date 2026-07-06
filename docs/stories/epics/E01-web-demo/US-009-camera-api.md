# US-009 RTSP Camera Connection and Testing API

## Status

implemented

## Lane

normal

## Product Contract

Xây dựng bộ API quản lý camera (`/api/cameras`) hỗ trợ thêm mới, truy vấn thông tin và kiểm tra kết nối (connection testing) của các nguồn video đầu vào (RTSP stream, file video, camera tích hợp) sử dụng OpenCV nhằm đáp ứng tiêu chí US-02.

## Relevant Product Docs

- `SPEC.md`
- `docs/product/overview.md`

## Acceptance Criteria

- [x] Tạo endpoint `POST /api/cameras` hỗ trợ đăng ký camera:
  - Nếu nguồn là `RTSP`: Thử kết nối bằng OpenCV `cv2.VideoCapture`. Nếu không mở được, trả về lỗi HTTP 400 Bad Request kèm thông tin lỗi kết nối.
  - Nếu nguồn là `FILE`: Kiểm tra sự tồn tại của file video trên local server. Trả về lỗi 400 nếu file không tồn tại.
  - Nếu nguồn là `WEBCAM`: Khởi tạo kiểm tra chỉ số camera.
- [x] Tạo endpoint `POST /api/cameras/{camera_id}/test` hỗ trợ kiểm tra nhanh kết nối camera, cập nhật trạng thái `ONLINE`/`OFFLINE` và ghi nhận mốc thời gian hoạt động cuối cùng `last_online_at`.
- [x] Viết và tích hợp script chạy kiểm định tự động `scripts/validate_camera_api.py`.

## Design Notes

- Sử dụng `cv2.VideoCapture` để bắt luồng RTSP thời gian thực trong thời gian ngắn và giải phóng ngay lập tức (`cap.release()`) để tránh chiếm dụng tài nguyên kết nối của IP camera.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Script `validate_camera_api.py` chạy qua các kịch bản kết nối hợp lệ/không hợp lệ |
| E2E | N/A |
| Platform | Chạy thành công trên môi trường Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-009` thành công:
  ```text
  Running: python scripts/validate_camera_api.py
  Starting validation of Camera Management and Connection Testing APIs...
  YOLOv8 ONNX Detector loaded successfully.
  FacePipeline ONNX Models loaded successfully.

  --- A. Registering camera with invalid RTSP ---
  Response status: 400
  Response body: {'detail': 'Failed to connect to RTSP stream: rtsp://invalid_address:8554/live'}

  --- B. Registering camera with invalid FILE path ---

  --- C. Registering camera with WEBCAM index ---
  Registered camera index successfully. Camera ID: 2

  --- D. Testing camera connection (ID: 2) ---
  Test connection result: {'status': 'OFFLINE'}

  All camera registration and connection validation tests PASSED!
  Cleaned up camera: RTSP Test Camera
  Story US-009 verification: pass
  ```
