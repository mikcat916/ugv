from datetime import datetime, timedelta

from ugv_backend import app_core as app_module


def test_load_robots_prefers_latest_telemetry_snapshot(monkeypatch):
    reported_at = datetime.now() - timedelta(seconds=30)

    monkeypatch.setattr(
        app_module,
        "query_all",
        lambda sql, params=None: [
            {
                "id": 1,
                "model": "巡检机器人-01",
                "ip_address": "192.168.31.200",
                "status": "idle",
                "health": 91,
                "battery": 78,
                "speed": 1.2,
                "signal_value": 60,
                "latency": 28,
                "lng": 121.817420,
                "lat": 31.091610,
                "heading": 15,
                "created_at": datetime(2026, 3, 31, 11, 0, 0),
                "telemetry_battery": 55,
                "telemetry_signal": 26,
                "telemetry_status": "online",
                "telemetry_lat": 31.092345,
                "telemetry_lng": 121.818765,
                "telemetry_reported_at": reported_at,
                "telemetry_source_ip": "192.168.31.200",
            }
        ],
    )

    robots = app_module.load_robots()

    assert len(robots) == 1
    robot = robots[0]
    assert robot["battery"] == 55
    assert robot["signal"] == 26
    assert robot["location"] == [121.818765, 31.092345]
    assert robot["networkStatus"] == "warning"
    assert robot["isRealtime"] is True
    assert robot["lastSeenAt"] == reported_at.isoformat(timespec="seconds")


def test_build_maintenance_items_uses_network_status():
    items = app_module.build_maintenance_items(
        [
            {
                "id": 1,
                "model": "巡检机器人-01",
                "status": "idle",
                "battery": 66,
                "health": 90,
                "signal": 18,
                "networkStatus": "offline",
                "lastSeenAt": "2026-03-31T12:20",
                "createdAt": "2026-03-31T12:00",
            }
        ],
        [],
    )

    assert items[0]["state"] == "critical"
    assert "网络已离线" in items[0]["summary"]
