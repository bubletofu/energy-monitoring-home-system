#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script nén dữ liệu từ bảng original_samples, lưu kết quả vào bảng compressed_data_optimized.
Sử dụng thuật toán nén dữ liệu từ module data_compression.py.
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, inspect
import pandas as pd
import argparse
import matplotlib.pyplot as plt
import numpy as np
import psycopg2
from dotenv import load_dotenv

# Import thuật toán nén từ module data_compression
from data_compression import DataCompressor

# Import thêm thư viện cho MyEncoder
import numpy as np

# Import từ module visualization_analyzer
from visualization_analyzer import create_visualizations

# Lớp JSONEncoder tùy chỉnh cho việc chuyển đổi các kiểu dữ liệu NumPy và boolean
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            # Xử lý giá trị NaN và vô cực
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, float):
            # Xử lý giá trị NaN và vô cực trong floating point thông thường
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj
        elif isinstance(obj, np.bool_):
            return bool(obj)  # Xử lý np.bool_ đúng cách
        elif isinstance(obj, bool):
            return bool(obj)  # Đảm bảo boolean Python thông thường được xử lý
        elif isinstance(obj, set):
            return list(obj)  # Chuyển đổi set thành list
        return super(MyEncoder, self).default(obj)

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("compress.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load biến môi trường từ file .env
load_dotenv()

# Lấy thông tin kết nối từ biến môi trường
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'iot_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')

