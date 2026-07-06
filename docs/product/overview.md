# Product Overview - LibCounterAI

## 1. Giới thiệu

LibCounterAI là hệ thống nhận diện khuôn mặt và thống kê lượt ra/vào thư viện của độc giả theo thời gian thực sử dụng camera giám sát kết hợp với xử lý AI tập trung trên server.

## 2. Mục tiêu hệ thống

- Phân loại rõ ràng người quen (độc giả đã đăng ký mẫu khuôn mặt) và người lạ (khách vãng lai).
- Tự động gán định danh ẩn danh (`UNKNOWN_XXX`) cho người lạ nhằm phục vụ thống kê không cần danh tính.
- Đếm chính xác lượt vào (ENTRY) và lượt ra (EXIT) dựa trên vạch ảo tự cấu hình (line crossing).
- Ghi nhận và quản lý thời gian vào/ra, tính toán thời lượng lưu lại thư viện theo phiên di chuyển (visit sessions).
- Cung cấp màn hình Dashboard hiển thị trạng thái thời gian thực của thư viện (số lượng người đang có mặt, biểu đồ lưu lượng theo giờ, nhật ký sự kiện vào/ra).

## 3. Kiến trúc xử lý (AI on Server)

Hệ thống hoạt động theo phương án **xử lý AI tập trung trên server (Server-side processing)**:
- Camera hoặc webcam chỉ thu và gửi luồng hình ảnh/video thô (qua RTSP/HTTP).
- Không yêu cầu camera có phần cứng AI mạnh hay nạp model trực tiếp trên thiết bị.
- Server chịu trách nhiệm phân tích luồng, detect đối tượng, track vết di chuyển, detect mặt và so khớp đặc trưng vector sinh trắc học.
- Đảm bảo tính linh hoạt khi nâng cấp model AI và dễ dàng quản lý database tập trung.

## 4. Phân loại đối tượng và Phiên truy cập

### 4.1. Người quen (Known Person)
Là những người đã được đăng ký trước hồ sơ trong hệ thống (thông tin tên, vai trò, mã số sinh viên/thẻ thư viện) và có lưu trữ vector khuôn mặt (face embedding) trong cơ sở dữ liệu.

### 4.2. Người lạ (Unknown Visitor)
Là người chưa có thông tin trong CSDL. Khi xuất hiện lần đầu qua line, hệ thống tự cấp mã định danh ẩn danh dạng `UNKNOWN_<UUID/STT>`.
- Hệ thống so sánh vector khuôn mặt của họ với database người lạ còn hiệu lực để tránh sinh nhiều định danh khác nhau cho cùng một người quay lại nhiều lần trong khoảng thời gian lưu giữ (retention window).
- Không lưu ảnh chụp khuôn mặt gốc mặc định để bảo mật quyền riêng tư sinh trắc học.

### 4.3. Phiên ra/vào (Visit Session)
Một phiên bắt đầu khi có sự kiện ENTRY và đóng lại khi có sự kiện EXIT của một định danh (Known hoặc Unknown).
- Một người có thể phát sinh nhiều phiên ra/vào trong ngày.
- Trường hợp có sự kiện EXIT mà không có active session tương ứng trước đó, hệ thống ghi nhận sự kiện `unmatched_exit` để phục vụ giám sát và báo cáo lỗi đếm.

## 5. Quy tắc nghiệp vụ đếm và Debounce

- Chỉ đếm khi đối tượng thực sự cắt qua line ảo (line crossing) theo hướng cấu hình.
- Đối tượng đứng yên hoặc di chuyển qua lại liên tục gần line trong khoảng thời gian ngắn (debounce window) sẽ không bị kích hoạt nhiều sự kiện trùng lắp.
- Thời gian chờ của phiên (session timeout) tự động đóng các phiên kéo dài quá lâu (ví dụ quá 8-12 tiếng) nếu thiếu sự kiện EXIT tương ứng.
