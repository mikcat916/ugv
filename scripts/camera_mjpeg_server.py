#!/usr/bin/env python3
"""MJPEG camera server compatible with mjpg_streamer action URLs."""

from __future__ import annotations

import argparse
import configparser
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import cv2


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
DEFAULT_DEVICE = "/dev/video0"
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 15
JPEG_QUALITY = 80
BOUNDARY = "project4frame"
HTTP_TIMEOUT_SEC = 10


class Camera:
    def __init__(self, device: str, width: int, height: int, fps: int) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.lock = Lock()
        self.latest_frame: bytes | None = None
        self.latest_error = ""
        self.capture = self._open_capture()
        Thread(target=self._capture_loop, daemon=True).start()

    def _open_capture(self) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(self.device)
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_FPS, self.fps)
        if not capture.isOpened():
            raise RuntimeError(f"camera device unavailable: {self.device}")
        return capture

    def _capture_loop(self) -> None:
        delay = 1.0 / max(1, self.fps)
        while True:
            try:
                self._capture_once()
            except RuntimeError as exc:
                with self.lock:
                    self.latest_error = str(exc)
            time.sleep(delay)

    def _capture_once(self) -> None:
        ok, frame = self.capture.read()
        if not ok:
            raise RuntimeError("failed to read camera frame")
        params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        encoded_ok, encoded = cv2.imencode(".jpg", frame, params)
        if not encoded_ok:
            raise RuntimeError("failed to encode camera frame")
        with self.lock:
            self.latest_frame = encoded.tobytes()
            self.latest_error = ""

    def jpeg_frame(self) -> bytes:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            with self.lock:
                if self.latest_frame is not None:
                    return self.latest_frame
                latest_error = self.latest_error
            if latest_error:
                raise RuntimeError(latest_error)
            time.sleep(0.05)
        raise RuntimeError("camera frame unavailable")


def upload_loop(camera: Camera, config_path: str, interval: int) -> None:
    server, token = load_upload_config(config_path)
    while True:
        try:
            upload_snapshot(server, token, camera.jpeg_frame())
        except Exception as exc:
            print(f"camera upload failed: {exc}", flush=True)
        time.sleep(max(5, interval))


def load_upload_config(config_path: str) -> tuple[str, str]:
    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding="utf-8")
    server = cfg.get("client", "server", fallback="").strip().rstrip("/")
    token = cfg.get("client", "token", fallback="").strip()
    if not server:
        raise RuntimeError("missing server in camera upload config")
    if not token:
        raise RuntimeError("missing token in camera upload config")
    return server, token


def upload_snapshot(server: str, token: str, frame: bytes) -> None:
    boundary = f"project4-{int(time.time() * 1000)}"
    body = multipart_body(boundary, "file", "snapshot.jpg", "image/jpeg", frame)
    request = Request(
        f"{server}/api/iot/camera/snapshot",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "X-Device-Token": token,
        },
        method="POST",
    )
    with urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
        response.read()


def multipart_body(boundary: str, field: str, filename: str, content_type: str, content: bytes) -> bytes:
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + content + tail


class CameraHTTPServer(ThreadingHTTPServer):
    request_queue_size = 64
    daemon_threads = True


class CameraHandler(BaseHTTPRequestHandler):
    camera: Camera

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.client_address[0]} - {format % args}", flush=True)

    def do_GET(self) -> None:
        action = parse_qs(urlparse(self.path).query).get("action", ["snapshot"])[0]
        if action == "snapshot":
            self.handle_snapshot()
            return
        if action == "stream":
            self.handle_stream()
            return
        self.send_error(HTTPStatus.BAD_REQUEST, "unsupported action")

    def handle_snapshot(self) -> None:
        try:
            frame = self.camera.jpeg_frame()
        except RuntimeError as exc:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, str(exc))
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(frame)

    def handle_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        delay = 1.0 / max(1, self.camera.fps)
        try:
            while True:
                frame = self.camera.jpeg_frame()
                self.write_stream_part(frame)
                time.sleep(delay)
        except OSError:
            return

    def write_stream_part(self, frame: bytes) -> None:
        self.wfile.write(f"--{BOUNDARY}\r\n".encode("ascii"))
        self.wfile.write(b"Content-Type: image/jpeg\r\n")
        self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
        self.wfile.write(frame)
        self.wfile.write(b"\r\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project4 MJPEG camera server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--upload-config", default="")
    parser.add_argument("--upload-interval", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    CameraHandler.camera = Camera(args.device, args.width, args.height, args.fps)
    if args.upload_config:
        Thread(
            target=upload_loop,
            args=(CameraHandler.camera, args.upload_config, args.upload_interval),
            daemon=True,
        ).start()
    server = CameraHTTPServer((args.host, args.port), CameraHandler)
    print(f"Project4 camera server listening on {args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
