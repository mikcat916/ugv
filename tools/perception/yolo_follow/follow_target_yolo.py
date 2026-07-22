#!/usr/bin/env python3
import argparse
import json
import socket
import sys
import time
from typing import Optional, Tuple

import cv2
from ultralytics import YOLO


DEFAULT_STREAM_URL = "http://192.168.31.198:8080/?action=stream"
DEFAULT_ROBOT_HOST = "192.168.31.198"
DEFAULT_ROBOT_PORT = 9000


class RobotClient:
    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.recv_buf = b""

    def connect(self) -> None:
        if self.sock:
            return
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None
                self.recv_buf = b""

    def send(self, payload: dict) -> Optional[dict]:
        self.connect()
        assert self.sock is not None
        message = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        self.sock.sendall(message)
        return self._read_line()

    def _read_line(self) -> Optional[dict]:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if b"\n" in self.recv_buf:
                line, self.recv_buf = self.recv_buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    return json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    return None
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.recv_buf += chunk
        return None

    def stop(self) -> None:
        try:
            self.send({"type": "stop"})
        except Exception:
            self.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YOLO on a PC and send cmd_vel to the Raspberry Pi.")
    parser.add_argument("--stream-url", default=DEFAULT_STREAM_URL, help="MJPEG stream URL from the Raspberry Pi camera")
    parser.add_argument("--robot-host", default=DEFAULT_ROBOT_HOST, help="Raspberry Pi control server host")
    parser.add_argument("--robot-port", type=int, default=DEFAULT_ROBOT_PORT, help="Raspberry Pi control server port")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics model name or local path")
    parser.add_argument("--device", default="auto", help="Inference device: auto, cpu, cuda, cuda:0")
    parser.add_argument("--target-class", default="person", help="Class name to follow, for example person")
    parser.add_argument("--frame-skip", type=int, default=2, help="Run YOLO every N frames to reduce CPU load")
    parser.add_argument("--conf", type=float, default=0.45, help="Detection confidence threshold")
    parser.add_argument("--image-size", type=int, default=320, help="Inference image size")
    parser.add_argument("--linear-speed", type=float, default=0.18, help="Forward speed when target is far enough")
    parser.add_argument("--max-angular-speed", type=float, default=0.8, help="Max turn speed sent to robot_server")
    parser.add_argument("--deadband", type=float, default=0.08, help="Horizontal error deadband, 0.08 means 8 percent")
    parser.add_argument("--target-width-ratio", type=float, default=0.22, help="Desired target width ratio in the frame")
    parser.add_argument("--max-width-ratio", type=float, default=0.38, help="Stop moving forward when target appears larger than this ratio")
    parser.add_argument("--show-window", action="store_true", help="Show a local preview window. Keep this off on headless servers.")
    parser.add_argument("--log-interval", type=float, default=1.0, help="Status log interval in seconds")
    return parser.parse_args()


def select_target(result, target_class: str) -> Optional[Tuple[Tuple[int, int, int, int], float]]:
    names = result.names
    best = None
    best_conf = -1.0
    boxes = result.boxes
    if boxes is None:
        return None
    for box in boxes:
        cls_idx = int(box.cls.item())
        cls_name = names.get(cls_idx, str(cls_idx))
        if cls_name != target_class:
            continue
        conf = float(box.conf.item())
        if conf > best_conf:
            xyxy = box.xyxy[0].tolist()
            best = (tuple(int(v) for v in xyxy), conf)
            best_conf = conf
    return best


def compute_cmd(
    frame_width: int,
    box: Tuple[int, int, int, int],
    linear_speed: float,
    max_angular_speed: float,
    deadband: float,
    target_width_ratio: float,
    max_width_ratio: float,
) -> Tuple[float, float]:
    x1, y1, x2, y2 = box
    center_x = (x1 + x2) / 2.0
    width_ratio = max(0.0, min(1.0, (x2 - x1) / float(frame_width)))
    error_x = (center_x / frame_width) - 0.5

    if abs(error_x) < deadband:
        angular = 0.0
    else:
        angular = max(-1.0, min(1.0, error_x / 0.5)) * max_angular_speed

    if width_ratio >= max_width_ratio:
        linear = 0.0
    elif abs(error_x) > 0.35:
        linear = 0.0
    elif width_ratio < target_width_ratio:
        linear = linear_speed
    else:
        linear = linear_speed * max(0.0, (max_width_ratio - width_ratio) / max(0.001, max_width_ratio - target_width_ratio))

    return linear, angular


def main() -> int:
    args = parse_args()

    model = YOLO(args.model)
    predict_device = None if args.device == "auto" else args.device
    cap = cv2.VideoCapture(args.stream_url)
    if not cap.isOpened():
        print(f"Cannot open stream: {args.stream_url}", file=sys.stderr)
        return 1

    robot = RobotClient(args.robot_host, args.robot_port)
    frame_index = 0
    last_detection = None
    last_sent = 0.0
    last_seen = 0.0
    last_log = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read frame from MJPEG stream", file=sys.stderr)
                time.sleep(0.2)
                continue

            frame_index += 1
            frame_h, frame_w = frame.shape[:2]

            if frame_index % max(1, args.frame_skip) == 0:
                results = model.predict(frame, imgsz=args.image_size, conf=args.conf, verbose=False, device=predict_device)
                result = results[0]
                last_detection = select_target(result, args.target_class)
                if last_detection:
                    last_seen = time.time()

            linear = 0.0
            angular = 0.0
            overlay = "target: none"

            if last_detection and (time.time() - last_seen) < 1.0:
                box, conf = last_detection
                linear, angular = compute_cmd(
                    frame_w,
                    box,
                    args.linear_speed,
                    args.max_angular_speed,
                    args.deadband,
                    args.target_width_ratio,
                    args.max_width_ratio,
                )
                x1, y1, x2, y2 = box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (50, 220, 50), 2)
                overlay = f"{args.target_class} conf={conf:.2f} v={linear:.2f} w={angular:.2f}"
            else:
                overlay = "target lost -> stop"

            now = time.time()
            if now - last_sent >= 0.15:
                try:
                    if linear == 0.0 and angular == 0.0:
                        robot.send({"type": "stop"})
                    else:
                        robot.send({"type": "cmd_vel", "v": linear, "w": angular})
                except Exception as exc:
                    robot.close()
                    overlay = f"robot link error: {exc}"
                last_sent = now

            if now - last_log >= args.log_interval:
                print(overlay, flush=True)
                last_log = now

            if args.show_window:
                cv2.putText(frame, overlay, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("YOLO Follow", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
    finally:
        robot.stop()
        robot.close()
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
