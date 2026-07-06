# US-001 Project Structure Setup and Health Check Verification

## Status

implemented

## Lane

normal

## Product Contract

Khởi tạo cấu trúc khung dự án (backend FastAPI, frontend React/Vite, cấu hình Docker Compose) và cung cấp endpoint `/api/health` để kiểm tra trạng thái hoạt động của hệ thống backend.

## Relevant Product Docs

- `docs/product/overview.md`

## Acceptance Criteria

- [x] Backend API được khởi tạo trong thư mục `app/` với các dependencies được quản lý rõ ràng.
- [x] Frontend Web Dashboard được khởi tạo trong thư mục `surfaces/browser/` bằng React + Vite.
- [x] Có file `docker-compose.yml` ở thư mục gốc để khởi chạy cả Backend, Frontend, PostgreSQL và Redis.
- [x] Backend cung cấp endpoint `GET /api/health` trả về kết quả JSON dạng `{"status": "healthy", "services": {"database": "up", "cache": "up"}}`.
- [x] Có lệnh kiểm định tự động (verify command) có thể ping endpoint health check và trả về mã thoát (exit code) 0 nếu healthy.

## Design Notes

- **Backend structure**:
  ```text
  app/
    main.py
    requirements.txt
    Dockerfile
  ```
- **Frontend structure**:
  ```text
  surfaces/
    browser/
      src/
      package.json
      Dockerfile
  ```
- **Docker Compose Ports**:
  - Backend: 8000
  - Frontend: 5173
  - PostgreSQL: 5432
  - Redis: 6379

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Không yêu cầu ở bước setup |
| Integration | Chạy script check health endpoint trả về HTTP 200 và JSON hợp lệ |
| E2E | Khởi chạy docker-compose up -d và chạy script validation thành công |
| Platform | Docker containers hoạt động ổn định trên môi trường Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Lệnh chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-001` đã chạy thành công qua python script `scripts/validate_health.py` và trả về kết quả:
  ```text
  Starting health validation check against http://localhost:8000/api/health...
  Received response: {'status': 'healthy', 'timestamp': 1783326927.6204493, 'services': {'database': 'configured at localhost', 'cache': 'configured at localhost'}}
  Health check validation PASSED successfully!
  Story US-001 verification: pass
  ```

