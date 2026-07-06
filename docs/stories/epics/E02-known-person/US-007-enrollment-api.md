# US-007 Known Person Registration (Enrollment) API

## Status

implemented

## Lane

normal

## Product Contract

Xây dựng endpoint API `/api/persons/register` cho phép đăng ký người quen mới bằng cách tải lên hình ảnh chân dung khuôn mặt đơn lẻ, trích xuất đặc trưng khuôn mặt (128-d vector) qua `FacePipeline` và lưu trữ cả thông tin đối tượng lẫn face template vào cơ sở dữ liệu.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`
- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Định nghĩa API endpoint `/api/persons/register` (POST) nhận dữ liệu dạng form (`full_name`, `member_code`, `role`, `status`) và tệp tin ảnh khuôn mặt (`file`).
- [x] Thực hiện các kiểm tra nghiệp vụ (validation):
  - Kiểm tra trùng lặp `member_code` trong CSDL và báo lỗi 400.
  - Giải mã ảnh gửi lên và phát hiện khuôn mặt qua `FacePipeline`.
  - Nếu không phát hiện khuôn mặt: trả về lỗi 400 ("No face detected in the uploaded photo").
  - Nếu phát hiện nhiều hơn 1 khuôn mặt: trả về lỗi 400 ("Multiple faces detected in the uploaded photo. Please upload a portrait with exactly one face").
- [x] Trích xuất embedding vector 128 chiều từ khuôn mặt và lưu đối tượng `Person` kèm `FaceTemplate` liên kết vào CSDL.
- [x] Trả về mã phản hồi `201 Created` kèm thông tin chi tiết của người dùng đã đăng ký thành công (bao gồm cả database ID).
- [x] Viết script kiểm định `scripts/validate_enrollment.py` giả lập đăng ký với ảnh Lena mẫu, kiểm tra trùng lặp mã thành viên, kiểm tra trường hợp lỗi ảnh trống không có mặt, và kiểm chứng các bản ghi đã được lưu đúng trong DB.

## Design Notes

- **Database Session in API**:
  - Sử dụng dependency `get_db` để quản lý SQLAlchemy session an toàn trong endpoint FastAPI.
  - Sử dụng transaction rollback tự động khi phát sinh ngoại lệ để tránh lưu trữ dữ liệu rác/không đầy đủ (ví dụ: tạo Person nhưng tạo FaceTemplate thất bại).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Script `validate_enrollment.py` mô phỏng đầy đủ các kịch bản lỗi và đăng ký thành công qua API |
| E2E | N/A |
| Platform | Chạy thành công trên môi trường Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-007` thành công:
  ```text
  Running: python scripts/validate_enrollment.py
  Starting enrollment validation tests...
  Downloading test face image...
  YOLOv8 ONNX Detector loaded successfully.
  FacePipeline ONNX Models loaded successfully.

  --- Testing Successful Registration ---
  Status code: 201
  Response: {'id': 1, 'full_name': 'Nguyen Van A', 'member_code': 'SV999999', 'role': 'STUDENT', 'status': 'ACTIVE', 'face_template': {'id': 1, 'model_name': 'sface', 'quality_score': 0.9089785814285278}}

  --- Testing Duplicate Registration ---
  Status code: 400
  Response: {'detail': 'Member code SV999999 is already registered.'}

  --- Testing Registration with No Face ---
  Status code: 400
  Response: {'detail': 'No face detected in the uploaded photo.'}

  All enrollment validation tests PASSED successfully!
  Cleaning up database records for member_code: SV999999
  Story US-007 verification: pass
  ```

