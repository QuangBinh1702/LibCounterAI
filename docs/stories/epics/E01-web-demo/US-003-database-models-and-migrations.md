# US-003 Database Models and Schema Setup

## Status

implemented

## Lane

normal

## Product Contract

Thiết lập cơ sở dữ liệu quan hệ, định nghĩa các mô hình thực thể (SQLAlchemy Models) tương ứng với tài liệu `docs/product/data-model.md`, và cấu hình cơ chế migration sử dụng Alembic để quản lý thay đổi lược đồ database.

## Relevant Product Docs

- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Định nghĩa cấu hình kết nối database trong `app/database.py` hỗ trợ cả PostgreSQL (kèm pgvector) và tự động fallback về SQLite cho môi trường phát triển cục bộ nếu cần.
- [x] Định nghĩa các SQLAlchemy Models trong `app/models.py` cho tất cả các bảng dữ liệu: `users`, `persons`, `face_templates`, `unknown_identities`, `cameras`, `camera_configs`, `events`, `visit_sessions`.
- [x] Tích hợp kiểu dữ liệu `pgvector` cho cột lưu trữ vector khuôn mặt (512 chiều) khi chạy trên PostgreSQL.
- [x] Khởi tạo môi trường Alembic migrations và viết kịch bản tạo bảng tự động.
- [x] Có script kiểm định tự động (verify script) để chạy khởi tạo/migration database cục bộ và xác nhận cấu trúc bảng được tạo thành công.

## Design Notes

- **SQLAlchemy mapping**:
  - `face_templates.embedding_vector` -> sử dụng `pgvector.sqlalchemy.Vector(512)` trên PostgreSQL, fallback về `Text` hoặc `JSON` trên SQLite.
  - Sử dụng khóa ngoại và mối quan hệ (relationship) đúng đắn (ví dụ: `persons` -> `face_templates` cascade delete).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Chạy migration tạo các bảng dữ liệu thành công |
| E2E | N/A |
| Platform | Hoạt động tốt với SQLite hoặc PostgreSQL cục bộ trên Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-003` thành công qua Alembic migration và Python script:
  ```text
  Running: python scripts/validate_database.py
  Database connection & models imported successfully.
  Creating database tables...
  Database tables created successfully!
  Testing database CRUD operations...
  Database insert transaction committed successfully.
  Performing assertions and querying data...
  All database assertions PASSED successfully!
  Cleaning up test database records...
  Cleanup transaction committed successfully.
  Story US-003 verification: pass
  ```

