from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "tools" / "device" / "iot_client.py"
SPEC = importlib.util.spec_from_file_location("iot_client_module", SCRIPT_PATH)
iot_client = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(iot_client)


def test_parse_nmea_sentence_from_gga():
    lat, lng = iot_client.parse_nmea_sentence("$GNGGA,024226.00,3114.1234,N,12128.5678,E,1,12,0.90,51.4,M,6.7,M,,*47")

    assert lat == 31.23539
    assert lng == 121.47613


def test_parse_iwlist_scan_output_filters_local_mac():
    output = """
    Cell 01 - Address: 00:11:22:33:44:55
              Channel:6
              Quality=70/70  Signal level=-39 dBm
    Cell 02 - Address: 02:AA:BB:CC:DD:EE
              Channel:1
              Quality=49/70  Signal level=-61 dBm
    """

    points = iot_client.parse_iwlist_scan_output(output)

    assert points == [{"macAddress": "00:11:22:33:44:55", "signalStrength": -39, "channel": 6}]


def test_get_gps_report_uses_serial_fallback_when_configured(monkeypatch):
    monkeypatch.setattr(
        iot_client,
        "probe_gps_via_gpspipe",
        lambda timeout: iot_client.build_gps_report("no_data", "gpspipe-json", message="gpspipe 仅返回 DEVICES"),
    )
    monkeypatch.setattr(
        iot_client,
        "probe_gps_via_raw_nmea",
        lambda timeout: iot_client.build_gps_report("no_data", "gpspipe-raw", message="没有原始 NMEA"),
    )
    monkeypatch.setattr(
        iot_client,
        "probe_gps_via_serial",
        lambda device, baud, timeout: iot_client.build_gps_report(
            "fix",
            f"serial:{device}",
            lat=31.2304,
            lng=121.4737,
            message="串口直读成功",
        ),
    )
    monkeypatch.setattr(iot_client, "serial_probe_supported", lambda: True)

    report = iot_client.get_gps_report(
        timeout=5,
        serial_device="/dev/ttyAMA0",
        serial_baud=9600,
        include_serial_fallback=True,
        auto_probe_serial=False,
    )

    assert report["status"] == "fix"
    assert report["source"] == "serial:/dev/ttyAMA0"
    assert report["lat"] == 31.2304
    assert len(report["attempts"]) == 3


def test_collect_telemetry_includes_gps_diagnostics(monkeypatch):
    monkeypatch.setattr(iot_client, "read_battery", lambda: None)
    monkeypatch.setattr(iot_client, "read_signal", lambda: 88)
    monkeypatch.setattr(
        iot_client,
        "get_gps_report",
        lambda **kwargs: iot_client.build_gps_report(
            "serial_silent",
            "serial:/dev/ttyAMA0",
            message="串口 /dev/ttyAMA0 没有任何输出",
        ),
    )
    monkeypatch.setattr(iot_client, "_read_file", lambda path: "42345" if "thermal_zone0" in path else None)

    payload, gps_report = iot_client.collect_telemetry(
        {
            "gps_timeout": 5,
            "gps_serial_device": "/dev/ttyAMA0",
            "gps_serial_baud": 9600,
        }
    )

    assert "lat" not in payload
    assert payload["signal"] == 88
    assert payload["extra"]["cpu_temp_c"] == 42.3
    assert payload["extra"]["gps"] == {
        "status": "serial_silent",
        "source": "serial:/dev/ttyAMA0",
        "message": "串口 /dev/ttyAMA0 没有任何输出",
    }
    assert gps_report["status"] == "serial_silent"


def test_collect_telemetry_uses_network_fallback(monkeypatch):
    monkeypatch.setattr(iot_client, "read_battery", lambda: None)
    monkeypatch.setattr(iot_client, "read_signal", lambda: 66)
    monkeypatch.setattr(
        iot_client,
        "get_gps_report",
        lambda **kwargs: iot_client.build_gps_report(
            "gpspipe_error",
            "gpspipe-raw",
            message="timeout",
        ),
    )
    monkeypatch.setattr(
        iot_client,
        "get_network_location_report",
        lambda cfg: iot_client.build_gps_report(
            "fix",
            "network:google",
            lat=31.2304,
            lng=121.4737,
            message="网络定位成功",
            details={"accuracyMeters": 180.0, "wifiCount": 3, "wifiScanStatus": "ok"},
        ),
    )
    monkeypatch.setattr(iot_client, "_read_file", lambda path: None)

    payload, location_report = iot_client.collect_telemetry(
        {
            "network_locate_enabled": True,
            "network_api_key": "dummy-key",
        }
    )

    assert payload["lat"] == 31.2304
    assert payload["lng"] == 121.4737
    assert payload["extra"]["locationSource"] == "network:google"
    assert payload["extra"]["networkLocation"]["status"] == "fix"
    assert payload["extra"]["networkLocation"]["accuracyMeters"] == 180.0
    assert location_report["source"] == "network:google"
