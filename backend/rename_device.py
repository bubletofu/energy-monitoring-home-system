#!/usr/bin/env python3
"""
Script để đổi tên device_id
"""

import os
import logging
import argparse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def rename_device(old_device_id, new_device_id):
    """Đổi tên device_id"""
    # Load biến môi trường
    load_dotenv()
    
    # Cấu hình Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Bắt đầu transaction
            with connection.begin():
                # 1. Kiểm tra device cũ có tồn tại không
                result = connection.execute(
                    text("SELECT id, name, description FROM devices WHERE device_id = :device_id"),
                    {"device_id": old_device_id}
                ).fetchone()
                
                if not result:
                    raise ValueError(f"Không tìm thấy device với device_id: {old_device_id}")
                
                device_id, name, description = result
                logger.info(f"Đã tìm thấy device cũ: {old_device_id}")
                
                # 2. Kiểm tra device mới đã tồn tại chưa
                result = connection.execute(
                    text("SELECT id FROM devices WHERE device_id = :device_id"),
                    {"device_id": new_device_id}
                ).fetchone()
                
                if result:
                    raise ValueError(f"Device_id {new_device_id} đã tồn tại")
                
                logger.info(f"Device_id mới {new_device_id} chưa tồn tại, có thể sử dụng")
                
                # 3. Tạo device mới
                connection.execute(
                    text("""
                        INSERT INTO devices (device_id, name, description, created_at)
                        VALUES (:device_id, :name, :description, NOW())
                    """),
                    {
                        "device_id": new_device_id,
                        "name": name,
                        "description": description
                    }
                )
                logger.info(f"Đã tạo device mới: {new_device_id}")
                
                # 4. Cập nhật tên trong bảng sensor_data
                connection.execute(
                    text("UPDATE sensor_data SET device_id = :new_device_id WHERE device_id = :old_device_id"),
                    {"new_device_id": new_device_id, "old_device_id": old_device_id}
                )
                logger.info(f"Đã cập nhật device_id trong bảng sensor_data")
                
                # 5. Cập nhật tên trong bảng original_samples
                connection.execute(
                    text("UPDATE original_samples SET device_id = :new_device_id WHERE device_id = :old_device_id"),
                    {"new_device_id": new_device_id, "old_device_id": old_device_id}
                )
                logger.info(f"Đã cập nhật device_id trong bảng original_samples")
                
                # 6. Cập nhật tên trong bảng compressed_data_optimized
                connection.execute(
                    text("UPDATE compressed_data_optimized SET device_id = :new_device_id WHERE device_id = :old_device_id"),
                    {"new_device_id": new_device_id, "old_device_id": old_device_id}
                )
                logger.info(f"Đã cập nhật device_id trong bảng compressed_data_optimized")
                
                # 7. Cập nhật tên trong bảng feed_device_mapping
                connection.execute(
                    text("UPDATE feed_device_mapping SET device_id = :new_device_id WHERE device_id = :old_device_id"),
                    {"new_device_id": new_device_id, "old_device_id": old_device_id}
                )
                logger.info(f"Đã cập nhật device_id trong bảng feed_device_mapping")
                
                # 8. Xóa device cũ
                connection.execute(
                    text("DELETE FROM devices WHERE device_id = :old_device_id"),
                    {"old_device_id": old_device_id}
                )
                logger.info(f"Đã xóa device cũ: {old_device_id}")
                
                logger.info(f"Đã đổi tên device_id từ '{old_device_id}' thành '{new_device_id}' thành công")
                
    except Exception as e:
        logger.error(f"Lỗi khi đổi tên device_id: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Đổi tên device_id')
    parser.add_argument('old_device_id', help='Device_id cũ')
    parser.add_argument('new_device_id', help='Device_id mới')
    args = parser.parse_args()
    
    rename_device(args.old_device_id, args.new_device_id) 