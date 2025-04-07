#!/usr/bin/env python3
"""
Script để xóa thiết bị và tất cả dữ liệu liên quan từ database

Cách sử dụng:
    python remove_device.py --device-id <device_id> [--confirm]
    
    Tham số:
    --device-id: ID của thiết bị cần xóa
    --confirm: Xác nhận xóa mà không cần hỏi lại
    --user-id: ID của người dùng yêu cầu xóa thiết bị (để kiểm tra quyền sở hữu)
"""

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging
log_file = 'remove_device.log'
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

def check_tables_with_device_foreign_keys(engine, device_id):
    """
    Kiểm tra tất cả các bảng có chứa foreign key đến device_id trong bảng devices
    """
    try:
        with engine.connect() as conn:
            # Kiểm tra các bảng với cột device_id
            tables_with_references = [
                "sensor_data", 
                "original_samples", 
                "compressed_data_optimized"
            ]
            
            results = {}
            
            for table in tables_with_references:
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table} WHERE device_id = :device_id"),
                        {"device_id": device_id}
                    ).fetchone()
                    
                    if result and result[0] > 0:
                        results[table] = result[0]
                except Exception as e:
                    logger.warning(f"Không thể kiểm tra bảng {table}: {str(e)}")
            
            return results
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra các bảng có foreign key: {str(e)}")
        return {}

def remove_device(device_id, confirm=False, user_id=None):
    """
    Xóa thiết bị và tất cả dữ liệu liên quan
    
    Args:
        device_id: ID của thiết bị cần xóa
        confirm: Xác nhận xóa mà không cần hỏi lại
        user_id: ID của người dùng (để kiểm tra quyền sở hữu)
        
    Returns:
        dict: Kết quả xóa thiết bị
    """
    try:
        # Kết nối database
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Bắt đầu transaction
            transaction = conn.begin()
            
            # Biến để theo dõi trạng thái
            device_exists = False
            has_devices_table = False
            
            # Thử kiểm tra bảng devices
            try:
                conn.execute(text("SELECT 1 FROM devices LIMIT 1"))
                has_devices_table = True
                
                if has_devices_table:
                    # Lấy thông tin chi tiết về thiết bị
                    device_info = conn.execute(
                        text("SELECT id, device_id, user_id FROM devices WHERE device_id = :device_id"),
                        {"device_id": device_id}
                    ).fetchone()
                    
                    if device_info:
                        device_exists = True
                        device_id_in_db = device_info[1]  # device_id
                        device_owner_id = device_info[2]  # user_id
                        logger.info(f"Tìm thấy thiết bị trong bảng devices: {device_id_in_db} (Owner ID: {device_owner_id})")
                        
                        # Kiểm tra quyền sở hữu nếu user_id được cung cấp
                        if user_id is not None and device_owner_id is not None and device_owner_id != user_id and user_id != 1:
                            logger.warning(f"Người dùng {user_id} không có quyền xóa thiết bị thuộc về người dùng {device_owner_id}")
                            return {
                                "success": False,
                                "message": f"Bạn không có quyền xóa thiết bị này. Thiết bị thuộc về người dùng khác.",
                                "device_id": device_id,
                                "owner_id": device_owner_id
                            }
            except Exception as e:
                logger.warning(f"Lỗi khi kiểm tra bảng devices: {str(e)}")
            
            # Kiểm tra các bảng có tham chiếu đến thiết bị này
            references = check_tables_with_device_foreign_keys(engine, device_id)
            
            # Nếu không tìm thấy thiết bị trong bất kỳ bảng nào
            if not device_exists and not references:
                logger.warning(f"Không tìm thấy thiết bị {device_id} trong bất kỳ bảng nào")
                return {
                    "success": False,
                    "message": f"Không tìm thấy thiết bị {device_id}",
                    "device_id": device_id
                }
            
            # Nếu không có xác nhận và có dữ liệu
            if not confirm and references:
                # Hiển thị thông tin về dữ liệu sẽ bị xóa
                return {
                    "success": False,
                    "message": "Cần xác nhận xóa",
                    "device_id": device_id,
                    "references": references,
                    "needs_confirmation": True
                }
            
            try:
                # Xóa dữ liệu từ các bảng con trước
                for table in references:
                    if table != "devices":  # Để bảng devices lại để xóa cuối cùng
                        conn.execute(
                            text(f"DELETE FROM {table} WHERE device_id = :device_id"),
                            {"device_id": device_id}
                        )
                        logger.info(f"Đã xóa dữ liệu từ bảng {table}")
                
                # Cuối cùng xóa từ bảng devices nếu có
                if has_devices_table:
                    conn.execute(
                        text("DELETE FROM devices WHERE device_id = :device_id"),
                        {"device_id": device_id}
                    )
                    logger.info("Đã xóa thiết bị từ bảng devices")
                
                # Commit transaction
                transaction.commit()
                logger.info(f"Đã xóa thành công thiết bị {device_id}")
                
                return {
                    "success": True,
                    "message": f"Đã xóa thiết bị {device_id} và tất cả dữ liệu liên quan",
                    "device_id": device_id,
                    "deleted_counts": references
                }
                
            except Exception as e:
                transaction.rollback()
                logger.error(f"Lỗi khi xóa thiết bị: {str(e)}")
                return {
                    "success": False,
                    "message": f"Lỗi khi xóa thiết bị: {str(e)}",
                    "device_id": device_id
                }
                
    except Exception as e:
        logger.error(f"Lỗi khi kết nối database: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi kết nối database: {str(e)}",
            "device_id": device_id
        }

def main():
    parser = argparse.ArgumentParser(description="Xóa thiết bị và tất cả dữ liệu liên quan từ database")
    parser.add_argument("--device-id", type=str, required=True, help="ID của thiết bị cần xóa")
    parser.add_argument("--confirm", action="store_true", help="Xác nhận xóa mà không cần hỏi lại")
    parser.add_argument("--user-id", type=int, help="ID của người dùng yêu cầu xóa thiết bị (để kiểm tra quyền sở hữu)")
    
    args = parser.parse_args()
    
    result = remove_device(args.device_id, args.confirm, args.user_id)
    
    if result["success"]:
        print("="*80)
        print(f"ĐÃ XÓA THÀNH CÔNG THIẾT BỊ: {args.device_id}")
        print("="*80)
        if "deleted_counts" in result:
            for table, count in result["deleted_counts"].items():
                print(f"- {table}: {count} bản ghi")
    else:
        print("="*80)
        print(f"KHÔNG THỂ XÓA THIẾT BỊ: {args.device_id}")
        print(f"Lý do: {result['message']}")
        print("="*80)
        if "owner_id" in result:
            print(f"Thiết bị thuộc về người dùng ID: {result['owner_id']}")

if __name__ == "__main__":
    main()
