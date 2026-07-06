SPEC v2.0
HỆ THỐNG NHẬN DIỆN VÀ ĐẾM PHIÊN NGƯỜI RA/VÀO THƯ VIỆN BẰNG CAMERA
PHƯƠNG ÁN CHỐT: XỬ LÝ AI TRÊN SERVER

1. TỔNG QUAN HỆ THỐNG

Hệ thống được xây dựng nhằm giám sát, nhận diện và thống kê người ra/vào thư viện thông qua camera. Hệ thống sử dụng nhận diện khuôn mặt để phân biệt người quen và người lạ, đồng thời ghi nhận từng phiên ra/vào của mỗi người.

Điểm chốt quan trọng của phiên bản SPEC này là:

- Camera hoặc webcam chỉ đóng vai trò là nguồn cung cấp video.
- Toàn bộ xử lý AI sẽ được thực hiện trên server.
- Camera không cần có NPU/GPU.
- Không cần nạp model AI trực tiếp vào camera.
- Server sẽ thực hiện các tác vụ như phát hiện người, tracking, phát hiện khuôn mặt, trích xuất embedding, nhận diện người quen/người lạ và quản lý phiên ra/vào.

Lý do chọn phương án xử lý trên server:

- Server có thể sử dụng GPU mạnh hơn camera.
- Dễ thay đổi, nâng cấp và tối ưu model AI.
- Dễ debug trong quá trình phát triển.
- Dễ quản lý database embedding tập trung.
- Dễ mở rộng nhiều camera.
- Không phụ thuộc vào việc camera có hỗ trợ SDK, NPU hoặc GPU hay không.
- Kết quả nhận diện và tracking ổn định hơn so với xử lý trực tiếp trên camera yếu.

Trong giai đoạn demo, hệ thống sẽ chạy dưới dạng web application, nhận input từ webcam, video upload hoặc RTSP stream. Trong giai đoạn production, camera giám sát thật sẽ gửi video stream về server AI để xử lý.


2. MỤC TIÊU HỆ THỐNG

Hệ thống cần đạt được các mục tiêu sau:

- Nhận diện người quen đã đăng ký trong database.
- Nhận diện người lạ chưa có trong database.
- Gán mã định danh ẩn danh cho người lạ.
- Đếm lượt người đi vào thư viện.
- Đếm lượt người đi ra khỏi thư viện.
- Quản lý từng phiên ra/vào của mỗi người.
- Ghi nhận thời gian vào, thời gian ra và thời lượng ở trong thư viện.
- Cho phép một người có nhiều phiên ra/vào trong ngày.
- Thống kê số người hiện đang có mặt trong thư viện.
- Hiển thị dashboard realtime cho người quản lý.
- Hỗ trợ nhiều camera và nhiều cổng trong tương lai.
- Lưu embedding và log thời gian, không lưu ảnh snapshot nếu không cần thiết.
- Đảm bảo dữ liệu khuôn mặt được xử lý an toàn và có kiểm soát.


3. PHẠM VI HỆ THỐNG

3.1. Phạm vi bản web demo

Bản web demo tập trung vào các chức năng:

- Đăng nhập admin.
- Quản lý camera demo.
- Nhận video từ webcam.
- Nhận video upload.
- Có thể nhận RTSP nếu có camera IP.
- Hiển thị video trên dashboard.
- Cho phép admin vẽ line vào/ra.
- Phát hiện người trong video.
- Theo dõi người bằng tracking.
- Xác định hướng vào/ra bằng line crossing.
- Đăng ký người quen bằng ảnh hoặc camera.
- Trích xuất embedding khuôn mặt trên server.
- Nhận diện người quen.
- Gán unknown_id cho người lạ.
- Tạo phiên ra/vào.
- Hiển thị dashboard realtime.
- Xem lịch sử session.
- Export dữ liệu.

3.2. Phạm vi production

Giai đoạn production mở rộng thêm:

- Kết nối camera giám sát thật qua RTSP/ONVIF.
- Camera gửi video stream về AI server.
- AI server xử lý toàn bộ inference.
- Hỗ trợ nhiều camera/nhiều cổng.
- Tối ưu tốc độ xử lý FPS và latency.
- Có cơ chế reconnect camera khi mất kết nối.
- Có log lỗi hệ thống.
- Có giám sát trạng thái camera và AI server.
- Có phân quyền người dùng.
- Có chính sách lưu trữ và xóa dữ liệu sinh trắc.
- Có báo cáo đánh giá accuracy, FPS và latency.


4. PHƯƠNG ÁN TRIỂN KHAI ĐÃ CHỐT

4.1. Web Demo Mode

Trong giai đoạn demo, video được gửi về backend/server để xử lý AI.

Luồng xử lý:

Webcam / Video Upload / RTSP
        ↓
AI Server
        ↓
Backend API
        ↓
Database
        ↓
Web Dashboard

Frontend web chỉ đảm nhiệm:

- Hiển thị giao diện.
- Hiển thị live video.
- Cho phép admin vẽ line vào/ra.
- Quản lý người quen.
- Xem dashboard.
- Xem lịch sử.
- Export báo cáo.

AI server đảm nhiệm:

- Đọc video.
- Tách frame.
- Detect người.
- Tracking người.
- Detect khuôn mặt.
- Extract embedding.
- Match known/unknown.
- Tạo event vào/ra.
- Quản lý session.

4.2. Production Server Processing Mode

Trong production, camera giám sát thật không xử lý AI. Camera chỉ gửi luồng video về server thông qua RTSP/ONVIF.

Luồng xử lý:

Camera Hikvision / IP Camera
        ↓ RTSP/ONVIF
AI Processing Server
        ↓
Backend API
        ↓
PostgreSQL + pgvector
        ↓
Web Dashboard

Đây là phương án production chính thức của hệ thống.

4.3. On-camera AI Mode

Không chọn làm phương án chính.

Lý do:

- Camera có thể không có NPU/GPU.
- Không phải camera nào cũng cho phép nạp code/model AI.
- Việc debug khó hơn.
- Việc cập nhật model khó hơn.
- Khả năng xử lý nhiều bước AI phức tạp bị hạn chế.
- Không phù hợp với yêu cầu nhận diện người quen, tái định danh người lạ và quản lý phiên ra/vào.

Do đó, hệ thống không yêu cầu camera phải xử lý AI trực tiếp.


5. ĐỊNH NGHĨA NGHIỆP VỤ

