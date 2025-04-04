#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script để thêm các cột trạng thái thiết bị vào bảng devices
"""

import logging
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Kết nối database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/iot_db")

def run_migration():
    """
    Thực hiện migration để thêm các cột trạng thái thiết bị vào bảng devices
    """
    try:
        # Kết nối đến database
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # Kiểm tra xem bảng devices có tồn tại không
        has_devices_table = inspector.has_table("devices")
        
        if not has_devices_table:
            logger.error("Bảng devices không tồn tại, không thể thêm các cột trạng thái")
            return False
        
        # Kiểm tra cấu trúc bảng devices
        columns = inspector.get_columns("devices")
        column_names = [col["name"] for col in columns]
        
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                logger.info("Kiểm tra và thêm các cột trạng thái thiết bị...")
                
                # Thêm cột is_online nếu chưa tồn tại
                if "is_online" not in column_names:
                    logger.info("Thêm cột is_online")
                    conn.execute(text("ALTER TABLE devices ADD COLUMN is_online BOOLEAN DEFAULT FALSE"))
                    
                # Thêm cột last_value nếu chưa tồn tại
                if "last_value" not in column_names:
                    logger.info("Thêm cột last_value")
                    conn.execute(text("ALTER TABLE devices ADD COLUMN last_value FLOAT"))
                    
                # Thêm cột last_updated nếu chưa tồn tại
                if "last_updated" not in column_names:
                    logger.info("Thêm cột last_updated")
                    conn.execute(text("ALTER TABLE devices ADD COLUMN last_updated TIMESTAMP"))
                    
                # Thêm cột status_details nếu chưa tồn tại
                if "status_details" not in column_names:
                    logger.info("Thêm cột status_details")
                    conn.execute(text("ALTER TABLE devices ADD COLUMN status_details JSONB"))
                    
                # Tạo index cho cột is_online để tối ưu truy vấn
                try:
                    logger.info("Tạo index cho cột is_online")
                    conn.execute(text("CREATE INDEX idx_devices_is_online ON devices (is_online)"))
                except Exception as e:
                    # Index có thể đã tồn tại
                    logger.warning(f"Không thể tạo index cho cột is_online: {str(e)}")
                
                # Commit transaction
                transaction.commit()
                logger.info("Migration hoàn tất thành công")
                
            except Exception as e:
                transaction.rollback()
                logger.error(f"Lỗi khi thêm các cột trạng thái: {str(e)}")
                raise
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện migration: {str(e)}")
        return False

def main():
    """
    Hàm chính để chạy migration
    """
    print("==> Bắt đầu thêm các cột trạng thái thiết bị vào bảng devices...")
    
    if run_migration():
        print("==> Migration hoàn tất thành công!")
    else:
        print("==> Migration thất bại!")
        sys.exit(1)

if __name__ == "__main__":
    main() 