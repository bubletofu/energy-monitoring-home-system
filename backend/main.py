from fastapi import FastAPI, Depends, HTTPException, status, Query, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, date, timezone
from typing import Dict, List, Optional, Any
import models, auth
from pydantic import BaseModel, Field
import logging
from database import engine, get_db, init_db
import os
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import jwt
from config import settings
from fastapi.security import OAuth2PasswordBearer

# Hàm trợ giúp để làm việc với timezone
def get_current_utc_time():
    """
    Trả về thời gian hiện tại ở múi giờ UTC
    """
    return datetime.now(timezone.utc)

def ensure_timezone(timestamp):
    """
    Đảm bảo timestamp có timezone UTC, thêm nếu thiếu
    """
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp

def format_time_difference(minutes):
    """Format time difference in human-readable format (hours and minutes)"""
    if minutes < 60:
        return f"Thiết bị không hoạt động trong {int(minutes)} phút"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if mins == 0:
            return f"Thiết bị không hoạt động trong {hours} giờ"
        else:
            return f"Thiết bị không hoạt động trong {hours} giờ {mins} phút"

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import modules theo dõi thiết bị
try:
    from user_action.watching import start_watcher, stop_watcher
    has_device_watcher = True
    logger.info("Successfully imported device watcher module")
except ImportError:
    has_device_watcher = False
    logger.warning("Could not import device watcher module. Device status monitoring will be limited.")

# Thông tin kết nối database từ config
logger.info("Initializing database connection")

# Kiểm tra kết nối database
try:
    with engine.connect() as connection:
        logger.info("Successfully connected to database")
except Exception as e:
    logger.error(f"Failed to connect to database: {str(e)}")
    raise

# Tạo các bảng nếu chưa tồn tại
init_db()

app = FastAPI()

# Cập nhật import cho remove_device
try:
    from user_action.remove_device import remove_device as device_remover
    has_device_remover = True
    logger.info("Successfully imported device remover module")
except ImportError:
    has_device_remover = False
    logger.warning("Could not import device remover module. Device removal features will be limited.")

# Import add_device module
try:
    from user_action.add_device import add_device_for_user
    has_device_adder = True
    logger.info("Successfully imported device adder module")
except ImportError:
    has_device_adder = False
    logger.warning("Could not import device adder module. Device adding features will be limited.")

# Sự kiện khởi động ứng dụng
@app.on_event("startup")
async def startup_event():
    """
    Sự kiện khi ứng dụng bắt đầu khởi động
    - Chuẩn bị hệ thống
    """
    logger.info("Ứng dụng đang khởi động...")
    
    # Ngưỡng để xác định thiết bị offline (phút)
    OFFLINE_THRESHOLD = 10
    # Khoảng thời gian kiểm tra (phút)
    CHECK_INTERVAL = 5
    
    # Không khởi động dịch vụ theo dõi thiết bị ngay, chờ đến khi người dùng đăng nhập
    if has_device_watcher:
        logger.info(f"Dịch vụ theo dõi thiết bị sẵn sàng. Sẽ được kích hoạt khi người dùng đăng nhập. " +
                  f"(check_interval={CHECK_INTERVAL}, offline_threshold={OFFLINE_THRESHOLD})")
    else:
        logger.warning("Không thể khởi động dịch vụ theo dõi thiết bị")

# Sự kiện dừng ứng dụng
@app.on_event("shutdown")
async def shutdown_event():
    """
    Sự kiện khi ứng dụng đang dừng
    - Dừng dịch vụ theo dõi thiết bị
    """
    logger.info("Ứng dụng đang dừng...")
    
    # Dừng dịch vụ theo dõi thiết bị
    if has_device_watcher:
        try:
            logger.info("Dừng dịch vụ theo dõi thiết bị...")
            stop_watcher()
            logger.info("Dịch vụ theo dõi thiết bị đã được dừng")
        except Exception as e:
            logger.error(f"Lỗi khi dừng dịch vụ theo dõi thiết bị: {str(e)}")

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class DeviceClaim(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100, description="ID của thiết bị cần yêu cầu sở hữu")

