# Hướng dẫn sử dụng công cụ giải nén dữ liệu IDEALEM

## Trường hợp không cần giải nén mà muốn sử dụng gốc 

Vui lòng tham khảo bảng: original_samples

## Tổng quan nguồn và đầu ra dữ liệu

**compressed_data**: Dùng để lưu dữ liệu sau khi nén, chỉ tập trung vào các mẫu để so sánh
**compressed_data_optimized**: Dùng để lưu dữ liệu sau khi nén để phục vụ cho giải nén sau này
**<name_device>.json**: đầu ra của dữ liệu sau khi đã được giải nén

## Trước khi sử dụng nén và giải nén

Đảm bảo bảng original_samples có dữ liệu. 

Dùng lệnh tạo giả lập nếu cần: 


```bash
python templates/gentwo.py --device-id <name_device> --num-days <number>
```

Dữ liệu sẽ được lưu vào bảng original_samples.

## Sử dụng

### Sử dụng cơ bản cho nén

Muốn nén dữ liệu và lưu vào trong bảng compressed_data:

```bash
python compress.py --device-id <name_device>
```

Muốn nén dữ liệu và tạo biểu đồ so sánh: 

```bash
python compress.py --device-id <name_device> --visualize
```

Muốn nén dữ liệu và sau này giải nén, sẽ được lưu vào bảng compressed_data_optimized: 

```bash
python compress.py --device-id <name_device> --use-optimized
```

### Sử dụng cơ bản cho giải nén

```bash
python decompress.py --device-id <name_device>
```

Lệnh này sẽ giải nén tất cả dữ liệu của thiết bị đó nằm trong bảng compressed_data_optimized và lưu kết quả vào file `<name_device>.json`.

### Tham số

- `--h`: help

## Cấu trúc dữ liệu đầu ra


## Lưu ý

- Quá trình giải nén hoạt động tốt nhất khi bảng `original_samples` có đầy đủ dữ liệu.
- Thời gian xử lý có thể tăng lên nếu lượng dữ liệu lớn, hãy sử dụng tham số `--start-date` và `--end-date` để lọc dữ liệu trong khoảng thời gian cụ thể. 