5.1. Người quen

Người quen là người đã đăng ký trong hệ thống, có hồ sơ và embedding khuôn mặt trong database.

Ví dụ:

person_id: P001
full_name: Nguyễn Văn A
member_code: SV001
role: student
status: active

5.2. Người lạ

Người lạ là người chưa có trong database người quen. Khi người lạ xuất hiện, hệ thống tạo mã định danh ẩn danh.

Ví dụ:

unknown_id: UNKNOWN_001

Người lạ không có tên thật, không có mã sinh viên và không lưu ảnh gốc. Hệ thống chỉ lưu embedding và log thời gian phục vụ thống kê ra/vào.

5.3. Phiên ra/vào

Một phiên ra/vào bắt đầu khi một người đi vào thư viện và kết thúc khi người đó đi ra.

Ví dụ:

| Người        | Vào   | Ra    | Phiên     |
|--------------|-------|-------|-----------|
| Nguyễn Văn A | 08:00 | 09:00 | Session 1 |
| Nguyễn Văn A | 12:00 | 14:00 | Session 2 |
| UNKNOWN_001  | 08:30 | 10:00 | Session 1 |
| UNKNOWN_001  | 13:00 | 15:00 | Session 2 |

Kết luận:

- Nguyễn Văn A là 1 người quen duy nhất nhưng có 2 phiên.
- UNKNOWN_001 là 1 người lạ duy nhất nhưng có 2 phiên.

5.4. Quy tắc đếm

Hệ thống không đếm theo từng frame. Hệ thống chỉ tạo event khi người đó thật sự đi qua line vào/ra.

| Tình huống | Cách xử lý |
|------------|------------|
| Người đứng trước camera nhiều giây | Không đếm nhiều lần |
| Người quen vào rồi ra | Tạo 1 session |
| Người quen vào lại sau khi đã ra | Tạo session mới |
| Người lạ vào rồi ra | Tạo session cho unknown_id |
| Người lạ quay lại sau đó | Nếu nhận diện lại được unknown_id cũ thì tạo session mới |
| Không nhận diện được mặt | Ghi event confidence thấp hoặc unresolved |
| Người đi sát nhau | Tracking cố gắng tách từng người |
| Người dao động gần line | Không tạo event trùng trong debounce window |


6. KIẾN TRÚC TỔNG THỂ

6.1. Kiến trúc hệ thống

Camera / Webcam / Video File
        ↓
Video Ingestion Service
        ↓
AI Processing Service
        ↓
Event & Session Service
        ↓
Database
        ↓
Backend API
        ↓
Web Dashboard

6.2. Thành phần chính

Frontend Web:
- React.js hoặc Next.js.
- Hiển thị dashboard.
- Hiển thị live video.
- Quản lý người quen.
- Quản lý camera.
- Cấu hình line/ROI.
- Xem lịch sử.
- Export báo cáo.

Backend API:
- Python FastAPI.
- Cung cấp REST API.
- Cung cấp WebSocket realtime.
- Quản lý person, camera, event, session, dashboard.

AI Processing Service:
- OpenCV/FFmpeg để đọc video.
- YOLO để phát hiện người.
- ByteTrack hoặc BoT-SORT để tracking.
- InsightFace/SCRFD để phát hiện và trích xuất embedding khuôn mặt.
- Cosine similarity để so khớp embedding.
- Gửi event về backend.

Database:
- PostgreSQL lưu dữ liệu chính.
- pgvector lưu và tìm kiếm embedding.
- Redis lưu cache realtime, active session, debounce cache và trạng thái camera.

Storage:
- Không lưu snapshot khuôn mặt mặc định.
- Chỉ lưu embedding và log thời gian.
- Nếu sau này cần lưu snapshot để review lỗi thì phải có cấu hình riêng và chính sách lưu trữ rõ ràng.


7. ACTOR TRONG HỆ THỐNG

| Actor | Vai trò |
|-------|---------|
| Admin | Quản lý hệ thống, camera, người quen, line, báo cáo |
| Librarian / Staff | Theo dõi dashboard, xem số người hiện tại, xem lịch sử |
| Registered Person | Người quen đã đăng ký |
| Unknown Visitor | Người lạ chưa có danh tính |
| AI Processing Service | Xử lý video và tạo event |
| System Operator | Triển khai, vận hành và giám sát server/camera |


8. USER STORIES

8.1. Nhóm Admin

US-01 — Đăng nhập hệ thống

Là Admin, tôi muốn đăng nhập vào hệ thống để chỉ người có quyền mới được quản lý dữ liệu ra/vào thư viện.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Admin nhập đúng tài khoản | Đăng nhập thành công |
| Admin nhập sai tài khoản | Hiển thị lỗi |
| Người chưa đăng nhập truy cập dashboard | Bị chuyển về trang đăng nhập |
| Token hết hạn | Yêu cầu đăng nhập lại |

US-02 — Thêm camera

Là Admin, tôi muốn thêm camera vào hệ thống để hệ thống có thể lấy video từ camera đó.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Admin nhập camera name, source type, source URL | Camera được tạo thành công |
| Source URL sai hoặc không kết nối được | Hệ thống báo lỗi kết nối |
| Camera là webcam demo | Hệ thống hiển thị được live preview |
| Camera là RTSP | AI server đọc được stream nếu URL hợp lệ |
| Camera không có GPU/NPU | Không ảnh hưởng vì AI chạy trên server |

US-03 — Cấu hình line vào/ra

Là Admin, tôi muốn vẽ line ảo trên video để hệ thống biết đâu là ranh giới vào/ra.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Admin vẽ line trên khung hình | Line được lưu vào cấu hình camera |
| Admin chọn hướng ngoài vào trong | Hệ thống hiểu đó là ENTRY |
| Admin chọn hướng trong ra ngoài | Hệ thống hiểu đó là EXIT |
| Người đi qua line đúng hướng | Tạo event đúng loại |
| Người dao động gần line | Không tạo nhiều event trùng |

US-04 — Đăng ký người quen

Là Admin, tôi muốn đăng ký người quen bằng ảnh hoặc camera để hệ thống nhận diện họ trong những lần ra/vào sau.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Admin tạo hồ sơ người mới | Hồ sơ có trạng thái pending |
| Admin upload đủ ảnh hợp lệ | Server tạo embedding thành công |
| Ảnh bị mờ, quá tối hoặc không có mặt | Hệ thống từ chối ảnh |
| Ảnh có nhiều khuôn mặt | Hệ thống yêu cầu upload ảnh khác |
| Người này giống hồ sơ đã tồn tại | Hệ thống cảnh báo có thể bị trùng |
| Đăng ký hoàn tất | Trạng thái chuyển sang active |

