#!/usr/bin/env python3
"""
Module để phân tích và tạo biểu đồ từ dữ liệu nén được lưu trong bảng compressed_data.
Tập trung vào:
1. So sánh dữ liệu trước và sau khi nén (số dòng, kích thước)
2. Phân tích quá trình nén (templates, kích thước khối)
"""

import os
import sys
import json
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Tuple
from sqlalchemy import create_engine, text
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cấu hình đồ thị
plt.style.use('ggplot')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

def get_database_connection():
    """
    Tạo kết nối đến cơ sở dữ liệu
    
    Returns:
        SQLAlchemy engine
    """
    # Sử dụng DATABASE_URL từ biến môi trường nếu có, nếu không thì tạo từ các thành phần
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Lấy thông tin kết nối từ biến môi trường
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5433")
        db_name = os.getenv("DB_NAME", "iot_db")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "1234")
        
        # Tạo URL kết nối
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Tạo engine
        engine = create_engine(database_url)
        
        # Kiểm tra kết nối
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
        logger.info(f"Kết nối đến cơ sở dữ liệu thành công: {database_url}")
        return engine
        
    except Exception as e:
        logger.error(f"Lỗi kết nối đến cơ sở dữ liệu: {str(e)}")
        raise

def get_compression_data(engine, compression_id: int) -> Dict[str, Any]:
    """
    Lấy dữ liệu nén từ bảng compressed_data với ID chỉ định
    
    Args:
        engine: SQLAlchemy engine
        compression_id: ID của bản ghi nén
        
    Returns:
        Dict chứa thông tin về dữ liệu nén
    """
    try:
        # Câu truy vấn SQL
        query = """
        SELECT c.* 
        FROM compressed_data c
        WHERE c.id = :compression_id
        LIMIT 1
        """
        
        # Thực hiện truy vấn
        with engine.connect() as conn:
            result = conn.execute(text(query), {"compression_id": compression_id})
            row = result.fetchone()
            
            if not row:
                raise ValueError(f"Không tìm thấy dữ liệu nén với ID: {compression_id}")
                
            # Chuyển đổi thành dict
            column_names = result.keys()
            record = {col: row[idx] for idx, col in enumerate(column_names)}
            
            # Nếu không có trường compressed_data trong bảng, tạo dict rỗng
            if "compressed_data" not in record or record["compressed_data"] is None:
                compressed_data = {}
                record["compressed_data"] = compressed_data
            else:
                # Parse các trường JSON nếu cần
                if isinstance(record["compressed_data"], str):
                    try:
                        record["compressed_data"] = json.loads(record["compressed_data"])
                    except json.JSONDecodeError:
                        record["compressed_data"] = {}
                compressed_data = record["compressed_data"]
            
            # Parse config nếu có
            if "config" in record and isinstance(record["config"], str):
                try:
                    record["config"] = json.loads(record["config"])
                except json.JSONDecodeError:
                    record["config"] = {}
            
            # Trích xuất thông tin từ compressed_data hoặc gán giá trị mặc định
            record["id"] = compression_id
            record["total_values"] = compressed_data.get("total_values", 0)
            record["templates_count"] = len(compressed_data.get("templates", {}))
            record["blocks_processed"] = compressed_data.get("blocks_processed", 0)
            record["hit_ratio"] = compressed_data.get("hit_ratio", 0)
            
            # Trích xuất thông tin mới từ thuật toán nén đã cải tiến
            record["avg_cer"] = compressed_data.get("avg_cer", 0.0)
            record["avg_similarity"] = compressed_data.get("avg_similarity", 0.0)
            record["cost"] = compressed_data.get("cost", 0.0)
            
            # Lấy thêm thông tin về similarity scores và CER values nếu có
            record["similarity_scores"] = compressed_data.get("similarity_scores", [])
            record["cer_values"] = compressed_data.get("cer_values", [])
            
            # Đảm bảo có compression_ratio từ bảng
            if "compression_ratio" not in record or not record["compression_ratio"]:
                record["compression_ratio"] = compressed_data.get("compression_ratio", 1.0)
            
        logger.info(f"Đã lấy dữ liệu nén với ID: {compression_id}")
        return record
        
    except Exception as e:
        logger.error(f"Lỗi lấy dữ liệu nén: {str(e)}")
        raise

def get_original_data(engine, start_date: str = None, end_date: str = None, limit: int = 100) -> pd.DataFrame:
    """
    Lấy dữ liệu gốc từ bảng original_samples
    
    Args:
        engine: SQLAlchemy engine
        start_date: Ngày bắt đầu (YYYY-MM-DD) - tùy chọn
        end_date: Ngày kết thúc (YYYY-MM-DD) - tùy chọn
        limit: Số lượng bản ghi tối đa khi không chỉ định ngày - mặc định 100
        
    Returns:
        DataFrame chứa dữ liệu gốc
    """
    try:
        # Xây dựng câu truy vấn SQL dựa trên các tham số đầu vào
        if start_date and end_date:
            query = """
            SELECT *
            FROM original_samples
            WHERE timestamp BETWEEN :start_date AND :end_date
            ORDER BY timestamp
            """
            params = {"start_date": start_date, "end_date": end_date}
            
            # Thực hiện truy vấn
            with engine.connect() as conn:
                df = pd.read_sql(query, conn, params=params)
                
            logger.info(f"Đã lấy {len(df)} bản ghi dữ liệu gốc từ {start_date} đến {end_date}")
        else:
            # Nếu không có ngày, lấy số lượng bản ghi giới hạn theo thứ tự thời gian
            query = """
            SELECT *
            FROM original_samples
            ORDER BY timestamp
            LIMIT :limit
            """
            params = {"limit": limit}
            
            # Thực hiện truy vấn
            with engine.connect() as conn:
                df = pd.read_sql(query, conn, params=params)
                
            logger.info(f"Đã lấy {len(df)} bản ghi dữ liệu gốc gần nhất")
            
        return df
        
    except Exception as e:
        logger.error(f"Lỗi lấy dữ liệu gốc: {str(e)}")
        raise

