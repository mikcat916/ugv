# -*- coding: utf-8 -*-
"""
存储信息编辑对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QDoubleSpinBox, QComboBox, QPushButton, 
    QMessageBox, QGroupBox, QDateTimeEdit
)
from PyQt5.QtCore import Qt, QDateTime

from qfluentwidgets import ComboBox, DateTimeEdit, DoubleSpinBox, PrimaryPushButton, PushButton

from .animations import enable_click_animations
from .styles import DIALOG_STYLE
from .database import DeviceDatabase


class StorageDialog(QDialog):
    """存储信息编辑对话框"""
    
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
        title = "编辑存储信息" if self.is_edit_mode else "添加存储信息"
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
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
        
        # 内存信息
        mem_group = QGroupBox("内存信息 (GB)")
        mem_layout = QFormLayout(mem_group)
        mem_layout.setSpacing(12)
        mem_layout.setLabelAlignment(Qt.AlignRight)
        
        self.mem_total_spin = self._create_spin(0, 9999)
        mem_layout.addRow("物理内存总量", self.mem_total_spin)
        
        self.mem_used_spin = self._create_spin(0, 9999)
        mem_layout.addRow("已使用量", self.mem_used_spin)
        
        self.gpu_shared_spin = self._create_spin(0, 9999)
        mem_layout.addRow("GPU共享内存", self.gpu_shared_spin)
        
        self.mem_buffers_spin = self._create_spin(0, 9999)
        mem_layout.addRow("缓冲区内存", self.mem_buffers_spin)
        
        self.mem_cached_spin = self._create_spin(0, 9999)
        mem_layout.addRow("缓存内存", self.mem_cached_spin)
        
        self.mem_free_spin = self._create_spin(0, 9999)
        mem_layout.addRow("空闲内存", self.mem_free_spin)
        
        main_layout.addWidget(mem_group)
        
        # 磁盘信息
        disk_group = QGroupBox("磁盘信息 (GB)")
        disk_layout = QFormLayout(disk_group)
        disk_layout.setSpacing(12)
        disk_layout.setLabelAlignment(Qt.AlignRight)
        
        self.disk_total_spin = self._create_spin(0, 99999)
        disk_layout.addRow("磁盘总量", self.disk_total_spin)
        
        self.disk_used_spin = self._create_spin(0, 99999)
        disk_layout.addRow("已使用量", self.disk_used_spin)
        
        main_layout.addWidget(disk_group)
        
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
    
    def _create_spin(self, min_val, max_val):
        """创建数值输入框"""
        spin = DoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(2)
        return spin
    
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
        
        self.mem_total_spin.setValue(self.data.get('MemTotal', 0) or 0)
        self.mem_used_spin.setValue(self.data.get('MemUsed', 0) or 0)
        self.gpu_shared_spin.setValue(self.data.get('GPUShared', 0) or 0)
        self.mem_buffers_spin.setValue(self.data.get('MemBuffers', 0) or 0)
        self.mem_cached_spin.setValue(self.data.get('MemCached', 0) or 0)
        self.mem_free_spin.setValue(self.data.get('MemFree', 0) or 0)
        self.disk_total_spin.setValue(self.data.get('DiskTotal', 0) or 0)
        self.disk_used_spin.setValue(self.data.get('DiskUsed', 0) or 0)
        
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
            'MemTotal': self.mem_total_spin.value(),
            'MemUsed': self.mem_used_spin.value(),
            'GPUShared': self.gpu_shared_spin.value(),
            'MemBuffers': self.mem_buffers_spin.value(),
            'MemCached': self.mem_cached_spin.value(),
            'MemFree': self.mem_free_spin.value(),
            'DiskTotal': self.disk_total_spin.value(),
            'DiskUsed': self.disk_used_spin.value(),
            'TimeStamp': self.timestamp_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        }

