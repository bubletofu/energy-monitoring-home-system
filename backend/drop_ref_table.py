#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để xóa bảng ref khỏi cơ sở dữ liệu.
Bảng này không còn được sử dụng trong hệ thống nén dữ liệu mới.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("drop_table.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Kết nối database từ biến môi trường hoặc giá trị mặc định
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")

def drop_ref_table():
    """
    Xóa bảng ref khỏi cơ sở dữ liệu nếu nó tồn tại.
    
    Returns:
        bool: True nếu xóa thành công, False nếu có lỗi
    """
    try:
        # Tạo engine kết nối đến database
        engine = create_engine(DATABASE_URL)
        
        # Kiểm tra xem bảng có tồn tại không
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            
            if 'ref' not in tables:
                logger.info("Bảng ref không tồn tại trong cơ sở dữ liệu.")
                return True
            
            # Xóa các khóa ngoại trước khi xóa bảng
            # (Có thể cần điều chỉnh dựa trên cấu trúc cụ thể của cơ sở dữ liệu)
            try:
                conn.execute(text("""
                    DO $$
                    BEGIN
                        -- Disable constraint trước khi xóa
                        ALTER TABLE ref DROP CONSTRAINT IF EXISTS ref_compression_id_fkey;
                        
                        -- Đề phòng trường hợp tên constraint khác
                        ALTER TABLE ref DROP CONSTRAINT IF EXISTS ref_device_id_fkey;
                    EXCEPTION WHEN OTHERS THEN
                        -- Bỏ qua lỗi nếu constraint không tồn tại
                        NULL;
                    END $$;
                """))
                conn.commit()
                logger.info("Đã vô hiệu hóa các khóa ngoại của bảng ref")
            except Exception as e:
                logger.warning(f"Lỗi khi vô hiệu hóa khóa ngoại: {str(e)}")
                # Tiếp tục thực hiện xóa bảng ngay cả khi có lỗi vô hiệu hóa khóa ngoại
            
            # Xóa bảng ref
            conn.execute(text("DROP TABLE IF EXISTS ref CASCADE"))
            conn.commit()
            logger.info("Đã xóa bảng ref thành công")
            
            # Kiểm tra lại để đảm bảo bảng đã được xóa
            tables_after = inspector.get_table_names()
            if 'ref' not in tables_after:
                logger.info("Xác nhận: Bảng ref đã bị xóa khỏi cơ sở dữ liệu")
                return True
            else:
                logger.error("Bảng ref vẫn còn tồn tại sau khi cố gắng xóa")
                return False
            
    except Exception as e:
        logger.error(f"Lỗi khi xóa bảng ref: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """
    Hàm chính để thực thi script
    """
    logger.info("=== BẮT ĐẦU XÓA BẢNG REF ===")
    
    # Yêu cầu xác nhận từ người dùng
    print("\nCHÚ Ý: Bạn đang chuẩn bị XÓA bảng 'ref' khỏi cơ sở dữ liệu.")
    print("Hành động này KHÔNG THỂ HOÀN TÁC và sẽ xóa vĩnh viễn dữ liệu.")
    print(f"Cơ sở dữ liệu mục tiêu: {DATABASE_URL}\n")
    
    confirmation = input("Nhập 'XÓA' để xác nhận xóa bảng ref: ")
    
    if confirmation.strip() != 'XÓA':
        logger.info("Đã hủy thao tác xóa bảng")
        print("Đã hủy thao tác xóa bảng.")
        return
    
    # Thực hiện xóa bảng
    success = drop_ref_table()
    
    if success:
        print("\nĐã xóa bảng ref thành công.")
        logger.info("=== KẾT THÚC XÓA BẢNG REF: THÀNH CÔNG ===")
    else:
        print("\nKhông thể xóa bảng ref. Vui lòng kiểm tra file log để biết thêm chi tiết.")
        logger.info("=== KẾT THÚC XÓA BẢNG REF: THẤT BẠI ===")

if __name__ == "__main__":
    main() 