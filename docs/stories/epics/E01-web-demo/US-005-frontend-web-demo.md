# US-005 Interactive Web UI for Real-time Detection and Counting

## Status

implemented

## Lane

normal

## Product Contract

Xây dựng giao diện Web Dashboard (React + TypeScript) cho phép người dùng kết nối webcam hoặc tải lên video mẫu, vẽ cấu hình đường vạch ảo ảo (virtual line) trực tiếp trên khung hình và gửi các frame liên tục đến API backend để hiển thị kết quả tracking cùng số lượt vào/ra theo thời gian thực.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`
- `docs/product/dashboard-and-reports.md`

## Acceptance Criteria

- [x] Giao diện Web Dashboard thiết kế hiện đại (Premium Dark Mode) sử dụng React + TypeScript trong thư mục `surfaces/browser/`.
- [x] Cho phép kết nối Webcam của trình duyệt hoặc tải lên tệp tin video để chạy thử nghiệm.
- [x] Hỗ trợ cấu hình vạch ảo bằng cách nhấp chuột/kéo thả trực tiếp trên màn hình video (canvas overlay).
- [x] Tự động trích xuất frame từ video (ví dụ: 5-10 FPS) và gửi qua API `/api/process-frame` kèm theo tọa độ vạch ảo.
- [x] Hiển thị trực quan bounding box của người, số hiệu tracking ID, và vạch ảo trên màn hình phát.
- [x] Hiển thị bảng thống kê lượt người vào (ENTRY) và người ra (EXIT) kèm biểu tượng và hiệu ứng chuyển đổi trạng thái sinh động.
- [x] Ứng dụng biên dịch thành công không có lỗi TypeScript hay Oxlint.

## Design Notes

- **Real-time pipeline inside browser**:
  - Trình duyệt đọc luồng video từ webcam qua `navigator.mediaDevices.getUserMedia`.
  - Sử dụng thẻ `<video>` ẩn và vẽ nội dung lên `<canvas>` để chụp frame dưới dạng JPEG blob.
  - Sử dụng hàm `fetch` gửi multipart/form-data đến endpoint `/api/process-frame` của backend FastAPI.
  - Nhận phản hồi vẽ lại các bounding box và cập nhật bộ đếm lượt vào/ra.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Build dự án Vite React thành công (`npm run build` không có lỗi) |
| E2E | Chạy server cục bộ, tương tác vẽ vạch ảo và đếm lượt mô phỏng thành công |
| Platform | Hoạt động mượt mà trên Chrome/Edge trên Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-005` thành công:
  ```text
  Running: npm --prefix surfaces/browser run build

  > surfaces-browser@0.0.0 build
  > tsc -b && vite build

  vite v8.1.3 building client environment for production...
  transforming...✓ 17 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                   0.47 kB │ gzip:  0.31 kB
  dist/assets/index-D2MvzH8I.css    8.24 kB │ gzip:  2.39 kB
  dist/assets/index-Cs6oivB7.js   204.67 kB │ gzip: 64.39 kB

  ✓ built in 139ms
  Story US-005 verification: pass
  ```

