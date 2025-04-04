-- Xóa bảng cũ
DROP TABLE IF EXISTS original_samples CASCADE;

-- Tạo lại bảng với cấu trúc mới
CREATE TABLE original_samples (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR REFERENCES devices(device_id),
    value NUMERIC(10,2) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_device
        FOREIGN KEY(device_id) 
        REFERENCES devices(device_id)
);

-- Tạo các index cần thiết
CREATE INDEX idx_original_samples_device_id ON original_samples(device_id);
CREATE INDEX idx_original_samples_timestamp ON original_samples(timestamp);
CREATE INDEX idx_original_samples_value ON original_samples(value); 