# Giải nén dữ liệu IDEALEM


Script `decompress_data_for_ai.py` kết nối đến PostgreSQL database, trích xuất dữ liệu nén từ bảng `compressed_data` và các mẫu gốc từ bảng `original_samples`, sau đó tái tạo dữ liệu đầy đủ với tất cả các thông số cảm biến.


## Sử dụng

### Sử dụng cơ bản

```bash
python decompress_data_for_ai.py --output data.json
```

Lệnh này sẽ giải nén tất cả dữ liệu nén và lưu kết quả vào file `data.json`.

### Tham số

- `--output`: (Bắt buộc) Đường dẫn file đầu ra
- `--start-date`: (Tùy chọn) Ngày bắt đầu để lọc dữ liệu (định dạng YYYY-MM-DD)
- `--end-date`: (Tùy chọn) Ngày kết thúc để lọc dữ liệu (định dạng YYYY-MM-DD)
- `--debug`: (Tùy chọn) Bật chế độ debug để hiển thị thông tin chi tiết
- `--format`: (Tùy chọn) Định dạng file đầu ra, hỗ trợ `json` hoặc `csv` (mặc định: `json`)
- `--csv-output`: (Tùy chọn) Đường dẫn file CSV đầu ra (chỉ khi `--format=csv`)

### Ví dụ

1. Lấy dữ liệu trong một khoảng thời gian:

```bash
python decompress_data_for_ai.py --output data.json --start-date 2025-03-01 --end-date 2025-03-31
```

2. Bật chế độ debug:

```bash
python decompress_data_for_ai.py --output data.json --debug
```

3. Xuất dữ liệu dạng CSV:

```bash
python decompress_data_for_ai.py --output data.csv --format csv
```

4. Xuất dữ liệu dạng CSV với tên file khác:

```bash
python decompress_data_for_ai.py --output data.json --format csv --csv-output sensor_data.csv
```

## Cấu trúc dữ liệu đầu ra

File JSON đầu ra chứa một mảng các đối tượng với cấu trúc sau:

```json
[
  {
    "device_id": "sensor_01",
    "timestamp": "2025-03-31T02:11:01.202996",
    "readings": {
      "temperature": 22.062,
      "humidity": 68.407,
      "pressure": 1013.713,
      "power": 10.123,
      "battery": 98
    }
  },
  ...
]
```

Mỗi đối tượng bao gồm:
- `device_id`: ID của thiết bị
- `timestamp`: Thời gian ghi nhận dữ liệu
- `readings`: Các thông số cảm biến, bao gồm:
  - `temperature`: Nhiệt độ (°C)
  - `humidity`: Độ ẩm (%)
  - `pressure`: Áp suất (hPa)
  - `power`: Công suất (W)
  - `battery`: Dung lượng pin (%)

## Xử lý dữ liệu với Python

Bạn có thể dễ dàng đọc và xử lý dữ liệu JSON đầu ra bằng Python:

```python
import json
import pandas as pd

# Đọc dữ liệu từ file JSON
with open('data.json', 'r') as f:
    data = json.load(f)

# Chuyển đổi sang DataFrame
rows = []
for item in data:
    row = {
        'device_id': item['device_id'],
        'timestamp': item['timestamp']
    }
    # Thêm các thông số readings
    if 'readings' in item:
        for key, value in item['readings'].items():
            row[key] = value
    rows.append(row)

# Tạo DataFrame
df = pd.DataFrame(rows)

# Chuyển timestamp sang định dạng datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Bây giờ bạn có thể phân tích dữ liệu
print(df.describe())
```

## Xử lý sự cố

Nếu bạn gặp vấn đề khi chạy script, hãy thử các bước sau:

1. Bật chế độ debug để xem thông tin chi tiết:
   ```bash
   python decompress_data_for_ai.py --output data.json --debug
   ```

2. Kiểm tra kết nối database:
   ```bash
   psql -U postgres -d iot_db -h localhost -p 5433 -c "SELECT COUNT(*) FROM compressed_data;"
   ```

3. Kiểm tra cấu trúc bảng trong database:
   ```bash
   psql -U postgres -d iot_db -h localhost -p 5433 -c "\d+ compressed_data"
   psql -U postgres -d iot_db -h localhost -p 5433 -c "\d+ original_samples"
   ```

## Lưu ý

- Script này tự động tái tạo dữ liệu cảm biến từ templates được lưu trong database.
- Quá trình giải nén hoạt động tốt nhất khi cả hai bảng `compressed_data` và `original_samples` đều có đầy đủ dữ liệu.
- Thời gian xử lý có thể tăng lên nếu lượng dữ liệu lớn, hãy sử dụng tham số `--start-date` và `--end-date` để lọc dữ liệu trong khoảng thời gian cụ thể. 
