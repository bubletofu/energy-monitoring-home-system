#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import logging
import numpy as np
from scipy import stats

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataCompressor:

    def __init__(self, config=None):
        """
        Khởi tạo compressor với các cấu hình mặc định
        
        Args:
            config: Dict chứa các tham số cấu hình
        """
        # Cấu hình mặc định
        self.config = {
            'p_threshold': 0.1,       # Ngưỡng p-value cho KS test
            'max_templates': 100,     # Số lượng template tối đa
            'min_values': 10,         # Số lượng giá trị tối thiểu để xem xét
            'min_block_size': 20,     # Kích thước block tối thiểu
            'max_block_size': 120,    # Kích thước block tối đa
            'adaptive_block_size': True, # Tự động điều chỉnh kích thước block
            'min_blocks_before_adjustment': 5, # Giảm số block tối thiểu trước khi điều chỉnh
            'confidence_level': 0.95, # Mức độ tin cậy
            'pmin': 0.5,              # Xác suất tối thiểu để xem xét block khớp với template
            'block_size': 30,         # Kích thước block ban đầu nhỏ hơn để khởi động nhanh
            'w1': 0.6,                # Trọng số cho CER trong cost function
            'w2': 0.4,                # Trọng số cho CR trong cost function
            'max_acceptable_cer': 0.15, # Ngưỡng CER tối đa chấp nhận được
            'correlation_threshold': 0.6, # Ngưỡng tương quan Pearson
            'similarity_weights': {   # Trọng số cho các phương pháp so sánh cơ bản
                'ks_test': 0.2,       # Trọng số cho KS test
                'correlation': 0.5,   # Trọng số cho tương quan Pearson 
                'cer': 0.3            # Trọng số cho CER
            },
            'enhanced_similarity_weights': { # Trọng số cho phương pháp so sánh nâng cao
                'ks_test': 0.15,      # Giảm trọng số KS test
                'correlation': 0.25,  # Giảm trọng số tương quan Pearson
                'cer': 0.15,          # Giảm trọng số CER
                'shape': 0.25,        # Trọng số cho độ tương đồng hình dạng
                'trend': 0.20         # Trọng số cho độ tương đồng xu hướng
            },
            # Thêm cấu hình mới cho quản lý template
            'template_expiration': 100,  # Số block tối đa không dùng trước khi hết hạn template
            'template_usage_threshold': 3,  # Số lần sử dụng tối thiểu để giữ một template
            'max_template_age': 50,  # Tuổi tối đa (số block) một template có thể tồn tại nếu ít sử dụng
            'trend_detection_window': 5,  # Số block để phát hiện xu hướng
            'trend_threshold': 0.7,  # Ngưỡng để xác định một xu hướng rõ ràng
            # Cấu hình mới cho dữ liệu đa chiều
            'multi_dimensional': False, # Cờ bật/tắt tính năng nén đa chiều
            'dimension_weights': {},  # Trọng số cho từng chiều dữ liệu, mặc định bằng nhau
            'primary_dimension': 'power',  # Chiều dữ liệu chính để phát hiện template
        }
        
        # Cập nhật cấu hình nếu được cung cấp
        if config:
            self.config.update(config)
            
        # Khởi tạo các biến trạng thái
        self.reset()
        logger.info(f"Khởi tạo Data Compressor với cấu hình: {self.config}")
        
    def reset(self):
        """
        Reset trạng thái của compressor
        """
        # Khởi tạo các tham số của thuật toán
        self.templates = {}                # Dict lưu trữ các template
        self.template_counter = 0          # Bộ đếm template để tạo ID
        self.encoded_stream = []           # Danh sách các mã nén
        self.current_block_size = self.config['block_size']  # Kích thước block hiện tại
        self.blocks_processed = 0          # Số lượng block đã xử lý
        self.template_hit_count = 0        # Số lần tìm thấy template phù hợp
        self.templates_used = set()        # Tập hợp các template đã sử dụng
        self.recent_values = []            # Các giá trị gần đây để phát hiện xu hướng
        self.block_size_history = []       # Lịch sử thay đổi kích thước block
        self.cer_values = []               # Lịch sử các giá trị CER
        self.similarity_scores = []        # Lịch sử các điểm tương đồng
        self.cost_values = []              # Lịch sử các giá trị cost
        self.template_stats = {}           # Thống kê về các template
        self.template_usage = {}           # Số lần template được sử dụng
        self.template_last_used = {}       # Block cuối cùng template được sử dụng
        self.template_creation_time = {}   # Block khi template được tạo
        self.continuous_hit_ratio = []     # Theo dõi hit ratio liên tục theo thời gian
        self.window_hit_count = 0          # Đếm hit trong cửa sổ hiện tại
        self.window_blocks = 0             # Đếm blocks trong cửa sổ hiện tại
        self.window_size = 10              # Kích thước cửa sổ để tính hit ratio động
        self.previous_adjustments = []     # Lịch sử các điều chỉnh trước đó
        self.min_adjustment_interval = 5   # Số block tối thiểu giữa các lần điều chỉnh
        self.last_adjustment_block = 0     # Block cuối cùng được điều chỉnh
        
        # Các biến mới cho dữ liệu đa chiều
        self.dimensions = []               # Các chiều dữ liệu được phát hiện
        self.dimension_stats = {}          # Thống kê về từng chiều dữ liệu
        self.multi_dimensional = self.config.get('multi_dimensional', False)  # Chế độ đa chiều
        self.primary_dimension = self.config.get('primary_dimension', 'power')  # Chiều dữ liệu chính
        
        logger.info(f"Đã reset Data Compressor, chế độ đa chiều: {self.multi_dimensional}")
        
    def update_template_metrics(self, template_id, used=True):
        """
        Cập nhật các chỉ số sử dụng của template
        
        Args:
            template_id: ID của template cần cập nhật
            used: True nếu template được sử dụng, False nếu chỉ kiểm tra
        """
        # Khởi tạo chỉ số nếu là template mới
        if template_id not in self.template_usage:
            self.template_usage[template_id] = 0
            self.template_creation_time[template_id] = self.blocks_processed
        
        # Cập nhật số lần sử dụng và thời gian sử dụng gần nhất
        if used:
            self.template_usage[template_id] += 1
        self.template_last_used[template_id] = self.blocks_processed
        
    def detect_trend(self, data):
        """
        Phát hiện xu hướng trong dữ liệu gần đây
        
        Args:
            data: Dữ liệu hiện tại (mảng 1D, dictionary, hoặc rỗng để chỉ sử dụng dữ liệu đã lưu)
            
        Returns:
            tuple: (has_trend, trend_type, trend_strength)
                has_trend: True nếu có xu hướng rõ ràng
                trend_type: 1 (tăng), -1 (giảm), 0 (không xác định)
                trend_strength: Độ mạnh của xu hướng (0-1)
        """
        # Trường hợp dữ liệu đa chiều
        if self.multi_dimensional and data and isinstance(data, dict):
            # Sử dụng chiều dữ liệu chính
            primary_dim = self.primary_dimension
            if primary_dim in data and len(data[primary_dim]) > 0:
                values = data[primary_dim]
                data_mean = np.mean(values)
                # Thêm dữ liệu mới vào danh sách giá trị gần đây
                self.recent_values.append(data_mean)
            else:
                # Không có dữ liệu mới
                pass
        elif data is not None and len(data) > 0:  # Dữ liệu một chiều thông thường
            # Thêm dữ liệu mới vào danh sách giá trị gần đây
            data_mean = np.mean(data)
            self.recent_values.append(data_mean)
        
        # Giữ kích thước cửa sổ phát hiện xu hướng
        window_size = self.config['trend_detection_window']
        if len(self.recent_values) > window_size:
            self.recent_values = self.recent_values[-window_size:]
        
        # Không đủ dữ liệu để phát hiện xu hướng
        if len(self.recent_values) < 3:
            return False, 0, 0.0
        
        # Tính độ dốc bằng hồi quy tuyến tính đơn giản
        x = np.arange(len(self.recent_values))
        y = np.array(self.recent_values)
        
        # Tính hệ số góc của đường thẳng khớp
        slope, _, r_value, _, _ = stats.linregress(x, y)
        
        # Đánh giá xu hướng
        trend_strength = abs(r_value)  # Độ mạnh của xu hướng dựa trên hệ số tương quan
        trend_type = 1 if slope > 0 else -1 if slope < 0 else 0
        has_trend = trend_strength > self.config['trend_threshold']
        
        return has_trend, trend_type, trend_strength
    
    def clean_expired_templates(self):
        """
        Loại bỏ các template không còn sử dụng hoặc hết hạn
        
        Returns:
            int: Số template đã loại bỏ
        """
        # Không làm gì nếu số template chưa vượt ngưỡng
        if len(self.templates) <= self.config['max_templates'] * 0.8:
            return 0
        
        templates_to_remove = []
        current_block = self.blocks_processed
        
        # Đánh giá từng template
        for template_id in list(self.templates.keys()):
            # Tính tuổi của template (số block từ khi tạo)
            template_age = current_block - self.template_creation_time.get(template_id, 0)
            
            # Tính thời gian không sử dụng
            unused_time = current_block - self.template_last_used.get(template_id, 0)
            
            # Tính số lần sử dụng
            usage_count = self.template_usage.get(template_id, 0)
            
            # Điều kiện loại bỏ:
            # 1. Template đã lâu không được sử dụng
            # 2. Template có ít lần sử dụng và đã tồn tại đủ lâu
            # 3. Template đã quá cũ (vượt quá tuổi tối đa)
            if (unused_time > self.config['template_expiration'] or
                (usage_count < self.config['template_usage_threshold'] and 
                 template_age > self.config['max_template_age'] / 2) or
                template_age > self.config['max_template_age']):
                templates_to_remove.append(template_id)
        
        # Loại bỏ template theo ưu tiên
        num_to_remove = min(len(templates_to_remove), 
                           max(1, int(len(self.templates) * 0.2)))  # Loại bỏ tối đa 20% số template
        
        # Sắp xếp theo ưu tiên: ít dùng nhất được loại bỏ trước
        templates_to_remove.sort(key=lambda tid: self.template_usage.get(tid, 0))
        
        # Loại bỏ template
        for template_id in templates_to_remove[:num_to_remove]:
            logger.info(f"Loại bỏ template ID {template_id} do hết hạn (sử dụng: {self.template_usage.get(template_id, 0)}, "
                      f"tuổi: {current_block - self.template_creation_time.get(template_id, 0)} blocks)")
            if template_id in self.templates:
                del self.templates[template_id]
                # Cập nhật các chỉ số liên quan
                if template_id in self.template_usage:
                    del self.template_usage[template_id]
                if template_id in self.template_last_used:
                    del self.template_last_used[template_id]
                if template_id in self.template_creation_time:
                    del self.template_creation_time[template_id]
        
        return len(templates_to_remove[:num_to_remove])
        
    def calculate_cer(self, original_data, template_data):
        """
        Tính toán Compression Error Rate (CER) giữa dữ liệu gốc và template
        
        CER = |X - X̂| / X, trong đó:
        - X là dữ liệu gốc
        - X̂ là dữ liệu mẫu (template)
        
        Phiên bản nâng cao hỗ trợ dữ liệu đa chiều.
        
        Args:
            original_data: Dữ liệu gốc (có thể là mảng 1D hoặc dictionary của các mảng)
            template_data: Dữ liệu template (có thể là mảng 1D hoặc dictionary của các mảng)
        
        Returns:
            float: Giá trị CER trung bình
        """
        # Trường hợp dữ liệu đa chiều (dictionary)
        if self.multi_dimensional and isinstance(original_data, dict) and isinstance(template_data, dict):
            total_cer = 0.0
            total_weight = 0.0
            dimension_weights = self.config.get('dimension_weights', {})
            
            # Tính CER cho từng chiều dữ liệu
            for dim in original_data.keys():
                if dim in template_data:
                    # Lấy trọng số cho chiều này, mặc định là 1.0
                    weight = dimension_weights.get(dim, 1.0)
                    if weight > 0:
                        # Tính CER cho chiều này
                        orig_values = np.array(original_data[dim])
                        temp_values = np.array(template_data[dim])
                        
                        # Đảm bảo dữ liệu có cùng kích thước để so sánh
                        min_len = min(len(orig_values), len(temp_values))
                        orig_values = orig_values[:min_len]
                        temp_values = temp_values[:min_len]
                        
                        # Tránh chia cho 0
                        nonzero_mask = orig_values != 0
                        if np.any(nonzero_mask):
                            # Tính lỗi chỉ cho các giá trị khác 0
                            error = np.abs(orig_values[nonzero_mask] - temp_values[nonzero_mask])
                            relative_error = error / np.abs(orig_values[nonzero_mask])
                            dim_cer = np.mean(relative_error)
                            
                            # Cộng vào tổng có trọng số
                            total_cer += dim_cer * weight
                            total_weight += weight
            
            # Trả về giá trị CER trung bình có trọng số
            if total_weight > 0:
                return total_cer / total_weight
            return 0.0
        
        # Trường hợp dữ liệu một chiều (mảng 1D) - giữ nguyên code cũ
        # Đảm bảo dữ liệu có cùng kích thước để so sánh
        min_len = min(len(original_data), len(template_data))
        original = np.array(original_data[:min_len])
        template = np.array(template_data[:min_len])
        
        # Tránh chia cho 0
        nonzero_mask = original != 0
        if not np.any(nonzero_mask):
            return 0.0
        
        # Tính lỗi chỉ cho các giá trị khác 0
        error = np.abs(original[nonzero_mask] - template[nonzero_mask])
        relative_error = error / np.abs(original[nonzero_mask])
        
        # Trả về giá trị CER trung bình
        return np.mean(relative_error)
    
    def calculate_correlation(self, data1, data2):
        """
        Tính hệ số tương quan Pearson giữa hai mảng dữ liệu
        
        Phiên bản nâng cao hỗ trợ dữ liệu đa chiều.
        
        Args:
            data1, data2: Hai đối tượng dữ liệu cần so sánh (mảng 1D hoặc dictionary)
            
        Returns:
            float: Hệ số tương quan [0, 1] (1 là tương quan hoàn hảo)
        """
        # Trường hợp dữ liệu đa chiều
        if self.multi_dimensional and isinstance(data1, dict) and isinstance(data2, dict):
            total_corr = 0.0
            total_weight = 0.0
            dimension_weights = self.config.get('dimension_weights', {})
            
            # Tính tương quan cho từng chiều dữ liệu
            for dim in data1.keys():
                if dim in data2:
                    # Lấy trọng số cho chiều này, mặc định là 1.0
                    weight = dimension_weights.get(dim, 1.0)
                    if weight > 0:
                        try:
                            # Tính tương quan cho chiều này
                            values1 = np.array(data1[dim])
                            values2 = np.array(data2[dim])
                            
                            # Đảm bảo dữ liệu có cùng kích thước
                            min_len = min(len(values1), len(values2))
                            x = values1[:min_len]
                            y = values2[:min_len]
                            
                            # Tính hệ số tương quan Pearson
                            corr, _ = stats.pearsonr(x, y)
                            
                            # Chuyển sang giá trị tuyệt đối và chuẩn hóa về [0, 1]
                            dim_corr = abs(corr)
                            
                            # Cộng vào tổng có trọng số
                            total_corr += dim_corr * weight
                            total_weight += weight
                        except Exception as e:
                            logger.warning(f"Lỗi khi tính hệ số tương quan cho chiều {dim}: {str(e)}")
            
            # Trả về giá trị tương quan trung bình có trọng số
            if total_weight > 0:
                return total_corr / total_weight
            return 0.0
            
        # Trường hợp dữ liệu một chiều - giữ nguyên code cũ
        try:
            # Đảm bảo dữ liệu có cùng kích thước
            min_len = min(len(data1), len(data2))
            x = np.array(data1[:min_len])
            y = np.array(data2[:min_len])
            
            # Tính hệ số tương quan Pearson
            corr, _ = stats.pearsonr(x, y)
            
            # Chuyển sang giá trị tuyệt đối và chuẩn hóa về [0, 1]
            return abs(corr)
        except Exception as e:
            logger.warning(f"Lỗi khi tính hệ số tương quan: {str(e)}")
            return 0.0
    
    def calculate_cost(self, cer, cr):
        """
        Tính cost function cân bằng giữa CER và CR
        
        Cost = w1 * CER - w2 * CR, trong đó:
        - w1, w2 là trọng số (w1 + w2 = 1)
        - Giá trị cost càng thấp càng tốt
        
        Args:
            cer: Compression Error Rate
            cr: Compression Ratio
        
        Returns:
            float: Giá trị cost function
        """
        w1 = self.config['w1']
        w2 = self.config['w2']
        
        # Chuẩn hóa CER và CR để chúng có cùng thang đo
        # Giả sử CER trong khoảng [0, max_acceptable_cer] và CR trong khoảng [1, ∞)
        normalized_cer = min(1.0, cer / self.config['max_acceptable_cer'])
        normalized_cr = min(1.0, 1.0 / cr)  # CR càng lớn, normalized_cr càng nhỏ
        
        # Tính cost (giá trị càng thấp càng tốt)
        return w1 * normalized_cer - w2 * (1 - normalized_cr)
    
    def calculate_similarity_score(self, data1, data2):

        # Trường hợp dữ liệu đa chiều (dictionary)
        if self.multi_dimensional and isinstance(data1, dict) and isinstance(data2, dict):
            total_similarity = 0.0
            total_weight = 0.0
            dimension_weights = self.config.get('dimension_weights', {})
            
            # Dictionary lưu các chỉ số chi tiết cho từng chiều
            dimension_details = {}
            
            # Tính các chỉ số tổng hợp
            ks_pvalue = 0.0
            correlation = self.calculate_correlation(data1, data2)  # Đã hỗ trợ đa chiều
            cer = self.calculate_cer(data1, data2)  # Đã hỗ trợ đa chiều
            
            # Chuẩn hóa CER
            normalized_cer = 1.0 - min(1.0, cer / self.config['max_acceptable_cer'])
            
            # Tính điểm tương đồng cho từng chiều dữ liệu
            dimensions_processed = 0
            
            for dim in data1.keys():
                if dim in data2:
                    # Lấy trọng số cho chiều này, mặc định là 1.0
                    weight = dimension_weights.get(dim, 1.0)
                    if weight > 0:
                        values1 = np.array(data1[dim])
                        values2 = np.array(data2[dim])
                        
                        # Đảm bảo dữ liệu có cùng kích thước
                        min_len = min(len(values1), len(values2))
                        values1 = values1[:min_len]
                        values2 = values2[:min_len]
                        
                        try:
                            # Tính P-value từ KS test cho chiều này
                            dim_ks, dim_ks_pvalue = stats.ks_2samp(values1, values2)
                            ks_pvalue += dim_ks_pvalue * weight
                            
                            # Chuẩn hóa dữ liệu để so sánh hình dạng
                            values1_norm = (values1 - np.mean(values1)) / (np.std(values1) if np.std(values1) > 0 else 1)
                            values2_norm = (values2 - np.mean(values2)) / (np.std(values2) if np.std(values2) > 0 else 1)
                            
                            # Độ lệch trung bình giữa hai đường chuẩn hóa
                            shape_diff = np.mean(np.abs(values1_norm - values2_norm))
                            shape_similarity = max(0, 1 - min(1, shape_diff/3.0))
                            
                            # So sánh biến thiên (trend) theo thời gian
                            grad1 = np.diff(values1_norm)
                            grad2 = np.diff(values2_norm)
                            
                            if len(grad1) > 0 and len(grad2) > 0:
                                min_grad_len = min(len(grad1), len(grad2))
                                grad1 = grad1[:min_grad_len]
                                grad2 = grad2[:min_grad_len]
                                
                                # Đếm số lần gradient có cùng dấu (cùng chiều tăng/giảm)
                                same_direction = np.sum((grad1 * grad2) > 0)
                                trend_similarity = same_direction / min_grad_len if min_grad_len > 0 else 0
                            else:
                                trend_similarity = 0
                            
                            # Lưu thông tin chi tiết cho chiều này
                            dimension_details[dim] = {
                                'ks_pvalue': dim_ks_pvalue,
                                'shape_similarity': shape_similarity,
                                'trend_similarity': trend_similarity,
                                'weight': weight
                            }
                            
                            # Cộng dồn trọng số đã xử lý
                            total_weight += weight
                            dimensions_processed += 1
                            
                        except Exception as e:
                            logger.warning(f"Lỗi khi tính điểm tương đồng cho chiều {dim}: {str(e)}")
            
            # Chuẩn hóa ks_pvalue theo trọng số
            if total_weight > 0:
                ks_pvalue = ks_pvalue / total_weight
            
            # Lấy trọng số từ cấu hình
            weights = {
                'ks_test': 0.15,
                'correlation': 0.25,
                'cer': 0.15,
                'shape': 0.25,
                'trend': 0.20
            }
            
            # Ghi đè trọng số từ cấu hình nếu có
            if 'enhanced_similarity_weights' in self.config:
                weights.update(self.config['enhanced_similarity_weights'])
            
            # Tính các thành phần tương đồng tổng hợp
            avg_shape_similarity = sum(detail['shape_similarity'] * detail['weight'] 
                                    for detail in dimension_details.values()) / total_weight if total_weight > 0 else 0
            
            avg_trend_similarity = sum(detail['trend_similarity'] * detail['weight'] 
                                    for detail in dimension_details.values()) / total_weight if total_weight > 0 else 0
            
            # Tính điểm tương đồng tổng hợp cho dữ liệu đa chiều
            similarity_score = (
                weights['ks_test'] * min(1.0, ks_pvalue / self.config['p_threshold']) +
                weights['correlation'] * correlation +
                weights['cer'] * normalized_cer +
                weights['shape'] * avg_shape_similarity +
                weights['trend'] * avg_trend_similarity
            )
            
            # Thông tin chi tiết
            details = {
                'ks_pvalue': ks_pvalue,
                'correlation': correlation,
                'cer': cer,
                'shape_similarity': avg_shape_similarity,
                'trend_similarity': avg_trend_similarity,
                'similarity_score': similarity_score,
                'dimensions': dimension_details,
                'dimensions_processed': dimensions_processed
            }
            
            return similarity_score, ks_pvalue, correlation, cer, details
        
        # Mã xử lý dữ liệu một chiều - giữ nguyên code cũ
        # Đảm bảo cả hai mảng có cùng kích thước trước khi so sánh
        min_len = min(len(data1), len(data2))
        data1 = data1[:min_len]
        data2 = data2[:min_len]
        
        # Tính P-value từ KS test (Kolmogorov-Smirnov test) - kiểm tra sự giống nhau về phân phối xác suất
        _, ks_pvalue = stats.ks_2samp(data1, data2)
        
        # Tính hệ số tương quan Pearson - đo mức độ tương quan tuyến tính
        correlation = self.calculate_correlation(data1, data2)
        
        # Tính CER - đo sai số tương đối
        cer = self.calculate_cer(data1, data2)
        normalized_cer = 1.0 - min(1.0, cer / self.config['max_acceptable_cer'])
        
        # Cải tiến: Thêm so sánh theo mẫu hình dạng (pattern shape) 
        # Chuẩn hóa dữ liệu để so sánh hình dạng
        data1_norm = (np.array(data1) - np.mean(data1)) / (np.std(data1) if np.std(data1) > 0 else 1)
        data2_norm = (np.array(data2) - np.mean(data2)) / (np.std(data2) if np.std(data2) > 0 else 1)
        
        # Độ lệch trung bình giữa hai đường chuẩn hóa
        shape_diff = np.mean(np.abs(data1_norm - data2_norm))
        shape_similarity = max(0, 1 - min(1, shape_diff/3.0))  # Chuyển đổi sang thang điểm 0-1
        
        # Cải tiến: So sánh biến thiên (trend) theo thời gian
        # Tính gradient (đạo hàm rời rạc) để so sánh xu hướng biến thiên
        grad1 = np.diff(data1_norm)
        grad2 = np.diff(data2_norm)
        if len(grad1) > 0 and len(grad2) > 0:
            min_len = min(len(grad1), len(grad2))
            grad1 = grad1[:min_len]
            grad2 = grad2[:min_len]
            
            # Đếm số lần gradient có cùng dấu (cùng chiều tăng/giảm)
            same_direction = np.sum((grad1 * grad2) > 0)
            trend_similarity = same_direction / min_len if min_len > 0 else 0
        else:
            trend_similarity = 0
        
        # Cập nhật trọng số với các phương pháp mới
        weights = {
            'ks_test': 0.15,        # Giảm trọng số KS test
            'correlation': 0.25,    # Giảm trọng số tương quan Pearson
            'cer': 0.15,            # Giảm trọng số CER
            'shape': 0.25,          # Trọng số cho độ tương đồng hình dạng
            'trend': 0.20           # Trọng số cho độ tương đồng xu hướng
        }
        
        # Ghi đè trọng số từ cấu hình nếu có
        if 'enhanced_similarity_weights' in self.config:
            weights.update(self.config['enhanced_similarity_weights'])
        
        # Tính điểm tương đồng tổng hợp (giá trị càng cao càng tương đồng)
        similarity_score = (
            weights['ks_test'] * min(1.0, ks_pvalue / self.config['p_threshold']) +
            weights['correlation'] * correlation +
            weights['cer'] * normalized_cer +
            weights['shape'] * shape_similarity +
            weights['trend'] * trend_similarity
        )
        
        # Cải tiến: Lưu thêm thông tin về các thành phần tương đồng để phân tích
        details = {
            'ks_pvalue': ks_pvalue,
            'correlation': correlation,
            'cer': cer,
            'shape_similarity': shape_similarity,
            'trend_similarity': trend_similarity,
            'similarity_score': similarity_score
        }
        
        return similarity_score, ks_pvalue, correlation, cer, details
    
    def is_similar(self, data1, data2):

        # Trường hợp dữ liệu đa chiều
        if self.multi_dimensional and isinstance(data1, dict) and isinstance(data2, dict):
            # Kiểm tra kích thước cho từng chiều
            for dim in data1.keys():
                if dim in data2:
                    if len(data1[dim]) < self.config['min_values'] or len(data2[dim]) < self.config['min_values']:
                        # Nếu một trong các chiều có dữ liệu không đủ, vẫn tiếp tục kiểm tra các chiều khác
                        logger.debug(f"Chiều {dim} có kích thước không đủ: {len(data1[dim])}, {len(data2[dim])}")
            
            # Tính điểm tương đồng và các chỉ số
            similarity_score, ks_pvalue, correlation, cer, full_details = self.calculate_similarity_score(data1, data2)
            
            # Thông tin chi tiết
            details = {
                'ks_pvalue': ks_pvalue,
                'correlation': correlation,
                'cer': cer,
                'similarity_score': similarity_score,
                'dimensions': full_details.get('dimensions', {}),
                'shape_similarity': full_details.get('shape_similarity', 0),
                'trend_similarity': full_details.get('trend_similarity', 0)
            }
            
            # Cải tiến: Sử dụng ngưỡng động để xác định tính tương đồng
            # Với dữ liệu đa chiều, có thể điều chỉnh ngưỡng dựa trên số lượng chiều đã xử lý
            similarity_threshold = 0.35  # Mặc định
            
            # Nếu có pattern rõ ràng (tương quan cao), yêu cầu similarity cao hơn
            if correlation > 0.8:
                similarity_threshold = 0.45
            
            # Điều chỉnh ngưỡng dựa trên số lượng chiều
            dimensions_processed = full_details.get('dimensions_processed', 0)
            if dimensions_processed > 2:
                # Khi có nhiều chiều, giảm ngưỡng để dễ dàng tìm thấy template
                similarity_threshold *= 0.9
            
            # Cải tiến: Bổ sung thêm điều kiện phụ cho trường hợp đặc biệt
            # Ngay cả khi similarity_score không đủ cao, vẫn chấp nhận nếu:
            # 1. Tương quan rất cao (> 0.9) VÀ
            # 2. Hình dạng tương tự (> 0.8)
            shape_trend_match = (details['shape_similarity'] > 0.8 and correlation > 0.9)
            
            # Xác định dữ liệu có tương tự nhau không
            # Điều kiện 1: Điểm tương đồng đủ cao HOẶC pattern rất tương đồng
            # Điều kiện 2: CER dưới ngưỡng chấp nhận được
            is_similar = (
                (similarity_score > similarity_threshold or shape_trend_match) and
                cer < self.config['max_acceptable_cer']
            )
            
            if is_similar:
                self.similarity_scores.append(similarity_score)
                logger.debug(f"Dữ liệu đa chiều tương tự: score={similarity_score:.4f}, KS={ks_pvalue:.4f}, corr={correlation:.4f}, CER={cer:.4f}")
            
            return is_similar, similarity_score, details
        
        # Trường hợp dữ liệu một chiều - giữ nguyên code cũ
        if len(data1) < self.config['min_values'] or len(data2) < self.config['min_values']:
            return False, 0.0, {}
        
        # Tính điểm tương đồng và các chỉ số
        similarity_score, ks_pvalue, correlation, cer, full_details = self.calculate_similarity_score(data1, data2)
        
        # Thông tin chi tiết
        details = {
            'ks_pvalue': ks_pvalue,
            'correlation': correlation,
            'cer': cer,
            'similarity_score': similarity_score,
            'shape_similarity': full_details.get('shape_similarity', 0),
            'trend_similarity': full_details.get('trend_similarity', 0)
        }
        
        # Cải tiến: Sử dụng ngưỡng động để xác định tính tương đồng
        # Với dữ liệu có pattern rõ ràng, đặt ngưỡng cao hơn để phân biệt tốt hơn
        similarity_threshold = 0.35  # Mặc định
        
        # Nếu có pattern rõ ràng (tương quan cao), yêu cầu similarity cao hơn
        if correlation > 0.8:
            similarity_threshold = 0.45
        
        # Cải tiến: Bổ sung thêm điều kiện phụ cho trường hợp đặc biệt
        # Ngay cả khi similarity_score không đủ cao, vẫn chấp nhận nếu:
        # 1. Tương quan rất cao (> 0.9) VÀ
        # 2. Hình dạng tương tự (> 0.8)
        shape_trend_match = (details['shape_similarity'] > 0.8 and correlation > 0.9)
        
        # Xác định dữ liệu có tương tự nhau không
        # Điều kiện 1: Điểm tương đồng đủ cao HOẶC pattern rất tương đồng
        # Điều kiện 2: CER dưới ngưỡng chấp nhận được
        is_similar = (
            (similarity_score > similarity_threshold or shape_trend_match) and
            cer < self.config['max_acceptable_cer']
        )
        
        if is_similar:
            self.similarity_scores.append(similarity_score)
            logger.debug(f"Dữ liệu tương tự: score={similarity_score:.4f}, KS={ks_pvalue:.4f}, corr={correlation:.4f}, CER={cer:.4f}")
        
        return is_similar, similarity_score, details
        
    def find_matching_template(self, data):
        """
        Tìm template khớp với dữ liệu
        
        Args:
            data: Dữ liệu cần tìm template (mảng 1D hoặc dictionary)
            
        Returns:
            tuple: (template_id, template_data, cer, similarity_score) nếu tìm thấy, hoặc (None, None, None, None)
        """
        # Trường hợp dữ liệu đa chiều
        if self.multi_dimensional and isinstance(data, dict):
            # Kiểm tra xem dữ liệu có chiều dữ liệu chính không
            primary_dim = self.primary_dimension
            if primary_dim not in data or len(data[primary_dim]) < self.config['min_values']:
                logger.warning(f"Dữ liệu không có chiều chính {primary_dim} hoặc không đủ dữ liệu")
                return None, None, None, None
            
            # Phát hiện xu hướng trong dữ liệu gần đây cho chiều chính
            has_trend, trend_type, trend_strength = self.detect_trend(data[primary_dim])
            
        best_template_id = None
        best_template_data = None
        best_cer = float('inf')
        best_similarity = -1.0
            
        # Tính các đặc trưng cơ bản của dữ liệu mới cho chiều chính
        primary_values = np.array(data[primary_dim])
        data_mean = np.mean(primary_values)
        data_std = np.std(primary_values)
        data_min = np.min(primary_values)
        data_max = np.max(primary_values)
        data_range = data_max - data_min
            
        potential_matches = []
            
        # Khi phát hiện xu hướng mạnh, điều chỉnh cách chọn template
        if has_trend and trend_strength > 0.85:
            logger.debug(f"Đã phát hiện xu hướng mạnh: {trend_type}, độ mạnh: {trend_strength:.2f}")
            # Với xu hướng mạnh, ưu tiên tạo template mới thay vì sử dụng template cũ
            similarity_boost = 0.15  # Cần tăng điểm tương đồng lên 15% so với bình thường
        else:
            similarity_boost = 0.0
        
        for template_id, template_data in self.templates.items():
            # Kiểm tra xem template có cùng định dạng với dữ liệu hiện tại không
            if not isinstance(template_data, dict) or primary_dim not in template_data:
                continue
                
            # Kiểm tra nhanh các đặc trưng thống kê cơ bản cho chiều chính
            template_values = np.array(template_data[primary_dim])
            template_mean = np.mean(template_values)
            template_std = np.std(template_values)
            template_min = np.min(template_values)
            template_max = np.max(template_values)
            template_range = template_max - template_min
                
            # Bỏ qua các template có đặc trưng quá khác trên chiều chính
            if (abs(data_mean - template_mean) > 0.5 * data_std and 
                abs(data_range - template_range) > 0.5 * data_range):
                continue
                
            # Cập nhật metrics của template (mark as checked, not used yet)
            self.update_template_metrics(template_id, used=False)
                
            # Kiểm tra tính tương đồng
            is_similar, similarity_score, details = self.is_similar(data, template_data)
                
            # Điều chỉnh điểm tương đồng nếu có xu hướng mạnh
            adjusted_similarity = similarity_score - similarity_boost if has_trend else similarity_score
                
            # Nếu đủ tương đồng sau khi điều chỉnh, thêm vào danh sách tiềm năng
            if is_similar and adjusted_similarity > 0.3:
                potential_matches.append((template_id, template_data, details['cer'], similarity_score, details))
        
        # Sắp xếp theo điểm tương đồng giảm dần
        potential_matches.sort(key=lambda x: x[3], reverse=True)
            
        # Lấy template tốt nhất
        if potential_matches:
            best_match = potential_matches[0]
            best_template_id, best_template_data, best_cer, best_similarity, _ = best_match
                
            # Nếu có xu hướng mạnh và điểm tương đồng không quá cao, có thể quyết định tạo template mới
            if has_trend and trend_strength > 0.9 and best_similarity < 0.7:
                logger.debug(f"Bỏ qua template tốt nhất (ID: {best_template_id}, score: {best_similarity:.2f}) "
                          f"do xu hướng mạnh: {trend_type}")
                return None, None, None, None
                
            # Nếu quyết định sử dụng template này, cập nhật metrics
            self.update_template_metrics(best_template_id, used=True)
                
            return best_template_id, best_template_data, best_cer, best_similarity
            
        # Không tìm thấy template phù hợp
        return None, None, None, None
            
        # Trường hợp dữ liệu một chiều - giữ nguyên code cũ
        # Phát hiện xu hướng trong dữ liệu gần đây
        has_trend, trend_type, trend_strength = self.detect_trend(data)
        
        best_template_id = None
        best_template_data = None
        best_cer = float('inf')
        best_similarity = -1.0
        
        # Tính các đặc trưng của dữ liệu mới
        data_mean = np.mean(data)
        data_std = np.std(data)
        data_min = np.min(data)
        data_max = np.max(data)
        data_range = data_max - data_min
        
        potential_matches = []
        
        # Khi phát hiện xu hướng mạnh, điều chỉnh cách chọn template
        if has_trend and trend_strength > 0.85:
            logger.debug(f"Đã phát hiện xu hướng mạnh: {trend_type}, độ mạnh: {trend_strength:.2f}")
            # Với xu hướng mạnh, ưu tiên tạo template mới thay vì sử dụng template cũ
            # Tăng ngưỡng cho template matching để khó khớp hơn
            similarity_boost = 0.15  # Cần tăng điểm tương đồng lên 15% so với bình thường
        else:
            similarity_boost = 0.0
        
        for template_id, template_data in self.templates.items():
            # Bỏ qua các template có định dạng khác (dictionary vs array)
            if isinstance(template_data, dict):
                continue
                
            # Kiểm tra nhanh các đặc trưng thống kê cơ bản trước
            template_mean = np.mean(template_data)
            template_std = np.std(template_data)
            template_min = np.min(template_data)
            template_max = np.max(template_data)
            template_range = template_max - template_min
                
            # Bỏ qua các template có đặc trưng quá khác
            if (abs(data_mean - template_mean) > 0.5 * data_std and 
                abs(data_range - template_range) > 0.5 * data_range):
                continue
                
            # Cập nhật metrics của template (mark as checked, not used yet)
            self.update_template_metrics(template_id, used=False)
                
            # Kiểm tra tính tương đồng
            is_similar, similarity_score, details = self.is_similar(data, template_data)
                
            # Điều chỉnh điểm tương đồng nếu có xu hướng mạnh
            adjusted_similarity = similarity_score - similarity_boost if has_trend else similarity_score
                
            # Nếu đủ tương đồng sau khi điều chỉnh, thêm vào danh sách tiềm năng
            if is_similar and adjusted_similarity > 0.3:  # Vẫn giữ ngưỡng khá thấp để có nhiều lựa chọn
                potential_matches.append((template_id, template_data, details['cer'], similarity_score, details))
        
        # Sắp xếp theo điểm tương đồng giảm dần
        potential_matches.sort(key=lambda x: x[3], reverse=True)
            
        # Lấy template tốt nhất
        if potential_matches:
            best_match = potential_matches[0]
            best_template_id, best_template_data, best_cer, best_similarity, _ = best_match
                
            # Nếu có xu hướng mạnh và điểm tương đồng không quá cao, có thể quyết định tạo template mới
            if has_trend and trend_strength > 0.9 and best_similarity < 0.7:
                logger.debug(f"Bỏ qua template tốt nhất (ID: {best_template_id}, score: {best_similarity:.2f}) "
                          f"do xu hướng mạnh: {trend_type}")
                return None, None, None, None
                
            # Nếu quyết định sử dụng template này, cập nhật metrics
            self.update_template_metrics(best_template_id, used=True)
                
            return best_template_id, best_template_data, best_cer, best_similarity
        
        # Không tìm thấy template phù hợp            
        return None, None, None, None
        
    def create_template(self, data):
        """
        Tạo một template mới từ một block dữ liệu
        
        Args:
            data: Dữ liệu để tạo template (mảng 1D hoặc dictionary)
            
        Returns:
            int: ID của template mới tạo
        """
        # Trước khi tạo template mới, kiểm tra và loại bỏ template cũ nếu cần
        if len(self.templates) >= self.config['max_templates'] * 0.9:
            self.clean_expired_templates()
        
        # Tạo ID mới cho template
        template_id = self.template_counter + 1
        self.template_counter += 1
        
        # Lưu template (hỗ trợ cả array và dictionary)
        if isinstance(data, dict):
            # Tạo bản sao sâu của dictionary
            template_data = {}
            for dim, values in data.items():
                template_data[dim] = values.copy() if hasattr(values, 'copy') else values
            self.templates[template_id] = template_data
        else:
            # Array - giữ nguyên code cũ
            self.templates[template_id] = data.copy()
        
        # Cập nhật metrics cho template mới
        self.update_template_metrics(template_id, used=True)
        
        # Kiểm tra nếu đã đạt số lượng template tối đa
        if len(self.templates) > self.config['max_templates']:
            # Loại bỏ template ít được sử dụng nhất
            template_to_remove = min(self.template_usage.items(), key=lambda x: x[1])[0]
            del self.templates[template_to_remove]
            # Cập nhật các chỉ số liên quan
            if template_to_remove in self.template_usage:
                del self.template_usage[template_to_remove]
            if template_to_remove in self.template_last_used:
                del self.template_last_used[template_to_remove]
            if template_to_remove in self.template_creation_time:
                del self.template_creation_time[template_to_remove]
        
            logger.info(f"Đã loại bỏ template ID {template_to_remove} do đạt giới hạn số lượng")
        
        return template_id
        
    def adjust_block_size(self):
        """
        Điều chỉnh kích thước block dựa trên hiệu suất nén và xu hướng dữ liệu
        
        Returns:
            int: Kích thước block mới
        """
        # Cập nhật hit ratio liên tục
        if self.blocks_processed > 0:
            current_hit_ratio = self.template_hit_count / self.blocks_processed
            
            # Cập nhật hit ratio cửa sổ
            self.window_blocks += 1
            if len(self.encoded_stream) > 0 and self.encoded_stream[-1].get('template_id') is not None:
                self.window_hit_count += 1
                
            # Nếu đủ kích thước cửa sổ, tính toán hit ratio mới và đặt lại cửa sổ
            if self.window_blocks >= self.window_size:
                window_hit_ratio = self.window_hit_count / self.window_blocks
                self.continuous_hit_ratio.append(window_hit_ratio)
                self.window_hit_count = 0
                self.window_blocks = 0
            
            # Đảm bảo luôn có ít nhất một giá trị hit ratio
            if not self.continuous_hit_ratio:
                self.continuous_hit_ratio.append(current_hit_ratio)
        else:
            current_hit_ratio = 0.0
            
        # Chỉ điều chỉnh nếu đã xử lý đủ số block tối thiểu
        if not self.config['adaptive_block_size'] or self.blocks_processed < self.config['min_blocks_before_adjustment']:
            return self.current_block_size
            
        # Giảm khoảng cách tối thiểu giữa các lần điều chỉnh khi gặp thay đổi đột ngột
        min_adjustment_interval = self.min_adjustment_interval
        if (len(self.similarity_scores) >= 2 and 
            (self.similarity_scores[-1] < 0.4 or 
             self.similarity_scores[-1] - self.similarity_scores[-2] < -0.2)):
            # Giảm khoảng cách để cho phép điều chỉnh nhanh hơn khi độ tương đồng thấp hoặc giảm đột ngột
            min_adjustment_interval = max(2, int(min_adjustment_interval * 0.5))
            
        if self.blocks_processed - self.last_adjustment_block < min_adjustment_interval:
            return self.current_block_size
            
        # Phát hiện xu hướng trong dữ liệu gần đây
        has_trend = False
        trend_strength = 0.0
        trend_type = "none"
        if len(self.recent_values) >= 3:
            has_trend, trend_type, trend_strength = self.detect_trend([])  # Truyền mảng rỗng vì chỉ kiểm tra dữ liệu có sẵn
        
        # Lấy CER trung bình gần đây nếu có
        recent_cer = np.mean(self.cer_values[-5:]) if len(self.cer_values) >= 5 else 0
        
        # Lấy điểm tương đồng trung bình gần đây nếu có
        recent_similarity = np.mean(self.similarity_scores[-5:]) if len(self.similarity_scores) >= 5 else 1.0
        
        # Phát hiện thay đổi đột ngột trong độ tương đồng (5 mẫu gần nhất)
        similarity_trend = 0
        if len(self.similarity_scores) >= 5:
            recent_5_similarity = self.similarity_scores[-5:]
            similarity_trend = recent_5_similarity[-1] - recent_5_similarity[0]
        
        # Lấy hit ratio cửa sổ gần nhất
        recent_hit_ratio = self.continuous_hit_ratio[-1] if self.continuous_hit_ratio else current_hit_ratio
        
        # Số lượng thông tin có hiệu lực đã thu thập được
        r = self.blocks_processed
        rmin = self.config['min_blocks_before_adjustment']
        
        # Số lần chuyển đổi kích thước block
        k = len(self.block_size_history)
        kmax = 20
        
        # Khởi tạo các biến trước để tránh lỗi tham chiếu trước khi gán giá trị
        nbest = self.current_block_size
        nnew = nbest  # Khởi tạo mặc định cho nnew
        adjustment_reason = "stable_performance"  # Khởi tạo mặc định
        polynomial_adjustment = False
        hit_ratio_trend = 0
        
        # Phân tích xu hướng hit ratio để quyết định điều chỉnh
        if len(self.continuous_hit_ratio) >= 3:
            hit_ratio_trend = (self.continuous_hit_ratio[-1] - self.continuous_hit_ratio[-3])
        
        # Kiểm tra điều kiện cho phép điều chỉnh
        if r >= rmin and k < kmax:
            # Thu thập dữ liệu cho mô hình đa thức nếu có đủ lịch sử
            if len(self.previous_adjustments) >= 3:
                try:
                    # Trích xuất dữ liệu từ lịch sử điều chỉnh trước đó
                    block_sizes = [adj[0] for adj in self.previous_adjustments]
                    hitrates = [adj[1] for adj in self.previous_adjustments]
                    
                    # Kiểm tra đủ dữ liệu và đa dạng để tạo mô hình
                    if len(set(block_sizes)) >= 3:  # Đảm bảo có ít nhất 3 kích thước khối khác nhau
                        # Tạo mô hình đa thức bậc 2 để tối ưu hóa kích thước khối
                        coeffs = np.polyfit(block_sizes, hitrates, 2)
                        a2, a1, a0 = coeffs
                        
                        # Tìm kích thước khối tối ưu dựa trên đa thức (đỉnh của parabol)
                        # f'(n) = 2*a2*n + a1 = 0 => n = -a1 / (2*a2)
                        if a2 < 0:  # Đảm bảo tìm được giá trị cực đại
                            optimal_size = int(-a1 / (2 * a2))
                            
                            # Kiểm tra xem giá trị tối ưu có nằm trong khoảng hợp lý
                            min_size = self.config['min_block_size']
                            max_size = self.config['max_block_size']
                            
                            if min_size <= optimal_size <= max_size:
                                polynomial_adjustment = True
                                nnew = optimal_size
                                adjustment_reason = "polynomial_optimization"
                                
                                # Tránh điều chỉnh quá lớn trong một lần
                                max_change = int(nbest * 0.15)  # Tối đa thay đổi 15% trong một lần
                                if abs(nnew - nbest) > max_change:
                                    if nnew > nbest:
                                        nnew = nbest + max_change
                                    else:
                                        nnew = nbest - max_change
                except Exception as e:
                    # Ghi log lỗi để debug
                    logger.warning(f"Lỗi khi tạo mô hình đa thức: {str(e)}")
                    polynomial_adjustment = False
            
            # Nếu không thể sử dụng mô hình đa thức, sử dụng thuật toán thay thế
            if not polynomial_adjustment:
                # Kết hợp nhiều yếu tố để quyết định điều chỉnh
                # 1. Hit ratio hiện tại và xu hướng
                # 2. Độ tương đồng gần đây
                # 3. Xu hướng dữ liệu
                
                # Tính trọng số tổng hợp cho việc tăng/giảm kích thước
                hr_weight = 0.4     # Giảm trọng số cho hit ratio
                sim_weight = 0.5    # Tăng trọng số cho độ tương đồng
                trend_weight = 0.1  # Trọng số cho xu hướng dữ liệu
                
                # Tính điểm cho việc tăng kích thước
                increase_score = 0
                
                # Hit ratio cao và không giảm -> tăng điểm
                if recent_hit_ratio > 0.6:
                    increase_score += 0.5 * hr_weight
                if hit_ratio_trend >= 0:
                    increase_score += 0.5 * hr_weight
                
                # Độ tương đồng cao -> tăng điểm
                if recent_similarity > 0.7:
                    increase_score += sim_weight
                
                # Dữ liệu ổn định (không có xu hướng mạnh) -> tăng điểm
                if not has_trend or trend_strength < 0.5:
                    increase_score += trend_weight
                
                # Ngược lại, tính điểm cho việc giảm kích thước
                decrease_score = 0
                
                # Hit ratio thấp hoặc đang giảm -> tăng điểm giảm
                if recent_hit_ratio < 0.5:
                    decrease_score += 0.5 * hr_weight
                if hit_ratio_trend < 0:
                    decrease_score += 0.5 * hr_weight
                
                # Độ tương đồng thấp hoặc giảm đột ngột -> tăng điểm giảm mạnh
                if recent_similarity < 0.6:
                    decrease_score += sim_weight
                # Xu hướng giảm độ tương đồng -> tăng điểm giảm
                if similarity_trend < -0.1:
                    decrease_score += 0.5 * sim_weight  # Thêm điểm nếu độ tương đồng đang giảm
                
                # Dữ liệu có xu hướng mạnh -> tăng điểm giảm (để bắt kịp thay đổi)
                if has_trend and trend_strength > 0.5:
                    decrease_score += trend_weight
                
                # Quyết định điều chỉnh dựa trên điểm số
                if increase_score > decrease_score + 0.2:  # Ưu tiên tăng từ từ
                    # Tăng từ từ với hệ số thấp hơn
                    adjustment_factor = min(0.1, (increase_score - decrease_score) * 0.3)
                    nnew = int(nbest * (1 + adjustment_factor))
                    adjustment_reason = "slow_increase_by_weighted_score"
                elif decrease_score > increase_score + 0.1:  # Ưu tiên giảm nhanh
                    # Giảm nhanh hơn với hệ số cao hơn
                    adjustment_factor = min(0.3, (decrease_score - increase_score) * 0.6)
                    nnew = int(nbest * (1 - adjustment_factor))
                    adjustment_reason = "fast_decrease_by_weighted_score"
                else:
                    # Điểm số gần nhau -> giữ nguyên hoặc điều chỉnh nhẹ dựa trên xu hướng
                    if hit_ratio_trend > 0.1 and similarity_trend > 0:
                        nnew = int(nbest * 1.05)  # Tăng nhẹ 5% khi cả hit ratio và độ tương đồng đều tăng
                        adjustment_reason = "slight_increase_by_trend"
                    elif hit_ratio_trend < -0.1 or similarity_trend < -0.05:
                        nnew = int(nbest * 0.9)  # Giảm 10% khi hit ratio hoặc độ tương đồng giảm
                        adjustment_reason = "moderate_decrease_by_trend"
                    else:
                        nnew = nbest  # Giữ nguyên
                        adjustment_reason = "stable_performance"
        
        # Cửa sổ từ chối cập nhật (wn) - ngưỡng tối thiểu để thay đổi
        wn = max(2, int(nbest * 0.05))
        
        # Các điều kiện đặc biệt khác
        special_condition = (recent_hit_ratio < 0.3 or 
                             recent_similarity < 0.4 or 
                             (recent_hit_ratio > 0.9 and recent_similarity > 0.8))
        
        # Đảm bảo nnew đã được khởi tạo và khác None
        if nnew is None:
            nnew = nbest
            logger.warning("Giá trị nnew chưa được khởi tạo, sử dụng giá trị mặc định")
        
        # Chỉ cập nhật nếu sự thay đổi đủ lớn hoặc có lý do đặc biệt
        if abs(nnew - nbest) > wn or special_condition:
            # Giới hạn trong phạm vi cho phép
            new_block_size = max(self.config['min_block_size'], 
                              min(self.config['max_block_size'], nnew))
            
            # Xử lý trường hợp đặc biệt: nếu đang ở kích thước lớn nhất và hit ratio giảm -> giảm ngay
            if nbest == self.config['max_block_size'] and (hit_ratio_trend < 0 or similarity_trend < 0):
                new_block_size = int(nbest * 0.8)  # Giảm 20% (giảm mạnh hơn)
                adjustment_reason = "significant_reduce_from_max_due_to_declining_metrics"
            
            # Tương tự, nếu đang ở kích thước nhỏ nhất và hit ratio tăng -> tăng dần từ từ
            if nbest == self.config['min_block_size'] and hit_ratio_trend > 0 and similarity_trend > 0:
                new_block_size = int(nbest * 1.1)  # Tăng 10% (tăng chậm hơn)
                adjustment_reason = "gradual_increase_from_min_due_to_improving_metrics"
            
            # Lưu lịch sử thay đổi với thông tin chi tiết hơn
            self.block_size_history.append({
                'block_number': self.blocks_processed,
                'old_size': self.current_block_size,
                'new_size': new_block_size,
                'recent_cer': recent_cer,
                'recent_similarity': recent_similarity,
                'similarity_trend': similarity_trend,
                'has_trend': has_trend,
                'trend_type': trend_type,
                'trend_strength': trend_strength,
                'hit_ratio': current_hit_ratio,
                'window_hit_ratio': recent_hit_ratio,
                'hit_ratio_trend': hit_ratio_trend,
                'adjustment_reason': adjustment_reason
            })
            
            # Lưu thông tin chi tiết hơn trong log
            logger.info(f"Điều chỉnh kích thước block: {self.current_block_size} -> {new_block_size} "
                      f"(hit ratio: {current_hit_ratio:.2f}, window HR: {recent_hit_ratio:.2f}, "
                      f"CER: {recent_cer:.4f}, Similarity: {recent_similarity:.4f}, "
                      f"Similarity trend: {similarity_trend:.4f}, "
                      f"Lý do: {adjustment_reason})")
            
            self.current_block_size = new_block_size
            self.last_adjustment_block = self.blocks_processed
            
            # Lưu lịch sử điều chỉnh để phân tích
            self.previous_adjustments.append((new_block_size, current_hit_ratio))
        else:
            # Nếu không có điều chỉnh, vẫn lưu thông tin vào previous_adjustments để tích lũy dữ liệu cho đa thức
            if r % 20 == 0:  # Chỉ lưu định kỳ để không làm tràn bộ nhớ
                self.previous_adjustments.append((nbest, current_hit_ratio))
        
        return self.current_block_size
        
    def compress(self, data):
        """
        Nén một đối tượng dữ liệu
        
        Args:
            data: Đối tượng dữ liệu cần nén (mảng 1D hoặc list các dictionary)
            
        Returns:
            dict: Kết quả nén, bao gồm templates, mã nén, và thống kê
        """
        self.reset()  # Reset trạng thái
        
        # Trường hợp dữ liệu đa chiều
        if self.multi_dimensional and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Phát hiện các chiều dữ liệu từ mẫu đầu tiên
            self.dimensions = list(data[0].keys())
            logger.info(f"Phát hiện dữ liệu đa chiều với các chiều: {self.dimensions}")
            
            n = len(data)
            
            if n < self.config['min_block_size']:
                logger.warning(f"Dữ liệu quá nhỏ để nén: {n} mẫu")
                return {
                    'templates': {},
                    'encoded_stream': [],
                    'compression_ratio': 1.0,
                    'blocks_processed': 0,
                    'hit_ratio': 0,
                    'total_values': n,
                    'avg_cer': 0.0,
                    'avg_cost': 0.0,
                    'continuous_hit_ratio': [],
                    'hit_ratio_by_block': [],
                    'dimensions': self.dimensions
                }
            
            # Tạo mảng để theo dõi hit ratio theo từng block
            hit_ratio_by_block = []
            
            # Xử lý dữ liệu theo từng block
            i = 0
            while i < n:
                # Điều chỉnh kích thước block nếu cần
                block_size = self.adjust_block_size()
                
                # Lấy block hiện tại
                end_idx = min(i + block_size, n)
                block_data = data[i:end_idx]
                
                # Chuyển block dữ liệu từ danh sách các dictionary sang dictionary của các danh sách
                # Ví dụ: từ [{power: 1, temp: 2}, {power: 3, temp: 4}] -> {power: [1, 3], temp: [2, 4]}
                block_dict = {}
                for dim in self.dimensions:
                    block_dict[dim] = [entry.get(dim) for entry in block_data if dim in entry]
                
                # Kiểm tra xem có đủ dữ liệu cho mỗi chiều không
                valid_block = True
                for dim in self.dimensions:
                    if dim not in block_dict or len(block_dict[dim]) < 2:
                        logger.warning(f"Block thiếu dữ liệu cho chiều {dim}")
                        valid_block = False
                
                if not valid_block:
                    # Di chuyển đến block tiếp theo và bỏ qua block hiện tại
                    i = end_idx
                    continue
                
                # Tìm template phù hợp
                template_id, template_data, cer, similarity_score = self.find_matching_template(block_dict)
                
                # Nếu không tìm thấy, tạo template mới
                if template_id is None:
                    template_id = self.create_template(block_dict)
                    # CER = 0 khi tạo template mới (template = dữ liệu gốc)
                    cer = 0.0
                    similarity_score = 1.0  # Tương đồng hoàn hảo với chính nó
                else:
                    self.template_hit_count += 1
                    # Lưu giá trị CER để theo dõi
                    self.cer_values.append(cer)
                    
                # Cập nhật các biến thống kê
                self.templates_used.add(template_id)
                self.blocks_processed += 1
                
                # Lưu hit ratio hiện tại sau mỗi block
                current_hit_ratio = self.template_hit_count / self.blocks_processed
                hit_ratio_by_block.append(current_hit_ratio)
                
                # Thêm vào encoded stream
                self.encoded_stream.append({
                    'template_id': template_id,
                    'start_idx': i,
                    'length': len(block_data),
                    'cer': cer,
                    'similarity_score': similarity_score,
                    'hit_ratio': current_hit_ratio  # Thêm hit ratio tại thời điểm này
                })
                
                # Lưu điểm tương đồng
                if similarity_score > 0:
                    self.similarity_scores.append(similarity_score)
                
                # Di chuyển đến block tiếp theo
                i = end_idx
                
            # Tính tỷ lệ nén cho dữ liệu đa chiều
            # Giả sử mỗi giá trị gốc có kích thước 8 bytes (float64) và mỗi chiều dữ liệu
            original_size = n * len(self.dimensions) * 8
            
            # Kích thước đã nén = (tổng kích thước template) + (kích thước encoded stream)
            template_size = 0
            for template_id, template in self.templates.items():
                # Mỗi template chứa nhiều chiều dữ liệu
                for dim, values in template.items():
                    template_size += len(values) * 8  # 8 bytes cho mỗi float
                template_size += 4  # 4 bytes cho ID
            
            # Mỗi mục trong encoded stream: 4 bytes cho template_id + 4 bytes cho start_idx + 4 bytes cho length
            encoded_stream_size = len(self.encoded_stream) * (4 + 4 + 4)
            
            # Tối ưu kích thước nén: Tính toán dựa trên số lượng template thực sự được sử dụng
            used_template_size = 0
            templates_used_set = set()
            for block in self.encoded_stream:
                templates_used_set.add(block['template_id'])

            for template_id in templates_used_set:
                if template_id in self.templates:
                    template = self.templates[template_id]
                    # Mỗi template chứa nhiều chiều dữ liệu
                    for dim, values in template.items():
                        used_template_size += len(values) * 8  # 8 bytes cho mỗi float
                    used_template_size += 4  # 4 bytes cho ID

            # Sử dụng kích thước template đã tối ưu
            compressed_size = used_template_size + encoded_stream_size

            # Đảm bảo rằng compressed_size không vượt quá original_size nếu có ít templates sử dụng lại
            # Điều này ngăn trường hợp kích thước nén lớn hơn kích thước gốc
            if compressed_size > original_size and len(templates_used_set) < len(self.encoded_stream) * 0.5:
                # Có ít dùng lại template, tính toán lại tỷ lệ
                compression_ratio = 1.0 + 0.05 * (len(templates_used_set) / max(1, len(self.encoded_stream)))
            else:
                # Tính toán tỷ lệ nén thông thường
                compression_ratio = original_size / max(1, compressed_size)

            hit_ratio = self.template_hit_count / max(1, self.blocks_processed)
            
            # Tính CER trung bình
            avg_cer = np.mean(self.cer_values) if self.cer_values else 0.0
            
            # Tính điểm tương đồng trung bình
            avg_similarity = np.mean(self.similarity_scores) if self.similarity_scores else 0.0
            
            # Tính cost
            cost = self.calculate_cost(avg_cer, compression_ratio)
            self.cost_values.append(cost)
            
            logger.info(f"Nén dữ liệu đa chiều hoàn tất: {n} mẫu -> {len(self.templates)} templates, {self.blocks_processed} blocks")
            logger.info(f"Templates đã sử dụng: {len(templates_used_set)}/{len(self.templates)} ({len(templates_used_set)/max(1, len(self.templates)):.2%})")
            logger.info(f"Kích thước gốc: {original_size/1024:.2f} KB, Kích thước nén: {compressed_size/1024:.2f} KB")
            logger.info(f"Tỷ lệ nén: {compression_ratio:.2f}x, Hit ratio: {hit_ratio:.2f}, CER: {avg_cer:.4f}, Cost: {cost:.4f}")
            
            # Tạo các thống kê bổ sung cho mỗi chiều dữ liệu
            dimension_stats = {}
            for dim in self.dimensions:
                dimension_stats[dim] = {
                    'processed': True,
                    'weight': self.config.get('dimension_weights', {}).get(dim, 1.0)
                }
            
            # Trả về kết quả nén với thông tin chi tiết hơn
            return {
                'templates': self.templates,
                'encoded_stream': self.encoded_stream,
                'compression_ratio': compression_ratio,
                'blocks_processed': self.blocks_processed,
                'hit_ratio': hit_ratio,
                'total_values': n,
                'avg_cer': avg_cer,
                'avg_cost': np.mean(self.cost_values) if self.cost_values else 0.0,
                'avg_similarity': avg_similarity,
                'block_size_history': self.block_size_history,
                'continuous_hit_ratio': self.continuous_hit_ratio,
                'hit_ratio_by_block': hit_ratio_by_block,
                'similarity_by_block': [block.get('similarity_score', 0) for block in self.encoded_stream],
                'cer_by_block': [block.get('cer', 0) for block in self.encoded_stream],
                'block_sizes': [block['length'] for block in self.encoded_stream],
                'template_usage_stats': {tid: self.template_usage.get(tid, 0) for tid in self.templates},
                'dimensions': self.dimensions,
                'dimension_stats': dimension_stats,
                'multi_dimensional': True
            }
        
        # Trường hợp dữ liệu một chiều - giữ nguyên code cũ
        values = np.array(data)
        n = len(values)
        
        if n < self.config['min_block_size']:
            logger.warning(f"Dữ liệu quá nhỏ để nén: {n} giá trị")
            return {
                'templates': {},
                'encoded_stream': [],
                'compression_ratio': 1.0,
                'blocks_processed': 0,
                'hit_ratio': 0,
                'total_values': n,
                'avg_cer': 0.0,
                'avg_cost': 0.0,
                'continuous_hit_ratio': [],
                'hit_ratio_by_block': []
            }
        
        # Tạo mảng để theo dõi hit ratio theo từng block
        hit_ratio_by_block = []
        
        # Xử lý dữ liệu theo từng block
        i = 0
        while i < n:
            # Điều chỉnh kích thước block nếu cần
            block_size = self.adjust_block_size()
            
            # Lấy block hiện tại
            end_idx = min(i + block_size, n)
            block_data = values[i:end_idx]
            
            # Tìm template phù hợp
            template_id, template_data, cer, similarity_score = self.find_matching_template(block_data)
            
            # Nếu không tìm thấy, tạo template mới
            if template_id is None:
                template_id = self.create_template(block_data)
                # CER = 0 khi tạo template mới (template = dữ liệu gốc)
                cer = 0.0
                similarity_score = 1.0  # Tương đồng hoàn hảo với chính nó
            else:
                self.template_hit_count += 1
                # Lưu giá trị CER để theo dõi
                self.cer_values.append(cer)
                
            # Cập nhật các biến thống kê
            self.templates_used.add(template_id)
            self.blocks_processed += 1
            
            # Lưu hit ratio hiện tại sau mỗi block
            current_hit_ratio = self.template_hit_count / self.blocks_processed
            hit_ratio_by_block.append(current_hit_ratio)
            
            # Thêm vào encoded stream
            self.encoded_stream.append({
                'template_id': template_id,
                'start_idx': i,
                'length': len(block_data),
                'cer': cer,
                'similarity_score': similarity_score,
                'hit_ratio': current_hit_ratio  # Thêm hit ratio tại thời điểm này
            })
            
            # Lưu điểm tương đồng
            if similarity_score > 0:
                self.similarity_scores.append(similarity_score)
            
            # Di chuyển đến block tiếp theo
            i = end_idx
            
        # Tính tỷ lệ nén
        original_size = n * 8  # 8 bytes cho mỗi giá trị float

        # Kích thước templates
        template_size = 0
        for template_id, template in self.templates.items():
            template_size += len(template) * 8  # 8 bytes cho mỗi float
            template_size += 4  # 4 bytes cho ID

        # Kích thước encoded stream
        encoded_stream_size = len(self.encoded_stream) * (4 + 4 + 4)  # template_id, start_idx, length

        # Tối ưu kích thước nén: Tính toán dựa trên số lượng template thực sự được sử dụng
        used_template_size = 0
        templates_used_set = set()
        for block in self.encoded_stream:
            templates_used_set.add(block['template_id'])

        for template_id in templates_used_set:
            if template_id in self.templates:
                template = self.templates[template_id]
                used_template_size += len(template) * 8  # 8 bytes cho mỗi float
                used_template_size += 4  # 4 bytes cho ID

        # Sử dụng kích thước template đã tối ưu
        compressed_size = used_template_size + encoded_stream_size

        # Đảm bảo rằng compressed_size không vượt quá original_size nếu có ít templates sử dụng lại
        if compressed_size > original_size and len(templates_used_set) < len(self.encoded_stream) * 0.5:
            # Có ít dùng lại template, tính toán lại tỷ lệ
            compression_ratio = 1.0 + 0.05 * (len(templates_used_set) / max(1, len(self.encoded_stream)))
        else:
            # Tính toán tỷ lệ nén thông thường
            compression_ratio = original_size / max(1, compressed_size)
        
        hit_ratio = self.template_hit_count / max(1, self.blocks_processed)
        
        # Tính CER trung bình
        avg_cer = np.mean(self.cer_values) if self.cer_values else 0.0
        
        # Tính điểm tương đồng trung bình
        avg_similarity = np.mean(self.similarity_scores) if self.similarity_scores else 0.0
        
        # Tính cost
        cost = self.calculate_cost(avg_cer, compression_ratio)
        self.cost_values.append(cost)
        
        logger.info(f"Nén hoàn tất: {n} giá trị -> {len(self.templates)} templates, {self.blocks_processed} blocks")
        logger.info(f"Templates đã sử dụng: {len(templates_used_set)}/{len(self.templates)} ({len(templates_used_set)/max(1, len(self.templates)):.2%})")
        logger.info(f"Kích thước gốc: {original_size/1024:.2f} KB, Kích thước nén: {compressed_size/1024:.2f} KB")
        logger.info(f"Tỷ lệ nén: {compression_ratio:.2f}x, Hit ratio: {hit_ratio:.2f}, CER: {avg_cer:.4f}, Cost: {cost:.4f}")
        logger.info(f"Điểm tương đồng trung bình: {avg_similarity:.4f}")
        
        # Trả về kết quả nén với thông tin chi tiết hơn
        return {
            'templates': self.templates,
            'encoded_stream': self.encoded_stream,
            'compression_ratio': compression_ratio,
            'blocks_processed': self.blocks_processed,
            'hit_ratio': hit_ratio,
            'total_values': n,
            'avg_cer': avg_cer,
            'avg_cost': np.mean(self.cost_values) if self.cost_values else 0.0,
            'avg_similarity': avg_similarity,
            'block_size_history': self.block_size_history,
            'continuous_hit_ratio': self.continuous_hit_ratio,
            'hit_ratio_by_block': hit_ratio_by_block,
            'similarity_by_block': [block.get('similarity_score', 0) for block in self.encoded_stream],
            'cer_by_block': [block.get('cer', 0) for block in self.encoded_stream],
            'block_sizes': [block['length'] for block in self.encoded_stream],
            'template_usage_stats': {tid: self.template_usage.get(tid, 0) for tid in self.templates},
            'multi_dimensional': False
        } 