US-05 — Quản lý người quen

Là Admin, tôi muốn xem, sửa, vô hiệu hóa hoặc xóa người quen trong database.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Admin xem danh sách người quen | Hiển thị tên, mã, vai trò, trạng thái |
| Admin sửa thông tin | Dữ liệu được cập nhật |
| Admin disable người quen | Người đó không còn được nhận diện là known active |
| Admin xóa người quen | Hồ sơ bị xóa mềm hoặc ẩn khỏi hệ thống |
| Người bị disable xuất hiện | Có thể được gán unknown hoặc inactive known tùy cấu hình |

US-06 — Xem dashboard realtime

Là Admin hoặc Librarian, tôi muốn xem số người hiện đang ở trong thư viện và các event ra/vào theo thời gian thực.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Có người đi vào | Dashboard tăng lượt vào |
| Có người đi ra | Dashboard tăng lượt ra |
| Có người đang ở trong thư viện | Occupancy tăng/giảm chính xác |
| Event mới phát sinh | Dashboard cập nhật realtime |
| Mất kết nối camera | Dashboard hiển thị camera offline |
| AI server lỗi | Dashboard hiển thị trạng thái AI service lỗi |

US-07 — Xem lịch sử ra/vào

Là Admin hoặc Librarian, tôi muốn xem lại lịch sử ra/vào theo ngày, người, loại người và camera.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Chọn một ngày cụ thể | Hiển thị event/session trong ngày đó |
| Lọc theo người quen | Chỉ hiển thị session của người đó |
| Lọc theo unknown | Hiển thị session của người lạ |
| Lọc theo camera/cổng | Hiển thị event từ camera/cổng đó |
| Không có dữ liệu | Hiển thị trạng thái rỗng rõ ràng |

US-08 — Export báo cáo

Là Admin, tôi muốn export dữ liệu ra/vào để phục vụ thống kê và báo cáo.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Admin chọn khoảng ngày | Hệ thống xuất dữ liệu đúng khoảng ngày |
| Export CSV | File CSV tải được |
| Export Excel | File Excel tải được |
| Dữ liệu export | Có entry time, exit time, duration, identity type, camera/gate |
| Không có dữ liệu | Export file rỗng có header hoặc báo không có dữ liệu |


8.2. Nhóm Librarian / Staff

US-09 — Theo dõi số người hiện tại

Là thủ thư, tôi muốn biết hiện tại có bao nhiêu người trong thư viện để hỗ trợ quản lý không gian.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Một người vào | Số người hiện tại +1 |
| Một người ra | Số người hiện tại -1 |
| Người vào nhưng chưa ra | Được tính là đang ở trong thư viện |
| Người ra nhưng không có session vào | Tạo unmatched exit để kiểm tra |
| Số người không được âm | Nếu có lỗi exit, hệ thống không giảm dưới 0 |

US-10 — Xem khung giờ đông

Là thủ thư, tôi muốn biết khung giờ nào đông người để hỗ trợ quản lý thư viện.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Chọn ngày | Hiển thị biểu đồ lượt vào/ra theo giờ |
| Có nhiều session | Tính đúng peak hour |
| Không có dữ liệu | Hiển thị biểu đồ rỗng hoặc thông báo |
| Dữ liệu thay đổi realtime | Biểu đồ cập nhật hoặc refresh được |


8.3. Nhóm Registered Person

US-11 — Người quen đi vào thư viện

Là người đã đăng ký, khi tôi đi vào thư viện, hệ thống cần nhận diện tôi và tạo phiên vào mới.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Người quen đi qua line từ ngoài vào trong | Tạo ENTRY event |
| Nhận diện khớp database | Gán đúng person_id |
| Người đó chưa có active session | Tạo session mới |
| Người đó đã có active session | Không tạo session trùng |
| Người đó vào lại sau khi đã ra | Tạo session mới |

US-12 — Người quen đi ra khỏi thư viện

Là người đã đăng ký, khi tôi đi ra, hệ thống cần đóng phiên hiện tại của tôi.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Người quen đi từ trong ra ngoài | Tạo EXIT event |
| Có active session | Cập nhật exit_at và duration |
| Không có active session | Tạo unmatched exit |
| Người đó ra rồi vào lại | Session cũ giữ nguyên, session mới được tạo khi vào lại |


8.4. Nhóm Unknown Visitor

US-13 — Người lạ đi vào thư viện

Là người chưa đăng ký, khi tôi đi vào thư viện, hệ thống cần gán cho tôi một unknown_id và tạo phiên vào.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Không match known database | Gán identity_type = UNKNOWN |
| Không match unknown cũ | Tạo unknown_id mới |
| Có match unknown cũ | Dùng lại unknown_id cũ |
| Người lạ đi vào | Tạo session active |
| Không lưu ảnh gốc | Chỉ lưu embedding và log thời gian |

US-14 — Người lạ quay lại nhiều lần

Là hệ thống, tôi cần nhận diện cùng một người lạ quay lại để đếm đúng số phiên ra/vào.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| UNKNOWN_001 vào 08:00, ra 09:00 | Tạo session 1 |
| UNKNOWN_001 quay lại 12:00 | Tạo session 2 cho cùng unknown_id |
| UNKNOWN_001 ra 14:00 | Đóng session 2 |
| Dashboard thống kê | Hiển thị 1 unknown person, 2 sessions |
| Unknown hết thời gian lưu | Xóa hoặc vô hiệu hóa unknown embedding |


8.5. Nhóm AI Processing Service

US-15 — Phát hiện và tracking người

Là AI service, tôi muốn phát hiện và tracking người trong video để tránh đếm trùng.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Một người xuất hiện nhiều frame | Giữ cùng track_id trong thời gian hợp lý |
| Người đi qua line | Chỉ tạo 1 crossing event |
| Người đứng gần line | Không tạo event lặp |
| Người bị mất dấu ngắn hạn | Cố gắng nối lại track nếu trong ngưỡng thời gian |
| Nhiều người cùng xuất hiện | Mỗi người có track riêng nếu nhìn thấy rõ |

