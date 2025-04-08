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
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text, UniqueConstraint, and_
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
logger.info(f"Database URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

# Kiểm tra kết nối
try:
    with engine.connect() as conn:
        logger.info("Kết nối database thành công")
except Exception as e:
    logger.error(f"Lỗi kết nối database: {str(e)}")
    sys.exit(1)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo model
Base = declarative_base()

class Feed(Base):
    __tablename__ = "feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(String, unique=True, index=True)
    device_id = Column(String, index=True)

class SensorData(Base):
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    feed_id = Column(String, index=True)
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('device_id', 'feed_id', 'timestamp', name='uix_device_feed_time'),
    )

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

def ensure_feed_exists(db, feed_id):
    """Đảm bảo feed tồn tại trong bảng feeds"""
    try:
        # Kiểm tra xem feed đã tồn tại chưa
        feed = db.query(Feed).filter(Feed.feed_id == feed_id).first()
        
        if feed:
            logger.info(f"Feed đã tồn tại: feed_id={feed_id}, device_id={feed.device_id}")
            return feed.device_id
        
        # Nếu chưa tồn tại, tạo feed mới với device_id duy nhất
        device_id = f"device-{feed_id}"  # Tạo device_id duy nhất từ feed_id
        new_feed = Feed(feed_id=feed_id, device_id=device_id)
        db.add(new_feed)
        db.commit()
        
        logger.info(f"Đã tạo feed mới: feed_id={feed_id}, device_id={device_id}")
        return device_id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khi tạo feed: {str(e)}")
        raise

def save_to_database(feed_id, data_points):
    """Lưu dữ liệu vào database"""
    db = SessionLocal()
    count = 0
    updated = 0
    
    try:
        # Lấy device_id từ feed
        device_id = ensure_feed_exists(db, feed_id)
        logger.info(f"Đang lưu dữ liệu cho device_id: {device_id}, feed_id: {feed_id}")
        
        for point in data_points:
            try:
                # Lấy giá trị từ point
                raw_value = point.get("value")
                logger.debug(f"Giá trị thô: {raw_value}")
                
                # Xử lý giá trị JSON
                if isinstance(raw_value, dict):
                    value = raw_value.get("value")
                    if value is None:
                        logger.warning(f"Bỏ qua giá trị JSON không có trường value: {raw_value}")
                        continue
                    raw_value = value
                
                # Chỉ lưu các giá trị số
                try:
                    value = float(raw_value)
                except (ValueError, TypeError):
                    logger.warning(f"Bỏ qua giá trị không phải số: {raw_value}")
                    continue
                
                # Xử lý timestamp
                timestamp_str = point.get("created_at")
                if timestamp_str:
                    timestamp_str = timestamp_str.replace('Z', '+00:00')
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        timestamp = datetime.utcnow()
                        logger.warning(f"Sử dụng thời gian hiện tại do không thể parse: {timestamp_str}")
                else:
                    timestamp = datetime.utcnow()
                    logger.warning("Không có timestamp, sử dụng thời gian hiện tại")
                
                # Tạo bản ghi mới
                new_data = SensorData(
                    device_id=device_id,
                    feed_id=feed_id,
                    value=value,
                    timestamp=timestamp
                )
                db.add(new_data)
                count += 1
                
                if count % 100 == 0:
                    logger.info(f"Đã thêm {count} bản ghi mới")
                
            except Exception as e:
                logger.error(f"Lỗi khi xử lý điểm dữ liệu: {str(e)}")
                continue
        
        db.commit()
        logger.info(f"Đã lưu {count} điểm dữ liệu mới từ feed {feed_id}")
        
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
    parser.add_argument('--date', type=str, help='Fetch data for specific date (format: YYYY-MM-DD)')
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
    if args.date:
        try:
            # Parse ngày từ input
            start_time = datetime.strptime(args.date, "%Y-%m-%d")
            logger.info(f"Đang lấy dữ liệu cho ngày {args.date}")
        except ValueError:
            logger.error("Định dạng ngày không hợp lệ. Vui lòng sử dụng định dạng YYYY-MM-DD (ví dụ: 2024-04-08)")
            return
    elif not args.all:
        # Lấy dữ liệu từ đầu ngày hôm nay
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = today
        logger.info("Đang lấy dữ liệu từ đầu ngày hôm nay")
    
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