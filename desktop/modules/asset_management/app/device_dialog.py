# -*- coding: utf-8 -*-
"""
设备信息编辑对话框
用于添加和编辑设备信息
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox,
    QPushButton, QFileDialog, QMessageBox, QGroupBox,
    QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from qfluentwidgets import ComboBox, DoubleSpinBox, EditableComboBox, LineEdit, PrimaryPushButton, PushButton

from .animations import enable_click_animations
from .styles import DIALOG_STYLE
from .database import DeviceDatabase


class DeviceDialog(QDialog):
    """设备信息编辑对话框"""
    
    # 预定义的定位方式选项
    POSITIONING_OPTIONS = ['', 'GPS', '北斗', '激光SLAM', 'GPS+北斗', 'RTK', '视觉定位', '其他']
    
    # 预定义的型号选项
    MODEL_OPTIONS = ['', '四驱轮式无人车', '六驱轮式无人车', '履带式无人车', '四足机器人', '轮腿复合无人车', '其他']
    
    def __init__(self, parent=None, device_data=None, db: DeviceDatabase = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            device_data: 设备数据（编辑模式时传入）
            db: 数据库实例
        """
        super().__init__(parent)
        self.device_data = device_data
        self.db = db
        self.is_edit_mode = device_data is not None
        
        self._init_ui()
        self._apply_style()
        enable_click_animations(self)
        
        if self.is_edit_mode:
            self._load_data()
    
    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        title = "编辑设备" if self.is_edit_mode else "添加设备"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # 标题
        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(15)
        basic_layout.setLabelAlignment(Qt.AlignRight)
        
        # 无人车编号
        self.code_edit = LineEdit()
        self.code_edit.setPlaceholderText("请输入编号，如 U01-XX-YY")
        basic_layout.addRow("无人车编号 *", self.code_edit)
        
        # 无人车名称
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("请输入名称")
        basic_layout.addRow("无人车名称", self.name_edit)
        
        # 无人车型号
        self.model_combo = EditableComboBox()
        self.model_combo.addItems(self.MODEL_OPTIONS)
        basic_layout.addRow("无人车型号", self.model_combo)
        
        # 图片路径
        image_layout = QHBoxLayout()
        self.image_edit = LineEdit()
        self.image_edit.setPlaceholderText("本地路径或URL")
        browse_btn = PushButton("浏览")
        browse_btn.setObjectName("browseBtn")
        browse_btn.clicked.connect(self._browse_image)
        image_layout.addWidget(self.image_edit)
        image_layout.addWidget(browse_btn)
        basic_layout.addRow("无人车图片", image_layout)
        
        main_layout.addWidget(basic_group)
        
        # 技术参数组
        tech_group = QGroupBox("技术参数")
        tech_layout = QFormLayout(tech_group)
        tech_layout.setSpacing(15)
        tech_layout.setLabelAlignment(Qt.AlignRight)
        
        # 定位方式
        self.positioning_combo = EditableComboBox()
        self.positioning_combo.addItems(self.POSITIONING_OPTIONS)
        tech_layout.addRow("定位方式", self.positioning_combo)
        
        # 车载传感器
        self.sensor_edit = LineEdit()
        self.sensor_edit.setPlaceholderText("传感器ID，以逗号分隔，如 1,8,19")
        tech_layout.addRow("车载传感器", self.sensor_edit)
        
        # 电池容量
        self.battery_spin = DoubleSpinBox()
        self.battery_spin.setRange(0, 9999.99)
        self.battery_spin.setDecimals(2)
        self.battery_spin.setSuffix(" kWh")
        tech_layout.addRow("电池容量", self.battery_spin)
        
        main_layout.addWidget(tech_group)
        
        # 安全设置组
        security_group = QGroupBox("安全设置")
        security_layout = QFormLayout(security_group)
        security_layout.setSpacing(15)
        security_layout.setLabelAlignment(Qt.AlignRight)
        
        # 使用密码
        self.use_pwd_edit = LineEdit()
        self.use_pwd_edit.setEchoMode(QLineEdit.Password)
        self.use_pwd_edit.setPlaceholderText("留空不修改" if self.is_edit_mode else "请输入使用密码")
        security_layout.addRow("使用密码", self.use_pwd_edit)
        
        # 管理密码
        self.mag_pwd_edit = LineEdit()
        self.mag_pwd_edit.setEchoMode(QLineEdit.Password)
        self.mag_pwd_edit.setPlaceholderText("留空不修改" if self.is_edit_mode else "请输入管理密码")
        security_layout.addRow("管理密码", self.mag_pwd_edit)
        
        main_layout.addWidget(security_group)
        
        # 按钮区域
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
        """应用样式"""
        self.setStyleSheet(DIALOG_STYLE)
    
    def _load_data(self):
        """加载设备数据（编辑模式）"""
        if not self.device_data:
            return
        
        self.code_edit.setText(self.device_data.get('UGVCode', ''))
        self.name_edit.setText(self.device_data.get('UGVName', ''))
        self.image_edit.setText(self.device_data.get('UGVImage', ''))
        self.sensor_edit.setText(self.device_data.get('SensorList', ''))
        self.battery_spin.setValue(self.device_data.get('BatteryCap', 0) or 0)
        
        # 设置型号下拉框
        model = self.device_data.get('UGVModel', '')
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setCurrentText(model)
        
        # 设置定位方式下拉框
        positioning = self.device_data.get('Positioning', '')
        idx = self.positioning_combo.findText(positioning)
        if idx >= 0:
            self.positioning_combo.setCurrentIndex(idx)
        else:
            self.positioning_combo.setCurrentText(positioning)
    
    def _browse_image(self):
        """浏览选择图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
        )
        if file_path:
            self.image_edit.setText(file_path)
    
    def _validate(self) -> bool:
        """
        验证表单数据
        
        Returns:
            验证是否通过
        """
        # 检查必填字段
        code = self.code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, "验证失败", "无人车编号不能为空！")
            self.code_edit.setFocus()
            return False
        
        # 检查编号唯一性
        if self.db:
            exclude_id = self.device_data.get('UGVId') if self.is_edit_mode else None
            if self.db.check_code_exists(code, exclude_id):
                QMessageBox.warning(self, "验证失败", f"无人车编号 '{code}' 已存在！")
                self.code_edit.setFocus()
                return False
        
        return True
    
    def _save(self):
        """保存设备信息"""
        if not self._validate():
            return
        
        self.accept()
    
    def get_data(self) -> dict:
        """
        获取表单数据
        
        Returns:
            设备信息字典
        """
        data = {
            'UGVCode': self.code_edit.text().strip(),
            'UGVName': self.name_edit.text().strip(),
            'UGVImage': self.image_edit.text().strip(),
            'UGVModel': self.model_combo.currentText().strip(),
            'Positioning': self.positioning_combo.currentText().strip(),
            'SensorList': self.sensor_edit.text().strip(),
            'BatteryCap': self.battery_spin.value(),
        }
        
        # 密码处理
        use_pwd = self.use_pwd_edit.text()
        mag_pwd = self.mag_pwd_edit.text()
        
        if self.is_edit_mode:
            # 编辑模式：如果密码为空，保留原密码
            data['UsePwd'] = use_pwd if use_pwd else self.device_data.get('UsePwd', '')
            data['MagPwd'] = mag_pwd if mag_pwd else self.device_data.get('MagPwd', '')
            data['_update_password'] = bool(use_pwd or mag_pwd)
        else:
            # 添加模式：直接使用输入的密码
            data['UsePwd'] = use_pwd
            data['MagPwd'] = mag_pwd
        
        return data



