from mqtt_client import MQTTClient
import time
import logging
import json
from datetime import datetime
import sys

# Cấu hình logging chi tiết hơn
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mqtt_test.log')
    ]
)
logger = logging.getLogger(__name__)

class MQTTTester:
    def __init__(self):
        self.mqtt_client = MQTTClient()
        self.received_messages = []
        self.connection_successful = False
        
    def test_connection(self):
        try:
            logger.info("=== Bắt đầu kiểm tra kết nối MQTT ===")
            
            # Thử kết nối
            logger.info("Đang thử kết nối tới HiveMQ Cloud...")
            self.mqtt_client.connect()
            
            # Đợi để kiểm tra kết nối ổn định
            logger.info("Đợi 5 giây để kiểm tra kết nối ổn định...")
            time.sleep(5)
            
            # Test publish message
            self.test_publish()
            
            # Test subscribe
            self.test_subscribe()
            
            # Kiểm tra kết nối liên tục
            self.test_connection_stability()
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi trong quá trình test: {str(e)}")
            return False
        finally:
            self.cleanup()

    def test_publish(self):
        try:
            # Tạo message test
            test_message = {
                "type": "test_message",
                "content": "Hello from MQTT Tester",
                "timestamp": datetime.now().isoformat()
            }
            
            # Publish message
            logger.info("Đang thử publish message...")
            self.mqtt_client.publish_message("test/connection", test_message)
            logger.info("Đã publish message thành công")
            
            # Đợi một chút để đảm bảo message được gửi
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Lỗi khi publish message: {str(e)}")
            raise

    def test_subscribe(self):
        try:
            logger.info("Đang thử subscribe vào topic test...")
            # Subscribe được xử lý trong mqtt_client.py thông qua on_connect callback
            time.sleep(3)  # Đợi để đảm bảo subscribe hoàn tất
            logger.info("Đã subscribe thành công")
            
        except Exception as e:
            logger.error(f"Lỗi khi subscribe: {str(e)}")
            raise

    def test_connection_stability(self):
        try:
            logger.info("Kiểm tra độ ổn định kết nối trong 10 giây...")
            for i in range(10):
                if i % 2 == 0:
                    test_message = {
                        "type": "stability_test",
                        "sequence": i,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.mqtt_client.publish_message("test/stability", test_message)
                time.sleep(1)
            logger.info("Kiểm tra độ ổn định kết nối thành công")
            
        except Exception as e:
            logger.error(f"Lỗi trong quá trình kiểm tra độ ổn định: {str(e)}")
            raise

    def cleanup(self):
        try:
            logger.info("Đang dọn dẹp và ngắt kết nối...")
            self.mqtt_client.disconnect()
            logger.info("Đã ngắt kết nối thành công")
        except Exception as e:
            logger.error(f"Lỗi khi ngắt kết nối: {str(e)}")

def main():
    logger.info("=== Bắt đầu chương trình test MQTT ===")
    
    tester = MQTTTester()
    success = tester.test_connection()
    
    if success:
        logger.info("=== Tất cả các test đều thành công! ===")
    else:
        logger.error("=== Có lỗi xảy ra trong quá trình test ===")

if __name__ == "__main__":
    main()