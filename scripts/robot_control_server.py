#!/usr/bin/env python3
"""TCP cmd_vel bridge for the Raspberry Pi motor controller."""

from __future__ import annotations

import json
import os
import socket
import time
from threading import Lock, Thread

import serial

HOST = "0.0.0.0"
PORT = 9000
CMD_TIMEOUT_SEC = 0.5
STATUS_PERIOD_SEC = 1.0
SERIAL_PORT = os.getenv("ROBOT_SERIAL_PORT", "/dev/ttyACM0")
BAUDRATE = int(os.getenv("ROBOT_SERIAL_BAUDRATE", "115200"))
MAX_LINEAR = float(os.getenv("ROBOT_MAX_LINEAR", "0.6"))
MAX_ANGULAR = float(os.getenv("ROBOT_MAX_ANGULAR", "2.0"))

lock = Lock()
last_cmd_time = 0.0
current_v = 0.0
current_w = 0.0
ser: serial.Serial | None = None


def split_i16(value: int) -> tuple[int, int]:
    normalized = value & 0xFFFF
    return (normalized >> 8) & 0xFF, normalized & 0xFF


def clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def motor_packet(v: float, w: float) -> bytes:
    tx = [0x7B, 0x00, 0x00, 0, 0, 0, 0, 0, 0]
    v_i16 = int(clamp(v, MAX_LINEAR) * 1000)
    w_i16 = int(clamp(w, MAX_ANGULAR) * 1000)
    tx[3], tx[4] = split_i16(v_i16)
    tx[7], tx[8] = split_i16(w_i16)
    checksum = 0
    for byte in tx:
        checksum ^= byte
    return bytes(tx + [checksum, 0x7D])


def motor_serial() -> serial.Serial:
    global ser
    if ser is None or not ser.is_open:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    return ser


def send_cmd_to_motor(v: float, w: float) -> None:
    packet = motor_packet(v, w)
    written = motor_serial().write(packet)
    packet_hex = " ".join(f"{byte:02x}" for byte in packet)
    print(
        f"[SERIAL] v={v:.3f} w={w:.3f} bytes={written} packet={packet_hex}",
        flush=True,
    )


def hard_stop() -> None:
    global current_v, current_w
    current_v = 0.0
    current_w = 0.0
    send_cmd_to_motor(0.0, 0.0)


def watchdog_loop() -> None:
    global last_cmd_time
    while True:
        time.sleep(0.05)
        with lock:
            expired = last_cmd_time > 0 and (time.time() - last_cmd_time) > CMD_TIMEOUT_SEC
            if expired:
                last_cmd_time = 0
                print("[SAFE] cmd timeout -> STOP", flush=True)
                hard_stop()


def send_json_line(conn: socket.socket, obj: dict) -> None:
    data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
    conn.sendall(data)


def status_loop(conn: socket.socket) -> None:
    while True:
        time.sleep(STATUS_PERIOD_SEC)
        try:
            send_json_line(conn, {"type": "status", "motor": "ok", "v": current_v, "w": current_w, "ts": int(time.time())})
        except OSError:
            return


def handle_command(conn: socket.socket, msg: dict) -> None:
    global current_v, current_w, last_cmd_time
    now = time.time()
    mtype = msg.get("type")
    if mtype == "ping":
        send_json_line(conn, {"type": "pong", "ts": int(now)})
        return
    if mtype == "stop":
        with lock:
            last_cmd_time = now
        hard_stop()
        send_json_line(conn, {"type": "ack", "ok": True, "ts": int(now)})
        return
    if mtype == "cmd_vel":
        v = clamp(float(msg.get("v", 0.0)), MAX_LINEAR)
        w = clamp(float(msg.get("w", 0.0)), MAX_ANGULAR)
        with lock:
            last_cmd_time = now
            current_v = v
            current_w = w
        send_cmd_to_motor(v, w)
        send_json_line(conn, {"type": "ack", "ok": True, "ts": int(now)})
        return
    send_json_line(conn, {"type": "ack", "ok": False, "err": "unknown_type", "ts": int(now)})


def handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
    print("connected:", addr, flush=True)
    conn.settimeout(2.0)
    Thread(target=status_loop, args=(conn,), daemon=True).start()
    buf = b""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line.strip():
                    handle_command(conn, json.loads(line.decode("utf-8")))
    except Exception as exc:
        print("client error:", exc, flush=True)
    finally:
        print("disconnected:", addr, flush=True)
        hard_stop()
        conn.close()


def main() -> None:
    Thread(target=watchdog_loop, daemon=True).start()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"[SERVER] listen on {HOST}:{PORT}", flush=True)
    while True:
        conn, addr = server.accept()
        Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
