from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PYDEPS_DIR = ROOT_DIR / ".pydeps"
if PYDEPS_DIR.exists():
    sys.path.insert(0, str(PYDEPS_DIR))

import paramiko


DEFAULT_REMOTE_DIR = "/home/pi/project4-iot"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy iot_client.py to a remote device and register a systemd service.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default="pi")
    parser.add_argument("--password", required=True)
    parser.add_argument("--remote-dir", default="", help="Remote deployment directory (default: auto based on user)")
    parser.add_argument("--server", required=True, help="Backend base URL, e.g. http://192.168.31.46:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--point-id", type=int, default=0)
    parser.add_argument("--route-id", type=int, default=0)
    parser.add_argument("--gps-timeout", type=int, default=5)
    parser.add_argument("--gps-serial-device", default="")
    parser.add_argument("--gps-serial-baud", type=int, default=9600)
    parser.add_argument("--gps-log-every", type=int, default=10)
    parser.add_argument("--network-locate-enabled", action="store_true")
    parser.add_argument("--network-provider", default="google")
    parser.add_argument("--network-api-key", default="")
    parser.add_argument("--network-api-url", default="https://www.googleapis.com/geolocation/v1/geolocate")
    parser.add_argument("--network-timeout", type=int, default=10)
    parser.add_argument("--network-interface", default="wlan0")
    parser.add_argument("--network-consider-ip", type=int, default=1)
    parser.add_argument("--ros", action="store_true", help="Deploy ros_iot_bridge.py for ROS devices (LiDAR/stereo/camera topics)")
    parser.add_argument("--camera-device", default="", help="Local camera device path (e.g. /dev/video0)")
    parser.add_argument("--camera-interval", type=int, default=10)
    parser.add_argument("--lidar-topic", default="/scan_raw")
    parser.add_argument("--camera-topic", default="/camera/rgb/image_raw/compressed")
    parser.add_argument("--stereo-left-topic", default="")
    parser.add_argument("--stereo-right-topic", default="")
    parser.add_argument("--depth-topic", default="", help="Raw ROS depth Image topic to upload as channel=depth")
    parser.add_argument("--lidar-interval", type=int, default=1)
    parser.add_argument("--ros-sensor-interval", type=int, default=10)
    return parser.parse_args()


def sftp_write_text(sftp: paramiko.SFTPClient, remote_path: str, content: str) -> None:
    with sftp.file(remote_path, "w") as remote_file:
        remote_file.write(content)


def main() -> int:
    args = parse_args()
    local_client = ROOT_DIR / "scripts" / "iot_client.py"
    local_bridge = ROOT_DIR / "scripts" / "ros_iot_bridge.py"
    if not local_client.exists():
        print(f"Missing file: {local_client}", file=sys.stderr)
        return 1
    if args.ros and not local_bridge.exists():
        print(f"Missing file: {local_bridge}", file=sys.stderr)
        return 1

    remote_dir = args.remote_dir or (f"/home/{args.user}/project4-iot" if args.user != "pi" else DEFAULT_REMOTE_DIR)
    service_name = "project4-iot.service"
    config_text = "\n".join(
        [
            "[client]",
            f"server = {args.server}",
            f"token = {args.token}",
            f"interval = {args.interval}",
            f"point_id = {args.point_id}",
            f"route_id = {args.route_id}",
            f"gps_timeout = {args.gps_timeout}",
            f"gps_serial_device = {args.gps_serial_device}",
            f"gps_serial_baud = {args.gps_serial_baud}",
            f"gps_log_every = {args.gps_log_every}",
            f"network_locate_enabled = {1 if args.network_locate_enabled else 0}",
            f"network_provider = {args.network_provider}",
            f"network_api_key = {args.network_api_key}",
            f"network_api_url = {args.network_api_url}",
            f"network_timeout = {args.network_timeout}",
            f"network_interface = {args.network_interface}",
            f"network_consider_ip = {args.network_consider_ip}",
            f"camera_device = {args.camera_device}",
            f"camera_interval = {args.camera_interval}",
            "",
        ]
    )
    if args.ros:
        config_text += "\n".join([
            "[sensors]",
            f"camera_topic = {args.camera_topic}",
            f"stereo_left_topic = {args.stereo_left_topic}",
            f"stereo_right_topic = {args.stereo_right_topic}",
            f"depth_topic = {args.depth_topic}",
            f"lidar_topic = {args.lidar_topic}",
            f"camera_interval = {args.ros_sensor_interval}",
            f"lidar_interval = {args.lidar_interval}",
            "",
        ])
    service_text = "\n".join(
        [
            "[Unit]",
            f"Description=Project4 {'ROS IoT Bridge' if args.ros else 'IoT Client'}",
            f"After=network-online.target{' project4-ros-base.service' if args.ros else ''}",
            "Wants=network-online.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={remote_dir}",
            "Environment=PYTHONUNBUFFERED=1",
            (
                f"ExecStart=/bin/bash -c 'source /opt/ros/noetic/setup.bash && "
                f"source /home/{args.user}/wheeltec_robot/devel/setup.bash 2>/dev/null; "
                f"/usr/bin/python3 {remote_dir}/ros_iot_bridge.py --config {remote_dir}/iot_client.conf'"
                if args.ros else
                f"ExecStart=/usr/bin/python3 {remote_dir}/iot_client.py --config {remote_dir}/iot_client.conf"
            ),
            "Restart=always",
            "RestartSec=5",
            f"User={args.user}",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=args.host, username=args.user, password=args.password, timeout=10, banner_timeout=10, auth_timeout=10)
    try:
        sftp = client.open_sftp()
        try:
            client.exec_command(f"mkdir -p {remote_dir}")
            sftp.put(str(local_client), f"{remote_dir}/iot_client.py")
            sftp_write_text(sftp, f"{remote_dir}/iot_client.conf", config_text)
            if args.ros:
                sftp.put(str(local_bridge), f"{remote_dir}/ros_iot_bridge.py")
                print(f"uploaded ros_iot_bridge.py -> {remote_dir}/ros_iot_bridge.py")
        finally:
            sftp.close()

        commands = [
            f"chmod +x {remote_dir}/iot_client.py",
            f"printf '%s\\n' \"{args.password}\" | sudo -S apt-get update -y",
            f"printf '%s\\n' \"{args.password}\" | sudo -S apt-get install -y python3",
            f"cat > /tmp/{service_name} <<'EOF'\n{service_text}EOF",
            f"printf '%s\\n' \"{args.password}\" | sudo -S mv /tmp/{service_name} /etc/systemd/system/{service_name}",
            f"printf '%s\\n' \"{args.password}\" | sudo -S systemctl daemon-reload",
            f"printf '%s\\n' \"{args.password}\" | sudo -S systemctl enable {service_name}",
            f"printf '%s\\n' \"{args.password}\" | sudo -S systemctl restart {service_name}",
            f"printf '%s\\n' \"{args.password}\" | sudo -S systemctl status {service_name} --no-pager",
        ]
        for command in commands:
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)
            output = stdout.read().decode("utf-8", "replace")
            error = stderr.read().decode("utf-8", "replace")
            if output:
                print(output)
            if error:
                print(error, file=sys.stderr)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