US-16 — Nhận diện khuôn mặt

Là AI service, tôi muốn nhận diện khuôn mặt để phân loại known/unknown.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Face rõ, đủ sáng | Tạo embedding thành công |
| Face match known threshold | Gán person_id |
| Face không match known | Chuyển sang unknown matching |
| Face chất lượng thấp | Không dùng để tạo identity chính thức |
| Không thấy mặt | Vẫn có thể tracking người, nhưng event có confidence thấp |

US-17 — Tạo event vào/ra

Là AI service, tôi muốn tạo event khi người crossing line đúng hướng.

Acceptance criteria:

| Điều kiện | Kết quả mong muốn |
|----------|-------------------|
| Track đi từ outside zone sang inside zone | Tạo ENTRY |
| Track đi từ inside zone sang outside zone | Tạo EXIT |
| Track chưa crossing line | Không tạo event |
| Track crossing nhiều lần trong debounce window | Chỉ tạo 1 event |
| Event có identity | Lưu identity_type, person_id/unknown_id, confidence |


9. FUNCTIONAL REQUIREMENTS

9.1. Quản lý camera

Hệ thống phải cho phép:

- Thêm camera.
- Sửa camera.
- Xóa hoặc disable camera.
- Kiểm tra trạng thái online/offline.
- Cấu hình nguồn video.
- Cấu hình RTSP URL.
- Cấu hình line vào/ra.
- Cấu hình vùng ROI.
- Cấu hình cổng/gate tương ứng.
- Kiểm tra kết nối camera.
- Hiển thị trạng thái camera realtime.

9.2. Quản lý người quen

Hệ thống phải cho phép:

- Tạo hồ sơ người quen.
- Upload ảnh hoặc thu mẫu từ camera.
- Kiểm tra chất lượng ảnh.
- Tạo face embedding trên server.
- Kiểm tra trùng người.
- Active hồ sơ sau khi enrollment đạt.
- Disable hoặc xóa người quen.
- Cập nhật thêm mẫu khuôn mặt nếu nhận diện chưa ổn.

9.3. Nhận diện người quen

Hệ thống phải:

- Detect face.
- Align face.
- Extract embedding.
- So sánh embedding với database.
- Gán person_id nếu vượt ngưỡng.
- Không nhận diện nếu confidence thấp.
- Đánh dấu low-confidence nếu có nhiều người match gần nhau.

9.4. Nhận diện người lạ

Hệ thống phải:

- Tạo unknown_id nếu người không match known database.
- So sánh với unknown database để tái định danh người lạ.
- Gán lại unknown_id cũ nếu đủ giống.
- Tạo unknown_id mới nếu không đủ giống.
- Cho phép một unknown_id có nhiều session.
- Xóa hoặc vô hiệu hóa unknown embedding sau thời gian lưu trữ.

9.5. Quản lý session

Hệ thống phải:

- Tạo session khi có ENTRY.
- Đóng session khi có EXIT.
- Cho phép một người có nhiều session.
- Không tạo session trùng khi người đó đang active.
- Ghi nhận unmatched exit nếu không tìm thấy active session.
- Tính duration của mỗi session.
- Đánh dấu session timeout nếu người vào quá lâu nhưng chưa có event ra.

9.6. Dashboard

Dashboard phải hiển thị:

- Số người hiện đang ở trong thư viện.
- Tổng lượt vào hôm nay.
- Tổng lượt ra hôm nay.
- Tổng session hôm nay.
- Số known visitors.
- Số unknown visitors.
- Event log realtime.
- Trạng thái camera.
- Trạng thái AI server.
- Biểu đồ theo giờ.

9.7. Báo cáo

Hệ thống phải hỗ trợ:

- Lọc theo ngày.
- Lọc theo người.
- Lọc theo known/unknown.
- Lọc theo camera/gate.
- Lọc theo session status.
- Export CSV.
- Export Excel.


10. TECHNOLOGY DECISION / QUYẾT ĐỊNH CÔNG NGHỆ

10.1. Frontend

Công nghệ đề xuất:

- React.js hoặc Next.js.
- WebSocket để cập nhật realtime.
- Canvas hoặc video overlay để vẽ line/ROI trên video.

Frontend chịu trách nhiệm:

- Hiển thị dashboard.
- Hiển thị live camera.
- Cấu hình line/ROI.
- Quản lý người quen.
- Xem lịch sử.
- Export báo cáo.

10.2. Backend

Công nghệ đề xuất:

- Python FastAPI.
- REST API cho CRUD.
- WebSocket cho realtime event.
- Background worker cho tác vụ xử lý video.

Backend chịu trách nhiệm:

- Quản lý user.
- Quản lý camera.
- Quản lý người quen.
- Quản lý event.
- Quản lý session.
- Giao tiếp với AI service.
- Cung cấp API cho dashboard.

10.3. AI Processing

Công nghệ đề xuất:

- OpenCV để xử lý frame.
- FFmpeg để đọc RTSP ổn định hơn.
- YOLO11n hoặc YOLOv8n để detect người.
- ByteTrack cho tracking.
- InsightFace FaceAnalysis để detect mặt, align mặt và extract embedding.
- Cosine similarity để so sánh embedding.

10.4. Database

Công nghệ đề xuất:

- PostgreSQL để lưu dữ liệu chính.
- pgvector để lưu và tìm kiếm face embedding.
- Redis để lưu cache realtime, active session, debounce cache và trạng thái camera.

10.5. Deployment

Công nghệ đề xuất:

- Docker.
- Docker Compose cho MVP.
- GPU server nếu có điều kiện.
- ONNX Runtime hoặc TensorRT nếu cần tối ưu production.
- Nginx reverse proxy nếu triển khai web production.

10.6. Camera

Camera production:

- Camera Hikvision hoặc camera IP tương đương.
- Camera chỉ cần hỗ trợ RTSP/ONVIF.
- Camera không cần NPU/GPU.
- Camera không cần chạy code AI trực tiếp.
- Server sẽ đọc stream và xử lý AI.


11. PIPELINE AI

11.1. Pipeline tổng quát

Video Stream
        ↓
Frame Sampling
        ↓
Person Detection
        ↓
Person Tracking
        ↓
Line Crossing Detection
        ↓
Face Detection
        ↓
Face Alignment
        ↓
Face Embedding Extraction
        ↓
Known Person Matching
        ↓
Unknown Re-identification
        ↓
Session Management
        ↓