def analyze_compression_ratio(compression_data, output_dir):
    """
    Tạo biểu đồ phân tích tỷ lệ nén
    
    Args:
        compression_data: Dữ liệu nén đã được truy xuất
        output_dir: Thư mục đầu ra để lưu biểu đồ
    """
    # Kiểm tra đường dẫn đầu ra
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Lấy các chỉ số cần thiết từ dữ liệu nén
    total_values = compression_data.get('total_values', 0)
    templates_count = compression_data.get('templates_count', 0)
    blocks_processed = compression_data.get('blocks_processed', 0)
    compression_ratio = compression_data.get('compression_ratio', 0)
    
    if not total_values or not compression_ratio:
        logger.warning("Không có đủ dữ liệu để phân tích tỷ lệ nén")
        return
        
    # Tính toán kích thước
    original_size = total_values
    compressed_size = original_size / compression_ratio if compression_ratio else 0
    
    # Tạo biểu đồ
    plt.figure(figsize=(10, 6))
    bars = plt.bar(['Dữ liệu gốc', 'Dữ liệu đã nén'], [original_size, compressed_size], color=['#3498db', '#2ecc71'])
    
    # Thêm nhãn
    plt.title('So sánh kích thước dữ liệu trước và sau khi nén', fontsize=14)
    plt.ylabel('Kích thước (số giá trị)', fontsize=12)
    
    # Thêm giá trị lên đầu thanh
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', fontsize=11)
    
    # Thêm thông tin tỷ lệ nén
    textstr = f"""
    Tỷ lệ nén: {compression_ratio:.2f}x
    Tổng số giá trị: {total_values}
    Số mẫu: {templates_count}
    Số block: {blocks_processed}
    """
    
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    plt.text(0.05, 0.95, textstr, transform=plt.gca().transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    
    # Lưu biểu đồ
    output_file = os.path.join(output_dir, 'compression_ratio.png')
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    
    logger.info(f"Đã tạo biểu đồ phân tích tỷ lệ nén: {output_file}")
    return output_file

def analyze_templates(compression_data: Dict[str, Any], output_prefix: str = None):
    """
    Phân tích và tạo biểu đồ về các template
    
    Args:
        compression_data: Dict chứa dữ liệu nén
        output_prefix: Tiền tố cho tên file biểu đồ
    """
    # Trích xuất thông tin template
    compressed_data_json = compression_data.get("compressed_data", {})
    if isinstance(compressed_data_json, str):
        try:
            compressed_data = json.loads(compressed_data_json)
        except json.JSONDecodeError:
            logger.error("Lỗi giải mã JSON từ trường compressed_data")
            return
    else:
        compressed_data = compressed_data_json
    
    templates = compressed_data.get("templates", {})
    
    # Kiểm tra nếu không có templates
    if not templates:
        logger.warning("Không có templates để phân tích")
        return
    
    # Chuyển đổi templates thành DataFrame để dễ phân tích
    template_info = []
    for tid, template in templates.items():
        template_info.append({
            "id": tid,
            "use_count": template.get("use_count", 0),
            "dimensions": len(template.get("values", [])[0]) if template.get("values") and template.get("values") else 0,
            "values_count": len(template.get("values", []))
        })
    
    template_df = pd.DataFrame(template_info)
    
    # Tạo biểu đồ phân tích template
    fig, axs = plt.subplots(1, 2, figsize=(16, 6))
    
    # 1. Biểu đồ top templates được sử dụng nhiều nhất
    top_n = min(10, len(template_df))
    top_templates = template_df.nlargest(top_n, 'use_count')
    
    bars = axs[0].bar(top_templates['id'], top_templates['use_count'], color='orange')
    axs[0].set_title(f"Top {top_n} templates được sử dụng nhiều nhất")
    axs[0].set_xlabel("Template ID")
    axs[0].set_ylabel("Số lần sử dụng")
    
    # Thêm số liệu lên biểu đồ
    for bar in bars:
        height = bar.get_height()
        axs[0].text(bar.get_x() + bar.get_width()/2., height + 0.1,
                  f'{height:.0f}',
                  ha='center', va='bottom', fontweight='bold')
    
    # 2. Biểu đồ phân bố số lần sử dụng template
    axs[1].hist(template_df['use_count'], bins=10, color='skyblue', edgecolor='black')
    axs[1].set_title("Phân bố số lần sử dụng template")
    axs[1].set_xlabel("Số lần sử dụng")
    axs[1].set_ylabel("Số lượng template")
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    if output_prefix:
        plt.savefig(f"{output_prefix}_template_analysis.png", bbox_inches='tight', dpi=300)
    
    plt.close()

def analyze_blocks(compression_data: Dict[str, Any], output_prefix: str = None):
    """
    Phân tích và tạo biểu đồ về các khối dữ liệu
    
    Args:
        compression_data: Dict chứa dữ liệu nén
        output_prefix: Tiền tố cho tên file biểu đồ
    """
    # Trích xuất thông tin khối
    compressed_data_json = compression_data.get("compressed_data", {})
    if isinstance(compressed_data_json, str):
        try:
            compressed_data = json.loads(compressed_data_json)
        except json.JSONDecodeError:
            logger.error("Lỗi giải mã JSON từ trường compressed_data")
            return
    else:
        compressed_data = compressed_data_json
    
    encoded_stream = compressed_data.get("encoded_stream", [])
    
    # Kiểm tra nếu không có khối
    if not encoded_stream:
        logger.warning("Không có khối dữ liệu để phân tích")
        return
    
    # Chuyển đổi khối thành DataFrame để dễ phân tích
    block_info = []
    for block in encoded_stream:
        # Cập nhật để đọc trường similarity_score thay vì is_match từ phiên bản cũ
        similarity_score = block.get("similarity_score", 0.0)
        # Xác định block có phải template mới hay là template được tái sử dụng
        is_template_match = similarity_score < 1.0  # Nếu similarity < 1.0 thì là template match, không phải template mới
        
        block_info.append({
            "template_id": block.get("template_id", -1),
            "is_template_match": is_template_match,  # Dùng để xác định nếu block là template mới hoặc tái sử dụng
            "similarity_score": similarity_score,
            "cer": block.get("cer", 0.0),
            "length": block.get("length", 0)
        })
    
    block_df = pd.DataFrame(block_info)
    
    # Tạo biểu đồ phân tích khối (2x2 grid để hiển thị thêm thông tin)
    fig, axs = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Biểu đồ tỷ lệ template mới/tái sử dụng
    template_reuse = block_df['is_template_match'].value_counts()
    axs[0, 0].pie(template_reuse, 
                labels=['Template tái sử dụng', 'Template mới'] if len(template_reuse) > 1 else ['Template tái sử dụng'],
                autopct='%1.1f%%', 
                colors=['lightgreen', 'lightcoral'] if len(template_reuse) > 1 else ['lightgreen'])
    axs[0, 0].set_title("Tỷ lệ tái sử dụng template")
    
    # 2. Biểu đồ phân bố điểm tương đồng (similarity score)
    axs[0, 1].hist(block_df['similarity_score'], bins=20, color='skyblue', edgecolor='black')
    axs[0, 1].set_title("Phân bố điểm tương đồng (Similarity Score)")
    axs[0, 1].set_xlabel("Điểm tương đồng")
    axs[0, 1].set_ylabel("Số lượng khối")
    
    # 3. Biểu đồ phân bố CER
    axs[1, 0].hist(block_df['cer'], bins=20, color='lightgreen', edgecolor='black')
    axs[1, 0].set_title("Phân bố Compression Error Rate (CER)")
    axs[1, 0].set_xlabel("CER")
    axs[1, 0].set_ylabel("Số lượng khối")
    
    # 4. Biểu đồ phân bố kích thước khối
    axs[1, 1].hist(block_df['length'], bins=20, color='orange', edgecolor='black')
    axs[1, 1].set_title("Phân bố kích thước khối")
    axs[1, 1].set_xlabel("Kích thước khối")
    axs[1, 1].set_ylabel("Số lượng khối")
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    if output_prefix:
        plt.savefig(f"{output_prefix}_block_analysis.png", bbox_inches='tight', dpi=300)
    
    plt.close()
    
    # Tạo biểu đồ bổ sung cho phân tích điểm tương đồng
    plt.figure(figsize=(10, 6))
    if len(compression_data.get("similarity_scores", [])) > 0:
        similarity_scores = compression_data.get("similarity_scores", [])
        plt.plot(range(len(similarity_scores)), similarity_scores, marker='o', linestyle='-', color='blue', alpha=0.5)
        plt.axhline(y=compression_data.get("avg_similarity", 0.0), color='r', linestyle='-', label=f'Trung bình: {compression_data.get("avg_similarity", 0.0):.4f}')
        plt.title("Điểm tương đồng theo thời gian")
        plt.xlabel("Số thứ tự template match")
        plt.ylabel("Điểm tương đồng")
        plt.grid(True)
        plt.legend()
        
        if output_prefix:
            plt.savefig(f"{output_prefix}_similarity_trend.png", bbox_inches='tight', dpi=300)
        
    plt.close()

def analyze_parameter_adjustments(compression_data: Dict[str, Any], output_prefix: str = None):
    """
    Phân tích và tạo biểu đồ về sự điều chỉnh tham số kích thước khối
    
    Args:
        compression_data: Dict chứa dữ liệu nén
        output_prefix: Tiền tố cho tên file biểu đồ
    """
    # Trích xuất thông tin điều chỉnh tham số
    compressed_data_json = compression_data.get("compressed_data", {})
    if isinstance(compressed_data_json, str):
        try:
            compressed_data = json.loads(compressed_data_json)
        except json.JSONDecodeError:
            logger.error("Lỗi giải mã JSON từ trường compressed_data")
            return
    else:
        compressed_data = compressed_data_json
    
    block_size_history = compressed_data.get("block_size_history", [])
    
    # Kiểm tra nếu không có lịch sử điều chỉnh
    if not block_size_history:
        logger.warning("Không có lịch sử điều chỉnh kích thước khối để phân tích")
        return
    
    # Trích xuất dữ liệu từ lịch sử điều chỉnh
    blocks = []
    sizes = []
    hit_ratios = []
    cers = []
    similarities = []
    
    for item in block_size_history:
        if isinstance(item, dict):
            # Cấu trúc mới với block_number và các thông số khác
            blocks.append(item.get('block_number', 0))
            sizes.append(item.get('new_size', 0))
            hit_ratios.append(item.get('hit_ratio', 0))
            cers.append(item.get('recent_cer', 0))
            similarities.append(item.get('recent_similarity', 0))
        else:
            # Cấu trúc cũ là tuple (block_number, size)
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                blocks.append(item[0])
                sizes.append(item[1])
    
    # Tạo biểu đồ nhiều panel để phân tích đầy đủ hơn
    fig, axs = plt.subplots(2, 1, figsize=(14, 12), sharex=True)
    
    # 1. Biểu đồ điều chỉnh kích thước khối
    axs[0].plot(blocks, sizes, marker='o', linestyle='-', color='green', label='Kích thước khối')
    axs[0].set_title("Điều chỉnh kích thước khối")
    axs[0].set_ylabel("Kích thước khối")
    axs[0].grid(True)
    axs[0].legend(loc='upper left')
    
    # 2. Biểu đồ tỷ lệ hit và điểm tương đồng theo thời gian
    if hit_ratios and similarities:
        ax_hr = axs[1]
        ax_hr.plot(blocks, hit_ratios, marker='s', linestyle='-', color='blue', label='Tỷ lệ hit')
        ax_hr.set_xlabel("Số khối đã xử lý")
        ax_hr.set_ylabel("Tỷ lệ hit", color='blue')
        ax_hr.tick_params(axis='y', labelcolor='blue')
        ax_hr.set_ylim(0, 1.1)
        
        # Thêm trục thứ hai cho điểm tương đồng
        ax_sim = ax_hr.twinx()
        ax_sim.plot(blocks, similarities, marker='^', linestyle='-', color='red', label='Điểm tương đồng')
        ax_sim.set_ylabel("Điểm tương đồng", color='red')
        ax_sim.tick_params(axis='y', labelcolor='red')
        ax_sim.set_ylim(0, 1.1)
        
        # Thêm legend cho cả hai trục
        lines1, labels1 = ax_hr.get_legend_handles_labels()
        lines2, labels2 = ax_sim.get_legend_handles_labels()
        ax_hr.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    if output_prefix:
        plt.savefig(f"{output_prefix}_block_size_adjustments.png", bbox_inches='tight', dpi=300)
    
    plt.close()

def analyze_memory_usage(compression_data: Dict[str, Any], output_prefix: str = None):
    """
    Phân tích và tạo biểu đồ sử dụng bộ nhớ
    
    Args:
        compression_data: Dict chứa dữ liệu nén
        output_prefix: Tiền tố cho tên file biểu đồ
    """
    # Lấy dữ liệu nén đã xử lý
    compressed_data_field = compression_data.get("compressed_data", {})
    if isinstance(compressed_data_field, str):
        try:
            compressed_data = json.loads(compressed_data_field)
        except json.JSONDecodeError:
            logger.error("Lỗi giải mã JSON từ trường compressed_data")
            return
    else:
        compressed_data = compressed_data_field
        
    # Tính kích thước của dữ liệu gốc và dữ liệu nén
    # Sử dụng cơ chế ước tính nếu không có thông tin chính xác
    total_values = compression_data.get("total_values", 0)
    compression_ratio = compression_data.get("compression_ratio", 1.0)
    
    # Ước tính kích thước (giả định mỗi giá trị là 8 bytes)
    bytes_per_value = 8
    original_size = total_values * bytes_per_value
    compressed_size = original_size / compression_ratio if compression_ratio else original_size
    
    # Chuyển đổi sang KB và MB
    original_kb = original_size / 1024
    compressed_kb = compressed_size / 1024
    
    original_mb = original_kb / 1024
    compressed_mb = compressed_kb / 1024
    
    # Tạo biểu đồ
    fig, axs = plt.subplots(1, 2, figsize=(16, 6))
    
    # 1. Biểu đồ so sánh kích thước bytes
    bars1 = axs[0].bar(["Dữ liệu gốc", "Dữ liệu nén"], 
                      [original_size, compressed_size], 
                      color=['blue', 'green'])
    
    axs[0].set_title("So sánh kích thước dữ liệu (Bytes)")
    axs[0].set_ylabel("Kích thước (Bytes)")
    
    # Thêm số liệu lên biểu đồ
    for bar in bars1:
        height = bar.get_height()
        axs[0].text(bar.get_x() + bar.get_width()/2., height + 0.1,
                  f'{height:.0f}',
                  ha='center', va='bottom', fontweight='bold')
    
    # 2. Biểu đồ so sánh kích thước MB
    bars2 = axs[1].bar(["Dữ liệu gốc", "Dữ liệu nén"], 
                      [original_mb, compressed_mb], 
                      color=['blue', 'green'])
    
    axs[1].set_title("So sánh kích thước dữ liệu (MB)")
    axs[1].set_ylabel("Kích thước (MB)")
    
    # Thêm số liệu lên biểu đồ
    for bar in bars2:
        height = bar.get_height()
        axs[1].text(bar.get_x() + bar.get_width()/2., height + 0.1,
                  f'{height:.4f}',
                  ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    if output_prefix:
        plt.savefig(f"{output_prefix}_memory_usage.png", bbox_inches='tight', dpi=300)
    
    plt.close()

def create_summary_chart(compression_data: Dict[str, Any], output_prefix: str = None):
    """
    Tạo biểu đồ tổng hợp về kết quả nén
    
    Args:
        compression_data: Dict chứa dữ liệu nén
        output_prefix: Tiền tố cho tên file biểu đồ
    """
    # Trích xuất thông tin cần thiết
    total_values = compression_data.get("total_values", 0)
    templates_count = compression_data.get("templates_count", 0)
    blocks_processed = compression_data.get("blocks_processed", 0)
    hit_ratio = compression_data.get("hit_ratio", 0)
    compression_ratio = compression_data.get("compression_ratio", 0)
    avg_cer = compression_data.get("avg_cer", 0.0)
    avg_similarity = compression_data.get("avg_similarity", 0.0)
    cost = compression_data.get("cost", 0.0)
    
    # Tạo biểu đồ tổng hợp với 3x2 grid
    fig, axs = plt.subplots(3, 2, figsize=(18, 15))
    
    # 1. Biểu đồ tỷ lệ nén
    bars1 = axs[0, 0].bar(["Dữ liệu gốc", "Dữ liệu nén"], 
                        [1, 1/compression_ratio if compression_ratio else 0], 
                        color=['blue', 'green'])
    
    # Thêm số liệu lên biểu đồ
    for bar in bars1:
        height = bar.get_height()
        axs[0, 0].text(bar.get_x() + bar.get_width()/2., height + 0.01,
                     f'{height:.4f}',
                     ha='center', va='bottom', fontweight='bold')
    
    axs[0, 0].set_title(f"Tỷ lệ kích thước (Gốc = 1)")
    axs[0, 0].set_ylim(0, 1.2)
    
    # 2. Biểu đồ số lượng khối và template
    bars2 = axs[0, 1].bar(["Templates", "Khối"], 
                        [templates_count, blocks_processed], 
                        color=['orange', 'purple'])
    
    # Thêm số liệu lên biểu đồ
    for bar in bars2:
        height = bar.get_height()
        axs[0, 1].text(bar.get_x() + bar.get_width()/2., height + 0.1,
                     f'{height:.0f}',
                     ha='center', va='bottom', fontweight='bold')
    
    axs[0, 1].set_title("Số lượng template và khối")
    
    # 3. Biểu đồ tỷ lệ hit
    axs[1, 0].pie([hit_ratio, 1-hit_ratio], 
                labels=['Trùng khớp', 'Không trùng khớp'],
                autopct='%1.1f%%', 
                colors=['lightgreen', 'lightcoral'])
    axs[1, 0].set_title(f"Tỷ lệ hit: {hit_ratio:.2f}")
    
    # 4. Biểu đồ CER và điểm tương đồng
    metrics = ['CER', 'Điểm tương đồng', 'Cost']
    values = [avg_cer, avg_similarity, cost]
    colors = ['red', 'blue', 'purple']
    
    bars3 = axs[1, 1].bar(metrics, values, color=colors)
    
    # Thêm số liệu lên biểu đồ
    for bar in bars3:
        height = bar.get_height()
        axs[1, 1].text(bar.get_x() + bar.get_width()/2., height + 0.01,
                     f'{height:.4f}',
                     ha='center', va='bottom', fontweight='bold')
                     
    axs[1, 1].set_title("Các chỉ số chất lượng nén")
    axs[1, 1].set_ylim(0, 1.2)
    
    # 5. Biểu đồ xu hướng nén lý tưởng
    # Tạo biểu đồ mục tiêu lý tưởng (high hit ratio, high similarity, low CER)
    ideal_metrics = ['Tỷ lệ Hit', 'Điểm tương đồng', 'Kháng CER']
    current_values = [hit_ratio, avg_similarity, 1.0 - min(1.0, avg_cer / 0.15)]  # Kháng CER = 1 - normalized CER
    
    # Tạo biểu đồ radar
    angles = np.linspace(0, 2*np.pi, len(ideal_metrics), endpoint=False).tolist()
    angles += angles[:1]  # Đóng vòng tròn
    
    current_values += current_values[:1]  # Đóng vòng tròn cho giá trị
    
    ax_radar = axs[2, 0]
    ax_radar.plot(angles, current_values, 'o-', linewidth=2, color='green')
    ax_radar.fill(angles, current_values, alpha=0.25, color='green')
    ax_radar.set_thetagrids(np.degrees(angles[:-1]), ideal_metrics)
    ax_radar.set_ylim(0, 1)
    ax_radar.set_title("Biểu đồ đánh giá hiệu suất nén")
    ax_radar.grid(True)
    
    # 6. Thông tin tổng hợp
    axs[2, 1].axis('off')  # Tắt trục tọa độ
    
    # Lấy thông tin thời gian từ timestamp nếu có
    timestamp = compression_data.get("timestamp", "N/A")
    device_id = compression_data.get("device_id", "N/A")
    
    # Tạo textbox thông tin
    compression_info = f"""
    THÔNG TIN TỔNG HỢP NÉN
    -----------------------
    ID nén: {compression_data.get('id', 'N/A')}
    Thiết bị: {device_id}
    
    Số lượng giá trị gốc: {total_values}
    Số lượng template: {templates_count}
    Số lượng khối: {blocks_processed}
    
    Tỷ lệ hit: {hit_ratio:.4f}
    Tỷ lệ nén: {compression_ratio:.4f}
    Điểm tương đồng: {avg_similarity:.4f}
    CER: {avg_cer:.4f}
    Cost: {cost:.4f}
    
    Ghi chú: {compression_data.get('notes', 'Sử dụng thuật toán nén đã cải tiến')}
    """
    
    axs[2, 1].text(0.5, 0.5, compression_info, 
                 horizontalalignment='center', 
                 verticalalignment='center', 
                 transform=axs[2, 1].transAxes,
                 fontsize=12,
                 family='monospace',
                 bbox=dict(boxstyle="round,pad=1", facecolor="white", alpha=0.8))
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    if output_prefix:
        plt.savefig(f"{output_prefix}_summary.png", bbox_inches='tight', dpi=300)
    
    plt.close()

def analyze_similarity_metrics(compression_data: Dict[str, Any], output_prefix: str = None):
    """
    Phân tích chi tiết về các chỉ số tương đồng và hiệu suất của thuật toán nén đã cải tiến
    
    Args:
        compression_data: Dict chứa dữ liệu nén
        output_prefix: Tiền tố cho tên file biểu đồ
    """
    # Trích xuất thông tin từ compressed_data
    compressed_data_json = compression_data.get("compressed_data", {})
    if isinstance(compressed_data_json, str):
        try:
            compressed_data = json.loads(compressed_data_json)
        except json.JSONDecodeError:
            logger.error("Lỗi giải mã JSON từ trường compressed_data")
            return
    else:
        compressed_data = compressed_data_json
        
    # Lấy các dữ liệu cần thiết
    similarity_scores = compression_data.get("similarity_scores", [])
    cer_values = compression_data.get("cer_values", [])
    cost_values = compressed_data.get("cost_values", [])
    
    # Kiểm tra nếu không có dữ liệu
    if not similarity_scores and not cer_values:
        logger.warning("Không có dữ liệu về các chỉ số tương đồng để phân tích")
        return
        
    # Tạo biểu đồ phân tích chi tiết
    fig, axs = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Biểu đồ tương quan giữa điểm tương đồng và CER
    if similarity_scores and cer_values:
        # Lấy số lượng mẫu tối thiểu từ hai danh sách
        min_len = min(len(similarity_scores), len(cer_values))
        if min_len > 0:
            x = similarity_scores[:min_len]
            y = cer_values[:min_len]
            
            # Vẽ biểu đồ scatter
            axs[0, 0].scatter(x, y, alpha=0.5, color='blue')
            axs[0, 0].set_title("Tương quan giữa Điểm tương đồng và CER")
            axs[0, 0].set_xlabel("Điểm tương đồng")
            axs[0, 0].set_ylabel("CER")
            
            # Thêm đường xu hướng
            try:
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                axs[0, 0].plot(x, p(x), "r--", alpha=0.8)
                
                # Tính hệ số tương quan
                corr = np.corrcoef(x, y)[0, 1]
                axs[0, 0].text(0.05, 0.95, f"Hệ số tương quan: {corr:.4f}", 
                            transform=axs[0, 0].transAxes,
                            fontsize=10, verticalalignment='top',
                            bbox=dict(boxstyle="round", alpha=0.1))
            except:
                logger.warning("Không thể tính đường xu hướng cho tương quan Similarity-CER")
                
    # 2. Biểu đồ phân bố điểm tương đồng
    if similarity_scores:
        axs[0, 1].hist(similarity_scores, bins=15, color='green', alpha=0.7)
        axs[0, 1].set_title("Phân bố điểm tương đồng")
        axs[0, 1].set_xlabel("Điểm tương đồng")
        axs[0, 1].set_ylabel("Số lượng")
        axs[0, 1].axvline(x=0.4, color='red', linestyle='--', label='Ngưỡng 0.4')
        axs[0, 1].legend()
    
    # 3. Biểu đồ theo dõi Cost function
    if cost_values:
        axs[1, 0].plot(range(len(cost_values)), cost_values, marker='o', linestyle='-', color='purple', alpha=0.6)
        axs[1, 0].set_title("Giá trị Cost function")
        axs[1, 0].set_xlabel("Lần tính cost")
        axs[1, 0].set_ylabel("Cost value")
        axs[1, 0].grid(True)
    
    # 4. Thêm bảng thống kê tóm tắt
    axs[1, 1].axis('off')  # Tắt trục tọa độ
    
    # Tính các thống kê
    sim_stats = {
        'Trung bình': np.mean(similarity_scores) if similarity_scores else "N/A",
        'Trung vị': np.median(similarity_scores) if similarity_scores else "N/A",
        'Min': np.min(similarity_scores) if similarity_scores else "N/A",
        'Max': np.max(similarity_scores) if similarity_scores else "N/A",
        'Std': np.std(similarity_scores) if similarity_scores else "N/A"
    }
    
    cer_stats = {
        'Trung bình': np.mean(cer_values) if cer_values else "N/A",
        'Trung vị': np.median(cer_values) if cer_values else "N/A",
        'Min': np.min(cer_values) if cer_values else "N/A",
        'Max': np.max(cer_values) if cer_values else "N/A",
        'Std': np.std(cer_values) if cer_values else "N/A"
    }
    
    # Tạo bảng thống kê
    stats_text = f"""
    THỐNG KÊ CHI TIẾT CÁC CHỈ SỐ
    ----------------------------
    
    Điểm tương đồng (Similarity):
       Trung bình: {sim_stats['Trung bình'] if isinstance(sim_stats['Trung bình'], str) else f"{sim_stats['Trung bình']:.4f}"}
       Trung vị: {sim_stats['Trung vị'] if isinstance(sim_stats['Trung vị'], str) else f"{sim_stats['Trung vị']:.4f}"}
       Min: {sim_stats['Min'] if isinstance(sim_stats['Min'], str) else f"{sim_stats['Min']:.4f}"}
       Max: {sim_stats['Max'] if isinstance(sim_stats['Max'], str) else f"{sim_stats['Max']:.4f}"}
       Độ lệch chuẩn: {sim_stats['Std'] if isinstance(sim_stats['Std'], str) else f"{sim_stats['Std']:.4f}"}
    
    CER (Compression Error Rate):
       Trung bình: {cer_stats['Trung bình'] if isinstance(cer_stats['Trung bình'], str) else f"{cer_stats['Trung bình']:.4f}"}
       Trung vị: {cer_stats['Trung vị'] if isinstance(cer_stats['Trung vị'], str) else f"{cer_stats['Trung vị']:.4f}"}
       Min: {cer_stats['Min'] if isinstance(cer_stats['Min'], str) else f"{cer_stats['Min']:.4f}"}
       Max: {cer_stats['Max'] if isinstance(cer_stats['Max'], str) else f"{cer_stats['Max']:.4f}"}
       Độ lệch chuẩn: {cer_stats['Std'] if isinstance(cer_stats['Std'], str) else f"{cer_stats['Std']:.4f}"}
       
    Mẫu dữ liệu:
       Số mẫu Similarity: {len(similarity_scores)}
       Số mẫu CER: {len(cer_values)}
       Số mẫu Cost: {len(cost_values)}
    """
    
    axs[1, 1].text(0.5, 0.5, stats_text, 
                 horizontalalignment='center', 
                 verticalalignment='center', 
                 transform=axs[1, 1].transAxes,
                 fontsize=10,
                 family='monospace',
                 bbox=dict(boxstyle="round,pad=1", facecolor="white", alpha=0.8))
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    if output_prefix:
        plt.savefig(f"{output_prefix}_similarity_metrics.png", bbox_inches='tight', dpi=300)
    
    plt.close()

def create_pattern_recognition_chart(data, compression_result, output_dir):
    """
    Tạo biểu đồ nhận dạng mẫu (Pattern Recognition Chart)
    
    Args:
        data: Dữ liệu gốc
        compression_result: Kết quả từ quá trình nén
        output_dir: Thư mục đầu ra cho biểu đồ
        
    Returns:
        str: Đường dẫn đến biểu đồ đã tạo
    """
    try:
        # Tạo thư mục đầu ra nếu không tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Lấy thông tin từ compression_result
        templates = compression_result.get('templates', {})
        encoded_stream = compression_result.get('encoded_stream', [])
        
        # Lấy thông tin thời gian
        time_info = extract_time_info(compression_result)
        
        # Tạo đường dẫn file
        pattern_recognition_chart = os.path.join(output_dir, 'template_recognition.png')
        
        # Chuẩn bị dữ liệu để vẽ
        primary_dim = None
        dimensions = {}
        
        # Phát hiện các chiều dữ liệu có sẵn
        if len(data) > 0 and isinstance(data[0], dict):
            # Dữ liệu đa chiều, kiểm tra các chiều có sẵn
            for record in data:
                for dim, value in record.items():
                    if value is not None:
                        dimensions[dim] = dimensions.get(dim, 0) + 1
            
            if dimensions:
                # Sắp xếp theo số lượng giá trị giảm dần
                sorted_dims = sorted(dimensions.items(), key=lambda x: x[1], reverse=True)
                primary_dim = sorted_dims[0][0]
        
        # Trích xuất và chuẩn bị dữ liệu để vẽ
        if len(data) > 0 and isinstance(data[0], dict):
            # Dữ liệu đa chiều
            primary_data = [record.get(primary_dim, None) for record in data]
            # Loại bỏ các giá trị None
            primary_data = [val for val in primary_data if val is not None]
        else:
            # Dữ liệu một chiều
            primary_data = data
        
        # Vẽ biểu đồ nhận dạng mẫu
        plt.figure(figsize=(15, 8))
        
        # Vẽ dữ liệu gốc
        plt.plot(primary_data, color='blue', alpha=0.5, label='Dữ liệu gốc')
        
        # Lấy giới hạn dữ liệu để tính toán vị trí nhãn
        y_min = min(primary_data) if primary_data else 0
        y_max = max(primary_data) if primary_data else 100
        y_range = y_max - y_min
        
        # Đánh dấu các template được sử dụng
        # Tạo một từ điển để theo dõi các template đã thấy
        template_seen = {}
        
        for block in encoded_stream:
            template_id = block.get('template_id')
            start_idx = block.get('start_idx')
            length = block.get('length')
            
            if template_id is not None and start_idx is not None and length is not None:
                # Tìm dải y cho khu vực này
                if start_idx + length <= len(primary_data):
                    segment_data = primary_data[start_idx:start_idx + length]
                    segment_min = min(segment_data) if segment_data else y_min
                    segment_max = max(segment_data) if segment_data else y_max
                    segment_middle = (segment_min + segment_max) / 2
                else:
                    segment_middle = (y_min + y_max) / 2
                
                # Chọn màu cho template này
                template_color = f'C{template_id % 10}'
                
                # Đánh dấu vùng sử dụng template với alpha thấp hơn
                rect = plt.axvspan(start_idx, start_idx + length, 
                                 color=template_color, alpha=0.3)
                
                # Thêm nhãn ở giữa vùng template với font size lớn hơn và nền màu
                middle_x = start_idx + length/2
                
                # Thêm một đường dấu chấm để nhấn mạnh vùng template
                if length > 5:  # Chỉ vẽ đường đánh dấu nếu khối đủ lớn
                    plt.axvline(x=middle_x, color=template_color, linestyle='--', alpha=0.7)
                
                # Đảm bảo vị trí nhãn ở giữa dữ liệu và không bị che
                template_label = f'T{template_id}'
                
                # Thêm nhãn template vào vị trí trung tâm khối với text box nổi bật
                text_y_position = segment_middle
                
                # Thêm nhãn template với khung nền
                plt.text(middle_x, text_y_position, template_label,
                         horizontalalignment='center', verticalalignment='center',
                         fontsize=11, fontweight='bold', color='black',
                         bbox=dict(facecolor=template_color, alpha=0.7, boxstyle='round,pad=0.5', 
                                  edgecolor='black', linewidth=1))
                
                # Theo dõi các template đã thấy để không lặp lại trong legend
                template_seen[template_id] = template_color
        
        # Cập nhật tiêu đề và nhãn trục không nhấn mạnh vào một chiều cụ thể
        title = 'Nhận dạng mẫu và phân khúc dữ liệu'
        if time_info:
            title += time_info
        plt.title(title)
        plt.xlabel('Chỉ số mẫu')
        plt.ylabel('Giá trị dữ liệu')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(pattern_recognition_chart, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ nhận dạng mẫu: {pattern_recognition_chart}")
        return pattern_recognition_chart
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ nhận dạng mẫu: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def create_block_size_chart(compression_result, output_dir):
    """
    Tạo biểu đồ điều chỉnh kích thước khối (Block Size Adjustment Chart)
    
    Args:
        compression_result: Kết quả từ quá trình nén
        output_dir: Thư mục đầu ra cho biểu đồ
        
    Returns:
        str: Đường dẫn đến biểu đồ đã tạo, hoặc None nếu không có dữ liệu block_size_history
    """
    try:
        # Tạo thư mục đầu ra nếu không tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Lấy thông tin từ compression_result
        block_size_history = compression_result.get('block_size_history', [])
        
        if not block_size_history:
            logger.warning("Không có dữ liệu lịch sử kích thước khối để tạo biểu đồ")
            return None
            
        # Lấy thông tin thời gian
        time_info = extract_time_info(compression_result)
            
        # Tạo đường dẫn file
        block_size_chart = os.path.join(output_dir, 'block_size_adjustment.png')
        
        plt.figure(figsize=(12, 6))
        
        # Vẽ lịch sử thay đổi kích thước khối
        block_sizes = [b.get('new_size', 0) for b in block_size_history]
        plt.plot(block_sizes, marker='o', linestyle='-', color='green', alpha=0.7)
        
        # Vẽ ngưỡng min và max từ compression_result
        min_size = compression_result.get('min_block_size', 0)
        max_size = compression_result.get('max_block_size', 0)
        
        # Nếu không có trong compression_result, thử lấy từ block đầu tiên
        if (min_size == 0 or max_size == 0) and block_size_history:
            min_size = block_size_history[0].get('min_block_size', 30)  # Giá trị mặc định
            max_size = block_size_history[0].get('max_block_size', 120)  # Giá trị mặc định
        
        if min_size > 0:
            plt.axhline(y=min_size, color='red', linestyle='--', label=f'Min: {min_size}')
        if max_size > 0:
            plt.axhline(y=max_size, color='blue', linestyle='--', label=f'Max: {max_size}')
        
        # Thêm thông tin thời gian vào tiêu đề nếu có
        title = 'Điều chỉnh kích thước khối theo thời gian'
        if time_info:
            title += time_info
            
        plt.title(title)
        plt.xlabel('Block index')
        plt.ylabel('Kích thước khối')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(block_size_chart, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ điều chỉnh kích thước khối: {block_size_chart}")
        return block_size_chart
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ điều chỉnh kích thước khối: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def create_size_comparison_chart(data, compression_result, output_dir):
    """
    Tạo biểu đồ so sánh kích thước (Size Comparison Chart)
    
    Args:
        data: Dữ liệu gốc
        compression_result: Kết quả từ quá trình nén
        output_dir: Thư mục đầu ra cho biểu đồ
        
    Returns:
        str: Đường dẫn đến biểu đồ đã tạo
    """
    try:
        # Tạo thư mục đầu ra nếu không tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Lấy thông tin từ compression_result
        templates = compression_result.get('templates', {})
        encoded_stream = compression_result.get('encoded_stream', [])
        
        # Lấy thông tin thời gian
        time_info = extract_time_info(compression_result)
        
        # Tạo đường dẫn file
        size_comparison_chart = os.path.join(output_dir, 'size_comparison.png')
        
        # Tính kích thước chính xác hơn
        # Tính kích thước của dữ liệu gốc (json serialized)
        original_size_bytes = sum(len(json.dumps(item)) for item in data)
        
        # Tính kích thước sau khi nén: gồm templates + encoded_stream
        templates_size = len(json.dumps(templates))
        encoded_stream_size = len(json.dumps(encoded_stream))
        compressed_size_bytes = templates_size + encoded_stream_size
        
        # Cập nhật tỷ lệ nén thực tế
        actual_compression_ratio = original_size_bytes / compressed_size_bytes if compressed_size_bytes > 0 else 1.0
        
        plt.figure(figsize=(10, 6))
        
        # Vẽ biểu đồ cột so sánh kích thước
        sizes = [original_size_bytes, compressed_size_bytes]
        labels = ['Dữ liệu gốc', 'Dữ liệu nén']
        colors = ['blue', 'green']
        
        plt.bar(labels, sizes, color=colors, alpha=0.7)
        
        # Thêm nhãn giá trị lên cột (định dạng theo KB nếu lớn)
        for i, v in enumerate(sizes):
            if v > 1024:
                plt.text(i, v + 0.1, f"{v/1024:.1f} KB", ha='center', va='bottom')
            else:
                plt.text(i, v + 0.1, f"{v:,} bytes", ha='center', va='bottom')
        
        # Thêm thông tin tỷ lệ nén
        plt.text(0.5, 0.9, f"Tỷ lệ nén: {actual_compression_ratio:.2f}x", 
                transform=plt.gca().transAxes, ha='center', va='center',
                bbox=dict(facecolor='white', alpha=0.8))
        
        # Thêm thông tin thời gian vào tiêu đề nếu có
        title = 'So sánh kích thước dữ liệu trước và sau khi nén'
        if time_info:
            title += time_info
            
        plt.title(title)
        plt.ylabel('Kích thước (bytes)')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(size_comparison_chart, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ so sánh kích thước: {size_comparison_chart}")
        return size_comparison_chart
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ so sánh kích thước: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def create_visualizations(data, compression_result, output_dir='visualization', max_points=5000, sampling_method='adaptive', num_chunks=0):
    """
    Tạo các biểu đồ trực quan hóa kết quả nén
    
    Args:
        data: Dữ liệu gốc
        compression_result: Kết quả từ quá trình nén
        output_dir: Thư mục đầu ra cho biểu đồ
        max_points: Số điểm tối đa để hiển thị trên biểu đồ
        sampling_method: Phương pháp lấy mẫu dữ liệu cho biểu đồ
        num_chunks: Số chunks để chia dữ liệu khi lấy mẫu
    
    Returns:
        list: Danh sách đường dẫn đến các biểu đồ đã tạo
    """
    try:
        # Tạo thư mục đầu ra nếu không tồn tại
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Đã tạo thư mục đầu ra: {output_dir}")
        
        # Danh sách lưu các đường dẫn đến biểu đồ
        chart_files = []
        
        # 1. Tạo biểu đồ nhận dạng mẫu
        pattern_chart = create_pattern_recognition_chart(data, compression_result, output_dir)
        if pattern_chart:
            chart_files.append(pattern_chart)
        
        # 2. Tạo biểu đồ điều chỉnh kích thước khối
        block_chart = create_block_size_chart(compression_result, output_dir)
        if block_chart:
            chart_files.append(block_chart)
        
        # 3. Tạo biểu đồ so sánh kích thước
        size_chart = create_size_comparison_chart(data, compression_result, output_dir)
        if size_chart:
            chart_files.append(size_chart)
        
        logger.info(f"Tổng cộng đã tạo {len(chart_files)} biểu đồ trực quan hóa")
        return chart_files
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ trực quan hóa: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def create_analysis_visualizations(compression_id: int):
    """
    Tạo tất cả các biểu đồ phân tích cho một bản ghi nén
    
    Args:
        compression_id: ID bản ghi nén
    """
    try:
        # Tạo thư mục lưu biểu đồ
        output_dir = f"compression_analysis_{compression_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Kết nối DB và lấy dữ liệu
        engine = get_database_connection()
        compression_data = get_compression_data(engine, compression_id)
        
        logger.info(f"Bắt đầu tạo biểu đồ phân tích cho bản ghi nén ID: {compression_id}")
        
        # Tạo tiền tố cho tên file biểu đồ
        output_prefix = f"{output_dir}/compression_{compression_id}"
        
        # Tạo các biểu đồ phân tích
        analyze_compression_ratio(compression_data, output_prefix)
        analyze_templates(compression_data, output_prefix)
        analyze_blocks(compression_data, output_prefix)
        analyze_parameter_adjustments(compression_data, output_prefix)
        analyze_memory_usage(compression_data, output_prefix)
        create_summary_chart(compression_data, output_prefix)
        analyze_similarity_metrics(compression_data, output_prefix)
        
        # Tạo các biểu đồ trực quan hóa
        visualizations = create_visualizations(compression_data.get('original_data', []), compression_data)
        
        logger.info(f"Đã tạo các biểu đồ phân tích và lưu vào thư mục: {output_dir}")
        
        return output_dir
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ phân tích: {str(e)}")
        raise

def compare_compression_results(compression_ids: List[int], output_dir: str = None):
    """
    So sánh kết quả nén giữa nhiều bản nén khác nhau
    
    Args:
        compression_ids: Danh sách các ID bản ghi nén cần so sánh
        output_dir: Thư mục đầu ra để lưu biểu đồ
    
    Returns:
        Đường dẫn đến thư mục chứa biểu đồ so sánh
    """
    try:
        # Kiểm tra nếu không có ID nào được cung cấp
        if not compression_ids:
            logger.error("Không có ID bản ghi nén nào được cung cấp để so sánh")
            return None
            
        # Tạo thư mục đầu ra nếu chưa có
        if not output_dir:
            output_dir = f"comparison_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Kết nối DB
        engine = get_database_connection()
        
        # Lấy dữ liệu cho tất cả các bản ghi nén
        compression_data_list = []
        for comp_id in compression_ids:
            try:
                data = get_compression_data(engine, comp_id)
                compression_data_list.append(data)
                logger.info(f"Đã lấy dữ liệu nén ID: {comp_id}")
            except Exception as e:
                logger.warning(f"Không thể lấy dữ liệu cho ID {comp_id}: {str(e)}")
        
        # Kiểm tra nếu không thể lấy được bất kỳ dữ liệu nào
        if not compression_data_list:
            logger.error("Không thể lấy dữ liệu cho bất kỳ ID nào đã cung cấp")
            return None
            
        # Chuẩn bị dữ liệu để so sánh
        comp_ids = []
        hit_ratios = []
        comp_ratios = []
        template_counts = []
        avg_similarities = []
        avg_cers = []
        costs = []
        
        for data in compression_data_list:
            comp_id = data.get("id", "N/A")
            comp_ids.append(str(comp_id))
            hit_ratios.append(data.get("hit_ratio", 0))
            comp_ratios.append(data.get("compression_ratio", 0))
            template_counts.append(data.get("templates_count", 0))
            avg_similarities.append(data.get("avg_similarity", 0))
            avg_cers.append(data.get("avg_cer", 0))
            costs.append(data.get("cost", 0))
        
        # 1. Tạo biểu đồ so sánh tỷ lệ hit và tỷ lệ nén
        plt.figure(figsize=(14, 8))
        
        # Tính toán số lượng trụ cột và chiều rộng
        x = np.arange(len(comp_ids))
        width = 0.35
        
        # Trụ cột cho tỷ lệ hit
        plt.bar(x - width/2, hit_ratios, width, label='Tỷ lệ hit', color='skyblue')
        
        # Tạo trục y thứ hai cho tỷ lệ nén
        ax2 = plt.twinx()
        ax2.bar(x + width/2, comp_ratios, width, label='Tỷ lệ nén', color='lightgreen')
        
        # Thiết lập trục x
        plt.xticks(x, comp_ids, rotation=45)
        
        # Thêm nhãn và tiêu đề
        plt.xlabel('ID bản ghi nén')
        plt.ylabel('Tỷ lệ hit')
        ax2.set_ylabel('Tỷ lệ nén')
        
        # Thêm tiêu đề
        plt.title('So sánh tỷ lệ hit và tỷ lệ nén')
        
        # Thêm legend
        plt.legend(loc='upper left')
        ax2.legend(loc='upper right')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/comparison_hit_comp_ratio.png", bbox_inches='tight', dpi=300)
        plt.close()
        
        # 2. Biểu đồ so sánh chất lượng nén (CER và Similarity)
        plt.figure(figsize=(14, 8))
        
        # Trụ cột cho CER
        plt.bar(x - width/2, avg_cers, width, label='Trung bình CER', color='salmon')
        
        # Trục y thứ hai cho Similarity
        ax2 = plt.twinx()
        ax2.bar(x + width/2, avg_similarities, width, label='Trung bình Similarity', color='skyblue')
        
        # Thiết lập trục x
        plt.xticks(x, comp_ids, rotation=45)
        
        # Thêm nhãn và tiêu đề
        plt.xlabel('ID bản ghi nén')
        plt.ylabel('CER')
        ax2.set_ylabel('Similarity')
        
        # Thêm tiêu đề
        plt.title('So sánh chất lượng nén (CER và Similarity)')
        
        # Thêm legend
        plt.legend(loc='upper left')
        ax2.legend(loc='upper right')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/comparison_cer_similarity.png", bbox_inches='tight', dpi=300)
        plt.close()
        
        # 3. Biểu đồ so sánh số lượng template và cost
        plt.figure(figsize=(14, 8))
        
        # Trụ cột cho template count
        plt.bar(x - width/2, template_counts, width, label='Số lượng template', color='orchid')
        
        # Trục y thứ hai cho cost
        ax2 = plt.twinx()
        ax2.bar(x + width/2, costs, width, label='Cost', color='gold')
        
        # Thiết lập trục x
        plt.xticks(x, comp_ids, rotation=45)
        
        # Thêm nhãn và tiêu đề
        plt.xlabel('ID bản ghi nén')
        plt.ylabel('Số lượng template')
        ax2.set_ylabel('Cost')
        
        # Thêm tiêu đề
        plt.title('So sánh số lượng template và cost')
        
        # Thêm legend
        plt.legend(loc='upper left')
        ax2.legend(loc='upper right')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/comparison_templates_cost.png", bbox_inches='tight', dpi=300)
        plt.close()
        
        # 4. Biểu đồ radar cho so sánh tổng thể
        # Tạo dữ liệu radar chart
        fig = plt.figure(figsize=(14, 10))
        
        # Các chỉ số để so sánh
        metrics = ['Tỷ lệ hit', 'Tỷ lệ nén', 'Điểm tương đồng', 'Kháng CER', 'Kháng Cost']
        
        # Chuẩn hóa dữ liệu cho radar chart
        # Đảm bảo dữ liệu nằm trong khoảng [0, 1]
        radar_data = []
        for i, _ in enumerate(comp_ids):
            # Chuẩn hóa CER và Cost để có giá trị cao = tốt
            normalized_cer = 1.0 - min(1.0, avg_cers[i] / 0.15)  # Giả sử 0.15 là ngưỡng tối đa cho CER
            normalized_cost = 1.0 - min(1.0, costs[i])  # Giả sử cost đã nằm trong [0, 1]
            
            # Chuẩn hóa tỷ lệ nén để phù hợp với thang đo radar
            normalized_comp_ratio = min(1.0, comp_ratios[i] / 10.0)  # Giả sử 10x là tỷ lệ nén tốt nhất
            
            radar_values = [
                hit_ratios[i],                # Tỷ lệ hit
                normalized_comp_ratio,        # Tỷ lệ nén chuẩn hóa
                avg_similarities[i],          # Điểm tương đồng
                normalized_cer,               # Kháng CER
                normalized_cost               # Kháng Cost
            ]
            radar_data.append(radar_values)
        
        # Góc cho mỗi trục
        angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
        
        # Đóng vòng tròn
        angles += angles[:1]
        
        # Tạo biểu đồ con
        ax = plt.subplot(111, polar=True)
        
        # Thêm dữ liệu cho mỗi bản ghi nén
        for i, values in enumerate(radar_data):
            values_closed = values + values[:1]  # Đóng vòng tròn cho giá trị
            ax.plot(angles, values_closed, linewidth=2, label=f'ID {comp_ids[i]}')
            ax.fill(angles, values_closed, alpha=0.1)
        
        # Thiết lập nhãn cho mỗi trục
        ax.set_thetagrids(np.degrees(angles[:-1]), metrics)
        
        # Thiết lập giới hạn trục r
        ax.set_ylim(0, 1)
        
        # Thêm tiêu đề
        plt.title('So sánh hiệu suất nén tổng thể')
        
        # Thêm legend
        plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/comparison_radar.png", bbox_inches='tight', dpi=300)
        plt.close()
        
        # 5. Bảng so sánh chi tiết dạng văn bản
        # Tạo bảng thông tin chi tiết
        comparison_table = pd.DataFrame({
            'ID': comp_ids,
            'Tỷ lệ hit': hit_ratios,
            'Tỷ lệ nén': comp_ratios,
            'Số template': template_counts,
            'Avg Similarity': avg_similarities,
            'Avg CER': avg_cers,
            'Cost': costs
        })
        
        # Lưu bảng thành file CSV
        comparison_table.to_csv(f"{output_dir}/comparison_details.csv", index=False)
        
        # Tạo một bản tóm tắt dạng HTML để dễ xem
        html_table = comparison_table.to_html(index=False)
        with open(f"{output_dir}/comparison_details.html", 'w') as f:
            f.write(f"""
            <html>
            <head>
                <title>Bảng so sánh chi tiết</title>
                <style>
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ text-align: left; padding: 8px; border: 1px solid #ddd; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    th {{ background-color: #4CAF50; color: white; }}
                </style>
            </head>
            <body>
                <h1>So sánh chi tiết các bản ghi nén</h1>
                {html_table}
                <p>Tạo lúc: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </body>
            </html>
            """)
        
        logger.info(f"Đã tạo các biểu đồ so sánh và lưu vào thư mục: {output_dir}")
        return output_dir
        
    except Exception as e:
        logger.error(f"Lỗi khi so sánh kết quả nén: {str(e)}")
        return None

def extract_time_info(compression_result):
    """
    Trích xuất thông tin thời gian từ kết quả nén
    
    Args:
        compression_result: Kết quả từ quá trình nén
        
    Returns:
        str: Chuỗi thông tin thời gian đã định dạng (hoặc chuỗi rỗng nếu không có)
    """
    # Trích xuất thông tin thời gian
    time_range = None
    # Kiểm tra các vị trí có thể chứa thông tin time_range
    if 'time_range' in compression_result:
        time_range = compression_result['time_range']
    elif 'metadata' in compression_result and 'time_range' in compression_result['metadata']:
        time_range = compression_result['metadata']['time_range']
    
    # Xử lý time_range nếu có
    time_info = ""
    if time_range:
        # Nếu time_range là chuỗi định dạng "[start,end]"
        if isinstance(time_range, str) and time_range.startswith('[') and time_range.endswith(']'):
            time_parts = time_range[1:-1].split(',')
            if len(time_parts) == 2:
                start_time = time_parts[0].strip('"\'')
                end_time = time_parts[1].strip('"\'')
                time_info = f" - Từ {start_time} đến {end_time}"
        else:
            # Nếu time_range là một đối tượng có thuộc tính lower và upper
            try:
                if hasattr(time_range, 'lower') and hasattr(time_range, 'upper'):
                    start_time = time_range.lower.isoformat() if time_range.lower else "N/A"
                    end_time = time_range.upper.isoformat() if time_range.upper else "N/A"
                    time_info = f" - Từ {start_time} đến {end_time}"
            except:
                # Sử dụng chuỗi hoặc đối tượng nguyên bản nếu không thể trích xuất
                time_info = f" - Phạm vi thời gian: {str(time_range)}"
    
    return time_info

def main():
    """Hàm chính"""
    try:
        # Kiểm tra tham số dòng lệnh
        if len(sys.argv) < 2:
            print("Sử dụng: python visualization_analyzer.py <compression_id> [<compression_id2> ...]")
            print("hoặc:    python visualization_analyzer.py --compare <compression_id1> <compression_id2> [<compression_id3> ...]")
            print("Ví dụ:   python visualization_analyzer.py 1")
            print("Ví dụ:   python visualization_analyzer.py --compare 1 2 3")
            sys.exit(1)
            
        # Xác định chế độ hoạt động
        if sys.argv[1] == "--compare" and len(sys.argv) > 2:
            # Chế độ so sánh
            compression_ids = []
            for i in range(2, len(sys.argv)):
                try:
                    compression_id = int(sys.argv[i])
                    compression_ids.append(compression_id)
                except ValueError:
                    print(f"Lỗi: ID '{sys.argv[i]}' phải là số nguyên")
                    sys.exit(1)
            
            # Thực hiện so sánh
            output_dir = compare_compression_results(compression_ids)
            if output_dir:
                print(f"Đã tạo các biểu đồ so sánh và lưu vào thư mục: {output_dir}")
            else:
                print("Không thể tạo biểu đồ so sánh.")
                sys.exit(1)
        else:
            # Chế độ phân tích đơn lẻ
            try:
                compression_id = int(sys.argv[1])
            except ValueError:
                print("Lỗi: ID phải là số nguyên")
                sys.exit(1)
                
            # Tạo biểu đồ phân tích
            output_dir = create_analysis_visualizations(compression_id)
            print(f"Đã tạo các biểu đồ phân tích và lưu vào thư mục: {output_dir}")
            
    except Exception as e:
        logger.error(f"Lỗi: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
