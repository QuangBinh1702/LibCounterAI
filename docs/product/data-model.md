# Database Schema & Data Model - LibCounterAI

Tài liệu này đặc tả cấu trúc bảng dữ liệu cho cơ sở dữ liệu chính của LibCounterAI.

## 1. Công nghệ lưu trữ

- **PostgreSQL**: CSDL quan hệ chính dùng để lưu trữ thông tin cấu hình camera, người quen, sự kiện ra/vào và các phiên.
- **pgvector**: Extension mở rộng của PostgreSQL để lưu trữ dữ liệu vector khuôn mặt 512 chiều (kiểu dữ liệu `vector(512)`) và thực hiện truy vấn so khớp cosine similarity nhanh chóng trực tiếp bằng SQL.
- **Redis**: CSDL dạng key-value tốc độ cao dùng để lưu trạng thái trực tuyến của camera, danh sách các phiên đang mở (active sessions), cache debounce cho thuật toán đếm, và log hoạt động thời gian thực phục vụ WebSocket API.

## 2. Lược đồ các bảng CSDL (PostgreSQL)

### 2.1. Bảng `users` (Quản trị viên / Thủ thư)
Lưu thông tin đăng nhập và phân quyền của nhân viên hệ thống.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN', 'LIBRARIAN')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2. Bảng `persons` (Người quen đăng ký)
Lưu thông tin hồ sơ cơ bản của người dùng thư viện đã đăng ký.

