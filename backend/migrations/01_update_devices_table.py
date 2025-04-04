#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script để thay đổi cấu trúc bảng devices:
- Xóa cột description
- Thêm cột user_id tham chiếu đến bảng users
"""

import logging
import os
import sys
from sqlalchemy import create_engine, text, inspect
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
    Thực hiện migration bảng devices
    """
    try:
        # Kết nối đến database
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # Kiểm tra xem bảng devices có tồn tại không
        has_devices_table = inspector.has_table("devices")
        
        if not has_devices_table:
            logger.info("Bảng devices không tồn tại, không cần migration")
            return True
        
        # Kiểm tra cấu trúc bảng devices
        columns = inspector.get_columns("devices")
        column_names = [col["name"] for col in columns]
        
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                # Step 1: Kiểm tra xem đã có cột user_id chưa
                if "user_id" in column_names:
                    logger.info("Cột user_id đã tồn tại trong bảng devices")
                else:
                    # Step 2: Thêm cột user_id
                    logger.info("Thêm cột user_id vào bảng devices")
                    conn.execute(text("""
                        ALTER TABLE devices ADD COLUMN user_id INTEGER;
                    """))
                
                # Step 3: Kiểm tra xem có cột description không
                if "description" not in column_names:
                    logger.info("Không tìm thấy cột description, migration đã hoàn thành")
                else:
                    # Step 4: Xóa cột description
                    logger.info("Xóa cột description từ bảng devices")
                    conn.execute(text("""
                        ALTER TABLE devices DROP COLUMN description;
                    """))
                
                # Step 5: Kiểm tra và thêm foreign key
                foreign_keys = [fk for fk in inspector.get_foreign_keys("devices") 
                                if "user_id" in fk["constrained_columns"]]
                
                if not foreign_keys:
                    logger.info("Thêm foreign key cho cột user_id")
                    conn.execute(text("""
                        ALTER TABLE devices 
                        ADD CONSTRAINT fk_devices_users
                        FOREIGN KEY (user_id) REFERENCES users(id);
                    """))
                else:
                    logger.info("Foreign key đã tồn tại cho cột user_id")
                
                # Commit transaction
                transaction.commit()
                logger.info("Migration hoàn tất thành công")
                
            except Exception as e:
                transaction.rollback()
                logger.error(f"Lỗi khi thực hiện migration: {str(e)}")
                raise
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện migration: {str(e)}")
        return False

def main():
    """
    Hàm chính để chạy migration
    """
    print("==> Bắt đầu thực hiện migration bảng devices...")
    
    if run_migration():
        print("==> Migration hoàn tất thành công!")
    else:
        print("==> Migration thất bại!")
        sys.exit(1)

if __name__ == "__main__":
    main() 