Database + Dashboard

11.2. Person Detection

Mục tiêu:

- Phát hiện người trong frame.
- Chỉ lấy class person.
- Bỏ qua object không phải người.

Đầu ra:

- person_bbox
- confidence
- frame_id
- timestamp

11.3. Tracking

Mục tiêu:

- Gán track_id cho từng người.
- Giữ track_id ổn định qua các frame.
- Hạn chế đếm trùng.
- Hỗ trợ xác định hướng di chuyển.

Đầu ra:

- track_id
- person_bbox
- trajectory
- direction
- last_seen_at

11.4. Line Crossing

Mục tiêu:

- Xác định người đi vào hay đi ra.
- Tạo ENTRY/EXIT event.

Quy tắc:

- Outside → Inside: ENTRY.
- Inside → Outside: EXIT.
- Crossing nhiều lần trong debounce window chỉ tính 1 lần.
- Người đứng gần line nhưng không crossing thì không tạo event.

11.5. Face Detection và Embedding

Mục tiêu:

- Detect khuôn mặt trong vùng person_bbox.
- Align khuôn mặt.
- Trích xuất embedding.
- So sánh với database.

Đầu ra:

- face_bbox
- face_quality_score
- embedding_vector
- recognition_confidence

11.6. Known Matching

Quy trình:

1. Lấy embedding từ khuôn mặt.
2. So sánh với known face_templates.
3. Nếu similarity >= known_threshold thì gán person_id.
4. Nếu không đạt ngưỡng thì chuyển sang unknown matching.

11.7. Unknown Matching

Quy trình:

1. Lấy embedding không match known.
2. So sánh với unknown_identities còn hiệu lực.
3. Nếu similarity >= unknown_threshold thì gán unknown_id cũ.
4. Nếu không match thì tạo unknown_id mới.
5. Unknown_id có thể có nhiều session.

11.8. Session Logic

Khi có ENTRY:

- Nếu identity chưa có active session: tạo session mới.
- Nếu identity đã có active session: không tạo session trùng.

Khi có EXIT:

- Nếu identity có active session: đóng session.
- Nếu không có active session: tạo unmatched_exit_event.


12. DATABASE SCHEMA ĐỀ XUẤT

12.1. Bảng users

id
username
password_hash
role
status
created_at
updated_at

12.2. Bảng persons

id
full_name
member_code
role
status
created_at
updated_at

12.3. Bảng face_templates

id
person_id
embedding_vector
model_name
model_version
quality_score
source_type
is_active
created_at

12.4. Bảng unknown_identities

id
anonymous_code
embedding_vector
first_seen_at
last_seen_at
visit_count
expire_at
status
created_at

12.5. Bảng cameras

id
name
source_type
source_url
location_id
gate_id
status
last_online_at
created_at
updated_at

12.6. Bảng camera_configs

id
camera_id
entry_line_config
exit_line_config
inside_zone_config
outside_zone_config
roi_config
debounce_seconds
person_detection_confidence
face_detection_confidence
recognition_threshold
unknown_threshold
created_at
updated_at

12.7. Bảng visit_sessions

id
identity_type: KNOWN | UNKNOWN
person_id nullable
unknown_id nullable
entry_camera_id
entry_gate_id
exit_camera_id nullable
exit_gate_id nullable
entry_at
exit_at nullable
duration_seconds nullable
status: ACTIVE | CLOSED | UNMATCHED | TIMEOUT
confidence_avg
created_at
updated_at

12.8. Bảng events

id
event_type: ENTRY | EXIT | SEEN | DUPLICATE | UNMATCHED_EXIT
identity_type: KNOWN | UNKNOWN | UNRESOLVED
person_id nullable
unknown_id nullable
track_id
camera_id
gate_id
timestamp
confidence
metadata_json
created_at

12.9. Bảng enrollment_sessions

id
person_id
created_by
status: pending | passed | failed
sample_count
accepted_sample_count
rejected_sample_count
created_at
completed_at

12.10. Bảng enrollment_samples

id
enrollment_session_id
quality_score
rejection_reason nullable
embedding_created
created_at

12.11. Bảng model_versions

id
model_name
model_type
model_version
runtime
embedding_dimension
status
activated_at
created_at


13. API ĐỀ XUẤT

13.1. Auth

POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me

13.2. Camera

POST   /api/cameras
GET    /api/cameras
GET    /api/cameras/{id}
PATCH  /api/cameras/{id}
DELETE /api/cameras/{id}
POST   /api/cameras/{id}/test-connection
PATCH  /api/cameras/{id}/config
GET    /api/cameras/{id}/status

13.3. Person

POST   /api/persons
GET    /api/persons
GET    /api/persons/{id}
PATCH  /api/persons/{id}
DELETE /api/persons/{id}

13.4. Enrollment

POST /api/persons/{id}/enrollment
POST /api/persons/{id}/faces/upload
POST /api/persons/{id}/faces/capture
POST /api/persons/{id}/activate

13.5. Unknown identities

GET    /api/unknown-identities
GET    /api/unknown-identities/{id}
DELETE /api/unknown-identities/{id}

13.6. Sessions

GET   /api/sessions
GET   /api/sessions/active
GET   /api/sessions/{id}
PATCH /api/sessions/{id}/review

13.7. Events

GET /api/events
GET /api/events?date=YYYY-MM-DD
GET /api/events?identity_type=KNOWN
GET /api/events?identity_type=UNKNOWN
GET /api/events?camera_id=...

13.8. Dashboard

GET /api/dashboard/today
GET /api/dashboard/hourly
GET /api/dashboard/occupancy
GET /api/dashboard/known-vs-unknown
GET /api/dashboard/camera-status
GET /api/dashboard/ai-server-status

13.9. Export

GET /api/export/sessions.csv
GET /api/export/sessions.xlsx
GET /api/export/events.csv
GET /api/export/events.xlsx


14. NON-FUNCTIONAL REQUIREMENTS

14.1. Hiệu năng

| Yêu cầu | Mục tiêu MVP | Mục tiêu production |
|---------|--------------|---------------------|
| FPS xử lý | 10–15 FPS | 20–30 FPS nếu server đáp ứng |
| Latency event | < 3 giây | < 1 giây đến 2 giây |
| Số camera | 1 | Nhiều camera |
| Dashboard update | 1–3 giây | Gần realtime |
| Query lịch sử | < 3 giây | < 1–2 giây |

