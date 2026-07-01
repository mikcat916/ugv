#!/usr/bin/env python3
"""Relay a real MJPEG snapshot endpoint into Project4 camera upload API."""

from __future__ import annotations

import argparse
import configparser
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


HTTP_TIMEOUT_SEC = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relay camera snapshots to Project4")
    parser.add_argument("--camera-url", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--token", default="")
    parser.add_argument("--config", default="")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def load_token(args: argparse.Namespace) -> str:
    if args.token:
        return args.token.strip()
    if not args.config:
        raise RuntimeError("missing --token or --config")
    cfg = configparser.ConfigParser()
    cfg.read(args.config, encoding="utf-8")
    token = cfg.get("client", "token", fallback="").strip()
    if not token:
        raise RuntimeError("missing token in config")
    return token


def fetch_snapshot(camera_url: str) -> bytes:
    with urlopen(camera_url, timeout=HTTP_TIMEOUT_SEC) as response:
        content = response.read()
    if not content.startswith(b"\xff\xd8"):
        raise RuntimeError("camera endpoint did not return JPEG")
    return content


def upload_snapshot(server: str, token: str, frame: bytes) -> dict:
    boundary = f"project4-relay-{int(time.time() * 1000)}"
    body = build_multipart(boundary, frame)
    request = Request(
        server.rstrip("/") + "/api/iot/camera/snapshot",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "X-Device-Token": token,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"upload failed HTTP {exc.code}: {body_text}") from exc


def build_multipart(boundary: str, frame: bytes) -> bytes:
    head = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="snapshot.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + frame + tail


def relay_once(args: argparse.Namespace, token: str) -> None:
    frame = fetch_snapshot(args.camera_url)
    result = upload_snapshot(args.server, token, frame)
    print(f"uploaded size={len(frame)} result={result}", flush=True)


def main() -> None:
    args = parse_args()
    token = load_token(args)
    while True:
        try:
            relay_once(args, token)
        except Exception as exc:
            print(f"relay failed: {exc}", flush=True)
        if args.once:
            return
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
