# US-011 Unknown Visit Session Tracking

## Status

implemented

## Lane

normal

## Product Contract

Khi người lạ (UNKNOWN) di chuyển cắt qua line ảo:
* Nếu hướng di chuyển là `ENTRY` (đi vào): Khởi tạo một phiên truy cập mới (`VisitSession`) trong cơ sở dữ liệu với trạng thái `ACTIVE`, loại `identity_type = 'UNKNOWN'`, trường `unknown_id` liên kết đến bản ghi định danh ẩn danh tương ứng.
* Nếu hướng di chuyển là `EXIT` (đi ra): Tìm kiếm phiên truy cập `ACTIVE` của người lạ đó, cập nhật thời gian ra `exit_at`, tính toán thời lượng lưu lại `duration_seconds` và chuyển trạng thái phiên thành `CLOSED`.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Sửa đổi logic ghi nhận sự kiện crossing trong `/api/process-frame`:
  - Khi có sự kiện `ENTRY` của một track được định danh là người lạ (`unknown_id` không rỗng):
    - Kiểm tra xem đã có phiên truy cập `ACTIVE` nào của `unknown_id` này chưa.
    - Nếu chưa, tạo mới một `VisitSession` lưu `unknown_id`, `entry_at`, `status = 'ACTIVE'`.
  - Khi có sự kiện `EXIT` của track người lạ:
    - Tìm phiên truy cập `ACTIVE` gần nhất của `unknown_id` này.
    - Cập nhật phiên: `exit_at` = hiện tại, `status = 'CLOSED'`, `duration_seconds` = exit_at - entry_at.
- [x] Đảm bảo logic xử lý an toàn và không gây trùng lặp phiên khi có sự kiện nhiễu (áp dụng cơ chế debounce).
- [x] Tích hợp kiểm thử tích hợp trong script `scripts/validate_unknown_reid.py`.

## Design Notes

- Tương tự như đối với người quen, trường hợp người lạ đi ra khỏi thư viện mà không tìm thấy phiên vào `ACTIVE` trước đó, hệ thống sẽ bỏ qua hoặc log lại để tránh phát sinh ngoại lệ gây gián đoạn luồng xử lý chính.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Xác minh tạo phiên ACTIVE khi vào và CLOSED khi ra thông qua script kiểm thử |
| E2E | N/A |
| Platform | Chạy thành công trên Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định tích hợp thành công.
