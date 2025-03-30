from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import timedelta, datetime
from typing import List, Dict, Any
import models, auth
from pydantic import BaseModel, Field
import logging
import json
from fastapi.responses import JSONResponse
from config import settings
from mqtt_client import MQTTClient

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo MQTT client
mqtt_client = MQTTClient()

# Thông tin kết nối database từ config
DATABASE_URL = settings.DATABASE_URL
logger.info(f"Initializing database connection with URL: {DATABASE_URL}")

# Tạo engine với URL đã được xác nhận
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Kiểm tra kết nối trước khi sử dụng
    pool_recycle=300,    # Tái sử dụng connection sau 5 phút
)

# Thử kết nối để kiểm tra
try:
    with engine.connect() as connection:
        logger.info("Successfully connected to database")
except Exception as e:
    logger.error(f"Failed to connect to database: {str(e)}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo các bảng nếu chưa tồn tại
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    try:
        mqtt_client.connect()
        logger.info("MQTT client connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect MQTT client: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    try:
        mqtt_client.disconnect()
        logger.info("MQTT client disconnected successfully")
    except Exception as e:
        logger.error(f"Error disconnecting MQTT client: {str(e)}")

# Dependency để lấy database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class DeviceConfigCreate(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=100)
    config_data: Dict[str, Any] = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "device_name": "my_device",
                "config_data": {
                    "temperature": 25,
                    "humidity": 60
                }
            }
        }

class Token(BaseModel):
    access_token: str
    token_type: str

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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
        access_token_expires = timedelta(minutes=30)
        access_token = auth.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        logger.info("Access token created successfully")
        
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

@app.post("/device-config/", response_model=dict)
async def create_device_config(
    config: DeviceConfigCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        logger.info(f"Received request for user: {current_user.username} (ID: {current_user.id})")
        logger.info(f"Device config data: {config.dict()}")

        # Validate config_data
        if not isinstance(config.config_data, dict):
            logger.error("Invalid config_data format")
            raise HTTPException(
                status_code=400,
                detail="config_data must be a valid JSON object"
            )

        logger.info("Creating device config in database...")
        try:
            # Create device config
            db_config = models.DeviceConfig(
                device_name=config.device_name,
                config_data=config.config_data,
                user_id=current_user.id
            )
            logger.info(f"Created device config object: {db_config.__dict__}")

            db.add(db_config)
            logger.info("Added to session")
            
            db.commit()
            logger.info("Committed to database")
            
            db.refresh(db_config)
            logger.info("Refreshed object")
            
            response_data = {
                "message": "Device configuration saved successfully",
                "device_id": db_config.id,
                "device_name": db_config.device_name,
                "user_id": db_config.user_id,
                "config_data": db_config.config_data
            }
            logger.info(f"Success response: {response_data}")
            return JSONResponse(
                status_code=200,
                content=response_data
            )
            
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error details: {str(db_error)}")
            logger.exception("Full database error traceback:")
            raise HTTPException(
                status_code=500,
                detail=f"Error saving to database: {str(db_error)}"
            )

    except HTTPException as http_ex:
        logger.error(f"HTTP exception: {str(http_ex)}")
        raise http_ex
    except Exception as e:
        logger.error(f"Unexpected error details: {str(e)}")
        logger.exception("Full error traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/device-config/{user_id}")
def get_device_configs(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        if current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this resource")
        
        configs = db.query(models.DeviceConfig).filter(models.DeviceConfig.user_id == user_id).all()
        return configs
    except Exception as e:
        logger.error(f"Error in get_device_configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/device-data/")
async def publish_device_data(
    data: Dict[str, Any],
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        # Thêm thông tin user vào data
        data["user_id"] = current_user.id
        data["timestamp"] = datetime.utcnow().isoformat()
        
        # Publish message
        topic = f"iot/devices/{current_user.id}"
        mqtt_client.publish_message(topic, data)
        
        return {"message": "Device data published successfully"}
    except Exception as e:
        logger.error(f"Error publishing device data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 