# 0009 Backend and AI Stack Selection

Date: 2026-07-06

## Status

Accepted

## Context

Hệ thống yêu cầu xử lý AI trên server tập trung (đọc video stream, chạy YOLO để phát hiện người, ByteTrack để tracking, InsightFace để nhận dạng mặt). Chúng ta cần chọn ngôn ngữ và framework cho Backend API và cấu trúc chạy AI model.

## Decision

Lựa chọn **Python với FastAPI** làm Backend API chính và sử dụng **ONNX Runtime** để chạy suy luận (inference) các model AI.
- FastAPI (Python) có tốc độ xử lý I/O không đồng bộ (asyncio) tốt, rất hợp với luồng WebSocket thời gian thực và REST API.
- Python là ngôn ngữ tiêu chuẩn của hệ sinh thái AI (OpenCV, YOLO, InsightFace).
- ONNX Runtime cho phép tải và chạy các model YOLO (phát hiện người) và SCRFD/ArcFace (phát hiện/trích xuất mặt) với hiệu năng tối ưu trên cả CPU và GPU mà không cần cài đặt toàn bộ thư viện PyTorch cồng kềnh.

## Alternatives Considered

1. **NestJS (Node.js)** làm API backend và gọi sang Python microservice xử lý AI: Bị loại bỏ ở giai đoạn MVP này vì gây phức tạp hóa hạ tầng (phải duy trì 2 service độc lập, tăng độ trễ giao tiếp). Một ứng dụng FastAPI duy nhất có background workers hoặc thread pools xử lý video là đủ gọn nhẹ cho Phase 1-4.
2. **C++ (OpenCV/Dlib)**: Cho hiệu năng cao nhất nhưng tốc độ phát triển chậm, khó bảo trì và tích hợp WebSockets so với Python/FastAPI.

## Consequences

Positive:

- Tối giản hạ tầng: Chỉ có 1 backend service viết bằng Python đảm nhận cả vai trò API Web và AI Processing.
- ONNX Runtime giúp giảm kích thước docker image đáng kể (không cần cuda-pytorch cồng kềnh trừ khi thực sự cần tối ưu hóa sâu trong production).
- Dễ dàng debug, viết unit test cho pipeline AI bằng Python.

Tradeoffs:

- Python bị ảnh hưởng bởi Global Interpreter Lock (GIL). Tác vụ xử lý video nặng cần được đẩy sang các Process/Thread riêng biệt để tránh làm nghẽn Event Loop của FastAPI.

## Follow-Up

- Khởi tạo backend trong thư mục `app/` sử dụng `poetry` hoặc `pip` + `requirements.txt`.
- Cấu hình Dockerfile hỗ trợ cài đặt các gói OpenCV-headless và ONNX Runtime.
