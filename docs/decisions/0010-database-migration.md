# 0010 Database Migration Tool

Date: 2026-07-06

## Status

Accepted

## Context

Dự án sử dụng cơ sở dữ liệu PostgreSQL kèm theo extension pgvector để lưu trữ dữ liệu người dùng, cấu hình camera, vector khuôn mặt và nhật ký sự kiện. Chúng ta cần một công cụ quản lý lược đồ cơ sở dữ liệu (migration tool) để theo dõi và cập nhật database schema một cách đồng nhất, tránh thực thi SQL thủ công trên production.

## Decision

Lựa chọn **Alembic** làm công cụ quản lý database migration cho backend Python.
- Alembic tích hợp hoàn hảo với **SQLAlchemy** (ORM đề xuất cho dự án FastAPI).
- Cho phép tự động sinh (auto-generate) các file migration bằng cách so sánh code định nghĩa Model với trạng thái database thực tế.
- Hỗ trợ tốt các kiểu dữ liệu tùy biến (như `vector` của pgvector) thông qua các lệnh raw SQL hoặc helper extensions.

## Alternatives Considered

1. **Chạy SQL Script thủ công**: Dễ làm ở giai đoạn demo nhưng cực kỳ rủi ro ở giai đoạn production, dễ dẫn đến mất đồng bộ schema giữa các môi trường.
2. **Prisma (Node.js)**: Không phù hợp vì backend được viết bằng Python. Việc dùng Prisma yêu cầu phải có Node runtime chạy song song ở backend.

## Consequences

Positive:

- Theo dõi lịch sử thay đổi schema dưới dạng code (migrations versioning).
- Dễ dàng tích hợp lệnh `alembic upgrade head` vào quá trình khởi động của Docker container trước khi backend khởi chạy.

Tradeoffs:

- Cần cấu hình ban đầu để Alembic nhận diện kiểu dữ liệu `vector` của pgvector mà không tạo ra các sai khác không đáng có khi chạy auto-generate.

## Follow-Up

- Cài đặt `alembic` và `SQLAlchemy` trong dependencies của backend.
- Tạo thư mục migrations và cấu hình file `env.py`.
