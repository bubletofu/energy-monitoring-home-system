#!/usr/bin/env python3
"""
Script để thêm thiết bị cho người dùng

Cách sử dụng:
    python add_device.py --device-id <device_id>
    
    Tham số:
    --device-id: ID của thiết bị cần thêm
    
Cách hoạt động:
    - Kiểm tra xem thiết bị đã tồn tại trong bảng devices chưa
    - Nếu chưa, tạo mới với user_id của người dùng hiện tại
    - Nếu đã tồn tại, kiểm tra quyền sở hữu và báo lỗi nếu đã thuộc về người dùng khác
"""

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from sqlalchemy import text
from database import get_db
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

def add_device_for_user(device_id, user_id):
    """
    Thêm quyền sở hữu thiết bị cho người dùng.
    
    Args:
        device_id (str): ID của thiết bị
        user_id (int): ID của người dùng
    
    Returns:
        dict: Kết quả của việc thêm thiết bị
    """
    logger.info(f"Đang thêm thiết bị {device_id} cho người dùng {user_id}")
    
    db = next(get_db())
    
    try:
        # Kiểm tra xem thiết bị đã tồn tại trong bảng devices chưa
        check_query = text("""
        SELECT user_id FROM devices 
        WHERE device_id = :device_id
        """)
        
        result = db.execute(check_query, {"device_id": device_id})
        owner = result.fetchone()
        
        if owner:
            current_owner_id = owner[0]
            
            # Nếu giá trị user_id là NULL hoặc None
            if current_owner_id is None:
                # Thiết bị tồn tại nhưng chưa có ai sở hữu, cập nhật user_id
                update_query = text("""
                UPDATE devices
                SET user_id = :user_id
                WHERE device_id = :device_id
                """)
                
                db.execute(update_query, {"device_id": device_id, "user_id": user_id})
                db.commit()
                
                logger.info(f"Thiết bị {device_id} đã được cập nhật quyền sở hữu cho người dùng {user_id}")
                return {
                    "success": True,
                    "message": f"Đã cập nhật quyền sở hữu thiết bị {device_id} thành công"
                }
            
            # Nếu đã sở hữu bởi người dùng hiện tại
            elif current_owner_id == user_id:
                logger.info(f"Thiết bị {device_id} đã thuộc về người dùng {user_id}")
                return {
                    "success": False,
                    "message": f"Thiết bị {device_id} đã thuộc về bạn"
                }
            else:
                logger.warning(f"Thiết bị {device_id} đã thuộc về người dùng {current_owner_id}")
                return {
                    "success": False,
                    "message": f"Thiết bị {device_id} đã thuộc về người dùng khác"
                }
        
        # Kiểm tra thiết bị có tồn tại trên Adafruit IO không
        try:
            # Tham khảo biến môi trường
            adafruit_io_username = os.getenv('ADAFRUIT_IO_USERNAME')
            adafruit_io_key = os.getenv('ADAFRUIT_IO_KEY')
            
            import requests
            
            # Tạo mode_select feed ID
            feed_id = f"{device_id}_mode_select"
            
            # URL kiểm tra feed tồn tại
            url = f"https://io.adafruit.com/api/v2/{adafruit_io_username}/feeds/{feed_id}"
            
            headers = {
                'X-AIO-Key': adafruit_io_key,
                'Content-Type': 'application/json'
            }
            
            # Gửi request GET để kiểm tra feed
            response = requests.get(url, headers=headers)
            
            # Nếu không tìm thấy feed
            if response.status_code == 404:
                logger.warning(f"Thiết bị {device_id} không tồn tại trên Adafruit IO")
                return {
                    "success": False,
                    "message": f"Thiết bị {device_id} không tồn tại trên hệ thống"
                }
                
        except Exception as e:
            logger.warning(f"Không thể kiểm tra thiết bị trên Adafruit IO: {str(e)}")
            # Tiếp tục xử lý, không bắt buộc phải kiểm tra trên Adafruit
        
        insert_query = text("""
        INSERT INTO devices (device_id, user_id)
        VALUES (:device_id, :user_id)
        """)
        
        db.execute(insert_query, {"device_id": device_id, "user_id": user_id})
        db.commit()
        
        logger.info(f"Thiết bị {device_id} đã được thêm cho người dùng {user_id}")
        return {
            "success": True,
            "message": f"Đã thêm thiết bị {device_id} thành công"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khi thêm thiết bị: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi thêm thiết bị: {str(e)}"
        }
    finally:
        db.close()

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
        print(f"- ID người dùng: {args.user_id}")
    else:
        print("="*80)
        print(f"KHÔNG THỂ THÊM THIẾT BỊ: {args.device_id}")
        print(f"Lý do: {result['message']}")
        print("="*80)

if __name__ == "__main__":
    main()
