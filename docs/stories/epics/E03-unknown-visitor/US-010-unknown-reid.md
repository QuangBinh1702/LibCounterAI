# US-010 Unknown Re-identification & Storage

## Status

implemented

## Lane

normal

## Product Contract

Khi phát hiện một khuôn mặt không trùng khớp với bất kỳ người quen (KNOWN) nào trong cơ sở dữ liệu (tức là cosine similarity < 0.6), hệ thống sẽ đối chiếu vector embedding đó với danh sách các định danh người lạ ẩn danh còn hiệu lực trong bảng `unknown_identities` (expire_at > datetime.utcnow()).
* Nếu độ tương đồng cosine similarity >= 0.55 (unknown_threshold): Tái định danh đối tượng bằng `anonymous_code` cũ, tăng `visit_count` và cập nhật `last_seen_at`.
* Nếu không khớp: Tạo một định danh `UnknownIdentity` mới với mã định dạng `UNKNOWN_YYYYMMDD_XXXX` (ví dụ: `UNKNOWN_20260706_0001`), lưu embedding vector và thiết lập thời gian hết hạn là 24 giờ kể từ thời điểm hiện tại.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Sửa đổi logic so khớp khuôn mặt trong endpoint `/api/process-frame` khi không khớp KNOWN template:
  - Truy vấn danh sách `unknown_identities` còn hoạt động (`status = 'ACTIVE'` và `expire_at > datetime.utcnow()`).
  - So sánh vector đặc trưng (128-d) của khuôn mặt hiện tại với embedding của các unknown visitors đó.
  - Tìm ra ứng viên có similarity cao nhất và >= 0.55.
- [x] Nếu tìm thấy ứng viên trùng khớp:
  - Cập nhật trường `last_seen_at` bằng thời gian hiện tại và tăng `visit_count` lên 1.
  - Sử dụng `anonymous_code` của ứng viên đó làm tên định danh của track.
- [x] Nếu không tìm thấy ứng viên trùng khớp:
  - Sinh mã `anonymous_code` theo quy tắc định dạng `UNKNOWN_YYYYMMDD_XXXX` (truy vấn đếm số lượng người lạ được tạo trong ngày hiện tại để tăng số thứ tự XXXX bắt đầu từ 0001).
  - Tạo mới bản ghi `UnknownIdentity` trong CSDL với `expire_at` = hiện tại + 24 giờ.
  - Sử dụng mã định danh mới này làm tên định danh của track.
- [x] Ghi nhận `unknown_id` liên kết vào sự kiện `Event` trong CSDL khi người lạ đi qua vạch ảo.
- [x] Viết script kiểm định `scripts/validate_unknown_reid.py` để xác thực toàn bộ luồng.

## Design Notes

- Sử dụng cơ chế khóa/Mutex hoặc truy vấn nguyên tử (Atomic query) của SQLAlchemy khi sinh số thứ tự `XXXX` trong ngày để tránh xung đột trùng lặp mã khi có nhiều luồng cùng ghi nhận người lạ đồng thời.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Chạy script `validate_unknown_reid.py` kiểm tra sinh mã mới và tái định danh khi gặp lại vector cũ |
| E2E | N/A |
| Platform | Chạy thành công trên Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định bằng script tự động thành công.