class DeviceRename(BaseModel):
    old_device_id: str
    new_device_id: str

@app.post("/register/", response_model=dict)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        hashed_password = auth.get_password_hash(user.password)
        db_user = models.User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"message": "User created successfully"}
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login/", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Login attempt for username: {form_data.username}")
        
        # Tìm user trong database
        user = db.query(models.User).filter(models.User.username == form_data.username).first()
        logger.info(f"User found in database: {user is not None}")
        
        if not user:
            logger.error(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Kiểm tra password
        is_password_correct = auth.verify_password(form_data.password, user.hashed_password)
        logger.info("Password verification result: " + str(is_password_correct))
        
        if not is_password_correct:
            logger.error("Incorrect password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Tạo access token
        logger.info("Creating access token...")
        access_token_expires = timedelta(days=auth.ACCESS_TOKEN_EXPIRE_DAYS)
        access_token = auth.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        logger.info("Access token created successfully")
        
        # Chuyển sang theo dõi thiết bị của người dùng đã đăng nhập
        if has_device_watcher:
            try:
                # Ngưỡng để xác định thiết bị offline (phút)
                OFFLINE_THRESHOLD = 10
                # Khoảng thời gian kiểm tra (phút)
                CHECK_INTERVAL = 5
                
                logger.info(f"Chuyển sang theo dõi thiết bị của người dùng {user.username} (ID: {user.id})")
                
                # Nếu là admin (user_id=1), không cần chuyển đổi vì đã đang theo dõi tất cả thiết bị
                if user.id != 1:
                    # Khởi động watcher mới chỉ theo dõi thiết bị của người dùng này
                    from user_action.watching import start_watcher
                    start_watcher(
                        check_interval=CHECK_INTERVAL, 
                        offline_threshold=OFFLINE_THRESHOLD, 
                        user_id=user.id
                    )
                    logger.info(f"Đã chuyển sang theo dõi thiết bị của người dùng {user.username} " +
                                f"(check_interval={CHECK_INTERVAL}, offline_threshold={OFFLINE_THRESHOLD})")
                else:
                    logger.info(f"Đã đăng nhập với tài khoản admin, tiếp tục theo dõi tất cả thiết bị")
                
            except Exception as e:
                logger.error(f"Lỗi khi chuyển sang theo dõi thiết bị của người dùng {user.username}: {str(e)}")
                # Không raise exception ở đây vì đăng nhập vẫn thành công dù không chuyển được chế độ theo dõi
        
        # Thiết lập cookie trong response
        auth.set_auth_cookie(response, access_token)
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException as http_ex:
        logger.error(f"HTTP Exception in login: {str(http_ex)}")
        raise http_ex
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}")
        logger.exception("Full error traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"Login error: {str(e)}"
        )

@app.post("/logout/")
def logout(response: Response):
    """
    Đăng xuất người dùng hiện tại bằng cách xóa cookie.
    """
    auth.clear_auth_cookie(response)
    return {"message": "Đăng xuất thành công"}

@app.get("/check-auth/")
async def check_auth(request: Request, db: Session = Depends(get_db)):
    """
    Kiểm tra xem người dùng đã đăng nhập hay chưa không yêu cầu xác thực.
    """
    # Lấy token từ cookie nếu có
    token = request.cookies.get(auth.COOKIE_NAME)
    if not token:
        # Không có cookie, người dùng chưa đăng nhập
        return {
            "is_authenticated": False,
            "user": None
        }
    
    try:
        # Giải mã token và lấy thông tin người dùng
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            return {"is_authenticated": False, "user": None}
        
        # Tìm người dùng trong database
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            return {"is_authenticated": False, "user": None}
        
        # Trả về thông tin người dùng
        return {
            "is_authenticated": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
    except Exception as e:
        logger.error(f"Error checking authentication: {str(e)}")
        return {"is_authenticated": False, "user": None}

@app.get("/auth/me/", response_model=Dict)
def get_current_user_info(current_user: models.User = Depends(auth.get_current_user)):
    """
    Trả về thông tin của người dùng hiện tại đã đăng nhập.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_authenticated": True
    }

@app.get("/")
def read_root():
    return {
        "message": "IoT Backend API - Authentication Service",
        "features": [
            "User authentication (login/register)",
            "View devices and data",
            "Claim ownership of devices",
            "Delete devices"
        ],
        "note": "Người dùng chỉ có thể xem dữ liệu và thực hiện các thao tác với thiết bị. Việc tạo thiết bị mới và gửi dữ liệu mẫu từ thiết bị không được hỗ trợ qua API này."
    }

@app.get("/fetch-data/", response_model=List[Dict])
def fetch_data(
    target_date: Optional[str] = Query(None, description="Ngày cần lấy dữ liệu (định dạng YYYY-MM-DD, mặc định: hôm nay)"),
    device_id: Optional[str] = Query(None, description="ID của thiết bị cần lấy dữ liệu (để trống để lấy tất cả)"),
    limit: int = Query(50, ge=1, le=1000, description="Số lượng bản ghi tối đa cần lấy"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Lấy dữ liệu từ bảng sensor_data cho một ngày cụ thể.
    Tương đương với việc chạy lệnh fetch.py --date <ngày tháng cụ thể>
    
    Args:
        target_date: Ngày cần lấy dữ liệu (định dạng YYYY-MM-DD, mặc định: hôm nay)
        device_id: ID của thiết bị cần lấy dữ liệu (để trống để lấy tất cả)
        limit: Số lượng bản ghi tối đa cần lấy
    """
    try:
        # Xử lý tham số ngày
        parsed_date = None
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Định dạng ngày không hợp lệ: {target_date}. Vui lòng sử dụng định dạng YYYY-MM-DD."
                )
        else:
            parsed_date = get_current_utc_time().date()
        
        logger.info(f"Đang lấy dữ liệu cho ngày: {parsed_date}")
        
        # Tạo thời gian bắt đầu và kết thúc cho ngày đã chọn
        start_time = datetime.combine(parsed_date, datetime.min.time())
        end_time = datetime.combine(parsed_date, datetime.max.time())
        
        # Chuẩn bị truy vấn SQL
        query = """
        SELECT id, device_id, feed_id, value, timestamp, raw_data
        FROM sensor_data
        WHERE timestamp BETWEEN :start_time AND :end_time
        """
        
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        # Thêm điều kiện device_id nếu có
        if device_id:
            query += " AND device_id = :device_id"
            params["device_id"] = device_id
            
        # Thêm limit và sắp xếp
        query += " ORDER BY timestamp DESC LIMIT :limit"
        params["limit"] = limit
        
        # Thực hiện truy vấn
        result = []
        with engine.connect() as conn:
            rows = conn.execute(text(query), params)
            for row in rows:
                # Chuyển đổi raw_data từ JSON string sang dict nếu có
                raw_data = None
                if row[5]:  # raw_data
                    try:
                        import json
                        raw_data = json.loads(row[5])
                    except:
                        raw_data = row[5]
                
                # Tạo dict cho mỗi bản ghi
                record = {
                    "id": row[0],
                    "device_id": row[1],
                    "feed_id": row[2],
                    "value": row[3],
                    "timestamp": row[4].isoformat() if row[4] else None,
                    "raw_data": raw_data
                }
                result.append(record)
        
        logger.info(f"Đã lấy {len(result)} bản ghi cho ngày {parsed_date}")
        
        return result
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi server: {str(e)}"
        )

