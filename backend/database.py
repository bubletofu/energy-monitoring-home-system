from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import os

# Xác định loại kết nối dựa trên biến môi trường
USER_ROLE = os.getenv("USER_ROLE", "default")

# Sử dụng DATABASE_URL từ settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Tạo engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Tạo session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo base class cho models
Base = declarative_base()

# Dependency để lấy database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 