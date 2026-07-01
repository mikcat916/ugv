import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QMessageBox, QHeaderView
from PyQt5.QtGui import QIcon, QPixmap
from MICCProject1.ui.Frm_InspectPoint import Ui_Frm_InspectPoint  # 导入自动生成的界面类
from MICCProject1.scripts.DBHelper import DBHelper
# 以下用于显示地图
from PyQt5.QtCore import QObject, pyqtSlot, QUrl, pyqtSignal, QEasingCurve, QPropertyAnimation, QCoreApplication, Qt
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QSizePolicy, QVBoxLayout, QSplitter, QWidget, QHBoxLayout, QLabel, QFrame, \
    QGraphicsOpacityEffect, QStyle
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF, PushButton, PrimaryPushButton, LineEdit
import requests
import json

class BLL_InspectPoint(QMainWindow):
    def __init__(self, on_prev=None, on_next=None, on_close=None, on_jump=None):
        super().__init__()
        self.ui = Ui_Frm_InspectPoint()
        self.ui.setupUi(self)
        self.db = DBHelper()
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_close = on_close
        self._on_jump = on_jump
        self._active_step = 1
        self.pointid = None
        self.init_ui()
        self.load_inspectpoint() #加载巡检点位
        self.load_inspectarea() # 加载巡检区域

        # 初始化当前选中的经纬度和点位ID
        self.selected_lng = None
        self.selected_lat = None
        self.current_point_id = None
        # 初始化地图通信
        self.init_map_channel()

        #self.setFixedSize(1639, 636)

    def init_ui(self) -> None:
        self.setMinimumSize(1120, 700)
        self._apply_window_icon()
        self._apply_form_style()
        self._replace_top_controls()
        self._apply_responsive_layout()
        self.ui.btn_Save.clicked.connect(self.on_save)
        self.ui.btn_Clear.clicked.connect(self.on_clear)
        self.ui.btn_Delete.clicked.connect(self.on_delete)
        self.ui.btn_Enable.clicked.connect(self.on_enable)
        self.ui.btn_Disable.clicked.connect(self.on_disable)
        self.ui.tv_InspectPoint.clicked.connect(self.on_select)
        self.ui.btn_Search.clicked.connect(self.on_search_address)
        # 绑定回车搜索（可选）
        self.ui.txt_MapAddress.returnPressed.connect(self.on_search_address)
        #显示当前区域所有点位标注
        self.ui.btn_showMarkers.clicked.connect(self.on_show_batch_markers)
        self.ui.btn_RemoveMarkers.clicked.connect(self.on_clear_batch_markers)

        self.ui.txt_PointType.addItems(["设备巡检","环境巡检","通道巡检"])
        self.ui.txt_PointType.setCurrentIndex(0)  # 默认选中第一个选项
        #新增:地图
        self.ui.widget_Map = QWebEngineView()
        self.ui.widget_Map.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 为GroupBox设置垂直布局
        layout = QVBoxLayout(self.ui.groupBox)
        layout.setContentsMargins(0, 0, 0, 0)  # 去除内边距，让web_view填满GroupBox
        # 手动创建QWebEngineView实例
        self.web_view = QWebEngineView()
        # 设置自适应大小（填满GroupBox）
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 将web_view添加到GroupBox的布局中
        layout.addWidget(self.web_view)
        self._init_nav()

    def _init_nav(self) -> None:
        self._nav_bar = QWidget(self)
        self._nav_bar.setObjectName("navBar")
        self._nav_bar.setFixedHeight(36)
        layout = QHBoxLayout(self._nav_bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._step_bar = self._build_step_bar(active_index=1)
        self._btn_prev = TransparentToolButton(FIF.LEFT_ARROW)
        self._btn_next = TransparentToolButton(FIF.RIGHT_ARROW)
        self._btn_close = TransparentToolButton(FIF.CLOSE)
        self._btn_prev.setToolTip("上一步")
        self._btn_next.setToolTip("下一步")
        self._btn_close.setToolTip("关闭")
        for btn in (self._btn_prev, self._btn_next, self._btn_close):
            btn.setFixedSize(28, 28)
            btn.setIconSize(btn.iconSize())
        self._btn_prev.clicked.connect(self._on_nav_prev)
        self._btn_next.clicked.connect(self._on_nav_next)
        self._btn_close.clicked.connect(self._on_nav_close)

        layout.addWidget(self._step_bar, 1)
        layout.addWidget(self._btn_prev)
        layout.addWidget(self._btn_next)
        layout.addWidget(self._btn_close)
        self._apply_nav_style()
        self._reposition_nav()

    def _build_step_bar(self, active_index: int) -> QWidget:
        bar = QFrame(self)
        bar.setObjectName("stepBar")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(10, 2, 10, 2)
        bar_layout.setSpacing(6)

        self._step_buttons = []
        labels = ["区域", "点位", "路线"]
        for i, name in enumerate(labels):
            btn = PushButton(name, bar)
            btn.setProperty("stepPill", True)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _=False, idx=i: self._on_step_clicked(idx))
            if i == active_index:
                btn.setChecked(True)
            self._step_buttons.append(btn)
            bar_layout.addWidget(btn)
            if i < len(labels) - 1:
                arrow = QLabel("->", bar)
                arrow.setObjectName("stepArrow")
                bar_layout.addWidget(arrow)

        self._active_step = active_index
        if self._step_buttons:
            self._animate_step(self._step_buttons[active_index])
        return bar

    def _apply_nav_style(self) -> None:
        self._nav_bar.setStyleSheet(
            "QWidget#navBar {"
            "background: rgba(255,255,255,210);"
            "border: 1px solid rgba(32,56,96,18);"
            "border-radius: 14px;"
            "}"
            "QFrame#stepBar {"
            "background: rgba(255,255,255,0.85);"
            "border: 1px solid rgba(40,80,140,20);"
            "border-radius: 14px;"
            "}"
            "QPushButton[stepPill='true'] {"
            "padding: 0 12px;"
            "border-radius: 13px;"
            "border: 1px solid rgba(0,0,0,20);"
            "background: rgba(255,255,255,0.7);"
            "color: #55606d;"
            "}"
            "QPushButton[stepPill='true']:hover {"
            "background: rgba(74,144,255,0.08);"
            "}"
            "QPushButton[stepPill='true']:checked {"
            "border: 1px solid #4a90ff;"
            "background: rgba(74,144,255,0.18);"
            "color: #1f2d3d;"
            "}"
            "QLabel#stepArrow {"
            "color: #8a97a5;"
            "}"
        )

    def _animate_step(self, btn: PushButton) -> None:
        effect = btn.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(btn)
            btn.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", btn)
        anim.setStartValue(0.6)
        anim.setEndValue(1.0)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        btn._step_anim = anim

    def _on_step_clicked(self, index: int) -> None:
        if index == self._active_step:
            return
        if getattr(self, "_step_buttons", None):
            if 0 <= index < len(self._step_buttons):
                self._animate_step(self._step_buttons[index])
        if callable(self._on_jump):
            self.close()
            self._on_jump(index)
            return
        if index < self._active_step and callable(self._on_prev):
            self.close()
            self._on_prev()
            return
        if index > self._active_step and callable(self._on_next):
            self.close()
            self._on_next()
            return

    def _reposition_nav(self) -> None:
        if self._dock_nav_bar():
            return
        w = self.width()
        title_h = self.style().pixelMetric(QStyle.PM_TitleBarHeight, None, self)
        self._nav_bar.adjustSize()
        self._nav_bar.move(w - self._nav_bar.width() - 12, max(8, title_h + 8))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()
        if hasattr(self, "_nav_bar"):
            self._reposition_nav()

    def _on_nav_prev(self) -> None:
        if callable(self._on_prev):
            self.close()
            self._on_prev()

    def _on_nav_next(self) -> None:
        if callable(self._on_next):
            self.close()
            self._on_next()

    def _on_nav_close(self) -> None:
        if callable(self._on_close):
            self._on_close()
        else:
            self.close()


    def load_inspectpoint(self) -> None:
        self.ui.tv_InspectPoint.setRowCount(0)
        recordlist = self.db.fetch_all("select *, ia.AreaName from InspectArea ia, InspectPoint ip where ip.AreaID = ia.AreaID")
        for row, record in enumerate(recordlist):
            self.ui.tv_InspectPoint.insertRow(row)
            self.ui.tv_InspectPoint.setItem(row, 0, QTableWidgetItem(str(record.get("PointId", ""))))  # 巡检点位ID
            self.ui.tv_InspectPoint.setItem(row, 1, QTableWidgetItem(str(record.get("PointName", ""))))  #点位名称
            self.ui.tv_InspectPoint.setItem(row, 2, QTableWidgetItem(str(record.get("AreaName", ""))))   #区域名称
            self.ui.tv_InspectPoint.setItem(row, 3,  QTableWidgetItem(str(record.get("Longitude",""))))  #经度
            self.ui.tv_InspectPoint.setItem(row, 4, QTableWidgetItem(str(record.get("Latitude",""))))  #纬度
            self.ui.tv_InspectPoint.setItem(row, 5, QTableWidgetItem("启用" if record.get("Status") == 1 else "禁用" )) #状态

        self.setup_table_view()


    def load_inspectarea(self):
        self.ui.txt_AreaId.clear()
        recordlist = self.db.fetch_all("SELECT AreaId, AreaName FROM InspectArea ORDER BY AreaId")
        if not recordlist:
            self.ui.txt_AreaId.addItem("暂无巡检区域")
            return
        for record in recordlist:
            areaid = record['AreaId']  # 通过键'AreaID'取对应值
            areaname = record['AreaName']  # 通过键'AreaName'取对应值
            self.ui.txt_AreaId.addItem(areaname,userData=areaid)


    def validate_required(self) -> bool:
        area_id = self.ui.txt_AreaId.currentData()
        if area_id is None:
            self.ui.lab_Note.setText("请先创建并选择巡检区域后再保存点位！")
            self.ui.lab_Note.setStyleSheet("color: red;")
            return False
        # 定义必填字段（控件变量 -> 字段名称）
        required = {
            self.ui.txt_PointName: "点位名称",
            self.ui.txt_PointCode: "点位编码"
        }
        for var, field_name in required.items():
            if not var.text().strip():
                self.ui.lab_Note.setText(f"{field_name}为必填项，请填写完整！")
                self.ui.lab_Note.setStyleSheet("color: red;")
                return False
        return True

    def setup_table_view(self) -> None:
        header = self.ui.tv_InspectPoint.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.ui.tv_InspectPoint.setAlternatingRowColors(True)
        self.ui.tv_InspectPoint.setShowGrid(True)
        self.ui.tv_InspectPoint.setStyleSheet(
            "QTableView {gridline-color: #d0d0d0; alternate-background-color: #f8f8f8;}"
        )

    def _apply_form_style(self) -> None:
        self.setStyleSheet(
            "QMainWindow {"
            "background: #f7f9fc;"
            "}"
            "QGroupBox {"
            "font: 600 13px 'Microsoft YaHei';"
            "border: 1px solid #dbe3ef;"
            "border-radius: 8px;"
            "margin-top: 10px;"
            "padding: 8px;"
            "}"
            "QGroupBox::title {"
            "subcontrol-origin: margin;"
            "left: 10px;"
            "padding: 0 6px;"
            "color: #2f3a4a;"
            "}"
            "QLabel {"
            "font: 13px 'Microsoft YaHei';"
            "color: #2f3a4a;"
            "}"
            "QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {"
            "font: 13px 'Microsoft YaHei';"
            "padding: 7px 9px;"
            "border: 1px solid #cfd7e3;"
            "border-radius: 6px;"
            "background: #ffffff;"
            "}"
            "QPushButton {"
            "font: 13px 'Microsoft YaHei';"
            "padding: 7px 16px;"
            "border-radius: 6px;"
            "border: 1px solid #cfd7e3;"
            "background: #ffffff;"
            "}"
            "QPushButton:hover {"
            "background: #eef4ff;"
            "border-color: #9bbcff;"
            "}"
            "QTableWidget {"
            "font: 13px 'Microsoft YaHei';"
            "gridline-color: #d0d7e2;"
            "background: #ffffff;"
            "}"
            "QHeaderView::section {"
            "font: 13px 'Microsoft YaHei';"
            "background: #f0f4fa;"
            "padding: 7px;"
            "border: 1px solid #dbe3ef;"
            "}"
        )
        for name in ("btn_Save", "btn_Clear", "btn_Delete", "btn_Enable", "btn_Disable", "btn_Search"):
            btn = getattr(self.ui, name, None)
            if btn:
                btn.setMinimumWidth(90)

    def _dock_nav_bar(self) -> bool:
        host = getattr(self.ui, "groupBox_2", None)
        table = getattr(self.ui, "tv_InspectPoint", None)
        if host is None or table is None:
            return False

        row_widget = getattr(self.ui, "layoutWidget", None)
        nav = self._nav_bar
        nav.setParent(host)
        nav.adjustSize()

        nav_y = 6
        nav_x = 8
        if row_widget is not None:
            row_h = row_widget.height()
            row_w = min(max(220, row_widget.width()), max(220, host.width() - 20))
            row_x = max(8, host.width() - row_w - 8)
            row_widget.setGeometry(row_x, 6, row_w, row_h)
            row_rect = row_widget.geometry()
            nav_y = row_rect.y() + row_rect.height() + 4

        nav.resize(host.width() - 16, nav.height())
        nav.move(max(6, nav_x), max(0, nav_y))

        min_table_y = nav.y() + nav.height() + 8
        new_y = max(40, min_table_y)
        new_h = max(100, host.height() - new_y - 10)
        new_w = max(220, host.width() - 20)
        table.setGeometry(10, new_y, new_w, new_h)
        return True

    def _apply_responsive_layout(self) -> None:
        if not hasattr(self.ui, "gbox_status") or not hasattr(self.ui, "groupBox_2") or not hasattr(self.ui, "groupBox"):
            return

        margin = 10
        gap = 10
        top = 10
        window_w = max(self.width(), self.minimumWidth())
        window_h = max(self.height(), self.minimumHeight())

        usable_w = max(900, window_w - margin * 2 - gap)
        left_w = min(450, max(380, int(usable_w * 0.38)))
        right_w = max(500, usable_w - left_w)
        right_x = margin + left_w + gap

        left_h = max(560, window_h - top - margin)
        top_left_h = min(420, max(340, int(left_h * 0.6)))
        bottom_left_h = max(180, left_h - top_left_h - gap)

        self.ui.gbox_status.setGeometry(margin, top, left_w, top_left_h)
        self.ui.groupBox_2.setGeometry(margin, top + top_left_h + gap, left_w, bottom_left_h)

        # Right side: search bar + map + bottom action buttons
        search_h = 35
        map_top = top + 50
        btn_h = 35
        btn_gap = 12
        btn_y = window_h - margin - btn_h
        map_h = max(240, btn_y - btn_gap - map_top)
        self.ui.groupBox.setGeometry(right_x, map_top, right_w, map_h)

        search_btn_w = min(240, max(180, int(right_w * 0.32)))
        search_input_w = max(200, right_w - search_btn_w - 10)
        self.ui.txt_MapAddress.setGeometry(right_x, top + 10, search_input_w, search_h)
        self.ui.btn_Search.setGeometry(right_x + search_input_w + 10, top + 8, search_btn_w, search_h)

        left_btn_w = max(220, int(right_w * 0.62))
        right_btn_w = max(140, right_w - left_btn_w - 12)
        self.ui.btn_showMarkers.setGeometry(right_x, btn_y, left_btn_w, btn_h)
        self.ui.btn_RemoveMarkers.setGeometry(right_x + left_btn_w + 12, btn_y, right_btn_w, btn_h)

    def _replace_top_controls(self) -> None:
        # Top buttons in list group box
        host = getattr(self.ui, "layoutWidget", None)
        layout = host.layout() if host is not None else None
        if layout is not None:
            for name in ("btn_Delete", "btn_Enable", "btn_Disable"):
                old = getattr(self.ui, name, None)
                if old:
                    old.hide()
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)

            btn_delete = PushButton("删除", host)
            btn_enable = PushButton("启用", host)
            btn_disable = PushButton("禁用", host)
            for btn in (btn_delete, btn_enable, btn_disable):
                btn.setFixedHeight(28)
                btn.setMinimumWidth(70)

            self.ui.btn_Delete = btn_delete
            self.ui.btn_Enable = btn_enable
            self.ui.btn_Disable = btn_disable

            layout.addWidget(btn_delete, 0, 0, 1, 1)
            layout.addWidget(btn_enable, 0, 1, 1, 1)
            layout.addWidget(btn_disable, 0, 2, 1, 1)

        # Top search controls
        old_input = getattr(self.ui, "txt_MapAddress", None)
        old_btn = getattr(self.ui, "btn_Search", None)
        if old_input is not None and old_btn is not None:
            old_input.hide()
            old_btn.hide()

            self._map_address = LineEdit(self)
            self._map_address.setPlaceholderText("输入地址（如：北京市朝阳区天安门）")
            self._map_address.setGeometry(old_input.geometry())
            self._map_address.setFixedHeight(old_input.height())

            self._btn_search = PrimaryPushButton("搜索地址并定位", self)
            self._btn_search.setGeometry(old_btn.geometry())
            self._btn_search.setFixedHeight(old_btn.height())

            self.ui.txt_MapAddress = self._map_address
            self.ui.btn_Search = self._btn_search

            self._btn_search.clicked.connect(self.on_search_address)
            self._map_address.returnPressed.connect(self.on_search_address)

    def _apply_window_icon(self) -> None:
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "robot.png"
        if not icon_path.exists():
            return
        pix = QPixmap(str(icon_path))
        if pix.isNull():
            return
        icon = QIcon()
        for size in (16, 24, 32, 48, 64):
            icon.addPixmap(
                pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app:
            app.setWindowIcon(icon)

    def on_save(self) -> None:
        if not self.validate_required():
            return
        else:
            areaId = self.ui.txt_AreaId.currentData()
            pointName = self.ui.txt_PointName.text().strip()
            pointCode = self.ui.txt_PointCode.text().strip()
            pointType = self.ui.txt_PointType.currentIndex()
            longitude = self.ui.txt_Longitude.text().strip()
            latitude = self.ui.txt_Latitude.text().strip()
            remark = self.ui.txt_Remark.text().strip()
            try:
                # 如果是添加用户，则要检测用户名
                if self.pointid:
                    query = """
                    UPDATE InspectPoint
                    SET AreaId = %s, PointName = %s, PointCode = %s, PointType=%s, Longitude=%s, Latitude=%s,  Remark = %s
                    WHERE PointId = %s
                    """
                    params = (areaId, pointName, pointCode, pointType, longitude, latitude, remark,  self.pointid)
                    i = self.db.execute_query(query, params)
                    if (i>0):
                        self.ui.lab_Note.setText("巡检点位信息修改成功！")
                        self.clear_input()
                        self.load_inspectpoint()
                    else:
                        self.ui.lab_Note.setText("巡检点位信息修改失败！" )
                else:
                    query = """
                        INSERT INTO InspectPoint (AreaId, PointName, PointCode, PointType, Longitude, Latitude, Remark, Status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                        """
                    params = (areaId, pointName, pointCode, pointType, longitude, latitude, remark)
                    i = self.db.execute_query(query, params)
                    if (i>0):
                        self.ui.lab_Note.setText("巡检点位信息添加成功！" )
                        self.clear_input()
                        self.load_inspectpoint()
                    else:
                        self.ui.lab_Note.setText("巡检点位信息添加失败！" )
            except Exception as exc:
                self.ui.lab_Note.setText("巡检点位信息保存失败！"+str(exc))
                return

    # 选中某一项巡检点位数据
    def on_select(self, index) -> None:
        ins_item = self.ui.tv_InspectPoint.item(index.row(), 0)
        if ins_item is None:
            return
        self.pointid = int(ins_item.text())
        records = self.db.fetch_all("SELECT * FROM InspectPoint WHERE PointId = %s", (self.pointid,))
        if not records:
            return
        record = records[0]
        # 所属机构：匹配时直接通过userData查找
        for index in range(self.ui.txt_AreaId.count()):
            if self.ui.txt_AreaId.itemData(index) == record.get("AreaID", ""):
                self.ui.txt_AreaId.setCurrentIndex(index)
                break

        self.ui.txt_PointName.setText(record.get("PointName", ""))
        self.ui.txt_PointCode.setText(record.get("PointCode", ""))

        self.ui.txt_PointType.setCurrentIndex(record.get("PointType", 0))
        self.ui.txt_Longitude.setText(str(record.get("Longitude", "")))
        self.ui.txt_Latitude.setText(str(record.get("Latitude", "")))
        self.ui.txt_Remark.setText(record.get("Remark", ""))
        self.ui.gbox_status.setTitle("修改巡检点位")
        self.ui.lab_Note.clear()
        # 地图定位到该巡检点
        lng = record.get("Longitude", "")
        lat = record.get("Latitude", "")
        #self.web_view.page().runJavaScript(f"map.setCenter([{lng}, {lat}])")
        self.web_view.page().runJavaScript(f"locatePatrolMarker(1, {lng}, {lat}, '')")

        # 删除巡检点位
    def on_delete(self) -> None:
        selection = self.ui.tv_InspectPoint.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要删除的巡检点位！")
            return

        reply = QMessageBox.question(self, "确认删除", "确定要删除选中的巡检点位吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        else:
            ins_item = self.ui.tv_InspectPoint.item(self.ui.tv_InspectPoint.currentRow(), 0)
            if ins_item is None:
                return
            self.pointid = int(ins_item.text())
            i = self.db.execute_query("DELETE FROM InspectPoint WHERE PointId = %s", (self.pointid,))
            if (i>0):
                self.ui.lab_Note.setText("巡检点位删除成功！")
                self.clear_input()
                self.load_inspectpoint()
            else:
                self.ui.lab_Note.setText("巡检点位删除失败！")

    # 启用巡检点位
    def on_enable(self) -> None:
        selection = self.ui.tv_InspectPoint.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要启用的巡检点位！")
            return
        else:
            ins_item = self.ui.tv_InspectPoint.item(self.ui.tv_InspectPoint.currentRow(), 0)
            if ins_item is None:
                return
            self.pointid = int(ins_item.text())
            i = self.db.execute_query("UPDATE InspectPoint SET Status = 1 WHERE PointId = %s", (self.pointid,))
            if (i > 0):
                self.ui.lab_Note.setText("巡检点位已启用！")
                self.clear_input()
                self.load_inspectpoint()
            else:
                self.ui.lab_Note.setText("巡检点位启用失败！")

    # 禁用巡检点位
    def on_disable(self) -> None:
        selection = self.ui.tv_InspectPoint.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要禁用的巡检点位！")
            return
        else:
            ins_item = self.ui.tv_InspectPoint.item(self.ui.tv_InspectPoint.currentRow(), 0)
            if ins_item is None:
                return
            self.pointid = int(ins_item.text())
            i = self.db.execute_query("UPDATE InspectPoint SET Status = 0 WHERE PointId = %s", (self.pointid,))
            if (i > 0):
                self.ui.lab_Note.setText("巡检点位已禁用！")
                self.clear_input()
                self.load_inspectpoint()
            else:
                self.ui.lab_Note.setText("巡检点位禁用失败！")

    # 清空输入框和提示
    def on_clear(self):
        self.clear_input()
        self.ui.lab_Note.text()

    # 清空输入框
    def clear_input(self) -> None:
        self.ui.txt_PointName.clear()
        self.ui.txt_PointCode.clear()
        self.ui.txt_Latitude.clear()
        self.ui.txt_Longitude.clear()
        #self.ui.txt_PointType.setCurrentIndex(0)
        self.ui.txt_Remark.clear()
        self.ui.gbox_status.setTitle("新增巡检点位")
        self.pointid = None

    def init_map_channel(self):
        """初始化地图通信通道"""
        self.channel = QWebChannel()
        self.map_communicator = MapCommunicator(self.ui.txt_Longitude, self.ui.txt_Latitude)
        self.channel.registerObject("pythonObj", self.map_communicator)
        self.web_view.page().setWebChannel(self.channel)

        # 绑定信号
        self.map_communicator.point_selected.connect(self.on_map_point_selected)
        self.map_communicator.marker_clicked.connect(self.on_marker_click)
        # 新增：绑定搜索结果信号
        self.map_communicator.searchresult.connect(self.on_search_result)

        # 加载高德地图
        self.load_amap_html()

    def load_amap_html(self):
        """加载高德地图HTML页面 - 替换为你的高德Web API Key"""
        AMAP_KEY = "dcfef1b0386efcf3b898a1ca8c6b7a78"
        #AMAP_KEY = "972be3208e3a02cb10ca46c7116d20c3"
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>高德地图</title>
            <style>
                html, body, #container {{ width: 100%; height: 100%; margin: 0; padding: 0; }}
            </style>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script type="text/javascript" src="https://webapi.amap.com/maps?v=2.0&key={AMAP_KEY}"></script>
        </head>
        <body>
            <div id="container"></div>
            <script>
                // 初始化Python通信对象
                let pythonObj = null;
                let clickMarker = null;  // 全局单例标注（统一管理搜索/巡检点标注）
                let batchMarkers = new Map();   // 新增：批量标注映射表（独立管理，避免冲突）
                // 2. 巡检点标注映射表（PointId → Marker）
                let patrolMarkers = new Map();
                // 初始化通信
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    pythonObj = channel.objects.pythonObj;
                }});

                // 初始化地图
                var map = new AMap.Map('container', {{
                     zoom: 17,  // 缩放级别调16，校区显示更清晰（可选15/17）
                         center: [113.589038,22.347812] // 中山大学珠海校区精准坐标
                }});

                // 核心修改：点击地图→获取经纬度+显示同样式图标（单例，自动替换）
        map.on('click', function(e) {{
            var lng = e.lnglat.getLng().toFixed(6);
            var lat = e.lnglat.getLat().toFixed(6);
            var lnglat_str = lng + ", " + lat;
            // 1. 传递经纬度给Python
            pythonObj.receive_lnglat(lnglat_str);
            // 2. 移除旧的点击图标（确保仅显示一个）
            if (clickMarker) {{
                map.remove(clickMarker);
                clickMarker = null;
            }}
            // 3. 创建新的点击图标（同巡检点样式）
            clickMarker = new AMap.Marker({{
                position: e.lnglat,
                map: map
            }});
        }});

        // ========== 新增：接收Python传经纬度（Web服务解析后），定位并标注 ==========
        window.locateByLngLat = function(lng, lat, address) {{
            // 1. 移除旧标注（复用原有单例逻辑，和点击/巡检点标注统一）
            if (clickMarker) {{
                map.remove(clickMarker);
                clickMarker = null;
            }}
            // 2. 转换经纬度为数字类型，避免JS解析错误
            const lngNum = parseFloat(lng);
            const latNum = parseFloat(lat);
            // 3. 地图定位到该经纬度
            map.setCenter([lngNum, latNum]);
            map.setZoom(17);
            // 4. 创建标注（和原有点击标注样式一致）
            clickMarker = new AMap.Marker({{
                position: [lngNum, latNum],
                map: map,
                title: address || "搜索定位点"  // 鼠标悬停显示地址
            }});
        }};

        // 供Python调用：添加/更新巡检点标注（原有逻辑，完全不变）
        window.addPatrolMarker = function(pointId, lng, lat, name) {{
            if (patrolMarkers.has(pointId)) {{
                return;
            }}
            let marker = new AMap.Marker({{
                position: [lng, lat],
                map: map,
                title: name,
            }});
            patrolMarkers.set(pointId, marker);
        }};

        // 供Python调用：定位并高亮巡检点标注（UI选中时调用）（原有逻辑，完全不变）
        window.locatePatrolMarker = function(pointId, lng, lat, name) {{
            // 2. 移除旧的点击图标（确保仅显示一个）
            if (clickMarker) {{
                map.remove(clickMarker);
                clickMarker = null;
            }}

           clickMarker = new AMap.Marker({{
                position: [lng, lat],
                map: map,
                title: name,
            }});
            // 地图定位+缩放
            map.setCenter([lng, lat]);
            map.setZoom(17);
        }};

        // 供Python调用：移除单个巡检点标注（原有逻辑，完全不变）
        window.removePatrolMarker = function(pointId) {{
            if (patrolMarkers.has(pointId)) {{
                map.remove(patrolMarkers.get(pointId));
                patrolMarkers.delete(pointId);
            }}
        }};

        // 供Python调用：清空所有巡检点标注（原有逻辑，完全不变）
        window.clearAllPatrolMarkers = function() {{
            patrolMarkers.forEach(marker => map.remove(marker));
            patrolMarkers.clear();
        }};

        // 可选：清空表单时移除点击图标（按需添加）（原有逻辑，完全不变）
        window.clearClickMarker = function() {{
            if (clickMarker) {{
                map.remove(clickMarker);
                clickMarker = null;
            }}
        }};
        // ========== 新增：批量显示位置标注核心函数 ==========
        window.showBatchMarkers = function(positionList) {{
            // 1. 先清除旧的批量标注（避免重复）
            if (batchMarkers.size > 0) {{
                batchMarkers.forEach(marker => map.remove(marker));
                batchMarkers.clear();
            }}

             // 新增：创建marker数组，用于后续自动缩放
            let markerArray = [];
            
            // 2. 循环创建批量标注（positionList是经纬度列表）
            positionList.forEach((item, index) => {{
                // 解析每个位置的经纬度和名称
                const lng = parseFloat(item.lng);
                const lat = parseFloat(item.lat);
                const name = item.name || `批量标注${{index+1}}`;

                // 创建批量标注（用蓝色图标区分原有标注）
                const marker = new AMap.Marker({{
                    position: [lng, lat],
                    map: map
                }});

                // 存储批量标注（用index作为唯一标识）
                batchMarkers.set(`batch_${{index}}`, marker);
                // 新增：将marker加入数组
                markerArray.push(marker);
            }});

            // 3. 修复：自动缩放适配所有批量标注（核心修改）
            if (markerArray.length > 0) {{
                // 高德2.0正确用法：传递marker数组给setFitView
                map.setFitView(markerArray, {{
                    padding: [80, 80, 80, 80], // 边距（避免标注贴边）
                    duration: 800 // 缩放动画时长（毫秒），更流畅
                }});
            }} else {{
                console.warn("无有效批量标注，跳过自动缩放");
            }}
        }};

        // ========== 新增：清除批量标注（可选，方便用户操作） ==========
        window.clearBatchMarkers = function() {{
            batchMarkers.forEach(marker => map.remove(marker));
            batchMarkers.clear();
        }};
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(html, baseUrl=QUrl("https://webapi.amap.com/"))

    def on_map_point_selected(self, lng, lat):
        """地图选点成功 - 更新经纬度显示"""
        self.selected_lng = lng
        self.selected_lat = lat
        #self.lnglat_label.setText(f"已选坐标：{lng:.6f}, {lat:.6f}")
        self.ui.txt_Longitude.setText(f"{lng:.6f}")
        self.ui.txt_Latitude.setText(f"{lat:.6f}")

    def on_marker_click(self, point_id):
        """点击地图标记 - 自动选中右侧对应列表项"""
        for i in range(self.ui.tv_InspectPoint.count()):
            item = self.ui.tv_InspectPoint.item(i)
            if item.data(1)[0] == point_id:
                #self.ui.tv_InspectPoint.setCurrentItem(item)
                self.ui.txt_PointName.setText(item.data(1)[0])

                #self.on_select(item)
                break

    import requests
    from PyQt5.QtWidgets import QMessageBox

    # 在你的主窗口类中新增以下方法
    def call_amap_web_service(self, address):
        """调用高德Web服务API解析地址（地址→经纬度）"""
        AMAP_KEY = "972be3208e3a02cb10ca46c7116d20c3"  # 需开通地理编码服务
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": AMAP_KEY,
            "address": address.strip(),
            "city": "全国"  # 适配你的地图中心（中山大学珠海校区），提升解析精度
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "1" and len(result.get("geocodes", [])) > 0:
                geocode = result["geocodes"][0]
                lng, lat = geocode["location"].split(",")
                return True, lng, lat
            else:
                err_info = result.get("info", "地址解析失败")
                return False, err_info, ""
        except requests.exceptions.RequestException as e:
            return False, f"网络错误：{str(e)}", ""

    def on_search_address(self):
        """点击搜索按钮 - Web服务解析地址后调用JS定位"""
        address = self.ui.txt_MapAddress.text().strip()
        if not address:
            QMessageBox.warning(self, "提示", "请输入有效地址！")
            return

        success, res1, res2 = self.call_amap_web_service(address)
        if success:
            # 调用新增的JS函数locateByLngLat
            lng, lat = res1, res2
            self.ui.txt_Longitude.setText(lng)
            self.ui.txt_Latitude.setText(lat)
            self.web_view.page().runJavaScript(f"locateByLngLat('{lng}', '{lat}', '{address}')")
            QMessageBox.information(self, "成功", f"定位成功！\n{address}\n经纬度：{lng},{lat}")
        else:
            QMessageBox.warning(self, "失败", f"解析失败：{res1}")

    @pyqtSlot(str, str)
    def on_search_result(self, res_type, message):
        """接收JS返回的搜索结果（成功/失败）"""
        if res_type == "success":
            # 成功：显示提示
            QMessageBox.information(self, "成功", message)
            # 可选：将解析后的经纬度填充到表单（如果需要）
            # 示例：提取经纬度（message格式：定位成功：xxx，经纬度：116.xxx,39.xxx）
            import re
            lnglat_match = re.search(r'经纬度：([\d.]+),([\d.]+)', message)
            if lnglat_match:
                self.selected_lng = float(lnglat_match.group(1))
                self.selected_lat = float(lnglat_match.group(2))
                self.ui.txt_Longitude.setText(f"{self.selected_lng:.6f}")
                self.ui.txt_Latitude.setText(f"{self.selected_lat:.6f}")
                #self.lnglat_label.setText(f"坐标：{self.selected_lng:.6f}, {self.selected_lat:.6f}")
        else:
            # 失败：显示错误提示
            QMessageBox.warning(self, "失败", message)

    def on_show_batch_markers(self):

        # ========== 示例：你的位置列表（可从数据库/文件读取） ==========
        # 格式：每个元素包含lng（经度）、lat（纬度）、name（名称）
        # position_list = [
        #     {"lng": "113.589038", "lat": "22.347812", "name": "中山大学珠海校区-图书馆"},
        #     {"lng": "113.590123", "lat": "22.348945", "name": "中山大学珠海校区-教学楼"},
        #     {"lng": "113.587890", "lat": "22.346789", "name": "中山大学珠海校区-食堂"},
        #     {"lng": "113.591234", "lat": "22.349876", "name": "中山大学珠海校区-宿舍区"}
        # ]
        area_id = self.ui.txt_AreaId.currentData()
        if area_id is None:
            QMessageBox.information(self, "提示", "当前没有可用的巡检区域。")
            return

        position_list=[]
        recordlist = self.db.fetch_all(
            "SELECT * FROM InspectPoint WHERE AreaID=%s",
            (area_id,),
        )
        for row, record in enumerate(recordlist):
            position = {
            "lng": str(record.get("Longitude", "")),  # 转为字符串，兼容数字/字符串类型
            "lat": str(record.get("Latitude", "")),
            "name": record.get("PointName", f"未知位置{len(position_list) + 1}")
            }
            # 过滤无效数据（经纬度为空的跳过）
            if position["lng"] and position["lat"]:
                position_list.append(position)

        # 1. 将Python列表转为JSON字符串（JS能解析）
        position_json = json.dumps(position_list, ensure_ascii=False)
        # 2. 调用JS的showBatchMarkers函数
        self.web_view.page().runJavaScript(f"showBatchMarkers({position_json})")

    def on_clear_batch_markers(self):
        """点击按钮：清除批量标注"""
        self.web_view.page().runJavaScript("clearBatchMarkers()")
