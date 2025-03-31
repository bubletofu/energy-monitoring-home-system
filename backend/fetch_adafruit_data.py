#!/usr/bin/env python3
"""
Script lấy dữ liệu từ Adafruit IO và lưu vào database PostgreSQL

Cách sử dụng:
    python fetch_adafruit_data.py --username <adafruit_io_username> --key <adafruit_io_key> --feed <feed_id>
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time
import requests
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fetch_adafruit_data.log')
    ]
)
logger = logging.getLogger(__name__)

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")

# Tạo models
Base = declarative_base()

class SensorData(Base):
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    feed_id = Column(String, index=True)
    value = Column(Float)
    raw_data = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class FetchAdafruitData:
    def __init__(self, username: str, key: str):
        """
        Khởi tạo client để lấy dữ liệu từ Adafruit IO
        
        Args:
            username: Adafruit IO username
            key: Adafruit IO key
        """
        self.username = username
        self.key = key
        self.base_url = f"https://io.adafruit.com/api/v2/{username}"
        self.headers = {
            "X-AIO-Key": key,
            "Content-Type": "application/json"
        }
        
        # Kết nối database
        try:
            self.engine = create_engine(DATABASE_URL)
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info(f"Đã kết nối thành công đến database: {DATABASE_URL}")
        except Exception as e:
            logger.error(f"Lỗi kết nối database: {str(e)}")
            raise
    
    def _ensure_device_exists(self, device_id: str = "default") -> bool:
        """
        Đảm bảo thiết bị tồn tại trong database
        """
        try:
            db = self.SessionLocal()
            
            # Kiểm tra xem bảng devices có tồn tại không
            if not self.engine.dialect.has_table(self.engine, "devices"):
                # Nếu không có bảng devices, tạo bản ghi trực tiếp trong SensorData
                logger.warning("Bảng devices không tồn tại, lưu trực tiếp vào SensorData")
                db.close()
                return True
                
            # Nếu có bảng devices, kiểm tra và tạo thiết bị nếu cần
            from sqlalchemy import text
            result = db.execute(text(f"SELECT id FROM devices WHERE device_id = '{device_id}'")).fetchone()
            
            if not result:
                # Tạo thiết bị mới
                db.execute(text(f"""
                    INSERT INTO devices (device_id, name, description, created_at) 
                    VALUES ('{device_id}', 'Adafruit IO Device', 'Thiết bị dữ liệu từ Adafruit IO', NOW())
                """))
                db.commit()
                logger.info(f"Đã tạo thiết bị với ID: {device_id}")
            
            db.close()
            return True
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra thiết bị: {str(e)}")
            if db:
                db.close()
            return False
    
    def get_feeds(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách tất cả feeds từ Adafruit IO
        
        Returns:
            Danh sách các feed
        """
        try:
            url = f"{self.base_url}/feeds"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                feeds = response.json()
                logger.info(f"Đã lấy được {len(feeds)} feeds từ Adafruit IO")
                return feeds
            else:
                logger.error(f"Lỗi khi lấy feeds: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy feeds: {str(e)}")
            return []
    
    def get_feed_data(self, feed_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu từ một feed cụ thể
        
        Args:
            feed_key: Feed key/ID
            limit: Số lượng bản ghi cần lấy
            
        Returns:
            Danh sách dữ liệu từ feed
        """
        try:
            url = f"{self.base_url}/feeds/{feed_key}/data"
            params = {"limit": limit}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Đã lấy được {len(data)} điểm dữ liệu từ feed {feed_key}")
                return data
            else:
                logger.error(f"Lỗi khi lấy dữ liệu feed {feed_key}: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu feed: {str(e)}")
            return []
    
    def save_to_database(self, feed_id: str, data_points: List[Dict[str, Any]]) -> int:
        """
        Lưu dữ liệu từ Adafruit IO vào database
        
        Args:
            feed_id: ID của feed
            data_points: Danh sách các điểm dữ liệu
            
        Returns:
            Số lượng bản ghi đã lưu
        """
        try:
            self._ensure_device_exists()
            db = self.SessionLocal()
            count = 0
            
            for point in data_points:
                try:
                    # Lấy giá trị và chuyển đổi sang số
                    value_str = point.get("value", "0")
                    try:
                        value = float(value_str)
                    except (ValueError, TypeError):
                        value = 0.0
                    
                    # Xử lý timestamp
                    timestamp_str = point.get("created_at")
                    if timestamp_str:
                        try:
                            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            timestamp = datetime.datetime.utcnow()
                    else:
                        timestamp = datetime.datetime.utcnow()
                    
                    # Tạo bản ghi mới
                    new_data = SensorData(
                        device_id="default",
                        feed_id=feed_id,
                        value=value,
                        raw_data=json.dumps(point),
                        timestamp=timestamp
                    )
                    
                    db.add(new_data)
                    count += 1
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý điểm dữ liệu: {str(e)}")
            
            db.commit()
            logger.info(f"Đã lưu {count} điểm dữ liệu vào database")
            db.close()
            return count
        except Exception as e:
            logger.error(f"Lỗi khi lưu vào database: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
            return 0
    
    def fetch_and_save(self, feed_id: Optional[str] = None, limit: int = 10) -> int:
        """
        Lấy dữ liệu từ một hoặc tất cả feeds và lưu vào database
        
        Args:
            feed_id: ID của feed (nếu None thì lấy tất cả feeds)
            limit: Số lượng bản ghi cần lấy cho mỗi feed
            
        Returns:
            Tổng số bản ghi đã lưu
        """
        total_saved = 0
        
        if feed_id:
            # Lấy dữ liệu từ feed cụ thể
            data = self.get_feed_data(feed_id, limit)
            saved = self.save_to_database(feed_id, data)
            total_saved += saved
        else:
            # Lấy danh sách tất cả feeds
            feeds = self.get_feeds()
            for feed in feeds:
                feed_key = feed.get("key")
                if feed_key:
                    data = self.get_feed_data(feed_key, limit)
                    saved = self.save_to_database(feed_key, data)
                    total_saved += saved
                    # Tạm dừng để tránh rate limit
                    time.sleep(1)
        
        return total_saved

def main():
    parser = argparse.ArgumentParser(description="Lấy dữ liệu từ Adafruit IO và lưu vào database")
    parser.add_argument("--username", type=str, help="Adafruit IO username")
    parser.add_argument("--key", type=str, help="Adafruit IO key")
    parser.add_argument("--feed", type=str, help="Feed ID (nếu không cung cấp sẽ lấy tất cả feeds)")
    parser.add_argument("--limit", type=int, default=10, help="Số lượng bản ghi cần lấy cho mỗi feed (mặc định: 10)")
    
    args = parser.parse_args()
    
    # Sử dụng giá trị từ tham số dòng lệnh hoặc biến môi trường
    username = args.username or os.getenv("ADAFRUIT_IO_USERNAME")
    key = args.key or os.getenv("ADAFRUIT_IO_KEY")
    
    if not username or not key:
        logger.error("Thiếu thông tin đăng nhập Adafruit IO. Vui lòng cung cấp qua tham số hoặc biến môi trường.")
        sys.exit(1)
    
    try:
        client = FetchAdafruitData(username, key)
        total_saved = client.fetch_and_save(args.feed, args.limit)
        
        logger.info(f"Tổng số bản ghi đã lưu: {total_saved}")
        print(f"Đã lấy và lưu thành công {total_saved} bản ghi từ Adafruit IO")
    except Exception as e:
        logger.error(f"Lỗi khi thực thi: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 