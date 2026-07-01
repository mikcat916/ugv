import math
import json
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QCoreApplication, Qt, QUrl, QEvent
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QDialog, QAbstractItemView, QTableWidgetItem, QMessageBox, QHeaderView, \
    QWidget, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect, QVBoxLayout
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF, PushButton
from MICCProject1.ui.Frm_InspectRoute import Ui_Frm_InspectRoute  # 导入自动生成的界面类
from MICCProject1.scripts.DBHelper import DBHelper

try:
    from PyQt5.QtWebChannel import QWebChannel
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebChannel = None
    QWebEngineView = None


class BLL_InspectRoute(QDialog):
    def __init__(self, registration_mode: bool = False, on_prev=None, on_close=None, on_jump=None):
        super().__init__()
        self.ui = Ui_Frm_InspectRoute()
        self.ui.setupUi(self)
        self.db = DBHelper()
        self._on_prev = on_prev
        self._on_close = on_close
        self._on_jump = on_jump
        self._active_step = 2
        self.routeid = None
        self.web_view = None
        self._route_map_placeholder = None
        self._route_map_ready = False
        self._pending_route_points = None
        self._loading_route_points = False
        self._drag_row_from = -1
        self._drag_start_pos = None
        self._row_dragging = False
        self.init_ui()
        self.load_inspectroute() #加载巡检点位
        self.load_inspectarea() # 加载巡检区域
        self._init_nav()
        #self.setFixedSize(1639, 636)

    def _init_nav(self) -> None:
        self._nav_bar = QWidget(self)
        self._nav_bar.setObjectName("navBar")
        self._nav_bar.setFixedHeight(36)
        layout = QHBoxLayout(self._nav_bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._step_bar = self._build_step_bar(active_index=2)
        self._btn_prev = TransparentToolButton(FIF.LEFT_ARROW)
        self._btn_done = TransparentToolButton(FIF.ACCEPT)
        self._btn_close = TransparentToolButton(FIF.CLOSE)
        self._btn_prev.setToolTip("上一步")
        self._btn_done.setToolTip("完成")
        self._btn_close.setToolTip("关闭")
        for btn in (self._btn_prev, self._btn_done, self._btn_close):
            btn.setFixedSize(28, 28)
            btn.setIconSize(btn.iconSize())
        self._btn_prev.clicked.connect(self._on_nav_prev)
        self._btn_done.clicked.connect(self._on_nav_done)
        self._btn_close.clicked.connect(self._on_nav_close)

        layout.addWidget(self._step_bar, 1)
        layout.addWidget(self._btn_prev)
        layout.addWidget(self._btn_done)
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

    def _reposition_nav(self) -> None:
        w = self.width()
        self._nav_bar.setParent(self)
        self._nav_bar.adjustSize()
        self._nav_bar.move(w - self._nav_bar.width() - 12, 10)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_route_page()
        if hasattr(self, "_nav_bar"):
            self._reposition_nav()

    def _on_nav_prev(self) -> None:
        if callable(self._on_prev):
            self.close()
            self._on_prev()

    def _on_nav_done(self) -> None:
        if callable(self._on_close):
            self._on_close()
        else:
            self.close()

    def _on_nav_close(self) -> None:
        if callable(self._on_close):
            self._on_close()
        else:
            self.close()

    def init_ui(self) -> None:
        self._apply_window_icon()
        self._apply_form_style()
        self._replace_top_controls()
        self._tune_form_geometry()
        self._configure_tables()
        self._init_map_panel()
        self._relayout_route_page()
        self.ui.btn_New.clicked.connect(self.start_new_route)
        self.ui.txt_AreaId.currentIndexChanged.connect(self.on_area_changed)
        self.ui.btn_Save.clicked.connect(self.on_save)
        self.ui.btn_Clear.clicked.connect(self.on_clear)
        self.ui.btn_Delete.clicked.connect(self.on_delete)
        self.ui.btn_Enable.clicked.connect(self.on_enable)
        self.ui.btn_Disable.clicked.connect(self.on_disable)
        self.ui.tv_InspectRoute.clicked.connect(self.on_select)
        self.ui.btn_Add.clicked.connect(self.add_point_to_route)
        self.ui.btn_Remove.clicked.connect(self.remove_point_from_route)
        self.ui.btn_Up.clicked.connect(self.adjust_sort_up)
        self.ui.btn_Down.clicked.connect(self.adjust_sort_down)
        self.ui.btn_SaveRelation.clicked.connect(self.save_relation)
        self.ui.txt_PlanType.addItems(["自动规划","手动规划"])
        self.ui.txt_PlanType.setCurrentIndex(0)  # 默认选中第一个选项
        self.ui.txt_PathLength.setDecimals(2)  # 显示2位小数
        self.ui.txt_InsDuration.setDecimals(2)  # 显示2位小数
        self._clear_route_map()

    def load_inspectroute(self) -> None:
        self.ui.tv_InspectRoute.setRowCount(0)
        recordlist = self.db.fetch_all("select *, ia.AreaName from InspectArea ia, InspectRoute ir where ir.AreaID = ia.AreaID")
        for row, record in enumerate(recordlist):
            self.ui.tv_InspectRoute.insertRow(row)
            self.ui.tv_InspectRoute.setItem(row, 0, QTableWidgetItem(str(record.get("RouteId", ""))))  # 巡检点位ID
            self.ui.tv_InspectRoute.setItem(row, 1, QTableWidgetItem(str(record.get("AreaName", ""))))  #点位名称
            self.ui.tv_InspectRoute.setItem(row, 2, QTableWidgetItem(str(record.get("RouteName", ""))))   #区域名称
            self.ui.tv_InspectRoute.setItem(row, 3,  QTableWidgetItem(str(record.get("PointCount",""))))  #经度
            self.ui.tv_InspectRoute.setItem(row, 4, QTableWidgetItem(str(record.get("PathLength",""))))  #纬度
            self.ui.tv_InspectRoute.setItem(row, 5, QTableWidgetItem("启用" if record.get("Status") == 1 else "禁用" )) #状态

    def load_inspectarea(self):
        self.ui.txt_AreaId.clear()
        recordlist = self.db.fetch_all("SELECT AreaId, AreaName FROM InspectArea ORDER BY AreaId")
        if not recordlist:
            self.ui.txt_AreaId.addItem("暂无巡检区域")
            self.load_inspectPointByAreaId(None)
            self.ui.lab_selectedArea.setText("当前区域：未选择")
            return
        for record in recordlist:
            areaid = record['AreaId']  # 通过键'AreaID'取对应值
            areaname = record['AreaName']  # 通过键'AreaName'取对应值
            self.ui.txt_AreaId.addItem(areaname,userData=areaid)
        self.on_area_changed(self.ui.txt_AreaId.currentIndex())

    def on_area_changed(self, index: int) -> None:
        area_id = self.ui.txt_AreaId.itemData(index)
        area_name = self.ui.txt_AreaId.currentText().strip()
        if area_id is None:
            self.load_inspectPointByAreaId(None)
            self.ui.lab_selectedArea.setText("当前区域：未选择")
            if not self.routeid:
                self.ui.tv_InspectPoint2.setRowCount(0)
                self.ui.lab_selectedRoute.setText("当前路线：未选择")
                self._clear_route_map()
            return

        self.load_inspectPointByAreaId(area_id)
        self.ui.lab_selectedArea.setText(f"当前区域：{area_name}")
        if not self.routeid:
            self.ui.tv_InspectPoint2.setRowCount(0)
            self.ui.lab_selectedRoute.setText("当前路线：未选择")
            self._clear_route_map()

    def validate_required(self) -> bool:
        area_id = self.ui.txt_AreaId.currentData()
        if area_id is None:
            self.ui.lab_Note.setText("请先创建并选择巡检区域后再保存路线！")
            self.ui.lab_Note.setStyleSheet("color: red;")
            return False
        # 定义必填字段（控件变量 -> 字段名称）
        required = {
            self.ui.txt_RouteName: "路线名称",
            self.ui.txt_RouteCode: "路线编码"
        }
        for var, field_name in required.items():
            if not var.text().strip():
                self.ui.lab_Note.setText(f"{field_name}为必填项，请填写完整！")
                self.ui.lab_Note.setStyleSheet("color: red;")
                return False
        return True

    def _apply_form_style(self) -> None:
        self.setStyleSheet(
            "QDialog {"
            "background: #f7f9fc;"
            "}"
            "QGroupBox {"
            "font: 600 12px 'Microsoft YaHei';"
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
            "font: 12px 'Microsoft YaHei';"
            "color: #2f3a4a;"
            "}"
            "QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {"
            "font: 12px 'Microsoft YaHei';"
            "padding: 6px 8px;"
            "border: 1px solid #cfd7e3;"
            "border-radius: 6px;"
            "background: #ffffff;"
            "}"
            "QPushButton {"
            "font: 12px 'Microsoft YaHei';"
            "padding: 6px 14px;"
            "border-radius: 6px;"
            "border: 1px solid #cfd7e3;"
            "background: #ffffff;"
            "}"
            "QPushButton:hover {"
            "background: #eef4ff;"
            "border-color: #9bbcff;"
            "}"
            "QTableWidget {"
            "font: 12px 'Microsoft YaHei';"
            "gridline-color: #d0d7e2;"
            "background: #ffffff;"
            "}"
            "QHeaderView::section {"
            "font: 12px 'Microsoft YaHei';"
            "background: #f0f4fa;"
            "padding: 6px;"
            "border: 1px solid #dbe3ef;"
            "}"
        )
        for name in ("btn_Save", "btn_Clear", "btn_New", "btn_Delete", "btn_Enable", "btn_Disable"):
            btn = getattr(self.ui, name, None)
            if btn:
                btn.setMinimumWidth(90)

    def _tune_form_geometry(self) -> None:
        self.setMinimumSize(1160, 760)
        for name in (
            "txt_AreaId",
            "txt_RouteName",
            "txt_RouteCode",
            "txt_PlanType",
            "txt_PointCount",
            "txt_PathLength",
            "txt_InsDuration",
        ):
            widget = getattr(self.ui, name, None)
            if widget:
                widget.setFixedHeight(24)

        if hasattr(self.ui, "txt_Remark"):
            self.ui.txt_Remark.setFixedHeight(52)

        for name in ("label_11", "label_12"):
            label = getattr(self.ui, name, None)
            if label:
                label.setFixedHeight(20)

    def _relayout_route_page(self) -> None:
        margin = 12
        gap = 14
        top = 56
        width = self.width()
        height = self.height()
        content_width = width - margin * 2
        content_height = height - top - margin

        left_width = max(430, min(500, int(content_width * 0.39)))
        right_width = content_width - left_width - gap
        top_height = max(320, min(360, int(content_height * 0.44)))
        bottom_height = content_height - top_height - gap
        bottom_height = max(330, bottom_height)
        top_height = content_height - bottom_height - gap

        self.ui.groupBox_2.setGeometry(margin, top, left_width, top_height)
        self.ui.gbox_status.setGeometry(margin, top + top_height + gap, left_width, bottom_height)
        self.ui.groupbox3.setGeometry(margin + left_width + gap, top, right_width, top_height)
        self.ui.gbox_map.setGeometry(margin + left_width + gap, top + top_height + gap, right_width, bottom_height)

        self._relayout_route_list(left_width, top_height)
        self._relayout_status_form(left_width, bottom_height)
        self._relayout_relation_panel(right_width, top_height)

    def _relayout_route_list(self, group_width: int, group_height: int) -> None:
        inner_margin = 16
        button_gap = 10
        button_y = 28
        button_height = 30
        table_top = 68
        inner_width = group_width - inner_margin * 2
        button_width = max(82, (inner_width - button_gap * 3) // 4)
        buttons = [self.ui.btn_New, self.ui.btn_Delete, self.ui.btn_Enable, self.ui.btn_Disable]
        x = inner_margin
        for button in buttons:
            button.setGeometry(x, button_y, button_width, button_height)
            x += button_width + button_gap
        self.ui.tv_InspectRoute.setGeometry(
            inner_margin,
            table_top,
            inner_width,
            max(140, group_height - table_top - 12),
        )

    def _relayout_status_form(self, group_width: int, group_height: int) -> None:
        label_x = 18
        field_x = 84
        star_gap = 6
        right_margin = 18
        row_height = 26
        row_gap = 12
        top_y = 34
        field_width = group_width - field_x - right_margin - 18

        self.ui.label_2.setGeometry(label_x, top_y, 60, 24)
        self.ui.txt_AreaId.setGeometry(field_x, top_y, field_width, row_height)
        self.ui.label_15.setGeometry(field_x + field_width + star_gap, top_y + 4, 18, 18)

        y = top_y + row_height + row_gap
        self.ui.label.setGeometry(label_x, y, 60, 24)
        self.ui.txt_RouteName.setGeometry(field_x, y, field_width, row_height)
        self.ui.label_13.setGeometry(field_x + field_width + star_gap, y + 4, 18, 18)

        y += row_height + row_gap
        self.ui.label_8.setGeometry(label_x, y, 60, 24)
        self.ui.txt_RouteCode.setGeometry(field_x, y, field_width, row_height)
        self.ui.label_14.setGeometry(field_x + field_width + star_gap, y + 4, 18, 18)

        y += row_height + row_gap
        half_gap = 12
        compact_width = max(110, (field_width - 78 - half_gap) // 2)
        self.ui.label_7.setGeometry(label_x, y, 60, 24)
        self.ui.txt_PlanType.setGeometry(field_x, y, compact_width, row_height)
        right_label_x = field_x + compact_width + half_gap
        self.ui.label_12.setGeometry(right_label_x, y, 60, 24)
        self.ui.txt_PointCount.setGeometry(right_label_x + 64, y, field_width - compact_width - half_gap - 64, row_height)

        y += row_height + row_gap
        self.ui.label_10.setGeometry(label_x, y, 60, 24)
        self.ui.txt_PathLength.setGeometry(field_x, y, compact_width, row_height)
        self.ui.label_11.setGeometry(right_label_x, y, 60, 24)
        self.ui.txt_InsDuration.setGeometry(right_label_x + 64, y, field_width - compact_width - half_gap - 64, row_height)

        y += row_height + row_gap
        self.ui.label_9.setGeometry(label_x, y, 60, 24)
        note_height = 24
        buttons_height = 32
        buttons_bottom = 16
        buttons_y = group_height - buttons_height - buttons_bottom
        note_y = buttons_y - note_height - 10
        remark_height = max(60, note_y - y - 8)
        self.ui.txt_Remark.setGeometry(field_x, y, field_width, remark_height)
        self.ui.lab_Note.setGeometry(label_x, note_y, group_width - label_x - right_margin, note_height)
        self.ui.layoutWidget.setGeometry(
            max(40, (group_width - 290) // 2),
            buttons_y,
            min(290, group_width - 80),
            buttons_height,
        )

    def _relayout_relation_panel(self, group_width: int, group_height: int) -> None:
        left = 16
        top = 30
        bottom_margin = 14
        section_gap = 10
        button_col_width = 132
        table_top = 78
        table_height = max(150, group_height - table_top - bottom_margin)
        usable_width = group_width - left * 2
        # Prefer giving more space to the right (associated points) table.
        left_width = max(200, min(236, int(usable_width * 0.34)))
        right_width = usable_width - left_width - button_col_width - section_gap * 2
        min_right_width = 300
        if right_width < min_right_width:
            delta = min_right_width - right_width
            left_width = max(180, left_width - delta)
            right_width = usable_width - left_width - button_col_width - section_gap * 2

        button_x = left + left_width + section_gap
        right_x = button_x + button_col_width + section_gap
        right_width = max(280, right_width)

        self.ui.lab_selectedArea.setGeometry(left, top, left_width, 24)
        self.ui.lab_selectedRoute.setGeometry(right_x, top, right_width, 24)
        self.ui.label_5.setGeometry(left, top + 24, left_width, 20)
        self.ui.label_6.setGeometry(right_x, top + 24, right_width, 20)
        self.ui.tv_InspectPoint1.setGeometry(left, table_top, left_width, table_height)
        self.ui.tv_InspectPoint2.setGeometry(right_x, table_top, right_width, table_height)

        button_area_y = table_top + 8
        button_area_height = max(220, table_height - 16)
        self.ui.layoutWidget1.setGeometry(button_x, button_area_y, button_col_width, button_area_height)
        self.ui.gridLayout_3.setVerticalSpacing(10)
        self.ui.gridLayout_3.setHorizontalSpacing(0)
        for name in ("btn_Add", "btn_Remove", "btn_Up", "btn_Down", "btn_SaveRelation"):
            button = getattr(self.ui, name, None)
            if button:
                button.setMinimumHeight(32)
                button.setMinimumWidth(button_col_width)
                button.setMaximumWidth(button_col_width)

    def _configure_tables(self) -> None:
        for table in (
            self.ui.tv_InspectRoute,
            self.ui.tv_InspectPoint1,
            self.ui.tv_InspectPoint2,
        ):
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.setShowGrid(True)

        self.ui.tv_InspectRoute.setColumnHidden(0, True)
        route_header = self.ui.tv_InspectRoute.horizontalHeader()
        route_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        route_header.setSectionResizeMode(1, QHeaderView.Stretch)
        route_header.setSectionResizeMode(2, QHeaderView.Stretch)
        route_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        route_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        route_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.ui.tv_InspectRoute.setColumnWidth(3, 64)
        self.ui.tv_InspectRoute.setColumnWidth(4, 86)
        self.ui.tv_InspectRoute.setColumnWidth(5, 60)

        self.ui.tv_InspectPoint1.setColumnHidden(0, True)
        point_header = self.ui.tv_InspectPoint1.horizontalHeader()
        point_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        point_header.setSectionResizeMode(1, QHeaderView.Stretch)
        point_header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.ui.tv_InspectPoint1.setColumnWidth(2, 104)

        self.ui.tv_InspectPoint2.setColumnHidden(0, True)
        relation_header = self.ui.tv_InspectPoint2.horizontalHeader()
        relation_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        relation_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        relation_header.setSectionResizeMode(2, QHeaderView.Stretch)
        relation_header.setSectionResizeMode(3, QHeaderView.Fixed)
        relation_header.setSectionResizeMode(4, QHeaderView.Fixed)
        relation_header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.ui.tv_InspectPoint2.setColumnWidth(1, 72)
        self.ui.tv_InspectPoint2.setColumnWidth(3, 78)
        self.ui.tv_InspectPoint2.setColumnWidth(4, 64)
        self.ui.tv_InspectPoint2.setColumnWidth(5, 56)
        relation_header.setMinimumSectionSize(48)

        self.ui.tv_InspectPoint2.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self.ui.tv_InspectPoint2.setSortingEnabled(False)
        self.ui.tv_InspectPoint2.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.ui.tv_InspectPoint2.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        table = getattr(self.ui, "tv_InspectPoint2", None)
        if table is not None and obj is table.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_row_from = table.rowAt(event.pos().y())
                self._drag_start_pos = event.pos()
                self._row_dragging = False
            elif (
                event.type() == QEvent.MouseMove
                and self._drag_row_from >= 0
                and (event.buttons() & Qt.LeftButton)
                and self._drag_start_pos is not None
            ):
                if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                    self._row_dragging = True
                    table.setCursor(Qt.ClosedHandCursor)
            elif event.type() == QEvent.MouseButtonRelease:
                table.unsetCursor()
                if self._row_dragging and self._drag_row_from >= 0:
                    target_row = table.rowAt(event.pos().y())
                    if target_row < 0:
                        target_row = table.rowCount() - 1
                    self._move_route_point_row(self._drag_row_from, target_row)
                self._drag_row_from = -1
                self._drag_start_pos = None
                self._row_dragging = False
        return super().eventFilter(obj, event)

    def _move_route_point_row(self, src_row: int, dst_row: int) -> None:
        table = self.ui.tv_InspectPoint2
        row_count = table.rowCount()
        if row_count <= 1:
            return
        if src_row < 0 or src_row >= row_count or dst_row < 0:
            return
        if dst_row >= row_count:
            dst_row = row_count - 1
        if src_row == dst_row:
            return

        items = [table.takeItem(src_row, col) for col in range(table.columnCount())]
        table.removeRow(src_row)
        if src_row < dst_row:
            dst_row -= 1
        table.insertRow(dst_row)
        for col, item in enumerate(items):
            if item is None:
                item = QTableWidgetItem("")
            table.setItem(dst_row, col, item)
        table.selectRow(dst_row)
        self._persist_route_point_order()

    def _init_map_panel(self) -> None:
        host = getattr(self.ui, "gbox_map", None)
        if host is None:
            return

        layout = host.layout()
        if layout is None:
            layout = QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        if QWebEngineView is None or QWebChannel is None:
            self._route_map_placeholder = QLabel("地图预览需要安装 PyQtWebEngine", host)
            self._route_map_placeholder.setAlignment(Qt.AlignCenter)
            layout.addWidget(self._route_map_placeholder)
            self._route_map_ready = False
            return

        self.web_view = QWebEngineView(host)
        layout.addWidget(self.web_view)
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self._on_map_load_finished)
        self._load_route_map_html()

    def _load_route_map_html(self) -> None:
        if self.web_view is None:
            return

        amap_key = "dcfef1b0386efcf3b898a1ca8c6b7a78"
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>路线预览</title>
            <style>
                html, body, #container {{
                    width: 100%;
                    height: 100%;
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                    background: #eef3f9;
                }}
            </style>
            <script src="https://webapi.amap.com/maps?v=2.0&key={amap_key}"></script>
        </head>
        <body>
            <div id="container"></div>
            <script>
                var map = new AMap.Map('container', {{
                    zoom: 16,
                    center: [113.589038, 22.347812],
                    viewMode: '2D'
                }});
                var markers = [];
                var routeLine = null;

                function clearRoutePreview() {{
                    if (routeLine) {{
                        map.remove(routeLine);
                        routeLine = null;
                    }}
                    if (markers.length) {{
                        map.remove(markers);
                        markers = [];
                    }}
                }}

                function showRoutePreview(points) {{
                    clearRoutePreview();
                    if (!points || !points.length) {{
                        return;
                    }}

                    markers = points.map(function(point, index) {{
                        var label = String(index + 1);
                        return new AMap.Marker({{
                            position: [point.lng, point.lat],
                            title: point.name || label,
                            label: {{
                                content: label,
                                direction: 'top'
                            }}
                        }});
                    }});
                    map.add(markers);

                    var path = points.map(function(point) {{
                        return [point.lng, point.lat];
                    }});

                    if (path.length >= 2) {{
                        routeLine = new AMap.Polyline({{
                            path: path,
                            strokeColor: '#2d7ff9',
                            strokeOpacity: 0.95,
                            strokeWeight: 5,
                            strokeStyle: 'solid'
                        }});
                        map.add(routeLine);
                    }}

                    var overlays = markers.slice();
                    if (routeLine) {{
                        overlays.push(routeLine);
                    }}
                    map.setFitView(overlays, false, [40, 40, 40, 40]);
                }}
            </script>
        </body>
        </html>
        """
        self._route_map_ready = False
        self.web_view.setHtml(html, baseUrl=QUrl("https://webapi.amap.com/"))

    def _on_map_load_finished(self, ok: bool) -> None:
        self._route_map_ready = ok
        if not ok:
            return
        if self._pending_route_points is None:
            self._clear_route_map()
            return
        self._apply_route_map_points(self._pending_route_points)

    def _clear_route_map(self) -> None:
        self._pending_route_points = []
        if self.web_view is not None and self._route_map_ready:
            self.web_view.page().runJavaScript(
                "if (typeof clearRoutePreview === 'function') { clearRoutePreview(); }"
            )

    def _apply_route_map_points(self, points) -> None:
        self._pending_route_points = list(points)
        if self.web_view is None or not self._route_map_ready:
            return
        payload = json.dumps(self._pending_route_points, ensure_ascii=False)
        self.web_view.page().runJavaScript(
            f"if (typeof showRoutePreview === 'function') {{ showRoutePreview({payload}); }}"
        )

    def _refresh_route_map(self, route_id=None) -> None:
        if self.web_view is None:
            return

        route_id = route_id if route_id is not None else self.routeid
        if not route_id:
            self._clear_route_map()
            return

        recordlist = self.db.fetch_all(
            """
            SELECT ip.Longitude, ip.Latitude, ip.PointName
            FROM InspectRoutePoint rp
            JOIN InspectPoint ip ON rp.PointId = ip.PointId
            WHERE rp.RouteId = %s
            ORDER BY rp.SortNo
            """,
            (route_id,),
        )

        points = []
        for record in recordlist:
            lng = record.get("Longitude")
            lat = record.get("Latitude")
            if lng is None or lat is None:
                continue
            points.append(
                {
                    "lng": float(lng),
                    "lat": float(lat),
                    "name": record.get("PointName") or "",
                }
            )
        self._apply_route_map_points(points)

    def _dock_nav_bar(self) -> bool:
        return False

    def _replace_top_controls(self) -> None:
        host = getattr(self.ui, "groupBox_2", None)
        if host is None:
            return

        def _swap_button(name: str, text: str) -> PushButton | None:
            old = getattr(self.ui, name, None)
            if old is None:
                return None
            rect = old.geometry()
            old.hide()
            btn = PushButton(text, host)
            btn.setGeometry(rect)
            btn.setFixedHeight(rect.height())
            btn.setMinimumWidth(rect.width())
            setattr(self.ui, name, btn)
            return btn

        _swap_button("btn_New", "新建")
        _swap_button("btn_Delete", "删除")
        _swap_button("btn_Enable", "启用")
        _swap_button("btn_Disable", "禁用")

    def start_new_route(self) -> None:
        self.clear_input()
        self.ui.gbox_status.setTitle("新增巡检路线")
        self.ui.lab_Note.setText("已切换到新建模式，请填写路线信息后保存。")
        self.ui.lab_Note.setStyleSheet("color: #2f6feb;")
        self.ui.txt_RouteName.setFocus()

    def _find_route_row(self, route_id: int) -> int:
        for row in range(self.ui.tv_InspectRoute.rowCount()):
            item = self.ui.tv_InspectRoute.item(row, 0)
            if item is not None and item.text() == str(route_id):
                return row
        return -1

    def _select_route_by_id(self, route_id: int) -> None:
        row = self._find_route_row(route_id)
        if row < 0:
            return
        self.ui.tv_InspectRoute.selectRow(row)
        self.on_select(row)

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
            routeName = self.ui.txt_RouteName.text().strip()
            routeCode = self.ui.txt_RouteCode.text().strip()
            planType = self.ui.txt_PlanType.currentIndex()
            pointCount = self.ui.txt_PointCount.value()
            pathLength = self.ui.txt_PathLength.value()
            insDuration = self.ui.txt_InsDuration.value()
            remark = self.ui.txt_Remark.toPlainText().strip()

            try:
                # 新增
                if not self.routeid:
                    # 校验路线编码唯一性
                    check_sql = "SELECT * FROM InspectRoute WHERE RouteCode=%s"
                    if self.db.execute_query(check_sql, (routeCode,)):
                        QMessageBox.warning(self, "提示", "路线编码已存在！")
                        return
                    # 插入数据
                    query = """
                                INSERT INTO InspectRoute (AreaId, RouteName, RouteCode, PlanType, Status, PointCount, PathLength, InsDuration,Remark)
                                VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s)
                                """
                    params = (areaId, routeName, routeCode, planType, pointCount, pathLength,insDuration, remark)
                    i = self.db.execute_query(query, params)
                    if i is None:
                        self.ui.lab_Note.setText("巡检路线添加失败！")
                    else:
                        new_route = self.db.fetch_all(
                            "SELECT RouteId FROM InspectRoute WHERE RouteCode=%s ORDER BY RouteId DESC LIMIT 1",
                            (routeCode,),
                        )
                        self.load_inspectroute()
                        if new_route:
                            self.routeid = int(new_route[0]["RouteId"])
                            self._select_route_by_id(self.routeid)
                        self.ui.lab_Note.setText("巡检路线添加成功！")
                        if hasattr(self.ui, "lab_selectedRoute"):
                            self.ui.lab_selectedRoute.setText(f"当前路线：{routeName}")
                        self.ui.gbox_status.setTitle("修改巡检路线")
                else:
                    duplicate = self.db.fetch_all(
                        "SELECT RouteId FROM InspectRoute WHERE RouteCode=%s AND RouteId<>%s",
                        (routeCode, self.routeid),
                    )
                    if duplicate:
                        QMessageBox.warning(self, "提示", "路线编码已存在！")
                        return
                    query = """
                    UPDATE InspectRoute
                    SET AreaId = %s, RouteName = %s, RouteCode = %s, PlanType=%s, PointCount=%s, PathLength=%s, InsDuration=%s,  Remark = %s
                    WHERE RouteId = %s
                    """
                    params = (areaId, routeName, routeCode, planType, pointCount, pathLength,insDuration, remark,  self.routeid)
                    i = self.db.execute_query(query, params)
                    if i is None:
                        self.ui.lab_Note.setText("巡检路线修改失败！")
                    else:
                        self.ui.lab_Note.setText("巡检路线修改成功！" if i > 0 else "巡检路线未发生变更。")
                        self.clear_input()
                        self.load_inspectroute()
            except Exception as exc:
                self.ui.lab_Note.setText("巡检路线保存失败！"+str(exc))
                return

    # 选中某一项巡检点位数据
    def on_select(self, index) -> None:
        row = index.row() if hasattr(index, 'row') else int(index)
        ins_item = self.ui.tv_InspectRoute.item(row, 0)
        if ins_item is None:
            return
        self.routeid = int(ins_item.text())
        recordlist = self.db.fetch_all("SELECT * FROM InspectRoute WHERE RouteId = %s", (self.routeid,))
        if not recordlist:
            return
        record = recordlist[0]
        # 所属机构：匹配时直接通过userData查找
        for i in range(self.ui.txt_AreaId.count()):
            if self.ui.txt_AreaId.itemData(i) == record.get("AreaID", ""):
                self.ui.txt_AreaId.setCurrentIndex(i)
                break

        self.ui.txt_RouteName.setText(record.get("RouteName", ""))
        self.ui.txt_RouteCode.setText(record.get("RouteCode", ""))
        self.ui.txt_PlanType.setCurrentIndex(record.get("PlanType", 0))
        self.ui.txt_PointCount.setValue(record.get("PointCount", 0))
        path_length = record.get("PathLength")
        self.ui.txt_PathLength.setValue(float(path_length) if path_length else 0.0)
        ins_duration = record.get("InsDuration")
        self.ui.txt_InsDuration.setValue(float(ins_duration) if ins_duration else 0.0)
        self.ui.txt_Remark.setPlainText(record.get("Remark", "") or "")
        self.ui.gbox_status.setTitle("修改巡检路线")
        self.ui.lab_Note.clear()
        if hasattr(self.ui, "lab_selectedArea"):
            area_item = self.ui.tv_InspectRoute.item(row, 1)
            if area_item is not None:
                self.ui.lab_selectedArea.setText(f"当前区域：{area_item.text()}")
        if hasattr(self.ui, "lab_selectedRoute"):
            self.ui.lab_selectedRoute.setText(f"当前路线：{record.get('RouteName', '')}")
        self.load_inspectPointByAreaId(record.get("AreaId", record.get("AreaID", None)))
        self.load_inspectPointByRouteId(self.routeid)

    # 删除巡检点位
    def on_delete(self) -> None:
        selection = self.ui.tv_InspectRoute.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要删除的巡检路线！")
            return

        reply = QMessageBox.question(self, "确认删除", "确定要删除选中的巡检路线吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        else:
            ins_item = self.ui.tv_InspectRoute.item(self.ui.tv_InspectRoute.currentRow(), 0)
            if ins_item is None:
                return
            self.routeid = int(ins_item.text())
            self.db.execute_query("DELETE FROM InspectRoutePoint WHERE RouteId = %s", (self.routeid,))
            i = self.db.execute_query("DELETE FROM InspectRoute WHERE RouteId = %s", (self.routeid,))
            if (i>0):
                self.ui.lab_Note.setText("巡检路线删除成功！")
                self.clear_input()
                self.load_inspectroute()
            else:
                self.ui.lab_Note.setText("巡检路线删除失败！")

    # 启用巡检点位
    def on_enable(self) -> None:
        selection = self.ui.tv_InspectRoute.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要启用的巡检路线！")
            return
        else:
            ins_item = self.ui.tv_InspectRoute.item(self.ui.tv_InspectRoute.currentRow(), 0)
            if ins_item is None:
                return
            self.routeid = int(ins_item.text())
            i = self.db.execute_query("UPDATE InspectRoute SET Status = 1 WHERE RouteId = %s", (self.routeid,))
            if (i > 0):
                self.ui.lab_Note.setText("巡检路线已启用！")
                self.clear_input()
                self.load_inspectroute()
            else:
                self.ui.lab_Note.setText("巡检路线启用失败！")

    # 禁用巡检点位
    def on_disable(self) -> None:
        selection = self.ui.tv_InspectRoute.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要禁用的巡检点位！")
            return
        else:
            ins_item = self.ui.tv_InspectRoute.item(self.ui.tv_InspectRoute.currentRow(), 0)
            if ins_item is None:
                return
            self.routeid = int(ins_item.text())
            i = self.db.execute_query("UPDATE InspectRoute SET Status = 0 WHERE RouteId = %s", (self.routeid,))
            if (i > 0):
                self.ui.lab_Note.setText("巡检路线已禁用！")
                self.clear_input()
                self.load_inspectroute()
            else:
                self.ui.lab_Note.setText("巡检路线禁用失败！")

    #清空输入框和提示
    def on_clear(self):
        self.clear_input()
        self.ui.lab_Note.text()

    """清空输入框"""
    def clear_input(self) -> None:
        self.ui.tv_InspectRoute.clearSelection()
        self.ui.txt_RouteName.clear()
        self.ui.txt_RouteCode.clear()
        self.ui.txt_PointCount.setValue(0)
        self.ui.txt_PathLength.setValue(0.0)
        self.ui.txt_InsDuration.setValue(0.0)
        self.ui.txt_Remark.clear()
        self.ui.gbox_status.setTitle("新增巡检路线")
        self.routeid = None
        self.ui.lab_Note.setStyleSheet("")
        self.ui.lab_Note.clear()
        self.ui.lab_selectedRoute.setText("当前路线：未选择")
        self.ui.tv_InspectPoint2.setRowCount(0)
        self.on_area_changed(self.ui.txt_AreaId.currentIndex())
        self._clear_route_map()


    def load_inspectPointByAreaId(self, areaid) -> None:
        table = getattr(self.ui, "tv_InspectPoint1", None)
        if table is None:
            return
        table.setRowCount(0)
        if areaid is None:
            return

        recordlist = self.db.fetch_all(
            "SELECT PointId, PointName, Longitude, Latitude FROM InspectPoint WHERE AreaId=%s AND Status=1",
            (areaid,),
        )
        table.setColumnCount(3)
        for row, record in enumerate(recordlist):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(record.get("PointId", ""))))
            table.setItem(row, 1, QTableWidgetItem(str(record.get("PointName", ""))))
            lng_lat = f"{record.get('Longitude', '')},{record.get('Latitude', '')}"
            table.setItem(row, 2, QTableWidgetItem(lng_lat))

    def load_inspectPointByRouteId(self, route_id) -> None:
        table = getattr(self.ui, "tv_InspectPoint2", None)
        if table is None:
            return
        self._loading_route_points = True
        try:
            table.setRowCount(0)
            if route_id is None:
                self._clear_route_map()
                return

            recordlist = self.db.fetch_all(
                """
                SELECT ip.PointId, ip.PointName, ip.Longitude, ip.Latitude,
                       rp.StayTime, rp.InspectAngle, rp.SortNo
                FROM InspectRoutePoint rp
                JOIN InspectPoint ip ON rp.PointId = ip.PointId
                WHERE rp.RouteId = %s
                ORDER BY rp.SortNo
                """,
                (route_id,),
            )
            table.setColumnCount(6)
            for row, record in enumerate(recordlist):
                table.insertRow(row)
                point_id_item = QTableWidgetItem(str(record.get("PointId", "")))
                point_name_item = QTableWidgetItem(str(record.get("PointName", "")))
                lng_lat = f"{record.get('Longitude', '')},{record.get('Latitude', '')}"
                lng_lat_item = QTableWidgetItem(lng_lat)
                stay_item = QTableWidgetItem(str(record.get("StayTime", 10)))
                angle_item = QTableWidgetItem(str(record.get("InspectAngle", 0)))
                sort_item = QTableWidgetItem(str(record.get("SortNo", row + 1)))

                for readonly_item in (point_id_item, point_name_item, lng_lat_item, sort_item):
                    readonly_item.setFlags(readonly_item.flags() & ~Qt.ItemIsEditable)

                table.setItem(row, 0, point_id_item)
                table.setItem(row, 1, point_name_item)
                table.setItem(row, 2, lng_lat_item)
                table.setItem(row, 3, stay_item)
                table.setItem(row, 4, angle_item)
                table.setItem(row, 5, sort_item)
        finally:
            self._loading_route_points = False
        self._refresh_route_map(route_id)

    def _persist_route_point_order(self) -> None:
        if not self.routeid:
            return
        table = self.ui.tv_InspectPoint2
        for row in range(table.rowCount()):
            point_item = table.item(row, 0)
            sort_item = table.item(row, 5)
            if point_item is None:
                continue
            point_id = point_item.text()
            sort_no = row + 1
            if sort_item is not None:
                sort_item.setText(str(sort_no))
            self.db.execute_query(
                "UPDATE InspectRoutePoint SET SortNo=%s WHERE RouteId=%s AND PointId=%s",
                (sort_no, self.routeid, point_id),
            )

        self._refresh_route_metrics_after_relation_change()
        self._refresh_route_map(self.routeid)

    def _refresh_route_metrics_after_relation_change(self) -> None:
        if not self.routeid:
            return
        point_count, path_length, ins_duration = self.calculate_route_metrics(self.routeid)
        self.ui.txt_PointCount.setValue(point_count)
        self.ui.txt_PathLength.setValue(path_length)
        self.ui.txt_InsDuration.setValue(ins_duration)
        self.load_inspectroute()
        self._select_route_by_id(self.routeid)

    def _on_route_points_rows_moved(self, parent, start, end, destination, row) -> None:
        if self._loading_route_points:
            return
        if not self.routeid:
            return
        self._persist_route_point_order()

    def add_point_to_route(self) -> None:
        if not self.routeid:
            QMessageBox.warning(self, "提示", "请先新建并保存路线")
            return
        selected_row = self.ui.tv_InspectPoint1.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "提示", "请选择要添加的点位")
            return

        point_id = self.ui.tv_InspectPoint1.item(selected_row, 0).text()
        exists = self.db.fetch_all(
            "SELECT 1 FROM InspectRoutePoint WHERE RouteId=%s AND PointId=%s",
            (self.routeid, point_id),
        )
        if exists:
            QMessageBox.warning(self, "提示", "该点位已在路线中")
            return

        max_sort = self.db.fetch_all(
            "SELECT IFNULL(MAX(SortNo), 0) AS max_sort FROM InspectRoutePoint WHERE RouteId=%s",
            (self.routeid,),
        )
        sort_no = int(max_sort[0].get("max_sort", 0)) + 1
        self.db.execute_query(
            "INSERT INTO InspectRoutePoint (RouteId, PointId, SortNo, StayTime, InspectAngle) VALUES (%s, %s, %s, 10, 0)",
            (self.routeid, point_id, sort_no),
        )
        self.load_inspectPointByRouteId(self.routeid)

    def adjust_sort_up(self) -> None:
        self.adjust_sort(-1)

    def adjust_sort_down(self) -> None:
        self.adjust_sort(1)

    def adjust_sort(self, step: int) -> None:
        if not self.routeid:
            return
        selected_row = self.ui.tv_InspectPoint2.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "提示", "请选择要调整顺序的点位")
            return

        target_row = selected_row + step
        if target_row < 0 or target_row >= self.ui.tv_InspectPoint2.rowCount():
            return

        curr_point_id = self.ui.tv_InspectPoint2.item(selected_row, 0).text()
        curr_sort = int(self.ui.tv_InspectPoint2.item(selected_row, 5).text())
        target_point_id = self.ui.tv_InspectPoint2.item(target_row, 0).text()
        target_sort = int(self.ui.tv_InspectPoint2.item(target_row, 5).text())

        self.db.execute_query(
            "UPDATE InspectRoutePoint SET SortNo=%s WHERE RouteId=%s AND PointId=%s",
            (target_sort, self.routeid, curr_point_id),
        )
        self.db.execute_query(
            "UPDATE InspectRoutePoint SET SortNo=%s WHERE RouteId=%s AND PointId=%s",
            (curr_sort, self.routeid, target_point_id),
        )
        self.load_inspectPointByRouteId(self.routeid)
        self._refresh_route_metrics_after_relation_change()

    def remove_point_from_route(self) -> None:
        if not self.routeid:
            return
        selected_row = self.ui.tv_InspectPoint2.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "提示", "请选择要移除的点位")
            return

        point_id = self.ui.tv_InspectPoint2.item(selected_row, 0).text()
        ok = QMessageBox.question(
            self, "确认", "确认移除该点位吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return

        self.db.execute_query(
            "DELETE FROM InspectRoutePoint WHERE RouteId=%s AND PointId=%s",
            (self.routeid, point_id),
        )
        rows = self.db.fetch_all(
            "SELECT PointId FROM InspectRoutePoint WHERE RouteId=%s ORDER BY SortNo",
            (self.routeid,),
        )
        for idx, row in enumerate(rows, start=1):
            self.db.execute_query(
                "UPDATE InspectRoutePoint SET SortNo=%s WHERE RouteId=%s AND PointId=%s",
                (idx, self.routeid, row["PointId"]),
            )
        self.load_inspectPointByRouteId(self.routeid)
        self._refresh_route_metrics_after_relation_change()

    def save_relation(self) -> None:
        if not self.routeid:
            QMessageBox.warning(self, "提示", "请先选择路线")
            return

        for row in range(self.ui.tv_InspectPoint2.rowCount()):
            point_item = self.ui.tv_InspectPoint2.item(row, 0)
            if point_item is None or not point_item.text().strip():
                QMessageBox.warning(self, "提示", f"第 {row + 1} 行点位数据为空，请重新拖动后再保存")
                return
            point_id = point_item.text().strip()
            stay_item = self.ui.tv_InspectPoint2.item(row, 3)
            angle_item = self.ui.tv_InspectPoint2.item(row, 4)
            stay_text = stay_item.text() if stay_item is not None else "0"
            angle_text = angle_item.text() if angle_item is not None else "0"
            try:
                stay_time = int(float(stay_text))
                inspect_angle = int(float(angle_text))
            except ValueError:
                QMessageBox.warning(self, "提示", f"第 {row + 1} 行停留时间或角度格式错误")
                return

            self.db.execute_query(
                "UPDATE InspectRoutePoint SET StayTime=%s, InspectAngle=%s, SortNo=%s WHERE RouteId=%s AND PointId=%s",
                (stay_time, inspect_angle, row + 1, self.routeid, point_id),
            )

        point_count, path_length, ins_duration = self.calculate_route_metrics(self.routeid)
        self.ui.txt_PointCount.setValue(point_count)
        self.ui.txt_PathLength.setValue(path_length)
        self.ui.txt_InsDuration.setValue(ins_duration)
        self.load_inspectPointByRouteId(self.routeid)
        self.load_inspectroute()
        QMessageBox.information(self, "完成", "路线点位关系已保存")

    def calculate_distance(self, lng1, lat1, lng2, lat2) -> float:
        radius = 6371000
        lng1_rad = math.radians(float(lng1))
        lat1_rad = math.radians(float(lat1))
        lng2_rad = math.radians(float(lng2))
        lat2_rad = math.radians(float(lat2))

        dlng = lng2_rad - lng1_rad
        dlat = lat2_rad - lat1_rad
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    def calculate_route_metrics(self, route_id: int):
        rows = self.db.fetch_all(
            """
            SELECT rp.PointId, rp.SortNo, rp.StayTime, ip.Longitude, ip.Latitude
            FROM InspectRoutePoint rp
            LEFT JOIN InspectPoint ip ON rp.PointId = ip.PointId
            WHERE rp.RouteId = %s
            ORDER BY rp.SortNo ASC
            """,
            (route_id,),
        )
        point_count = len(rows)

        path_length = 0.0
        for i in range(max(0, point_count - 1)):
            p1 = rows[i]
            p2 = rows[i + 1]
            if p1.get("Longitude") is None or p1.get("Latitude") is None:
                continue
            if p2.get("Longitude") is None or p2.get("Latitude") is None:
                continue
            path_length += self.calculate_distance(p1["Longitude"], p1["Latitude"], p2["Longitude"], p2["Latitude"])

        stay_total = sum(int(r.get("StayTime") or 0) for r in rows)
        move_time = path_length / 0.5 if path_length > 0 else 0
        ins_duration = stay_total + move_time

        self.db.execute_query(
            "UPDATE InspectRoute SET PointCount=%s, PathLength=%s, InsDuration=%s WHERE RouteId=%s",
            (point_count, round(path_length, 2), round(ins_duration, 2), route_id),
        )
        return point_count, round(path_length, 2), round(ins_duration, 2)


if __name__ == "__main__":
    # 运行应用
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    window = BLL_InspectRoute()
    window.show()
    sys.exit(app.exec())

