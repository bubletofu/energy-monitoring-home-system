import logging
import json
import time
import random
import math
import numpy as np
import os
import datetime
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from data_compression import IDEALEMCompressor
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
import argparse

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

def generate_sensor_data(num_points: int = 100, device_id: str = "sensor_02", start_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Tạo dữ liệu giả lập từ cảm biến với mỗi điểm cách nhau đúng 1 phút
    
    Dữ liệu được mô phỏng dựa trên các yếu tố thực tế như:
    - Thời gian trong ngày (giờ): Nhiệt độ, độ ẩm và tiêu thụ điện thay đổi theo chu kỳ ngày
    - Ngày trong tuần: Các ngày làm việc và cuối tuần có mẫu tiêu thụ khác nhau
    - Tháng và mùa trong năm: Mỗi mùa có đặc điểm nhiệt độ, độ ẩm, và tiêu thụ điện khác nhau
    - Các sự kiện đặc biệt/ngày lễ: Tiêu thụ điện có thể tăng đột biến vào các dịp lễ
    
    Args:
        num_points: Số lượng điểm dữ liệu cần tạo
        device_id: ID của thiết bị
        start_date: Thời gian bắt đầu (nếu None sẽ dùng mặc định là 10:00:00 của ngày hiện tại)
        
    Returns:
        Danh sách các điểm dữ liệu
    """
    data_points = []
    
    # Đảm bảo số điểm ít nhất là 2
    if num_points <= 1:
        num_points = 2
    
    # Tạo thời gian bắt đầu
    if start_date is None:
        # Sử dụng mốc thời gian mặc định là 10:00 sáng ngày hiện tại
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        start_time = today
    else:
        # Sử dụng thời gian được chỉ định
        start_time = start_date.replace(microsecond=0)
    
    # Lấy thông tin ngày/tháng/mùa ban đầu
    initial_month = start_time.month
    initial_weekday = start_time.weekday()  # 0 = Thứ 2, 6 = Chủ nhật
    weekday_name = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'][initial_weekday]
    
    # Phân loại mùa (theo bắc bán cầu)
    # Mùa xuân: tháng 3-5, Mùa hè: tháng 6-8, Mùa thu: tháng 9-11, Mùa đông: tháng 12-2
    seasons = {
        1: "Đông", 2: "Đông", 
        3: "Xuân", 4: "Xuân", 5: "Xuân", 
        6: "Hè", 7: "Hè", 8: "Hè", 
        9: "Thu", 10: "Thu", 11: "Thu", 
        12: "Đông"
    }
    initial_season = seasons[initial_month]
    
    logger.info(f"Tạo dữ liệu cho {weekday_name} ({start_time.strftime('%Y-%m-%d')}), Tháng {initial_month}, Mùa {initial_season}")

    # Thiết lập các giá trị cơ bản theo tháng
    # Dùng dictionary để lưu trữ thông số cơ bản theo tháng
    monthly_base_values = {
        # Tháng: [base_temp, base_humidity, base_pressure, base_power]
        1: [15.0, 75.0, 1018.0, 130.0],  # Tháng 1 - Mùa đông, trời lạnh, độ ẩm cao, áp suất cao, dùng nhiều điện sưởi
        2: [16.0, 72.0, 1017.0, 125.0],  # Tháng 2
        3: [19.0, 70.0, 1016.0, 115.0],  # Tháng 3 - Đầu xuân
        4: [22.0, 68.0, 1014.0, 105.0],  # Tháng 4
        5: [25.0, 65.0, 1012.0, 100.0],  # Tháng 5
        6: [28.0, 70.0, 1010.0, 120.0],  # Tháng 6 - Đầu hè, bắt đầu nóng, dùng điều hòa
        7: [32.0, 75.0, 1008.0, 150.0],  # Tháng 7 - Giữa hè, nóng nhất, độ ẩm cao, dùng nhiều điều hòa
        8: [31.0, 78.0, 1007.0, 145.0],  # Tháng 8 - Cuối hè, nóng và ẩm nhất
        9: [28.0, 75.0, 1010.0, 125.0],  # Tháng 9 - Đầu thu
        10: [24.0, 70.0, 1012.0, 115.0], # Tháng 10
        11: [20.0, 72.0, 1015.0, 120.0], # Tháng 11
        12: [16.0, 74.0, 1018.0, 125.0]  # Tháng 12 - Đầu đông
    }
    
    # Lấy giá trị cơ bản từ tháng hiện tại
    month = start_time.month
    base_temp, base_humidity, base_pressure, base_power = monthly_base_values[month]
    
    # Điều chỉnh các giá trị cơ bản dựa trên thứ trong tuần
    weekend_factor = 1.0
    
    if initial_weekday >= 5:  # Thứ bảy, chủ nhật
        weekend_factor = 1.3     # Tăng 30% tiêu thụ điện
        # Điều chỉnh nhiệt độ và độ ẩm trong nhà theo mùa
        if initial_season == "Hè":
            base_temp -= 2.0      # Mùa hè, nhiệt độ trong nhà thấp hơn do mở điều hòa
            base_humidity -= 10.0  # Độ ẩm giảm do điều hòa
        elif initial_season == "Đông":
            base_temp += 3.0      # Mùa đông, nhiệt độ trong nhà cao hơn do bật sưởi
            base_humidity -= 5.0   # Độ ẩm giảm do sưởi
    else:
        # Các ngày khác nhau trong tuần có thể có các mẫu tiêu thụ khác nhau
        if initial_weekday == 0:  # Thứ 2
            base_power *= 1.1    # Thứ 2 thường tiêu thụ năng lượng cao hơn (sau nghỉ)
        elif initial_weekday == 4:  # Thứ 6
            base_power *= 1.15   # Thứ 6 tiêu thụ cao hơn (về sớm, giải trí)
    
    # Danh sách các ngày lễ đặc biệt (ví dụ: Tết, Giáng sinh, v.v.)
    # Format: (tháng, ngày)
    holidays = [
        (1, 1),    # Tết dương lịch
        (4, 30),   # Giải phóng miền Nam
        (5, 1),    # Quốc tế lao động
        (9, 2),    # Quốc khánh
        (12, 24),  # Đêm Giáng sinh
        (12, 25),  # Giáng sinh
        (12, 31)   # Đêm giao thừa dương lịch
    ]
    
    # Hệ số biến động theo tháng
    # Biên độ dao động nhiệt trong ngày cao nhất vào những tháng giao mùa, thấp nhất vào giữa mùa
    month_temp_amplitude = {
        1: 6.0, 2: 7.0, 3: 9.0, 4: 10.0, 5: 9.0, 6: 8.0,
        7: 7.0, 8: 7.0, 9: 8.0, 10: 9.0, 11: 8.0, 12: 6.0
    }
    
    month_humidity_amplitude = {
        1: 10.0, 2: 12.0, 3: 15.0, 4: 18.0, 5: 20.0, 6: 25.0,
        7: 25.0, 8: 25.0, 9: 20.0, 10: 15.0, 11: 12.0, 12: 10.0
    }
    
    # Lưu các thông số hiện tại để xử lý khi chuyển ngày/tháng/mùa
    current_day = start_time.day
    current_month = month
    current_season = initial_season
    
    for i in range(num_points):
        # Tạo thời gian cho điểm dữ liệu hiện tại, mỗi điểm tăng đúng 1 phút
        point_time = start_time + timedelta(minutes=i)
        
        # Kiểm tra các thay đổi về ngày/tháng/mùa
        new_day = point_time.day
        new_month = point_time.month
        new_season = seasons[new_month]
        new_weekday = point_time.weekday()
        
        # Kiểm tra nếu đang là ngày lễ
        is_holiday = (new_month, new_day) in holidays
        
        # Kiểm tra nếu đã sang ngày mới
        day_changed = new_day != current_day
        
        # Kiểm tra nếu đã sang tháng mới
        month_changed = new_month != current_month
        
        # Kiểm tra nếu đã sang mùa mới
        season_changed = new_season != current_season
        
        # Xử lý các thay đổi
        if day_changed or month_changed or season_changed:
            # Cập nhật nhật ký
            if day_changed:
                weekday_name = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'][new_weekday]
                logger.info(f"Đã sang ngày mới: {weekday_name} ({point_time.strftime('%Y-%m-%d')})")
            
            if month_changed:
                logger.info(f"Đã sang tháng mới: Tháng {new_month}")
                # Cập nhật giá trị cơ bản theo tháng mới
                base_temp, base_humidity, base_pressure, base_power = monthly_base_values[new_month]
            
            if season_changed:
                logger.info(f"Đã sang mùa mới: Mùa {new_season}")
            
            # Cập nhật các tham số
            current_day = new_day
            current_month = new_month
            current_season = new_season
            
            # Điều chỉnh lại các hệ số theo ngày trong tuần
            if new_weekday >= 5:  # Thứ 7 và Chủ nhật
                weekend_factor = 1.3  # Tăng 30%
                # Điều chỉnh nhiệt độ và độ ẩm theo mùa
                if new_season == "Hè":
                    base_temp -= 2.0
                    base_humidity -= 10.0
                elif new_season == "Đông":
                    base_temp += 3.0
                    base_humidity -= 5.0
            else:
                weekend_factor = 1.0  # Ngày thường
                
                # Hiệu chỉnh cho thứ Hai (tiêu thụ điện tăng khi bắt đầu tuần)
                if new_weekday == 0:  # Thứ Hai
                    weekend_factor = 1.1  # Tăng 10% so với ngày thường
                
                # Hiệu chỉnh cho thứ Sáu (tiêu thụ điện tăng, chuẩn bị cho cuối tuần)
                if new_weekday == 4:  # Thứ Sáu
                    weekend_factor = 1.15  # Tăng 15% so với ngày thường
        
        # Format timestamp theo ISO 8601 không có phần microsecond
        timestamp = point_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Tính giờ trong ngày (0-23) để tạo xu hướng trong ngày
        hour = point_time.hour
        
        # ==== Tạo dữ liệu nhiệt độ ====
        # Nhiệt độ thấp nhất vào sáng sớm (4-5h), cao nhất vào buổi trưa (13-14h)
        # Điều chỉnh giờ cao điểm nhiệt độ theo mùa
        peak_hour = 14 if current_season in ["Xuân", "Hè"] else 13  # Mùa hè nắng kéo dài hơn
        hour_factor_temp = math.sin(math.pi * (hour - 5) / 12) if 5 <= hour <= (peak_hour + 3) else -0.5
        
        # Biên độ nhiệt trong ngày thay đổi theo tháng
        temp_daily_amplitude = month_temp_amplitude[current_month]
        temp_daily_cycle = temp_daily_amplitude * hour_factor_temp
        
        # Thêm nhiễu ngẫu nhiên cho nhiệt độ, biên độ nhiễu cũng thay đổi theo mùa
        temp_noise_amplitude = 1.2 if current_season in ["Xuân", "Thu"] else 0.8  # Giao mùa nhiễu lớn hơn
        temp_noise = random.uniform(-temp_noise_amplitude, temp_noise_amplitude)
        
        # Giá trị nhiệt độ cuối cùng
        temperature = base_temp + temp_daily_cycle + temp_noise
        
        # ==== Tạo dữ liệu độ ẩm ====
        # Độ ẩm thường ngược với nhiệt độ (cao vào buổi sáng và tối, thấp vào buổi trưa)
        # Biên độ dao động độ ẩm thay đổi theo tháng
        humidity_daily_amplitude = month_humidity_amplitude[current_month]
        humidity_daily_cycle = -humidity_daily_amplitude * hour_factor_temp
        
        # Thêm nhiễu ngẫu nhiên cho độ ẩm
        humid_noise_amplitude = 3.0 if current_season in ["Hè", "Thu"] else 2.0  # Mùa mưa nhiễu lớn hơn
        humid_noise = random.uniform(-humid_noise_amplitude, humid_noise_amplitude)
        
        # Giá trị độ ẩm cuối cùng
        humidity = base_humidity + humidity_daily_cycle + humid_noise
        
        # ==== Tạo dữ liệu áp suất ====
        # Áp suất thay đổi theo mùa và giờ trong ngày
        pressure_cycle_amplitude = 3.0 if current_season in ["Xuân", "Thu"] else 2.0  # Giao mùa biến động lớn hơn
        pressure_cycle = pressure_cycle_amplitude * math.sin(math.pi * hour / 12 + math.pi/6)
        
        # Thêm nhiễu ngẫu nhiên cho áp suất
        pressure_noise_amplitude = 0.5 if current_season in ["Xuân", "Thu"] else 0.3
        pressure_noise = random.uniform(-pressure_noise_amplitude, pressure_noise_amplitude)
        
        # Áp suất thấp hơn nếu đang có mưa (xác suất mưa cao hơn vào mùa hè và mùa thu)
        rain_probability = 0.2  # Xác suất cơ bản
        if current_season == "Hè":
            rain_probability = 0.35
        elif current_season == "Thu":
            rain_probability = 0.25
            
        # Giảm áp suất nếu đang mưa
        is_raining = random.random() < rain_probability
        rain_effect = -2.0 if is_raining else 0.0
        
        # Giá trị áp suất cuối cùng
        pressure = base_pressure + pressure_cycle + pressure_noise + rain_effect
        
        # ==== Tạo dữ liệu tiêu thụ điện ====
        # Tiêu thụ điện thay đổi theo mùa, giờ trong ngày, và ngày trong tuần
        
        # Hệ số mùa cho tiêu thụ điện (cao hơn vào mùa hè và mùa đông)
        season_power_factor = 1.0
        if current_season == "Hè":
            season_power_factor = 1.3  # Sử dụng điều hòa làm mát
        elif current_season == "Đông":
            season_power_factor = 1.2  # Sử dụng thiết bị sưởi
        
        # Hệ số tiêu thụ buổi trưa - cao hơn vào mùa hè do sử dụng điều hòa
        lunch_peak_start = 11
        lunch_peak_end = 14
        if current_season == "Hè":
            lunch_peak_start = 10  # Mùa hè bắt đầu dùng điều hòa sớm hơn
            lunch_peak_end = 15    # và kéo dài hơn
        
        if lunch_peak_start <= hour <= lunch_peak_end:
            power_lunch_factor = 0.8 + 0.2 * math.sin(math.pi * (hour - lunch_peak_start) / (lunch_peak_end - lunch_peak_start))
            # Hiệu chỉnh theo mùa
            if current_season == "Hè":
                power_lunch_factor *= 1.5  # Mùa hè trưa nóng, dùng điều hòa nhiều
            elif current_season == "Đông":
                power_lunch_factor *= 1.2  # Mùa đông dùng thiết bị sưởi
                
            # Vào cuối tuần, buổi trưa tiêu thụ nhiều hơn (ở nhà)
            if new_weekday >= 5:
                power_lunch_factor *= 1.4  # Tăng 40% so với ngày thường
        else:
            power_lunch_factor = 0.0
        
        # Hệ số tiêu thụ buổi tối - cao hơn vào mùa đông do trời tối sớm hơn
        evening_peak_start = 18
        evening_peak_end = 22
        if current_season == "Đông":
            evening_peak_start = 17  # Mùa đông trời tối sớm hơn
        elif current_season == "Hè":
            evening_peak_end = 23     # Mùa hè hoạt động kéo dài hơn
        
        if evening_peak_start <= hour <= evening_peak_end:
            power_evening_factor = 1.0 - 0.2 * math.sin(math.pi * (hour - evening_peak_start) / (evening_peak_end - evening_peak_start)) 
            # Hiệu chỉnh theo mùa
            if current_season == "Đông":
                power_evening_factor *= 1.3  # Mùa đông tối sớm, sử dụng đèn và sưởi nhiều hơn
            
            # Hiệu chỉnh theo ngày
            if new_weekday == 4 or new_weekday == 5:  # Thứ 6, thứ 7
                power_evening_factor *= 1.3  # Tăng 30% so với ngày thường (giải trí, tiệc tùng)
        else:
            power_evening_factor = 0.0
        
        # Hệ số tiêu thụ nền (thay đổi theo giờ và mùa)
        power_base_factor = 0.3
        if 0 <= hour <= 5:
            power_base_factor = 0.1 + 0.05 * hour  # Tăng dần từ khuya đến sáng
            # Mùa đông tiêu thụ điện cao hơn vào ban đêm do sưởi
            if current_season == "Đông":
                power_base_factor += 0.1
        elif 6 <= hour <= 10:
            # Vào ngày trong tuần, buổi sáng tiêu thụ nhiều hơn (chuẩn bị đi làm)
            if new_weekday < 5:
                power_base_factor = 0.3 + 0.15 * math.sin(math.pi * (hour - 6) / 4)
                if current_season == "Đông":
                    power_base_factor += 0.1  # Mùa đông buổi sáng tiêu thụ cao hơn (sưởi, nước nóng)
            else:
                # Cuối tuần buổi sáng thường tiêu thụ ít hơn (ngủ nướng)
                power_base_factor = 0.2 + 0.05 * math.sin(math.pi * (hour - 6) / 4)
        elif 15 <= hour <= 17:
            # Giờ tan học, tan làm
            power_base_factor = 0.4
            if new_weekday < 5:  # Ngày trong tuần
                power_base_factor += 0.1  # Tăng lên do người về nhà
        elif 23 == hour:
            power_base_factor = 0.2
            if is_holiday:
                power_base_factor += 0.3  # Các ngày lễ, đêm khuya vẫn hoạt động nhiều
        
        # Hiệu ứng ngày lễ đặc biệt
        holiday_factor = 1.5 if is_holiday else 1.0
            
        # Kết hợp các hệ số
        power_factor = max(power_base_factor, power_lunch_factor, power_evening_factor)
        
        # Áp dụng các hệ số nhân
        power_factor *= weekend_factor * season_power_factor * holiday_factor
        
        # Thêm nhiễu ngẫu nhiên (±10% giá trị)
        power_noise = random.uniform(-0.1, 0.1) * base_power * power_factor
        
        # Giá trị công suất điện cuối cùng
        power = base_power * power_factor + power_noise
        
        # ==== Tạo dữ liệu pin ====
        # Thiết bị có thể sạc vào đêm khuya, pin giảm dần trong ngày
        # Mùa đông pin giảm nhanh hơn do nhiệt độ thấp
        battery_drain_factor = 1.2 if current_season == "Đông" else 1.0
        daily_drain = 20.0 * battery_drain_factor  # Giảm 20-24% trong một ngày tùy theo mùa
        
        battery_level = 100 - (daily_drain * (hour / 24))
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
        
        # Thêm thông tin về thời tiết nếu đang mưa
        if is_raining:
            data_point["readings"]["is_raining"] = True
            
        # Thêm cờ đánh dấu ngày lễ
        if is_holiday:
            data_point["readings"]["is_holiday"] = True
        
        data_points.append(data_point)
    
    # Thống kê cuối cùng
    season_count = {}
    month_count = {}
    for point in data_points:
        ts = datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
        month = ts.month
        season = seasons[month]
        
        if month not in month_count:
            month_count[month] = 0
        month_count[month] += 1
        
        if season not in season_count:
            season_count[season] = 0
        season_count[season] += 1
        
    for month, count in month_count.items():
        percentage = (count / len(data_points)) * 100
        logger.info(f"Tháng {month}: {count} điểm dữ liệu ({percentage:.1f}%)")
        
    for season, count in season_count.items():
        percentage = (count / len(data_points)) * 100
        logger.info(f"Mùa {season}: {count} điểm dữ liệu ({percentage:.1f}%)")
    
    return data_points

def save_original_sample_to_db(original_data: Dict[str, Any], device_id: str = "sensor_02") -> int:
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
        # Lấy timestamp từ dữ liệu gốc nếu có
        timestamp = None
        if 'timestamp' in original_data:
            timestamp_str = original_data.get('timestamp')
            # Chuyển đổi timestamp thành datetime nếu là string
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # Thử format không có timezone và microsecond
                        if 'T' in timestamp_str and not '.' in timestamp_str:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        logger.warning(f"Không thể parse timestamp {timestamp_str}, sẽ sử dụng NOW()")
                        timestamp = None
        
        # Tạo SQL query dựa trên việc có timestamp hay không
        if timestamp:
            sql = text("""
                INSERT INTO original_samples 
                (device_id, original_data, timestamp)
                VALUES 
                (:device_id, :original_data, :timestamp)
                RETURNING id
            """)
            
            # Chuẩn bị dữ liệu với timestamp
            params = {
                "device_id": device_id,
                "original_data": json.dumps(original_data),
                "timestamp": timestamp
            }
        else:
            # Sử dụng NOW() nếu không có timestamp
            sql = text("""
                INSERT INTO original_samples 
                (device_id, original_data, timestamp)
                VALUES 
                (:device_id, :original_data, NOW())
                RETURNING id
            """)
            
            # Chuẩn bị dữ liệu không có timestamp
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
                            stats: Dict[str, Any], device_id: str = "sensor_02") -> int:
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
        
        # Lấy timestamp từ template_data nếu có
        timestamp = None
        if 'timestamp' in template_data:
            timestamp_str = template_data.get('timestamp')
            # Chuyển đổi timestamp thành datetime nếu là string
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # Thử format không có timezone và microsecond
                        if 'T' in timestamp_str and not '.' in timestamp_str:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        logger.warning(f"Không thể parse timestamp {timestamp_str}, sẽ sử dụng NOW()")
                        timestamp = None
        
        # Tạo SQL query dựa trên việc có timestamp hay không
        if timestamp:
            sql = text("""
                INSERT INTO compressed_data 
                (device_id, compressed_data, compression_ratio, timestamp)
                VALUES 
                (:device_id, :compressed_data, :compression_ratio, :timestamp)
                RETURNING id
            """)
            
            # Chuẩn bị dữ liệu với timestamp
            params = {
                "device_id": device_id,
                "compressed_data": json.dumps(template_data),
                "compression_ratio": stats.get("compression_ratio", 1.0),
                "timestamp": timestamp
            }
        else:
            # Sử dụng NOW() nếu không có timestamp
            sql = text("""
                INSERT INTO compressed_data 
                (device_id, compressed_data, compression_ratio, timestamp)
                VALUES 
                (:device_id, :compressed_data, :compression_ratio, NOW())
                RETURNING id
            """)
            
            # Chuẩn bị dữ liệu không có timestamp
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
        
        # Lưu mẫu dữ liệu gốc (100%)
        if save_to_db:
            record_id = save_original_sample_to_db(
                original_data=data_point,
                device_id=data_point.get("device_id", "sensor_02")
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
                "device_id": data_points[0].get("device_id", "sensor_02"),
                "template_id": i,
                "template_data": template
            }
            
            # Chọn timestamp đặc trưng cho các khoảng thời gian trong ngày
            # thay vì chỉ lấy timestamp từ một vài điểm đầu tiên
            found_timestamp = False
            
            # Nếu số lượng template ít, phân bổ đều trong tập dữ liệu
            if len(templates) <= 4:
                # Phân bổ đều trong tập dữ liệu với khoảng cách bằng nhau
                index = int((len(data_points) - 1) * (i / max(1, len(templates) - 1)))
                if 'timestamp' in data_points[index]:
                    template_data["timestamp"] = data_points[index]["timestamp"]
                    found_timestamp = True
                    logger.info(f"Template {i}: Sử dụng timestamp từ điểm dữ liệu thứ {index}")
            else:
                # Phân loại các template theo những thời điểm đặc trưng trong ngày
                # Chia tập dữ liệu thành các phân đoạn theo thời gian
                segments = []
                
                # Phân tích timestamps trong tập dữ liệu
                valid_timestamps = []
                hours_map = {}
                
                for j, point in enumerate(data_points):
                    if 'timestamp' in point:
                        try:
                            ts_str = point['timestamp']
                            if isinstance(ts_str, str):
                                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                valid_timestamps.append((j, ts))
                                
                                # Gom nhóm theo giờ
                                hour = ts.hour
                                if hour not in hours_map:
                                    hours_map[hour] = []
                                hours_map[hour].append((j, ts))
                        except (ValueError, TypeError):
                            pass
                
                # Phân nhóm thời gian theo khung giờ đáng chú ý
                time_segments = {
                    "sáng sớm (0-6h)": [h for h in range(0, 7)],
                    "buổi sáng (7-11h)": [h for h in range(7, 12)],
                    "buổi trưa (12-14h)": [h for h in range(12, 15)],
                    "buổi chiều (15-18h)": [h for h in range(15, 19)],
                    "buổi tối (19-23h)": [h for h in range(19, 24)]
                }
                
                # Tìm một timestamp từ các phân khúc thời gian
                if len(templates) <= len(time_segments):
                    # Nếu số template ít hơn số phân khúc, chọn phân khúc phù hợp với index
                    segment_keys = list(time_segments.keys())
                    segment_index = i % len(segment_keys)
                    segment_name = segment_keys[segment_index]
                    segment_hours = time_segments[segment_name]
                    
                    # Tìm điểm dữ liệu từ phân khúc thời gian này
                    candidates = []
                    for hour in segment_hours:
                        if hour in hours_map:
                            candidates.extend(hours_map[hour])
                    
                    if candidates:
                        # Chọn một điểm ngẫu nhiên từ phân khúc
                        idx, ts = random.choice(candidates)
                        template_data["timestamp"] = data_points[idx]["timestamp"]
                        found_timestamp = True
                        logger.info(f"Template {i}: Sử dụng timestamp từ {segment_name}, điểm dữ liệu thứ {idx}")
                else:
                    # Nếu có nhiều template, phân bổ đều trong tập dữ liệu
                    if valid_timestamps:
                        step = max(1, len(valid_timestamps) // len(templates))
                        idx_in_valid = (i * step) % len(valid_timestamps)
                        j, _ = valid_timestamps[idx_in_valid]
                        
                        template_data["timestamp"] = data_points[j]["timestamp"]
                        found_timestamp = True
                        logger.info(f"Template {i}: Sử dụng timestamp từ điểm dữ liệu thứ {j}")
            
            # Nếu không tìm được timestamp từ dữ liệu gốc, sử dụng timestamp hiện tại
            if not found_timestamp:
                template_data["timestamp"] = datetime.now().isoformat()
                logger.warning(f"Template {i}: Không tìm được timestamp phù hợp, sử dụng thời gian hiện tại")
            
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
                device_id=data_points[0].get("device_id", "sensor_02")
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
        logger.info(f"Đã lưu {saved_original_samples} mẫu dữ liệu gốc vào bảng original_samples (100% dữ liệu)")
    
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
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Kiểm thử thuật toán nén dữ liệu IDEALEM")
        parser.add_argument("--save-to-db", action="store_true", help="Lưu dữ liệu nén vào database")
        parser.add_argument("--num-points", type=int, default=3600, help="Số lượng điểm dữ liệu cần tạo (mặc định: 3600)")
        parser.add_argument("--device-id", type=str, default="sensor_02", help="ID của thiết bị (mặc định: sensor_02)")
        parser.add_argument("--date", type=str, help="Ngày tạo dữ liệu (định dạng YYYY-MM-DD, mặc định: hôm nay)")
        parser.add_argument("--start-time", type=str, default="10:00:00", help="Thời gian bắt đầu (định dạng HH:MM:SS, mặc định: 10:00:00)")
        args = parser.parse_args()

        # Sử dụng giá trị mặc định
        num_points = args.num_points
        device_id = args.device_id
        save_to_db = args.save_to_db
        
        # Tương tác với người dùng
        try:
            # Hỏi về tùy chọn số điểm dữ liệu
            use_custom_points = input(f"Bạn có muốn đổi số lượng điểm dữ liệu cần tạo? (y/n, mặc định: n [{num_points} điểm]): ").strip().lower()
            if use_custom_points == 'y' or use_custom_points == 'yes':
                custom_points = input(f"Nhập số điểm dữ liệu (mặc định: {num_points}): ").strip()
                if custom_points and custom_points.isdigit() and int(custom_points) > 0:
                    num_points = int(custom_points)
                    logger.info(f"Sử dụng số điểm dữ liệu: {num_points}")
                else:
                    logger.info(f"Giữ nguyên số điểm dữ liệu mặc định: {num_points}")
            
            # Đặt save_to_db mặc định là True
            if not args.save_to_db:
                save_db_input = input("Bạn có muốn lưu dữ liệu nén vào database? (y/n, mặc định: y): ").strip().lower()
                save_to_db = save_db_input not in ['n', 'no']
            
            # Hỏi về tùy chọn device_id
            use_custom_device = input(f"Bạn có muốn đổi ID thiết bị? (y/n, mặc định: n [{device_id}]): ").strip().lower()
            if use_custom_device == 'y' or use_custom_device == 'yes':
                custom_device = input(f"Nhập ID thiết bị (mặc định: {device_id}): ").strip()
                if custom_device:
                    device_id = custom_device
                    logger.info(f"Sử dụng ID thiết bị: {device_id}")
                else:
                    logger.info(f"Giữ nguyên ID thiết bị mặc định: {device_id}")
        except Exception as e:
            logger.error(f"Lỗi khi xử lý tùy chọn từ người dùng: {str(e)}")
            logger.info(f"Sử dụng giá trị mặc định: {num_points} điểm, device ID: {device_id}, lưu DB: {save_to_db}")

        # Xử lý tham số ngày và thời gian
        start_date = None
        if args.date:
            try:
                date_part = datetime.strptime(args.date, "%Y-%m-%d").date()
                time_part = datetime.strptime(args.start_time, "%H:%M:%S").time() if args.start_time else datetime.strptime("10:00:00", "%H:%M:%S").time()
                start_date = datetime.combine(date_part, time_part)
                logger.info(f"Sử dụng ngày tạo dữ liệu: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
            except ValueError as e:
                logger.error(f"Lỗi định dạng ngày/giờ: {str(e)}")
                logger.info("Sử dụng ngày hiện tại")
                start_date = None
        else:
            # Nếu không có tham số ngày, hỏi người dùng có muốn nhập ngày không
            try:
                use_custom_date = input("Bạn có muốn nhập ngày tháng năm để tạo dữ liệu? (y/n, mặc định n): ").strip().lower()
                if use_custom_date == 'y' or use_custom_date == 'yes':
                    date_input = input("Nhập ngày (định dạng YYYY-MM-DD): ").strip()
                    time_input = input("Nhập giờ (định dạng HH:MM:SS, mặc định 10:00:00): ").strip()
                    
                    if not time_input:
                        time_input = "10:00:00"
                        
                    date_part = datetime.strptime(date_input, "%Y-%m-%d").date()
                    time_part = datetime.strptime(time_input, "%H:%M:%S").time()
                    start_date = datetime.combine(date_part, time_part)
                    logger.info(f"Sử dụng ngày tạo dữ liệu: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logger.info("Sử dụng ngày hiện tại")
            except Exception as e:
                logger.error(f"Lỗi khi nhập ngày: {str(e)}")
                logger.info("Sử dụng ngày hiện tại")
                start_date = None

        # Tạo dữ liệu giả lập
        logger.info("Đang tạo dữ liệu giả lập...")
        sensor_data = generate_sensor_data(num_points=num_points, device_id=device_id, start_date=start_date)
        logger.info(f"Đã tạo {len(sensor_data)} điểm dữ liệu giả lập (mỗi điểm cách nhau 1 phút)")
        
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
        
        # Thông báo trạng thái lưu database
        if save_to_db:
            logger.info("Sẽ lưu dữ liệu nén vào database")
        else:
            logger.info("Không lưu dữ liệu nén vào database")
        
        # Chạy kiểm thử IDEALEM với tính năng thích nghi kích thước khối
        logger.info("Bắt đầu kiểm thử thuật toán nén IDEALEM với tính năng thích nghi kích thước khối...")
        run_idealem_compression_test(sensor_data, idealem_config, save_to_db=save_to_db)
        logger.info("Hoàn thành kiểm thử thuật toán nén IDEALEM")
        
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện kiểm thử: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 