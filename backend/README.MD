

Yêu cầu:
- Docker (https://docs.docker.com/get-docker/)
- Docker Compose (https://docs.docker.com/compose/install/)

Các bước thiết lập:

1. Clone repository:
   git clone https://github.com/bubletofu/energy-monitoring-home-system/tree/backend/backend
   cd your-repo

2. Khởi động môi trường Docker:
   docker-compose up -d

3. Truy cập Jupyter Notebook:
   - Mở trình duyệt và truy cập: http://localhost:8888
   - Để lấy token đăng nhập, chạy lệnh:
     docker-compose logs ai-notebook

CẤU TRÚC DỮ LIỆU
---------------

Database Schema:

1. devices: Thông tin về các thiết bị IoT
   - id: ID của thiết bị (primary key)
   - device_id: ID duy nhất của thiết bị (string)
   - name: Tên thiết bị
   - description: Mô tả thiết bị
   - created_at: Thời gian tạo thiết bị

2. sensor_data: Dữ liệu từ các cảm biến
   - id: ID của bản ghi (primary key)
   - device_id: ID của thiết bị (foreign key)
   - feed_id: ID của feed Adafruit IO
   - value: Giá trị đo được
   - timestamp: Thời gian ghi nhận dữ liệu

3. users: Thông tin người dùng
   - id: ID của người dùng (primary key)
   - username: Tên đăng nhập
   - email: Email
   - hashed_password: Mật khẩu đã được mã hóa

4. device_configs: Cấu hình thiết bị
   - id: ID của cấu hình (primary key)
   - user_id: ID của người dùng (foreign key)
   - device_name: Tên thiết bị
   - config_data: Dữ liệu cấu hình (JSON)

Dữ liệu mẫu:
- 3 thiết bị: Temperature Sensor, Humidity Sensor, Light Sensor
- Dữ liệu cảm biến trong 7 ngày gần đây
- 1 tài khoản người dùng mẫu

KẾT NỐI ĐẾN DATABASE
-------------------

Trong Jupyter Notebook, bạn có thể kết nối đến database bằng đoạn code sau:

import pandas as pd
from sqlalchemy import create_engine

# Kết nối đến database
engine = create_engine('postgresql://ai_user:1234@db:5432/iot_db')

# Truy vấn dữ liệu
df = pd.read_sql("SELECT * FROM sensor_data LIMIT 10", engine)
print(df.head())

VÍ DỤ PHÂN TÍCH DỮ LIỆU
----------------------

1. Truy vấn dữ liệu cảm biến:

import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns

# Kết nối đến database
engine = create_engine('postgresql://ai_user:1234@db:5432/iot_db')

# Truy vấn dữ liệu nhiệt độ
query = """
SELECT timestamp, value 
FROM sensor_data 
JOIN devices ON sensor_data.device_id = devices.device_id
WHERE devices.name = 'Temperature Sensor'
ORDER BY timestamp
"""
temp_data = pd.read_sql(query, engine)

# Chuyển đổi timestamp thành datetime
temp_data['timestamp'] = pd.to_datetime(temp_data['timestamp'])

# Vẽ biểu đồ
plt.figure(figsize=(12, 6))
plt.plot(temp_data['timestamp'], temp_data['value'])
plt.title('Temperature over time')
plt.xlabel('Time')
plt.ylabel('Temperature (°C)')
plt.grid(True)
plt.tight_layout()
plt.show()
