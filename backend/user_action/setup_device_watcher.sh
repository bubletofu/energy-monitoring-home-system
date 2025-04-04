#!/bin/bash
# Script để cài đặt dịch vụ theo dõi thiết bị thông qua crontab

# Đảm bảo script được chạy với quyền sudo
if [ "$EUID" -ne 0 ]; then
  echo "Vui lòng chạy script với quyền sudo"
  exit 1
fi

# Lấy thư mục hiện tại
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Tạo file log
LOGFILE="$ROOT_DIR/device_watcher.log"
touch $LOGFILE
chmod 666 $LOGFILE

# Cài đặt package python nếu cần
pip install schedule requests sqlalchemy psycopg2-binary python-dotenv

# Đường dẫn đến watching.py
WATCHER_SCRIPT="$SCRIPT_DIR/watching.py"
chmod +x $WATCHER_SCRIPT

# Tạo crontab entry để chạy script mỗi 5 phút
CRON_COMMAND="*/5 * * * * cd $ROOT_DIR && python $WATCHER_SCRIPT --check-interval 5 --offline-threshold 10 >> $LOGFILE 2>&1"

# Kiểm tra nếu crontab entry đã tồn tại
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -F "$WATCHER_SCRIPT")

if [ -z "$EXISTING_CRON" ]; then
  # Thêm crontab entry mới
  (crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -
  echo "Đã cài đặt dịch vụ theo dõi thiết bị. Script sẽ chạy mỗi 5 phút."
else
  echo "Dịch vụ theo dõi thiết bị đã được cài đặt trước đó."
fi

# Tạo file systemd service cho chạy dịch vụ nền (nếu muốn)
SERVICE_FILE="/etc/systemd/system/device-watcher.service"

cat > $SERVICE_FILE << EOL
[Unit]
Description=Device Status Watcher Service
After=network.target

[Service]
Type=simple
User=$(logname)
WorkingDirectory=$ROOT_DIR
ExecStart=/usr/bin/python3 $WATCHER_SCRIPT --daemon
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=device-watcher

[Install]
WantedBy=multi-user.target
EOL

echo "Đã tạo file service systemd: $SERVICE_FILE"
echo "Để kích hoạt service, chạy các lệnh sau:"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable device-watcher.service"
echo "  sudo systemctl start device-watcher.service"

echo ""
echo "Lựa chọn cách chạy dịch vụ:"
echo "1. Chạy mỗi 5 phút qua crontab (đã cài đặt)"
echo "2. Chạy như dịch vụ nền liên tục qua systemd"
echo ""
echo "Vui lòng chọn một trong hai phương pháp trên để tránh chạy trùng lặp." 