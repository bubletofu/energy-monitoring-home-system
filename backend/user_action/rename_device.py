def rename_device(old_device_id: str, new_device_id: str, user_id: int) -> bool:
    """
    Đổi tên device_id của người dùng.
    Chỉ cho phép đổi tên nếu người dùng sở hữu thiết bị đó.
    
    Args:
        old_device_id: ID cũ của thiết bị
        new_device_id: ID mới của thiết bị
        user_id: ID của người dùng
        
    Returns:
        bool: True nếu đổi tên thành công, False nếu thất bại
    """
    try:
        # Kết nối database
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Kiểm tra quyền sở hữu thiết bị
            device = conn.execute(
                text("SELECT id FROM devices WHERE device_id = :device_id AND user_id = :user_id"),
                {"device_id": old_device_id, "user_id": user_id}
            ).fetchone()
            
            if not device:
                logger.error(f"Thiết bị {old_device_id} không tồn tại hoặc không thuộc về người dùng {user_id}")
                return False
            
            # Kiểm tra device_id mới chưa tồn tại
            existing_device = conn.execute(
                text("SELECT id FROM devices WHERE device_id = :device_id"),
                {"device_id": new_device_id}
            ).fetchone()
            
            if existing_device:
                logger.error(f"Device_id {new_device_id} đã tồn tại")
                return False
            
            # Bắt đầu transaction
            transaction = conn.begin()
            try:
                # Cập nhật device_id trong bảng devices
                # Các bảng khác sẽ tự động cập nhật nhờ ON UPDATE CASCADE
                conn.execute(
                    text("UPDATE devices SET device_id = :new_id WHERE device_id = :old_id"),
                    {"new_id": new_device_id, "old_id": old_device_id}
                )
                
                # Commit transaction
                transaction.commit()
                logger.info(f"Đã đổi tên thiết bị từ {old_device_id} thành {new_device_id}")
                return True
                
            except Exception as e:
                transaction.rollback()
                logger.error(f"Lỗi khi đổi tên thiết bị: {str(e)}")
                return False
                
    except Exception as e:
        logger.error(f"Lỗi khi kết nối database: {str(e)}")
        return False 