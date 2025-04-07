
# Tính năng

- **API Backend (FastAPI)**: Xử lý yêu cầu từ thiết bị IoT và ứng dụng front-end
- **Tích hợp Adafruit IO**: Đồng bộ dữ liệu và lấy dữ liệu về database
- **Nén Dữ liệu IDEALEM**: Giảm dung lượng lưu trữ cần thiết, giữ thông tin quan trọng, loss compression
- **Công cụ giải nén**: Phục hồi dữ liệu gốc từ dữ liệu nén

## Cài đặt và Sử dụng

1. Cài đặt Docker và Docker Compose (Khuyến nghị & tuỳ chọn)
``` bash
brew install --cask docker
```
2. Tạo file `.env` 
``` bash
DATABASE_URL=postgresql://postgres:1234@localhost:5444/iot_db
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS = 7 

# config cho Adafruit IO
ADAFRUIT_IO_USERNAME=NguyenNgocDuy
ADAFRUIT_IO_KEY=
MQTT_HOST=io.adafruit.com
MQTT_PORT=8883 
MQTT_USERNAME=${ADAFRUIT_IO_USERNAME}
MQTT_PASSWORD=${ADAFRUIT_IO_KEY}
MQTT_TOPIC=${ADAFRUIT_IO_USERNAME}/feeds/#
MQTT_SSL=true  # Thêm flag để xác định có sử dụng SSL hay không

DB_HOST=localhost
DB_PORT=5444
DB_NAME=iot_db
DB_USER=postgres
DB_PASS=1234
```
3. Chạy hệ thống:

### Bật Docker Desktop

Tải app về máy:

```
https://www.docker.com/products/docker-desktop/
```

Chạy ứng dụng: 


``` bash
open -a Docker (Mac OS)
```

``` bash

Mở Docker Desktop từ Start Menu (chờ nó báo “Docker is running”). (Window)
```

   
#### Tạo môi trường ảo mới
```
python -m venv docker_env
```

#### Kích hoạt môi trường
```
source docker_env/bin/activate  # Trên macOS/Linux
docker_env\Scripts\activate # Trên Window
```


### Chạy PostgreSQL & App bằng Docker Compose

(Đảm bảo app Docker đã bật mỗi khi chạy lệnh docker compose) 

``` bash

docker compose up -d db
```


### Chạy file khởi tạo cơ sở dữ liệu

```
python setup_database.py
```


4. Khởi chạy ứng dụng (dành cho front end)
```
uvicorn main:app --reload
```

Ở đây cung cấp các tính năng cơ bản như login, claim device, remove device, đẩy feed lên adafruit, lấy danh sách feed từ adafruit, theo dõi thiết bị online/offline. 


### Khi gặp lỗi và cần reset database:

 Xóa toàn bộ container + volume

```
docker compose down -v
```

sau đó làm lại các bước thiết lập docker từ đầu.



### Kết nối với PostgreSQL từ bên ngoài

```
Host	localhost
Port	5444
User	postgres
Password	1234
Database	(Tùy tên bạn tạo)
```

## Lấy dữ liệu từ Adafruit theo ngày cụ thể

  

Chọn một ngày để lấy dữ liệu từ Adafruit và lưu vào database.

  

### Lệnh cơ bản:

```
python fetch.py
```

Mặc định sẽ lấy dữ liệu của ngày hiện tại.


### Tải tất cả

```
python fetch.py --all
```

## Công cụ nén và giải nén dữ liệu (Data Compression) 

Công cụ giải nén dữ liệu dùng để phục hồi dữ liệu gốc từ dữ liệu nén. Xem chi tiết cách sử dụng tại [README_DATA_DECOMPRESSION.md](./README_DATA_DECOMPRESSION.md).

Cấu trúc sử dụng cơ bản:
```
python decompress.py --device-id <name_device>
```

Output sẽ mặc định là <name_device>.json

``` bash
compress.py để sử dụng thuật toán trong file data_compress.py 
visualization_analyzer.py để tạo biểu đồ thông qua compress.py
```

## Tài liệu khác

A data compression algorithm was used, based on the research paper “Dynamic Online Performance Optimization in Streaming Data Compression.”
