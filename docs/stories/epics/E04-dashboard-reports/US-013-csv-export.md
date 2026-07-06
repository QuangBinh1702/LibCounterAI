# US-013 CSV Export and Date-Filtered Sessions

## Status

implemented

## Lane

normal

## Product Contract

Cho phép người dùng xuất dữ liệu phiên truy cập ra file CSV từ giao diện Web Dashboard và hỗ trợ lọc phiên theo ngày cụ thể.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Tạo hàm `exportToCSV` trên Frontend cho phép xuất toàn bộ danh sách sessions hiện tại ra file CSV với BOM UTF-8.
- [x] File CSV bao gồm các cột: Session ID, Person Name, Member Code, Identity Type, Entry Time, Exit Time, Duration (s), Status.
- [x] Thêm input `type="date"` và nút "Filter" vào tab Visit Sessions cho phép lọc phiên theo ngày.
- [x] Nâng cấp API `GET /api/sessions` hỗ trợ tham số query `?date=YYYY-MM-DD` để lọc sessions theo ngày.
- [x] Thêm trường `identity_type` vào response của API `/api/sessions`.
- [x] Viết script kiểm định `scripts/validate_dashboard_reports.py`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Script `validate_dashboard_reports.py` kiểm tra date filter API |
| E2E | N/A |
| Platform | Chạy thành công trên Windows |

## Harness Delta

- Không có.

## Evidence

- Story US-013 verification: pass