```sql
CREATE TABLE persons (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    member_code VARCHAR(50) UNIQUE NOT NULL, -- Mã số sinh viên / mã thẻ thư viện
    role VARCHAR(20) NOT NULL CHECK (role IN ('STUDENT', 'FACULTY', 'STAFF', 'GUEST')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACTIVE', 'INACTIVE')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3. Bảng `face_templates` (Mẫu khuôn mặt người quen)
Lưu các mẫu vector khuôn mặt đã trích xuất từ ảnh đăng ký của người quen. Một người quen có thể có nhiều mẫu (từ 5-8 mẫu ảnh khác nhau) để tăng độ chính xác nhận diện.

```sql
CREATE TABLE face_templates (
    id SERIAL PRIMARY KEY,
    person_id INT REFERENCES persons(id) ON DELETE CASCADE,
    embedding_vector vector(512) NOT NULL, -- Yêu cầu extension pgvector
    model_name VARCHAR(50) NOT NULL,       -- Ví dụ: 'arcface_r100_v1'
    model_version VARCHAR(20) NOT NULL,
    quality_score FLOAT NOT NULL,          -- Điểm chất lượng ảnh thu mẫu
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('UPLOAD', 'CAMERA')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
-- Index hỗ trợ tìm kiếm cosine similarity
CREATE INDEX ON face_templates USING hnsw (embedding_vector vector_cosine_ops);
```

### 2.4. Bảng `unknown_identities` (Định danh người lạ)
Lưu mã định danh ẩn danh và vector khuôn mặt của người lạ để tái định danh khi họ quay lại.

```sql
CREATE TABLE unknown_identities (
    id SERIAL PRIMARY KEY,
    anonymous_code VARCHAR(50) UNIQUE NOT NULL, -- Ví dụ: 'UNKNOWN_20260706_0001'
    embedding_vector vector(512) NOT NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    visit_count INT DEFAULT 1,
    expire_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Thời gian hết hiệu lực của vector (1-7 ngày)
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'EXPIRED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ON unknown_identities USING hnsw (embedding_vector vector_cosine_ops);
```

### 2.5. Bảng `cameras` (Thiết bị Camera)
Lưu cấu hình kết nối của các camera trong hệ thống.

```sql
CREATE TABLE cameras (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('WEBCAM', 'FILE', 'RTSP')),
    source_url VARCHAR(500) NOT NULL, -- RTSP URL hoặc webcam ID / path file
    status VARCHAR(20) NOT NULL DEFAULT 'OFFLINE' CHECK (status IN ('ONLINE', 'OFFLINE', 'ERROR')),
    last_online_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.6. Bảng `camera_configs` (Cấu hình vạch ảo và thuật toán AI)
Lưu tọa độ đường vẽ line ảo và các tham số ngưỡng cấu hình cho từng camera.

```sql
CREATE TABLE camera_configs (
    id SERIAL PRIMARY KEY,
    camera_id INT UNIQUE REFERENCES cameras(id) ON DELETE CASCADE,
    entry_line_config JSONB NOT NULL,    -- Tọa độ vạch ảo vào (ví dụ: [[x1,y1],[x2,y2]])
    exit_line_config JSONB NOT NULL,     -- Tọa độ vạch ảo ra (nếu vẽ chung một vạch thì cấu hình hướng)
    inside_zone_config JSONB,            -- Định nghĩa đa giác vùng phía trong thư viện
    outside_zone_config JSONB,           -- Định nghĩa đa giác vùng phía ngoài thư viện
    roi_config JSONB,                    -- Region of Interest (vùng quan tâm bỏ qua phần biên nhiễu)
    debounce_seconds INT DEFAULT 5,
    person_detection_confidence FLOAT DEFAULT 0.5,
    face_detection_confidence FLOAT DEFAULT 0.6,
    recognition_threshold FLOAT DEFAULT 0.6,
    unknown_threshold FLOAT DEFAULT 0.55,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.7. Bảng `events` (Nhật ký sự kiện đếm người)
Lưu trữ thông tin chi tiết của từng sự kiện di chuyển cắt line ảo.

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('ENTRY', 'EXIT', 'SEEN', 'UNMATCHED_EXIT')),
    identity_type VARCHAR(20) NOT NULL CHECK (identity_type IN ('KNOWN', 'UNKNOWN', 'UNRESOLVED')),
    person_id INT REFERENCES persons(id) ON DELETE SET NULL,
    unknown_id INT REFERENCES unknown_identities(id) ON DELETE SET NULL,
    track_id INT NOT NULL,               -- ID theo dõi sinh ra bởi ByteTrack
    camera_id INT REFERENCES cameras(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    confidence FLOAT NOT NULL,           -- Độ tin cậy của thuật toán nhận dạng mặt
    metadata_json JSONB,                 -- Các thông tin metadata phụ (tọa độ cắt line, file video ghi lại lỗi...)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.8. Bảng `visit_sessions` (Phiên truy cập thư viện)
Lưu kết quả tổng hợp của quá trình vào và ra của từng người đọc. Dùng để thống kê lượng người đang ở trong thư viện và thời gian lưu lại trung bình.

```sql
CREATE TABLE visit_sessions (
    id SERIAL PRIMARY KEY,
    identity_type VARCHAR(20) NOT NULL CHECK (identity_type IN ('KNOWN', 'UNKNOWN')),
    person_id INT REFERENCES persons(id) ON DELETE SET NULL,
    unknown_id INT REFERENCES unknown_identities(id) ON DELETE SET NULL,
    entry_camera_id INT REFERENCES cameras(id) ON DELETE SET NULL,
    entry_event_id INT REFERENCES events(id) ON DELETE SET NULL,
    exit_camera_id INT REFERENCES cameras(id) ON DELETE SET NULL,
    exit_event_id INT REFERENCES events(id) ON DELETE SET NULL,
    entry_at TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INT,                -- exit_at - entry_at (tính bằng giây)
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED', 'UNMATCHED', 'TIMEOUT')),
    confidence_avg FLOAT,                -- Độ chính xác trung bình của nhận dạng trong phiên
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sessions_active ON visit_sessions(status) WHERE status = 'ACTIVE';
```

## 3. Bảng nhật ký kiểm toán

### 3.1. Bảng `audit_logs` (Nhật ký kiểm toán)

Lưu vết tất cả hành động liên quan đến bảo mật, quyền riêng tư và vòng đời dữ liệu.

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER,
    actor VARCHAR(100),
    details JSON,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ON audit_logs(action, created_at);
CREATE INDEX ON audit_logs(entity_type, entity_id);
```