14.2. Độ chính xác

| Thành phần | Mục tiêu |
|------------|----------|
| Counting accuracy | >= 90% trong môi trường test |
| Known recognition | Đánh giá bằng dữ liệu thực tế |
| Unknown re-identification | Chấp nhận sai số ở MVP, cải thiện ở production |
| Duplicate event | Có debounce để giảm đếm trùng |
| Unmatched exit | Có log để review |

14.3. Bảo mật

Hệ thống phải có:

- Đăng nhập admin.
- Phân quyền người dùng.
- Không lưu ảnh gốc nếu không cần.
- Không lưu snapshot người lạ mặc định.
- Bảo vệ embedding trong database.
- Log thao tác admin.
- Cấu hình thời hạn lưu unknown embedding.
- Cơ chế xóa dữ liệu khi cần.
- Không hiển thị dữ liệu nhạy cảm cho người không có quyền.

14.4. Khả năng mở rộng

Hệ thống cần có khả năng mở rộng từ:

1 camera / 1 cổng

lên:

N camera / N cổng / nhiều khu vực

Session phải gắn với location/library, không gắn cứng với một camera duy nhất.


15. CÁC GIAI ĐOẠN TRIỂN KHAI VÀ ACCEPTANCE CRITERIA

PHASE 0 — CHỐT YÊU CẦU VÀ KIẾN TRÚC SERVER PROCESSING

Mục tiêu:

Chốt rằng toàn bộ AI sẽ xử lý trên server, camera chỉ gửi video.

Công việc:

- Chốt phương án xử lý AI trên server.
- Chốt loại input demo: webcam, video upload, RTSP.
- Chốt camera production chỉ cần RTSP/ONVIF.
- Chốt không xử lý trực tiếp trên camera.
- Chốt không lưu snapshot mặc định.
- Chốt thời gian lưu unknown embedding.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Kiến trúc được chốt | Camera gửi video, server xử lý AI |
| Camera không cần NPU/GPU | SPEC ghi rõ camera không xử lý AI |
| Demo input được chốt | Có webcam/video/RTSP |
| Dữ liệu lưu được chốt | Lưu embedding + log thời gian |
| Unknown retention được chốt | Có giá trị cụ thể, ví dụ 1 đến 7 ngày |


PHASE 1 — WEB DEMO ĐẾM NGƯỜI BẰNG TRACKING VÀ LINE CROSSING

Mục tiêu:

Chứng minh hệ thống có thể detect người, tracking và xác định vào/ra bằng server AI.

Chức năng cần có:

- Nhận input video.
- Gửi video/frame về server xử lý.
- Detect person.
- Tracking person.
- Vẽ line vào/ra.
- Tạo ENTRY/EXIT event.
- Dashboard hiển thị realtime.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Input video hoạt động | Web đọc được webcam hoặc video upload |
| Server nhận video | AI server nhận và xử lý được frame/video |
| Line crossing hoạt động | Người đi qua line tạo event đúng hướng |
| Không đếm theo frame | Một người đứng trước camera không bị đếm nhiều lần |
| Dashboard cập nhật | Lượt vào/ra thay đổi khi có event |
| Occupancy không âm | Số người hiện tại không giảm dưới 0 |
| Event log | Mỗi event có timestamp, camera_id, direction, track_id |


PHASE 2 — ĐĂNG KÝ VÀ NHẬN DIỆN NGƯỜI QUEN

Mục tiêu:

Cho phép đăng ký người quen và nhận diện họ bằng server AI.

Chức năng cần có:

- Tạo hồ sơ người quen.
- Upload ảnh đăng ký.
- Server kiểm tra chất lượng ảnh.
- Server tạo embedding.
- Lưu embedding vào pgvector.
- Nhận diện người quen trong video.
- Tạo session cho người quen.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Tạo hồ sơ người quen | Admin tạo được person profile |
| Upload ảnh | Admin upload được nhiều ảnh cho một người |
| Server tạo embedding | Ảnh hợp lệ được trích xuất embedding |
| Kiểm tra ảnh lỗi | Ảnh mờ, tối, không có mặt hoặc nhiều mặt bị từ chối |
| Active người quen | Người có đủ mẫu hợp lệ chuyển sang active |
| Nhận diện đúng | Người đã đăng ký được gán đúng person_id trong test |
| Session người quen | Người quen vào-ra tạo session đúng |
| Vào lại sau khi ra | Tạo session mới, không ghi đè session cũ |


PHASE 3 — NHẬN DIỆN VÀ TÁI ĐỊNH DANH NGƯỜI LẠ

Mục tiêu:

Gán unknown_id cho người lạ và nhận ra cùng người lạ khi họ quay lại.

Chức năng cần có:

- Nếu không match known thì chuyển sang unknown matching.
- Nếu match unknown cũ thì dùng lại unknown_id.
- Nếu không match thì tạo unknown_id mới.
- Tạo nhiều session cho cùng unknown_id.
- Tự động xóa/vô hiệu hóa unknown embedding sau thời gian lưu.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Người lạ mới | Tạo được UNKNOWN_001 |
| Người lạ vào-ra | Tạo session cho UNKNOWN_001 |
| Người lạ quay lại | Nếu đủ giống, dùng lại UNKNOWN_001 |
| Người lạ có nhiều session | UNKNOWN_001 có session 1, session 2 |
| Không lưu ảnh gốc | Database không lưu snapshot khuôn mặt |
| Có retention | Unknown embedding hết hạn được xóa/vô hiệu hóa |
| Dashboard phân loại | Hiển thị known và unknown riêng biệt |


PHASE 4 — DASHBOARD, BÁO CÁO VÀ REVIEW LỖI

Mục tiêu:

Hoàn thiện dashboard vận hành và báo cáo thống kê.

Chức năng cần có:

- Dashboard realtime.
- Lịch sử session.
- Lịch sử event.
- Bộ lọc theo ngày, người, known/unknown, camera.
- Biểu đồ lượt vào/ra theo giờ.
- Export CSV/Excel.
- Danh sách unmatched events.
- Review/correct event nếu cần.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Dashboard realtime | Event mới xuất hiện trên dashboard trong vài giây |
| Lịch sử session | Xem được entry_at, exit_at, duration |
| Lọc dữ liệu | Lọc đúng theo ngày, người, camera, identity type |
| Biểu đồ theo giờ | Hiển thị lưu lượng theo từng khung giờ |
| Export CSV/Excel | File xuất ra có dữ liệu đúng |
| Review lỗi | Admin xem được unmatched exit hoặc low-confidence event |
| AI server status | Dashboard hiển thị trạng thái AI server |