# Tạo DATABASE_URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def setup_optimized_database():
    """
    Thiết lập kết nối đến database và tạo cấu trúc bảng tối ưu không cần bảng ref
    
    Returns:
        engine: SQLAlchemy engine, hoặc None nếu không thể kết nối
    """
    try:
        # Tạo engine kết nối đến database
        engine = create_engine(DATABASE_URL)
        
        # Kiểm tra kết nối
        with engine.connect() as conn:
            # Tạo bảng devices nếu chưa tồn tại
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS devices (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR UNIQUE NOT NULL,
                    name VARCHAR,
                    description VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Tạo index cho bảng devices
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_devices_id ON devices (id);
                CREATE UNIQUE INDEX IF NOT EXISTS ix_devices_device_id ON devices (device_id);
            """))
            
            # Tạo bảng compressed_data_optimized nếu chưa tồn tại
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS compressed_data_optimized (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    compression_metadata JSONB, -- Lưu thông tin nén (compression_ratio, hit_ratio, etc)
                    templates JSONB, -- Lưu templates
                    encoded_stream JSONB, -- Lưu chuỗi mã hóa
                    time_range TSRANGE, -- Phạm vi thời gian của dữ liệu
                    FOREIGN KEY (device_id) REFERENCES devices(device_id)
                )
            """))
            
            # Tạo index cho bảng compressed_data_optimized
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_compressed_data_optimized_device_id ON compressed_data_optimized (device_id);
                CREATE INDEX IF NOT EXISTS idx_compressed_data_optimized_timestamp ON compressed_data_optimized (timestamp);
                CREATE INDEX IF NOT EXISTS idx_compressed_data_optimized_time_range ON compressed_data_optimized USING GIST (time_range);
            """))
            
            conn.commit()
            
        logger.info(f"Đã kết nối thành công đến database và thiết lập bảng tối ưu: {DATABASE_URL}")
        return engine
    except Exception as e:
        logger.error(f"Lỗi khi kết nối đến database hoặc thiết lập bảng: {str(e)}")
        return None

def ensure_device_exists(engine, device_id):
    """
    Đảm bảo thiết bị tồn tại trong bảng devices
    
    Args:
        engine: SQLAlchemy engine
        device_id: ID của thiết bị
        
    Returns:
        bool: True nếu thiết bị đã tồn tại hoặc đã được thêm thành công, False nếu có lỗi
    """
    try:
        with engine.connect() as conn:
            # Kiểm tra xem device_id đã tồn tại trong bảng devices chưa
            result = conn.execute(
                text("SELECT device_id FROM devices WHERE device_id = :device_id"),
                {"device_id": device_id}
            ).fetchone()
            
            # Nếu device_id chưa tồn tại, thêm vào bảng devices
            if not result:
                device_name = f"Device {device_id}"
                device_description = f"Thiết bị được tự động thêm khi nén dữ liệu"
                
                conn.execute(text("""
                    INSERT INTO devices (device_id, name, description, created_at)
                    VALUES (:device_id, :name, :description, :created_at)
                """), {
                    "device_id": device_id,
                    "name": device_name,
                    "description": device_description,
                    "created_at": datetime.now()
                })
                conn.commit()
                logger.info(f"Đã tự động tạo thiết bị mới với device_id: {device_id}")
            
            return True
    except Exception as e:
        logger.error(f"Lỗi khi đảm bảo thiết bị tồn tại: {str(e)}")
        return False

def fetch_original_data(engine, limit=1000, device_id=None):
    """
    Lấy dữ liệu từ bảng original_samples
    
    Args:
        engine: SQLAlchemy engine
        limit: Số lượng bản ghi tối đa cần lấy
        device_id: ID của thiết bị cần lấy dữ liệu, None để lấy tất cả
        
    Returns:
        list: Danh sách các bản ghi dữ liệu
    """
    try:
        # Chuẩn bị truy vấn
        query = """
        SELECT id, device_id, value, timestamp
        FROM original_samples
        """
        
        # Thêm điều kiện filter
        params = {}
        if device_id:
            query += " WHERE device_id = :device_id"
            params['device_id'] = device_id
            
        # Thêm limit và sắp xếp theo thời gian giảm dần (mới nhất trước)
        query += " ORDER BY timestamp DESC LIMIT :limit"
        params['limit'] = limit
        
        # Thực hiện truy vấn
        records = []
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            for row in result:
                record = {
                    'id': row[0],
                    'device_id': row[1],
                    'value': row[2],  # Thay original_data bằng value
                    'timestamp': row[3]
                }
                records.append(record)
        
        # Đảo ngược lại danh sách để có thứ tự tăng dần theo thời gian khi xử lý
        records.reverse()
                
        logger.info(f"Đã lấy {len(records)} bản ghi từ bảng original_samples")
        return records
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu từ original_samples: {str(e)}")
        raise

def save_optimized_compression_result(engine, device_id, compression_result, timestamps=None):
    """
    Lưu kết quả nén vào bảng compressed_data_optimized
    """
    conn = None
    cursor = None
    try:
        # Tạo kết nối trực tiếp với psycopg2
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cursor = conn.cursor()

        # Chuẩn bị dữ liệu để lưu
        compression_metadata = {
            'compression_ratio': compression_result.get('compression_ratio', 0),
            'hit_ratio': compression_result.get('hit_ratio', 0),
            'avg_cer': compression_result.get('avg_cer', 0),
            'total_values': compression_result.get('total_values', 0)
        }

        # Chuyển đổi sang JSON
        compression_metadata_json = json.dumps(compression_metadata, cls=MyEncoder)
        templates_json = json.dumps(compression_result.get('templates', {}), cls=MyEncoder)
        encoded_stream_json = json.dumps(compression_result.get('encoded_stream', []), cls=MyEncoder)

        # Xử lý time_range nếu có timestamps
        time_range_str = None
        if timestamps and len(timestamps) > 0:
            min_time = min(timestamps)
            max_time = max(timestamps)
            time_range_str = f"[{min_time.isoformat()}, {max_time.isoformat()}]"

        # Lưu vào database
        if time_range_str:
            query = """
            INSERT INTO compressed_data_optimized 
            (device_id, compression_metadata, templates, encoded_stream, time_range)
            VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s::tsrange)
            RETURNING id
            """
            cursor.execute(query, (
                device_id, compression_metadata_json, templates_json, 
                encoded_stream_json, time_range_str
            ))
        else:
            query = """
            INSERT INTO compressed_data_optimized 
            (device_id, compression_metadata, templates, encoded_stream)
            VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb)
            RETURNING id
            """
            cursor.execute(query, (
                device_id, compression_metadata_json, templates_json, 
                encoded_stream_json
            ))

        # Lấy ID từ kết quả trả về
        compression_id = cursor.fetchone()[0]
        conn.commit()

        # Tính tỷ lệ nén thực tế từ database
        try:
            # Query để lấy kích thước dữ liệu nén
            query_compressed = """
            SELECT pg_column_size(templates) + pg_column_size(encoded_stream) + 
                   pg_column_size(compression_metadata)
            FROM compressed_data_optimized
            WHERE id = %s
            """
            cursor.execute(query_compressed, (compression_id,))
            compressed_size = cursor.fetchone()[0] or 0

            # Query để lấy kích thước dữ liệu gốc (đã thay đổi theo cấu trúc mới)
            query_original = """
            SELECT SUM(pg_column_size(value))
            FROM original_samples
            WHERE device_id = %s
            """
            cursor.execute(query_original, (device_id,))
            original_size = cursor.fetchone()[0] or 0

            if compressed_size > 0:
                real_ratio = original_size / compressed_size
                # Cập nhật tỷ lệ nén thực tế vào metadata
                cursor.execute("""
                    UPDATE compressed_data_optimized 
                    SET compression_metadata = jsonb_set(
                        compression_metadata::jsonb,
                        '{compression_ratio}',
                        %s::text::jsonb
                    )
                    WHERE id = %s
                """, (str(real_ratio), compression_id))
                conn.commit()

        except Exception as e:
            logger.error(f"Lỗi khi tính tỷ lệ nén thực tế: {str(e)}")

        return compression_id

    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả nén tối ưu: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def run_compression(device_id=None, limit=200000, save_result=False, output_file=None, visualize=False, output_dir=None, visualize_max_points=5000, visualize_sampling='adaptive', visualize_chunks=0):
    """
    Nén dữ liệu từ bảng original_samples
    
    Args:
        device_id: ID của thiết bị cần lấy dữ liệu, None để lấy tất cả
        limit: Số lượng bản ghi tối đa cần xử lý
        save_result: Lưu kết quả nén vào file JSON
        output_file: Đường dẫn file để lưu kết quả nén
        visualize: Tạo biểu đồ trực quan hóa
        output_dir: Thư mục đầu ra cho biểu đồ trực quan hóa
        visualize_max_points: Số điểm tối đa để hiển thị trên biểu đồ
        visualize_sampling: Phương pháp lấy mẫu dữ liệu cho biểu đồ
        visualize_chunks: Số chunks để chia dữ liệu khi lấy mẫu
        
    Returns:
        dict: Thông tin về quá trình nén
    """
    try:
        # Thiết lập kết nối database
        engine = setup_optimized_database()
        
        # Lấy dữ liệu từ bảng original_samples
        records = fetch_original_data(engine, limit, device_id)
        
        if not records:
            logger.warning("Không có dữ liệu nào để nén")
            return {
                'success': False,
                'message': 'Không có dữ liệu nào để nén',
                'stats': {}
            }
        
        current_device_id = device_id if device_id else 'default_device'
        
        # Chuẩn bị dữ liệu cho quá trình nén
        data_points = []
        timestamps = []
        
        # Thu thập dữ liệu từ các bản ghi
        for record in records:
            # Giờ value là một số thực đơn giản
            value = record['value']
            timestamp = record['timestamp']
            
            data_points.append({
                'value': value,
                'timestamp': timestamp
            })
            timestamps.append(timestamp)

        # Khởi tạo compressor và nén dữ liệu
        compressor = DataCompressor()
        compression_result = compressor.compress(data_points)
        
        if not compression_result:
            raise Exception("Không thể nén dữ liệu")

        # Lưu kết quả nén vào database nếu cần
        if not save_result:
            # Đảm bảo device tồn tại
            if ensure_device_exists(engine, current_device_id):
                compression_id = save_optimized_compression_result(
                    engine, current_device_id, compression_result, timestamps
                )
                logger.info(f"Đã lưu kết quả nén với ID: {compression_id}")
            else:
                logger.error(f"Không thể đảm bảo thiết bị '{current_device_id}' tồn tại trong bảng devices")

        # Tính các chỉ số thống kê
        stats = {
            'num_records': len(data_points),
            'num_templates': len(compression_result['templates']),
            'num_blocks': len(compression_result['encoded_stream']),
            'compression_ratio': compression_result['compression_ratio'],
            'hit_ratio': compression_result['hit_ratio'],
            'avg_cer': compression_result['avg_cer'],
            'avg_similarity': compression_result.get('avg_similarity', 0),
            'compression_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu kết quả vào file JSON nếu có tùy chọn save-result
        if save_result:
            if not output_file:
                # Nếu không chỉ định file output, tạo tên file dựa trên thời gian
                output_file = f"compression_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            logger.info(f"Đang lưu kết quả nén vào {output_file}")
            
            # Chỉ lưu các thông tin cần thiết cho báo cáo
            simplified_result = {
                'device_id': device_id,
                'stats': {
                    'num_records': len(data_points),
                    'num_templates': len(compression_result['templates']),
                    'num_blocks': len(compression_result['encoded_stream']),
                    'compression_ratio': compression_result['compression_ratio'],
                    'hit_ratio': compression_result['hit_ratio'],
                    'avg_cer': compression_result['avg_cer'],
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(simplified_result, f, indent=2, cls=MyEncoder)
            
            logger.info(f"Đã lưu báo cáo kết quả nén vào {output_file}")
            
            # Thông báo lưu ý về việc không cần file JSON cho giải nén
            logger.info("Lưu ý: File JSON này chỉ chứa báo cáo kết quả nén, không cần thiết cho quá trình giải nén.")
            logger.info("Dữ liệu nén đã được lưu trực tiếp vào database và có thể giải nén bằng lệnh decompress_optimized.py.")
        
        # Hiển thị thông tin
        print("\n===== KẾT QUẢ NÉN =====")
        print(f"Tổng số điểm dữ liệu: {len(data_points)}")
        print(f"Số lượng template: {len(compression_result['templates'])}")
        print(f"Số lượng block: {len(compression_result['encoded_stream'])}")
        print(f"Tỷ lệ nén: {compression_result['compression_ratio']:.2f}x")
        print(f"Hit ratio: {compression_result['hit_ratio']:.2f}")
        print(f"CER trung bình: {compression_result['avg_cer']:.4f}")
        print(f"Tương đồng trung bình: {compression_result.get('avg_similarity', 0):.4f}")
        
        # Tạo biểu đồ nếu cần
        if visualize:
            try:
                # Tạo biểu đồ sử dụng hàm từ module visualization_analyzer
                from visualization_analyzer import create_visualizations
                
                # Đảm bảo thư mục đầu ra tồn tại
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # Chuyển các thông tin về thời gian cho module visualization_analyzer
                time_info = None
                if timestamps and len(timestamps) > 0:
                    time_info = {
                        'min_time': min(timestamps),
                        'max_time': max(timestamps)
                    }
                
                # Lấy thông tin compression_id từ database để truy vấn kích thước chính xác
                # compression_id đã được định nghĩa nếu dùng use_optimized
                compression_id_for_size = None
                if not save_result and 'compression_id' in locals():
                    compression_id_for_size = compression_id
                    logger.info(f"Sử dụng compression_id: {compression_id_for_size} để truy vấn kích thước từ database")
                else:
                    # Nếu không có compression_id (trường hợp không lưu vào database), thử lấy ID mới nhất
                    try:
                        if 'engine' in locals() and engine:
                            from sqlalchemy import text
                            with engine.connect() as conn:
                                # Lấy compression_id mới nhất
                                result = conn.execute(text("SELECT id FROM compressed_data_optimized ORDER BY timestamp DESC LIMIT 1")).fetchone()
                                if result:
                                    compression_id_for_size = result[0]
                                    logger.info(f"Lấy compression_id mới nhất từ database: {compression_id_for_size}")
                    except Exception as e:
                        logger.error(f"Lỗi khi lấy compression_id từ database: {str(e)}")
                
                logger.info(f"Gọi module visualization_analyzer để tạo biểu đồ phân tích")
                chart_files = create_visualizations(
                    data=data_points,
                    compression_result=compression_result, 
                    output_dir=output_dir,
                    max_points=visualize_max_points,
                    sampling_method=visualize_sampling,
                    num_chunks=visualize_chunks,
                    time_info=time_info,
                    compression_id=compression_id_for_size,
                    device_id=current_device_id
                )
                
                if chart_files:
                    logger.info(f"Đã tạo {len(chart_files)} biểu đồ phân tích: {', '.join(chart_files)}")
                    print(f"\nĐã tạo {len(chart_files)} biểu đồ phân tích trong thư mục: {output_dir}")
                else:
                    logger.warning("Không có biểu đồ nào được tạo")
            except Exception as e:
                logger.error(f"Lỗi khi tạo biểu đồ phân tích: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
        return {
            'success': True,
            'message': 'Nén dữ liệu thành công',
            'stats': stats,
            'data_points': data_points,
            'compression_result': compression_result
        }
    except Exception as e:
        logger.error(f"Lỗi khi nén dữ liệu: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'message': f'Lỗi khi nén dữ liệu: {str(e)}',
            'stats': {}
        }

def main():
    """
    Hàm chính để thực thi script nén dữ liệu
    """
    # Thiết lập tham số dòng lệnh
    parser = argparse.ArgumentParser(description='Nén dữ liệu từ database')
    parser.add_argument('--device-id', type=str, help='ID của thiết bị cần nén dữ liệu')
    parser.add_argument('--limit', type=int, default=200000, help='Số lượng bản ghi tối đa cần nén (mặc định: 200000)')
    parser.add_argument('--save-result', action='store_true', help='Lưu kết quả nén vào file JSON')
    parser.add_argument('--output-file', type=str, help='Đường dẫn file để lưu kết quả nén')
    
    # Tham số cho phần trực quan hóa
    parser.add_argument('--visualize', action='store_true', help='Tạo biểu đồ trực quan hóa')
    parser.add_argument('--output-dir', type=str, default='visualization_' + datetime.now().strftime('%Y%m%d_%H%M%S'), 
                        help='Thư mục đầu ra cho biểu đồ trực quan hóa')
    parser.add_argument('--visualize-max-points', type=int, default=5000, 
                        help='Số điểm tối đa để hiển thị trên biểu đồ (mặc định: 5000)')
    parser.add_argument('--visualize-sampling', type=str, choices=['uniform', 'peak', 'adaptive'], default='adaptive',
                        help='Phương pháp lấy mẫu dữ liệu cho biểu đồ (mặc định: adaptive)')
    parser.add_argument('--visualize-chunks', type=int, default=0,
                        help='Số chunks để chia dữ liệu khi lấy mẫu (0 = tự động)')
    
    # Parse tham số
    args = parser.parse_args()
    
    # Sử dụng nén thông qua database (luôn sử dụng bảng tối ưu)
    result = run_compression(
        device_id=args.device_id, 
        limit=args.limit,
        save_result=args.save_result,
        output_file=args.output_file,
        visualize=args.visualize,
        output_dir=args.output_dir,
        visualize_max_points=args.visualize_max_points,
        visualize_sampling=args.visualize_sampling,
        visualize_chunks=args.visualize_chunks
    )
    
    # In kết quả
    if result['success']:
        logger.info("=== KẾT QUẢ NÉN DỮ LIỆU ===")
        for key, value in result['stats'].items():
            if isinstance(value, float):
                logger.info(f"{key}: {value:.2f}")
            else:
                logger.info(f"{key}: {value}")
    else:
        logger.error(f"Nén dữ liệu thất bại: {result['message']}")
    
    logger.info("Kết thúc chương trình nén dữ liệu")

if __name__ == "__main__":
    main()