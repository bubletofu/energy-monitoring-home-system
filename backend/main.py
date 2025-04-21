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
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter

# Import các module từ user_action
from user_action.user_device import rename_device
from user_action.add_device import add_device_for_user
from user_action.remove_device import remove_device
from user_action.turn_device import turn_device

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # Frontend trên localhost
        "http://127.0.0.1:3000",       # Frontend trên IP loopback
        "http://27.75.228.222:3000",   # Frontend nếu truy cập qua IP của bạn
        # Thêm origin của các dev khác nếu cần
        # Ví dụ: "http://192.168.1.5:3000", "http://dev-workstation:3000", etc.
    ],
    allow_credentials=True,  # Quan trọng để cookies hoạt động
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

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

# Sự kiện dừng ứng dụng
@app.on_event("shutdown")
async def shutdown_event():
    """
    Sự kiện khi ứng dụng đang dừng
    """
    logger.info("Ứng dụng đang dừng...")

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

class DeviceTurnRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100, description="ID của thiết bị cần bật/tắt")
    value: int = Field(..., ge=0, le=1, description="Giá trị 0 (tắt) hoặc 1 (bật)")

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

@app.post("/login/")
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
        
        # Thêm log để debug
        logger.info(f"Access token created: {access_token[:10]}...")
        
        # Sửa lại đặt cookie
        auth.set_auth_cookie(response, access_token)
        
        # Thêm log để kiểm tra
        logger.info(f"Cookie auth_token đã được đặt. max_age={access_token_expires.total_seconds()}")
        
        # Trả về thông tin người dùng thay vì token
        return {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
        
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
def logout(
    response: Response,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Đăng xuất người dùng hiện tại bằng cách xóa cookie.
    """
    try:
        # Bạn có thể thêm xử lý đăng xuất khác ở đây nếu cần
        pass  # Thêm pass để tránh khối try trống
    except Exception as e:
        logger.error(f"Lỗi khi đăng xuất: {str(e)}")
    finally:
        # Xóa cookie bất kể có lỗi hay không
        auth.clear_auth_cookie(response)
        return {"message": "Đăng xuất thành công"}

@app.get("/check-auth/")
async def check_auth(request: Request, db: Session = Depends(get_db)):
    """
    Kiểm tra xem người dùng đã đăng nhập hay chưa không yêu cầu xác thực.
    """
    # Debug headers và cookies
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request cookies: {request.cookies}")
    
    # Thử lấy token từ cả cookie và header
    token = None
    
    # 1. Lấy từ cookie
    if auth.COOKIE_NAME in request.cookies:
        token = request.cookies.get(auth.COOKIE_NAME)
        logger.info(f"Found token in cookie: {token[:20] if token else None}...")
    
    # 2. Lấy từ header Authorization nếu không có trong cookie
    if not token:
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            logger.info(f"Found token in Authorization header: {token[:20] if token else None}...")
    
    if not token:
        logger.warning("No auth token found in cookies or headers")
        return {
            "is_authenticated": False,
            "user": None
        }
    
    try:
        # Giải mã token và lấy thông tin người dùng
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        
        if not username:
            logger.warning("Username not found in token payload")
            return {"is_authenticated": False, "user": None}
        
        logger.info(f"Username from token: {username}")
        
        # Tìm người dùng trong database
        user = db.query(models.User).filter(models.User.username == username).first()
        
        if not user:
            logger.warning(f"User not found in database: {username}")
            return {"is_authenticated": False, "user": None}
        
        # Trả về thông tin người dùng
        logger.info(f"User authenticated: {user.username}")
        return {
            "is_authenticated": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        return {"is_authenticated": False, "user": None, "error": "token_expired"}
    except jwt.InvalidTokenError:
        logger.error("Invalid token")
        return {"is_authenticated": False, "user": None, "error": "invalid_token"}
    except Exception as e:
        logger.error(f"Error checking authentication: {str(e)}")
        return {"is_authenticated": False, "user": None, "error": str(e)}

@app.get("/auth/me/", response_model=Dict)
def get_current_user_info(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Trả về thông tin của người dùng hiện tại đã đăng nhập.
    """
    logger.info(f"Auth/me request headers: {dict(request.headers)}")
    
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
            "Claim ownership of devices",
            "Rename devices",
            "Remove device ownership",
            "Turn devices on/off"
        ],
        "note": "Người dùng chỉ có thể thực hiện các thao tác quản lý thiết bị. Việc theo dõi trạng thái thiết bị, tạo thiết bị mới và gửi dữ liệu mẫu từ thiết bị không được hỗ trợ qua API này."
    }

@app.post("/devices/rename/", response_model=dict)
def rename_device_endpoint(
    device_rename: DeviceRename,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Đổi tên device_id của người dùng.
    Chỉ cho phép đổi tên nếu người dùng sở hữu thiết bị đó.
    """
    try:
        result = rename_device(device_rename.old_device_id, device_rename.new_device_id, current_user.id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
        return {
            "message": result["message"]
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi đổi tên device_id: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/api/devices/claim/{device_id}")
def claim_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """API để người dùng claim thiết bị"""
    # Kiểm tra xem thiết bị có tồn tại không
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
    
    # Kiểm tra xem thiết bị đã được gán cho người dùng khác chưa
    if device.user_id is not None and device.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Thiết bị đã thuộc về người dùng khác")
    
    # Gán thiết bị cho người dùng hiện tại
    device.user_id = current_user.id
    db.commit()
    
    return {"message": f"Đã gán thiết bị {device_id} cho người dùng {current_user.username}"}

@app.post("/devices/remove/", response_model=dict)
def remove_device(
    device_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Từ bỏ quyền sở hữu một thiết bị.
    """
    try:
        # Gọi hàm remove_device từ user_device.py
        from user_action.user_device import remove_device
        remove_device(device_id, current_user.id)
        
        return {
            "message": f"Đã từ bỏ quyền sở hữu thiết bị {device_id} thành công"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Lỗi khi từ bỏ quyền sở hữu thiết bị: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/devices/turn/", response_model=dict)
def turn_device_endpoint(
    turn_request: DeviceTurnRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bật hoặc tắt thiết bị.
    value=0: Tắt thiết bị
    value=1: Bật thiết bị
    
    Chỉ cho phép điều khiển nếu người dùng sở hữu thiết bị đó.
    """
    try:
        result = turn_device(turn_request.device_id, current_user.id, turn_request.value)
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
        return result
        
    except Exception as e:
        logger.error(f"Lỗi khi bật/tắt thiết bị: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 