@app.get("/fetch-devices/", response_model=List[Dict])
def fetch_devices(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Lấy danh sách các thiết bị có trong bảng sensor_data
    """
    try:
        # Truy vấn để lấy danh sách các device_id duy nhất
        query = """
        SELECT DISTINCT device_id, 
               COUNT(*) as record_count, 
               MIN(timestamp) as first_record, 
               MAX(timestamp) as last_record
        FROM sensor_data
        GROUP BY device_id
        ORDER BY device_id
        """
        
        # Thực hiện truy vấn
        result = []
        with engine.connect() as conn:
            rows = conn.execute(text(query))
            for row in rows:
                device = {
                    "device_id": row[0],
                    "record_count": row[1],
                    "first_record": row[2].isoformat() if row[2] else None,
                    "last_record": row[3].isoformat() if row[3] else None
                }
                result.append(device)
        
        logger.info(f"Đã lấy danh sách {len(result)} thiết bị từ bảng sensor_data")
        
        return result
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách thiết bị: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi server: {str(e)}"
        )

@app.delete("/devices/{device_id}", tags=["devices"])
async def delete_device(
    device_id: str,
    confirm: bool = Query(False, description="Xác nhận xóa mà không cần hỏi lại"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Xóa thiết bị và tất cả dữ liệu liên quan.
    
    - Yêu cầu xác thực người dùng
    - Chỉ người dùng sở hữu thiết bị hoặc admin mới có quyền xóa
    - Tham số `confirm=True` để xác nhận xóa mà không cần hỏi lại
    """
    # Kiểm tra quyền hạn - admin hoặc chủ sở hữu thiết bị mới được xóa
    is_admin = current_user.id == 1
    
    # Kiểm tra thiết bị tồn tại và thuộc về người dùng
    try:
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy thiết bị: {device_id}")
        
        # Kiểm tra quyền sở hữu
        if not is_admin and device.user_id != current_user.id:
            raise HTTPException(
                status_code=403, 
                detail=f"Bạn không có quyền xóa thiết bị này. Thiết bị thuộc về người dùng khác."
            )
        
        # Thử dùng module device_remover nếu có
        try:
            from user_action.remove_device import remove_device as device_remover
            
            # Ghi log hành động xóa thiết bị
            logger.info(f"Người dùng {current_user.username} (ID: {current_user.id}) đang xóa thiết bị {device_id}")
            
            # Thực hiện xóa thiết bị
            result = device_remover(device_id, confirm, current_user.id)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return {
                "status": "success",
                "message": f"Đã xóa thiết bị {device_id} thành công",
                "details": result.get("deleted_counts", {})
            }
        
        except ImportError:
            # Nếu không có module remove_device, thì dùng cách xóa cũ
            logger.warning("Không tìm thấy module remove_device, sử dụng cách xóa cũ")
            
            if not confirm:
                return {
                    "status": "error",
                    "message": "Chưa xác nhận xóa thiết bị. Vui lòng gửi lại với tham số confirm=True"
                }
            
            # Xóa dữ liệu từ các bảng liên quan
            deleted_data = {}
            
            # Xóa dữ liệu sensor_data
            sensor_data_count = db.query(models.SensorData).filter(models.SensorData.device_id == device_id).count()
            if sensor_data_count > 0:
                db.query(models.SensorData).filter(models.SensorData.device_id == device_id).delete()
                deleted_data["sensor_data"] = sensor_data_count
            
            # Xóa dữ liệu original_samples nếu bảng tồn tại
            try:
                original_samples_count = db.execute(
                    text("SELECT COUNT(*) FROM original_samples WHERE device_id = :device_id"),
                    {"device_id": device_id}
                ).scalar()
                
                if original_samples_count and original_samples_count > 0:
                    db.execute(
                        text("DELETE FROM original_samples WHERE device_id = :device_id"),
                        {"device_id": device_id}
                    )
                    deleted_data["original_samples"] = original_samples_count
            except Exception as e:
                logger.warning(f"Không thể xóa dữ liệu từ original_samples: {str(e)}")
            
            # Xóa dữ liệu compressed_data_optimized nếu bảng tồn tại
            try:
                compressed_count = db.execute(
                    text("SELECT COUNT(*) FROM compressed_data_optimized WHERE device_id = :device_id"),
                    {"device_id": device_id}
                ).scalar()
                
                if compressed_count and compressed_count > 0:
                    db.execute(
                        text("DELETE FROM compressed_data_optimized WHERE device_id = :device_id"),
                        {"device_id": device_id}
                    )
                    deleted_data["compressed_data_optimized"] = compressed_count
            except Exception as e:
                logger.warning(f"Không thể xóa dữ liệu từ compressed_data_optimized: {str(e)}")
            
            # Xóa thiết bị từ bảng devices
            db.delete(device)
            deleted_data["devices"] = 1
            
            # Commit các thay đổi vào database
            db.commit()
            
            return {
                "status": "success", 
                "message": f"Đã xóa thiết bị {device_id} thành công",
                "details": deleted_data
            }
            
    except HTTPException as http_e:
        # Re-raise HTTP exceptions
        raise http_e
    except Exception as e:
        logger.error(f"Lỗi khi xóa thiết bị {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa thiết bị: {str(e)}")

@app.post("/claim-device/", response_model=Dict[str, Any])
def claim_device(
    device: DeviceClaim,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Yêu cầu sở hữu một thiết bị đã tồn tại.
    Chỉ hoạt động cho các thiết bị chưa có chủ (user_id là NULL) hoặc thuộc tài khoản mặc định (user_id = 1)
    
    Args:
        device_id: ID của thiết bị cần yêu cầu sở hữu
    """
    device_claimed = False  # Biến để theo dõi xem có claim thiết bị mới không
    
    try:
        if has_device_adder:
            # Sử dụng module add_device nếu có
            result = add_device_for_user(device.device_id, current_user.id, None)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=result["message"]
                )
                
            logger.info(f"Người dùng {current_user.username} đã yêu cầu sở hữu thiết bị {device.device_id}")
            device_claimed = True  # Đánh dấu đã claim thiết bị mới
            
            # Kích hoạt lại theo dõi thiết bị sau khi claim
            if device_claimed and has_device_watcher:
                try:
                    logger.info(f"Kích hoạt lại theo dõi thiết bị sau khi claim thiết bị {device.device_id}")
                    from user_action.watching import start_watcher
                    start_watcher(check_interval=5, offline_threshold=10, user_id=current_user.id)
                except Exception as e:
                    logger.error(f"Lỗi khi kích hoạt lại theo dõi thiết bị: {str(e)}")
                    # Không cần raise exception vì việc claim thiết bị vẫn thành công
            
            return result
        else:
            # Xử lý thủ công nếu không có module add_device
            existing_device = db.query(models.Device).filter(models.Device.device_id == device.device_id).first()
            
            if not existing_device:
                raise HTTPException(
                    status_code=404,
                    detail=f"Không tìm thấy thiết bị với ID: {device.device_id}. Thiết bị phải tồn tại trước khi được gán cho người dùng."
                )
            
            # Kiểm tra xem thiết bị đã có chủ chưa
            if existing_device.user_id is not None and existing_device.user_id != 1 and existing_device.user_id != current_user.id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Thiết bị {device.device_id} đã thuộc về người dùng khác"
                )
            
            # Cập nhật thiết bị cho người dùng hiện tại
            if existing_device.user_id is None or existing_device.user_id == 1:
                # Cập nhật thông tin thiết bị
                existing_device.user_id = current_user.id
                
                db.commit()
                device_claimed = True  # Đánh dấu đã claim thiết bị mới
                
                logger.info(f"Người dùng {current_user.username} đã yêu cầu sở hữu thiết bị {device.device_id}")
                
                # Kích hoạt lại theo dõi thiết bị sau khi claim
                if device_claimed and has_device_watcher:
                    try:
                        logger.info(f"Kích hoạt lại theo dõi thiết bị sau khi claim thiết bị {device.device_id}")
                        from user_action.watching import start_watcher
                        start_watcher(check_interval=5, offline_threshold=10, user_id=current_user.id)
                    except Exception as e:
                        logger.error(f"Lỗi khi kích hoạt lại theo dõi thiết bị: {str(e)}")
                        # Không cần raise exception vì việc claim thiết bị vẫn thành công
                
                return {
                    "success": True,
                    "message": f"Đã cập nhật thiết bị {device.device_id} cho tài khoản của bạn",
                    "device_id": device.device_id,
                    "user_id": current_user.id
                }
            
            # Nếu thiết bị đã thuộc về người dùng này
            if existing_device.user_id == current_user.id:
                # Cập nhật tên nếu có thay đổi
                if device.name and device.name != existing_device.name:
                    existing_device.name = device.name
                    db.commit()
                    
                return {
                    "success": True,
                    "message": f"Thiết bị {device.device_id} đã thuộc về tài khoản của bạn",
                    "device_id": device.device_id,
                    "user_id": current_user.id
                }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Lỗi khi yêu cầu sở hữu thiết bị: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi server: {str(e)}"
        )

@app.get("/device-status/", response_model=List[Dict])
def get_device_status(
    device_id: Optional[str] = Query(None, description="ID của thiết bị cần kiểm tra (để trống để lấy tất cả)"),
    refresh: bool = Query(False, description="Cập nhật lại trạng thái thiết bị trước khi trả về kết quả"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Lấy trạng thái thiết bị (online/offline)
    
    Args:
        device_id: ID của thiết bị cần kiểm tra (để trống để lấy tất cả)
        refresh: Cập nhật lại trạng thái thiết bị trước khi trả về kết quả
    """
    # Ngưỡng để xác định thiết bị offline (phút)
    OFFLINE_THRESHOLD = 10
    
    try:
        # Nếu yêu cầu refresh, cập nhật trạng thái thiết bị trước
        if refresh and has_device_watcher:
            try:
                # Chỉ cập nhật thiết bị của người dùng hiện tại (hoặc tất cả nếu là admin)
                user_id = None if current_user.id == 1 else current_user.id
                
                # Import DeviceWatcher từ watching.py
                from user_action.watching import DeviceWatcher
                
                # Tạo một DeviceWatcher instance với user_id phù hợp và ngưỡng offline chuẩn
                watcher = DeviceWatcher(user_id=user_id, offline_threshold=OFFLINE_THRESHOLD)
                
                # Nếu device_id được cung cấp và thuộc về người dùng, chỉ cập nhật thiết bị đó
                if device_id:
                    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
                    if device and (current_user.id == 1 or device.user_id == current_user.id):
                        watcher.check_specific_device(device_id)
                        logger.info(f"Đã cập nhật trạng thái thiết bị {device_id} theo yêu cầu refresh")
                    else:
                        logger.warning(f"Không tìm thấy thiết bị {device_id} hoặc không có quyền truy cập")
                else:
                    # Cập nhật tất cả thiết bị của người dùng
                    watcher.check_all_devices()
                    logger.info(f"Đã cập nhật trạng thái thiết bị cho người dùng {current_user.username}")
            except Exception as e:
                logger.error(f"Lỗi khi refresh trạng thái thiết bị: {str(e)}")
        
        # Lấy trạng thái thiết bị từ database
        query = """
        SELECT d.id, d.device_id, d.name, d.is_online, d.last_value, d.last_updated, 
               d.status_details, d.user_id
        FROM devices d
        """
        
        params = {}
        
        # Thêm điều kiện nếu device_id được cung cấp
        if device_id:
            query += " WHERE d.device_id = :device_id"
            params["device_id"] = device_id
        
        # Nếu không phải admin (user_id = 1), chỉ lấy thiết bị của người dùng hiện tại
        if current_user.id != 1:
            if device_id:
                query += " AND d.user_id = :user_id"
            else:
                query += " WHERE d.user_id = :user_id"
            params["user_id"] = current_user.id
        
        # Thực hiện truy vấn
        result = []
        rows = db.execute(text(query), params)
        
        # Lấy thời gian hiện tại một lần cho tất cả thiết bị để đảm bảo tính nhất quán
        current_time = get_current_utc_time()
        logger.debug(f"Thời gian hiện tại khi lấy trạng thái thiết bị: {current_time.isoformat()}")
        
        for row in rows:
            # Parse status_details từ JSONB thành dict
            status_details = {}
            if row[6]:  # status_details
                try:
                    import json
                    status_details = json.loads(row[6])
                except:
                    status_details = {}
            
            # Tính thời gian offline nếu thiết bị không online
            is_online = row[3] or False
            last_updated = row[5]
            offline_info = {}
            
            if not is_online and last_updated:
                try:
                    # Use the DeviceWatcher class for all time calculations
                    if has_device_watcher:
                        from user_action.watching import DeviceWatcher
                        # Create watcher with the standard OFFLINE_THRESHOLD
                        watcher = DeviceWatcher(offline_threshold=OFFLINE_THRESHOLD)
                        # Check this specific device
                        status = watcher.check_device_status(row[1])
                        if status:
                            # Use the status details from the watcher which already has all calculated fields
                            offline_info = status["status_details"]
                            # Update the online status based on fresh calculations
                            is_online = status["is_online"]
                            
                            # Log that we used the watcher for this device
                            logger.debug(f"Using DeviceWatcher for status calculation of device {row[1]}")
                            
                            # Update the DB if needed and if the status has changed
                            if is_online and refresh:
                                try:
                                    db.execute(
                                        text("UPDATE devices SET is_online = TRUE WHERE device_id = :device_id"),
                                        {"device_id": row[1]}
                                    )
                                    db.commit()
                                    logger.info(f"Đã cập nhật trạng thái thiết bị {row[1]} thành ONLINE")
                                except Exception as e:
                                    logger.error(f"Lỗi khi cập nhật trạng thái thiết bị: {str(e)}")
                    else:
                        # Fallback only if the watcher module is not available
                        logger.warning(f"DeviceWatcher module not available, using fallback calculation for device {row[1]}")
                        # Ensure timestamp has timezone
                        last_updated = ensure_timezone(last_updated)
                        
                        # Simplest calculation: Just get direct time difference without worrying about timezones
                        current_time_naive = datetime.now()
                        last_time_naive = last_updated.replace(tzinfo=None)  # Remove timezone info
                        
                        # Calculate direct time difference
                        time_diff_delta = current_time_naive - last_time_naive
                        time_diff_seconds = time_diff_delta.total_seconds()
                        time_diff_minutes = time_diff_seconds / 60
                        
                        logger.debug(f"TIMESTAMP SIMPLE CHECK: Current={current_time_naive}, Last={last_time_naive}, Diff={time_diff_seconds}s = {time_diff_minutes}m")
                        
                        # Check if device is online based on threshold
                        is_online = time_diff_minutes <= OFFLINE_THRESHOLD
                        
                        if not is_online:
                            # Format time for logging only
                            if time_diff_minutes >= 60:
                                hours = int(time_diff_minutes // 60)
                                minutes = int(time_diff_minutes % 60)
                                formatted_time = f"{hours} giờ {minutes} phút"
                            else:
                                formatted_time = f"{int(time_diff_minutes)} phút"
                            
                            logger.debug(f"Thiết bị {row[1]} offline trong {formatted_time}")
                            
                            # Create offline info with consistent time handling
                            offline_info = {
                                "data_source": "sensor_data",
                                "last_data_time": last_time_naive.isoformat(),  # Use naive time directly
                                "current_time": datetime.now().isoformat(),
                                "message": format_time_difference(time_diff_minutes)
                            }
                            
                            logger.debug(f"[API] OFFLINE CALCULATION - Device: {row[1]}, " +
                                      f"Current: {current_time.isoformat()}, " +
                                      f"Last Updated: {last_updated.isoformat()}, " +
                                      f"Diff: {round(time_diff_minutes, 2)} phút")
                        else:
                            logger.info(f"Thiết bị {row[1]} được đánh dấu là offline trong DB nhưng thực tế đang online " +
                                      f"(chênh lệch: {round(time_diff_minutes, 2)} phút, ngưỡng: {OFFLINE_THRESHOLD} phút)")
                            
                            # Update DB if needed
                            if refresh:
                                try:
                                    db.execute(
                                        text("UPDATE devices SET is_online = TRUE WHERE device_id = :device_id"),
                                        {"device_id": row[1]}
                                    )
                                    db.commit()
                                    logger.info(f"Đã cập nhật trạng thái thiết bị {row[1]} thành ONLINE")
                                except Exception as e:
                                    logger.error(f"Lỗi khi cập nhật trạng thái thiết bị: {str(e)}")
                except Exception as e:
                    logger.error(f"Lỗi khi tính thời gian offline: {str(e)}")
            
            # Bổ sung thông tin offline vào status_details
            if offline_info:
                status_details.update(offline_info)
            
            # Tạo đối tượng trạng thái thiết bị
            device_status = {
                "id": row[0],
                "device_id": row[1],
                "name": row[2],
                "is_online": is_online,  # Sử dụng trạng thái đã được tính toán lại
                "last_value": row[4],
                "status_details": status_details,
                "user_id": row[7]
            }
            result.append(device_status)
        
        logger.info(f"Đã lấy trạng thái của {len(result)} thiết bị")
        return result
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái thiết bị: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi server: {str(e)}"
        ) 

@app.post("/devices/rename/", response_model=dict)
def rename_device(
    device_rename: DeviceRename,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Đổi tên device_id của người dùng.
    Chỉ cho phép đổi tên nếu người dùng sở hữu thiết bị đó.
    """
    try:
        # Kiểm tra quyền sở hữu thiết bị
        device = db.query(models.Device).filter(
            models.Device.device_id == device_rename.old_device_id,
            models.Device.user_id == current_user.id
        ).first()
        
        if not device:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền đổi tên thiết bị này"
            )
        
        # Kiểm tra device_id mới chưa tồn tại
        existing_device = db.query(models.Device).filter(
            models.Device.device_id == device_rename.new_device_id
        ).first()
        
        if existing_device:
            raise HTTPException(
                status_code=400,
                detail="Device_id mới đã tồn tại"
            )
        
        # Gọi hàm rename_device từ user_device.py
        from user_action.user_device import rename_device
        rename_device(
            device_rename.old_device_id,
            device_rename.new_device_id,
            current_user.id
        )
        
        return {
            "message": f"Đã đổi tên device_id từ '{device_rename.old_device_id}' thành '{device_rename.new_device_id}' thành công"
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi đổi tên device_id: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 

@app.get("/sensor-data/{device_id}")
async def get_sensor_data(device_id: str):
    """
    Lấy dữ liệu cảm biến của một thiết bị
    """
    try:
        with engine.connect() as conn:
            # Lấy dữ liệu từ bảng sensor_data
            result = conn.execute(
                text("""
                    SELECT id, device_id, feed_id, value, timestamp
                    FROM sensor_data
                    WHERE device_id = :device_id
                    ORDER BY timestamp DESC
                    LIMIT 100
                """),
                {"device_id": device_id}
            )
            
            data = []
            for row in result:
                data.append({
                    "id": row[0],
                    "device_id": row[1],
                    "feed_id": row[2],
                    "value": row[3],
                    "timestamp": row[4]
                })
            
            return {"status": "success", "data": data}
            
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu cảm biến: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 