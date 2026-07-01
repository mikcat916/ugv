# -*- coding: utf-8 -*-
"""通信信息编辑对话框。"""

from PyQt5.QtCore import QDateTime, Qt
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
    QVBoxLayout,
)

from qfluentwidgets import ComboBox, DateTimeEdit, DoubleSpinBox, EditableComboBox, PrimaryPushButton, PushButton, SpinBox

from .animations import enable_click_animations
from .database import DeviceDatabase
from .styles import DIALOG_STYLE


class CommunicationDialog(QDialog):
    """新增/编辑通信信息。"""

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
        title = "编辑通信信息" if self.is_edit_mode else "新增通信信息"
        self.setWindowTitle(title)
        self.setMinimumWidth(560)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)

        group = QGroupBox("通信字段")
        form = QFormLayout(group)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.device_combo = ComboBox()
        form.addRow("选择设备 *", self.device_combo)

        self.iface_combo = EditableComboBox()
        self.iface_combo.addItems(["wlan0", "eth0", "docker0"])
        form.addRow("网络接口", self.iface_combo)

        self.wifi_rx_spin = self._f(0, 100000, 2, " Mbps")
        form.addRow("WiFi接收速率", self.wifi_rx_spin)

        self.wifi_tx_spin = self._f(0, 100000, 2, " Mbps")
        form.addRow("WiFi发送速率", self.wifi_tx_spin)

        self.wifi_rssi_spin = SpinBox()
        self.wifi_rssi_spin.setRange(-200, 0)
        self.wifi_rssi_spin.setSuffix(" dBm")
        form.addRow("WiFi信号强度", self.wifi_rssi_spin)

        self.wifi_link_spin = SpinBox()
        self.wifi_link_spin.setRange(0, 100000)
        self.wifi_link_spin.setSuffix(" Mbps")
        form.addRow("WiFi链路速率", self.wifi_link_spin)

        self.wifi_loss_spin = self._f(0, 100, 2, " %")
        form.addRow("WiFi丢包率", self.wifi_loss_spin)

        self.ws_rx_spin = self._f(0, 100000, 2, " Mbps")
        form.addRow("WebSocket接收速率", self.ws_rx_spin)

        self.ws_tx_spin = self._f(0, 100000, 2, " Mbps")
        form.addRow("WebSocket发送速率", self.ws_tx_spin)

        self.ws_conn_spin = SpinBox()
        self.ws_conn_spin.setRange(0, 100000)
        form.addRow("WebSocket连接数", self.ws_conn_spin)

        self.ws_reconnect_spin = SpinBox()
        self.ws_reconnect_spin.setRange(0, 1000000)
        form.addRow("WebSocket重连次数", self.ws_reconnect_spin)

        self.net_status_spin = SpinBox()
        self.net_status_spin.setRange(0, 1)
        form.addRow("网络状态", self.net_status_spin)

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
    def _f(min_val, max_val, decimals, suffix):
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
        self.iface_combo.setCurrentText(self.data.get("IfaceName", "") or "")
        self.wifi_rx_spin.setValue(self.data.get("WifiRxRate", 0) or 0)
        self.wifi_tx_spin.setValue(self.data.get("WifiTxRate", 0) or 0)
        self.wifi_rssi_spin.setValue(int(self.data.get("WifiRSSI", 0) or 0))
        self.wifi_link_spin.setValue(int(self.data.get("WifiLinkSpeed", 0) or 0))
        self.wifi_loss_spin.setValue(self.data.get("WifiLossRate", 0) or 0)
        self.ws_rx_spin.setValue(self.data.get("WsRxRate", 0) or 0)
        self.ws_tx_spin.setValue(self.data.get("WsTxRate", 0) or 0)
        self.ws_conn_spin.setValue(int(self.data.get("WsConnCount", 0) or 0))
        self.ws_reconnect_spin.setValue(int(self.data.get("WsReconnectCount", 0) or 0))
        self.net_status_spin.setValue(int(self.data.get("NetStatus", 0) or 0))
        if self.data.get("Timestamp"):
            dt = QDateTime.fromString(str(self.data["Timestamp"]), "yyyy-MM-dd HH:mm:ss")
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
            "IfaceName": self.iface_combo.currentText().strip(),
            "WifiRxRate": self.wifi_rx_spin.value(),
            "WifiTxRate": self.wifi_tx_spin.value(),
            "WifiRSSI": self.wifi_rssi_spin.value(),
            "WifiLinkSpeed": self.wifi_link_spin.value(),
            "WifiLossRate": self.wifi_loss_spin.value(),
            "WsRxRate": self.ws_rx_spin.value(),
            "WsTxRate": self.ws_tx_spin.value(),
            "WsConnCount": self.ws_conn_spin.value(),
            "WsReconnectCount": self.ws_reconnect_spin.value(),
            "NetStatus": self.net_status_spin.value(),
            "Timestamp": self.timestamp_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
        }



