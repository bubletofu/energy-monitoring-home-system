#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để di chuyển dữ liệu thiết bị từ cấu trúc cũ sang cấu trúc mới
"""

import logging
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Kết nối database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/iot_db")

def migrate_device_data():
    """
    Di chuyển dữ liệu thiết bị: gán user_id cho các thiết bị hiện tại
    """
    try:
        # Kết nối đến database
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Lấy thông tin người dùng admin (người dùng đầu tiên)
            admin_user = session.execute(text("""
                SELECT id FROM users ORDER BY id LIMIT 1
            """)).scalar()
            
            if not admin_user:
                logger.warning("Không tìm thấy người dùng nào, không thể di chuyển dữ liệu")
                return False
            
            # Đếm số thiết bị không có user_id
            null_user_count = session.execute(text("""
                SELECT COUNT(*) FROM devices WHERE user_id IS NULL
            """)).scalar()
            
            logger.info(f"Có {null_user_count} thiết bị không có user_id")
            
            if null_user_count > 0:
                # Cập nhật user_id cho các thiết bị không có chủ sở hữu
                result = session.execute(text("""
                    UPDATE devices SET user_id = :admin_id WHERE user_id IS NULL
                """), {"admin_id": admin_user})
                
                session.commit()
                
                logger.info(f"Đã cập nhật user_id cho {null_user_count} thiết bị")
            else:
                logger.info("Không có thiết bị nào cần cập nhật")
            
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Lỗi khi di chuyển dữ liệu: {str(e)}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Lỗi khi di chuyển dữ liệu: {str(e)}")
        return False

def main():
    """
    Hàm chính để chạy migration dữ liệu
    """
    print("==> Bắt đầu di chuyển dữ liệu thiết bị...")
    
    if migrate_device_data():
        print("==> Di chuyển dữ liệu thành công!")
    else:
        print("==> Di chuyển dữ liệu thất bại!")
        sys.exit(1)

if __name__ == "__main__":
    main() 