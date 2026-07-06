# US-012 Unknown Session API & UI Sync

## Status

implemented

## Lane

normal

## Product Contract

Đồng bộ các API thống kê và lịch sử phiên truy cập để đưa thông tin của người lạ (Unknown Visitors) lên giao diện Web Dashboard. Đảm bảo hiển thị đúng mã định danh ẩn danh dạng `UNKNOWN_YYYYMMDD_XXXX` thay vì hiển thị trống hoặc bị lỗi phân tách thông tin.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-model.md`
- `docs/product/dashboard-and-reports.md`

## Acceptance Criteria

- [x] Nâng cấp API `GET /api/sessions`:
  - Lấy cả danh sách các phiên của người quen và người lạ.
  - Đối với phiên của người lạ: trả về `person_name = anonymous_code` (ví dụ: `UNKNOWN_20260706_0001`), `member_code = None`.
- [x] Nâng cấp API `GET /api/stats/occupancy`:
  - Tính toán số người hiện tại trong thư viện bằng cách đếm tất cả các active sessions (của cả người quen lẫn người lạ).
  * Tính tổng số lượt vào/ra trong ngày bao gồm cả sự kiện của người lạ.
- [x] Nâng cấp API `GET /api/stats/hourly`:
  - Phân bổ số lượt ra/vào theo giờ bao gồm tất cả các đối tượng (KNOWN và UNKNOWN).
- [x] Đảm bảo giao diện Web Dashboard (tab **Visit Sessions**, **Analytics & Reports**) hiển thị chính xác tên người lạ ẩn danh và phân bổ biểu đồ thống kê lưu lượng.

## Design Notes

- Sử dụng các câu truy vấn Outer Join trong SQLAlchemy để lấy được thông tin liên kết của bảng `persons` (khi `identity_type = 'KNOWN'`) hoặc bảng `unknown_identities` (khi `identity_type = 'UNKNOWN'`).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Xác thực API trả về đúng dữ liệu thông qua script validate_api_extras.py nâng cấp |
| E2E | Kiểm tra giao diện hiển thị người lạ ẩn danh trên trình duyệt |
| Platform | Chạy thành công trên Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định thành công và giao diện hiển thị chính xác.