# ------------------------------ 以下代码完全不变（地图/通信/界面） ------------------------------
class MapCommunicator(QObject):
    # 定义信号，用于向主窗口传递地图选点经纬度和标记点击事件
    point_selected = pyqtSignal(float, float)
    marker_clicked = pyqtSignal(int)
    # 搜索结果信号（类型：success/error，消息：提示文本）
    searchresult = pyqtSignal(str, str)

    def __init__(self, txt_lng, txt_lat):
        super().__init__()
        self.txt_lng = txt_lng  # 用于显示经纬度的QT标签
        self.txt_lat = txt_lat

        # 定义JS可调用的槽函数，接收经纬度字符串（装饰器必须加）
        # pyqtSlot(str) 表示接收字符串类型参数

    @pyqtSlot(str)
    def receive_lnglat(self, lnglat_str):
        # 如需单独获取经度、纬度，可拆分字符串
        lng, lat = lnglat_str.split(',')
        self.txt_lng.setText(lng)
        self.txt_lat.setText(lat)
        # print(f"经度：{lng.strip()}，纬度：{lat.strip()}")

    @pyqtSlot(str)
    def on_map_click(self, lnglat_str):
        """接收地图点击的经纬度"""
        lng, lat = map(float, lnglat_str.split(','))
        self.point_selected.emit(lng, lat)

    @pyqtSlot(str)
    def on_marker_click(self, point_id_str):
        """接收地图标记点击事件"""
        self.marker_clicked.emit(int(point_id_str))

    # 新增：接收JS的搜索结果
    @pyqtSlot(str, str)
    def search_result(self, res_type, message):
        self.searchresult.emit(res_type, message)


if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    window = BLL_InspectPoint()
    window.show()
    sys.exit(app.exec())

