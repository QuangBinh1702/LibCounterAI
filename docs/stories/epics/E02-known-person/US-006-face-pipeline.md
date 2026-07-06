# US-006 Face Detection and Embedding Extraction Pipeline

## Status

implemented

## Lane

normal

## Product Contract

Tích hợp mô hình ONNX phát hiện khuôn mặt (YuNet) và trích xuất vector đặc trưng khuôn mặt (SFace) từ OpenCV Model Zoo để phục vụ việc nhận diện danh tính người dùng trong bounding box của người được tracking.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`

## Acceptance Criteria

- [x] Cấu hình tải tự động các mô hình `face_detection_yunet_2023mar.onnx` và `face_recognition_sface_2021dec.onnx` trong file `app/download_models.py`.
- [x] Tạo lớp `FacePipeline` trong `app/face_pipeline.py` sử dụng các API `cv2.FaceDetectorYN` và `cv2.FaceRecognizerSF` của OpenCV.
- [x] Hỗ trợ phát hiện khuôn mặt và định vị 5 điểm mốc (landmarks - mắt, mũi, miệng).
- [x] Thực hiện căn chỉnh khuôn mặt (alignment) và trích xuất vector đặc trưng 128 chiều (SFace embedding).
- [x] Cập nhật định nghĩa CSDL trong `app/models.py` và `scripts/validate_database.py` thành `VectorType(128)` tương thích với SFace.
- [x] Viết script kiểm định `scripts/validate_face_pipeline.py` dùng fixture ảnh mẫu cục bộ và chạy trích xuất embedding thành công.

## Design Notes

- **YuNet & SFace**:
  - YuNet là bộ phát hiện khuôn mặt siêu nhẹ (~100KB) chạy cực nhanh trên CPU.
  - SFace là bộ nhận diện khuôn mặt trích xuất vector 128 chiều.
  - Cả hai mô hình đều được hỗ trợ trực tiếp bởi các C++ API tối ưu của OpenCV, giúp viết mã Python cực kỳ ngắn gọn và ổn định mà không cần cài thêm InsightFace hay PyTorch.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Chạy trích xuất đặc trưng thành công trên ảnh mẫu Lena với 128-d output |
| Integration | Script `validate_face_pipeline.py` chạy qua Harness trả về `verify: pass` |
| E2E | N/A |
| Platform | Chạy thành công trên Windows qua CPU execution |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-006` thành công:
  ```text
  Running: python scripts/validate_face_pipeline.py
  Starting face pipeline validation tests...
  FacePipeline initialized successfully (models loaded).
  Copied face test fixture to D:\taggo\LibCounterAI\lena.jpg
  Loaded test image: shape=(512, 512, 3)
  Detected 1 face(s).
  Face bbox: [207, 182, 145, 206]
  Face landmarks: [[271, 269], [328, 276], [309, 312], [270, 342], [311, 348]]
  Face detection confidence score: 0.9090
  Extracting embedding vector...
  Extracted embedding: type=<class 'list'>, length=128
  All FacePipeline validation tests PASSED successfully!
  Test face image lena.jpg cleaned up successfully.
  Story US-006 verification: pass
  ```

- 2026-07-06: `scripts/validate_face_pipeline.py` now uses
  `tests/fixtures/lena.jpg` through `scripts/validation_assets.py`, so the
  verification no longer requires internet access at runtime.
