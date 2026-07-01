# -*- coding: utf-8 -*-
"""系统信息编辑对话框。"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from qfluentwidgets import ComboBox, LineEdit, PrimaryPushButton, PushButton, TextEdit

from .animations import enable_click_animations
from .database import DeviceDatabase
from .styles import DIALOG_STYLE


class SystemDialog(QDialog):
    """新增/编辑系统信息。"""

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
        title = "编辑系统信息" if self.is_edit_mode else "新增系统信息"
        self.setWindowTitle(title)
        self.setMinimumWidth(560)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)

        group = QGroupBox("系统字段")
        form = QFormLayout(group)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.device_combo = ComboBox()
        form.addRow("选择设备 *", self.device_combo)

        self.serial_edit = LineEdit()
        self.serial_edit.setPlaceholderText("设备唯一序列号")
        form.addRow("设备序列号", self.serial_edit)

        self.hardware_edit = LineEdit()
        self.hardware_edit.setPlaceholderText("开发板型号")
        form.addRow("开发板型号", self.hardware_edit)

        self.os_edit = LineEdit()
        self.os_edit.setPlaceholderText("操作系统名称")
        form.addRow("操作系统", self.os_edit)

        self.eth0_edit = LineEdit()
        self.eth0_edit.setPlaceholderText("以太网 IP 地址")
        form.addRow("Eth0", self.eth0_edit)

        self.wlan0_edit = LineEdit()
        self.wlan0_edit.setPlaceholderText("无线 IP 地址")
        form.addRow("Wlan0", self.wlan0_edit)

        self.docker0_edit = LineEdit()
        self.docker0_edit.setPlaceholderText("Docker 网络 IP")
        form.addRow("Docker0", self.docker0_edit)

        self.hostname_edit = LineEdit()
        self.hostname_edit.setPlaceholderText("Host 名称")
        form.addRow("HostName", self.hostname_edit)

        self.remark_edit = TextEdit()
        self.remark_edit.setPlaceholderText("备注")
        self.remark_edit.setMinimumHeight(80)
        form.addRow("备注", self.remark_edit)

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
        self.serial_edit.setText(self.data.get("SerialNumber", "") or "")
        self.hardware_edit.setText(self.data.get("HardwareModel", "") or "")
        self.os_edit.setText(self.data.get("OpSystem", "") or "")
        self.eth0_edit.setText(self.data.get("Eth0", "") or "")
        self.wlan0_edit.setText(self.data.get("Wlan0", "") or "")
        self.docker0_edit.setText(self.data.get("Docker0", "") or "")
        self.hostname_edit.setText(self.data.get("HostName", "") or "")
        self.remark_edit.setPlainText(self.data.get("Remark", "") or "")

    def _save(self):
        if self.device_combo.currentIndex() < 0:
            QMessageBox.warning(self, "验证失败", "请选择关联设备。")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "UGVId": self.device_combo.currentData(),
            "SerialNumber": self.serial_edit.text().strip(),
            "HardwareModel": self.hardware_edit.text().strip(),
            "OpSystem": self.os_edit.text().strip(),
            "Eth0": self.eth0_edit.text().strip(),
            "Wlan0": self.wlan0_edit.text().strip(),
            "Docker0": self.docker0_edit.text().strip(),
            "HostName": self.hostname_edit.text().strip(),
            "Remark": self.remark_edit.toPlainText().strip(),
        }


