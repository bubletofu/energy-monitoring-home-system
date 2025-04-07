#!/usr/bin/env python3
"""
Script để thêm thiết bị cho người dùng

Cách sử dụng:
    python add_device.py --device-id <device_id> [--name <name>]
    
    Tham số:
    --device-id: ID của thiết bị cần thêm
    --name: Tên hiển thị của thiết bị (tùy chọn)
    
Cách hoạt động:
    - Nếu thiết bị chưa tồn tại, báo lỗi
    - Nếu thiết bị đã tồn tại và có user_id = 1, cập nhật thành user_id của người dùng hiện tại
    - Nếu thiết bị đã tồn tại và có user_id khác 1, báo lỗi (thiết bị đã thuộc về người dùng khác)
"""

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
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

# Cấu hình Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")

# Tạo Base cho models
Base = declarative_base()

def add_device_for_user(device_id, user_id):
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
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Kiểm tra thiết bị đã tồn tại chưa
            device_check = session.execute(
                text("SELECT id, device_id, user_id FROM devices WHERE device_id = :device_id"),
                {"device_id": device_id}
            ).fetchone()
            
            if not device_check:
                logger.warning(f"Không tìm thấy thiết bị với ID: {device_id}")
                return {
                    "success": False,
                    "message": f"Không tìm thấy thiết bị với ID: {device_id}. Thiết bị phải tồn tại trước khi được gán cho người dùng.",
                    "device_id": device_id
                }
            
            # Thiết bị đã tồn tại
            device_id_from_db = device_check[1]
            current_user_id = device_check[2]
            
            # Kiểm tra nếu thiết bị đã có người dùng khác với user_id=1
            if current_user_id is not None and current_user_id != 1 and current_user_id != user_id:
                logger.warning(f"Thiết bị {device_id} đã thuộc về người dùng khác (ID: {current_user_id})")
                return {
                    "success": False,
                    "message": f"Thiết bị {device_id} đã thuộc về người dùng khác",
                    "device_id": device_id,
                    "current_owner": current_user_id
                }
            
            # Cập nhật thiết bị cho người dùng mới nếu chưa có chủ hoặc thuộc về user_id=1
            if current_user_id is None or current_user_id == 1:
                # Cập nhật thiết bị
                session.execute(
                    text("UPDATE devices SET user_id = :user_id WHERE device_id = :device_id"),
                    {"user_id": user_id, "device_id": device_id}
                )
                
                session.commit()
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
            session.rollback()
            logger.error(f"Lỗi khi thêm thiết bị: {str(e)}")
            raise
        finally:
            session.close()
            
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
    parser.add_argument("--name", type=str, help="Tên hiển thị của thiết bị")
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
