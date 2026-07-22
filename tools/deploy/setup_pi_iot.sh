#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: bash setup_pi_iot.sh <SERVER_URL> <DEVICE_TOKEN> [INTERVAL] [POINT_ID] [ROUTE_ID] [GPS_SERIAL_DEVICE] [GPS_SERIAL_BAUD]"
  exit 1
fi

SERVER_URL="$1"
DEVICE_TOKEN="$2"
INTERVAL="${3:-60}"
POINT_ID="${4:-0}"
ROUTE_ID="${5:-0}"
GPS_SERIAL_DEVICE="${6:-}"
GPS_SERIAL_BAUD="${7:-9600}"

APP_DIR="$HOME/project4-iot"
SERVICE_FILE="/etc/systemd/system/project4-iot.service"
SCRIPT_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$APP_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y python3
fi

if [[ ! -f "$SCRIPT_SOURCE_DIR/iot_client.py" ]]; then
  echo "Missing local file: $SCRIPT_SOURCE_DIR/iot_client.py"
  exit 1
fi

cp "$SCRIPT_SOURCE_DIR/iot_client.py" "$APP_DIR/iot_client.py"

cat > "$APP_DIR/iot_client.conf" <<EOF
[client]
server = ${SERVER_URL}
token = ${DEVICE_TOKEN}
interval = ${INTERVAL}
point_id = ${POINT_ID}
route_id = ${ROUTE_ID}
gps_timeout = 5
gps_serial_device = ${GPS_SERIAL_DEVICE}
gps_serial_baud = ${GPS_SERIAL_BAUD}
gps_log_every = 10
network_locate_enabled = 0
network_provider = google
network_api_key =
network_api_url = https://www.googleapis.com/geolocation/v1/geolocate
network_timeout = 10
network_interface = wlan0
network_consider_ip = 1
EOF

chmod +x "$APP_DIR/iot_client.py"

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=Project4 IoT Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 ${APP_DIR}/iot_client.py --config ${APP_DIR}/iot_client.conf
Restart=always
RestartSec=5
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable project4-iot.service
sudo systemctl restart project4-iot.service
sudo systemctl status project4-iot.service --no-pager
