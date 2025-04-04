#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script để xóa bảng device_configs khỏi database
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
    Thực hiện migration để xóa bảng device_configs
    """
    try:
        # Kết nối đến database
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # Kiểm tra xem bảng device_configs có tồn tại không
        has_device_configs_table = inspector.has_table("device_configs")
        
        if not has_device_configs_table:
            logger.info("Bảng device_configs không tồn tại, không cần xóa")
            return True
        
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                logger.info("Đang xóa bảng device_configs...")
                
                # Xóa dữ liệu trong bảng trước
                try:
                    conn.execute(text("DELETE FROM device_configs"))
                    logger.info("Đã xóa dữ liệu trong bảng device_configs")
                except Exception as e:
                    logger.warning(f"Không thể xóa dữ liệu trong bảng device_configs: {str(e)}")
                
                # Xóa bảng
                conn.execute(text("DROP TABLE device_configs"))
                logger.info("Đã xóa bảng device_configs thành công")
                
                # Commit transaction
                transaction.commit()
                logger.info("Migration hoàn tất thành công")
                
            except Exception as e:
                transaction.rollback()
                logger.error(f"Lỗi khi xóa bảng device_configs: {str(e)}")
                raise
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện migration: {str(e)}")
        return False

def main():
    """
    Hàm chính để chạy migration
    """
    print("==> Bắt đầu xóa bảng device_configs...")
    
    if run_migration():
        print("==> Migration hoàn tất thành công!")
    else:
        print("==> Migration thất bại!")
        sys.exit(1)

if __name__ == "__main__":
    main() 