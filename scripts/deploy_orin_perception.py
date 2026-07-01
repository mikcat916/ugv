#!/usr/bin/env python3
"""Deploy Project4 Orin perception service over SSH."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PYDEPS_DIR = ROOT_DIR / ".pydeps"
if PYDEPS_DIR.exists():
    sys.path.insert(0, str(PYDEPS_DIR))

import paramiko


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy Project4 perception service to Jetson Orin")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default="nvidia")
    parser.add_argument("--password", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--root", default="/home/nvidia/project4-perception")
    parser.add_argument("--precision", choices=("fp16", "int8"), default="fp16")
    parser.add_argument("--camera-topic", default="/camera/image_raw")
    parser.add_argument("--lidar-topic", default="/points_raw")
    parser.add_argument("--imu-topic", default="/imu/data")
    parser.add_argument("--model-path", default="")
    parser.add_argument("--engine-path", default="")
    parser.add_argument("--calibration-dir", default="")
    parser.add_argument("--extrinsics-path", default="")
    parser.add_argument("--upload-interval", type=float, default=1.0)
    return parser.parse_args()


def run(client: paramiko.SSHClient, command: str, sudo: bool = False, password: str = "") -> str:
    if sudo:
        command = "sudo -S -p '' " + command
    stdin, stdout, stderr = client.exec_command(command, get_pty=True)
    if sudo and password:
        stdin.write(password + "\n")
        stdin.flush()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if code != 0:
        raise RuntimeError(f"command failed rc={code}: {command}\nSTDOUT={out}\nSTDERR={err}")
    return out + err


def write_text(sftp: paramiko.SFTPClient, path: str, content: str) -> None:
    with sftp.file(path, "w") as handle:
        handle.write(content)


def config_text(args: argparse.Namespace) -> str:
    lines = [
        "[perception]",
        f"server = {args.server.rstrip('/')}",
        f"token = {args.token}",
        "model_name = orin-perception",
        f"precision = {args.precision}",
        f"camera_topic = {args.camera_topic}",
        f"lidar_topic = {args.lidar_topic}",
        f"imu_topic = {args.imu_topic}",
        f"model_path = {args.model_path}",
        f"engine_path = {args.engine_path}",
        f"calibration_dir = {args.calibration_dir}",
        f"extrinsics_path = {args.extrinsics_path}",
        f"upload_interval = {args.upload_interval}",
        "",
    ]
    return "\n".join(lines)


def service_text(args: argparse.Namespace) -> str:
    command = (
        "bash -lc 'source /opt/ros/noetic/setup.bash 2>/dev/null || true; "
        f"/usr/bin/python3 {args.root}/orin_perception_service.py --config {args.root}/perception.conf'"
    )
    return "\n".join([
        "[Unit]",
        "Description=Project4 Orin Perception Service",
        "After=network-online.target roscore.service",
        "Wants=network-online.target roscore.service",
        "",
        "[Service]",
        "Type=simple",
        f"WorkingDirectory={args.root}",
        "Environment=ROS_MASTER_URI=http://192.168.31.224:11311",
        "Environment=ROS_IP=192.168.31.224",
        "Environment=PATH=/usr/local/cuda/bin:/usr/local/cuda-11.4/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "Environment=LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda-11.4/lib64",
        "Environment=LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1",
        f"ExecStart={command}",
        "Restart=always",
        "RestartSec=5",
        f"User={args.user}",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ])


def roscore_text() -> str:
    return "\n".join([
        "[Unit]",
        "Description=ROS Core Master",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Service]",
        "Type=simple",
        "User=nimda",
        "Environment=ROS_MASTER_URI=http://192.168.31.224:11311",
        "Environment=ROS_IP=192.168.31.224",
        "ExecStart=/usr/bin/roscore",
        "Restart=always",
        "RestartSec=3",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ])


def remote_probe(client: paramiko.SSHClient) -> str:
    command = "uname -a; cat /etc/nv_tegra_release 2>/dev/null || true; command -v rostopic || true; command -v python3"
    return run(client, command)


def deploy(args: argparse.Namespace) -> None:
    script_path = ROOT_DIR / "scripts" / "orin_perception_service.py"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.host, username=args.user, password=args.password, timeout=10, banner_timeout=10, auth_timeout=10)
    try:
        print(remote_probe(client))
        run(client, f"mkdir -p {args.root}")
        sftp = client.open_sftp()
        try:
            sftp.put(str(script_path), f"{args.root}/orin_perception_service.py")
            write_text(sftp, f"{args.root}/perception.conf", config_text(args))
            write_text(sftp, "/tmp/roscore.service", roscore_text())
            write_text(sftp, "/tmp/project4-perception.service", service_text(args))
        finally:
            sftp.close()
        run(client, f"chmod +x {args.root}/orin_perception_service.py")
        run(client, "mv /tmp/roscore.service /etc/systemd/system/roscore.service", sudo=True, password=args.password)
        run(client, "mv /tmp/project4-perception.service /etc/systemd/system/project4-perception.service", sudo=True, password=args.password)
        run(client, "systemctl daemon-reload", sudo=True, password=args.password)
        run(client, "systemctl enable roscore.service", sudo=True, password=args.password)
        run(client, "systemctl enable project4-perception.service", sudo=True, password=args.password)
        run(client, "systemctl restart roscore.service", sudo=True, password=args.password)
        run(client, "systemctl restart project4-perception.service", sudo=True, password=args.password)
        print(run(client, "systemctl status project4-perception.service --no-pager"))
    finally:
        client.close()


def main() -> int:
    deploy(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
