#!/usr/bin/env python3
"""Project4 Orin perception status and upload service.

This service never fabricates detections. If TensorRT, ROS topics, models, or
calibration data are missing, it reports explicit status metadata to Project4.
"""

from __future__ import annotations

import argparse
import configparser
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


HTTP_TIMEOUT_SEC = 10
MIN_INT8_CALIBRATION_IMAGES = 20
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project4 Orin perception service")
    parser.add_argument("--config", default=str(Path(__file__).with_name("perception.conf")))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--probe-only", action="store_true")
    return parser.parse_args()


def load_config(path: str) -> dict[str, str]:
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    section = "perception"
    required = ("server", "token")
    missing = [key for key in required if not cfg.get(section, key, fallback="").strip()]
    if missing:
        raise RuntimeError(f"missing config keys: {', '.join(missing)}")
    return {key: value.strip() for key, value in cfg.items(section)}


def run_command(command: list[str], timeout: int = 3) -> dict[str, str]:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"status": "missing", "output": ""}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "output": ""}
    output = (result.stdout + result.stderr).strip()
    return {"status": "ok" if result.returncode == 0 else "error", "output": output}


def import_status(module_name: str) -> str:
    try:
        __import__(module_name)
        return "available"
    except Exception as exc:
        return f"missing:{type(exc).__name__}"


def list_ros_topics() -> list[str]:
    result = run_command(["rostopic", "list"], timeout=5)
    if result["status"] != "ok":
        return []
    return [line.strip() for line in result["output"].splitlines() if line.strip()]


def topic_status(topics: list[str], topic_name: str) -> str:
    return "online" if topic_name and topic_name in topics else "missing"


def count_calibration_images(path_text: str) -> int:
    path = Path(path_text)
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.iterdir() if item.suffix.lower() in IMAGE_EXTENSIONS)


def validate_precision(config: dict[str, str]) -> None:
    precision = config.get("precision", "fp16").lower()
    if precision != "int8":
        return
    count = count_calibration_images(config.get("calibration_dir", ""))
    if count < MIN_INT8_CALIBRATION_IMAGES:
        raise RuntimeError(f"INT8 calibration requires at least {MIN_INT8_CALIBRATION_IMAGES} images, found {count}")


def model_status(config: dict[str, str]) -> dict[str, str]:
    model_path_text = config.get("model_path", "").strip()
    engine_path_text = config.get("engine_path", "").strip()
    return {
        "model": "available" if model_path_text and Path(model_path_text).exists() else "missing",
        "engine": "available" if engine_path_text and Path(engine_path_text).exists() else "missing",
        "precision": config.get("precision", "fp16").lower(),
    }


def build_metadata(config: dict[str, str]) -> dict:
    topics = list_ros_topics()
    camera_topic = config.get("camera_topic", "/camera/image_raw")
    lidar_topic = config.get("lidar_topic", "/points_raw")
    imu_topic = config.get("imu_topic", "/imu/data")
    return {
        "frameId": f"orin-status-{int(time.time() * 1000)}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": config.get("model_name", "orin-perception"),
        "precision": config.get("precision", "fp16").lower(),
        "fps": 0,
        "latencyMs": 0,
        "sensorStatus": {
            "camera": topic_status(topics, camera_topic),
            "lidar": topic_status(topics, lidar_topic),
            "imu": topic_status(topics, imu_topic),
            "ros": "online" if topics else "missing",
            "tensorrt": import_status("tensorrt"),
            "cuda": run_command(["nvcc", "--version"])["status"],
            **model_status(config),
        },
        "fusionStatus": "ready" if config.get("extrinsics_path", "").strip() and Path(config["extrinsics_path"]).exists() else "uncalibrated",
        "detections": [],
        "tracks": [],
    }


def multipart_body(boundary: str, metadata: dict) -> bytes:
    payload = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    head = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="metadata"\r\n'
        "Content-Type: application/json\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + payload + tail


def upload_metadata(config: dict[str, str], metadata: dict) -> dict:
    boundary = f"project4-perception-{int(time.time() * 1000)}"
    body = multipart_body(boundary, metadata)
    request = Request(
        config["server"].rstrip("/") + "/api/iot/perception",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "X-Device-Token": config["token"]},
        method="POST",
    )
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"upload failed HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    validate_precision(config)
    while True:
        metadata = build_metadata(config)
        if args.probe_only:
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(upload_metadata(config, metadata), ensure_ascii=False), flush=True)
        if args.once:
            return 0
        time.sleep(max(1.0, float(config.get("upload_interval", "1"))))


if __name__ == "__main__":
    raise SystemExit(main())
