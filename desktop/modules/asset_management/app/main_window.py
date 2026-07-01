# -*- coding: utf-8 -*-
"""设备信息管理系统主窗口。"""

from PyQt5.QtCore import QEvent, QPoint, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import PrimaryPushButton, PushButton, TransparentToolButton

from .animations import enable_click_animations
from .communication_dialog import CommunicationDialog
from .computing_dialog import ComputingDialog
from .database import DeviceDatabase
from .device_dialog import DeviceDialog
from .energy_dialog import EnergyDialog
from .storage_dialog import StorageDialog
from .styles import MAIN_STYLE
from .system_dialog import SystemDialog


class MainWindow(QMainWindow):
    """主窗口。"""

    DEVICE_COLUMNS = [
        ("UGVId", "ID", 70),
        ("UGVCode", "设备编号", 140),
        ("UGVName", "设备名称", 140),
        ("UGVModel", "设备型号", 180),
        ("Positioning", "定位方式", 120),
        ("SensorList", "传感器", 200),
        ("BatteryCap", "电池容量(kWh)", 130),
        ("UGVImage", "图片路径", 260),
    ]

    STORAGE_COLUMNS = [
        ("MSId", "ID", 70),
        ("UGVCode", "设备编号", 120),
        ("UGVName", "设备名称", 120),
        ("MemTotal", "内存总量(GB)", 130),
        ("MemUsed", "内存已用(GB)", 130),
        ("MemFree", "内存空闲(GB)", 130),
        ("DiskTotal", "磁盘总量(GB)", 130),
        ("DiskUsed", "磁盘已用(GB)", 130),
        ("TimeStamp", "记录时间", 180),
    ]

    COMPUTING_COLUMNS = [
        ("CPId", "ID", 70),
        ("UGVCode", "设备编号", 120),
        ("UGVName", "设备名称", 120),
        ("CPUUsage", "CPU使用率(%)", 130),
        ("CPUTemp", "CPU温度(℃)", 120),
        ("GPUUsage", "GPU使用率(%)", 130),
        ("GPUTemp", "GPU温度(℃)", 120),
        ("GPUFreq", "GPU频率(MHz)", 140),
        ("TimeStamp", "记录时间", 180),
    ]

    SYSTEM_COLUMNS = [
        ("SIId", "ID", 70),
        ("UGVCode", "设备编号", 120),
        ("UGVName", "设备名称", 120),
        ("SerialNumber", "设备序列号", 180),
        ("HardwareModel", "开发板型号", 160),
        ("OpSystem", "操作系统", 140),
        ("Eth0", "Eth0", 130),
        ("Wlan0", "Wlan0", 130),
        ("Docker0", "Docker0", 130),
        ("HostName", "HostName", 140),
        ("Remark", "备注", 220),
    ]

    ENERGY_COLUMNS = [
        ("BEId", "ID", 70),
        ("UGVCode", "设备编号", 120),
        ("UGVName", "设备名称", 120),
        ("VDDIn", "输入功率(W)", 120),
        ("VDDSoc", "模块功耗(W)", 120),
        ("VDDCpuGpuCv", "算力功耗(W)", 130),
        ("ComputeVoltage", "算力电压(V)", 130),
        ("ComputeCurrent", "算力电流(A)", 130),
        ("Uptime", "稳定运行时长", 150),
        ("BatteryLevel", "剩余电量(%)", 130),
        ("TimeStamp", "记录时间", 180),
    ]

    COMMUNICATION_COLUMNS = [
        ("NMId", "ID", 70),
        ("UGVCode", "设备编号", 120),
        ("UGVName", "设备名称", 120),
        ("IfaceName", "网络接口", 110),
        ("WifiRxRate", "WiFi接收速率", 130),
        ("WifiTxRate", "WiFi发送速率", 130),
        ("WifiRSSI", "WiFi信号强度", 130),
        ("WifiLinkSpeed", "WiFi链路速率", 130),
        ("WifiLossRate", "WiFi丢包率(%)", 130),
        ("WsRxRate", "WS接收速率", 120),
        ("WsTxRate", "WS发送速率", 120),
        ("WsConnCount", "WS连接数", 110),
        ("WsReconnectCount", "WS重连次数", 120),
        ("NetStatus", "网络状态", 100),
        ("Timestamp", "记录时间", 180),
    ]

    def __init__(self, db: DeviceDatabase):
        super().__init__()
        self.db = db
        self._dragging = False
        self._drag_pos = QPoint()
        self._init_ui()
        self._apply_style()
        enable_click_animations(self)
        self._load_all_data()

    def _init_ui(self):
        self.setWindowTitle("设备信息管理系统")
        self.setMinimumSize(1200, 700)
        self.resize(1480, 860)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_StyledBackground, True)

        central_widget = QFrame()
        central_widget.setObjectName("rootFrame")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(10)

        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(52)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(6, 4, 6, 4)
        title_layout.setSpacing(8)

        self.btn_back = TransparentToolButton(FIF.LEFT_ARROW, self.title_bar)
        self.btn_back.setObjectName("titleBtn")
        self.btn_back.setFixedSize(36, 36)
        self.btn_back.clicked.connect(self.close)
        title_layout.addWidget(self.btn_back)

        self.title_label = QLabel("设备信息管理系统")
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)

        self.btn_min = TransparentToolButton(FIF.MINIMIZE, self.title_bar)
        self.btn_min.setObjectName("titleBtn")
        self.btn_min.setFixedSize(36, 36)
        self.btn_min.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.btn_min)

        self.btn_max = TransparentToolButton(FIF.FULL_SCREEN, self.title_bar)
        self.btn_max.setObjectName("titleBtn")
        self.btn_max.setFixedSize(36, 36)
        self.btn_max.clicked.connect(self._toggle_maximize)
        title_layout.addWidget(self.btn_max)

        self.btn_close = TransparentToolButton(FIF.CLOSE, self.title_bar)
        self.btn_close.setObjectName("titleBtnClose")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.clicked.connect(self.close)
        title_layout.addWidget(self.btn_close)

        self.title_bar.installEventFilter(self)
        layout.addWidget(self.title_bar)

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_widget)

        self.device_tab = self._create_tab_widget(self.DEVICE_COLUMNS, "device")
        self.tab_widget.addTab(self.device_tab["widget"], "设备基本信息")

        self.storage_tab = self._create_tab_widget(self.STORAGE_COLUMNS, "storage")
        self.tab_widget.addTab(self.storage_tab["widget"], "存储信息")

        self.computing_tab = self._create_tab_widget(self.COMPUTING_COLUMNS, "computing")
        self.tab_widget.addTab(self.computing_tab["widget"], "算力信息")

        self.system_tab = self._create_tab_widget(self.SYSTEM_COLUMNS, "system")
        self.tab_widget.addTab(self.system_tab["widget"], "系统信息")

        self.energy_tab = self._create_tab_widget(self.ENERGY_COLUMNS, "energy")
        self.tab_widget.addTab(self.energy_tab["widget"], "能量信息")

        self.communication_tab = self._create_tab_widget(self.COMMUNICATION_COLUMNS, "communication")
        self.tab_widget.addTab(self.communication_tab["widget"], "通信信息")

    def _create_tab_widget(self, columns, tab_type):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        add_btn = PrimaryPushButton("新增")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(lambda: self._add_record(tab_type))
        toolbar.addWidget(add_btn)

        edit_btn = PushButton("编辑")
        edit_btn.clicked.connect(lambda: self._edit_record(tab_type))
        toolbar.addWidget(edit_btn)

        delete_btn = PushButton("删除")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.clicked.connect(lambda: self._delete_record(tab_type))
        toolbar.addWidget(delete_btn)

        refresh_btn = PushButton("刷新")
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.clicked.connect(lambda: self._load_tab_data(tab_type))
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        search_edit = QLineEdit()
        search_edit.setObjectName("searchEdit")
        search_edit.setPlaceholderText("输入关键字后回车搜索")
        search_edit.setMinimumWidth(260)
        search_edit.returnPressed.connect(lambda: self._search(tab_type))
        toolbar.addWidget(search_edit)

        search_btn = PushButton("搜索")
        search_btn.setObjectName("searchBtn")
        search_btn.clicked.connect(lambda: self._search(tab_type))
        toolbar.addWidget(search_btn)

        clear_btn = PushButton("清空")
        clear_btn.setObjectName("searchBtn")
        clear_btn.clicked.connect(lambda: self._clear_search(tab_type))
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([col[1] for col in columns])

        header = table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setMinimumSectionSize(90)

        for i, (_, _, width) in enumerate(columns):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            table.setColumnWidth(i, width)

        if columns:
            header.setSectionResizeMode(len(columns) - 1, QHeaderView.Stretch)

        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.doubleClicked.connect(lambda: self._edit_record(tab_type))

        layout.addWidget(table)

        return {
            "widget": widget,
            "table": table,
            "search_edit": search_edit,
            "columns": columns,
        }

    def _apply_style(self):
        self.setStyleSheet(
            MAIN_STYLE
            + """
            QTabWidget::pane {
                border: 1px solid #dbe7f5;
                border-radius: 10px;
                background-color: rgba(255, 255, 255, 230);
            }
            QTabBar::tab {
                background: transparent;
                color: #5b6a7f;
                padding: 10px 18px;
                margin-right: 6px;
                border: none;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                color: #1473e6;
                font-weight: 600;
                border-bottom: 2px solid #48b7ff;
            }
            QTabBar::tab:hover:!selected {
                color: #2f84eb;
            }
        """
        )

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def eventFilter(self, obj, event):
        if obj is self.title_bar:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                target = self.title_bar.childAt(event.pos())
                if isinstance(target, QToolButton):
                    return False
                self._dragging = True
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.MouseMove and self._dragging:
                if not self.isMaximized():
                    self.move(event.globalPos() - self._drag_pos)
                return True
            if event.type() == QEvent.MouseButtonRelease:
                self._dragging = False
                return True
        return super().eventFilter(obj, event)

    def _on_tab_changed(self, index):
        tab_types = ["device", "storage", "computing", "system", "energy", "communication"]
        if 0 <= index < len(tab_types):
            self._update_status(tab_types[index])

    def _load_all_data(self):
        for tab_type in ["device", "storage", "computing", "system", "energy", "communication"]:
            self._load_tab_data(tab_type)
        self._update_status("device")

    def _load_tab_data(self, tab_type):
        if tab_type == "device":
            data = self.db.get_all_devices()
            self._populate_table(self.device_tab, data)
        elif tab_type == "storage":
            data = self.db.get_all_storage()
            self._populate_table(self.storage_tab, data)
        elif tab_type == "computing":
            data = self.db.get_all_computing()
            self._populate_table(self.computing_tab, data)
        elif tab_type == "system":
            data = self.db.get_all_system()
            self._populate_table(self.system_tab, data)
        elif tab_type == "energy":
            data = self.db.get_all_energy()
            self._populate_table(self.energy_tab, data)
        elif tab_type == "communication":
            data = self.db.get_all_communication()
            self._populate_table(self.communication_tab, data)
        self._update_status(tab_type)

    def _populate_table(self, tab_info, data):
        table = tab_info["table"]
        columns = tab_info["columns"]
        table.setRowCount(len(data))

        for row, record in enumerate(data):
            for col, (field, _, _) in enumerate(columns):
                value = record.get(field, "")
                if isinstance(value, float):
                    value = f"{value:.2f}"
                elif value is None:
                    value = ""
                else:
                    value = str(value)

                item = QTableWidgetItem(value)
                pk_field = columns[0][0]
                item.setData(Qt.UserRole, record.get(pk_field))
                if col == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col, item)

    def _update_status(self, tab_type):
        if not hasattr(self, "statusbar") or self.statusbar is None:
            return

        if tab_type == "device":
            self.statusbar.showMessage(f"设备: 共 {self.db.get_device_count()} 条记录")
        elif tab_type == "storage":
            self.statusbar.showMessage(f"存储信息: 共 {self.db.get_storage_count()} 条记录")
        elif tab_type == "computing":
            self.statusbar.showMessage(f"算力信息: 共 {self.db.get_computing_count()} 条记录")
        elif tab_type == "system":
            self.statusbar.showMessage(f"系统信息: 共 {self.db.get_system_count()} 条记录")
        elif tab_type == "energy":
            self.statusbar.showMessage(f"能量信息: 共 {self.db.get_energy_count()} 条记录")
        elif tab_type == "communication":
            self.statusbar.showMessage(f"通信信息: 共 {self.db.get_communication_count()} 条记录")

    def _get_selected_id(self, tab_type):
        table_map = {
            "device": self.device_tab["table"],
            "storage": self.storage_tab["table"],
            "computing": self.computing_tab["table"],
            "system": self.system_tab["table"],
            "energy": self.energy_tab["table"],
            "communication": self.communication_tab["table"],
        }
        table = table_map[tab_type]
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _add_record(self, tab_type):
        try:
            if tab_type == "device":
                dialog = DeviceDialog(self, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.insert_device(dialog.get_data())
                    self._load_tab_data("device")
                    QMessageBox.information(self, "成功", "设备添加成功")
            elif tab_type == "storage":
                dialog = StorageDialog(self, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.insert_storage(dialog.get_data())
                    self._load_tab_data("storage")
                    QMessageBox.information(self, "成功", "存储信息添加成功")
            elif tab_type == "computing":
                dialog = ComputingDialog(self, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.insert_computing(dialog.get_data())
                    self._load_tab_data("computing")
                    QMessageBox.information(self, "成功", "算力信息添加成功")
            elif tab_type == "system":
                dialog = SystemDialog(self, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.insert_system(dialog.get_data())
                    self._load_tab_data("system")
                    QMessageBox.information(self, "成功", "系统信息添加成功")
            elif tab_type == "energy":
                dialog = EnergyDialog(self, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.insert_energy(dialog.get_data())
                    self._load_tab_data("energy")
                    QMessageBox.information(self, "成功", "能量信息添加成功")
            elif tab_type == "communication":
                dialog = CommunicationDialog(self, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.insert_communication(dialog.get_data())
                    self._load_tab_data("communication")
                    QMessageBox.information(self, "成功", "通信信息添加成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {e}")

    def _edit_record(self, tab_type):
        record_id = self._get_selected_id(tab_type)
        if not record_id:
            QMessageBox.warning(self, "提示", "请先选择要编辑的记录")
            return

        try:
            if tab_type == "device":
                data = self.db.get_device_by_id(record_id)
                dialog = DeviceDialog(self, device_data=data, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    new_data = dialog.get_data()
                    update_pwd = new_data.pop("_update_password", False)
                    self.db.update_device(record_id, new_data, update_pwd)
                    self._load_tab_data("device")
                    QMessageBox.information(self, "成功", "设备更新成功")
            elif tab_type == "storage":
                data = self.db.get_storage_by_id(record_id)
                dialog = StorageDialog(self, data=data, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.update_storage(record_id, dialog.get_data())
                    self._load_tab_data("storage")
                    QMessageBox.information(self, "成功", "存储信息更新成功")
            elif tab_type == "computing":
                data = self.db.get_computing_by_id(record_id)
                dialog = ComputingDialog(self, data=data, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.update_computing(record_id, dialog.get_data())
                    self._load_tab_data("computing")
                    QMessageBox.information(self, "成功", "算力信息更新成功")
            elif tab_type == "system":
                data = self.db.get_system_by_id(record_id)
                dialog = SystemDialog(self, data=data, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.update_system(record_id, dialog.get_data())
                    self._load_tab_data("system")
                    QMessageBox.information(self, "成功", "系统信息更新成功")
            elif tab_type == "energy":
                data = self.db.get_energy_by_id(record_id)
                dialog = EnergyDialog(self, data=data, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.update_energy(record_id, dialog.get_data())
                    self._load_tab_data("energy")
                    QMessageBox.information(self, "成功", "能量信息更新成功")
            elif tab_type == "communication":
                data = self.db.get_communication_by_id(record_id)
                dialog = CommunicationDialog(self, data=data, db=self.db)
                if dialog.exec_() == dialog.Accepted:
                    self.db.update_communication(record_id, dialog.get_data())
                    self._load_tab_data("communication")
                    QMessageBox.information(self, "成功", "通信信息更新成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新失败: {e}")

    def _delete_record(self, tab_type):
        record_id = self._get_selected_id(tab_type)
        if not record_id:
            QMessageBox.warning(self, "提示", "请先选择要删除的记录")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除选中的记录吗？\n\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            if tab_type == "device":
                self.db.delete_device(record_id)
            elif tab_type == "storage":
                self.db.delete_storage(record_id)
            elif tab_type == "computing":
                self.db.delete_computing(record_id)
            elif tab_type == "system":
                self.db.delete_system(record_id)
            elif tab_type == "energy":
                self.db.delete_energy(record_id)
            elif tab_type == "communication":
                self.db.delete_communication(record_id)
            self._load_tab_data(tab_type)
            QMessageBox.information(self, "成功", "记录已删除")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def _search(self, tab_type):
        tab_map = {
            "device": self.device_tab,
            "storage": self.storage_tab,
            "computing": self.computing_tab,
            "system": self.system_tab,
            "energy": self.energy_tab,
            "communication": self.communication_tab,
        }
        keyword = tab_map[tab_type]["search_edit"].text().strip()
        if not keyword:
            self._load_tab_data(tab_type)
            return

        if tab_type == "device":
            data = self.db.search_devices(keyword)
            msg = f"搜索 '{keyword}' 找到 {len(data)} 条设备记录"
        elif tab_type == "storage":
            data = self.db.search_storage(keyword)
            msg = f"搜索 '{keyword}' 找到 {len(data)} 条存储记录"
        elif tab_type == "computing":
            data = self.db.search_computing(keyword)
            msg = f"搜索 '{keyword}' 找到 {len(data)} 条算力记录"
        elif tab_type == "system":
            data = self.db.search_system(keyword)
            msg = f"搜索 '{keyword}' 找到 {len(data)} 条系统记录"
        elif tab_type == "energy":
            data = self.db.search_energy(keyword)
            msg = f"搜索 '{keyword}' 找到 {len(data)} 条能量记录"
        else:
            data = self.db.search_communication(keyword)
            msg = f"搜索 '{keyword}' 找到 {len(data)} 条通信记录"

        self._populate_table(tab_map[tab_type], data)
        self.statusbar.showMessage(msg)

    def _clear_search(self, tab_type):
        tab_map = {
            "device": self.device_tab,
            "storage": self.storage_tab,
            "computing": self.computing_tab,
            "system": self.system_tab,
            "energy": self.energy_tab,
            "communication": self.communication_tab,
        }
        tab_map[tab_type]["search_edit"].clear()
        self._load_tab_data(tab_type)

    def closeEvent(self, event):
        if self.db:
            self.db.close()
        event.accept()
