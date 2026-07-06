# 0008 Frontend Stack Selection

Date: 2026-07-06

## Status

Accepted

## Context

Hệ thống cần cung cấp một giao diện web cho admin và librarian để xem dashboard thời gian thực, quản lý camera, cấu hình vẽ line ảo trực tiếp trên video preview, quản lý danh sách người quen và người lạ. Chúng ta cần lựa chọn công nghệ frontend phù hợp giữa React với Vite (Single Page Application) và Next.js (SSR/Framework full-stack).

## Decision

Lựa chọn **React kết hợp với Vite** cho sự phát triển của Web UI.
- Giao diện web hoạt động hoàn toàn như một Client-Side Dashboard.
- Không cần SEO cho trang quản trị nội bộ này.
- Giao tiếp với backend API thông qua REST (FastAPI) và WebSocket (cho luồng cập nhật sự kiện thời gian thực).
- Vite cung cấp trải nghiệm dev cực kỳ nhanh và cấu trúc build gọn nhẹ.

## Alternatives Considered

1. **Next.js**: Bị loại bỏ vì các tính năng như Server-Side Rendering (SSR) hay React Server Components không đem lại lợi ích rõ rệt cho một ứng dụng Dashboard quản lý nội bộ qua WebSocket, đồng thời làm tăng độ phức tạp trong cấu hình triển khai (dockerization).
2. **Vanilla HTML/JS**: Bị loại bỏ vì việc xây dựng biểu đồ, quản lý state và tương tác canvas vẽ line ảo trực tiếp sẽ rất phức tạp và khó bảo trì nếu không có component framework.

## Consequences

Positive:

- Tách biệt rõ ràng Frontend (React) và Backend (FastAPI), dễ dockerize độc lập.
- Tận dụng hệ sinh thái thư viện React phong phú cho Dashboard (Recharts cho biểu đồ, Lucide React cho icon, Tailwind/Vanilla CSS cho UI).
- Hot Module Replacement (HMR) của Vite giúp dev nhanh chóng.

Tradeoffs:

- Client-side routing phải tự quản lý qua `react-router-dom`.
- Toàn bộ source code frontend được tải về trình duyệt, cần chú ý bảo mật cấu hình environment variables.

## Follow-Up

- Thực hiện khởi tạo thư mục dự án frontend dưới `surfaces/browser/` bằng Vite.
