
# Tính năng

- **Tích hợp Adafruit IO**: Đồng bộ dữ liệu và lấy dữ liệu về database
- **Nén Dữ liệu IDEALEM**: Giảm dung lượng lưu trữ cần thiết mà vẫn giữ được chất lượng dữ liệu
- **Công cụ giải nén**: Script riêng dành cho AI developer để phục hồi dữ liệu gốc từ dữ liệu nén

## Cài đặt và Sử dụng

### Sử dụng Docker (Khuyến nghị)

1. Cài đặt Docker và Docker Compose
2. cd backend
3. Sao chép file `.env.example` thành `.env` và cập nhật thông tin kết nối
4. Chạy hệ thống:
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
## Công cụ giải nén dữ liệu

Công cụ giải nén dữ liệu IDEALEM được cung cấp cho các bạn AI để phục hồi dữ liệu gốc từ dữ liệu nén. Xem chi tiết cách sử dụng tại [README_DATA_DECOMPRESSION.md](./README_DATA_DECOMPRESSION.md).

Cấu trúc sử dụng cơ bản:

```
python decompress_data_for_ai.py --output data.json
python decompress_data_for_ai.py --format csv --output data.csv
```

