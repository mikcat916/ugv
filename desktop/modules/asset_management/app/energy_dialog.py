# -*- coding: utf-8 -*-
"""能量信息编辑对话框。"""

from datetime import timedelta

from PyQt5.QtCore import QDateTime, QTime, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from qfluentwidgets import ComboBox, DateTimeEdit, DoubleSpinBox, PrimaryPushButton, PushButton, SpinBox, TimeEdit

from .animations import enable_click_animations
from .database import DeviceDatabase
from .styles import DIALOG_STYLE


class EnergyDialog(QDialog):
    """新增/编辑能量信息。"""

    def __init__(self, parent=None, data=None, db: DeviceDatabase = None):
        super().__init__(parent)
        self.data = data
        self.db = db
        self.is_edit_mode = data is not None

        self._init_ui()
        self._apply_style()
        enable_click_animations(self)
        self._load_devices()
        if self.is_edit_mode:
            self._load_data()

    def _init_ui(self):
        title = "编辑能量信息" if self.is_edit_mode else "新增能量信息"
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)

        group = QGroupBox("能量字段")
        form = QFormLayout(group)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.device_combo = ComboBox()
        form.addRow("选择设备 *", self.device_combo)

        self.vddin_spin = self._make_float(0, 100000, 2, " W")
        form.addRow("输入功率", self.vddin_spin)

        self.vddsoc_spin = self._make_float(0, 100000, 2, " W")
        form.addRow("模块功耗", self.vddsoc_spin)

        self.vddcpu_spin = self._make_float(0, 100000, 2, " W")
        form.addRow("算力功耗", self.vddcpu_spin)

        self.compute_voltage_spin = self._make_float(0, 100000, 2, " V")
        form.addRow("算力电压", self.compute_voltage_spin)

        self.compute_current_spin = self._make_float(0, 100000, 2, " A")
        form.addRow("算力电流", self.compute_current_spin)

        self.uptime_edit = TimeEdit()
        self.uptime_edit.setDisplayFormat("HH:mm:ss")
        self.uptime_edit.setTime(QTime(0, 0, 0))
        form.addRow("稳定运行时长", self.uptime_edit)

        self.battery_level_spin = SpinBox()
        self.battery_level_spin.setRange(0, 100)
        self.battery_level_spin.setSuffix(" %")
        form.addRow("剩余电量", self.battery_level_spin)

        self.timestamp_edit = DateTimeEdit()
        self.timestamp_edit.setDateTime(QDateTime.currentDateTime())
        self.timestamp_edit.setCalendarPopup(True)
        self.timestamp_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        form.addRow("记录时间", self.timestamp_edit)

        main_layout.addWidget(group)
        main_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = PushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = PrimaryPushButton("保存")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    @staticmethod
    def _make_float(min_val, max_val, decimals, suffix):
        spin = DoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        return spin

    def _apply_style(self):
        self.setStyleSheet(DIALOG_STYLE)

    def _load_devices(self):
        if not self.db:
            return
        self.device_combo.clear()
        for device in self.db.get_all_devices():
            text = f"{device['UGVCode']} - {device.get('UGVName', '')}"
            self.device_combo.addItem(text, device["UGVId"])

    def _load_data(self):
        if not self.data:
            return
        ugv_id = self.data.get("UGVId")
        for i in range(self.device_combo.count()):
            if self.device_combo.itemData(i) == ugv_id:
                self.device_combo.setCurrentIndex(i)
                break

        self.vddin_spin.setValue(self.data.get("VDDIn", 0) or 0)
        self.vddsoc_spin.setValue(self.data.get("VDDSoc", 0) or 0)
        self.vddcpu_spin.setValue(self.data.get("VDDCpuGpuCv", 0) or 0)
        self.compute_voltage_spin.setValue(self.data.get("ComputeVoltage", 0) or 0)
        self.compute_current_spin.setValue(self.data.get("ComputeCurrent", 0) or 0)
        self.battery_level_spin.setValue(int(self.data.get("BatteryLevel", 0) or 0))

        uptime = self.data.get("Uptime")
        if isinstance(uptime, timedelta):
            total_seconds = int(uptime.total_seconds())
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            self.uptime_edit.setTime(QTime(hours, minutes, seconds))
        elif isinstance(uptime, str):
            parts = uptime.split(":")
            if len(parts) >= 3:
                try:
                    self.uptime_edit.setTime(QTime(int(parts[0]) % 24, int(parts[1]) % 60, int(parts[2]) % 60))
                except ValueError:
                    pass

        if self.data.get("TimeStamp"):
            dt = QDateTime.fromString(str(self.data["TimeStamp"]), "yyyy-MM-dd HH:mm:ss")
            if dt.isValid():
                self.timestamp_edit.setDateTime(dt)

    def _save(self):
        if self.device_combo.currentIndex() < 0:
            QMessageBox.warning(self, "验证失败", "请选择关联设备。")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "UGVId": self.device_combo.currentData(),
            "VDDIn": self.vddin_spin.value(),
            "VDDSoc": self.vddsoc_spin.value(),
            "VDDCpuGpuCv": self.vddcpu_spin.value(),
            "ComputeVoltage": self.compute_voltage_spin.value(),
            "ComputeCurrent": self.compute_current_spin.value(),
            "Uptime": self.uptime_edit.time().toString("HH:mm:ss"),
            "BatteryLevel": self.battery_level_spin.value(),
            "TimeStamp": self.timestamp_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
        }


