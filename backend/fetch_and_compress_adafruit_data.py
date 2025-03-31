#!/usr/bin/env python3
"""
Script lấy dữ liệu từ Adafruit IO trong khoảng thời gian cụ thể và tùy chọn nén dữ liệu

Cách sử dụng:
    python fetch_and_compress_adafruit_data.py --start-date 2023-11-20 --end-date 2023-11-21 --compress
    python fetch_and_compress_adafruit_data.py --start-date 2023-11-20 --end-date 2023-11-21
    
    Tham số:
    --start-date: Ngày bắt đầu lấy dữ liệu (định dạng YYYY-MM-DD)
    --end-date: Ngày kết thúc lấy dữ liệu (định dạng YYYY-MM-DD, mặc định: ngày bắt đầu)
    --compress: Nén dữ liệu trước khi lưu vào database
    --limit: Số lượng bản ghi cần lấy cho mỗi feed (mặc định: 1000)
    --force-reload: Bỏ qua kiểm tra trùng lặp, tải lại tất cả dữ liệu
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
import requests
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import numpy as np
from scipy import stats

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging
log_file = 'fetch_adafruit_and_compress.log'
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

# Tạo models
Base = declarative_base()

class SensorData(Base):
    """Model cho dữ liệu cảm biến chưa nén"""
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    feed_id = Column(String, index=True)
    value = Column(Float)
    raw_data = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class CompressedData(Base):
    """Model cho dữ liệu cảm biến đã nén"""
    __tablename__ = "compressed_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    compressed_data = Column(JSONB)  # Dữ liệu đã nén
    compression_ratio = Column(Float)  # Tỷ lệ nén
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class IDEALEMCompressor:
    """
    Thuật toán nén IDEALEM sử dụng khoảng cách tương đồng
    để phát hiện mẫu giữa các chuỗi dữ liệu
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo IDEALEM compressor với cấu hình
        """
        # Cấu hình mặc định
        default_config = {
            "p_threshold": 0.7,       # Ngưỡng tương đồng (>0.7 coi là tương tự)
            "max_templates": 100,     # Số lượng mẫu tối đa
            "min_values": 1,          # Số lượng giá trị tối thiểu để so sánh
            "similarity_factor": 20,  # Hệ số cho phép tìm mẫu tương tự 
        }
        
        self.config = default_config
        if config:
            self.config.update(config)
            
        # Trạng thái nội bộ
        self.templates = {}                    # Từ điển lưu các mẫu
        self.template_counts = {}              # Đếm số lần mỗi mẫu được sử dụng
        self.template_id_counter = 0           # Bộ đếm ID cho mẫu mới
        self.compressed_size_history = []      # Lịch sử kích thước đã nén
        self.original_size_history = []        # Lịch sử kích thước gốc
        self.data_count = 0                    # Tổng số điểm dữ liệu đã xử lý
        self.hits = 0                          # Số lần trúng mẫu
        self.trials = 0                        # Số lần thử nghiệm
        
        logger.info(f"IDEALEM Compressor đã được khởi tạo với cấu hình: {self.config}")
    
    def _extract_values(self, data_point: Dict[str, Any]) -> List[float]:
        """
        Trích xuất giá trị từ điểm dữ liệu Adafruit
        """
        values = []
        
        try:
            # Nếu dữ liệu đã là một giá trị số
            if isinstance(data_point.get('value'), (int, float)):
                values.append(float(data_point['value']))
                return values
                
            # Nếu dữ liệu là chuỗi có thể chuyển đổi
            if isinstance(data_point.get('value'), str):
                try:
                    values.append(float(data_point['value']))
                    return values
                except (ValueError, TypeError):
                    pass
            
            # Nếu có raw_data dạng JSON
            if 'raw_data' in data_point and data_point['raw_data']:
                try:
                    raw_data = json.loads(data_point['raw_data'])
                    
                    if isinstance(raw_data, dict):
                        if 'value' in raw_data and isinstance(raw_data['value'], (int, float, str)):
                            try:
                                values.append(float(raw_data['value']))
                            except (ValueError, TypeError):
                                pass
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất giá trị: {str(e)}")
        
        return values
    
    def _calculate_similarity(self, template: List[float], data: List[float]) -> float:
        """
        Tính độ tương đồng giữa template và dữ liệu mới
        """
        if len(template) < self.config["min_values"] or len(data) < self.config["min_values"]:
            return 0.0  # Không đủ giá trị để so sánh
            
        try:
            # Đảm bảo hai chuỗi có cùng độ dài
            if len(template) != len(data):
                min_len = min(len(template), len(data))
                template = template[:min_len]
                data = data[:min_len]
                
            # Tính khoảng cách tương đối trung bình
            total_diff = 0
            count = 0
            
            for t_val, d_val in zip(template, data):
                if t_val == 0 and d_val == 0:
                    continue
                    
                rel_diff = abs(t_val - d_val) / max(abs(t_val), abs(d_val), 1.0)
                total_diff += rel_diff
                count += 1
                
            if count == 0:
                return 0.0
                
            avg_diff = total_diff / count
            
            # Chuyển đổi khoảng cách thành độ tương đồng (0-1)
            similarity = max(0, 1.0 - avg_diff * self.config["similarity_factor"])
            
            return similarity
            
        except Exception as e:
            logger.error(f"Lỗi khi tính độ tương đồng: {str(e)}")
            return 0.0
            
    def _find_matching_template(self, data: List[float]) -> Tuple[int, float]:
        """
        Tìm mẫu phù hợp nhất với dữ liệu hiện tại
        """
        best_match = -1
        best_p_value = 0.0
        
        # Kiểm tra từng mẫu trong bộ nhớ
        for template_id, template_data in self.templates.items():
            p_value = self._calculate_similarity(template_data, data)
            if p_value > self.config["p_threshold"] and p_value > best_p_value:
                best_match = template_id
                best_p_value = p_value
                
        return best_match, best_p_value
    
    def _add_new_template(self, data: List[float]) -> int:
        """
        Thêm mẫu mới vào bộ nhớ
        """
        template_id = self.template_id_counter
        self.templates[template_id] = data.copy()
        self.template_counts[template_id] = 1
        self.template_id_counter += 1
        
        # Nếu vượt quá số lượng mẫu tối đa, loại bỏ mẫu ít sử dụng nhất
        if len(self.templates) > self.config["max_templates"]:
            least_used = min(self.template_counts, key=self.template_counts.get)
            del self.templates[least_used]
            del self.template_counts[least_used]
            
        return template_id
    
    def _calculate_size_bytes(self, data: Any) -> int:
        """
        Tính kích thước dữ liệu theo bytes
        """
        return len(json.dumps(data).encode('utf-8'))
        
    def compress(self, data_point: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Nén dữ liệu
        """
        start_time = time.time()
        
        # Tạo bản sao để không ảnh hưởng đến dữ liệu gốc
        compressed_data = data_point.copy()
        
        # Trích xuất các giá trị trong data_point
        values = self._extract_values(data_point)
        
        # Nếu không trích xuất được giá trị
        if not values:
            # Tạo thống kê
            stats = {
                "original_size_bytes": self._calculate_size_bytes(data_point),
                "compressed_size_bytes": self._calculate_size_bytes(compressed_data),
                "compression_ratio": 1.0,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "is_valid": False,
                "error": "Không thể trích xuất giá trị từ dữ liệu"
            }
            
            return compressed_data, stats
        
        # Tăng bộ đếm
        self.data_count += 1
        self.trials += 1
        
        # Tìm mẫu phù hợp
        best_match, best_p_value = self._find_matching_template(values)
        
        # Kiểm tra có hit (tìm được mẫu phù hợp) hay không
        is_hit = best_match >= 0 and best_p_value > self.config["p_threshold"]
        
        if is_hit:
            # Trúng mẫu, sử dụng ID và tăng số lần sử dụng
            self.hits += 1
            self.template_counts[best_match] += 1
            template_id = best_match
            
            # Thêm metadata cho trường hợp hit
            if 'compression_meta' not in compressed_data:
                compressed_data['compression_meta'] = {}
                
            compressed_data['compression_meta']['template_id'] = template_id
            compressed_data['compression_meta']['p_value'] = best_p_value
            compressed_data['compression_meta']['algorithm'] = 'idealem'
            compressed_data['compression_meta']['timestamp'] = datetime.datetime.now().isoformat()
            compressed_data['compression_meta']['is_hit'] = True
        else:
            # Không tìm thấy mẫu phù hợp, tạo mẫu mới
            template_id = self._add_new_template(values)
            
            # Thêm metadata cho trường hợp template mới
            if 'compression_meta' not in compressed_data:
                compressed_data['compression_meta'] = {}
                
            compressed_data['compression_meta']['template_id'] = template_id
            compressed_data['compression_meta']['algorithm'] = 'idealem'
            compressed_data['compression_meta']['timestamp'] = datetime.datetime.now().isoformat()
            compressed_data['compression_meta']['is_template'] = True
        
        # Tính kích thước trước và sau khi nén
        original_size = self._calculate_size_bytes(data_point)
        compressed_size = self._calculate_size_bytes(compressed_data)
        
        # Tính tỷ lệ nén
        compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
        
        # Lưu lịch sử kích thước
        self.original_size_history.append(original_size)
        self.compressed_size_history.append(compressed_size)
        
        # Thời gian xử lý
        processing_time = (time.time() - start_time) * 1000  # ms
        
        # Tạo thống kê
        stats = {
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": compression_ratio,
            "processing_time_ms": processing_time,
            "hit_ratio": self.hits / self.trials if self.trials > 0 else 0.0,
            "is_template": not is_hit,
            "is_valid": True
        }
        
        return compressed_data, stats
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê tổng thể
        """
        # Tính kích thước trung bình và tỷ lệ nén
        avg_original_size = sum(self.original_size_history) / len(self.original_size_history) if self.original_size_history else 0
        avg_compressed_size = sum(self.compressed_size_history) / len(self.compressed_size_history) if self.compressed_size_history else 0
        overall_compression_ratio = avg_original_size / avg_compressed_size if avg_compressed_size > 0 else 1.0
        
        return {
            "data_count": self.data_count,
            "template_count": len(self.templates),
            "hit_ratio": self.hits / self.trials if self.trials > 0 else 0.0,
            "trials": self.trials,
            "hits": self.hits,
            "overall_compression_ratio": overall_compression_ratio,
            "avg_original_size": avg_original_size,
            "avg_compressed_size": avg_compressed_size
        }

class AdafruitIOFetcher:
    """
    Lớp để lấy dữ liệu từ Adafruit IO và tùy chọn nén
    """
    
    def __init__(self, username: str = None, key: str = None, 
                 compress: bool = False, force_reload: bool = False):
        """
        Khởi tạo fetcher để lấy dữ liệu từ Adafruit IO
        
        Args:
            username: Adafruit IO username
            key: Adafruit IO key
            compress: Có nén dữ liệu trước khi lưu vào database hay không
            force_reload: Bỏ qua kiểm tra trùng lặp nếu True
        """
        self.username = username or os.getenv("ADAFRUIT_IO_USERNAME")
        self.key = key or os.getenv("ADAFRUIT_IO_KEY")
        self.compress = compress
        self.force_reload = force_reload
        
        if not self.username or not self.key:
            error_msg = "Thiếu thông tin đăng nhập Adafruit IO. Vui lòng cung cấp qua tham số hoặc biến môi trường."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.base_url = f"https://io.adafruit.com/api/v2/{self.username}"
        self.headers = {
            "X-AIO-Key": self.key,
            "Content-Type": "application/json"
        }
        
        # Khởi tạo compressor nếu cần
        self.compressor = None
        if self.compress:
            self.compressor = IDEALEMCompressor()
            logger.info("Đã khởi tạo IDEALEM Compressor")
        
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
                # Nếu không có bảng devices, lưu trực tiếp vào SensorData
                logger.warning("Bảng devices không tồn tại, lưu trực tiếp vào bảng dữ liệu")
                db.close()
                return True
                
            # Nếu có bảng devices, kiểm tra và tạo thiết bị nếu cần
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
            if 'db' in locals():
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
    
    def get_feed_data_for_date_range(self, feed_key: str, start_date: datetime.date, 
                                    end_date: datetime.date, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu từ một feed cho một khoảng thời gian cụ thể
        
        Args:
            feed_key: Feed key/ID
            start_date: Ngày bắt đầu
            end_date: Ngày kết thúc
            limit: Số lượng bản ghi tối đa cần lấy
            
        Returns:
            Danh sách dữ liệu từ feed
        """
        try:
            # Tạo thời gian bắt đầu và kết thúc (00:00 của ngày bắt đầu và 23:59:59 của ngày kết thúc)
            start_time = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
            end_time = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=datetime.timezone.utc)
            
            start_time_str = start_time.isoformat()
            end_time_str = end_time.isoformat()
            
            url = f"{self.base_url}/feeds/{feed_key}/data"
            params = {
                "limit": limit,
                "start_time": start_time_str,
                "end_time": end_time_str
            }
                
            logger.info(f"Lấy dữ liệu feed {feed_key} từ {start_time_str} đến {end_time_str}")
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Đã lấy được {len(data)} điểm dữ liệu từ feed {feed_key} từ {start_date} đến {end_date}")
                return data
            else:
                logger.error(f"Lỗi khi lấy dữ liệu feed {feed_key}: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu feed: {str(e)}")
            return []
    
    def save_to_sensor_data(self, feed_id: str, data_points: List[Dict[str, Any]]) -> int:
        """
        Lưu dữ liệu từ Adafruit IO vào bảng sensor_data (không nén)
        
        Args:
            feed_id: ID của feed
            data_points: Danh sách các điểm dữ liệu
            
        Returns:
            Số lượng bản ghi đã lưu
        """
        try:
            if not data_points:
                logger.info(f"Không có dữ liệu từ feed {feed_id}")
                return 0
                
            self._ensure_device_exists()
            db = self.SessionLocal()
            count = 0
            
            for point in data_points:
                try:
                    # Kiểm tra trùng lặp nếu không force_reload
                    if not self.force_reload:
                        point_id = point.get("id")
                        if point_id:
                            # Kiểm tra xem điểm dữ liệu đã tồn tại trong database chưa
                            result = db.execute(text(
                                f"SELECT id FROM sensor_data WHERE raw_data LIKE '%{point_id}%' LIMIT 1"
                            )).fetchone()
                            
                            if result:
                                logger.debug(f"Bỏ qua điểm dữ liệu {point_id} (đã tồn tại)")
                                continue
                
                    # Xử lý giá trị và chuyển đổi sang số
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
            
            if count > 0:
                db.commit()
                logger.info(f"Đã lưu {count} điểm dữ liệu mới vào bảng sensor_data từ feed {feed_id}")
            
            db.close()
            return count
        except Exception as e:
            logger.error(f"Lỗi khi lưu vào database: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
            return 0
    
    def save_to_compressed_data(self, feed_id: str, data_points: List[Dict[str, Any]]) -> int:
        """
        Nén dữ liệu từ Adafruit IO và lưu vào bảng compressed_data
        
        Args:
            feed_id: ID của feed
            data_points: Danh sách các điểm dữ liệu
            
        Returns:
            Số lượng bản ghi đã lưu
        """
        try:
            if not data_points:
                logger.info(f"Không có dữ liệu từ feed {feed_id}")
                return 0
            
            if not self.compressor:
                logger.error("Compressor chưa được khởi tạo")
                return 0
                
            self._ensure_device_exists()
            db = self.SessionLocal()
            count = 0
            
            for point in data_points:
                try:
                    # Kiểm tra trùng lặp nếu không force_reload
                    if not self.force_reload:
                        point_id = point.get("id")
                        if point_id:
                            # Kiểm tra xem điểm dữ liệu đã tồn tại trong database chưa
                            result = db.execute(text(
                                f"SELECT id FROM compressed_data WHERE compressed_data::text LIKE '%{point_id}%' LIMIT 1"
                            )).fetchone()
                            
                            if result:
                                logger.debug(f"Bỏ qua điểm dữ liệu {point_id} (đã tồn tại)")
                                continue
                    
                    # Xử lý timestamp
                    timestamp_str = point.get("created_at")
                    if timestamp_str:
                        try:
                            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            timestamp = datetime.datetime.utcnow()
                    else:
                        timestamp = datetime.datetime.utcnow()
                    
                    # Tạo dữ liệu có cấu trúc phù hợp cho compressor
                    structured_data = {
                        "device_id": "default",
                        "feed_id": feed_id,
                        "value": point.get("value"),
                        "raw_data": json.dumps(point),
                        "timestamp": timestamp.isoformat() if timestamp else None
                    }
                    
                    # Nén dữ liệu
                    compressed_data, stats = self.compressor.compress(structured_data)
                    
                    # Kiểm tra xem quá trình nén có thành công không
                    if not stats.get("is_valid", False):
                        logger.warning(f"Không thể nén dữ liệu: {stats.get('error', 'Lỗi không xác định')}")
                        continue
                    
                    # Tạo bản ghi mới
                    new_data = CompressedData(
                        device_id="default",
                        compressed_data=compressed_data,
                        compression_ratio=stats["compression_ratio"],
                        timestamp=timestamp
                    )
                    
                    db.add(new_data)
                    count += 1
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý điểm dữ liệu nén: {str(e)}")
            
            if count > 0:
                db.commit()
                logger.info(f"Đã lưu {count} điểm dữ liệu nén vào bảng compressed_data từ feed {feed_id}")
                
                # In thống kê nén
                stats = self.compressor.get_stats()
                logger.info(f"Thống kê nén: {len(data_points)} điểm dữ liệu -> {stats['template_count']} templates")
                logger.info(f"Tỷ lệ nén: {stats['overall_compression_ratio']:.2f}, Tỷ lệ hit: {stats['hit_ratio']:.2f}")
            
            db.close()
            return count
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu nén vào database: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
            return 0
    
    def fetch_and_save_for_date_range(self, start_date: datetime.date, end_date: datetime.date, limit: int = 1000) -> Dict[str, Any]:
        """
        Lấy dữ liệu từ tất cả feeds cho một khoảng thời gian cụ thể và lưu vào database
        
        Args:
            start_date: Ngày bắt đầu
            end_date: Ngày kết thúc
            limit: Số lượng bản ghi cần lấy cho mỗi feed
            
        Returns:
            Thống kê về số lượng bản ghi đã lưu
        """
        total_stats = {
            "total_feeds": 0,
            "total_data_points": 0,
            "total_saved": 0,
            "compress": self.compress,
            "feeds_data": {}
        }
        
        logger.info(f"Bắt đầu lấy dữ liệu từ {start_date} đến {end_date} với tối đa {limit} bản ghi cho mỗi feed")
        
        # Lấy danh sách tất cả feeds
        feeds = self.get_feeds()
        if not feeds:
            logger.warning("Không thể lấy danh sách feeds. Vui lòng kiểm tra kết nối hoặc thông tin đăng nhập Adafruit IO.")
            return total_stats
            
        total_stats["total_feeds"] = len(feeds)
        logger.info(f"Tìm thấy {len(feeds)} feeds từ Adafruit IO")
        
        for feed in feeds:
            feed_key = feed.get("key")
            feed_name = feed.get("name", "Không có tên")
            
            if feed_key:
                logger.info(f"Đang xử lý feed: {feed_name} (key: {feed_key})")
                
                # Lấy dữ liệu từ feed
                data = self.get_feed_data_for_date_range(feed_key, start_date, end_date, limit)
                total_stats["total_data_points"] += len(data)
                
                # Lưu thống kê cho feed
                feed_stats = {
                    "name": feed_name,
                    "data_points": len(data),
                    "saved": 0
                }
                
                # Lưu dữ liệu vào database
                if self.compress:
                    # Nén dữ liệu và lưu vào bảng compressed_data
                    saved = self.save_to_compressed_data(feed_key, data)
                else:
                    # Lưu trực tiếp vào bảng sensor_data
                    saved = self.save_to_sensor_data(feed_key, data)
                
                feed_stats["saved"] = saved
                total_stats["total_saved"] += saved
                total_stats["feeds_data"][feed_key] = feed_stats
                
                logger.info(f"Đã lưu {saved}/{len(data)} bản ghi từ feed {feed_name}")
                
                # Tạm dừng một chút giữa các request để tránh giới hạn rate
                time.sleep(0.5)
        
        return total_stats

def validate_date(date_string: str) -> datetime.date:
    """
    Kiểm tra và chuyển đổi chuỗi ngày thành đối tượng date
    
    Args:
        date_string: Chuỗi ngày (YYYY-MM-DD)
        
    Returns:
        Đối tượng date
        
    Raises:
        ValueError: Nếu chuỗi ngày không hợp lệ
    """
    try:
        return datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Định dạng ngày không hợp lệ: {date_string}. Vui lòng sử dụng định dạng YYYY-MM-DD.")

def main():
    parser = argparse.ArgumentParser(description="Lấy dữ liệu từ Adafruit IO trong khoảng thời gian cụ thể và tùy chọn nén")
    parser.add_argument("--start-date", type=str, required=True, help="Ngày bắt đầu lấy dữ liệu (định dạng YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Ngày kết thúc lấy dữ liệu (định dạng YYYY-MM-DD, mặc định: ngày bắt đầu)")
    parser.add_argument("--compress", action="store_true", help="Nén dữ liệu trước khi lưu vào database")
    parser.add_argument("--limit", type=int, default=1000, help="Số lượng bản ghi cần lấy cho mỗi feed (mặc định: 1000)")
    parser.add_argument("--force-reload", action="store_true", help="Bỏ qua kiểm tra trùng lặp, tải lại tất cả dữ liệu")
    parser.add_argument("--username", type=str, help="Adafruit IO username")
    parser.add_argument("--key", type=str, help="Adafruit IO key")
    
    args = parser.parse_args()
    
    try:
        # Xử lý tham số ngày
        start_date = validate_date(args.start_date)
        
        if args.end_date:
            end_date = validate_date(args.end_date)
            # Đảm bảo end_date >= start_date
            if end_date < start_date:
                logger.warning(f"Ngày kết thúc {end_date} trước ngày bắt đầu {start_date}, đang hoán đổi")
                start_date, end_date = end_date, start_date
        else:
            end_date = start_date
        
        logger.info(f"Đang lấy dữ liệu từ {start_date} đến {end_date}")
        if args.compress:
            logger.info("Chế độ NÉN DỮ LIỆU: Dữ liệu sẽ được nén trước khi lưu vào database")
        if args.force_reload:
            logger.info("Chế độ FORCE RELOAD: Bỏ qua kiểm tra trùng lặp, tải lại tất cả dữ liệu")
        
        # Khởi tạo fetcher
        fetcher = AdafruitIOFetcher(
            username=args.username,
            key=args.key,
            compress=args.compress,
            force_reload=args.force_reload
        )
        
        # Lấy và lưu dữ liệu
        stats = fetcher.fetch_and_save_for_date_range(start_date, end_date, args.limit)
        
        # In kết quả
        print("\n" + "="*80)
        print(f"KẾT QUẢ LẤY DỮ LIỆU TỪ ADAFRUIT IO: {start_date} đến {end_date}")
        print(f"- Số lượng feeds: {stats['total_feeds']}")
        print(f"- Tổng số điểm dữ liệu: {stats['total_data_points']}")
        print(f"- Tổng số điểm dữ liệu đã lưu: {stats['total_saved']}")
        print(f"- Chế độ nén: {'BẬT' if stats['compress'] else 'TẮT'}")
        
        # Chi tiết từng feed
        print("\nChi tiết theo feed:")
        for feed_key, feed_stats in stats.get('feeds_data', {}).items():
            print(f"  + {feed_stats['name']} ({feed_key}): {feed_stats['saved']}/{feed_stats['data_points']} điểm dữ liệu")
        
        print("="*80)
        
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Lỗi khi thực thi: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 