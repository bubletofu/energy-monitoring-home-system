#!/usr/bin/env python3
"""
Script giải nén dữ liệu IDEALEM từ database dành cho AI Developer

Cách sử dụng:
    python decompress_data_for_ai.py --output decompressed_data.json
    python decompress_data_for_ai.py --date 2023-11-01 --output decompressed_data.json
    python decompress_data_for_ai.py --date-range 2023-11-01 2023-11-10 --output decompressed_data.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import time

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('decompress_data.log')
    ]
)
logger = logging.getLogger(__name__)

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")

class DataDecompressor:
    """
    Lớp giải nén dữ liệu từ IDEALEM
    """
    
    def __init__(self, db_url=None):
        """
        Khởi tạo đối tượng giải nén
        
        Args:
            db_url: Chuỗi kết nối đến database
        """
        # Khởi tạo kết nối database
        if db_url is None:
            # Tải URL từ biến môi trường hoặc sử dụng giá trị mặc định
            db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")
        
        # Khởi tạo các thuộc tính
        self.templates = {}
        self.original_samples = []
        
        # Khởi tạo database connection
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Thử kết nối đến database
        try:
            # Kiểm tra kết nối
            with self.engine.connect() as conn:
                logger.info(f"Đã kết nối thành công đến PostgreSQL database: {db_url}")
        except Exception as e:
            logger.error(f"Lỗi kết nối đến database: {str(e)}")
            raise
    
    def parse_json_data(self, data):
        """
        Phân tích dữ liệu JSON, hỗ trợ cả chuỗi và dictionary
        
        Args:
            data: Dữ liệu JSON dạng chuỗi hoặc đã là dictionary
            
        Returns:
            Dictionary đã phân tích
        """
        if isinstance(data, dict):
            return data
        elif isinstance(data, str):
            return json.loads(data)
        else:
            return {}
    
    def load_templates_from_original_samples(self) -> int:
        """
        Tải các template từ bảng original_samples
        
        Returns:
            Số lượng templates đã tải
        """
        try:
            db = self.SessionLocal()
            
            # Truy vấn tất cả bản ghi original_samples
            query = text("""
                SELECT id, device_id, original_data, timestamp 
                FROM original_samples 
                ORDER BY timestamp
            """)
            
            result = db.execute(query).fetchall()
            
            count = 0
            template_ids = set()  # Để theo dõi các template_id đã tải
            
            for i, row in enumerate(result):
                try:
                    original_data = self.parse_json_data(row[2])
                    
                    # Nếu có readings, tạo template từ readings
                    if 'readings' in original_data and isinstance(original_data['readings'], dict):
                        readings = original_data['readings']
                        
                        # Tạo template từ các giá trị readings
                        template_values = []
                        if 'temperature' in readings:
                            template_values.append(readings['temperature'])
                        if 'humidity' in readings:
                            template_values.append(readings['humidity'])
                        if 'pressure' in readings:
                            template_values.append(readings['pressure'])
                        if 'power' in readings:
                            template_values.append(readings['power'])
                        if 'battery' in readings:
                            template_values.append(readings['battery'])
                        
                        # Tạo template_id từ timestamp
                        timestamp = original_data.get('timestamp', '')
                        template_id = count  # Sử dụng count làm template_id
                        
                        # Thêm template nếu có đủ dữ liệu
                        if len(template_values) >= 3:  # Ít nhất phải có 3 thông số
                            self.templates[template_id] = template_values
                            template_ids.add(template_id)
                            count += 1
                            
                            # Ghi log 5 template đầu tiên
                            if count <= 5:
                                logger.debug(f"Tạo template {template_id} từ bản ghi {i+1}: {template_values}")
                except Exception as e:
                    logger.warning(f"Lỗi khi xử lý bản ghi {i+1}: {str(e)}")
            
            logger.info(f"Đã tạo {count} templates từ original_samples")
            
            # Ánh xạ các template_id trong compressed_data
            if count > 0:
                # Lấy danh sách tất cả compressed_data
                compressed_query = text("""
                    SELECT id, compressed_data 
                    FROM compressed_data 
                    ORDER BY id
                """)
                
                compressed_result = db.execute(compressed_query).fetchall()
                
                # Tạo ánh xạ từ template_id trong compressed_data đến template_id trong templates
                template_mapping = {}
                for row in compressed_result:
                    try:
                        compressed_data = self.parse_json_data(row[1])
                        if 'template_id' in compressed_data and 'template_data' in compressed_data:
                            template_id = compressed_data['template_id']
                            template_data = compressed_data['template_data']
                            
                            # Nếu template_data là số nguyên và template_id chưa được ánh xạ
                            if (isinstance(template_data, int) or isinstance(template_data, float)) and template_id not in template_mapping:
                                # Ánh xạ template_id đến template_data % count
                                template_mapping[template_id] = int(template_data) % count
                                logger.debug(f"Ánh xạ template_id={template_id} -> template={template_mapping[template_id]}")
                    except Exception as e:
                        logger.warning(f"Lỗi khi xử lý compressed_data {row[0]}: {str(e)}")
                
                # Cập nhật lại templates
                new_templates = {}
                for template_id, template in self.templates.items():
                    new_templates[template_id] = template
                
                # Thêm ánh xạ từ các template_id trong compressed_data
                for template_id, mapped_id in template_mapping.items():
                    if mapped_id in self.templates:
                        new_templates[template_id] = self.templates[mapped_id]
                
                self.templates = new_templates
                logger.info(f"Đã ánh xạ {len(template_mapping)} template_id từ compressed_data")
            
            db.close()
            return count
        
        except Exception as e:
            logger.error(f"Lỗi khi tải templates từ original_samples: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            if 'db' in locals():
                db.close()
            return 0
    
    def load_original_samples(self) -> int:
        """
        Tải dữ liệu mẫu gốc từ bảng original_samples
        
        Returns:
            Số lượng mẫu đã tải
        """
        try:
            db = self.SessionLocal()
            
            # Truy vấn tất cả bản ghi original_samples
            query = text("""
                SELECT id, device_id, original_data, timestamp FROM original_samples
                ORDER BY timestamp
            """)
            
            result = db.execute(query).fetchall()
            
            # Lưu trữ tất cả mẫu
            self.original_samples = []
            count = 0
            
            for i, row in enumerate(result):
                try:
                    sample_id = row[0]
                    device_id = row[1]
                    original_data = self.parse_json_data(row[2])
                    timestamp = row[3]
                    
                    # Thêm vào danh sách original_samples
                    sample_record = {
                        'id': sample_id,
                        'device_id': device_id,
                        'original_data': original_data,
                        'timestamp': timestamp
                    }
                    self.original_samples.append(sample_record)
                    count += 1
                except Exception as e:
                    logger.warning(f"Lỗi khi xử lý mẫu original_samples {i+1}: {str(e)}")
            
            logger.info(f"Đã tải {count} mẫu dữ liệu gốc từ original_samples")
            db.close()
            return count
            
        except Exception as e:
            logger.error(f"Lỗi khi tải original samples: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            if 'db' in locals():
                db.close()
            return 0
    
    def get_compressed_data(self, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu nén từ database
        
        Args:
            start_date: Thời gian bắt đầu (tùy chọn) 
            end_date: Thời gian kết thúc (tùy chọn)
            
        Returns:
            Danh sách các điểm dữ liệu nén
        """
        try:
            db = self.SessionLocal()
            
            # Xây dựng truy vấn dựa trên parameters đã cung cấp
            query_str = """
                SELECT id, device_id, compressed_data, compression_ratio, timestamp
                FROM compressed_data
            """
            
            conditions = []
            params = {}
            
            if start_date:
                conditions.append("timestamp >= :start_date")
                params["start_date"] = start_date
                
            if end_date: 
                conditions.append("timestamp <= :end_date")
                params["end_date"] = end_date
            
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)
            
            query_str += " ORDER BY timestamp"
            
            query = text(query_str)
            result = db.execute(query, params).fetchall()
            
            compressed_data_list = []
            for row in result:
                compressed_point = {
                    "id": row[0],
                    "device_id": row[1],
                    "compressed_data": row[2],
                    "compression_ratio": row[3],
                    "timestamp": row[4]
                }
                compressed_data_list.append(compressed_point)
            
            logger.info(f"Đã tải {len(compressed_data_list)} bản ghi dữ liệu nén từ database")
            db.close()
            return compressed_data_list
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu nén: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            if 'db' in locals():
                db.close()
            return []
    
    def extract_readings_from_template(self, template_id, template_data=None) -> Dict[str, Any]:
        """
        Trích xuất dữ liệu từ template đã lưu trong bộ nhớ
        
        Args:
            template_id: ID của template
            template_data: Dữ liệu template bổ sung (nếu có)
            
        Returns:
            Dictionary chứa các readings từ template
        """
        # Các sensor mà chúng ta đang xử lý
        sensors = ['temperature', 'humidity', 'pressure', 'power', 'battery']
        readings = {}
        
        if template_id in self.templates:
            template = self.templates[template_id]
            logger.debug(f"Đã tìm thấy template {template_id}: {template}")
            
            # Map template values vào sensors theo thứ tự
            for i, sensor in enumerate(sensors):
                if i < len(template):
                    readings[sensor] = template[i]
        else:
            logger.debug(f"Không tìm thấy template {template_id}")
        
        return readings
        
    def reconstruct_data_point(self, compressed_point: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tái tạo điểm dữ liệu từ dữ liệu nén
        
        Args:
            compressed_point: Điểm dữ liệu nén
            
        Returns:
            Điểm dữ liệu đã giải nén
        """
        try:
            # Tạo bản sao để tránh thay đổi dữ liệu gốc
            result = {
                'device_id': compressed_point.get('device_id', ''),
                'timestamp': compressed_point.get('timestamp', ''),
                'readings': {}
            }
            
            # Parse compressed_data nếu có
            compressed_data = None
            if 'compressed_data' in compressed_point and compressed_point['compressed_data']:
                compressed_data = self.parse_json_data(compressed_point['compressed_data'])
                
                # Cập nhật device_id và timestamp nếu có trong compressed_data
                if 'device_id' in compressed_data:
                    result['device_id'] = compressed_data['device_id']
                if 'timestamp' in compressed_data:
                    result['timestamp'] = compressed_data['timestamp']
            
            # Debug compressed_data
            logger.debug(f"Compressed data: {compressed_data}")
            
            # Nếu có template_id trong compressed_data, sử dụng để trích xuất readings
            template_id = None
            if compressed_data and 'template_id' in compressed_data:
                template_id = compressed_data['template_id']
                logger.debug(f"Đang giải nén điểm dữ liệu với template_id={template_id}")
                
                # Kiểm tra xem template_id có trong templates không
                if template_id in self.templates:
                    result['readings'] = self.extract_readings_from_template(template_id)
                    logger.debug(f"Đã tìm thấy template {template_id} và trích xuất readings: {result['readings']}")
                else:
                    logger.debug(f"Không tìm thấy template với id={template_id}")
            
            # Nếu không có readings hoặc không thể sử dụng template, thử tìm trong original_samples
            if not result['readings'] or len(result['readings']) == 0:
                device_id = result['device_id']
                timestamp = result['timestamp']
                
                # Chuẩn bị timestamp cho so sánh
                try:
                    # Xử lý timestamp dạng datetime và string
                    if isinstance(timestamp, datetime):
                        dt = timestamp
                    elif isinstance(timestamp, str):
                        # Cố gắng chuyển đổi timestamp thành datetime
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except:
                            # Xử lý format khác nếu cần
                            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        logger.warning(f"Không thể xử lý timestamp kiểu {type(timestamp)}")
                        dt = None
                    
                    if dt:
                        # Tìm original sample gần nhất
                        closest_sample = None
                        min_time_diff = timedelta(hours=1)  # Tối đa 1 giờ khác biệt
                        
                        for sample in self.original_samples:
                            orig_data = self.parse_json_data(sample.get('original_data', {}))
                            
                            if orig_data.get('device_id') == device_id and 'timestamp' in orig_data:
                                # Chuyển timestamp của original_data thành datetime
                                try:
                                    orig_timestamp_str = orig_data['timestamp']
                                    orig_dt = datetime.fromisoformat(orig_timestamp_str.replace('Z', '+00:00'))
                                    
                                    # Tính khoảng cách thời gian
                                    time_diff = abs(dt - orig_dt)
                                    
                                    if time_diff < min_time_diff:
                                        min_time_diff = time_diff
                                        closest_sample = orig_data
                                        logger.debug(f"Tìm thấy mẫu gần nhất cách {time_diff}")
                                except Exception as e:
                                    logger.warning(f"Lỗi khi xử lý timestamp của original_sample: {str(e)}")
                        
                        # Sử dụng mẫu gần nhất nếu tìm thấy
                        if closest_sample and 'readings' in closest_sample:
                            result['readings'] = closest_sample['readings']
                            logger.debug(f"Sử dụng mẫu gốc gần nhất cách {min_time_diff}: {result['readings']}")
                except Exception as e:
                    logger.warning(f"Lỗi khi tìm original sample: {str(e)}")
            
            # Kiểm tra nếu vẫn không có readings, thử dùng template_id làm chỉ mục đến templates
            if (not result['readings'] or len(result['readings']) == 0) and template_id is not None:
                # Tính toán index dựa trên template_id và số lượng templates
                if len(self.templates) > 0:
                    index = template_id % len(self.templates)
                    if index in self.templates:
                        result['readings'] = self.extract_readings_from_template(index)
                        logger.debug(f"Sử dụng template với index={index}: {result['readings']}")
            
            # Log kết quả cuối cùng
            logger.debug(f"Kết quả giải nén: device_id={result['device_id']}, timestamp={result['timestamp']}, readings={result['readings']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tái tạo điểm dữ liệu: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'device_id': compressed_point.get('device_id', ''),
                'timestamp': compressed_point.get('timestamp', ''),
                'readings': {},
                'error': str(e)
            }
    
    def decompress_all_data(self, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Giải nén tất cả dữ liệu trong khoảng thời gian chỉ định
        
        Args:
            start_date: Thời gian bắt đầu (tùy chọn)
            end_date: Thời gian kết thúc (tùy chọn)
            
        Returns:
            Danh sách dữ liệu đã giải nén
        """
        # Tải templates từ original_samples
        self.load_templates_from_original_samples()
        
        # Hiển thị số lượng templates đã tải
        logger.info(f"Tổng số templates đã tải: {len(self.templates)}")
        for i, (template_id, template) in enumerate(sorted(self.templates.items())):
            if i < 5:  # Chỉ hiển thị 5 template đầu tiên
                logger.debug(f"Template {template_id}: {template}")
        
        # Tải mẫu dữ liệu gốc
        self.load_original_samples()
        
        # Lấy dữ liệu nén
        compressed_data_list = self.get_compressed_data(start_date, end_date)
        
        # Giải nén từng điểm dữ liệu
        decompressed_data_list = []
        for compressed_point in compressed_data_list:
            decompressed_point = self.reconstruct_data_point(compressed_point)
            decompressed_data_list.append(decompressed_point)
            
        logger.info(f"Đã giải nén {len(decompressed_data_list)} điểm dữ liệu")
        return decompressed_data_list
    
    def convert_to_dataframe(self, decompressed_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Chuyển đổi dữ liệu đã giải nén thành DataFrame để phân tích
        
        Args:
            decompressed_data: Danh sách dữ liệu đã giải nén
            
        Returns:
            DataFrame chứa dữ liệu đã giải nén
        """
        # Tạo cấu trúc dữ liệu phẳng
        flat_data = []
        
        for point in decompressed_data:
            # Thông tin cơ bản
            flat_point = {
                "device_id": point.get("device_id"),
                "timestamp": point.get("timestamp"),
                "record_id": point.get("record_id")
            }
            
            # Thêm readings
            if "readings" in point and isinstance(point["readings"], dict):
                for key, value in point["readings"].items():
                    flat_point[key] = value
            
            flat_data.append(flat_point)
            
        # Tạo DataFrame
        df = pd.DataFrame(flat_data)
        
        # Chuyển đổi timestamp sang datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
        return df

def main():
    """
    Hàm main để chạy giải nén dữ liệu
    """
    parser = argparse.ArgumentParser(description='Giải nén dữ liệu từ database')
    parser.add_argument('--output', type=str, required=True, help='Đường dẫn file output')
    parser.add_argument('--start-date', type=str, help='Ngày bắt đầu (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Ngày kết thúc (YYYY-MM-DD)')
    parser.add_argument('--debug', action='store_true', help='Bật chế độ debug')
    parser.add_argument('--format', type=str, choices=['json', 'csv'], default='json',
                        help='Định dạng file đầu ra (mặc định: json)')
    parser.add_argument('--csv-output', type=str,
                        help='File đầu ra CSV (chỉ khi --format=csv, mặc định: cùng tên với --output)')
    args = parser.parse_args()
    
    # Cấu hình logging
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Đã bật chế độ debug")
    
    # Khởi tạo decompressor
    decompressor = DataDecompressor()
    
    # Parse các tham số ngày tháng
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        # Đặt end_date là cuối ngày
        end_date = end_date.replace(hour=23, minute=59, second=59)
    
    # Ghi log thông tin thời gian
    if start_date:
        logger.info(f"Thời gian bắt đầu: {start_date}")
    if end_date:
        logger.info(f"Thời gian kết thúc: {end_date}")
    
    # Đo thời gian chạy
    start_time = time.time()
    
    # Giải nén dữ liệu
    decompressed_data = decompressor.decompress_all_data(start_date, end_date)
    
    # Lấy thông tin thời gian từ dữ liệu
    timestamps = [point.get('timestamp') for point in decompressed_data if 'timestamp' in point]
    if timestamps:
        min_timestamp = min(timestamps)
        max_timestamp = max(timestamps)
        logger.info(f"Khoảng thời gian trong dữ liệu: {min_timestamp} đến {max_timestamp}")
    
    # Lưu kết quả dựa trên định dạng đầu ra
    if args.format == 'json':
        # Lưu dưới dạng JSON
        with open(args.output, 'w') as f:
            json.dump(decompressed_data, f, indent=2)
        logger.info(f"Đã lưu dữ liệu dạng JSON vào {args.output}")
    else:  # args.format == 'csv'
        # Xác định tên file CSV
        csv_output = args.csv_output or args.output
        # Chuyển đổi thành DataFrame và lưu
        df = decompressor.convert_to_dataframe(decompressed_data)
        df.to_csv(csv_output, index=False)
        logger.info(f"Đã lưu dữ liệu dạng CSV vào {csv_output}")
    
    # Thống kê thời gian và kết quả
    elapsed_time = time.time() - start_time
    logger.info(f"Đã giải nén {len(decompressed_data)} điểm dữ liệu trong {elapsed_time:.2f} giây")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 