#!/usr/bin/env python
import requests
import json
import time
import logging
import sys
import random
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('adafruit_test_full.log')
    ]
)
logger = logging.getLogger(__name__)

# URL của FastAPI server
BASE_URL = "http://127.0.0.1:8000"

class AdafruitTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.access_token = None
        self.username = f"testuser_{int(time.time())}"  # Tạo username ngẫu nhiên với timestamp
        self.password = "password123"
        self.email = f"{self.username}@example.com"
        self.device_id = f"test_device_{int(time.time())}"
        self.test_feed_id = "test"
        
    def check_server_status(self):
        """
        Kiểm tra xem server FastAPI có hoạt động không
        """
        try:
            logger.info("=== KIỂM TRA TRẠNG THÁI SERVER ===")
            response = requests.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                logger.info(f"✅ Server hoạt động: {response.json()}")
                return True
            else:
                logger.error(f"❌ Server phản hồi bất thường: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Không thể kết nối đến server: {str(e)}")
            logger.error("⚠️ Đảm bảo server đang chạy với lệnh: uvicorn main:app --reload")
            return False
            
    def register_user(self):
        """
        Đăng ký người dùng mới
        """
        try:
            logger.info("\n=== ĐĂNG KÝ NGƯỜI DÙNG MỚI ===")
            
            register_url = f"{self.base_url}/register/"
            user_data = {
                "username": self.username,
                "email": self.email,
                "password": self.password
            }
            
            logger.info(f"Đăng ký người dùng: {self.username}")
            response = requests.post(register_url, json=user_data)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Đăng ký thành công: {result}")
                return True
            else:
                logger.error(f"❌ Đăng ký thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi đăng ký: {str(e)}")
            return False
            
    def login(self):
        """
        Đăng nhập và lấy token xác thực
        """
        try:
            logger.info("\n=== ĐĂNG NHẬP HỆ THỐNG ===")
            
            login_url = f"{self.base_url}/login/"
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            logger.info(f"Đăng nhập với tài khoản: {self.username}")
            response = requests.post(login_url, data=login_data)
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result["access_token"]
                logger.info(f"✅ Đăng nhập thành công, đã nhận access token")
                return True
            else:
                logger.error(f"❌ Đăng nhập thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi đăng nhập: {str(e)}")
            return False
    
    def test_adafruit_direct_connection(self):
        """
        Kiểm tra kết nối trực tiếp đến Adafruit IO thông qua endpoint /publish
        """
        try:
            logger.info("\n=== KIỂM TRA KẾT NỐI TRỰC TIẾP ADAFRUIT IO ===")
            
            test_value = str(time.time())
            url = f"{self.base_url}/publish/{self.test_feed_id}/{test_value}"
            
            logger.info(f"Gửi dữ liệu đến feed {self.test_feed_id}: {test_value}")
            response = requests.get(url)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Gửi dữ liệu thành công: {result}")
                return True
            else:
                logger.error(f"❌ Gửi dữ liệu thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi kết nối Adafruit IO: {str(e)}")
            return False
            
    def create_device_config(self):
        """
        Tạo cấu hình thiết bị mới
        """
        try:
            logger.info("\n=== TẠO CẤU HÌNH THIẾT BỊ ===")
            
            if not self.access_token:
                logger.error("❌ Chưa có token xác thực, cần đăng nhập trước")
                return False
                
            url = f"{self.base_url}/device-config/"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            config_data = {
                "device_name": self.device_id,
                "config_data": {
                    "temperature": {
                        "min": 0,
                        "max": 40,
                        "unit": "°C",
                        "alert_threshold": 35
                    },
                    "humidity": {
                        "min": 0,
                        "max": 100,
                        "unit": "%",
                        "alert_threshold": 85
                    },
                    "pressure": {
                        "min": 900,
                        "max": 1100,
                        "unit": "hPa"
                    },
                    "sample_rate": 5,
                    "power_mode": "normal"
                }
            }
            
            logger.info(f"Tạo cấu hình cho thiết bị: {self.device_id}")
            response = requests.post(url, headers=headers, json=config_data)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Tạo cấu hình thiết bị thành công: {result}")
                return True
            else:
                logger.error(f"❌ Tạo cấu hình thiết bị thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi tạo cấu hình thiết bị: {str(e)}")
            return False
            
    def send_device_data(self):
        """
        Gửi dữ liệu thiết bị thông qua API
        """
        try:
            logger.info("\n=== GỬI DỮ LIỆU THIẾT BỊ QUA API ===")
            
            if not self.access_token:
                logger.error("❌ Chưa có token xác thực, cần đăng nhập trước")
                return False
                
            url = f"{self.base_url}/device-data/"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Tạo dữ liệu ngẫu nhiên
            data = {
                "device_id": self.device_id,
                "readings": {
                    "temperature": round(25 + random.uniform(-5, 5), 2),
                    "humidity": round(65 + random.uniform(-10, 10), 2),
                    "pressure": round(1013 + random.uniform(-5, 5), 2)
                }
            }
            
            logger.info(f"Gửi dữ liệu thiết bị: {json.dumps(data)}")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Gửi dữ liệu thiết bị thành công: {result}")
                return True
            else:
                logger.error(f"❌ Gửi dữ liệu thiết bị thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi gửi dữ liệu thiết bị: {str(e)}")
            return False
            
    def test_compression_api(self):
        """
        Kiểm tra API nén dữ liệu
        """
        try:
            logger.info("\n=== KIỂM TRA API NÉN DỮ LIỆU ===")
            
            if not self.access_token:
                logger.error("❌ Chưa có token xác thực, cần đăng nhập trước")
                return False
                
            url = f"{self.base_url}/compression/compress"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Tạo dữ liệu mẫu để nén
            current_time = datetime.now()
            data_points = []
            
            for i in range(5):
                timestamp = (current_time - timedelta(minutes=i*5)).isoformat()
                
                data_point = {
                    "device_id": self.device_id,
                    "timestamp": timestamp,
                    "readings": {
                        "temperature": round(25 + 0.1 * i + random.uniform(-0.5, 0.5), 3),
                        "humidity": round(65 - 0.2 * i + random.uniform(-1, 1), 3),
                        "pressure": round(1013 + 0.05 * i + random.uniform(-0.2, 0.2), 3),
                        "battery": random.randint(90, 100)
                    }
                }
                data_points.append(data_point)
            
            # Nén một điểm dữ liệu đầu tiên
            test_data = data_points[0]
            logger.info(f"Nén dữ liệu: {json.dumps(test_data)}")
            
            response = requests.post(url, headers=headers, json=test_data)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Nén dữ liệu thành công:")
                logger.info(f"   - Dữ liệu nén: {json.dumps(result['compressed_data'])}")
                logger.info(f"   - Tỷ lệ nén: {result['statistics']['compression_ratio']:.4f}")
                logger.info(f"   - Phương pháp nén: {result.get('compression_method', 'không xác định')}")
                
                # Kiểm tra xem dữ liệu đã được lưu vào database chưa
                if result.get('saved_to_database'):
                    logger.info(f"✅ Dữ liệu đã được lưu vào database với ID: {result.get('saved_id')}")
                    
                    # Kiểm tra API lấy dữ liệu nén từ database
                    if self.test_get_compressed_data():
                        logger.info("✅ Kiểm tra lấy dữ liệu nén từ database thành công")
                    else:
                        logger.error("❌ Kiểm tra lấy dữ liệu nén từ database thất bại")
                else:
                    logger.warning("⚠️ Dữ liệu KHÔNG được lưu vào database")
                
                # Kiểm tra chuyển đổi phương pháp nén
                if self.test_compression_method_switch(headers, data_points[1]):
                    logger.info("✅ Kiểm tra chuyển đổi phương pháp nén thành công")
                else:
                    logger.error("❌ Kiểm tra chuyển đổi phương pháp nén thất bại")
                
                # Kiểm tra batch compress
                return self.test_batch_compression(data_points[2:], headers)
            else:
                logger.error(f"❌ Nén dữ liệu thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi nén dữ liệu: {str(e)}")
            return False
            
    def test_compression_method_switch(self, headers, test_data):
        """
        Kiểm tra chuyển đổi phương pháp nén
        """
        try:
            logger.info("\n=== KIỂM TRA CHUYỂN ĐỔI PHƯƠNG PHÁP NÉN ===")
            
            # 1. Đầu tiên, lấy phương pháp nén hiện tại
            url_stats = f"{self.base_url}/compression/stats"
            response_stats = requests.get(url_stats, headers=headers)
            
            if response_stats.status_code != 200:
                logger.error(f"❌ Không thể lấy thông tin phương pháp nén hiện tại: {response_stats.status_code}")
                return False
                
            current_method = response_stats.json().get("current_method", "idealem")
            logger.info(f"Phương pháp nén hiện tại: {current_method}")
            
            # 2. Chuyển đổi phương pháp nén sang phương pháp khác
            url_method = f"{self.base_url}/compression/method"
            new_method = "dynamic" if current_method == "idealem" else "idealem"
            
            logger.info(f"Chuyển đổi phương pháp nén từ {current_method} sang {new_method}")
            response_switch = requests.post(
                url_method, 
                headers=headers, 
                json={"method": new_method}
            )
            
            if response_switch.status_code != 200:
                logger.error(f"❌ Không thể chuyển đổi phương pháp nén: {response_switch.status_code}")
                return False
                
            switch_result = response_switch.json()
            logger.info(f"Kết quả chuyển đổi: {switch_result}")
            
            # 3. Kiểm tra nén với phương pháp mới
            url_compress = f"{self.base_url}/compression/compress"
            
            logger.info(f"Nén dữ liệu với phương pháp {new_method}")
            response_compress = requests.post(url_compress, headers=headers, json=test_data)
            
            if response_compress.status_code != 200:
                logger.error(f"❌ Nén dữ liệu với phương pháp mới thất bại: {response_compress.status_code}")
                return False
                
            compress_result = response_compress.json()
            if compress_result.get('compression_method') != new_method:
                logger.error(f"❌ Phương pháp nén không đúng: {compress_result.get('compression_method')} (kỳ vọng: {new_method})")
                return False
                
            logger.info(f"✅ Nén dữ liệu với phương pháp {new_method} thành công:")
            logger.info(f"   - Tỷ lệ nén: {compress_result['statistics']['compression_ratio']:.4f}")
            
            # 4. Chuyển lại phương pháp nén ban đầu
            logger.info(f"Chuyển đổi phương pháp nén trở lại {current_method}")
            requests.post(
                url_method, 
                headers=headers, 
                json={"method": current_method}
            )
            
            return True
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra chuyển đổi phương pháp nén: {str(e)}")
            return False
            
    def test_get_compressed_data(self):
        """
        Kiểm tra API lấy dữ liệu nén từ database
        """
        try:
            logger.info("\n=== KIỂM TRA LẤY DỮ LIỆU NÉN TỪ DATABASE ===")
            
            if not self.access_token:
                logger.error("❌ Chưa có token xác thực, cần đăng nhập trước")
                return False
                
            url = f"{self.base_url}/compression/compressed-data"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            params = {
                "skip": 0,
                "limit": 5  # Giới hạn để dễ đọc
            }
            
            logger.info("Lấy dữ liệu nén từ database")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if 'data' in result and isinstance(result['data'], list):
                    count = len(result['data'])
                    logger.info(f"✅ Lấy dữ liệu nén thành công: {count} bản ghi")
                    
                    # Hiển thị một số bản ghi đầu tiên
                    for i, item in enumerate(result['data'][:2]):
                        logger.info(f"   - Bản ghi {i+1}: ID={item['id']}, Device={item['device_id']}, " +
                                    f"Tỷ lệ nén={item['compression_ratio']:.4f}, " +
                                    f"Thời gian={item['timestamp']}")
                    
                    if count > 2:
                        logger.info(f"   - ... và {count-2} bản ghi khác")
                    
                    return True
                else:
                    logger.warning(f"⚠️ Dữ liệu trả về không đúng định dạng: {result}")
                    return False
            else:
                logger.error(f"❌ Lấy dữ liệu nén thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi lấy dữ liệu nén: {str(e)}")
            return False
            
    def test_batch_compression(self, data_points, headers):
        """
        Kiểm tra API nén dữ liệu hàng loạt
        """
        try:
            logger.info("\n=== KIỂM TRA NÉN DỮ LIỆU HÀNG LOẠT ===")
            
            url = f"{self.base_url}/compression/batch_compress"
            
            logger.info(f"Nén hàng loạt {len(data_points)} điểm dữ liệu")
            response = requests.post(url, headers=headers, json=data_points)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Nén hàng loạt thành công:")
                logger.info(f"   - Số điểm dữ liệu đã nén: {len(result['results'])}")
                logger.info(f"   - Tỷ lệ nén tổng thể: {result['overall_statistics']['overall_compression_ratio']:.4f}")
                
                # Kiểm tra xem dữ liệu đã được lưu vào database chưa
                if result.get('saved_to_database'):
                    logger.info(f"✅ Dữ liệu nén hàng loạt đã được lưu vào database")
                    if 'saved_ids' in result:
                        logger.info(f"   - Đã lưu {len(result['saved_ids'])} bản ghi với IDs: {result['saved_ids'][:3]}...")
                else:
                    logger.warning("⚠️ Dữ liệu nén hàng loạt KHÔNG được lưu vào database")
                
                # Kiểm tra cấu hình compressor
                return self.test_compressor_config(headers)
            else:
                logger.error(f"❌ Nén hàng loạt thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi nén hàng loạt: {str(e)}")
            return False
            
    def test_compressor_config(self, headers):
        """
        Kiểm tra API cấu hình compressor
        """
        try:
            logger.info("\n=== KIỂM TRA CẤU HÌNH COMPRESSOR ===")
            
            url = f"{self.base_url}/compression/config"
            
            # Cấu hình mới cho compressor
            config = {
                "compression_ratio": 0.6,
                "error_threshold": 0.03,
                "window_size": 100,
                "adaptation_rate": 0.2,
                "min_bandwidth": 15
            }
            
            logger.info(f"Cập nhật cấu hình compressor: {json.dumps(config)}")
            response = requests.post(url, headers=headers, json=config)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Cập nhật cấu hình compressor thành công: {result}")
                
                # Kiểm tra lấy thống kê
                return self.test_compression_stats(headers)
            else:
                logger.error(f"❌ Cập nhật cấu hình compressor thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi cập nhật cấu hình compressor: {str(e)}")
            return False
            
    def test_compression_stats(self, headers):
        """
        Kiểm tra API lấy thống kê về nén dữ liệu
        """
        try:
            logger.info("\n=== KIỂM TRA THỐNG KÊ NÉN DỮ LIỆU ===")
            
            url = f"{self.base_url}/compression/stats"
            
            logger.info("Lấy thống kê về nén dữ liệu")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Lấy thống kê nén dữ liệu thành công: {result}")
                
                # Reset compressor
                return self.test_reset_compressor(headers)
            else:
                logger.error(f"❌ Lấy thống kê nén dữ liệu thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi lấy thống kê nén dữ liệu: {str(e)}")
            return False
            
    def test_reset_compressor(self, headers):
        """
        Kiểm tra API reset compressor
        """
        try:
            logger.info("\n=== KIỂM TRA RESET COMPRESSOR ===")
            
            url = f"{self.base_url}/compression/reset"
            
            logger.info("Reset compressor")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Reset compressor thành công: {result}")
                return True
            else:
                logger.error(f"❌ Reset compressor thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi reset compressor: {str(e)}")
            return False
            
    def get_sensor_data(self):
        """
        Lấy dữ liệu cảm biến từ database
        """
        try:
            logger.info("\n=== LẤY DỮ LIỆU CẢM BIẾN ===")
            
            url = f"{self.base_url}/sensor-data/"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            params = {
                "skip": 0,
                "limit": 5  # Giới hạn để dễ đọc
            }
            
            logger.info("Lấy dữ liệu cảm biến từ database")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        count = len(data)
                        logger.info(f"✅ Lấy dữ liệu cảm biến thành công: {count} bản ghi")
                        
                        # Hiển thị một số bản ghi
                        for i, record in enumerate(data[:3]):
                            logger.info(f"   - Bản ghi {i+1}: {json.dumps(record)}")
                            
                        if count > 3:
                            logger.info(f"   - ... và {count-3} bản ghi khác")
                    else:
                        logger.warning(f"⚠️ Dữ liệu không ở dạng danh sách: {data}")
                    return True
                except Exception as e:
                    logger.error(f"❌ Lỗi xử lý dữ liệu JSON: {str(e)}")
                    return False
            else:
                logger.error(f"❌ Lấy dữ liệu cảm biến thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi lấy dữ liệu cảm biến: {str(e)}")
            return False
    
    def compare_compression_methods(self):
        """
        So sánh hiệu suất của các phương pháp nén khác nhau
        """
        try:
            logger.info("\n=== SO SÁNH PHƯƠNG PHÁP NÉN ===")
            
            if not self.access_token:
                logger.error("❌ Chưa có token xác thực, cần đăng nhập trước")
                return False
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Tạo dữ liệu mẫu có tính chu kỳ để test
            data_points = []
            current_time = datetime.now()
            
            # Tạo 20 điểm dữ liệu có dạng hình sin
            for i in range(20):
                # Tạo dữ liệu có tính chu kỳ
                import math
                angle = i * math.pi / 10  # Góc tính theo radian
                
                temperature = 25 + 5 * math.sin(angle)
                humidity = 65 + 10 * math.sin(angle + math.pi/4)
                pressure = 1013 + 3 * math.sin(angle + math.pi/2)
                
                timestamp = (current_time - timedelta(minutes=i*5)).isoformat()
                
                data_point = {
                    "device_id": self.device_id,
                    "timestamp": timestamp,
                    "readings": {
                        "temperature": round(temperature, 3),
                        "humidity": round(humidity, 3),
                        "pressure": round(pressure, 3),
                        "battery": random.randint(90, 100)
                    }
                }
                data_points.append(data_point)
            
            results = {}
            
            # Test với phương pháp Dynamic
            url_method = f"{self.base_url}/compression/method"
            requests.post(url_method, headers=headers, json={"method": "dynamic"})
            
            # Nén dữ liệu với phương pháp Dynamic
            url_batch = f"{self.base_url}/compression/batch_compress"
            response_dynamic = requests.post(url_batch, headers=headers, json=data_points)
            
            if response_dynamic.status_code == 200:
                dynamic_result = response_dynamic.json()
                dynamic_ratio = dynamic_result['overall_statistics'].get('overall_compression_ratio', 0)
                results['dynamic'] = dynamic_ratio
                logger.info(f"✅ Phương pháp Dynamic: Tỷ lệ nén = {dynamic_ratio:.4f}")
            else:
                logger.error(f"❌ Nén với phương pháp Dynamic thất bại: {response_dynamic.status_code}")
            
            # Test với phương pháp IDEALEM
            requests.post(url_method, headers=headers, json={"method": "idealem"})
            
            # Nén dữ liệu với phương pháp IDEALEM
            response_idealem = requests.post(url_batch, headers=headers, json=data_points)
            
            if response_idealem.status_code == 200:
                idealem_result = response_idealem.json()
                idealem_ratio = idealem_result['overall_statistics'].get('overall_compression_ratio', 0)
                results['idealem'] = idealem_ratio
                logger.info(f"✅ Phương pháp IDEALEM: Tỷ lệ nén = {idealem_ratio:.4f}")
            else:
                logger.error(f"❌ Nén với phương pháp IDEALEM thất bại: {response_idealem.status_code}")
            
            # So sánh kết quả
            if 'dynamic' in results and 'idealem' in results:
                if results['idealem'] < results['dynamic']:
                    improvement = (1 - results['idealem'] / results['dynamic']) * 100
                    logger.info(f"✅ IDEALEM hiệu quả hơn Dynamic {improvement:.2f}%")
                elif results['dynamic'] < results['idealem']:
                    improvement = (1 - results['dynamic'] / results['idealem']) * 100
                    logger.info(f"✅ Dynamic hiệu quả hơn IDEALEM {improvement:.2f}%")
                else:
                    logger.info("⚠️ Hai phương pháp có hiệu quả tương đương nhau")
                
                # Kiểm tra số lượng bản ghi trong database
                url_compressed_data = f"{self.base_url}/compression/compressed-data"
                response_data = requests.get(url_compressed_data, headers=headers)
                
                if response_data.status_code == 200:
                    data_result = response_data.json()
                    logger.info(f"✅ Số lượng bản ghi nén trong database: {data_result.get('total', 0)}")
                    
                return True
            else:
                logger.error("❌ Không thể so sánh các phương pháp nén do thiếu dữ liệu")
                return False
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi so sánh phương pháp nén: {str(e)}")
            return False
    
    def run_all_tests(self):
        """
        Chạy tất cả các bài kiểm tra
        """
        logger.info("\n========== BẮT ĐẦU KIỂM TRA TOÀN DIỆN ADAFRUIT IO VÀ BACKEND ==========")
        
        # Kiểm tra server status
        if not self.check_server_status():
            logger.error("❌ Không thể kết nối đến server. Đảm bảo server đang chạy và thử lại.")
            return False
            
        # Đăng ký người dùng mới
        if not self.register_user():
            logger.error("❌ Đăng ký thất bại. Sử dụng tài khoản đã có.")
            
        # Đăng nhập
        if not self.login():
            logger.error("❌ Đăng nhập thất bại, không thể tiếp tục các bài kiểm tra yêu cầu xác thực.")
            # Chỉ thực hiện kiểm tra kết nối trực tiếp
            self.test_adafruit_direct_connection()
            return False
            
        # Thực hiện các bài kiểm tra
        tests = [
            ("Kết nối trực tiếp Adafruit IO", self.test_adafruit_direct_connection),
            ("Tạo cấu hình thiết bị", self.create_device_config),
            ("Gửi dữ liệu thiết bị", self.send_device_data),
            ("API nén dữ liệu", self.test_compression_api),
            ("So sánh phương pháp nén", self.compare_compression_methods),
            ("Lấy dữ liệu cảm biến", self.get_sensor_data)
        ]
        
        results = {}
        for name, test_func in tests:
            logger.info(f"\n>> Đang thực hiện: {name}...")
            result = test_func()
            results[name] = result
            
            # Thêm một khoảng nghỉ ngắn giữa các bài kiểm tra
            time.sleep(1)
            
        # Tổng kết
        logger.info("\n\n========== KẾT QUẢ KIỂM TRA ==========")
        success_count = 0
        
        for name, result in results.items():
            status = "✅ THÀNH CÔNG" if result else "❌ THẤT BẠI"
            if result:
                success_count += 1
            logger.info(f"{status}: {name}")
            
        success_rate = (success_count / len(tests)) * 100
        logger.info(f"\nTỶ LỆ THÀNH CÔNG: {success_rate:.1f}% ({success_count}/{len(tests)})")
        
        if success_rate == 100:
            logger.info("\n🎉 CÁC TÍNH NĂNG HOẠT ĐỘNG TỐT!")
        elif success_rate >= 80:
            logger.info("\n✨ HẦU HẾT CÁC TÍNH NĂNG HOẠT ĐỘNG TỐT!")
        elif success_rate >= 50:
            logger.info("\n⚠️ MỘT SỐ TÍNH NĂNG CẦN KIỂM TRA LẠI!")
        else:
            logger.info("\n❌ NHIỀU TÍNH NĂNG KHÔNG HOẠT ĐỘNG ĐÚNG, CẦN KIỂM TRA KỸ LẠI!")
            
        logger.info("\n========== KẾT THÚC KIỂM TRA ==========")
        return success_rate >= 80

if __name__ == "__main__":
    try:
        tester = AdafruitTester()
        tester.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Đã hủy kiểm tra bởi người dùng!")
    except Exception as e:
        logger.error(f"\n\n❌ Lỗi không mong đợi: {str(e)}")
        import traceback
        traceback.print_exc() 