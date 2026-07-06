# US-014 Enhanced Analytics with Known/Unknown Breakdown

## Status

implemented

## Lane

normal

## Product Contract

Mở rộng API thống kê và giao diện Analytics Dashboard để phân tách số liệu theo loại đối tượng (Known vs Unknown), hiển thị tổng số phiên truy cập, giúp quản trị viên có cái nhìn chi tiết hơn về cấu phần lưu lượng thư viện.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Nâng cấp API `GET /api/stats/occupancy` trả thêm các trường:
  - `known_visitors_today`: Số lượt vào của người quen hôm nay.
  - `unknown_visitors_today`: Số lượt vào của người lạ hôm nay.
  - `total_sessions_today`: Tổng số phiên truy cập hôm nay.
- [x] Cập nhật `OccupancyStats` interface trên Frontend để nhận các trường mới.
- [x] Thêm 3 thẻ thống kê mới trên tab Analytics: Known Visitors, Unknown Visitors, Total Sessions.
- [x] Viết script kiểm định `scripts/validate_dashboard_reports.py`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Script `validate_dashboard_reports.py` kiểm tra breakdown API |
| E2E | N/A |
| Platform | Chạy thành công trên Windows |

## Harness Delta

- Không có.

## Evidence

- Story US-014 verification: pass
