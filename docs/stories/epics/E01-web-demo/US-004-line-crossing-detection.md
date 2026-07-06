# US-004 Virtual Line Configuration and Line Crossing Detection

## Status

implemented

## Lane

normal

## Product Contract

Thiết lập cấu hình đường vạch ảo (virtual line) trên từng camera và phát triển thuật toán hình học xác định sự kiện cắt vạch ảo (Line Crossing Detection) dựa trên quỹ đạo di chuyển của đối tượng được theo vết để phân loại hướng di chuyển thành lượt vào (ENTRY) hoặc lượt ra (EXIT).

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`
- `docs/product/data-model.md`

## Acceptance Criteria

- [x] Cung cấp các hàm hình học phụ trợ trong `app/geometry.py` để xác định giao điểm giữa 2 đoạn thẳng và hướng cắt vạch ảo (sử dụng tích vô hướng/tích có hướng vector).
- [x] Theo dõi vị trí điểm trung tâm cạnh dưới (bottom center) của bounding box đối tượng qua các khung hình để làm điểm tham chiếu cắt vạch ảo.
- [x] Tích hợp bộ phát hiện cắt vạch ảo vào quy trình xử lý frame của camera, tự động sinh ra các sự kiện ENTRY hoặc EXIT tương ứng.
- [x] Có script kiểm định tự động (verify script) chạy mô phỏng quỹ đạo di chuyển của một đối tượng đi qua một vạch ảo mẫu và xác định đúng sự kiện cắt vạch (bao gồm cả hướng di chuyển).

## Design Notes

- **Line Crossing Geometry**:
  - Vạch ảo được định nghĩa bởi hai điểm: $A(x_1, y_1)$ và $B(x_2, y_2)$.
  - Điểm di chuyển của người là $P(t)$ tại thời điểm $t$. Quỹ đạo di chuyển được tạo bởi đoạn thẳng nối từ vị trí trước đó $P(t-1)$ tới vị trí hiện tại $P(t)$.
  - Phép giao cắt được xác định khi đoạn thẳng $P(t-1)P(t)$ cắt đoạn thẳng $AB$.
  - Hướng cắt vạch (ENTRY/EXIT) được xác định bằng dấu của tích có hướng giữa vector vạch ảo $\vec{AB}$ và vector di chuyển $\vec{P(t-1)P(t)}$.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Chạy thử nghiệm các hàm hình học cắt vạch với các điểm tọa độ mẫu |
| Integration | API nhận các frame liên tiếp mô phỏng một người đi qua vạch và sinh ra sự kiện tương ứng |
| E2E | N/A |
| Platform | Chạy thành công trên Windows |
| Release | N/A |

## Harness Delta

- Không có.

## Evidence

- Chạy kiểm định `.\scripts\bin\harness-cli.exe story verify US-004` thành công:
  ```text
  Running: python scripts/validate_crossing.py
  Starting validation test for line crossing...
  Geometry unit tests passed successfully.
  Launching FastAPI server...
  Server is ready and healthy!
  Sending Frame 1 (Person above line)...
  Frame 1 Response: {'session_id': 'session_1783328293', 'tracks': [{'track_id': 1, 'bbox': [100.0, 50.0, 200.0, 250.0], 'confidence': 0.9}], 'crossing_events': []}
  Sending Frame 2 (Person below line)...
  Frame 2 Response: {'session_id': 'session_1783328293', 'tracks': [{'track_id': 1, 'bbox': [100.0, 110.0, 200.0, 310.0], 'confidence': 0.9}], 'crossing_events': [{'track_id': 1, 'direction': 'ENTRY', 'timestamp': 1783328297.6427896}]}
  Line crossing integration tests PASSED successfully!
  Terminating server...
  Story US-004 verification: pass
  ```

