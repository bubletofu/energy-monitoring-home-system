#!/usr/bin/env python3
"""
Script để thiết lập cơ sở dữ liệu PostgreSQL từ đầu.
Bao gồm tạo database, các bảng cần thiết và thêm dữ liệu mẫu.

Cách sử dụng:
    python setup_database.py [--reset] [--sample-data]

Tùy chọn:
    --reset: Xóa và tạo lại database
    --sample-data: Thêm dữ liệu mẫu vào database
"""

import os
import sys
import argparse
import logging
import datetime
import random
import time
import json
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("setup_database.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_connection_string(database_name=None):
    """
    Tạo chuỗi kết nối dựa trên các biến môi trường hoặc giá trị mặc định
    """
    # Lấy thông tin kết nối từ biến môi trường
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5433")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "1234")
    
    # Tạo URL kết nối
    if database_name:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{database_name}"
    else:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/postgres"

def create_database(database_name="iot_db", reset=False):
    """
    Tạo database nếu chưa tồn tại hoặc reset nếu được chỉ định
    """
    # Kết nối đến database mặc định postgres để tạo database mới
    engine = create_engine(get_connection_string())
    conn = engine.connect()
    conn.execute(text("COMMIT"))  # Commit transaction trước
    
    try:
        if reset:
            # Ngắt kết nối tất cả client kết nối đến database
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{database_name}'
                AND pid <> pg_backend_pid()
            """))
            conn.execute(text("COMMIT"))
            
            # Drop database nếu tồn tại
            conn.execute(text(f"DROP DATABASE IF EXISTS {database_name}"))
            logger.info(f"Đã xóa database {database_name} (nếu tồn tại)")
        
        # Kiểm tra xem database đã tồn tại chưa
        result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'"))
        exists = result.scalar() == 1
        
        # Tạo database nếu chưa tồn tại
        if not exists:
            conn.execute(text(f"CREATE DATABASE {database_name}"))
            logger.info(f"Đã tạo database {database_name}")
        else:
            logger.info(f"Database {database_name} đã tồn tại")
            
    except Exception as e:
        logger.error(f"Lỗi khi tạo database: {str(e)}")
        raise
    finally:
        conn.close()
        engine.dispose()

def create_tables(database_name="iot_db"):
    """
    Tạo tất cả các bảng được định nghĩa trong models.py
    """
    try:
        # Import models ở đây để tránh lỗi circular import
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import Base
        
        # Kết nối đến database đã tạo
        engine = create_engine(get_connection_string(database_name))
        
        # Tạo tất cả các bảng đã định nghĩa
        Base.metadata.create_all(bind=engine)
        
        # Kiểm tra các bảng đã tạo
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Đã tạo thành công các bảng: {', '.join(tables)}")
        
        return engine
    except ImportError:
        logger.error("Không thể import models. Đảm bảo file models.py tồn tại và có thể truy cập.")
        raise
    except Exception as e:
        logger.error(f"Lỗi khi tạo bảng: {str(e)}")
        raise

def add_sample_data(engine):
    """
    Thêm dữ liệu mẫu vào database
    """
    try:
        # Import models ở đây để tránh lỗi circular import
        from models import User, DeviceConfig, Device, OriginalSample, SensorData
        
        # Tạo session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Kiểm tra xem đã có dữ liệu chưa
            existing_users = db.query(User).count()
            existing_devices = db.query(Device).count()
            
            if existing_users > 0 and existing_devices > 0:
                logger.info("Dữ liệu mẫu đã tồn tại, bỏ qua bước tạo dữ liệu mẫu.")
                return
            
            # Tạo user mẫu
            sample_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
            )
            db.add(sample_user)
            db.commit()
            db.refresh(sample_user)
            logger.info(f"Đã tạo user mẫu: {sample_user.username}")
            
            # Tạo device mẫu
            sample_devices = [
                Device(device_id="motk", name="Motion Sensor Kitchen", description="Kitchen motion sensor"),
                Device(device_id="temp01", name="Temperature Living Room", description="Living room temperature sensor"),
                Device(device_id="humi01", name="Humidity Bathroom", description="Bathroom humidity sensor")
            ]
            
            for device in sample_devices:
                db.add(device)
            
            db.commit()
            logger.info(f"Đã tạo {len(sample_devices)} thiết bị mẫu")
            
            # Tạo device config mẫu
            sample_config = DeviceConfig(
                user_id=sample_user.id,
                device_id="motk",
                config_data={"threshold": 25, "interval": 60}
            )
            db.add(sample_config)
            db.commit()
            logger.info("Đã tạo cấu hình thiết bị mẫu")
            
            # Tạo dữ liệu cảm biến mẫu
            now = datetime.datetime.utcnow()
            
            # Tạo dữ liệu cho mỗi thiết bị
            for device in sample_devices:
                logger.info(f"Đang tạo dữ liệu mẫu cho thiết bị {device.device_id}...")
                
                # Tạo dữ liệu mẫu cho bảng original_samples
                for i in range(100):  # 100 mẫu cho mỗi thiết bị
                    timestamp = now - datetime.timedelta(hours=i)
                    
                    # Tạo dữ liệu tùy theo loại thiết bị
                    if "Temperature" in device.name:
                        original_data = {
                            "temperature": round(random.uniform(18, 30), 1),
                            "humidity": round(random.uniform(40, 70), 1)
                        }
                    elif "Humidity" in device.name:
                        original_data = {
                            "humidity": round(random.uniform(40, 80), 1),
                            "temperature": round(random.uniform(18, 28), 1)
                        }
                    else:  # Motion sensor
                        original_data = {
                            "power": round(random.uniform(0, 100), 1),
                            "pressure": round(random.uniform(980, 1020), 1)
                        }
                    
                    # Thêm vào bảng original_samples
                    sample = OriginalSample(
                        device_id=device.device_id,
                        original_data=original_data,
                        timestamp=timestamp
                    )
                    db.add(sample)
                    
                    # Thêm vào bảng sensor_data
                    for key, value in original_data.items():
                        sensor_data = SensorData(
                            device_id=device.device_id,
                            feed_id=f"{device.device_id}_{key}",
                            value=value,
                            timestamp=timestamp
                        )
                        db.add(sensor_data)
                
                # Commit sau mỗi thiết bị để tránh giao dịch quá lớn
                db.commit()
                logger.info(f"Đã tạo 100 mẫu dữ liệu cho thiết bị {device.device_id}")
            
            logger.info("Đã tạo dữ liệu mẫu thành công!")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi khi tạo dữ liệu mẫu: {str(e)}")
            raise
        finally:
            db.close()
            
    except ImportError:
        logger.error("Không thể import models. Đảm bảo file models.py tồn tại và có thể truy cập.")
        raise
    except Exception as e:
        logger.error(f"Lỗi khi thêm dữ liệu mẫu: {str(e)}")
        raise

def update_env_file(database_name="iot_db"):
    """
    Cập nhật hoặc tạo file .env với thông tin kết nối database
    """
    try:
        # Lấy thông tin kết nối
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5433")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "1234")
        
        # Tạo chuỗi kết nối
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{database_name}"
        
        # Đọc file .env nếu đã tồn tại
        env_content = ""
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                env_content = f.read()
        
        # Kiểm tra xem DATABASE_URL đã tồn tại trong file chưa
        if "DATABASE_URL=" in env_content:
            # Cập nhật DATABASE_URL
            env_lines = env_content.split("\n")
            updated_lines = []
            for line in env_lines:
                if line.startswith("DATABASE_URL="):
                    updated_lines.append(f"DATABASE_URL={database_url}")
                else:
                    updated_lines.append(line)
            env_content = "\n".join(updated_lines)
        else:
            # Thêm DATABASE_URL vào file
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f"DATABASE_URL={database_url}\n"
        
        # Ghi lại file .env
        with open(".env", "w") as f:
            f.write(env_content)
        
        logger.info(f"Đã cập nhật file .env với DATABASE_URL={database_url}")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật file .env: {str(e)}")

def main():
    """
    Hàm chính để thiết lập database
    """
    parser = argparse.ArgumentParser(description="Thiết lập cơ sở dữ liệu PostgreSQL")
    parser.add_argument("--reset", action="store_true", help="Xóa và tạo lại database")
    parser.add_argument("--sample-data", action="store_true", help="Thêm dữ liệu mẫu vào database")
    parser.add_argument("--database", type=str, default="iot_db", help="Tên database (mặc định: iot_db)")
    parser.add_argument("--host", type=str, help="Host của PostgreSQL (mặc định: localhost)")
    parser.add_argument("--port", type=str, help="Port của PostgreSQL (mặc định: 5433)")
    parser.add_argument("--user", type=str, help="Username PostgreSQL (mặc định: postgres)")
    parser.add_argument("--password", type=str, help="Password PostgreSQL (mặc định: 1234)")
    
    args = parser.parse_args()
    
    # Cập nhật biến môi trường nếu được cung cấp
    if args.host:
        os.environ["DB_HOST"] = args.host
    if args.port:
        os.environ["DB_PORT"] = args.port
    if args.user:
        os.environ["DB_USER"] = args.user
    if args.password:
        os.environ["DB_PASSWORD"] = args.password
    
    try:
        logger.info("Bắt đầu thiết lập database...")
        
        # Tạo database
        create_database(args.database, args.reset)
        
        # Tạo các bảng
        engine = create_tables(args.database)
        
        # Thêm dữ liệu mẫu nếu được yêu cầu
        if args.sample_data:
            add_sample_data(engine)
        
        # Cập nhật file .env
        update_env_file(args.database)
        
        logger.info(f"Đã thiết lập database {args.database} thành công!")
        
        # Hiển thị thông tin kết nối
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5433")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "1234")
        
        print("\n" + "="*80)
        print(f"Database đã sẵn sàng để sử dụng!")
        print(f"  - Database: {args.database}")
        print(f"  - Host: {db_host}")
        print(f"  - Port: {db_port}")
        print(f"  - User: {db_user}")
        print(f"  - Password: {'*' * len(db_password)}")
        print(f"  - Connection URL: postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{args.database}")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập database: {str(e)}")
        print(f"\nLỗi: Không thể thiết lập database. Xem chi tiết trong file log: setup_database.log")
        sys.exit(1)

if __name__ == "__main__":
    main() 