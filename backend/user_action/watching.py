#!/usr/bin/env python3
"""
Script để theo dõi trạng thái thiết bị từ bảng sensor_data và cập nhật vào cơ sở dữ liệu

Cách sử dụng:
    python watching.py --check-interval 5 [--device-id <device_id>] [--user-id <user_id>]
    
    Tham số:
    --check-interval: Khoảng thời gian kiểm tra (phút, mặc định: 5)
    --device-id: ID của thiết bị cần kiểm tra (để trống để kiểm tra tất cả)
    --user-id: ID của người dùng (để chỉ kiểm tra thiết bị của người dùng cụ thể)
    --offline-threshold: Ngưỡng thời gian để xác định thiết bị đang offline (phút, mặc định: 10)
    --daemon: Chạy liên tục như một dịch vụ nền
"""

import argparse
import json
import logging
import os
import sys
import time
import datetime
from datetime import timezone, datetime as dt
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import schedule
import threading

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging
log_file = 'device_status_watcher.log'
log_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        log_handler
    ]
)
logger = logging.getLogger(__name__)

# Cấu hình Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")

# Biến toàn cục để kiểm soát trạng thái daemon
daemon_running = False
daemon_thread = None
current_watcher_user_id = None  # ID của người dùng hiện tại đang sử dụng watcher

# Hàm trợ giúp để làm việc với timezone
def get_current_utc_time():
    """
    Trả về thời gian hiện tại ở múi giờ UTC
    """
    return dt.now(timezone.utc)

def ensure_timezone(timestamp):
    """
    Đảm bảo timestamp có timezone UTC, thêm nếu thiếu
    """
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp

class DeviceWatcher:
    """
    Lớp theo dõi và cập nhật trạng thái thiết bị
    """
    def __init__(self, check_interval=5, offline_threshold=10, user_id=None):
        """
        Khởi tạo DeviceWatcher
        
        Args:
            check_interval: Khoảng thời gian kiểm tra (phút)
            offline_threshold: Ngưỡng thời gian để xác định thiết bị đang offline (phút)
            user_id: ID của người dùng (chỉ kiểm tra thiết bị của người dùng này)
        """
        self.check_interval = check_interval
        self.offline_threshold = offline_threshold  # Ngưỡng phút để xác định thiết bị offline
        self.user_id = user_id  # None = tất cả người dùng (chỉ admin mới làm được)
        self.has_devices = False  # Mặc định giả định không có thiết bị
        
        logger.info(f"Khởi tạo DeviceWatcher với check_interval={check_interval}, offline_threshold={offline_threshold}, user_id={user_id}")
        
        # Kết nối đến database
        try:
            self.engine = create_engine(DATABASE_URL)
            self.Session = sessionmaker(bind=self.engine)
            logger.info(f"Đã kết nối thành công đến database: {DATABASE_URL}")
        except Exception as e:
            logger.error(f"Lỗi kết nối database: {str(e)}")
            sys.exit(1)
    
    def get_all_devices(self):
        """
        Lấy danh sách các thiết bị từ database
        Nếu user_id được chỉ định, chỉ lấy thiết bị của người dùng đó
        
        Returns:
            list: Danh sách các thiết bị
        """
        try:
            db = self.Session()
            
            # Xây dựng truy vấn
            query_text = "SELECT id, device_id, name, user_id FROM devices"
            params = {}
            
            # Nếu chỉ định user_id, chỉ lấy thiết bị của người dùng đó
            if self.user_id:
                query_text += " WHERE user_id = :user_id"
                params["user_id"] = self.user_id
                
            query = text(query_text)
            result = db.execute(query, params)
            
            devices = [{"id": row[0], "device_id": row[1], "name": row[2], "user_id": row[3]} for row in result.fetchall()]
            db.close()
            
            # Cập nhật trạng thái có thiết bị hay không
            self.has_devices = len(devices) > 0
            
            if self.user_id and not self.has_devices:
                logger.info(f"Người dùng ID {self.user_id} không có thiết bị nào")
            
            return devices
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách thiết bị: {str(e)}")
            return []
    
    def check_device_status(self, device_id):
        """
        Kiểm tra trạng thái thiết bị dựa trên dữ liệu từ bảng sensor_data
        
        Args:
            device_id: ID của thiết bị
            
        Returns:
            dict: Thông tin trạng thái thiết bị
        """
        try:
            # Kiểm tra xem thiết bị có thuộc về người dùng không (nếu user_id được chỉ định)
            if self.user_id:
                db = self.Session()
                device_check = db.execute(
                    text("SELECT user_id FROM devices WHERE device_id = :device_id"),
                    {"device_id": device_id}
                ).fetchone()
                
                # Nếu thiết bị không thuộc về người dùng, bỏ qua
                if not device_check or device_check[0] != self.user_id:
                    logger.info(f"Thiết bị {device_id} không thuộc về người dùng ID {self.user_id}, bỏ qua")
                    db.close()
                    return None
                db.close()
            
            # Lấy thời gian hiện tại chính xác ở múi giờ UTC
            current_time = get_current_utc_time()
            logger.debug(f"Thời gian hiện tại UTC: {current_time.isoformat()}")
            
            # Thời điểm tính toán - thời gian cục bộ
            calculation_time = datetime.datetime.now().isoformat()
            
            db = self.Session()
            
            # Lấy bản ghi mới nhất từ bảng sensor_data
            query = text("""
                SELECT value, timestamp
                FROM sensor_data
                WHERE device_id = :device_id
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            
            result = db.execute(query, {"device_id": device_id}).fetchone()
            db.close()
            
            if not result:
                logger.warning(f"Không tìm thấy dữ liệu nào cho thiết bị {device_id}")
                return {
                    "device_id": device_id,
                    "is_online": False,
                    "last_value": None,
                    "last_updated": None,
                    "status_details": {
                        "data_source": "sensor_data",
                        "last_data_time": "Không có dữ liệu",
                        "current_time": datetime.datetime.now().isoformat(),  # Use local time as originally intended
                        "message": "Không tìm thấy dữ liệu cho thiết bị này"
                    }
                }
            
            # Phân tích kết quả
            value, timestamp = result
            
            # Đảm bảo timestamp có timezone, nếu không thì chuyển thành UTC
            timestamp = ensure_timezone(timestamp)
            logger.debug(f"Thời gian cuối cùng của thiết bị: {timestamp.isoformat()}")
            
            # CÁCH TÍNH ĐƠN GIẢN NHẤT: Chỉ quan tâm đến chênh lệch thời gian thực tế
            # Không cần quan tâm đến múi giờ, cứ lấy chênh lệch trực tiếp
            current_time_naive = datetime.datetime.now()
            last_time_naive = timestamp.replace(tzinfo=None)  # Loại bỏ thông tin múi giờ
            
            # Tính chênh lệch trực tiếp, không cần quan tâm timezone
            time_diff_delta = current_time_naive - last_time_naive
            time_diff_seconds = time_diff_delta.total_seconds()
            time_diff_minutes = time_diff_seconds / 60
            
            logger.debug(f"TIMESTAMP SIMPLE CHECK: Current={current_time_naive}, Last={last_time_naive}, Diff={time_diff_seconds}s = {time_diff_minutes}m")
            
            # Kiểm tra xem thiết bị có online không
            is_online = time_diff_minutes <= self.offline_threshold
            
            # Log chi tiết về việc kiểm tra trạng thái
            logger.debug(f"[CHECK] Thiết bị {device_id}: " +
                        f"Thời gian hiện tại={current_time.isoformat()}, " +
                        f"Cập nhật lần cuối={timestamp.isoformat()}, " +
                        f"Chênh lệch={round(time_diff_minutes, 2)} phút, " +
                        f"Ngưỡng={self.offline_threshold} phút, " +
                        f"Trạng thái={is_online}")
            
            # Tạo thông tin chi tiết về trạng thái
            status_details = {
                "data_source": "sensor_data",
                "last_data_time": timestamp.isoformat(),
                "current_time": datetime.datetime.now().isoformat(),  # Using local time as originally intended
                "message": format_time_difference(time_diff_minutes) if not is_online else f"Thiết bị đang hoạt động bình thường, cập nhật gần nhất cách đây {int(time_diff_minutes)} phút"
            }
            
            if not is_online:
                # Chỉ cập nhật trạng thái offline mà không thêm nhiều thông tin
                logger.info(f"[DETECT] Thiết bị {device_id} OFFLINE - Không hoạt động trong {round(time_diff_minutes, 2)} phút " +
                          f"(ngưỡng: {self.offline_threshold} phút)")
                
                # Thêm log chi tiết cho debug
                logger.debug(f"OFFLINE DETAILS: Device={device_id}, " +
                           f"Current={current_time.isoformat()}, " +
                           f"Last={timestamp.isoformat()}, " + 
                           f"TimeDiff={round(time_diff_minutes, 2)} phút")
            else:
                logger.info(f"[DETECT] Thiết bị {device_id} ONLINE - Cập nhật gần nhất cách đây {round(time_diff_minutes, 2)} phút")
            
            return {
                "device_id": device_id,
                "is_online": is_online,
                "last_value": float(value) if value is not None else None,
                "last_updated": timestamp,
                "status_details": status_details
            }
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra trạng thái thiết bị {device_id}: {str(e)}")
            # Lấy thời gian hiện tại cho thông báo lỗi
            return {
                "device_id": device_id,
                "is_online": False,
                "last_value": None,
                "last_updated": None,
                "status_details": {
                    "data_source": "sensor_data",
                    "last_data_time": "Lỗi khi kiểm tra",
                    "current_time": datetime.datetime.now().isoformat(),  # Use local time as originally intended
                    "message": f"Lỗi khi kiểm tra trạng thái thiết bị: {str(e)}"
                }
            }
    
    def update_device_status(self, device_status):
        """
        Cập nhật trạng thái thiết bị vào database
        
        Args:
            device_status: Thông tin trạng thái thiết bị
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu thất bại
        """
        # Nếu device_status là None, không cập nhật gì cả
        if device_status is None:
            return False
            
        try:
            device_id = device_status["device_id"]
            is_online = device_status["is_online"]
            last_value = device_status["last_value"]
            last_updated = device_status["last_updated"]
            status_details = device_status["status_details"]
            
            # Luôn lấy thời gian hiện tại mới nhất khi cập nhật trạng thái
            current_time = get_current_utc_time()
            logger.debug(f"[UPDATE] Thời gian hiện tại khi cập nhật: {current_time.isoformat()}")
            
            # Xác nhận lại trạng thái online dựa trên thời gian thực
            if last_updated:
                last_updated = ensure_timezone(last_updated)
                logger.debug(f"[UPDATE] Thời gian cuối cùng của thiết bị: {last_updated.isoformat()}")
                
                # Tính toán lại thời gian chênh lệch với thời gian hiện tại mới
                # CÁCH TÍNH ĐƠN GIẢN NHẤT: Chỉ quan tâm đến chênh lệch thời gian thực tế
                # Không cần quan tâm đến múi giờ, cứ lấy chênh lệch trực tiếp
                current_time_naive = datetime.datetime.now()
                last_time_naive = last_updated.replace(tzinfo=None)  # Loại bỏ thông tin múi giờ
                
                # Tính chênh lệch trực tiếp, không cần quan tâm timezone
                time_diff_delta = current_time_naive - last_time_naive
                time_diff_seconds = time_diff_delta.total_seconds()
                time_diff_minutes = time_diff_seconds / 60
                
                logger.debug(f"[UPDATE] TIMESTAMP SIMPLE CHECK: Current={current_time_naive}, Last={last_time_naive}, Diff={time_diff_seconds}s = {time_diff_minutes}m")
                
                # Đảm bảo trạng thái online được tính toán chính xác nhất
                is_online = time_diff_minutes <= self.offline_threshold
                logger.debug(f"[UPDATE] Chênh lệch thời gian: {round(time_diff_minutes, 2)} phút, Trạng thái: {'ONLINE' if is_online else 'OFFLINE'}, Ngưỡng: {self.offline_threshold} phút")
                
                # Đảm bảo status_details phản ánh đúng trạng thái với thời gian hiện tại mới
                if not is_online:
                    # Bất kể status_details có gì, cập nhật lại thông tin offline
                    # Format thời gian offline cho log
                    hours = int(time_diff_minutes // 60)
                    minutes = int(time_diff_minutes % 60)
                    time_diff_str = f"{hours} giờ {minutes} phút" if hours > 0 else f"{minutes} phút"
                    
                    # Log thông tin chi tiết về thời gian
                    logger.debug(f"[UPDATE] OFFLINE DETAILS - Device: {device_id}, " +
                              f"Current: {current_time.isoformat()}, " +
                              f"Last: {last_updated.isoformat()}, " + 
                              f"TimeDiff: {round(time_diff_minutes, 2)} phút, " +
                              f"Ngưỡng: {self.offline_threshold} phút")
                    
                    # Đơn giản hóa status_details, chỉ giữ lại thông tin cần thiết
                    status_details = {
                        "data_source": "sensor_data",
                        "last_data_time": last_updated.isoformat(),
                        "current_time": datetime.datetime.now().isoformat(),  # Using local time as originally intended
                        "message": format_time_difference(time_diff_minutes)
                    }
                else:
                    # Đơn giản hóa status_details, chỉ giữ lại thông tin cần thiết
                    status_details = {
                        "data_source": "sensor_data",
                        "last_data_time": last_updated.isoformat(),
                        "current_time": datetime.datetime.now().isoformat(),  # Using local time as originally intended
                        "message": f"Thiết bị đang hoạt động bình thường, cập nhật gần nhất cách đây {int(time_diff_minutes)} phút"
                    }
            
            # Chuyển status_details thành JSON string để lưu vào database
            status_details_json = json.dumps(status_details)
            
            db = self.Session()
            try:
                # Kiểm tra xem thiết bị có tồn tại không và có thuộc về người dùng không
                if self.user_id:
                    result = db.execute(
                        text("SELECT id FROM devices WHERE device_id = :device_id AND user_id = :user_id"),
                        {"device_id": device_id, "user_id": self.user_id}
                    ).fetchone()
                else:
                    result = db.execute(
                        text("SELECT id FROM devices WHERE device_id = :device_id"),
                        {"device_id": device_id}
                    ).fetchone()
                
                if not result:
                    if self.user_id:
                        logger.warning(f"Không tìm thấy thiết bị {device_id} của người dùng {self.user_id}")
                    else:
                        logger.warning(f"Không tìm thấy thiết bị với ID: {device_id}")
                    db.close()
                    return False
                
                # Cập nhật trạng thái thiết bị
                last_updated_str = last_updated.isoformat() if last_updated else None
                
                update_query = text("""
                    UPDATE devices
                    SET is_online = :is_online,
                        last_value = :last_value,
                        last_updated = :last_updated,
                        status_details = :status_details
                    WHERE device_id = :device_id
                """)
                
                db.execute(update_query, {
                    "is_online": is_online,
                    "last_value": last_value,
                    "last_updated": last_updated_str,
                    "status_details": status_details_json,
                    "device_id": device_id
                })
                
                db.commit()
                
                # Log rõ ràng về trạng thái thiết bị
                if is_online:
                    logger.info(f"Thiết bị {device_id} ONLINE - Cập nhật lần cuối: {last_updated_str}")
                else:
                    offline_info = ""
                    if "offline_duration" in status_details:
                        offline_info = f" - Offline trong: {status_details['offline_duration']}"
                    logger.info(f"Thiết bị {device_id} OFFLINE{offline_info} - Ngưỡng offline: {self.offline_threshold} phút")
                
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Lỗi khi cập nhật trạng thái thiết bị {device_id}: {str(e)}")
                raise
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trạng thái thiết bị: {str(e)}")
            return False
    
    def check_all_devices(self):
        """
        Kiểm tra trạng thái của tất cả các thiết bị (của người dùng nếu user_id được chỉ định)
        """
        # Lấy danh sách thiết bị
        devices = self.get_all_devices()
        
        # Nếu không có thiết bị nào, không cần kiểm tra
        if not devices:
            if self.user_id:
                logger.info(f"[SKIP] Người dùng {self.user_id} không có thiết bị nào, bỏ qua kiểm tra")
            else:
                logger.info("[SKIP] Không có thiết bị nào trong hệ thống, bỏ qua kiểm tra")
            return
        
        logger.info("=========================================================")
        logger.info(f"Bắt đầu kiểm tra trạng thái {len(devices)} thiết bị" + 
                   (f" của người dùng {self.user_id}" if self.user_id else ""))
        logger.info("=========================================================")
        
        # Thống kê kết quả
        stats = {
            "total": len(devices),
            "online": 0,
            "offline": 0,
            "error": 0
        }
        
        for device in devices:
            device_id = device["device_id"]
            try:
                logger.info(f"Kiểm tra thiết bị: {device_id}")
                
                status = self.check_device_status(device_id)
                if status:  # Nếu có thông tin trạng thái
                    self.update_device_status(status)
                    
                    # Cập nhật thống kê
                    if status['is_online']:
                        stats["online"] += 1
                    else:
                        stats["offline"] += 1
                else:
                    stats["error"] += 1
                
                # Tạm dừng để tránh quá tải database
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"[ERROR] Lỗi khi kiểm tra thiết bị {device_id}: {str(e)}")
                stats["error"] += 1
        
        logger.info("=========================================================")
        logger.info(f"Hoàn thành kiểm tra {stats['total']} thiết bị:")
        logger.info(f"- Online: {stats['online']}")
        logger.info(f"- Offline: {stats['offline']}")
        if stats["error"] > 0:
            logger.info(f"- Lỗi: {stats['error']}")
        logger.info("=========================================================")
        
        # Cập nhật trạng thái có thiết bị
        self.has_devices = (stats['total'] > 0)
    
    def check_specific_device(self, device_id):
        """
        Kiểm tra trạng thái của một thiết bị cụ thể
        
        Args:
            device_id: ID của thiết bị cần kiểm tra
            
        Returns:
            bool: True nếu kiểm tra và cập nhật thành công, False nếu thất bại
        """
        logger.info(f"========== Bắt đầu kiểm tra thiết bị: {device_id} ==========")
        
        # Nếu user_id được chỉ định, kiểm tra xem thiết bị có thuộc về người dùng không
        if self.user_id:
            db = self.Session()
            device = db.execute(
                text("SELECT id, name FROM devices WHERE device_id = :device_id AND user_id = :user_id"),
                {"device_id": device_id, "user_id": self.user_id}
            ).fetchone()
            db.close()
            
            if not device:
                logger.warning(f"[SKIP] Thiết bị {device_id} không thuộc về người dùng {self.user_id}")
                return False
                
        # Kiểm tra trạng thái thiết bị
        status = self.check_device_status(device_id)
        if not status:  # Nếu không có thông tin trạng thái
            logger.warning(f"[FAIL] Không thể lấy thông tin trạng thái của thiết bị {device_id}")
            return False
            
        # Cập nhật trạng thái vào database
        updated = self.update_device_status(status)
        
        if updated:
            logger.info(f"========== Hoàn thành kiểm tra thiết bị: {device_id} ==========")
            return True
        else:
            logger.warning(f"[FAIL] Không thể cập nhật trạng thái thiết bị {device_id}")
            return False
    
    def run_as_daemon(self):
        """
        Chạy liên tục như một dịch vụ nền
        """
        global daemon_running
        logger.info(f"Bắt đầu theo dõi thiết bị mỗi {self.check_interval} phút" + 
                   (f" cho người dùng {self.user_id}" if self.user_id else ""))
        
        # Chạy lần đầu
        try:
            self.check_all_devices()
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra thiết bị lần đầu: {str(e)}")
        
        # Lên lịch chạy định kỳ
        schedule.every(self.check_interval).minutes.do(self.check_all_devices)
        
        try:
            while daemon_running:
                # Nếu có chỉ định user_id và người dùng không có thiết bị, kiểm tra lại mỗi giờ
                if self.user_id and not self.has_devices:
                    # Kiểm tra xem người dùng đã claim thiết bị chưa
                    if schedule.jobs:
                        schedule.clear()
                    schedule.every(60).minutes.do(self.check_all_devices)  # Kiểm tra lại sau 1 giờ
                    logger.info(f"Người dùng {self.user_id} không có thiết bị nào, sẽ kiểm tra lại sau 1 giờ")
                
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Lỗi không mong muốn trong daemon: {str(e)}")
            raise
        finally:
            logger.info("Daemon đã dừng")

def start_watcher(check_interval=5, offline_threshold=10, user_id=None):
    """
    Bắt đầu dịch vụ theo dõi thiết bị trong một thread riêng biệt
    
    Args:
        check_interval: Khoảng thời gian kiểm tra (phút, mặc định: 5 phút)
        offline_threshold: Ngưỡng thời gian để xác định thiết bị đang offline (phút, mặc định: 10 phút)
        user_id: ID của người dùng (chỉ kiểm tra thiết bị của người dùng này)
    """
    global daemon_running, daemon_thread, current_watcher_user_id
    
    # Đảm bảo tham số có giá trị hợp lý
    if offline_threshold <= 0:
        logger.warning(f"Ngưỡng offline không hợp lệ: {offline_threshold}, đặt về giá trị mặc định 10 phút")
        offline_threshold = 10
    
    if check_interval <= 0:
        logger.warning(f"Khoảng thời gian kiểm tra không hợp lệ: {check_interval}, đặt về giá trị mặc định 5 phút")
        check_interval = 5
    
    # Nếu đã có daemon đang chạy, kiểm tra xem có phải cùng user_id không
    if daemon_running:
        if current_watcher_user_id == user_id:
            logger.info(f"Dịch vụ theo dõi thiết bị đã đang chạy cho người dùng {user_id}")
            return
        else:
            # Nếu khác user_id, dừng daemon cũ và tạo mới
            stop_watcher()
            logger.info(f"Đã dừng dịch vụ theo dõi thiết bị cho người dùng {current_watcher_user_id}")
    
    # Đánh dấu daemon đang chạy
    daemon_running = True
    current_watcher_user_id = user_id
    
    # Tạo watcher
    watcher = DeviceWatcher(check_interval, offline_threshold, user_id)
    
    # Chạy watcher trong một thread riêng biệt
    daemon_thread = threading.Thread(target=watcher.run_as_daemon, daemon=True)
    daemon_thread.start()
    
    logger.info(f"Đã bắt đầu dịch vụ theo dõi thiết bị mỗi {check_interval} phút, ngưỡng offline {offline_threshold} phút" + 
               (f" cho người dùng {user_id}" if user_id else ""))

def stop_watcher():
    """
    Dừng dịch vụ theo dõi thiết bị
    """
    global daemon_running, current_watcher_user_id
    
    if not daemon_running:
        logger.info("Dịch vụ theo dõi thiết bị không đang chạy")
        return
    
    # Đánh dấu daemon cần dừng
    daemon_running = False
    user_id_info = f" cho người dùng {current_watcher_user_id}" if current_watcher_user_id else ""
    logger.info(f"Đã gửi tín hiệu dừng cho dịch vụ theo dõi thiết bị{user_id_info}")
    current_watcher_user_id = None

def format_time_difference(minutes):
    """Format time difference in human-readable format (hours and minutes)"""
    if minutes < 60:
        return f"Thiết bị không hoạt động trong {int(minutes)} phút"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if mins == 0:
            return f"Thiết bị không hoạt động trong {hours} giờ"
        else:
            return f"Thiết bị không hoạt động trong {hours} giờ {mins} phút"

def main():
    parser = argparse.ArgumentParser(description="Theo dõi trạng thái thiết bị dựa trên dữ liệu từ bảng sensor_data")
    parser.add_argument("--check-interval", type=int, default=5, help="Khoảng thời gian kiểm tra (phút, mặc định: 5)")
    parser.add_argument("--device-id", type=str, help="ID của thiết bị cần kiểm tra (để trống để kiểm tra tất cả)")
    parser.add_argument("--user-id", type=int, help="ID của người dùng (chỉ kiểm tra thiết bị của người dùng này)")
    parser.add_argument("--offline-threshold", type=int, default=10, help="Ngưỡng thời gian để xác định thiết bị đang offline (phút, mặc định: 10)")
    parser.add_argument("--daemon", action="store_true", help="Chạy liên tục như một dịch vụ nền")
    
    args = parser.parse_args()
    
    # Đảm bảo tham số có giá trị hợp lý
    check_interval = max(1, args.check_interval)  # Tối thiểu 1 phút
    offline_threshold = max(1, args.offline_threshold)  # Tối thiểu 1 phút
    
    if check_interval != args.check_interval:
        logger.warning(f"Khoảng thời gian kiểm tra đã được điều chỉnh từ {args.check_interval} thành {check_interval} phút")
    
    if offline_threshold != args.offline_threshold:
        logger.warning(f"Ngưỡng offline đã được điều chỉnh từ {args.offline_threshold} thành {offline_threshold} phút")
    
    watcher = DeviceWatcher(check_interval, offline_threshold, args.user_id)
    
    logger.info(f"Khởi động với check_interval={check_interval}, offline_threshold={offline_threshold}, user_id={args.user_id}")
    
    if args.daemon:
        logger.info("Chạy ở chế độ daemon...")
        start_watcher(check_interval, offline_threshold, args.user_id)
        try:
            # Giữ tiến trình chính hoạt động
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_watcher()
            print("Đã dừng dịch vụ theo dõi thiết bị")
    elif args.device_id:
        watcher.check_specific_device(args.device_id)
        print(f"Đã kiểm tra thiết bị {args.device_id}")
    else:
        watcher.check_all_devices()
        print(f"Đã kiểm tra tất cả các thiết bị" + (f" của người dùng {args.user_id}" if args.user_id else ""))

if __name__ == "__main__":
    main()