PHASE 5 — HỖ TRỢ NHIỀU CAMERA/NHIỀU CỔNG

Mục tiêu:

Mở rộng hệ thống cho thư viện lớn có nhiều đường ra/vào.

Chức năng cần có:

- Quản lý nhiều camera.
- Mỗi camera gửi stream về server.
- Mỗi camera gắn với một gate.
- Mỗi gate có line/zone riêng.
- Session có thể vào ở cổng A, ra ở cổng B.
- Dashboard tổng hợp toàn thư viện.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Thêm nhiều camera | Hệ thống quản lý được nhiều camera |
| Server xử lý nhiều stream | AI server xử lý được nhiều camera theo cấu hình |
| Mỗi camera có config riêng | Line/ROI/debounce riêng từng camera |
| Vào cổng A, ra cổng B | Session vẫn đóng đúng |
| Dashboard tổng hợp | Occupancy tính toàn thư viện |
| Lọc theo gate | Xem được dữ liệu từng cổng |
| Camera offline | Hệ thống cảnh báo camera mất kết nối |


PHASE 6 — PRODUCTION VỚI CAMERA THẬT VÀ SERVER AI

Mục tiêu:

Triển khai hệ thống với camera giám sát thật, camera gửi RTSP/ONVIF về server AI.

Chức năng cần có:

- Kết nối camera thật qua RTSP.
- AI server đọc stream.
- AI server xử lý detect, tracking, face recognition.
- Server gửi event về backend.
- Backend lưu database.
- Dashboard realtime.
- Tự reconnect khi mất stream.
- Log lỗi camera và AI server.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Kết nối camera thật | Server đọc được RTSP stream |
| Camera không xử lý AI | Camera chỉ gửi video |
| Hệ thống chạy liên tục | Chạy ổn định trong thời gian test tối thiểu |
| Tự reconnect | Mất stream thì tự kết nối lại |
| Event production | Người ra/vào tạo event như demo |
| Latency đạt yêu cầu | Event xuất hiện trên dashboard trong ngưỡng cho phép |
| Có log lỗi | Lưu được lỗi stream, AI, database |
| Có tài liệu triển khai | Ghi rõ cách cấu hình camera, server, backend |


PHASE 7 — ĐÁNH GIÁ, TỐI ƯU VÀ NGHIỆM THU

Mục tiêu:

Đánh giá độ chính xác thực tế và hoàn thiện hệ thống trước khi bàn giao.

Công việc:

- Test nhiều điều kiện ánh sáng.
- Test nhiều người đi cùng lúc.
- Test người quen vào-ra nhiều phiên.
- Test người lạ vào-ra nhiều phiên.
- Test người vào cổng A, ra cổng B.
- Test trường hợp không thấy mặt.
- Test camera mất kết nối.
- Đánh giá accuracy, FPS, latency.
- Ghi nhận các case sai để cải thiện.

Acceptance criteria:

| Tiêu chí | Đạt khi |
|----------|---------|
| Test known visitor | Người quen được nhận diện đúng trong điều kiện test |
| Test unknown visitor | Người lạ được tạo unknown_id |
| Test nhiều session | Một người có nhiều session đúng |
| Test line crossing | Không đếm trùng khi đứng gần line |
| Test nhiều người | Hệ thống xử lý được nhiều người đi qua |
| Test lỗi camera | Camera offline được cảnh báo |
| Báo cáo đánh giá | Có bảng kết quả accuracy, FPS, latency |
| Nghiệm thu | Các tiêu chí MVP/production được xác nhận đạt |


16. CẤU HÌNH HỆ THỐNG ĐỀ XUẤT

person_detection_confidence = cấu hình sau khi test
face_detection_confidence = cấu hình sau khi test
known_recognition_threshold = cấu hình sau khi test
unknown_recognition_threshold = cấu hình sau khi test
line_crossing_debounce_seconds = 5 đến 10 giây
track_lost_timeout_seconds = 2 đến 5 giây
unknown_retention_days = 1 đến 7 ngày
session_timeout_hours = 8 đến 12 giờ
min_face_quality_score = cấu hình sau khi test
video_fps_processing_mvp = 10 đến 15 FPS
video_fps_processing_production = 20 đến 30 FPS nếu server đáp ứng

Không nên cố định threshold ngay từ đầu. Threshold phải được chọn sau khi test với dữ liệu thật tại thư viện.


17. ENROLLMENT NGƯỜI QUEN

17.1. Số lượng mẫu

Đề xuất:

- MVP: 5 đến 8 ảnh hợp lệ cho mỗi người.
- Production: 10 đến 20 frame chất lượng tốt lấy từ video ngắn.

17.2. Yêu cầu ảnh hợp lệ

Ảnh hợp lệ cần đáp ứng:

- Chỉ có một khuôn mặt.
- Mặt rõ, không mờ.
- Mặt đủ lớn.
- Ánh sáng đủ tốt.
- Không ngược sáng nặng.
- Không che mặt.
- Không đeo khẩu trang.
- Không đeo kính đen.
- Không quay nghiêng quá lớn.

17.3. Luồng đăng ký

Admin tạo hồ sơ
        ↓
Upload ảnh hoặc capture từ camera
        ↓
Server kiểm tra chất lượng ảnh
        ↓
Detect face
        ↓
Align face
        ↓
Extract embedding
        ↓
Kiểm tra trùng với database
        ↓
Lưu embedding
        ↓
Test nhận diện
        ↓
Active hồ sơ


18. LUỒNG XỬ LÝ CHÍNH

18.1. Luồng người quen đi vào

Camera gửi video về server
        ↓
Server detect người
        ↓
Tracking người
        ↓
Người crossing line theo hướng vào
        ↓
Detect face
        ↓
Extract embedding
        ↓
Match known database
        ↓
Gán person_id
        ↓
Nếu chưa có active session thì tạo session mới
        ↓
Dashboard cập nhật lượt vào

18.2. Luồng người quen đi ra

Camera gửi video về server
        ↓
Server tracking người
        ↓
Người crossing line theo hướng ra
        ↓
Face recognition
        ↓
Gán person_id
        ↓
Tìm active session
        ↓
Nếu có thì đóng session
        ↓
