#!/usr/bin/env python3
"""
Script để lấy dữ liệu từ Adafruit IO và lưu vào database PostgreSQL
"""

import os
import sys
import logging
import requests
import argparse
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load biến môi trường
load_dotenv()

# Cấu hình Adafruit IO
ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME")
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")
BASE_URL = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}"

# Cấu hình Database
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo model
Base = declarative_base()

class SensorData(Base):
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    feed_id = Column(String, index=True)
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

def get_feeds():
    """Lấy danh sách tất cả feeds từ Adafruit IO"""
    headers = {
        "X-AIO-Key": ADAFRUIT_IO_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/feeds", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Lỗi khi lấy feeds: {str(e)}")
        return []

def get_feed_data(feed_key, limit=100, start_time=None):
    """Lấy dữ liệu từ một feed cụ thể"""
    headers = {
        "X-AIO-Key": ADAFRUIT_IO_KEY,
        "Content-Type": "application/json"
    }
    
    params = {"limit": limit}
    if start_time:
        params["start_time"] = start_time.isoformat()
    
    try:
        response = requests.get(
            f"{BASE_URL}/feeds/{feed_key}/data",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu feed {feed_key}: {str(e)}")
        return []

def ensure_device_exists(db, feed_id):
    """Đảm bảo device tồn tại và có mapping với feed_id"""
    # Kiểm tra xem đã có mapping chưa
    mapping = db.execute(
        text("SELECT device_id FROM feed_device_mapping WHERE feed_id = :feed_id"),
        {"feed_id": feed_id}
    ).fetchone()
    
    if mapping:
        return mapping[0]  # Trả về device_id hiện tại
    
    # Nếu chưa có mapping, tạo device mới và mapping
    device_id = feed_id  # Mặc định sử dụng feed_id làm device_id
    
    # Đảm bảo device tồn tại
    result = db.execute(
        text("SELECT id FROM devices WHERE device_id = :device_id"),
        {"device_id": device_id}
    ).fetchone()
    
    if not result:
        db.execute(
            text("""
                INSERT INTO devices (device_id, name, description, created_at) 
                VALUES (:device_id, :name, :description, NOW())
            """),
            {
                "device_id": device_id,
                "name": f"Device {device_id}",
                "description": f"Device from Adafruit IO feed: {device_id}"
            }
        )
    
    # Tạo mapping
    db.execute(
        text("""
            INSERT INTO feed_device_mapping (feed_id, device_id)
            VALUES (:feed_id, :device_id)
        """),
        {
            "feed_id": feed_id,
            "device_id": device_id
        }
    )
    
    db.commit()
    logger.info(f"Đã tạo mapping mới: feed_id={feed_id} -> device_id={device_id}")
    return device_id

def save_to_database(feed_id, data_points):
    """Lưu dữ liệu vào database"""
    db = SessionLocal()
    count = 0
    
    try:
        # Lấy device_id từ mapping
        device_id = ensure_device_exists(db, feed_id)
        
        for point in data_points:
            try:
                # Lấy giá trị từ point
                raw_value = point.get("value")
                
                # Chỉ lưu các giá trị số
                try:
                    value = float(raw_value)
                except (ValueError, TypeError):
                    # Bỏ qua các giá trị không phải số
                    continue
                
                # Xử lý timestamp
                timestamp_str = point.get("created_at")
                if timestamp_str:
                    # Thay thế 'Z' bằng '+00:00' để phù hợp với định dạng ISO
                    timestamp_str = timestamp_str.replace('Z', '+00:00')
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        # Nếu không thể parse ISO format, sử dụng thời gian hiện tại
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()
                
                # Tạo bản ghi mới
                new_data = SensorData(
                    device_id=device_id,
                    feed_id=feed_id,
                    value=value,
                    timestamp=timestamp
                )
                
                db.add(new_data)
                count += 1
                
            except Exception as e:
                logger.warning(f"Bỏ qua điểm dữ liệu không hợp lệ: {str(e)}")
                continue
        
        db.commit()
        logger.info(f"Đã lưu {count} điểm dữ liệu từ feed {feed_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khi lưu vào database: {str(e)}")
    finally:
        db.close()
    
    return count

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Fetch data from Adafruit IO')
    parser.add_argument('--all', action='store_true', help='Fetch all data regardless of date')
    args = parser.parse_args()
    
    # Tạo bảng nếu chưa tồn tại
    Base.metadata.create_all(bind=engine)
    
    # Lấy danh sách feeds
    feeds = get_feeds()
    if not feeds:
        logger.error("Không thể lấy danh sách feeds. Vui lòng kiểm tra kết nối hoặc thông tin đăng nhập Adafruit IO.")
        return
    
    total_saved = 0
    
    # Xác định thời gian bắt đầu
    start_time = None
    if not args.all:
        # Lấy dữ liệu từ đầu ngày hôm nay
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = today
    
    # Xử lý từng feed
    for feed in feeds:
        feed_key = feed.get("key")
        if not feed_key:
            continue
            
        logger.info(f"Đang xử lý feed: {feed_key}")
        
        # Lấy dữ liệu từ feed
        data = get_feed_data(feed_key, start_time=start_time)
        if not data:
            logger.warning(f"Không có dữ liệu từ feed {feed_key}")
            continue
        
        # Lưu vào database
        saved = save_to_database(feed_key, data)
        total_saved += saved
    
    logger.info(f"Hoàn thành: Đã lưu tổng cộng {total_saved} bản ghi mới vào database")

if __name__ == "__main__":
    main() 