import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QCoreApplication, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QDialog, QAbstractItemView, QTableWidgetItem, QMessageBox, QHeaderView, \
    QWidget, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect, QStyle
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF, PushButton

from MICCProject1.ui.Frm_InspectArea import Ui_Frm_InspectArea  # 导入自动生成的界面类
from MICCProject1.scripts.DBHelper import DBHelper


class BLL_InspectArea(QDialog):
    def __init__(self, registration_mode: bool = False, on_next=None, on_close=None, on_jump=None):
        super().__init__()
        self.ui = Ui_Frm_InspectArea()
        self.ui.setupUi(self)
        self.db = DBHelper()
        self._on_next = on_next
        self._on_close = on_close
        self._on_jump = on_jump
        self._active_step = 0
        self.areaid = None
        self.init_ui()
        self.load_inspectarea() #加载地区信息
        self._init_nav()
        #self.setFixedSize(1639, 636)

    def _init_nav(self) -> None:
        self._nav_bar = QWidget(self)
        self._nav_bar.setObjectName("navBar")
        self._nav_bar.setFixedHeight(36)
        layout = QHBoxLayout(self._nav_bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._step_bar = self._build_step_bar(active_index=0)
        self._btn_next = TransparentToolButton(FIF.RIGHT_ARROW)
        self._btn_close = TransparentToolButton(FIF.CLOSE)
        self._btn_next.setToolTip("下一步")
        self._btn_close.setToolTip("关闭")
        for btn in (self._btn_next, self._btn_close):
            btn.setFixedSize(28, 28)
            btn.setIconSize(btn.iconSize())
        self._btn_next.clicked.connect(self._on_nav_next)
        self._btn_close.clicked.connect(self._on_nav_close)

        layout.addWidget(self._step_bar, 1)
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

    def _on_nav_next(self) -> None:
        if callable(self._on_next):
            self.close()
            self._on_next()

    def _on_nav_close(self) -> None:
        if callable(self._on_close):
            self._on_close()
        else:
            self.close()

    def init_ui(self) -> None:
        self.setMinimumSize(980, 620)
        self._apply_window_icon()
        self._apply_form_style()
        self._replace_top_controls()
        self._apply_responsive_layout()
        self.ui.btn_Save.clicked.connect(self.on_save)
        self.ui.btn_Clear.clicked.connect(self.on_clear)
        self.ui.btn_Delete.clicked.connect(self.on_delete)
        self.ui.btn_Enable.clicked.connect(self.on_enable)
        self.ui.btn_Disable.clicked.connect(self.on_disable)
        self.ui.tv_InspectArea.clicked.connect(self.on_select)

    def load_inspectarea(self) -> None:

        self.ui.tv_InspectArea.setRowCount(0)
        recordlist = self.db.fetch_all("select * from InspectArea")
        for row, record in enumerate(recordlist):
            self.ui.tv_InspectArea.insertRow(row)
            self.ui.tv_InspectArea.setItem(row, 0, QTableWidgetItem(str(record.get("AreaId", ""))))  # 机构ID
            self.ui.tv_InspectArea.setItem(row, 1, QTableWidgetItem(str(record.get("AreaName", ""))))  #机构名称
            self.ui.tv_InspectArea.setItem(row, 2, QTableWidgetItem(str(record.get("AreaCode", ""))))   #机构简称
            self.ui.tv_InspectArea.setItem(row, 3,  QTableWidgetItem(str(record.get("AreaDesc",""))))  #地区名称
            self.ui.tv_InspectArea.setItem(row, 4, QTableWidgetItem(str(record.get("Status",""))))  #机构类型
            self.ui.tv_InspectArea.setItem(row, 5, QTableWidgetItem(str(record.get("Remark","")))) #办学层次
        self.setup_table_view()


    def validate_required(self) -> bool:
        # 定义必填字段（控件变量 -> 字段名称）
        required = {
            self.ui.txt_AreaName: "区域名称",
            self.ui.txt_AreaCode: "区域编码"
        }
        for var, field_name in required.items():
            if not var.text().strip():
                self.ui.lab_Note.setText(f"{field_name}为必填项，请填写完整！")
                self.ui.lab_Note.setStyleSheet("color: red;")
                return False
        return True

    def setup_table_view(self) -> None:
        """Tune table appearance for better readability."""
        header = self.ui.tv_InspectArea.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.ui.tv_InspectArea.setAlternatingRowColors(True)
        self.ui.tv_InspectArea.setShowGrid(True)
        self.ui.tv_InspectArea.setStyleSheet(
            "QTableView {gridline-color: #d0d0d0; alternate-background-color: #f8f8f8;}"
        )

    def _apply_form_style(self) -> None:
        self.setStyleSheet(
            "QDialog {"
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
            "QLineEdit, QTextEdit, QComboBox {"
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
        if hasattr(self.ui, "btn_Save"):
            self.ui.btn_Save.setMinimumWidth(90)
        if hasattr(self.ui, "btn_Clear"):
            self.ui.btn_Clear.setMinimumWidth(90)

    def _dock_nav_bar(self) -> bool:
        host = getattr(self.ui, "groupBox_2", None)
        table = getattr(self.ui, "tv_InspectArea", None)
        if host is None or table is None:
            return False

        row_widget = getattr(self.ui, "layoutWidget1", None)
        nav = self._nav_bar
        nav.setParent(host)
        nav.adjustSize()

        nav_y = 6
        nav_x = 8
        if row_widget is not None:
            row_h = row_widget.height()
            row_w = min(max(240, row_widget.width()), max(240, host.width() - 20))
            row_x = max(8, host.width() - row_w - 8)
            row_widget.setGeometry(row_x, 6, row_w, row_h)
            row_rect = row_widget.geometry()
            nav_y = row_rect.y() + row_rect.height() + 4

        nav.resize(host.width() - 16, nav.height())
        nav.move(max(6, nav_x), max(0, nav_y))

        min_table_y = nav.y() + nav.height() + 8
        new_y = max(40, min_table_y)
        new_h = max(120, host.height() - new_y - 10)
        new_w = max(280, host.width() - 20)
        table.setGeometry(10, new_y, new_w, new_h)
        return True

    def _apply_responsive_layout(self) -> None:
        if not hasattr(self.ui, "gbox_status") or not hasattr(self.ui, "groupBox_2"):
            return

        margin = 10
        top = 20
        gap = 10
        bottom = 10
        window_w = max(self.width(), self.minimumWidth())
        window_h = max(self.height(), self.minimumHeight())

        usable_w = max(760, window_w - margin * 2 - gap)
        left_w = min(460, max(360, int(usable_w * 0.38)))
        right_w = max(340, usable_w - left_w)
        content_h = max(420, window_h - top - bottom)

        self.ui.gbox_status.setGeometry(margin, top, left_w, content_h)
        self.ui.groupBox_2.setGeometry(margin + left_w + gap, top, right_w, content_h)

        field_x = 110
        field_w = max(220, left_w - field_x - 18)
        star_x = max(350, left_w - 26)
        self.ui.txt_AreaName.setGeometry(field_x, 40, field_w, 30)
        self.ui.txt_AreaCode.setGeometry(field_x, 90, field_w, 30)
        self.ui.txt_AreaDesc.setGeometry(field_x, 140, field_w, 100)
        self.ui.txt_Remark.setGeometry(field_x, 250, field_w, 100)
        self.ui.label_13.setGeometry(star_x, 50, 16, 16)
        self.ui.label_14.setGeometry(star_x, 100, 16, 16)

        row_w = min(320, max(240, left_w - 100))
        row_x = max(20, int((left_w - row_w) / 2))
        self.ui.layoutWidget.setGeometry(row_x, max(370, content_h - 170), row_w, 45)
        self.ui.lab_Note.setGeometry(20, content_h - 70, max(180, left_w - 40), 24)

    def _replace_top_controls(self) -> None:
        host = getattr(self.ui, "layoutWidget1", None)
        layout = host.layout() if host is not None else None
        if layout is None:
            return

        # Hide native buttons and clear layout
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
        """Handle create or update operations for a user."""
        if not self.validate_required():
            return
        else:
            areaName = self.ui.txt_AreaName.text().strip()
            areaCode = self.ui.txt_AreaCode.text().strip()
            areaDesc = self.ui.txt_AreaDesc.text().strip()
            remark = self.ui.txt_Remark.text().strip()

            try:
                # 如果是添加用户，则要检测用户名
                if self.areaid:
                    query = """
                    UPDATE InspectArea
                    SET AreaName = %s, AreaCode = %s, AreaDesc = %s, Remark = %s
                    WHERE AreaId = %s
                    """
                    params = (areaName, areaCode, areaDesc, remark, self.areaid)
                    i = self.db.execute_query(query, params)
                    if (i>0):
                        self.ui.lab_Note.setText("巡检区域信息修改成功！")
                        self.clear_input()
                        self.load_inspectarea()
                    else:
                        self.ui.lab_Note.setText("巡检区域信息修改失败！" )
                else:
                    query = """
                        INSERT INTO InspectArea (AreaName, AreaCode, AreaDesc,  Remark, Status)
                        VALUES (%s, %s, %s, %s, 1)
                        """
                    params = (areaName, areaCode, areaDesc, remark)
                    i = self.db.execute_query(query, params)
                    if (i>0):
                        self.ui.lab_Note.setText("巡检区域信息添加成功！" )
                        self.clear_input()
                        self.load_inspectarea()
                    else:
                        self.ui.lab_Note.setText("巡检区域信息添加失败！" )
            except Exception as exc:
                self.ui.lab_Note.setText("巡检区域信息保存失败！"+str(exc))
                return

    # 选中某一项巡检区域数据
    def on_select(self, index) -> None:
        item = self.ui.tv_InspectArea.item(index.row(), 0)
        if item is None:
            return
        self.areaid = int(item.text())
        records = self.db.fetch_all("SELECT * FROM InspectArea WHERE AreaId = %s", (self.areaid,))
        if not records:
            return
        record = records[0]
        self.ui.txt_AreaName.setText(record.get("AreaName", ""))
        self.ui.txt_AreaCode.setText(record.get("AreaCode", ""))
        self.ui.txt_AreaDesc.setText(record.get("AreaDesc", ""))
        self.ui.txt_Remark.setText(record.get("Remark", ""))
        self.ui.gbox_status.setTitle("修改巡检区域")
        self.ui.lab_Note.clear()

    # 删除巡检区域
    def on_delete(self) -> None:
        selection = self.ui.tv_InspectArea.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要删除的巡检区域！")
            return

        reply = QMessageBox.question(self, "确认删除", "确定要删除选中的巡检区域吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        else:
            ins_item = self.ui.tv_InspectArea.item(self.ui.tv_InspectArea.currentRow(), 0)
            if ins_item is None:
                return
            self.areaid = int(ins_item.text())
            i = self.db.execute_query("DELETE FROM InspectArea WHERE AreaId = %s", (self.areaid,))
            if (i>0):
                self.ui.lab_Note.setText("巡检区域删除成功！")
                self.clear_input()
                self.load_inspectarea()
            else:
                self.ui.lab_Note.setText("巡检区域删除失败！")

    # 启用巡检区域
    def on_enable(self) -> None:
        selection = self.ui.tv_InspectArea.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要启用的巡检区域！")
            return
        else:
            ins_item = self.ui.tv_InspectArea.item(self.ui.tv_InspectArea.currentRow(), 0)
            if ins_item is None:
                return
            self.areaid = int(ins_item.text())
            i = self.db.execute_query("UPDATE InspectArea SET Status = 1 WHERE AreaId = %s", (self.areaid,))
            if (i > 0):
                self.ui.lab_Note.setText("巡检区域已启用！")
                self.clear_input()
                self.load_inspectarea()
            else:
                self.ui.lab_Note.setText("巡检区域启用失败！")

    # 禁用巡检区域
    def on_disable(self) -> None:
        selection = self.ui.tv_InspectArea.selectedItems()
        if not selection:
            QMessageBox.warning(self, "操作提示", "请先选中要禁用的巡检区域！")
            return
        else:
            ins_item = self.ui.tv_InspectArea.item(self.ui.tv_InspectArea.currentRow(), 0)
            if ins_item is None:
                return
            self.areaid = int(ins_item.text())
            i = self.db.execute_query("UPDATE InspectArea SET Status = 0 WHERE AreaId = %s", (self.areaid,))
            if (i > 0):
                self.ui.lab_Note.setText("巡检区域已禁用！")
                self.clear_input()
                self.load_inspectarea()
            else:
                self.ui.lab_Note.setText("巡检区域禁用失败！")

    #清空输入框和提示
    def on_clear(self):
        self.clear_input()
        self.ui.lab_Note.clear()

    """清空输入框"""
    def clear_input(self) -> None:
        self.ui.txt_AreaName.clear()
        self.ui.txt_AreaCode.clear()
        self.ui.txt_AreaDesc.clear()
        self.ui.txt_Remark.clear()
        self.ui.gbox_status.setTitle("新增巡检区域")
        self.areaid = None

if __name__ == "__main__":
    # 运行应用
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    window = BLL_InspectArea()
    window.show()
    sys.exit(app.exec())

