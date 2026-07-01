# -*- coding: utf-8 -*-
"""
算力信息编辑对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox, 
    QPushButton, QMessageBox, QGroupBox, QDateTimeEdit
)
from PyQt5.QtCore import Qt, QDateTime

from qfluentwidgets import ComboBox, DateTimeEdit, DoubleSpinBox, LineEdit, PrimaryPushButton, PushButton

from .animations import enable_click_animations
from .styles import DIALOG_STYLE
from .database import DeviceDatabase


class ComputingDialog(QDialog):
    """算力信息编辑对话框"""
    
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
        """初始化UI"""
        title = "编辑算力信息" if self.is_edit_mode else "添加算力信息"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setModal(True)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # 标题
        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)
        
        # 设备选择
        device_group = QGroupBox("关联设备")
        device_layout = QFormLayout(device_group)
        device_layout.setSpacing(12)
        device_layout.setLabelAlignment(Qt.AlignRight)
        
        self.device_combo = ComboBox()
        device_layout.addRow("选择设备 *", self.device_combo)
        
        self.timestamp_edit = DateTimeEdit()
        self.timestamp_edit.setDateTime(QDateTime.currentDateTime())
        self.timestamp_edit.setCalendarPopup(True)
        self.timestamp_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        device_layout.addRow("记录时间", self.timestamp_edit)
        
        main_layout.addWidget(device_group)
        
        # CPU信息
        cpu_group = QGroupBox("CPU信息")
        cpu_layout = QFormLayout(cpu_group)
        cpu_layout.setSpacing(12)
        cpu_layout.setLabelAlignment(Qt.AlignRight)
        
        self.cpu_usage_spin = DoubleSpinBox()
        self.cpu_usage_spin.setRange(0, 100)
        self.cpu_usage_spin.setDecimals(2)
        self.cpu_usage_spin.setSuffix(" %")
        cpu_layout.addRow("CPU使用率", self.cpu_usage_spin)
        
        self.cpu_core_usage_edit = LineEdit()
        self.cpu_core_usage_edit.setPlaceholderText("[10.5, 20.3, 15.0, ...]")
        cpu_layout.addRow("各核使用率", self.cpu_core_usage_edit)
        
        self.cpu_core_freq_edit = LineEdit()
        self.cpu_core_freq_edit.setPlaceholderText("[0.9, 1.7, 2.0, ...] MHz")
        cpu_layout.addRow("各核频率", self.cpu_core_freq_edit)
        
        self.cpu_temp_spin = DoubleSpinBox()
        self.cpu_temp_spin.setRange(0, 150)
        self.cpu_temp_spin.setDecimals(1)
        self.cpu_temp_spin.setSuffix(" ℃")
        cpu_layout.addRow("CPU温度", self.cpu_temp_spin)
        
        main_layout.addWidget(cpu_group)
        
        # GPU信息
        gpu_group = QGroupBox("GPU信息")
        gpu_layout = QFormLayout(gpu_group)
        gpu_layout.setSpacing(12)
        gpu_layout.setLabelAlignment(Qt.AlignRight)
        
        self.gpu_usage_spin = DoubleSpinBox()
        self.gpu_usage_spin.setRange(0, 100)
        self.gpu_usage_spin.setDecimals(2)
        self.gpu_usage_spin.setSuffix(" %")
        gpu_layout.addRow("GPU使用率", self.gpu_usage_spin)
        
        self.gpu_temp_spin = DoubleSpinBox()
        self.gpu_temp_spin.setRange(0, 150)
        self.gpu_temp_spin.setDecimals(1)
        self.gpu_temp_spin.setSuffix(" ℃")
        gpu_layout.addRow("GPU温度", self.gpu_temp_spin)
        
        self.gpu_freq_spin = DoubleSpinBox()
        self.gpu_freq_spin.setRange(0, 9999)
        self.gpu_freq_spin.setDecimals(0)
        self.gpu_freq_spin.setSuffix(" MHz")
        gpu_layout.addRow("GPU频率", self.gpu_freq_spin)
        
        main_layout.addWidget(gpu_group)
        
        # 按钮
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
        """加载设备列表"""
        if not self.db:
            return
        devices = self.db.get_all_devices()
        self.device_combo.clear()
        for device in devices:
            display = f"{device['UGVCode']} - {device.get('UGVName', '')}"
            self.device_combo.addItem(display, device['UGVId'])
    
    def _load_data(self):
        """加载数据"""
        if not self.data:
            return
        
        # 选择设备
        ugv_id = self.data.get('UGVId')
        for i in range(self.device_combo.count()):
            if self.device_combo.itemData(i) == ugv_id:
                self.device_combo.setCurrentIndex(i)
                break
        
        self.cpu_usage_spin.setValue(self.data.get('CPUUsage', 0) or 0)
        self.cpu_core_usage_edit.setText(self.data.get('CPUCoreUsage', '') or '')
        self.cpu_core_freq_edit.setText(self.data.get('CPUCoreFreq', '') or '')
        self.cpu_temp_spin.setValue(self.data.get('CPUTemp', 0) or 0)
        self.gpu_usage_spin.setValue(self.data.get('GPUUsage', 0) or 0)
        self.gpu_temp_spin.setValue(self.data.get('GPUTemp', 0) or 0)
        self.gpu_freq_spin.setValue(self.data.get('GPUFreq', 0) or 0)
        
        if self.data.get('TimeStamp'):
            dt = QDateTime.fromString(str(self.data['TimeStamp']), "yyyy-MM-dd HH:mm:ss")
            if dt.isValid():
                self.timestamp_edit.setDateTime(dt)
    
    def _save(self):
        """保存"""
        if self.device_combo.currentIndex() < 0:
            QMessageBox.warning(self, "验证失败", "请选择关联设备！")
            return
        self.accept()
    
    def get_data(self) -> dict:
        """获取表单数据"""
        return {
            'UGVId': self.device_combo.currentData(),
            'CPUUsage': self.cpu_usage_spin.value(),
            'CPUCoreUsage': self.cpu_core_usage_edit.text().strip(),
            'CPUCoreFreq': self.cpu_core_freq_edit.text().strip(),
            'CPUTemp': self.cpu_temp_spin.value(),
            'GPUUsage': self.gpu_usage_spin.value(),
            'GPUTemp': self.gpu_temp_spin.value(),
            'GPUFreq': self.gpu_freq_spin.value(),
            'TimeStamp': self.timestamp_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        }

