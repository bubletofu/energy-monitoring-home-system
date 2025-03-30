
# Tính năng

- **API Backend (FastAPI)**: Xử lý yêu cầu từ thiết bị IoT và ứng dụng front-end
- **Tích hợp Adafruit IO**: Đồng bộ dữ liệu và lấy dữ liệu về database
- **Nén Dữ liệu IDEALEM**: Giảm dung lượng lưu trữ cần thiết mà vẫn giữ được chất lượng dữ liệu
- **Công cụ giải nén**: Script riêng dành cho AI developer để phục hồi dữ liệu gốc từ dữ liệu nén

## Cài đặt và Sử dụng

### Sử dụng Docker (Khuyến nghị)

1. Cài đặt Docker và Docker Compose
2. Sao chép file `.env.example` thành `.env` và cập nhật thông tin kết nối
3. Chạy hệ thống:
```
docker-compose up -d
```

4. Khởi chạy ứng dụng:
```
uvicorn main:app --reload
```

## Lấy dữ liệu từ Adafruit theo ngày cụ thể

  

Chọn một ngày để lấy dữ liệu từ Adafruit và lưu vào database.

  

### Lệnh cơ bản:

```
python fetch_adafruit_data_manual.py
```

Mặc định sẽ lấy dữ liệu của ngày hiện tại.

  

### Lấy dữ liệu theo ngày cụ thể:

```
python fetch_adafruit_data_manual.py --date 2023-03-30
```

  

### Giới hạn số lượng bản ghi:

```
python fetch_adafruit_data_manual.py --date 2023-11-20 --limit 100
```

  

### Nếu gặp lỗi, thử ép buộc tải lại dữ liệu:

```
python fetch_adafruit_data_manual.py --date 2025-03-30 --force-reload
```

## Giải nén dữ liệu

Dành cho mấy bạn AI để giải nén và dùng để huấn luyện mô hình, có thể lưu dữ liệu dưới dạng csv, json.

Xem chi tiết cách sử dụng tại [README_DATA_DECOMPRESSION.md](./README_DATA_DECOMPRESSION.md).

Cấu trúc sử dụng cơ bản:
```
python decompress_data_for_ai.py --output data.json
python decompress_data_for_ai.py --format csv --output data.csv
```

## API Backend

### Chứng thực

1. Đăng ký tài khoản:
```
POST /register/
```

2. Đăng nhập:
```
POST /login/
```

### API Nén dữ liệu

1. Nén dữ liệu:
```
POST /compression/compress
```

2. Lấy dữ liệu đã nén:
```
GET /compression/compressed-data
```

3. Thống kê về nén:
```
GET /compression/stats
```
