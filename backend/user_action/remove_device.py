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
    Xóa thiết bị và tất cả dữ liệu liên quan từ database.
    Luôn xóa triệt để để đảm bảo dữ liệu không còn trong database.
    
    Args:
        device_id: ID của thiết bị cần xóa
        confirm: Xác nhận xóa mà không cần hỏi lại
        user_id: ID của người dùng yêu cầu xóa thiết bị (để kiểm tra quyền sở hữu)
        
    Returns:
        dict: Kết quả xóa thiết bị
    """
    try:
        # Kết nối database
        engine = create_engine(DATABASE_URL)
        deleted_counts = {}
        
        # Kiểm tra xem thiết bị có tồn tại không và các ràng buộc liên quan
        with engine.connect() as conn:
            # Kiểm tra thiết bị trong bảng devices
            has_devices_table = False
            device_exists = False
            device_id_in_db = None
            device_name = None
            device_owner_id = None
            
            # Thử kiểm tra bảng devices
            try:
                conn.execute(text("SELECT 1 FROM devices LIMIT 1"))
                has_devices_table = True
                
                if has_devices_table:
                    # Lấy thông tin chi tiết về thiết bị
                    device_info = conn.execute(
                        text("SELECT id, device_id, name, user_id FROM devices WHERE device_id = :device_id"),
                        {"device_id": device_id}
                    ).fetchone()
                    
                    if device_info:
                        device_exists = True
                        device_id_in_db = device_info[1]  # device_id
                        device_name = device_info[2]      # name
                        device_owner_id = device_info[3]  # user_id
                        logger.info(f"Tìm thấy thiết bị trong bảng devices: {device_id_in_db} (Name: {device_name}, Owner ID: {device_owner_id})")
                        
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
            
            if references:
                logger.info(f"Thiết bị {device_id} có tham chiếu trong các bảng: {references}")
            
            # Nếu không tìm thấy thiết bị trong bất kỳ bảng nào
            if not device_exists and not references:
                logger.warning(f"Không tìm thấy thiết bị với ID: {device_id} trong bất kỳ bảng nào")
                return {
                    "success": False,
                    "message": f"Không tìm thấy thiết bị với ID: {device_id}",
                    "device_id": device_id
                }
            
            # Hiển thị thông tin về dữ liệu sẽ bị xóa
            logger.info(f"Thông tin thiết bị {device_id}:")
            logger.info(f"- Tồn tại trong bảng devices: {device_exists} (ID: {device_id_in_db}, Name: {device_name}, Owner ID: {device_owner_id})")
            
            for table, count in references.items():
                logger.info(f"- Số bản ghi trong {table}: {count}")
            
            # Yêu cầu xác nhận nếu không có tham số --confirm
            if not confirm:
                confirmation = input(f"Bạn có chắc chắn muốn xóa thiết bị {device_id} và tất cả dữ liệu liên quan? (y/n): ")
                if confirmation.lower() != 'y':
                    logger.info("Đã hủy xóa thiết bị")
                    return {
                        "success": False,
                        "message": "Đã hủy xóa thiết bị",
                        "device_id": device_id
                    }
        
        # Xử lý xóa dữ liệu từng bảng riêng biệt một cách triệt để
        # Đầu tiên thử vô hiệu hóa ràng buộc khóa ngoại để dễ xóa
        try:
            with engine.connect() as conn:
                conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        except Exception as e:
            logger.warning(f"Không thể vô hiệu hóa ràng buộc khóa ngoại: {str(e)}")

        # Đầu tiên xóa dữ liệu từ các bảng con (bảng tham chiếu)
        for table, count in references.items():
            if count > 0:
                try:
                    with engine.connect() as conn:
                        trans = conn.begin()
                        try:
                            # Xóa dữ liệu từ bảng tham chiếu
                            result = conn.execute(
                                text(f"DELETE FROM {table} WHERE device_id = :device_id"),
                                {"device_id": device_id}
                            )
                            trans.commit()
                            deleted_counts[table] = count
                            logger.info(f"Đã xóa {count} bản ghi từ bảng {table}")
                        except Exception as table_e:
                            trans.rollback()
                            logger.error(f"Lỗi khi xóa dữ liệu từ bảng {table}: {str(table_e)}")
                            
                            # Thử phương pháp thay thế: cập nhật NULL trước, rồi xóa sau
                            try:
                                trans = conn.begin()
                                # Cập nhật NULL
                                conn.execute(
                                    text(f"UPDATE {table} SET device_id = NULL WHERE device_id = :device_id"),
                                    {"device_id": device_id}
                                )
                                trans.commit()
                                
                                # Sau đó thử xóa lại
                                trans = conn.begin()
                                result = conn.execute(
                                    text(f"DELETE FROM {table} WHERE device_id IS NULL"),
                                    {}
                                )
                                trans.commit()
                                deleted_counts[table] = count
                                logger.info(f"Đã xóa {count} bản ghi từ bảng {table} (phương pháp thay thế)")
                            except Exception as alt_e:
                                trans.rollback()
                                logger.error(f"Không thể xóa dữ liệu từ bảng {table} ngay cả với phương pháp thay thế: {str(alt_e)}")
                except Exception as e:
                    logger.error(f"Lỗi kết nối khi xóa từ bảng {table}: {str(e)}")
        
        # Cuối cùng xóa thiết bị từ bảng devices (nếu có)
        if has_devices_table and device_exists:
            try:
                with engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        # Xóa tất cả tham chiếu đến thiết bị này trong các bảng còn lại (nếu có)
                        try:
                            conn.execute(
                                text("""
                                    UPDATE sensor_data SET device_id = NULL WHERE device_id = :device_id;
                                    UPDATE original_samples SET device_id = NULL WHERE device_id = :device_id;
                                    UPDATE compressed_data_optimized SET device_id = NULL WHERE device_id = :device_id;
                                """),
                                {"device_id": device_id}
                            )
                            logger.info("Đã xóa tất cả tham chiếu đến thiết bị trong các bảng liên quan")
                        except Exception as fk_e:
                            logger.warning(f"Lỗi khi xóa tham chiếu: {str(fk_e)}")
                        
                        # Xóa trực tiếp thiết bị từ bảng devices
                        result = conn.execute(
                            text("DELETE FROM devices WHERE device_id = :device_id"),
                            {"device_id": device_id}
                        )
                        
                        if result.rowcount > 0:
                            deleted_counts["devices"] = result.rowcount
                            logger.info(f"Đã xóa thiết bị {device_id} từ bảng devices")
                        else:
                            logger.warning(f"Không tìm thấy thiết bị {device_id} trong bảng devices")
                            
                        trans.commit()
                    except Exception as dev_e:
                        trans.rollback()
                        logger.error(f"Lỗi khi xóa thiết bị từ bảng devices: {str(dev_e)}")
                        
                        # Thử phương pháp mạnh tay hơn
                        try:
                            # Thử sử dụng xóa trực tiếp với CASCADE
                            with engine.connect() as force_conn:
                                force_trans = force_conn.begin()
                                try:
                                    # Tắt kiểm tra ràng buộc tạm thời (PostgreSQL)
                                    force_conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
                                    
                                    # Xóa trực tiếp thiết bị
                                    force_result = force_conn.execute(
                                        text("DELETE FROM devices WHERE device_id = :device_id"),
                                        {"device_id": device_id}
                                    )
                                    
                                    if force_result.rowcount > 0:
                                        deleted_counts["devices"] = force_result.rowcount
                                        logger.info(f"Đã xóa thiết bị {device_id} từ bảng devices (phương pháp mạnh)")
                                    
                                    force_trans.commit()
                                except Exception as force_e:
                                    force_trans.rollback()
                                    logger.error(f"Không thể xóa thiết bị với phương pháp mạnh: {str(force_e)}")
                        except Exception as conn_e:
                            logger.error(f"Lỗi kết nối khi xóa thiết bị với phương pháp mạnh: {str(conn_e)}")
            except Exception as e:
                logger.error(f"Lỗi kết nối khi xóa thiết bị: {str(e)}")
        
        # Kiểm tra xem có thiết bị nào được xóa không
        if not deleted_counts:
            logger.warning(f"Không có dữ liệu nào được xóa cho thiết bị {device_id}")
            return {
                "success": False,
                "message": f"Không có dữ liệu nào được xóa cho thiết bị {device_id}",
                "device_id": device_id
            }
        
        logger.info(f"Đã xóa thành công thiết bị {device_id} và tất cả dữ liệu liên quan")
        
        return {
            "success": True,
            "message": f"Đã xóa thành công thiết bị {device_id} và tất cả dữ liệu liên quan",
            "device_id": device_id,
            "deleted_counts": deleted_counts
        }
    
    except Exception as e:
        logger.error(f"Lỗi khi xóa thiết bị: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi xóa thiết bị: {str(e)}",
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
