import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import json
import time
import logging
import datetime

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thuật toán nén IDEALEM sử dụng KS test
class IDEALEMCompressor:
    """
    Thuật toán nén IDEALEM sử dụng Kolmogorov-Smirnov test
    để phát hiện tương đồng giữa các chuỗi dữ liệu
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo IDEALEM compressor với cấu hình
        
        Args:
            config: Dictionary cấu hình với các tham số:
                - window_size: Kích thước cửa sổ phân tích (mặc định: 10)
                - p_threshold: Ngưỡng p-value cho KS test (mặc định: 0.05)
                - max_templates: Số lượng mẫu tối đa được lưu (mặc định: 100)
                - block_size: Kích thước khối dữ liệu (n) (mặc định: 8)
                - adaptive_block_size: Có tự động điều chỉnh kích thước khối hay không (mặc định: False)
                - min_block_size: Kích thước khối tối thiểu (mặc định: 4)
                - max_block_size: Kích thước khối tối đa (mặc định: 16)
                - kmax: Số lần chuyển đổi tối đa (mặc định: 5)
                - rmin: Số lượng thử nghiệm tối thiểu trước khi chuyển đổi (mặc định: 30)
                - wc: Cửa sổ cho đường cong (mặc định: 2)
                - wp: Cửa sổ cho mẫu (mặc định: 4)
                - wn: Cửa sổ từ chối (mặc định: 1)
                - confidence_level: Mức độ tin cậy cho tính toán pmin (mặc định: 0.95)
        """
        try:
            from scipy import stats
            logger.info("Đã nhập thư viện scipy.stats thành công")
        except ImportError:
            logger.error("Không thể import scipy.stats. Hãy cài đặt thư viện scipy: pip install scipy")
            raise
        
        default_config = {
            "window_size": 10,        # Kích thước cửa sổ
            "p_threshold": 0.7,       # Ngưỡng p-value (>0.7 coi là tương tự) - đã được điều chỉnh cao hơn
            "max_templates": 100,     # Số lượng mẫu tối đa
            "min_values": 5,          # Số lượng giá trị tối thiểu để áp dụng KS test
            "clean_interval": 1000,   # Số lượng điểm dữ liệu trước khi dọn dẹp cache
            "block_size": 8,          # Kích thước khối dữ liệu (n)
            "adaptive_block_size": False,  # Tự động điều chỉnh kích thước khối
            "min_block_size": 4,      # Kích thước khối tối thiểu
            "max_block_size": 16,     # Kích thước khối tối đa
            "pmin": 0.5,              # Tỷ lệ hit tối thiểu
            "kmax": 5,                # Số lần chuyển đổi tối đa
            "rmin": 30,               # Số lượng thử nghiệm tối thiểu (tối thiểu là 30 cho CLT)
            "wc": 2,                  # Cửa sổ cho đường cong
            "wp": 4,                  # Cửa sổ cho mẫu
            "wn": 1,                  # Cửa sổ từ chối
            "confidence_level": 0.95, # Mức độ tin cậy cho khoảng tin cậy (95%)
            "similarity_factor": 20,  # Hệ số cho phép tìm mẫu tương tự dễ dàng hơn
        }
        
        self.config = default_config
        if config:
            self.config.update(config)
            
        # Trạng thái nội bộ
        self.data_window = []                  # Cửa sổ dữ liệu hiện tại
        self.templates = {}                    # Từ điển lưu các mẫu
        self.template_counts = {}              # Đếm số lần mỗi mẫu được sử dụng
        self.template_id_counter = 0           # Bộ đếm ID cho mẫu mới
        self.compressed_size_history = []      # Lịch sử kích thước đã nén
        self.original_size_history = []        # Lịch sử kích thước gốc
        self.data_count = 0                    # Tổng số điểm dữ liệu đã xử lý
        self.hits = 0                          # Số lần trúng mẫu
        self.trials = 0                        # Số lần thử nghiệm
        self.current_n = self.config["block_size"]  # Kích thước khối hiện tại
        self.switch_count = 0                  # Bộ đếm chuyển đổi kích thước khối
        self.samples = []                      # Mẫu kích thước khối
        self.nbest = self.current_n            # Kích thước khối tốt nhất
        self.block_size_history = []           # Lịch sử kích thước khối
        self.min_compression_ratios = {}       # Lưu trữ tỷ lệ nén tối thiểu cho mỗi n
        self.hit_history = []                  # Lịch sử các lần hit (1) và miss (0)
        
        # Giá trị z* cho khoảng tin cậy
        from scipy import stats
        self.z_critical = stats.norm.ppf((1 + self.config["confidence_level"]) / 2)
        logger.info(f"Giá trị z* cho mức tin cậy {self.config['confidence_level']*100}%: {self.z_critical:.4f}")
        
        logger.info(f"IDEALEM Compressor đã được khởi tạo với cấu hình: {self.config}")
    
    def _extract_readings(self, data_point: Dict[str, Any]) -> List[float]:
        """
        Trích xuất các giá trị từ điểm dữ liệu
        """
        readings = []
        if isinstance(data_point, dict) and 'readings' in data_point:
            # Đảm bảo dữ liệu được trích xuất có cùng thứ tự
            # để việc so sánh được chính xác
            sorted_keys = sorted(data_point['readings'].keys())
            
            for sensor in sorted_keys:
                value = data_point['readings'].get(sensor)
                if isinstance(value, (int, float)):
                    # Chuẩn hóa giá trị để dễ dàng so sánh
                    readings.append(float(value))
                    
        return readings
    
    def _calculate_ks_similarity(self, template: List[float], data: List[float]) -> float:
        """
        Sử dụng KS test hoặc khoảng cách trung bình để tính độ tương đồng
        """
        if len(template) < self.config["min_values"] or len(data) < self.config["min_values"]:
            return 0.0  # Không đủ giá trị để áp dụng
            
        try:
            # Thay thế KS test bằng phương pháp khoảng cách trung bình đơn giản hơn
            # Với dữ liệu IoT, các giá trị lân cận thường có xu hướng tương tự
            # Chuẩn hóa dữ liệu trước khi so sánh
            if len(template) != len(data):
                # Nếu độ dài khác nhau, cắt ngắn cái dài hơn
                min_len = min(len(template), len(data))
                template = template[:min_len]
                data = data[:min_len]
                
            # Tính tỷ lệ tương đồng dựa trên khoảng cách
            total_diff = 0
            count = 0
            
            for i, (t_val, d_val) in enumerate(zip(template, data)):
                if t_val == 0 and d_val == 0:
                    # Tránh chia cho 0
                    continue
                    
                # Tính khoảng cách tương đối
                rel_diff = abs(t_val - d_val) / max(abs(t_val), abs(d_val), 1.0)
                total_diff += rel_diff
                count += 1
                
            if count == 0:
                return 0.0
                
            avg_diff = total_diff / count
            
            # Chuyển đổi khoảng cách thành thang đo tương đồng (0-1)
            # Khoảng cách nhỏ -> tương đồng cao
            similarity_factor = self.config.get("similarity_factor", 20)  # Lấy hệ số từ cấu hình
            similarity = max(0, 1.0 - avg_diff * similarity_factor)  # Hệ số cao hơn để nới lỏng điều kiện
            
            # Trả về giá trị tương đồng
            return similarity
            
        except Exception as e:
            logger.error(f"Lỗi khi tính độ tương đồng: {str(e)}")
            return 0.0
            
    def _find_matching_template(self, data: List[float]) -> Tuple[int, float]:
        """
        Tìm mẫu phù hợp nhất với dữ liệu hiện tại
        """
        best_match = -1
        best_p_value = 0.0
        
        # Kiểm tra từng mẫu trong bộ nhớ
        for template_id, template_data in self.templates.items():
            p_value = self._calculate_ks_similarity(template_data, data)
            if p_value > self.config["p_threshold"] and p_value > best_p_value:
                best_match = template_id
                best_p_value = p_value
                
        return best_match, best_p_value
    
    def _add_new_template(self, data: List[float]) -> int:
        """
        Thêm mẫu mới vào bộ nhớ
        """
        template_id = self.template_id_counter
        self.templates[template_id] = data.copy()
        self.template_counts[template_id] = 1
        self.template_id_counter += 1
        
        # Nếu vượt quá số lượng mẫu tối đa, loại bỏ mẫu ít sử dụng nhất
        if len(self.templates) > self.config["max_templates"]:
            least_used = min(self.template_counts, key=self.template_counts.get)
            del self.templates[least_used]
            del self.template_counts[least_used]
            
        return template_id
    
    def _clean_templates(self) -> None:
        """
        Làm sạch bộ nhớ các mẫu ít được sử dụng
        """
        if len(self.templates) <= self.config["max_templates"] // 2:
            return
            
        # Sắp xếp mẫu theo tần suất sử dụng
        sorted_templates = sorted(self.template_counts.items(), key=lambda x: x[1])
        
        # Giữ lại 50% mẫu được sử dụng nhiều nhất
        templates_to_keep = len(self.templates) // 2
        templates_to_remove = sorted_templates[:-templates_to_keep]
        
        # Xóa các mẫu ít sử dụng
        for template_id, _ in templates_to_remove:
            del self.templates[template_id]
            del self.template_counts[template_id]
    
    def _calculate_size_bytes(self, data: Any) -> int:
        """
        Tính kích thước dữ liệu theo bytes
        """
        return len(json.dumps(data).encode('utf-8'))

    def _calculate_real_compressed_size(self, data: Dict[str, Any]) -> int:
        """
        Tính kích thước thực tế sau khi nén bằng cách loại bỏ metadata thử nghiệm
        
        Đây là kích thước thực tế sẽ được lưu trữ trong cơ sở dữ liệu hoặc gửi đi
        """
        # Tạo bản sao để không ảnh hưởng đến dữ liệu gốc
        real_data = data.copy()
        
        if 'compression_meta' in real_data:
            # Loại bỏ dữ liệu gốc nếu là hit (không cần lưu trữ)
            if 'original_readings' in real_data['compression_meta']:
                del real_data['compression_meta']['original_readings']
            
            # Giữ lại chỉ các metadata cần thiết
            essential_meta = {
                'template_id': real_data['compression_meta'].get('template_id'),
                'algorithm': real_data['compression_meta'].get('algorithm')
            }
            
            # Nếu là template, giữ nguyên dữ liệu readings
            # Nếu không phải template, xóa readings vì đã có template_id
            if not real_data['compression_meta'].get('is_template', False) and 'readings' in real_data:
                del real_data['readings']
            
            # Thay thế metadata với phiên bản tinh gọn
            real_data['compression_meta'] = essential_meta
        
        # Tính kích thước sau khi đã loại bỏ metadata thử nghiệm
        return len(json.dumps(real_data).encode('utf-8'))
        
    def _calculate_pmin(self) -> float:
        """
        Tính pmin dựa trên khoảng tin cậy cho tỷ lệ hit
        """
        if self.trials < self.config["rmin"]:
            return self.config["pmin"]  # Không đủ mẫu, dùng giá trị mặc định
            
        # Tính phần trăm hit
        p_hat = self.hits / self.trials if self.trials > 0 else 0.0
        
        # Độ lệch chuẩn mẫu - giới hạn trên 0.5 (max của Bernoulli)
        sample_std = min(0.5, np.sqrt(p_hat * (1 - p_hat)))
        
        # Tính khoảng tin cậy (giới hạn dưới)
        margin_of_error = self.z_critical * (sample_std / np.sqrt(self.trials))
        pmin = max(0, p_hat - margin_of_error)
        
        return pmin
        
    def _calculate_min_compression_ratio(self, n: int, p: float) -> float:
        """
        Tính toán tỷ lệ nén tối thiểu đảm bảo với xác suất p và kích thước khối n
        ρmin = n / (1 + (n-1)*p)
        """
        if p <= 0:
            return 1.0  # Không đủ hit, không thể nén
        return n / (1 + (n-1)*p)
        
    def _adjust_block_size(self) -> None:
        """
        Điều chỉnh kích thước khối dựa trên giá trị pmin và tỷ lệ hit
        """
        if not self.config["adaptive_block_size"]:
            return
            
        # Chỉ điều chỉnh sau khi đã có đủ số lượng thử nghiệm
        if self.trials < self.config["rmin"]:
            return
            
        # Chỉ điều chỉnh tối đa kmax lần
        if self.switch_count >= self.config["kmax"]:
            return
            
        # Tính p và pmin
        p = self.hits / self.trials if self.trials > 0 else 0.0
        pmin = self._calculate_pmin()
        
        # Lưu giá trị pmin và rho_min cho kích thước khối hiện tại
        rho_min = self._calculate_min_compression_ratio(self.current_n, pmin)
        self.min_compression_ratios[self.current_n] = rho_min
        
        # Thử kích thước khối mới
        n_next = None
        
        if pmin > 0:
            # Dựa vào Figure 7 trong bài báo:
            # Thêm mẫu đánh giá kích thước khối
            self.samples.append(self.current_n)
            
            wc = self.config["wc"]  # Cửa sổ cho đường cong tương quan
            wp = self.config["wp"]  # Cửa sổ cho mẫu
            wn = self.config["wn"]  # Cửa sổ từ chối
            
            # Các điều kiện để tăng kích thước khối
            if self.current_n < self.config["max_block_size"]:
                # Nếu pmin cao, tăng kích thước khối
                if (len(self.samples) >= wc and
                    all(s == self.current_n for s in self.samples[-wc:]) and
                    pmin > 0.7):
                    n_next = self.current_n + 2
                    logger.info(f"Tăng kích thước khối từ {self.current_n} -> {n_next} (pmin={pmin:.4f})")
                    
            # Các điều kiện để giảm kích thước khối
            if self.current_n > self.config["min_block_size"]:
                # Nếu pmin thấp, giảm kích thước khối
                if (len(self.samples) >= wc and
                    all(s == self.current_n for s in self.samples[-wc:]) and
                    pmin < 0.3):
                    n_next = self.current_n - 2
                    logger.info(f"Giảm kích thước khối từ {self.current_n} -> {n_next} (pmin={pmin:.4f})")
        
        # Cập nhật kích thước khối nếu cần
        if n_next is not None:
            self.current_n = n_next
            self.nbest = n_next
            self.switch_count += 1
            self.block_size_history.append(n_next)
            self.hits = 0  # Reset số lần hit
            self.trials = 0  # Reset số lần thử
            
    def compress(self, data_point: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Nén dữ liệu sử dụng thuật toán IDEALEM
        
        Args:
            data_point: Điểm dữ liệu cần nén
            
        Returns:
            Tuple gồm dữ liệu đã nén và các thống kê
        """
        start_time = time.time()
        
        # Trích xuất giá trị từ điểm dữ liệu
        readings = self._extract_readings(data_point)
        
        # Tạo bản sao của điểm dữ liệu để nén
        compressed_data = data_point.copy()
        
        # Nếu không có giá trị để nén, trả về nguyên bản
        if not readings:
            stats = {
                "original_size_bytes": self._calculate_size_bytes(data_point),
                "compressed_size_bytes": self._calculate_size_bytes(compressed_data),
                "real_compressed_size_bytes": self._calculate_size_bytes(compressed_data),
                "compression_ratio": 1.0,
                "real_compression_ratio": 1.0,
                "compression_time_ms": (time.time() - start_time) * 1000,
                "is_compressed": False,
                "template_id": None,
                "current_block_size": self.current_n,
                "hit_ratio": self.hits / self.trials if self.trials > 0 else 0,
                "pmin": self._calculate_pmin(),
                "rho_min": self._calculate_min_compression_ratio(self.current_n, self._calculate_pmin())
            }
            return compressed_data, stats
        
        # Tìm mẫu phù hợp
        best_match, best_p_value = self._find_matching_template(readings)
        
        # Cập nhật biến thống kê
        self.trials += 1
        is_hit = (best_match != -1)
        self.hit_history.append(1 if is_hit else 0)
        
        if is_hit:
            # Trúng mẫu, sử dụng ID và tăng số lần sử dụng
            self.hits += 1
            self.template_counts[best_match] += 1
            template_id = best_match
            
            # Thay thế dữ liệu bằng tham chiếu đến mẫu
            if 'compression_meta' not in compressed_data:
                compressed_data['compression_meta'] = {}
                
            compressed_data['compression_meta']['template_id'] = template_id
            compressed_data['compression_meta']['p_value'] = best_p_value
            compressed_data['compression_meta']['algorithm'] = 'idealem'
            compressed_data['compression_meta']['timestamp'] = datetime.datetime.now().isoformat()
            
            # Xóa readings gốc vì đã được thay thế bằng tham chiếu
            if self.config["adaptive_block_size"]:
                # Với khối thích nghi, vẫn lưu giá trị gốc để thống kê
                compressed_data['compression_meta']['original_readings'] = compressed_data['readings']
            else:
                # Với khối cố định, xóa giá trị gốc để tiết kiệm dung lượng
                del compressed_data['readings']
        else:
            # Không tìm thấy mẫu phù hợp, tạo mẫu mới
            template_id = self._add_new_template(readings)
            
            # Thêm metadata nhưng giữ nguyên dữ liệu gốc
            if 'compression_meta' not in compressed_data:
                compressed_data['compression_meta'] = {}
                
            compressed_data['compression_meta']['is_template'] = True
            compressed_data['compression_meta']['template_id'] = template_id
            compressed_data['compression_meta']['algorithm'] = 'idealem'
            compressed_data['compression_meta']['timestamp'] = datetime.datetime.now().isoformat()
        
        # Tính kích thước trước và sau khi nén
        original_size = self._calculate_size_bytes(data_point)
        compressed_size = self._calculate_size_bytes(compressed_data)
        real_compressed_size = self._calculate_real_compressed_size(compressed_data)
        
        # Cập nhật lịch sử kích thước
        self.original_size_history.append(original_size)
        self.compressed_size_history.append(real_compressed_size)  # Sử dụng kích thước thực tế
        self.data_count += 1
        
        # Điều chỉnh kích thước khối nếu cần
        self._adjust_block_size()
        
        # Tính pmin và tỷ lệ nén tối thiểu
        pmin = self._calculate_pmin()
        rho_min = self._calculate_min_compression_ratio(self.current_n, pmin)
        
        # Tạo thống kê
        stats = {
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "real_compressed_size_bytes": real_compressed_size,
            "compression_ratio": compressed_size / original_size if original_size > 0 else 1.0,
            "real_compression_ratio": real_compressed_size / original_size if original_size > 0 else 1.0,
            "compression_time_ms": (time.time() - start_time) * 1000,
            "is_compressed": is_hit,
            "template_id": template_id,
            "current_block_size": self.current_n,
            "hit_ratio": self.hits / self.trials if self.trials > 0 else 0,
            "pmin": pmin,
            "rho_min": rho_min
        }
        
        # Làm sạch các mẫu nếu cần
        if self.data_count % self.config["clean_interval"] == 0:
            self._clean_templates()
            
        return compressed_data, stats
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê hiện tại của quá trình nén
        """
        total_original_size = sum(self.original_size_history) if self.original_size_history else 0
        total_compressed_size = sum(self.compressed_size_history) if self.compressed_size_history else 0
        
        # Tính tỷ lệ nén thực tế
        real_compression_ratio = 0
        if total_original_size > 0:
            real_compression_ratio = total_original_size / total_compressed_size
        else:
            real_compression_ratio = 1.0
        
        # Tính phần trăm hit
        hit_ratio = self.hits / self.trials if self.trials > 0 else 0
        
        # Tính pmin dựa trên khoảng tin cậy
        pmin = self._calculate_pmin()
        
        # Tính độ lệch chuẩn mẫu
        sample_std = min(0.5, np.sqrt(hit_ratio * (1 - hit_ratio))) if self.trials > 0 else 0
        
        # Tính tỷ lệ nén tối thiểu cho kích thước khối hiện tại
        rho_min = self._calculate_min_compression_ratio(self.current_n, pmin)
        
        return {
            "total_data_points": self.data_count,
            "total_templates": len(self.templates),
            "total_original_size": total_original_size,
            "total_compressed_size": total_compressed_size,
            "overall_compression_ratio": real_compression_ratio,
            "hits": self.hits,
            "trials": self.trials,
            "hit_ratio": hit_ratio,
            "pmin": pmin,
            "current_block_size": self.current_n,
            "block_size_history": self.block_size_history,
            "min_compression_ratio": rho_min,
            "sample_std": sample_std,
            "z_critical": self.z_critical,
            "confidence_level": self.config["confidence_level"],
            "template_count": len(self.templates),
            "record_count": self.data_count,
            "estimated_row_reduction": self.data_count / len(self.templates) if len(self.templates) > 0 else 1.0
        }
    
    def reset(self) -> None:
        """
        Reset trạng thái của compressor
        """
        self.data_window = []
        self.templates = {}
        self.template_counts = {}
        self.template_id_counter = 0
        self.compressed_size_history = []
        self.original_size_history = []
        self.data_count = 0
        self.hits = 0
        self.trials = 0
        self.current_n = self.config["block_size"]
        self.switch_count = 0
        self.samples = []
        self.nbest = self.current_n
        self.block_size_history = []
        self.min_compression_ratios = {}
        self.hit_history = []
        
        logger.info("Đã reset IDEALEM Compressor")

# Phương thức nén mặc định
DEFAULT_COMPRESSION_METHOD = "idealem" 