import paho.mqtt.client as mqtt
import json
import logging
from config import settings
import socket
import ssl

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='mqtt_adafruit.log')
logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Cấu hình kết nối Adafruit IO
        self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
        # Thiết lập SSL/TLS cho Adafruit IO
        self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
        
    def connect(self):
        try:
            logger.info(f"Đang kết nối đến Adafruit IO MQTT broker tại {settings.MQTT_HOST}:{settings.MQTT_PORT}")
            # Thử ping host trước
            try:
                socket.gethostbyname(settings.MQTT_HOST)
                logger.info(f"Đã phân giải tên miền thành công: {settings.MQTT_HOST}")
            except socket.gaierror as e:
                logger.error(f"Không thể phân giải tên miền {settings.MQTT_HOST}: {str(e)}")
                raise
            
            # Kết nối MQTT
            self.client.connect(settings.MQTT_HOST, settings.MQTT_PORT, 60)
            self.client.loop_start()
            logger.info("Đã kết nối đến Adafruit IO MQTT broker")
        except Exception as e:
            logger.error(f"Lỗi khi kết nối đến MQTT broker: {str(e)}")
            logger.exception("Chi tiết lỗi:")
            raise
            
    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Đã ngắt kết nối từ Adafruit IO")
        except Exception as e:
            logger.error(f"Lỗi khi ngắt kết nối từ Adafruit IO: {str(e)}")
            
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Đã kết nối thành công đến Adafruit IO")
            # Đăng ký nhận tin nhắn từ tất cả các feeds
            self.client.subscribe(settings.MQTT_TOPIC)
            logger.info(f"Đã đăng ký topic: {settings.MQTT_TOPIC}")
        else:
            logger.error(f"Kết nối thất bại với mã lỗi: {rc}")
            
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Cố gắng parse JSON nếu payload là JSON
            try:
                data = json.loads(payload)
                logger.info(f"Nhận tin nhắn từ topic {topic}: {data}")
            except json.JSONDecodeError:
                data = payload
                logger.info(f"Nhận tin nhắn (không phải JSON) từ topic {topic}: {data}")
            
            # Xử lý message ở đây
            self.handle_message(topic, data)
        except Exception as e:
            logger.error(f"Lỗi khi xử lý tin nhắn: {str(e)}")
            
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("Mất kết nối không mong muốn từ Adafruit IO. Đang thử kết nối lại...")
            
    def publish_message(self, feed_id, value):
        """
        Gửi dữ liệu lên một feed cụ thể trên Adafruit IO
        """
        try:
            # Định dạng topic cho Adafruit IO: username/feeds/feed_id
            username = settings.MQTT_USERNAME.split('/')[0]  # Lấy username từ MQTT_USERNAME
            topic = f"{username}/feeds/{feed_id}"
            
            # Chuyển đổi giá trị thành chuỗi nếu cần
            if isinstance(value, (dict, list)):
                payload = json.dumps(value)
            else:
                payload = str(value)
                
            self.client.publish(topic, payload)
            logger.info(f"Đã gửi dữ liệu đến {topic}: {value}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi dữ liệu: {str(e)}")
            return False
            
    def handle_message(self, topic, data):
        """
        Xử lý tin nhắn nhận được từ Adafruit IO
        
        Format topic Adafruit IO: username/feeds/feed_id
        """
        try:
            # Phân tích feed_id từ topic
            parts = topic.split('/')
            if len(parts) >= 3 and parts[1] == "feeds":
                feed_id = parts[2]
                logger.info(f"Đã xử lý dữ liệu từ feed {feed_id}: {data}")
                
                # TODO: Lưu dữ liệu vào database hoặc xử lý theo logic ứng dụng
                # Ví dụ:
                # from database import save_sensor_data
                # save_sensor_data(feed_id, data)
            else:
                logger.warning(f"Định dạng topic không đúng: {topic}")
        except Exception as e:
            logger.error(f"Lỗi khi xử lý dữ liệu: {str(e)}") 