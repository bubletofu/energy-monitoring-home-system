import logging
import requests
import os
from sqlalchemy import text
from database import get_db
from dotenv import load_dotenv
import datetime

# Tải biến môi trường từ file .env
load_dotenv()

# Lấy thông tin xác thực Adafruit IO từ biến môi trường
ADAFRUIT_IO_USERNAME = os.getenv('ADAFRUIT_IO_USERNAME')
ADAFRUIT_IO_KEY = os.getenv('ADAFRUIT_IO_KEY')

# Cấu hình logging
logger = logging.getLogger(__name__)

def send_to_adafruit(feed_id, value):
    """
    Gửi dữ liệu lên Adafruit IO
    
    Args:
        feed_id (str): ID của feed trên Adafruit IO
        value (int/str): Giá trị cần gửi (0 hoặc 1)
    
    Returns:
        dict: Kết quả của việc gửi dữ liệu
    """
    if not ADAFRUIT_IO_USERNAME or not ADAFRUIT_IO_KEY:
        logger.error("Thiếu thông tin xác thực Adafruit IO trong file .env")
        return {
            "success": False,
            "message": "Không thể kết nối với Adafruit IO: Thiếu thông tin xác thực"
        }
    
    try:
        # Lấy thời gian hiện tại của máy local
        local_timestamp = datetime.datetime.now()
        formatted_timestamp = local_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Log thông tin xác thực (chỉ để debug)
        logger.info(f"Sử dụng Adafruit IO Username: {ADAFRUIT_IO_USERNAME}")
        logger.info(f"API Key prefix: {ADAFRUIT_IO_KEY[:5]}...")
        logger.info(f"Thời gian local gửi dữ liệu: {formatted_timestamp}")
        
        # URL cho Adafruit IO REST API
        url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/{feed_id}/data"
        
        # Kiểm tra feed tồn tại trước
        check_url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/{feed_id}"
        logger.info(f"Kiểm tra feed có tồn tại: {check_url}")
        
        headers = {
            'X-AIO-Key': ADAFRUIT_IO_KEY,
            'Content-Type': 'application/json'
        }
        
        # Kiểm tra feed tồn tại
        try:
            check_response = requests.get(check_url, headers=headers)
            if check_response.status_code != 200:
                logger.error(f"Feed {feed_id} không tồn tại: {check_response.status_code} - {check_response.text}")
                return {
                    "success": False,
                    "message": f"Feed {feed_id} không tồn tại trên Adafruit IO",
                    "details": check_response.text
                }
        except Exception as e:
            logger.warning(f"Lỗi khi kiểm tra feed tồn tại: {str(e)}")
            # Tiếp tục xử lý
        
        # Dữ liệu cần gửi
        data = {
            'value': value
        }
        
        logger.info(f"Đang gửi request đến: {url}")
        # Gửi request POST
        response = requests.post(url, json=data, headers=headers)
        
        # Kiểm tra kết quả
        if response.status_code in [200, 201]:
            response_data = response.json()
            logger.info(f"Gửi dữ liệu thành công lên feed {feed_id}: {value}")
            
            # Chuyển đổi thời gian Adafruit từ UTC sang múi giờ local
            adafruit_time_str = response_data.get('created_at')
            if adafruit_time_str:
                try:
                    # Phân tích thời gian UTC từ Adafruit
                    adafruit_time_utc = datetime.datetime.strptime(adafruit_time_str, "%Y-%m-%dT%H:%M:%SZ")
                    # Thêm thông tin múi giờ UTC
                    adafruit_time_utc = adafruit_time_utc.replace(tzinfo=datetime.timezone.utc)
                    # Chuyển đổi sang múi giờ local
                    adafruit_time_local = adafruit_time_utc.astimezone()
                    # Format lại thời gian để hiển thị
                    adafruit_time_formatted = adafruit_time_local.strftime("%Y-%m-%d %H:%M:%S %z")
                    
                    logger.info(f"Thời gian Adafruit (UTC): {adafruit_time_str}")
                    logger.info(f"Thời gian Adafruit (local): {adafruit_time_formatted}")
                    
                    # Lưu thời gian đã chuyển đổi vào response_data
                    response_data['created_at_local'] = adafruit_time_formatted
                except Exception as e:
                    logger.warning(f"Không thể chuyển đổi múi giờ: {str(e)}")
            
            return {
                "success": True,
                "message": "Gửi dữ liệu lên Adafruit IO thành công",
                "response": response_data,
                "local_timestamp": local_timestamp
            }
        else:
            logger.error(f"Lỗi khi gửi dữ liệu lên Adafruit IO: {response.status_code} - {response.text}")
            return {
                "success": False,
                "message": f"Lỗi khi gửi dữ liệu lên Adafruit IO: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        logger.error(f"Ngoại lệ khi gửi dữ liệu lên Adafruit IO: {str(e)}")
        return {
            "success": False,
            "message": f"Không thể kết nối với Adafruit IO: {str(e)}"
        }

def turn_device(device_id, user_id, value):
    """
    Bật/tắt thiết bị với device_id cho người dùng user_id
    
    Args:
        device_id (str): ID của thiết bị cần bật/tắt
        user_id (int): ID của người dùng sở hữu thiết bị
        value (int): Giá trị 0 (tắt) hoặc 1 (bật)
    
    Returns:
        dict: Kết quả của việc bật/tắt thiết bị
    """
    logger.info(f"Yêu cầu bật/tắt thiết bị: device_id={device_id}, user_id={user_id}, value={value}")
    
    # Kiểm tra giá trị đầu vào
    if value not in [0, 1]:
        return {
            "success": False,
            "message": "Giá trị không hợp lệ. Chỉ chấp nhận 0 (tắt) hoặc 1 (bật)"
        }
    
    db = next(get_db())
    
    try:
        # Kiểm tra người dùng có sở hữu thiết bị không
        check_query = text("""
        SELECT id FROM devices 
        WHERE device_id = :device_id AND user_id = :user_id
        """)
        
        result = db.execute(check_query, {"device_id": device_id, "user_id": user_id})
        device = result.fetchone()
        
        if not device:
            logger.warning(f"Người dùng {user_id} không sở hữu thiết bị {device_id}")
            return {
                "success": False,
                "message": f"Thiết bị {device_id} không tồn tại hoặc bạn không có quyền điều khiển nó"
            }
        
        # Kiểm tra xem thiết bị có feed yolo-fan hay không
        check_feed_query = text("""
        SELECT DISTINCT feed_id FROM sensor_data 
        WHERE device_id = :device_id AND feed_id LIKE 'yolo-fan%'
        """)
        
        result = db.execute(check_feed_query, {"device_id": device_id})
        yolo_fan_feeds = result.fetchall()
        
        if not yolo_fan_feeds:
            logger.warning(f"Thiết bị {device_id} không có feed 'yolo-fan'")
            
            # Thử kiểm tra trong bảng feeds nếu không tìm thấy trong sensor_data
            check_feeds_table = text("""
            SELECT feed_id FROM feeds 
            WHERE device_id = :device_id AND feed_id LIKE 'yolo-fan%'
            """)
            
            feeds_result = db.execute(check_feeds_table, {"device_id": device_id})
            feeds_records = feeds_result.fetchall()
            
            if feeds_records:
                # Nếu tìm thấy trong bảng feeds nhưng không có trong sensor_data
                yolo_fan_feeds = feeds_records
                logger.info(f"Tìm thấy feed 'yolo-fan' trong bảng feeds cho thiết bị {device_id}")
            else:
                # Nếu vẫn không tìm thấy, tạo feed mới cho thiết bị
                try:
                    feed_id = f"yolo-fan-mode-select"
                    logger.info(f"Tạo feed mới '{feed_id}' cho thiết bị {device_id}")
                    
                    # Kiểm tra feed có tồn tại trên Adafruit IO không
                    test_feed = send_to_adafruit(feed_id, "0")
                    
                    # Nếu thành công, lưu vào bảng feeds
                    if test_feed["success"]:
                        insert_feed = text("""
                        INSERT INTO feeds (feed_id, device_id, last_fetched)
                        VALUES (:feed_id, :device_id, CURRENT_TIMESTAMP)
                        ON CONFLICT (feed_id) DO UPDATE SET device_id = :device_id
                        """)
                        
                        db.execute(insert_feed, {
                            "feed_id": feed_id,
                            "device_id": device_id
                        })
                        db.commit()
                        
                        # Sử dụng feed này cho điều khiển
                        feed_id = feed_id
                        logger.info(f"Đã tạo và kiểm tra feed mới: {feed_id}")
                        
                        # Trả về thành công sớm
                        return {
                            "success": True,
                            "message": f"{'Bật' if value == 1 else 'Tắt'} thiết bị {device_id} thành công (feed mới)",
                            "device_id": device_id,
                            "feed_id": feed_id,
                            "value": value,
                            "adafruit_response": test_feed.get("response", {})
                        }
                    else:
                        # Nếu không thành công, trả về lỗi
                        return {
                            "success": False,
                            "message": f"Không thể tạo feed mới cho thiết bị: {test_feed['message']}",
                            "device_id": device_id,
                            "details": test_feed.get("details", "")
                        }
                except Exception as e:
                    logger.error(f"Lỗi khi tạo feed mới: {str(e)}")
                    return {
                        "success": False,
                        "message": f"Thiết bị {device_id} không hỗ trợ điều khiển (không tìm thấy feed phù hợp)",
                        "details": str(e)
                    }
        
        if not yolo_fan_feeds:
            return {
                "success": False,
                "message": f"Thiết bị {device_id} không hỗ trợ điều khiển (không có feed yolo-fan)"
            }

        # Tìm feed phù hợp nhất để điều khiển
        logger.info(f"Danh sách feed tìm thấy: {[f[0] for f in yolo_fan_feeds]}")

        # Tìm 'yolo-fan-mode-select' trước tiên
        exact_mode_select = None
        for feed in yolo_fan_feeds:
            if feed[0] == 'yolo-fan-mode-select':
                exact_mode_select = feed[0]
                break

        if exact_mode_select:
            feed_id = exact_mode_select
            logger.info(f"Sử dụng feed chính xác: {feed_id}")
        else:
            # Tìm feed phù hợp nhất để điều khiển: ưu tiên feed chứa 'mode' hoặc 'control'
            control_feed_query = text("""
            SELECT feed_id FROM sensor_data 
            WHERE device_id = :device_id AND feed_id LIKE 'yolo-fan%' 
              AND (feed_id LIKE '%mode%' OR feed_id LIKE '%control%')
            LIMIT 1
            """)
            
            result = db.execute(control_feed_query, {"device_id": device_id})
            control_feed = result.fetchone()
            
            if control_feed:
                feed_id = control_feed[0]
                logger.info(f"Sử dụng feed điều khiển: {feed_id}")
            else:
                # Nếu không tìm thấy feed điều khiển cụ thể, lấy feed yolo-fan đầu tiên
                feed_id = yolo_fan_feeds[0][0]
                logger.info(f"Không tìm thấy feed điều khiển cụ thể, sử dụng feed: {feed_id}")
        
        # Gửi lệnh bật/tắt tới feed trên Adafruit IO
        adafruit_result = send_to_adafruit(feed_id, value)
        
        if not adafruit_result["success"]:
            logger.error(f"Lỗi khi gửi dữ liệu lên Adafruit IO: {adafruit_result['message']}")
            return {
                "success": False,
                "message": f"Không thể gửi lệnh đến thiết bị: {adafruit_result['message']}",
                "device_id": device_id,
                "feed_id": feed_id,
                "error": adafruit_result.get("details", "")
            }
        
        # THAY ĐỔI: Bỏ qua phần cập nhật bảng sensor_data
        logger.info("Bỏ qua cập nhật sensor_data, việc này sẽ được xử lý bởi fetch.py")
        
        # Trả về kết quả thành công với thời gian đã chuyển đổi múi giờ
        formatted_time = None
        if adafruit_result.get("response") and "created_at_local" in adafruit_result["response"]:
            formatted_time = adafruit_result["response"]["created_at_local"]
        else:
            formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
        
        return {
            "success": True,
            "message": f"{'Bật' if value == 1 else 'Tắt'} thiết bị {device_id} thành công",
            "device_id": device_id,
            "feed_id": feed_id,
            "value": value,
            "timestamp": formatted_time,
            "adafruit_response": adafruit_result.get("response", {})
        }
            
    except Exception as e:
        logger.error(f"Lỗi khi xử lý yêu cầu bật/tắt thiết bị: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi hệ thống: {str(e)}"
        }
    finally:
        db.close()