Cập nhật exit_at và duration
        ↓
Dashboard cập nhật lượt ra

18.3. Luồng người lạ

Camera gửi video về server
        ↓
Server detect và tracking người
        ↓
Người crossing line
        ↓
Detect face
        ↓
Extract embedding
        ↓
Không match known database
        ↓
So sánh unknown database
        ↓
Match unknown cũ hoặc tạo unknown mới
        ↓
Tạo/đóng session theo hướng vào/ra
        ↓
Dashboard cập nhật unknown statistics


19. QUY TẮC XỬ LÝ LỖI

| Lỗi | Cách xử lý |
|-----|------------|
| Không thấy mặt | Dùng tracking để tạo event, đánh dấu confidence thấp |
| Không match được identity | Gán UNRESOLVED hoặc UNKNOWN tạm |
| Người ra nhưng không có session vào | Tạo unmatched_exit_event |
| Người vào nhưng chưa ra quá lâu | Đánh dấu session timeout để admin review |
| Camera mất kết nối | Hiển thị offline, tự reconnect |
| AI server lỗi | Hiển thị AI server offline/error |
| Database lỗi | Queue event tạm thời nếu có thể |
| RTSP stream lỗi | Ghi log và retry kết nối |
| Ảnh đăng ký không hợp lệ | Từ chối và yêu cầu ảnh khác |


20. BẢO MẬT VÀ QUYỀN RIÊNG TƯ

Hệ thống xử lý face embedding, đây là dữ liệu sinh trắc học nhạy cảm. Vì vậy cần có các yêu cầu sau:

- Không lưu ảnh gốc nếu không cần thiết.
- Không lưu snapshot người lạ mặc định.
- Chỉ lưu embedding và log thời gian.
- Phân quyền truy cập theo vai trò.
- Admin mới được quản lý người quen.
- Staff chỉ được xem dashboard và báo cáo cần thiết.
- Có audit log cho thao tác xem, sửa, xóa, export dữ liệu.
- Có cơ chế xóa dữ liệu người quen khi không còn sử dụng.
- Có cơ chế tự động xóa/vô hiệu hóa unknown embedding sau thời gian cấu hình.
- Có thông báo tại khu vực camera rằng hệ thống sử dụng camera và nhận diện khuôn mặt cho mục đích thống kê ra/vào thư viện.
- Không sử dụng dữ liệu khuôn mặt cho mục đích khác ngoài phạm vi hệ thống.


21. TIÊU CHÍ THÀNH CÔNG TỔNG THỂ

Hệ thống được xem là hoàn thiện ở mức MVP khi:

- Có thể chạy demo web.
- Có thể nhận video từ webcam hoặc video upload.
- Video được gửi lên server để xử lý AI.
- Có thể vẽ line vào/ra.
- Server detect và tracking được người.
- Server tạo event ENTRY/EXIT.
- Có thể đăng ký người quen.
- Server trích xuất embedding khuôn mặt.
- Có thể nhận diện người quen.
- Có thể tạo unknown_id cho người lạ.
- Có thể quản lý nhiều phiên của cùng một người.
- Có dashboard realtime.
- Có lịch sử session.
- Có export báo cáo.

Hệ thống được xem là sẵn sàng production khi:

- Kết nối được camera thật qua RTSP/ONVIF.
- Camera chỉ gửi video, không xử lý AI.
- Server xử lý được video stream ổn định.
- Hệ thống chạy ổn định trong môi trường thư viện thật.
- Xử lý được nhiều người đi qua.
- Có cơ chế chống đếm trùng.
- Có log lỗi camera, stream và AI server.
- Có cơ chế reconnect camera.
- Có chính sách lưu trữ dữ liệu sinh trắc.
- Có báo cáo đánh giá accuracy, FPS, latency.
- Có tài liệu triển khai và vận hành.


22. CÁC QUYẾT ĐỊNH ĐÃ CHỐT

| Vấn đề | Quyết định |
|--------|------------|
| Xử lý AI ở đâu | Xử lý trên server |
| Camera có cần NPU/GPU không | Không |
| Có nạp code vào camera không | Không trong phương án chính |
| Camera production cần gì | Hỗ trợ RTSP/ONVIF |
| Demo web xử lý ở đâu | Backend/server xử lý AI |
| Có lưu ảnh gốc không | Không mặc định |
| Có lưu embedding không | Có |
| Người lạ lưu bao lâu | 1 đến 7 ngày, cấu hình được |
| Một người vào lại sau khi ra | Tạo session mới |
| Người quen đang active mà bị detect lại | Không tạo session mới |
| Thư viện nhiều cổng | Mỗi cổng có camera riêng, cùng gửi về server |
| Session vào cổng A, ra cổng B | Phải hỗ trợ |
| Công nghệ backend | Python FastAPI |
| Công nghệ database | PostgreSQL + pgvector |
| Công nghệ tracking | ByteTrack hoặc BoT-SORT |
| Công nghệ face embedding | InsightFace hoặc model tương đương |
| Công nghệ person detection | YOLO11/YOLOv8 |
| Realtime dashboard | WebSocket |


23. GỢI Ý CẤU TRÚC MÀN HÌNH WEB

23.1. Dashboard

- Live camera view.
- Occupancy hiện tại.
- Tổng lượt vào hôm nay.
- Tổng lượt ra hôm nay.
- Known visitors hôm nay.
- Unknown visitors hôm nay.
- Event log realtime.
- Camera status.
- AI server status.

23.2. Camera management

- Danh sách camera.
- Thêm/sửa/xóa camera.
- Test RTSP connection.
- Vẽ line vào/ra.
- Cấu hình ROI.
- Cấu hình debounce.
- Xem trạng thái stream.

23.3. Person management

- Danh sách người quen.
- Thêm người.
- Upload ảnh.
- Xem trạng thái enrollment.
- Disable/xóa người.
- Thêm lại mẫu khuôn mặt.

23.4. Unknown management

- Danh sách unknown_id.
- Số lần vào/ra.
- First seen.
- Last seen.
- Expire time.
- Trạng thái active/expired.

23.5. Session history

- Bảng session.
- Filter theo ngày.
- Filter theo người.
- Filter known/unknown.
- Filter camera/gate.
- Export CSV/Excel.

23.6. Review events

- Unmatched exit.
- Low-confidence event.
- Duplicate event.
- Session timeout.
- Camera offline event.
- AI server error event.