from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from sqlalchemy import desc
import models, auth
from database import get_db
from data_compression import IDEALEMCompressor, DEFAULT_COMPRESSION_METHOD
import logging
import json
import datetime

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo router
router = APIRouter(
    prefix="/compression",
    tags=["compression"],
    responses={404: {"description": "Not found"}},
)

# Khởi tạo compressor
idealem_compressor = IDEALEMCompressor()

# Biến toàn cục để theo dõi phương pháp nén hiện tại
current_compression_method = DEFAULT_COMPRESSION_METHOD

def get_active_compressor():
    """
    Trả về compressor hiện đang được sử dụng
    """
    return idealem_compressor

@router.post("/compress")
async def compress_data(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Nén dữ liệu sử dụng thuật toán IDEALEM và trả về dữ liệu đã nén cùng thống kê.
    Dữ liệu đã nén sẽ được lưu vào database.
    """
    try:
        # Đảm bảo device_id được đặt
        if "device_id" not in data:
            data["device_id"] = f"device_{current_user.id}"
            
        # Đảm bảo thiết bị tồn tại trong database
        device = db.query(models.Device).filter(models.Device.device_id == data["device_id"]).first()
        if not device:
            # Tạo thiết bị mới nếu chưa tồn tại
            device = models.Device(
                device_id=data["device_id"],
                name=f"Device {data['device_id']}",
                description=f"Thiết bị được tạo tự động cho người dùng {current_user.username}"
            )
            db.add(device)
            db.commit()
            db.refresh(device)
            logger.info(f"Đã tạo thiết bị mới với ID: {device.device_id}")
            
        # Lấy compressor
        compressor = get_active_compressor()
        
        # Kiểm tra dữ liệu đầu vào
        if "readings" not in data or not isinstance(data["readings"], dict):
            logger.warning(f"Dữ liệu đầu vào không hợp lệ: thiếu trường 'readings' hoặc không phải là dictionary")
            data["readings"] = {}  # Tạo readings rỗng để tránh lỗi
            
        # Nén dữ liệu
        try:
            compressed_data, stats = compressor.compress(data)
            logger.info(f"Nén dữ liệu thành công với tỷ lệ nén: {stats['compression_ratio']:.4f}")
        except Exception as e:
            logger.error(f"Lỗi trong quá trình nén dữ liệu: {str(e)}")
            # Tạo dữ liệu nén đơn giản nếu có lỗi
            compressed_data = {
                "device_id": data["device_id"],
                "timestamp": data.get("timestamp", datetime.datetime.utcnow().isoformat()),
                "readings": data.get("readings", {}),
                "compression_error": str(e)
            }
            stats = {
                "original_size_bytes": len(json.dumps(data).encode('utf-8')),
                "compressed_size_bytes": len(json.dumps(compressed_data).encode('utf-8')),
                "compression_ratio": 1.0,  # Không nén
                "error": 1.0,  # Đánh dấu có lỗi
                "method": "IDEALEM"
            }
        
        # Lưu vào database
        try:
            new_compressed_entry = models.CompressedData(
                device_id=data["device_id"],
                original_data=data,
                compressed_data=compressed_data,
                compression_ratio=stats["compression_ratio"],
                error=stats.get("error", 0.0),
                processing_time=stats.get("processing_time_ms"),
                compression_method="IDEALEM",
                timestamp=datetime.datetime.utcnow()
            )
            
            db.add(new_compressed_entry)
            db.commit()
            db.refresh(new_compressed_entry)
            logger.info(f"Đã lưu dữ liệu nén với ID: {new_compressed_entry.id}, tỷ lệ nén: {stats['compression_ratio']:.4f}")
            
            # Đánh dấu dữ liệu đã được lưu
            saved_to_database = True
            saved_id = new_compressed_entry.id
        except Exception as db_error:
            logger.error(f"Lỗi khi lưu dữ liệu nén vào database: {str(db_error)}")
            db.rollback()
            # Đánh dấu dữ liệu không được lưu
            saved_to_database = False
            saved_id = None
        
        return {
            "compressed_data": compressed_data,
            "statistics": stats,
            "saved_to_database": saved_to_database,
            "saved_id": saved_id,
            "compression_method": "IDEALEM"
        }
    except Exception as e:
        logger.error(f"Lỗi khi nén dữ liệu: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.get("/compressed-data")
async def get_compressed_data(
    skip: int = 0, 
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Lấy danh sách dữ liệu đã nén bằng phương pháp IDEALEM từ database
    """
    try:
        # Tạo truy vấn cơ bản lọc theo phương pháp nén IDEALEM
        query = db.query(models.CompressedData).filter(models.CompressedData.compression_method == "IDEALEM")
            
        # Thực hiện phân trang
        compressed_data = query.order_by(models.CompressedData.timestamp.desc()).offset(skip).limit(limit).all()
        
        # Chuyển đổi thành dạng có thể JSON hóa
        result = []
        for entry in compressed_data:
            result.append({
                "id": entry.id,
                "device_id": entry.device_id,
                "compression_ratio": entry.compression_ratio,
                "error": entry.error,
                "processing_time": entry.processing_time,
                "timestamp": entry.timestamp.isoformat(),
                "compression_method": entry.compression_method,
                "original_data": entry.original_data,
                "compressed_data": entry.compressed_data
            })
            
        return {
            "total": len(result),
            "data": result
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu nén: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.get("/stats")
async def get_compression_stats(
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Lấy thống kê về hiệu suất nén
    """
    try:
        # Lấy thống kê của compressor
        compressor = get_active_compressor()
        stats = compressor.get_stats()
        stats["current_method"] = current_compression_method
            
        return stats
    except Exception as e:
        logger.error(f"Lỗi khi lấy thống kê nén: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.post("/reset")
async def reset_compressor(
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Reset trạng thái của compressor
    """
    try:
        # Reset compressor
        compressor = get_active_compressor()
        compressor.reset()
            
        return {"message": f"Compressor đã được reset thành công"}
    except Exception as e:
        logger.error(f"Lỗi khi reset compressor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.post("/method")
async def set_compression_method(
    data: Dict[str, Any],
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Đặt phương pháp nén hiện tại
    """
    try:
        # Phương pháp duy nhất là idealem
        method = "idealem"
        global current_compression_method
        current_compression_method = method
        
        return {
            "message": f"Đang sử dụng phương pháp nén: {method}",
            "current_method": current_compression_method
        }
    except Exception as e:
        logger.error(f"Lỗi khi đặt phương pháp nén: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.post("/batch_compress")
async def batch_compress(
    data_points: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Nén hàng loạt các điểm dữ liệu sử dụng thuật toán IDEALEM và lưu vào database
    """
    try:
        results = []
        saved_ids = []
        failed_count = 0
        
        # Lấy compressor
        compressor = get_active_compressor()
        
        for index, data_point in enumerate(data_points):
            try:
                # Đảm bảo device_id được đặt
                if "device_id" not in data_point:
                    data_point["device_id"] = f"device_{current_user.id}"
                    
                # Đảm bảo thiết bị tồn tại
                device = db.query(models.Device).filter(models.Device.device_id == data_point["device_id"]).first()
                if not device:
                    device = models.Device(
                        device_id=data_point["device_id"],
                        name=f"Device {data_point['device_id']}",
                        description=f"Thiết bị được tạo tự động cho người dùng {current_user.username}"
                    )
                    db.add(device)
                    db.commit()
                    db.refresh(device)
                
                # Kiểm tra dữ liệu đầu vào
                if "readings" not in data_point or not isinstance(data_point["readings"], dict):
                    logger.warning(f"Điểm dữ liệu {index} không hợp lệ: thiếu trường 'readings' hoặc không phải là dictionary")
                    data_point["readings"] = {}  # Tạo readings rỗng để tránh lỗi
                
                # Nén dữ liệu
                try:
                    compressed_data, stats = compressor.compress(data_point)
                except Exception as e:
                    logger.error(f"Lỗi khi nén điểm dữ liệu {index}: {str(e)}")
                    # Tạo dữ liệu nén đơn giản nếu có lỗi
                    compressed_data = {
                        "device_id": data_point["device_id"],
                        "timestamp": data_point.get("timestamp", datetime.datetime.utcnow().isoformat()),
                        "readings": data_point.get("readings", {}),
                        "compression_error": str(e)
                    }
                    stats = {
                        "original_size_bytes": len(json.dumps(data_point).encode('utf-8')),
                        "compressed_size_bytes": len(json.dumps(compressed_data).encode('utf-8')),
                        "compression_ratio": 1.0,  # Không nén
                        "error": 1.0,  # Đánh dấu có lỗi
                        "method": "IDEALEM"
                    }
                
                # Lưu vào database
                try:
                    new_compressed_entry = models.CompressedData(
                        device_id=data_point["device_id"],
                        original_data=data_point,
                        compressed_data=compressed_data,
                        compression_ratio=stats["compression_ratio"],
                        error=stats.get("error", 0.0),
                        processing_time=stats.get("processing_time_ms"),
                        compression_method="IDEALEM",
                        timestamp=datetime.datetime.utcnow()
                    )
                    
                    db.add(new_compressed_entry)
                    db.commit()
                    db.refresh(new_compressed_entry)
                    saved_ids.append(new_compressed_entry.id)
                    
                    results.append({
                        "original_data": data_point,
                        "compressed_data": compressed_data,
                        "statistics": stats,
                        "saved_id": new_compressed_entry.id
                    })
                except Exception as db_error:
                    logger.error(f"Lỗi khi lưu điểm dữ liệu {index} vào database: {str(db_error)}")
                    db.rollback()
                    failed_count += 1
                    
                    results.append({
                        "original_data": data_point,
                        "compressed_data": compressed_data,
                        "statistics": stats,
                        "error": f"Không thể lưu vào database: {str(db_error)}"
                    })
            except Exception as e:
                logger.error(f"Lỗi khi xử lý điểm dữ liệu {index}: {str(e)}")
                failed_count += 1
                results.append({
                    "original_data": data_point if 'data_point' in locals() else {"error": "unknown data point"},
                    "error": f"Lỗi xử lý: {str(e)}"
                })
        
        # Lấy thống kê tổng thể
        try:
            overall_stats = compressor.get_stats()
        except Exception as e:
            logger.error(f"Lỗi khi lấy thống kê tổng thể: {str(e)}")
            overall_stats = {
                "error": f"Không thể lấy thống kê: {str(e)}",
                "method": "IDEALEM"
            }
        
        return {
            "results": results,
            "overall_statistics": overall_stats,
            "saved_to_database": len(saved_ids) > 0,
            "saved_ids": saved_ids,
            "failed_count": failed_count,
            "compression_method": "IDEALEM"
        }
    except Exception as e:
        logger.error(f"Lỗi khi nén hàng loạt: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.post("/config")
async def update_compressor_config(
    config: Dict[str, Any],
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Cập nhật cấu hình của compressor
    """
    try:
        # Khởi tạo lại compressor với cấu hình mới
        global idealem_compressor
        idealem_compressor = IDEALEMCompressor(config)
        
        return {
            "message": f"Cấu hình compressor đã được cập nhật",
            "current_config": config
        }
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.post("/daily_summary")
async def process_daily_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Tổng hợp và xử lý dữ liệu trong 24 giờ, sau đó gửi lên Adafruit IO
    Chức năng này sẽ:
    1. Lấy dữ liệu đã nén trong 24 giờ qua từ database
    2. Tổng hợp thống kê quan trọng
    3. Phát hiện điểm dữ liệu bất thường
    4. Gửi dữ liệu tổng hợp và cảnh báo lên Adafruit IO
    """
    try:
        from mqtt_client import MQTTClient
        from datetime import datetime, timedelta
        import numpy as np
        import statistics
        
        # Khởi tạo MQTT client để gửi dữ liệu lên Adafruit
        mqtt_client = MQTTClient()
        try:
            mqtt_client.connect()
            logger.info("Đã kết nối tới MQTT broker để gửi tổng hợp dữ liệu 24 giờ")
        except Exception as e:
            logger.error(f"Không thể kết nối tới MQTT broker: {str(e)}")
            return {
                "status": "error",
                "message": "Không thể kết nối tới MQTT broker",
                "error": str(e)
            }
        
        # Lấy thời điểm 24 giờ trước
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        # Truy vấn dữ liệu trong 24 giờ
        compressed_data = db.query(models.CompressedData).filter(
            models.CompressedData.timestamp >= twenty_four_hours_ago,
            models.CompressedData.compression_method == "IDEALEM"
        ).all()
        
        if not compressed_data:
            logger.warning("Không có dữ liệu nén trong 24 giờ qua")
            return {
                "status": "warning",
                "message": "Không có dữ liệu nén trong 24 giờ qua"
            }
        
        # Đếm số lượng dữ liệu
        data_count = len(compressed_data)
        logger.info(f"Tìm thấy {data_count} điểm dữ liệu trong 24 giờ qua")
        
        # Khởi tạo các biến thống kê
        hourly_stats = {}
        compression_ratios = []
        hit_ratios = []
        total_original_size = 0
        total_compressed_size = 0
        anomalies = []
        
        # Xử lý từng điểm dữ liệu
        for entry in compressed_data:
            # Lấy thông tin thời gian
            timestamp = entry.timestamp
            hour = timestamp.hour
            
            # Cập nhật thống kê nén
            compression_ratios.append(entry.compression_ratio)
            total_original_size += len(json.dumps(entry.original_data).encode('utf-8'))
            total_compressed_size += len(json.dumps(entry.compressed_data).encode('utf-8'))
            
            # Tạo thống kê theo giờ
            if hour not in hourly_stats:
                hourly_stats[hour] = {
                    "temperature": [],
                    "humidity": [],
                    "pressure": [],
                    "power": [],
                    "battery": []
                }
            
            # Lấy dữ liệu thực tế từ điểm dữ liệu
            readings = {}
            if 'readings' in entry.original_data:
                readings = entry.original_data['readings']
            elif 'compression_meta' in entry.compressed_data and 'original_readings' in entry.compressed_data['compression_meta']:
                readings = entry.compressed_data['compression_meta']['original_readings']
            
            # Cập nhật thống kê theo giờ
            for metric in hourly_stats[hour]:
                if metric in readings:
                    hourly_stats[hour][metric].append(readings[metric])
        
        # Tính toán tỷ lệ nén trung bình
        avg_compression_ratio = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0
        
        # Lấy thống kê từ compressor
        compressor = get_active_compressor()
        compression_stats = compressor.get_stats()
        hit_ratio = compression_stats.get('hit_ratio', 0)
        block_size = compression_stats.get('current_block_size', 0)
        
        # Phát hiện điểm bất thường trong dữ liệu
        for hour, metrics in hourly_stats.items():
            for metric_name, values in metrics.items():
                if len(values) >= 5:  # Cần ít nhất 5 điểm để phát hiện bất thường
                    try:
                        # Tính trung bình và độ lệch chuẩn
                        mean_value = sum(values) / len(values)
                        std_dev = statistics.stdev(values)
                        
                        # Kiểm tra điểm nằm ngoài phạm vi 3 độ lệch chuẩn
                        for i, value in enumerate(values):
                            if abs(value - mean_value) > 3 * std_dev:
                                anomalies.append({
                                    "hour": hour,
                                    "metric": metric_name,
                                    "value": value,
                                    "mean": mean_value,
                                    "std_dev": std_dev
                                })
                    except Exception as e:
                        logger.error(f"Lỗi khi phát hiện điểm bất thường: {str(e)}")
        
        # Chuẩn bị dữ liệu để gửi lên Adafruit
        # 1. Dữ liệu tổng hợp theo giờ
        hourly_summary = {}
        for hour, metrics in hourly_stats.items():
            hourly_summary[hour] = {}
            for metric_name, values in metrics.items():
                if values:
                    hourly_summary[hour][metric_name] = sum(values) / len(values)
        
        # 2. Chuẩn bị thống kê hiệu suất nén
        compression_summary = {
            "data_points": data_count,
            "compression_ratio": avg_compression_ratio,
            "hit_ratio": hit_ratio,
            "block_size": block_size,
            "total_original_size": total_original_size,
            "total_compressed_size": total_compressed_size,
            "space_saved_percent": (1 - (total_compressed_size / total_original_size)) * 100 if total_original_size > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 3. Chuẩn bị danh sách điểm bất thường
        anomalies_summary = {
            "count": len(anomalies),
            "details": anomalies[:10],  # Giới hạn số lượng chi tiết gửi đi
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Gửi dữ liệu lên Adafruit IO
        try:
            # Gửi tổng hợp theo giờ
            mqtt_client.publish_message("daily-summary", json.dumps(hourly_summary))
            logger.info("Đã gửi tổng hợp dữ liệu theo giờ lên Adafruit IO")
            
            # Gửi thống kê nén
            mqtt_client.publish_message("compression-stats", json.dumps(compression_summary))
            logger.info("Đã gửi thống kê hiệu suất nén lên Adafruit IO")
            
            # Gửi thông tin điểm bất thường (nếu có)
            if anomalies:
                mqtt_client.publish_message("anomalies", json.dumps(anomalies_summary))
                logger.info(f"Đã gửi thông tin về {len(anomalies)} điểm bất thường lên Adafruit IO")
        except Exception as e:
            logger.error(f"Lỗi khi gửi dữ liệu lên Adafruit IO: {str(e)}")
            return {
                "status": "partial_error",
                "message": "Có lỗi khi gửi dữ liệu lên Adafruit IO",
                "error": str(e),
                "data": {
                    "hourly_summary": hourly_summary,
                    "compression_summary": compression_summary,
                    "anomalies": anomalies_summary
                }
            }
        finally:
            # Đảm bảo ngắt kết nối MQTT
            mqtt_client.disconnect()
        
        # Lưu bản ghi về quá trình tổng hợp
        try:
            daily_summary = models.DailySummary(
                start_time=twenty_four_hours_ago,
                end_time=datetime.utcnow(),
                data_points=data_count,
                compression_ratio=avg_compression_ratio,
                hit_ratio=hit_ratio,
                anomalies_count=len(anomalies),
                summary_data=hourly_summary
            )
            db.add(daily_summary)
            db.commit()
            logger.info(f"Đã lưu tổng hợp 24 giờ vào database với ID: {daily_summary.id}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu tổng hợp vào database: {str(e)}")
            db.rollback()
        
        # Trả về kết quả
        return {
            "status": "success",
            "message": f"Đã xử lý {data_count} điểm dữ liệu trong 24 giờ qua",
            "hourly_summary": hourly_summary,
            "compression_summary": compression_summary,
            "anomalies": {
                "count": len(anomalies),
                "details": anomalies[:10] if len(anomalies) > 10 else anomalies
            }
        }
    except Exception as e:
        logger.error(f"Lỗi khi xử lý dữ liệu 24 giờ: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

# Tạo một scheduled task để tự động kích hoạt hàm xử lý hàng ngày
@router.on_event("startup")
async def setup_daily_task():
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        # Hàm để thực hiện cuộc gọi API
        async def trigger_daily_summary():
            try:
                from fastapi.testclient import TestClient
                from main import app
                
                client = TestClient(app)
                # Lấy token có quyền admin
                admin_token = get_admin_token()
                if not admin_token:
                    logger.error("Không thể lấy token admin để kích hoạt tổng hợp hàng ngày")
                    return
                
                # Gọi API tổng hợp dữ liệu
                response = client.post(
                    "/compression/daily_summary",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 200:
                    logger.info("Đã kích hoạt tổng hợp dữ liệu 24 giờ thành công")
                else:
                    logger.error(f"Lỗi khi kích hoạt tổng hợp dữ liệu: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Lỗi khi gọi API tổng hợp tự động: {str(e)}")
        
        # Khởi tạo scheduler
        scheduler = AsyncIOScheduler()
        
        # Lên lịch chạy hàng ngày vào lúc 00:05
        scheduler.add_job(
            trigger_daily_summary,
            CronTrigger(hour=0, minute=5),
            id="daily_summary_job",
            replace_existing=True
        )
        
        # Khởi động scheduler
        scheduler.start()
        logger.info("Đã lên lịch tổng hợp dữ liệu 24 giờ tự động vào lúc 00:05 hàng ngày")
    except ImportError:
        logger.warning("Không thể nhập APScheduler. Cài đặt với lệnh: pip install apscheduler")
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập tác vụ tự động: {str(e)}")

# Hàm hỗ trợ để lấy token admin
def get_admin_token() -> str:
    """
    Lấy token với quyền admin để gọi API nội bộ
    """
    try:
        from auth import create_access_token
        from datetime import timedelta
        
        # Tạo token với quyền admin (giả định user_id=1 là admin)
        access_token = create_access_token(
            data={"sub": "admin", "user_id": 1},
            expires_delta=timedelta(minutes=30)
        )
        return access_token
    except Exception as e:
        logger.error(f"Lỗi khi tạo token admin: {str(e)}")
        return ""

@router.get("/daily_summaries")
async def get_daily_summaries(
    skip: int = 0,
    limit: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Lấy danh sách các bản tổng hợp dữ liệu hàng ngày
    """
    try:
        # Truy vấn cơ sở dữ liệu để lấy các bản tổng hợp, sắp xếp theo thời gian gần nhất
        summaries = db.query(models.DailySummary)\
            .order_by(desc(models.DailySummary.end_time))\
            .offset(skip).limit(limit).all()
            
        # Chuyển đổi thành dạng có thể JSON hóa
        result = []
        for summary in summaries:
            result.append({
                "id": summary.id,
                "start_time": summary.start_time.isoformat() if summary.start_time else None,
                "end_time": summary.end_time.isoformat() if summary.end_time else None,
                "data_points": summary.data_points,
                "compression_ratio": summary.compression_ratio,
                "hit_ratio": summary.hit_ratio,
                "anomalies_count": summary.anomalies_count,
                "sent_to_adafruit": summary.sent_to_adafruit,
                "created_at": summary.created_at.isoformat() if summary.created_at else None,
            })
            
        return result
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bản tổng hợp dữ liệu hàng ngày: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        )

@router.get("/daily_summary/{summary_id}")
async def get_daily_summary_detail(
    summary_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Lấy chi tiết một bản tổng hợp dữ liệu hàng ngày
    """
    try:
        # Truy vấn cơ sở dữ liệu để lấy bản tổng hợp theo ID
        summary = db.query(models.DailySummary).filter(models.DailySummary.id == summary_id).first()
        
        if summary is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy bản tổng hợp với ID: {summary_id}"
            )
            
        # Chuyển đổi thành dạng có thể JSON hóa
        result = {
            "id": summary.id,
            "start_time": summary.start_time.isoformat() if summary.start_time else None,
            "end_time": summary.end_time.isoformat() if summary.end_time else None,
            "data_points": summary.data_points,
            "compression_ratio": summary.compression_ratio,
            "hit_ratio": summary.hit_ratio,
            "anomalies_count": summary.anomalies_count,
            "sent_to_adafruit": summary.sent_to_adafruit,
            "created_at": summary.created_at.isoformat() if summary.created_at else None,
            "summary_data": json.loads(summary.summary_data) if isinstance(summary.summary_data, str) else summary.summary_data,
        }
            
        return result
    except HTTPException as he:
        # Đẩy HTTPException lên cấp trên
        raise he
    except Exception as e:
        logger.error(f"Lỗi khi lấy chi tiết bản tổng hợp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý: {str(e)}"
        ) 