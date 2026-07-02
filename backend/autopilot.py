from __future__ import annotations

import copy
import math
import time
from datetime import datetime
from threading import RLock
from typing import Any, Callable


AUTOPILOT_MODES = {"manual", "auto_ready", "auto_running", "paused", "fault", "estop"}
CONTROL_PRIORITY = ("estop", "manual_override", "safety_supervisor", "autopilot", "remote_control")
STOP_REASONS = {"front_blocked", "both_front_blocked", "lidar_timeout", "control_timeout", "estop"}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def _round_or_none(value: Any, digits: int = 3) -> float | None:
    parsed = _finite_float(value)
    return round(parsed, digits) if parsed is not None else None


class AutopilotRuntime:
    """Small in-process autopilot state machine shared by API routes."""

    def __init__(self, lidar_timeout_seconds: float = 10.0, control_timeout_seconds: float = 10.0) -> None:
        self.lidar_timeout_seconds = float(lidar_timeout_seconds)
        self.control_timeout_seconds = float(control_timeout_seconds)
        self._lock = RLock()
        self._events: list[dict[str, Any]] = []
        self._next_event_id = 1
        self._event_recorder: Callable[[dict[str, Any]], int | None] | None = None
        self._event_loader: Callable[[int, int | None], list[dict[str, Any]]] | None = None
        self._active_faults: set[str] = set()
        self._state = self._initial_state()

    def configure_persistence(
        self,
        recorder: Callable[[dict[str, Any]], int | None] | None = None,
        loader: Callable[[int, int | None], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._event_recorder = recorder
        self._event_loader = loader

    def reset(self) -> None:
        with self._lock:
            self._events = []
            self._next_event_id = 1
            self._active_faults = set()
            self._state = self._initial_state()

    def _initial_state(self) -> dict[str, Any]:
        now = _now_iso()
        return {
            "mode": "manual",
            "requestedAuto": False,
            "safe": True,
            "reason": "manual_control",
            "linearX": 0.0,
            "angularZ": 0.0,
            "manualOverride": False,
            "estop": False,
            "robotId": None,
            "deviceId": None,
            "updatedAt": now,
            "lastControlAt": None,
            "_lastControlMonotonic": None,
            "lidar": {
                "online": False,
                "ageSeconds": None,
                "frontMin": None,
                "leftFrontMin": None,
                "rightFrontMin": None,
                "obstacleStatus": "unknown",
                "updatedAt": None,
                "_lastSeenMonotonic": None,
            },
        }

    def is_estopped(self) -> bool:
        with self._lock:
            return bool(self._state.get("estop")) or self._state.get("mode") == "estop"

    def status(self, *, include_events: bool = True, event_limit: int = 20) -> dict[str, Any]:
        with self._lock:
            self._apply_timeouts_locked()
            snapshot = self._snapshot_locked()
        if include_events:
            snapshot["events"] = self.events(event_limit, robot_id=snapshot.get("robotId"))
        return snapshot

    def events(self, limit: int = 20, robot_id: int | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 20), 100))
        if self._event_loader:
            try:
                loaded = self._event_loader(limit, robot_id)
                if loaded:
                    return loaded
            except Exception:
                pass
        with self._lock:
            items = [event for event in self._events if robot_id is None or event.get("robotId") in {None, robot_id}]
            return copy.deepcopy(items[:limit])

    def start(self, robot_id: Any = None) -> dict[str, Any]:
        with self._lock:
            if self._state.get("estop"):
                raise ValueError("estop_active")
            self._state["robotId"] = self._parse_optional_id(robot_id, self._state.get("robotId"))
            self._state["requestedAuto"] = True
            self._state["manualOverride"] = False
            lidar_ok = self._lidar_ready_locked()
            self._state["mode"] = "auto_running" if lidar_ok else "auto_ready"
            self._state["reason"] = "front_clear" if lidar_ok else self._unsafe_reason_locked("lidar_timeout")
            self._state["safe"] = lidar_ok
            self._state["updatedAt"] = _now_iso()
            self._record_event_locked("info", "autopilot_started", "自动驾驶启动", {"mode": self._state["mode"]})
            return self._snapshot_locked()

    def pause(self, reason: str = "user_paused", robot_id: Any = None) -> dict[str, Any]:
        with self._lock:
            if not self._state.get("estop"):
                self._state["mode"] = "paused"
            self._state["robotId"] = self._parse_optional_id(robot_id, self._state.get("robotId"))
            self._state["requestedAuto"] = True
            self._state["reason"] = reason
            self._state["linearX"] = 0.0
            self._state["angularZ"] = 0.0
            self._state["updatedAt"] = _now_iso()
            self._record_event_locked("info", "autopilot_paused", "自动驾驶暂停", {"reason": reason})
            return self._snapshot_locked()

    def resume(self, robot_id: Any = None) -> dict[str, Any]:
        with self._lock:
            if self._state.get("estop"):
                raise ValueError("estop_active")
            self._state["robotId"] = self._parse_optional_id(robot_id, self._state.get("robotId"))
            self._state["requestedAuto"] = True
            self._state["manualOverride"] = False
            lidar_ok = self._lidar_ready_locked()
            self._state["mode"] = "auto_running" if lidar_ok else "auto_ready"
            self._state["safe"] = lidar_ok
            self._state["reason"] = "front_clear" if lidar_ok else self._unsafe_reason_locked("lidar_timeout")
            self._state["updatedAt"] = _now_iso()
            self._record_event_locked("info", "autopilot_resumed", "自动驾驶继续", {"mode": self._state["mode"]})
            return self._snapshot_locked()

    def stop(self, reason: str = "stopped_by_user", robot_id: Any = None) -> dict[str, Any]:
        with self._lock:
            if not self._state.get("estop"):
                self._state["mode"] = "manual"
            self._state["robotId"] = self._parse_optional_id(robot_id, self._state.get("robotId"))
            self._state["requestedAuto"] = False
            self._state["manualOverride"] = False
            self._state["reason"] = reason
            self._state["safe"] = not self._state.get("estop")
            self._state["linearX"] = 0.0
            self._state["angularZ"] = 0.0
            self._state["updatedAt"] = _now_iso()
            self._record_event_locked("info", "autopilot_stopped", "自动驾驶停止", {"reason": reason})
            return self._snapshot_locked()

    def estop(self, robot_id: Any = None) -> dict[str, Any]:
        with self._lock:
            self._state["robotId"] = self._parse_optional_id(robot_id, self._state.get("robotId"))
            self._state["mode"] = "estop"
            self._state["requestedAuto"] = False
            self._state["estop"] = True
            self._state["manualOverride"] = False
            self._state["safe"] = False
            self._state["reason"] = "user_estop"
            self._state["linearX"] = 0.0
            self._state["angularZ"] = 0.0
            self._state["updatedAt"] = _now_iso()
            self._record_event_locked("critical", "estop_triggered", "急停触发", {"reason": "user_estop"})
            return self._snapshot_locked()

    def clear_estop(self, robot_id: Any = None) -> dict[str, Any]:
        with self._lock:
            self._state["robotId"] = self._parse_optional_id(robot_id, self._state.get("robotId"))
            self._state["estop"] = False
            self._state["mode"] = "manual"
            self._state["requestedAuto"] = False
            self._state["manualOverride"] = False
            self._state["safe"] = True
            self._state["reason"] = "estop_cleared"
            self._state["linearX"] = 0.0
            self._state["angularZ"] = 0.0
            self._state["updatedAt"] = _now_iso()
            self._active_faults.discard("estop")
            self._record_event_locked("info", "estop_cleared", "急停解除", {"manualReset": True})
            return self._snapshot_locked()

    def note_manual_override(self, robot_id: Any = None, source: str = "remote_control") -> dict[str, Any]:
        with self._lock:
            self._state["robotId"] = self._parse_optional_id(robot_id, self._state.get("robotId"))
            changed = self._state.get("mode") in {"auto_ready", "auto_running"}
            if changed:
                self._state["mode"] = "paused"
                self._state["requestedAuto"] = True
                self._state["reason"] = "manual_override"
                self._state["linearX"] = 0.0
                self._state["angularZ"] = 0.0
            self._state["manualOverride"] = True
            self._state["updatedAt"] = _now_iso()
            if changed:
                self._record_event_locked("warning", "manual_override", "人工接管，自动驾驶暂停", {"source": source})
            return self._snapshot_locked()

    def update_report(self, payload: dict[str, Any], *, device_id: Any = None, robot_id: Any = None) -> dict[str, Any]:
        with self._lock:
            self._state["deviceId"] = self._parse_optional_id(device_id, self._state.get("deviceId"))
            self._state["robotId"] = self._parse_optional_id(payload.get("robotId", robot_id), self._state.get("robotId"))

            if payload.get("estop") is True:
                self._state["estop"] = True
                self._state["mode"] = "estop"
                self._state["safe"] = False
                self._state["reason"] = "estop"

            lidar_payload = payload.get("lidar") if isinstance(payload.get("lidar"), dict) else {}
            if lidar_payload:
                self._update_lidar_locked(lidar_payload)

            linear = _round_or_none(payload.get("linearX", payload.get("linear_x")))
            angular = _round_or_none(payload.get("angularZ", payload.get("angular_z")))
            if linear is not None:
                self._state["linearX"] = linear
            if angular is not None:
                self._state["angularZ"] = angular
            if linear is not None or angular is not None:
                self._state["lastControlAt"] = _now_iso()
                self._state["_lastControlMonotonic"] = time.monotonic()

            reported_mode = str(payload.get("mode") or "").strip()
            if reported_mode in AUTOPILOT_MODES and not self._state.get("estop"):
                self._state["mode"] = reported_mode
                self._state["requestedAuto"] = reported_mode in {"auto_ready", "auto_running", "paused", "fault"}

            if "manualOverride" in payload:
                self._state["manualOverride"] = bool(payload.get("manualOverride"))

            reason = str(payload.get("reason") or "").strip()
            if reason:
                self._state["reason"] = reason
            if "safe" in payload:
                self._state["safe"] = bool(payload.get("safe"))

            self._state["updatedAt"] = _now_iso()
            self._derive_auto_mode_locked()
            self._apply_timeouts_locked()
            return self._snapshot_locked()

    def _update_lidar_locked(self, payload: dict[str, Any]) -> None:
        lidar = self._state["lidar"]
        online = bool(payload.get("online", True))
        lidar["online"] = online
        for source, target in (
            ("frontMin", "frontMin"),
            ("front_min", "frontMin"),
            ("leftFrontMin", "leftFrontMin"),
            ("left_front_min", "leftFrontMin"),
            ("rightFrontMin", "rightFrontMin"),
            ("right_front_min", "rightFrontMin"),
        ):
            if source in payload:
                lidar[target] = _round_or_none(payload.get(source))
        status = str(payload.get("obstacleStatus") or payload.get("obstacle_status") or "").strip()
        if status:
            lidar["obstacleStatus"] = status
        age = _finite_float(payload.get("ageSeconds", payload.get("age_seconds")))
        if online:
            now_mono = time.monotonic()
            lidar["_lastSeenMonotonic"] = now_mono - max(0.0, age or 0.0)
            lidar["updatedAt"] = _now_iso()
        elif payload.get("updatedAt") is None:
            lidar["online"] = False

    def _derive_auto_mode_locked(self) -> None:
        if self._state.get("estop"):
            self._state["mode"] = "estop"
            self._state["safe"] = False
            self._state["reason"] = "user_estop"
            return
        if not self._state.get("requestedAuto"):
            return
        if self._state.get("manualOverride"):
            self._state["mode"] = "paused"
            self._state["reason"] = "manual_override"
            self._state["linearX"] = 0.0
            self._state["angularZ"] = 0.0
            return
        lidar_ok = self._lidar_ready_locked()
        if lidar_ok:
            if self._state.get("mode") in {"auto_ready", "fault"}:
                self._state["mode"] = "auto_running"
            self._state["safe"] = True
            self._state["reason"] = "front_clear"
            self._active_faults.discard("lidar_timeout")
            self._active_faults.discard("front_blocked")
        elif not lidar_ok and self._state.get("mode") == "auto_running":
            self._state["safe"] = False
            reason = self._unsafe_reason_locked("front_blocked")
            self._state["reason"] = reason
            if reason in {"front_blocked", "both_front_blocked"}:
                self._record_fault_once_locked("front_blocked", "warning", "front_obstacle_too_close", "前方障碍物过近")

    def _apply_timeouts_locked(self) -> None:
        now = time.monotonic()
        lidar = self._state["lidar"]
        last_lidar = lidar.get("_lastSeenMonotonic")
        if last_lidar is None:
            lidar["ageSeconds"] = None
            lidar["online"] = False
        else:
            lidar_age = max(0.0, now - float(last_lidar))
            lidar["ageSeconds"] = round(lidar_age, 3)
            lidar["online"] = lidar_age <= self.lidar_timeout_seconds

        if self._state.get("estop"):
            self._state["mode"] = "estop"
            self._state["safe"] = False
            self._state["reason"] = "user_estop"
            return

        auto_active = self._state.get("mode") in {"auto_ready", "auto_running", "fault"} or self._state.get("requestedAuto")
        if auto_active and not lidar["online"]:
            self._state["safe"] = False
            self._state["linearX"] = 0.0
            self._state["angularZ"] = 0.0
            if self._state.get("mode") == "auto_running":
                self._state["mode"] = "fault"
            self._state["reason"] = "lidar_timeout"
            self._record_fault_once_locked("lidar_timeout", "warning", "lidar_timeout", "LiDAR 超过 2 秒未更新")

        last_control = self._state.get("_lastControlMonotonic")
        if self._state.get("mode") == "auto_running" and last_control is not None:
            control_age = now - float(last_control)
            if control_age > self.control_timeout_seconds:
                self._state["mode"] = "fault"
                self._state["safe"] = False
                self._state["reason"] = "control_timeout"
                self._state["linearX"] = 0.0
                self._state["angularZ"] = 0.0
                self._record_fault_once_locked("control_timeout", "warning", "control_timeout", "控制指令超时")

    def _lidar_ready_locked(self) -> bool:
        lidar = self._state["lidar"]
        last_lidar = lidar.get("_lastSeenMonotonic")
        if last_lidar is None or time.monotonic() - float(last_lidar) > self.lidar_timeout_seconds:
            return False
        front = _finite_float(lidar.get("frontMin"))
        if front is None or front < 0.5:
            return False
        status = str(lidar.get("obstacleStatus") or "").strip()
        return status not in STOP_REASONS

    def _unsafe_reason_locked(self, fallback: str) -> str:
        lidar = self._state["lidar"]
        status = str(lidar.get("obstacleStatus") or "").strip()
        if status and status != "unknown":
            return status
        front = _finite_float(lidar.get("frontMin"))
        if front is not None and front < 0.5:
            return "front_blocked"
        return fallback

    def _snapshot_locked(self) -> dict[str, Any]:
        state = copy.deepcopy(self._state)
        state.pop("requestedAuto", None)
        state.pop("_lastControlMonotonic", None)
        if isinstance(state.get("lidar"), dict):
            state["lidar"].pop("_lastSeenMonotonic", None)
        return state

    def _record_fault_once_locked(self, key: str, level: str, event_type: str, message: str) -> None:
        if key in self._active_faults:
            return
        self._active_faults.add(key)
        self._record_event_locked(level, event_type, message, {"reason": key})

    def _record_event_locked(self, level: str, event_type: str, message: str, data: dict[str, Any] | None = None) -> None:
        event = {
            "id": self._next_event_id,
            "robotId": self._state.get("robotId"),
            "level": level,
            "eventType": event_type,
            "message": message,
            "data": data or {},
            "createdAt": _now_iso(),
        }
        self._next_event_id += 1
        if self._event_recorder:
            try:
                inserted = self._event_recorder(copy.deepcopy(event))
                if inserted:
                    event["id"] = int(inserted)
            except Exception:
                pass
        self._events.insert(0, event)
        del self._events[100:]

    @staticmethod
    def _parse_optional_id(value: Any, fallback: Any = None) -> int | None:
        if value is None or value == "":
            return fallback if isinstance(fallback, int) else None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback if isinstance(fallback, int) else None
        return parsed if parsed > 0 else None
