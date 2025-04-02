# Xóa Bảng REF khỏi Hệ Thống

Tài liệu này mô tả quá trình xóa bảng `ref` không còn cần thiết khỏi cơ sở dữ liệu.

## Lý do xóa bảng `ref`

Bảng `ref` ban đầu được sử dụng để lưu trữ tham chiếu giữa dữ liệu gốc và dữ liệu nén. Trong phiên bản mới của hệ thống, chúng tôi đã tối ưu hóa cấu trúc bảng và quy trình nén dữ liệu, làm cho bảng `ref` trở nên không cần thiết. Những lý do chính:

1. **Đã chuyển sang bảng `compressed_data_optimized`**: Bảng mới này lưu trữ tất cả thông tin nén cần thiết mà không cần đến bảng ref.
2. **Tăng hiệu suất**: Loại bỏ bảng `ref` giúp giảm số lượng truy vấn JOIN và làm đơn giản hóa quy trình truy vấn dữ liệu.
3. **Giảm dung lượng lưu trữ**: Không cần lưu thông tin trùng lặp.
4. **Đơn giản hóa cấu trúc dữ liệu**: Ít bảng hơn, quản lý dễ dàng hơn.

## Các thay đổi đã thực hiện

1. Đã cập nhật `models.py` để xóa class `Ref`
2. Đã cập nhật `compress.py` để loại bỏ các tham chiếu đến bảng `ref` và hàm `save_ref_data`
3. Đã cập nhật `table.py` để xóa import của class `Ref`
4. Đã cập nhật `visualization_analyzer.py` để loại bỏ JOIN với bảng `ref`
5. Tạo script `drop_ref_table.py` để xóa bảng khỏi cơ sở dữ liệu

## Cách xóa bảng `ref` khỏi cơ sở dữ liệu

### Bước 1: Sao lưu dữ liệu (khuyến nghị)

Trước khi xóa bất kỳ bảng nào, bạn nên sao lưu cơ sở dữ liệu:

```bash
pg_dump -U postgres -h localhost -p 5433 -d iot_db > iot_db_backup_$(date +%Y%m%d).sql
```

### Bước 2: Chạy script xóa bảng

```bash
python drop_ref_table.py
```

Script sẽ yêu cầu xác nhận trước khi xóa bảng. Nhập `XÓA` để xác nhận.

### Bước 3: Kiểm tra logs

Script tạo file log `drop_table.log` - kiểm tra file này để xem chi tiết về quá trình xóa bảng.

## Lưu ý quan trọng

1. **Không thể phục hồi**: Khi bảng đã bị xóa, dữ liệu sẽ bị mất vĩnh viễn nếu không có bản sao lưu.
2. **Ứng dụng tương thích**: Đảm bảo rằng bạn đã cập nhật tất cả mã nguồn sử dụng bảng `ref` trước khi xóa nó.
3. **Các vấn đề có thể gặp phải**: Nếu có bất kỳ công cụ hoặc script nào vẫn đang sử dụng bảng `ref`, chúng sẽ bị lỗi sau khi bảng bị xóa.

## Thông tin liên hệ

Nếu gặp vấn đề trong quá trình xóa bảng `ref`, vui lòng liên hệ với người phụ trách hệ thống. 