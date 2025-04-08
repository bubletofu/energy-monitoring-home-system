#!/usr/bin/env python3
"""
Script để thêm thiết bị cho người dùng

Cách sử dụng:
    python add_device.py --device-id <device_id>
    
    Tham số:
    --device-id: ID của thiết bị cần thêm
    
Cách hoạt động:
    - Nếu thiết bị chưa tồn tại, tạo mới với user_id = NULL
    - Nếu thiết bị đã tồn tại và có user_id = NULL, cập nhật thành user_id của người dùng hiện tại
    - Nếu thiết bị đã tồn tại và có user_id khác NULL, báo lỗi (thiết bị đã thuộc về người dùng khác)
"""

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from sqlalchemy import text
from database import engine
import datetime
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging
log_file = 'add_device.log'
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

def add_device_for_user(device_id: str, user_id: int) -> dict:
    """
    Thêm thiết bị cho người dùng
    
    Args:
        device_id: ID của thiết bị
        user_id: ID của người dùng
        
    Returns:
        dict: Kết quả thêm thiết bị
    """
    try:
        # Kết nối database
        with engine.connect() as conn:
            try:
                # Kiểm tra thiết bị đã tồn tại chưa
                result = conn.execute(
                    text("""
                        SELECT user_id 
                        FROM devices 
                        WHERE device_id = :device_id
                    """),
                    {"device_id": device_id}
                )
                device = result.first()
                
                if not device:
                    # Nếu thiết bị chưa tồn tại, tạo mới với user_id = NULL
                    conn.execute(
                        text("""
                            INSERT INTO devices (device_id, user_id)
                            VALUES (:device_id, NULL)
                        """),
                        {"device_id": device_id}
                    )
                    conn.commit()
                    return {
                        "success": True,
                        "message": f"Đã tạo mới thiết bị {device_id}",
                        "device_id": device_id
                    }
                
                current_user_id = device[0]
                
                # Kiểm tra nếu thiết bị đã có người dùng khác
                if current_user_id is not None and current_user_id != user_id:
                    logger.warning(f"Thiết bị {device_id} đã thuộc về người dùng khác (ID: {current_user_id})")
                    return {
                        "success": False,
                        "message": f"Thiết bị {device_id} đã thuộc về người dùng khác",
                        "device_id": device_id,
                        "current_owner": current_user_id
                    }
                
                # Cập nhật thiết bị cho người dùng mới nếu chưa có chủ
                if current_user_id is None:
                    # Cập nhật thiết bị
                    conn.execute(
                        text("""
                            UPDATE devices 
                            SET user_id = :user_id
                            WHERE device_id = :device_id
                        """),
                        {"user_id": user_id, "device_id": device_id}
                    )
                    
                    conn.commit()
                    logger.info(f"Đã cập nhật thiết bị {device_id} cho người dùng {user_id}")
                    
                    return {
                        "success": True,
                        "message": f"Đã cập nhật thiết bị {device_id} cho tài khoản của bạn",
                        "device_id": device_id,
                        "user_id": user_id
                    }
                
                # Nếu thiết bị đã thuộc về người dùng này rồi
                if current_user_id == user_id:
                    return {
                        "success": True,
                        "message": f"Thiết bị {device_id} đã thuộc về tài khoản của bạn",
                        "device_id": device_id,
                        "user_id": user_id
                    }
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Lỗi khi thêm thiết bị: {str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"Lỗi kết nối database: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi thêm thiết bị: {str(e)}",
            "device_id": device_id
        }

def main():
    parser = argparse.ArgumentParser(description="Thêm thiết bị cho người dùng")
    parser.add_argument("--device-id", type=str, required=True, help="ID của thiết bị cần thêm")
    parser.add_argument("--user-id", type=int, required=True, help="ID của người dùng")
    
    args = parser.parse_args()
    
    result = add_device_for_user(args.device_id, args.user_id)
    
    if result["success"]:
        print("="*80)
        print(f"ĐÃ THÊM THIẾT BỊ THÀNH CÔNG: {args.device_id}")
        print("="*80)
        print(f"- ID người dùng: {result.get('user_id')}")
    else:
        print("="*80)
        print(f"KHÔNG THỂ THÊM THIẾT BỊ: {args.device_id}")
        print(f"Lý do: {result['message']}")
        print("="*80)

if __name__ == "__main__":
    main()
