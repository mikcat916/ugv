from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PYDEPS_DIR = ROOT_DIR / ".pydeps"
if PYDEPS_DIR.exists():
    sys.path.insert(0, str(PYDEPS_DIR))

import paramiko


@dataclass(frozen=True)
class DeployConfig:
    host: str
    user: str
    password: str
    server: str
    token: str
    root: str


def parse_args() -> DeployConfig:
    parser = argparse.ArgumentParser(description="Deploy Project4 services to a Wheeltec ROS robot.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default="wheeltec")
    parser.add_argument("--password", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--root", default="/home/wheeltec")
    args = parser.parse_args()
    return DeployConfig(
        host=args.host,
        user=args.user,
        password=args.password,
        server=args.server.rstrip("/"),
        token=args.token,
        root=args.root.rstrip("/"),
    )


def connect(config: DeployConfig) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=config.host,
        username=config.user,
        password=config.password,
        timeout=12,
        banner_timeout=12,
        auth_timeout=12,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def run(client: paramiko.SSHClient, config: DeployConfig, command: str, *, sudo: bool = False) -> None:
    if sudo:
        command = f"printf '%s\\n' '{config.password}' | sudo -S -p '' {command}"
    stdin, stdout, stderr = client.exec_command(command, get_pty=sudo, timeout=30)
    output = stdout.read().decode("utf-8", "replace")
    error = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if output:
        print(output)
    if error:
        print(error, file=sys.stderr)
    if code != 0:
        raise RuntimeError(f"remote command failed ({code}): {command}")


def sftp_write(sftp: paramiko.SFTPClient, path: str, content: str) -> None:
    with sftp.file(path, "w") as remote_file:
        remote_file.write(content)


def upload_files(client: paramiko.SSHClient, config: DeployConfig) -> None:
    scripts = {
        "project4-iot": ["ros_iot_bridge.py"],
        "project4-control": ["ros_control_bridge.py", "iot_control_poller.py"],
        "project4-camera": ["camera_mjpeg_server.py"],
    }
    run(client, config, "; ".join(f"mkdir -p {config.root}/{folder}" for folder in scripts))
    sftp = client.open_sftp()
    try:
        for folder, names in scripts.items():
            for name in names:
                sftp.put(str(ROOT_DIR / "scripts" / name), f"{config.root}/{folder}/{name}")
        sftp_write(sftp, f"{config.root}/project4-iot/iot_client.conf", iot_config(config))
        for name, service in service_files(config).items():
            sftp_write(sftp, f"/tmp/{name}", service)
    finally:
        sftp.close()


def iot_config(config: DeployConfig) -> str:
    return "\n".join(
        [
            "[client]",
            f"server = {config.server}",
            f"token = {config.token}",
            "interval = 15",
            "network_interface = wlan0",
            "network_consider_ip = 0",
            "",
            "[sensors]",
            "camera_topic = /usb_cam/image/compressed",
            "stereo_left_topic =",
            "stereo_right_topic =",
            "depth_topic = /camera/depth/image_raw",
            "lidar_topic = /scan",
            "camera_interval = 10",
            "lidar_interval = 1",
            "",
        ]
    )


def service_files(config: DeployConfig) -> dict[str, str]:
    return {
        "project4-ros-base.service": ros_base_service(config),
        "project4-iot.service": ros_iot_service(config),
        "project4-robot-control.service": ros_control_service(config),
        "project4-control-poller.service": control_poller_service(config),
        "project4-camera.service": camera_service(config),
    }


def ros_base_service(config: DeployConfig) -> str:
    return service_text(
        "Project4 ROS Base Driver",
        config,
        "network-online.target project4-roscore.service",
        "source /opt/ros/noetic/setup.bash && "
        f"source {config.root}/wheeltec_robot/devel/setup.bash && "
        f"roslaunch {config.root}/wheeltec_robot/src/turn_on_wheeltec_robot/launch/include/base_serial.launch",
        f"{config.root}/wheeltec_robot",
    )


def ros_iot_service(config: DeployConfig) -> str:
    return service_text(
        "Project4 ROS IoT Telemetry Bridge",
        config,
        "network-online.target project4-roscore.service project4-ros-base.service",
        "source /opt/ros/noetic/setup.bash && "
        f"source {config.root}/wheeltec_robot/devel/setup.bash && "
        f"/usr/bin/python3 {config.root}/project4-iot/ros_iot_bridge.py "
        f"--config {config.root}/project4-iot/iot_client.conf",
        f"{config.root}/project4-iot",
    )


def ros_control_service(config: DeployConfig) -> str:
    return service_text(
        "Project4 ROS Control Bridge",
        config,
        "network-online.target project4-roscore.service project4-ros-base.service",
        "source /opt/ros/noetic/setup.bash && "
        f"source {config.root}/wheeltec_robot/devel/setup.bash && "
        f"/usr/bin/python3 {config.root}/project4-control/ros_control_bridge.py",
        f"{config.root}/project4-control",
    )


def control_poller_service(config: DeployConfig) -> str:
    return service_text(
        "Project4 Queued Control Poller",
        config,
        "network-online.target project4-robot-control.service",
        f"/usr/bin/python3 {config.root}/project4-control/iot_control_poller.py "
        f"--config {config.root}/project4-iot/iot_client.conf",
        f"{config.root}/project4-control",
    )


def camera_service(config: DeployConfig) -> str:
    return service_text(
        "Project4 Camera MJPEG Server",
        config,
        "network-online.target",
        f"/usr/bin/python3 {config.root}/project4-camera/camera_mjpeg_server.py "
        "--host 0.0.0.0 --port 8080 --device /dev/video0 --width 640 --height 480 --fps 15 "
        f"--upload-config {config.root}/project4-iot/iot_client.conf --upload-interval 5",
        f"{config.root}/project4-camera",
        supplementary_groups="video",
    )


def service_text(
    description: str,
    config: DeployConfig,
    after: str,
    command: str,
    workdir: str,
    *,
    supplementary_groups: str = "",
) -> str:
    groups = [f"SupplementaryGroups={supplementary_groups}"] if supplementary_groups else []
    lines = [
        "[Unit]",
        f"Description={description}",
        f"After={after}",
        f"Wants={after}",
        "",
        "[Service]",
        "Type=simple",
        f"User={config.user}",
        "Environment=ROS_MASTER_URI=http://127.0.0.1:11311",
        *groups,
        f"WorkingDirectory={workdir}",
        f"ExecStart=/bin/bash -lc '{command}'",
        "Restart=always",
        "RestartSec=5",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]
    return "\n".join(lines)


def install_services(client: paramiko.SSHClient, config: DeployConfig) -> None:
    for name in service_files(config):
        run(client, config, f"mv /tmp/{name} /etc/systemd/system/{name}", sudo=True)
    run(client, config, "systemctl daemon-reload", sudo=True)
    for name in service_files(config):
        run(client, config, f"systemctl enable {name}", sudo=True)
        run(client, config, f"systemctl restart {name}", sudo=True)
    run(client, config, "systemctl is-active project4-ros-base.service project4-iot.service project4-robot-control.service project4-control-poller.service project4-camera.service")


def main() -> int:
    config = parse_args()
    client = connect(config)
    try:
        upload_files(client, config)
        install_services(client, config)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
