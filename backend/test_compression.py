import logging
import json
import time
import random
import math
import numpy as np
import os
import datetime
from datetime import datetime, timedelta
from typing import List, Dict, Any
from data_compression import IDEALEMCompressor
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cấu hình kết nối database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")
engine = None
SessionLocal = None

def setup_database():
    """
    Thiết lập kết nối đến cơ sở dữ liệu
    """
    global engine, SessionLocal
    try:
        # Tạo engine kết nối đến database
        engine = create_engine(DATABASE_URL)
        
        # Tạo session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Tạo bảng original_samples nếu chưa tồn tại
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS original_samples (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR NOT NULL,
                    original_data JSONB NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Đã tạo bảng original_samples để lưu mẫu dữ liệu gốc")
        
        logger.info(f"Đã kết nối thành công đến database: {DATABASE_URL}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kết nối đến database: {str(e)}")
        return False

def generate_sensor_data(num_points: int = 100, device_id: str = "sensor_01") -> List[Dict[str, Any]]:
    """
    Tạo dữ liệu giả lập từ cảm biến trong 24 giờ với mức tiêu thụ điện cao vào trưa và tối
    
    Args:
        num_points: Số lượng điểm dữ liệu cần tạo
        device_id: ID của thiết bị
        
    Returns:
        Danh sách các điểm dữ liệu
    """
    data_points = []
    # Giá trị cơ bản
    base_temp = 25.0        # Nhiệt độ cơ bản (°C)
    base_humidity = 65.0    # Độ ẩm cơ bản (%)
    base_pressure = 1013.0  # Áp suất cơ bản (hPa)
    base_power = 100.0      # Công suất điện cơ bản (W)
    
    # Tạo thời gian bắt đầu (đặt vào 00:00 của ngày hiện tại)
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Tính toán khoảng thời gian giữa các điểm
    if num_points <= 1:
        num_points = 2  # Đảm bảo ít nhất 2 điểm
    
    # Tính thời gian giữa mỗi điểm để đạt đủ 24 giờ
    time_step = timedelta(hours=24) / (num_points - 1)
    
    for i in range(num_points):
        # Tạo thời gian cho điểm dữ liệu hiện tại
        point_time = start_time + (time_step * i)
        timestamp = point_time.isoformat()
        
        # Tính giờ trong ngày (0-23) để tạo xu hướng trong ngày
        hour = point_time.hour
        
        # ==== Tạo dữ liệu nhiệt độ ====
        # Nhiệt độ thấp nhất vào sáng sớm (4-5h), cao nhất vào buổi trưa (13-14h)
        hour_factor_temp = math.sin(math.pi * (hour - 5) / 12) if 5 <= hour <= 17 else -0.5
        temp_daily_cycle = 5.0 * hour_factor_temp  # Biên độ nhiệt trong ngày ±5°C
        
        # Thêm nhiễu ngẫu nhiên cho nhiệt độ
        temp_noise = random.uniform(-0.8, 0.8)
        
        # Giá trị nhiệt độ cuối cùng
        temperature = base_temp + temp_daily_cycle + temp_noise
        
        # ==== Tạo dữ liệu độ ẩm ====
        # Độ ẩm thường ngược với nhiệt độ (cao vào buổi sáng và tối, thấp vào buổi trưa)
        humidity_daily_cycle = -8.0 * hour_factor_temp  # Biên độ độ ẩm trong ngày ±8%
        
        # Thêm nhiễu ngẫu nhiên
        humid_noise = random.uniform(-1.5, 1.5)
        
        # Giá trị độ ẩm cuối cùng
        humidity = base_humidity + humidity_daily_cycle + humid_noise
        
        # ==== Tạo dữ liệu áp suất ====
        # Áp suất thường có hai đỉnh trong ngày: khoảng 10h và 22h
        pressure_cycle = 2.0 * math.sin(math.pi * hour / 12 + math.pi/6)
        
        # Thêm nhiễu ngẫu nhiên
        pressure_noise = random.uniform(-0.3, 0.3)
        
        # Giá trị áp suất cuối cùng
        pressure = base_pressure + pressure_cycle + pressure_noise
        
        # ==== Tạo dữ liệu tiêu thụ điện ====
        # Mô hình tiêu thụ điện cao vào buổi trưa (11-14h) và buổi tối (18-22h)
        # Buổi trưa: sử dụng điều hòa, thiết bị làm mát
        # Buổi tối: đèn, TV, các thiết bị gia dụng
        
        # Hệ số tiêu thụ buổi trưa
        if 11 <= hour <= 14:
            power_lunch_factor = 0.8 + 0.2 * math.sin(math.pi * (hour - 11) / 3)
        else:
            power_lunch_factor = 0.0
        
        # Hệ số tiêu thụ buổi tối
        if 18 <= hour <= 22:
            power_evening_factor = 1.0 - 0.2 * math.sin(math.pi * (hour - 18) / 4) 
        else:
            power_evening_factor = 0.0
        
        # Hệ số tiêu thụ nền (thấp vào đêm khuya và sáng sớm)
        power_base_factor = 0.3
        if 0 <= hour <= 5:
            power_base_factor = 0.1 + 0.05 * hour  # Tăng dần từ khuya đến sáng
        elif 6 <= hour <= 10:
            power_base_factor = 0.3 + 0.1 * math.sin(math.pi * (hour - 6) / 4)
        elif 15 <= hour <= 17:
            power_base_factor = 0.4
        elif 23 == hour:
            power_base_factor = 0.2
            
        # Kết hợp các hệ số
        power_factor = max(power_base_factor, power_lunch_factor, power_evening_factor)
        
        # Thêm nhiễu ngẫu nhiên (±10% giá trị)
        power_noise = random.uniform(-0.1, 0.1) * base_power * power_factor
        
        # Giá trị công suất điện cuối cùng
        power = base_power * power_factor + power_noise
        
        # ==== Tạo dữ liệu pin ====
        # Thiết bị có thể sạc vào đêm khuya, pin giảm dần trong ngày
        battery_level = 100 - (20 * (hour / 24))  # Giảm 20% trong một ngày
        if 0 <= hour <= 4:  # Sạc vào đêm khuya
            battery_level = min(100, battery_level + 5 * hour)
            
        # Thêm một chút nhiễu
        battery_noise = random.uniform(-2, 2)
        battery_level = max(0, min(100, battery_level + battery_noise))
        
        # Tạo điểm dữ liệu
        data_point = {
            "device_id": device_id,
            "timestamp": timestamp,
            "readings": {
                "temperature": round(temperature, 3),
                "humidity": round(humidity, 3),
                "pressure": round(pressure, 3),
                "power": round(power, 3),
                "battery": round(battery_level)
            }
        }
        
        data_points.append(data_point)
    
    return data_points

def save_original_sample_to_db(original_data: Dict[str, Any], device_id: str = "sensor_01") -> int:
    """
    Lưu mẫu dữ liệu gốc vào bảng original_samples
    
    Args:
        original_data: Dữ liệu gốc
        device_id: ID của thiết bị
        
    Returns:
        ID của bản ghi đã lưu, hoặc -1 nếu có lỗi
    """
    if not SessionLocal:
        logger.error("Chưa thiết lập kết nối đến database")
        return -1
    
    db = SessionLocal()
    try:
        # Tạo bản ghi original_samples
        sql = text("""
            INSERT INTO original_samples 
            (device_id, original_data, timestamp)
            VALUES 
            (:device_id, :original_data, NOW())
            RETURNING id
        """)
        
        # Chuẩn bị dữ liệu
        params = {
            "device_id": device_id,
            "original_data": json.dumps(original_data)
        }
        
        # Thực thi truy vấn
        result = db.execute(sql, params).fetchone()
        db.commit()
        
        record_id = result[0] if result else -1
        logger.debug(f"Đã lưu mẫu dữ liệu gốc với ID: {record_id}")
        
        return record_id
    except Exception as e:
        logger.error(f"Lỗi khi lưu mẫu dữ liệu gốc vào database: {str(e)}")
        db.rollback()
        return -1
    finally:
        db.close()

def save_compressed_template_to_db(template_data: Dict[str, Any], 
                            stats: Dict[str, Any], device_id: str = "sensor_01") -> int:
    """
    Lưu template (mẫu) đã nén vào database trong bảng compressed_data
    
    Args:
        template_data: Dữ liệu template đã nén
        stats: Thông số thống kê nén
        device_id: ID của thiết bị
        
    Returns:
        ID của bản ghi đã lưu, hoặc -1 nếu có lỗi
    """
    if not SessionLocal:
        logger.error("Chưa thiết lập kết nối đến database")
        return -1
    
    db = SessionLocal()
    try:
        # Đảm bảo thiết bị tồn tại trong database
        device = db.execute(text(f"SELECT id FROM devices WHERE device_id = '{device_id}'")).fetchone()
        
        if not device:
            # Tạo thiết bị mới nếu chưa tồn tại
            logger.info(f"Thiết bị {device_id} chưa tồn tại, đang tạo mới...")
            db.execute(text(f"""
                INSERT INTO devices (device_id, name, description, created_at) 
                VALUES ('{device_id}', 'Test Device', 'Thiết bị tự động tạo từ test_compression.py', NOW())
            """))
            db.commit()
            logger.info(f"Đã tạo thiết bị mới với ID: {device_id}")
        
        # Tạo bản ghi compressed_data (loại bỏ tất cả các cột không cần thiết)
        sql = text("""
            INSERT INTO compressed_data 
            (device_id, compressed_data, compression_ratio, timestamp)
            VALUES 
            (:device_id, :compressed_data, :compression_ratio, NOW())
            RETURNING id
        """)
        
        # Chuẩn bị dữ liệu
        params = {
            "device_id": device_id,
            "compressed_data": json.dumps(template_data),
            "compression_ratio": stats.get("compression_ratio", 1.0)
        }
        
        # Thực thi truy vấn
        result = db.execute(sql, params).fetchone()
        db.commit()
        
        record_id = result[0] if result else -1
        logger.info(f"Đã lưu template nén với ID: {record_id}, tỷ lệ nén: {stats.get('compression_ratio', 1.0):.4f}")
        
        return record_id
    except Exception as e:
        logger.error(f"Lỗi khi lưu template nén vào database: {str(e)}")
        db.rollback()
        return -1
    finally:
        db.close()

def run_idealem_compression_test(data_points: List[Dict[str, Any]], config: Dict[str, Any] = None, save_to_db: bool = True) -> None:
    """
    Chạy kiểm thử thuật toán nén dữ liệu IDEALEM với tính năng thích nghi kích thước khối
    và tính toán pmin dựa trên khoảng tin cậy
    
    Args:
        data_points: Dữ liệu cần nén
        config: Cấu hình cho thuật toán nén
        save_to_db: Có lưu dữ liệu đã nén vào database hay không
    """
    # Khởi tạo compressor
    if config is None:
        # Mặc định bật tính năng thích nghi kích thước khối
        config = {
            "adaptive_block_size": True,
            "block_size": 8,
            "min_block_size": 4,
            "max_block_size": 16,
            "window_size": 10,
            "p_threshold": 0.05,
            "pmin": 0.6,
            "kmax": 10,
            "rmin": 50,
            "confidence_level": 0.95  # Mức độ tin cậy 95%
        }
    
    compressor = IDEALEMCompressor(config)
    logger.info(f"Khởi tạo IDEALEM Compressor thành công với cấu hình: {config}")
    
    # Các biến thống kê
    total_original_size = 0
    total_compressed_size = 0
    total_real_compressed_size = 0
    compression_times = []
    block_sizes = []
    hit_ratios = []
    pmin_values = []
    rho_min_values = []
    real_compression_ratios = []
    saved_original_samples = 0
    
    # Thiết lập kết nối đến database nếu cần lưu dữ liệu
    if save_to_db:
        if not setup_database():
            logger.warning("Không thể kết nối đến database, dữ liệu nén sẽ không được lưu")
            save_to_db = False
    
    # Xử lý từng điểm dữ liệu
    for i, data_point in enumerate(data_points):
        # Nén dữ liệu
        start_time = time.time()
        compressed_data, stats = compressor.compress(data_point)
        compression_time = (time.time() - start_time) * 1000  # ms
        compression_times.append(compression_time)
        
        # Cập nhật thống kê
        total_original_size += stats["original_size_bytes"]
        total_compressed_size += stats["compressed_size_bytes"]
        total_real_compressed_size += stats["real_compressed_size_bytes"]
        block_sizes.append(stats.get("current_block_size", 0))
        hit_ratios.append(stats.get("hit_ratio", 0))
        pmin_values.append(stats.get("pmin", 0))
        rho_min_values.append(stats.get("rho_min", 0))
        real_compression_ratios.append(stats.get("real_compression_ratio", 1.0))
        
        # Lưu mẫu dữ liệu gốc (10%)
        if save_to_db and (i % 10 == 0 or i == len(data_points) - 1):
            record_id = save_original_sample_to_db(
                original_data=data_point,
                device_id=data_point.get("device_id", "sensor_01")
            )
            if record_id > 0:
                saved_original_samples += 1
        
        # In thông kê cho điểm thứ i
        if i % 10 == 0 or i == len(data_points) - 1:
            logger.info(f"Điểm {i+1}/{len(data_points)} - Tỷ lệ nén thực tế: {stats['real_compression_ratio']:.4f} - Kích thước khối: {stats.get('current_block_size', 0)} - pmin: {stats.get('pmin', 0):.4f}")
            logger.debug(f"Điểm dữ liệu gốc: {json.dumps(data_point)}")
            logger.debug(f"Điểm dữ liệu nén: {json.dumps(compressed_data)}")
            
    # Lấy thống kê tổng thể
    overall_stats = compressor.get_stats()
    
    # Lưu các templates vào database
    saved_templates = 0
    if save_to_db:
        # Lấy danh sách templates từ compressor
        templates = compressor.templates
        logger.info(f"Chuẩn bị lưu {len(templates)} templates vào database")
        
        for i, template in enumerate(templates):
            # Tạo cấu trúc dữ liệu template để lưu vào DB
            template_data = {
                "device_id": data_points[0].get("device_id", "sensor_01"),
                "template_id": i,
                "template_data": template,
                "timestamp": datetime.now().isoformat()
            }
            
            # Tạo thống kê cho template
            template_stats = {
                "compression_ratio": overall_stats["overall_compression_ratio"],
                "hit_ratio": overall_stats["hit_ratio"],
                "block_size": overall_stats["current_block_size"]
            }
            
            # Lưu template vào database
            record_id = save_compressed_template_to_db(
                template_data=template_data,
                stats=template_stats,
                device_id=data_points[0].get("device_id", "sensor_01")
            )
            
            if record_id > 0:
                saved_templates += 1
                
    # In thống kê tổng thể
    logger.info("\n===== THỐNG KÊ TỔNG THỂ - IDEALEM =====")
    logger.info(f"Số lượng điểm dữ liệu: {len(data_points)}")
    logger.info(f"Kích thước dữ liệu gốc: {total_original_size} bytes")
    logger.info(f"Kích thước dữ liệu nén với metadata: {total_compressed_size} bytes")
    logger.info(f"Kích thước dữ liệu nén thực tế: {total_real_compressed_size} bytes")
    
    # Tính tỷ lệ nén thực tế
    real_ratio = total_original_size / total_real_compressed_size if total_real_compressed_size > 0 else 1.0
    logger.info(f"Tỷ lệ nén thực tế (bytes): {real_ratio:.4f}")
    
    # Tính số lượng dòng dữ liệu trước và sau khi nén
    original_row_count = len(data_points)
    template_count = overall_stats.get('template_count', 0)
    reference_count = original_row_count - template_count
    row_reduction_ratio = original_row_count / template_count if template_count > 0 else 1.0
    
    logger.info(f"Số lượng dòng dữ liệu ban đầu: {original_row_count}")
    logger.info(f"Số lượng mẫu (templates): {template_count}")
    logger.info(f"Số lượng tham chiếu: {reference_count}")
    logger.info(f"Tỷ lệ giảm số lượng dòng: {row_reduction_ratio:.4f}")
    
    logger.info(f"Tỷ lệ nén tổng thể: {overall_stats['overall_compression_ratio']:.4f}")
    logger.info(f"Thời gian nén trung bình: {sum(compression_times)/len(compression_times):.2f} ms")
    logger.info(f"Kích thước khối cuối cùng: {overall_stats.get('current_block_size', 0)}")
    logger.info(f"Tỷ lệ hit cuối cùng: {overall_stats.get('hit_ratio', 0):.4f}")
    logger.info(f"Giá trị pmin cuối cùng: {overall_stats.get('pmin', 0):.4f}")
    logger.info(f"Tỷ lệ nén tối thiểu đảm bảo: {overall_stats.get('min_compression_ratio', 0):.4f}")
    logger.info(f"Số lần thử nghiệm: {overall_stats.get('trials', 0)}")
    logger.info(f"Số lần hit: {overall_stats.get('hits', 0)}")
    logger.info(f"Độ lệch chuẩn mẫu: {overall_stats.get('sample_std', 0):.4f}")
    logger.info(f"Giá trị z* cho mức tin cậy {overall_stats.get('confidence_level', 0.95)*100}%: {overall_stats.get('z_critical', 0):.4f}")
    
    if save_to_db:
        logger.info(f"Đã lưu {saved_templates} templates vào bảng compressed_data")
        logger.info(f"Đã lưu {saved_original_samples} mẫu dữ liệu gốc vào bảng original_samples")
    
    # In lịch sử kích thước khối
    if 'block_size_history' in overall_stats:
        logger.info(f"Lịch sử kích thước khối: {overall_stats['block_size_history']}")
    
    # Vẽ biểu đồ nếu có thư viện matplotlib
    try:
        import matplotlib.pyplot as plt
        
        # Biểu đồ kích thước khối, giá trị pmin và tỷ lệ nén tối thiểu
        plt.figure(figsize=(15, 12))
        
        plt.subplot(3, 1, 1)
        plt.plot(block_sizes, label='Kích thước khối')
        plt.xlabel('Điểm dữ liệu')
        plt.ylabel('Kích thước khối')
        plt.title('Kích thước khối theo thời gian')
        plt.grid(True)
        plt.legend()
        
        plt.subplot(3, 1, 2)
        plt.plot(pmin_values, label='Giá trị pmin')
        plt.xlabel('Điểm dữ liệu')
        plt.ylabel('pmin')
        plt.title('Giá trị pmin theo thời gian')
        plt.grid(True)
        plt.legend()
        
        plt.subplot(3, 1, 3)
        plt.plot(rho_min_values, label='Tỷ lệ nén tối thiểu')
        plt.xlabel('Điểm dữ liệu')
        plt.ylabel('ρmin')
        plt.title('Tỷ lệ nén tối thiểu theo thời gian')
        plt.grid(True)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('idealem_stats.png')
        logger.info(f"Đã lưu biểu đồ thống kê vào file 'idealem_stats.png'")
        
        # Tạo biểu đồ so sánh số lượng dòng
        plt.figure(figsize=(10, 6))
        labels = ['Dữ liệu gốc', 'Sau khi nén']
        original_compressed = [original_row_count, template_count]
        
        plt.bar(labels, original_compressed, color=['blue', 'green'])
        plt.ylabel('Số lượng dòng dữ liệu')
        plt.title(f'So sánh số lượng dòng dữ liệu trước và sau khi nén\nTỷ lệ giảm: {row_reduction_ratio:.2f}x')
        
        # Thêm giá trị cụ thể lên đầu mỗi cột
        for i, v in enumerate(original_compressed):
            plt.text(i, v + 5, str(v), ha='center')
            
        # Thêm tỷ lệ % giảm
        reduction_percent = ((original_row_count - template_count) / original_row_count) * 100
        plt.figtext(0.5, 0.01, f'Giảm {reduction_percent:.1f}% số lượng dòng dữ liệu', ha='center', fontsize=12)
        
        plt.tight_layout()
        plt.savefig('row_reduction.png')
        logger.info(f"Đã lưu biểu đồ so sánh số lượng dòng vào file 'row_reduction.png'")
        
        # Tạo biểu đồ so sánh kích thước dữ liệu
        plt.figure(figsize=(10, 6))
        labels = ['Dữ liệu gốc', 'Sau khi nén']
        sizes = [total_original_size, total_real_compressed_size]
        
        plt.bar(labels, sizes, color=['blue', 'green'])
        plt.ylabel('Kích thước (bytes)')
        plt.title(f'So sánh kích thước dữ liệu trước và sau khi nén\nTỷ lệ nén: {real_ratio:.2f}x')
        
        # Thêm giá trị cụ thể lên đầu mỗi cột
        for i, v in enumerate(sizes):
            plt.text(i, v + 1000, f"{v:,} bytes", ha='center')
            
        # Thêm tỷ lệ % giảm
        size_reduction_percent = ((total_original_size - total_real_compressed_size) / total_original_size) * 100
        plt.figtext(0.5, 0.01, f'Giảm {size_reduction_percent:.1f}% kích thước dữ liệu', ha='center', fontsize=12)
        
        plt.tight_layout()
        plt.savefig('size_reduction.png')
        logger.info(f"Đã lưu biểu đồ so sánh kích thước dữ liệu vào file 'size_reduction.png'")
        
    except ImportError:
        logger.warning("Không thể tạo biểu đồ. Hãy cài đặt thư viện matplotlib: pip install matplotlib")

def main():
    try:
        # Tạo dữ liệu giả lập
        logger.info("Đang tạo dữ liệu giả lập...")
        sensor_data = generate_sensor_data(num_points=1400)  # Tạo 1400 điểm dữ liệu
        logger.info(f"Đã tạo {len(sensor_data)} điểm dữ liệu giả lập")
        
        # Cấu hình cho thuật toán nén IDEALEM
        idealem_config = {
            "adaptive_block_size": True,  # Bật thích nghi kích thước khối
            "block_size": 8,             # Kích thước khối ban đầu
            "min_block_size": 4,         # Kích thước khối tối thiểu
            "max_block_size": 16,        # Kích thước khối tối đa
            "p_threshold": 0.05,         # Ngưỡng p-value
            "pmin": 0.6,                 # Tỷ lệ hit tối thiểu ban đầu
            "kmax": 8,                   # Số lần chuyển đổi tối đa
            "rmin": 50,                  # Số lượng thử nghiệm tối thiểu
            "confidence_level": 0.95     # Mức độ tin cậy 95%
        }
        
        # Hỏi người dùng có muốn lưu vào database không
        save_to_db = input("Bạn có muốn lưu dữ liệu nén vào database không? (y/n): ").lower() == 'y'
        
        # Chạy kiểm thử IDEALEM với tính năng thích nghi kích thước khối
        logger.info("Bắt đầu kiểm thử thuật toán nén IDEALEM với tính năng thích nghi kích thước khối...")
        run_idealem_compression_test(sensor_data, idealem_config, save_to_db=save_to_db)
        logger.info("Hoàn thành kiểm thử thuật toán nén IDEALEM")
        
        # Lưu dữ liệu mẫu vào file
        with open('sample_data.json', 'w') as f:
            json.dump(sensor_data[:10], f, indent=2)
        logger.info("Đã lưu dữ liệu mẫu vào file sample_data.json")
        
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện kiểm thử: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 