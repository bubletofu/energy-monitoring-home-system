#!/usr/bin/env python3
"""
Script để đổi tên device_id của người dùng
"""

import os
import logging
import argparse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import models
from typing import Dict, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_device_ownership(device_id: str, user_id: int, db: Session) -> bool:
    """
    Kiểm tra xem người dùng có sở hữu thiết bị không
    
    Args:
        device_id: ID của thiết bị
        user_id: ID của người dùng
        db: Database session
        
    Returns:
        bool: True nếu người dùng sở hữu thiết bị, False nếu không
    """
    try:
        device = db.query(models.Device).filter(
            models.Device.device_id == device_id,
            models.Device.user_id == user_id
        ).first()
        
        return device is not None
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra quyền sở hữu thiết bị: {str(e)}")
        return False

def rename_device(old_device_id: str, new_device_id: str, user_id: int) -> Dict[str, Any]:
    """
    Đổi tên device_id của người dùng.
    Chỉ cho phép đổi tên nếu người dùng sở hữu thiết bị đó.
    
    Args:
        old_device_id: ID cũ của thiết bị
        new_device_id: ID mới của thiết bị
        user_id: ID của người dùng thực hiện đổi tên
        
    Returns:
        dict: Kết quả đổi tên thiết bị
    """
    try:
        # Tạo session mới
        from database import SessionLocal
        db = SessionLocal()
        
        try:
            # Kiểm tra quyền sở hữu thiết bị
            if not check_device_ownership(old_device_id, user_id, db):
                return {
                    "success": False,
                    "message": f"Bạn không có quyền đổi tên thiết bị {old_device_id}"
                }
            
            # Kiểm tra device_id mới chưa tồn tại
            existing_device = db.query(models.Device).filter(
                models.Device.device_id == new_device_id
            ).first()
            
            if existing_device:
                return {
                    "success": False,
                    "message": f"Device_id {new_device_id} đã tồn tại"
                }
            
            # Cập nhật device_id trong các bảng liên quan
            # 1. Cập nhật bảng devices
            device = db.query(models.Device).filter(
                models.Device.device_id == old_device_id
            ).first()
            
            if device:
                device.device_id = new_device_id
                db.commit()
                logger.info(f"Đã cập nhật device_id trong bảng devices")
            
            # 2. Cập nhật bảng sensor_data
            sensor_data_count = db.query(models.SensorData).filter(
                models.SensorData.device_id == old_device_id
            ).count()
            
            if sensor_data_count > 0:
                db.query(models.SensorData).filter(
                    models.SensorData.device_id == old_device_id
                ).update({"device_id": new_device_id})
                db.commit()
                logger.info(f"Đã cập nhật {sensor_data_count} bản ghi trong bảng sensor_data")
            
            # 3. Cập nhật bảng original_samples
            try:
                original_samples_count = db.execute(
                    text("SELECT COUNT(*) FROM original_samples WHERE device_id = :old_device_id"),
                    {"old_device_id": old_device_id}
                ).scalar()
                
                if original_samples_count and original_samples_count > 0:
                    db.execute(
                        text("UPDATE original_samples SET device_id = :new_device_id WHERE device_id = :old_device_id"),
                        {"new_device_id": new_device_id, "old_device_id": old_device_id}
                    )
                    db.commit()
                    logger.info(f"Đã cập nhật {original_samples_count} bản ghi trong bảng original_samples")
            except Exception as e:
                logger.warning(f"Không thể cập nhật dữ liệu từ original_samples: {str(e)}")
            
            # 4. Cập nhật bảng compressed_data_optimized
            try:
                compressed_count = db.execute(
                    text("SELECT COUNT(*) FROM compressed_data_optimized WHERE device_id = :old_device_id"),
                    {"old_device_id": old_device_id}
                ).scalar()
                
                if compressed_count and compressed_count > 0:
                    db.execute(
                        text("UPDATE compressed_data_optimized SET device_id = :new_device_id WHERE device_id = :old_device_id"),
                        {"new_device_id": new_device_id, "old_device_id": old_device_id}
                    )
                    db.commit()
                    logger.info(f"Đã cập nhật {compressed_count} bản ghi trong bảng compressed_data_optimized")
            except Exception as e:
                logger.warning(f"Không thể cập nhật dữ liệu từ compressed_data_optimized: {str(e)}")
            
            # 5. Cập nhật bảng feed_device_mapping
            try:
                mapping_count = db.execute(
                    text("SELECT COUNT(*) FROM feed_device_mapping WHERE device_id = :old_device_id"),
                    {"old_device_id": old_device_id}
                ).scalar()
                
                if mapping_count and mapping_count > 0:
                    db.execute(
                        text("UPDATE feed_device_mapping SET device_id = :new_device_id WHERE device_id = :old_device_id"),
                        {"new_device_id": new_device_id, "old_device_id": old_device_id}
                    )
                    db.commit()
                    logger.info(f"Đã cập nhật {mapping_count} bản ghi trong bảng feed_device_mapping")
            except Exception as e:
                logger.warning(f"Không thể cập nhật dữ liệu từ feed_device_mapping: {str(e)}")
            
            return {
                "success": True,
                "message": f"Đã đổi tên device_id từ '{old_device_id}' thành '{new_device_id}' thành công"
            }
            
        except Exception as e:
            db.rollback()
            raise
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Lỗi khi đổi tên device_id: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi đổi tên device_id: {str(e)}"
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Đổi tên device_id của người dùng')
    parser.add_argument('old_device_id', help='Device_id cũ')
    parser.add_argument('new_device_id', help='Device_id mới')
    parser.add_argument('user_id', type=int, help='ID của người dùng')
    args = parser.parse_args()
    
    rename_device(args.old_device_id, args.new_device_id, args.user_id)
