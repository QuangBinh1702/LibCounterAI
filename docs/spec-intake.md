# Spec Intake - LibCounterAI

Date: 2026-07-06

## Source

- User prompt: "Bắt đầu với AGENTS.md hãy đọc bản SPEC.md trước khi chúng ta bắt đầu làm bất cứ một việc gì, mình muốn bạn hãy hiểu codebase hiện tại..."
- Attached file: `SPEC.md` (Hệ thống nhận diện và đếm phiên người ra/vào thư viện bằng camera)

## Project Summary

Dự án LibCounterAI nhằm mục đích xây dựng một hệ thống giám sát, nhận diện khuôn mặt và thống kê người ra/vào thư viện theo thời gian thực. Hệ thống sử dụng một server AI tập trung để xử lý toàn bộ các tác vụ nặng (phát hiện người, tracking, nhận diện khuôn mặt và trích xuất embedding) từ luồng video của camera (Webcam, RTSP stream). Hệ thống phân biệt rõ ràng người quen (đã đăng ký trong hệ thống) và người lạ (unknown_id ẩn danh), theo dõi và quản lý các phiên (sessions) ra/vào của họ trong ngày mà không lưu trữ hình ảnh gốc mặc định nhằm bảo vệ quyền riêng tư sinh trắc học.

## Candidate Product Docs

Dưới đây là các tài liệu sẽ được tạo lập trong `docs/product/` để định nghĩa rõ ràng hợp đồng sản phẩm:

| File | Purpose | Source sections |
| --- | --- | --- |
| `docs/product/overview.md` | Giới thiệu hệ thống, mục tiêu, actors và phạm vi MVP/production | Mục 1, 2, 3, 5, 7, 21 |
| `docs/product/ai-pipeline.md` | Thiết kế pipeline AI (YOLO, ByteTrack, InsightFace, Line Crossing, Embedding matching) | Mục 10, 11, 16, 17, 18 |
| `docs/product/data-model.md` | Lược đồ CSDL PostgreSQL + pgvector + Redis, định nghĩa các bảng và cấu trúc quan hệ | Mục 12, 20, 22 |
| `docs/product/api-conventions.md` | Hợp đồng API RESTful và WebSocket kết nối frontend/backend | Mục 13, 22 |
| `docs/product/dashboard-and-reports.md` | Giao diện vận hành, cấu hình camera, xem báo cáo, lịch sử và phân quyền admin/staff | Mục 8, 9, 23 |

## Candidate Epics

| Epic | Description | Status |
| --- | --- | --- |
| E01 | Web Demo: Person detection, tracking và Line crossing (Phase 1) | planned |
| E02 | Known Person: Đăng ký (enrollment) và nhận diện người quen (Phase 2) | planned |
| E03 | Unknown Visitor: Tái định danh người lạ và quản lý visit sessions (Phase 3) | planned |
| E04 | Live Dashboard & Reports: WebSocket realtime và xuất báo cáo CSV/Excel (Phase 4) | planned |
| E05 | Multi-gate Scaling: Hỗ trợ đa camera, vào cổng A ra cổng B (Phase 5) | planned |
| E06 | Production Stream: Đọc luồng RTSP từ camera thực và cơ chế phục hồi lỗi (Phase 6) | planned |
| E07 | Hardening & Audit: Tối ưu hiệu năng, bảo mật sinh trắc học và audit logs (Phase 7) | planned |

## Architecture Questions

- **Runtime stack**: Python FastAPI cho backend API; React/Vite cho frontend dashboard; OpenCV & ONNX Runtime/PyTorch cho AI Processing.
- **Product surfaces**: Web Dashboard phục vụ Admin/Staff, HTTP REST API, WebSocket realtime stream.
- **Storage**: PostgreSQL cho dữ liệu quan hệ, pgvector cho lưu trữ và tìm kiếm vector khuôn mặt, Redis cho cache active sessions & trạng thái camera.
- **External providers**: Camera giám sát qua luồng RTSP/ONVIF.
- **Deployment target**: Docker & Docker Compose cho cả môi trường Demo và Production.
- **Security model**: Xác thực Admin bằng JWT; Phân quyền vai trò (Admin, Librarian/Staff); Dữ liệu khuôn mặt được mã hóa/bảo vệ dưới dạng vector embedding, không lưu ảnh gốc của người lạ.

## Validation Shape

| Layer | Expected proof |
| --- | --- |
| Unit | Các hàm trích xuất embedding, so sánh similarity, tính toán line crossing |
| Integration | API CRUD camera, API REST và WebSocket ghi nhận event, kết nối PostgreSQL/Redis |
| E2E | Luồng giả lập video gửi qua webcam/upload và kiểm tra tạo event/session tương ứng trên UI |
| Platform | Chạy thử nghiệm docker-compose trên Windows/Linux |
| Release | Đánh giá FPS, Latency và độ chính xác đếm lượt (Counting accuracy) |

## Open Decisions

- **0008-frontend-stack**: Chọn React với Vite hay Next.js để phát triển Web UI.
- **0009-ai-pipeline-framework**: Lựa chọn framework chạy YOLO & InsightFace tối ưu (onnxruntime hay framework gốc).
- **0010-database-migration**: Lựa chọn công cụ migration cho backend (Alembic cho FastAPI).

## First Story Candidates

- **US-001**: Khởi tạo cấu trúc dự án (Backend FastAPI, Frontend React, Docker Compose cơ bản) và endpoint Health Check.
- **US-002**: Pipeline AI đọc video/webcam frame, thực hiện Person Detection và Tracking (Phase 1).
- **US-003**: Cấu hình line ảo trên video và thuật toán phát hiện Line Crossing (ENTRY/EXIT).

## Harness Delta

- Không có thay đổi nào đối với Harness core. Sử dụng cấu trúc hiện tại của Harness v0.
