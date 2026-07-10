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

## Reporting Contract

- Báo cáo ngày và biểu đồ theo giờ dùng múi giờ Việt Nam (`UTC+7`), sau đó
  chuyển về UTC khi tạo boundary truy vấn database.
- `GET /api/stats/hourly` đếm các event `ENTRY` và `EXIT` theo giờ địa phương
  Việt Nam, không dùng trực tiếp giờ UTC lưu trong database.
- Analytics hiển thị `current_occupancy` riêng với tổng lượt vào/ra. Biểu đồ
  lưu lượng chỉ giữ hai tổng chính là **Tổng vào** và **Tổng ra**; không hiển
  thị chỉ số “Chênh lệch” vì đây không phải là số session đang active.

## Acceptance Criteria

- [x] Nâng cấp API `GET /api/stats/occupancy` trả thêm các trường:
  - `known_visitors_today`: Số lượt vào của người quen hôm nay.
  - `unknown_visitors_today`: Số lượt vào của người lạ hôm nay.
  - `total_sessions_today`: Tổng số phiên truy cập hôm nay.
- [x] Cập nhật `OccupancyStats` interface trên Frontend để nhận các trường mới.
- [x] Thêm 3 thẻ thống kê mới trên tab Analytics: Known Visitors, Unknown Visitors, Total Sessions.
- [x] Hiển thị giờ cao điểm và tổng lượt vào/ra theo khoảng ngày đang chọn.
- [x] Giữ số người đang ở trong thư viện (`current_occupancy`) là chỉ số trạng thái riêng, không trộn vào biểu đồ lưu lượng.
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
- Timezone smoke proof: `04:23 UTC` được quy đổi thành `11:23` giờ Việt Nam;
  ngày `2026-07-10` tạo query window UTC-naive `[2026-07-09 17:00, 2026-07-10 17:00)`.
