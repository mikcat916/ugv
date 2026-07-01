import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize, QRectF, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPainterPath, QRegion
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from qfluentwidgets import FluentIcon as FIF, ThemeColor

from modules.task_management.ui.generated.Taskmanagement import Ui_TaskExecPage
from modules.task_management.pages.hover_cruise_page import HoverCruisePage


class TaskManagementPage(QtWidgets.QWidget, Ui_TaskExecPage):
    def __init__(self, parent=None, embedded: bool = False):
        super().__init__(parent)
        self.setupUi(self)

        self._embedded = embedded
        if parent and embedded:
            self.resize(parent.size())
            self.setMinimumSize(parent.size())

        self._force_active_btn_name = "btnMapBuild"

        if not embedded:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        self.apply_background()
        self.apply_topbar()
        self.apply_cards()
        self.apply_titles()
        self.apply_placeholders()
        self.apply_controls()
        self.apply_demo_content()
        self.bind_sidebar()
        self.set_active_module(self._force_active_btn_name)
        if embedded:
            self._apply_embedded_layout()

    def apply_background(self) -> None:
        qss = """
        QWidget#TaskExecPage {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #f3f8ff,
                stop:0.5 #f6f7fb,
                stop:1 #f1f1f1
            );
            border: 1px solid rgba(0, 0, 0, 18);
            border-radius: 16px;
        }
        QWidget {
            border: none;
        }
        """
        self.setStyleSheet(self.styleSheet() + "\n" + qss)
        if self._embedded:
            self.setStyleSheet(self.styleSheet() + "\n" + "QWidget#TaskExecPage { border: none; }")

    def apply_topbar(self) -> None:
        accent = ThemeColor.PRIMARY.color()
        btn_style = (
            "QToolButton {"
            "border-radius: 8px;"
            "border: 1px solid rgba(0, 0, 0, 20);"
            "background-color: rgba(255, 255, 255, 180);"
            "}"
            "QToolButton:hover {"
            "border: 1px solid rgba(0, 0, 0, 40);"
            "background-color: rgba(255, 255, 255, 210);"
            "}"
        )

        if hasattr(self, "btnBack"):
            self.btnBack.setIcon(FIF.LEFT_ARROW.icon(accent))
            self.btnBack.setIconSize(QSize(18, 18))
            self.btnBack.setStyleSheet(btn_style)
            self.btnBack.clicked.connect(self.close)

        if hasattr(self, "btnMaximize"):
            self.btnMaximize.setIcon(FIF.FULL_SCREEN.icon(accent))
            self.btnMaximize.setIconSize(QSize(18, 18))
            self.btnMaximize.setStyleSheet(btn_style)
            self.btnMaximize.clicked.connect(self._toggle_maximize)

        if hasattr(self, "btnClose"):
            self.btnClose.setIcon(FIF.CLOSE.icon(accent))
            self.btnClose.setIconSize(QSize(18, 18))
            self.btnClose.setStyleSheet(btn_style)
            self.btnClose.clicked.connect(self.close)

    def _toggle_maximize(self) -> None:
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def _apply_card_style(self, widget) -> None:
        widget.setStyleSheet(
            "QFrame {"
            "background: rgba(255, 255, 255, 185);"
            "border: none;"
            "border-radius: 18px;"
            "}"
        )
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 40))
        widget.setGraphicsEffect(shadow)

    def apply_cards(self) -> None:
        for name in ["frameMap", "frameTaskDetail", "frameVideo", "frameRadar", "frameControls"]:
            frame = getattr(self, name, None)
            if frame:
                self._apply_card_style(frame)

        side = getattr(self, "sideBar", None)
        if side:
            side.setStyleSheet(
                "QFrame {"
                "background: rgba(255, 255, 255, 150);"
                "border: none;"
                "border-radius: 16px;"
                "}"
            )
            shadow = QGraphicsDropShadowEffect(side)
            shadow.setBlurRadius(26)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 40))
            side.setGraphicsEffect(shadow)

        title_bar = getattr(self, "titleBar", None)
        if title_bar:
            title_bar.setStyleSheet(
                "QFrame {"
                "background: rgba(255, 255, 255, 160);"
                "border: none;"
                "border-radius: 12px;"
                "}"
            )

    def apply_titles(self) -> None:
        title_qss = """
        QLabel {
            color: #5f6b7a;
            font-size: 12px;
            font-weight: 600;
        }
        """
        for name in [
            "lblTitle",
            "lblMapTitle",
            "lblTaskDetailTitle",
            "lblVideoTitle",
            "lblRadarTitle",
        ]:
            lbl = getattr(self, name, None)
            if lbl:
                lbl.setStyleSheet(title_qss)

        for name in ["lblMapRangeKey", "lblMapAreaKey", "lblProgressKey"]:
            lbl = getattr(self, name, None)
            if lbl:
                lbl.setStyleSheet("color: #8a96a6; font-size: 12px;")

        if hasattr(self, "lblTitle"):
            self.lblTitle.setText("\u4efb\u52a1\u6267\u884c\u7ba1\u7406")
        if hasattr(self, "lblMapTitle"):
            self.lblMapTitle.setText("\u5b9e\u65f6\u663e\u793a\u5730\u56fe")
        if hasattr(self, "lblTaskDetailTitle"):
            self.lblTaskDetailTitle.setText("\u4efb\u52a1\u8be6\u60c5")
        if hasattr(self, "lblVideoTitle"):
            self.lblVideoTitle.setText("\u5b9e\u65f6\u89c6\u9891\u753b\u9762")
        if hasattr(self, "lblRadarTitle"):
            self.lblRadarTitle.setText("\u5b9e\u65f6\u96f7\u8fbe\u753b\u9762")
        if hasattr(self, "lblMapRangeKey"):
            self.lblMapRangeKey.setText("\u5730\u56fe\u8303\u56f4")
        if hasattr(self, "lblMapAreaKey"):
            self.lblMapAreaKey.setText("\u5730\u56fe\u9762\u79ef")
        if hasattr(self, "lblProgressKey"):
            self.lblProgressKey.setText("\u5b8c\u6210\u5ea6")
        if hasattr(self, "taskForm"):
            self.taskForm.setVerticalSpacing(8)
            self.taskForm.setHorizontalSpacing(12)
        if hasattr(self, "taskFormLayout"):
            self.taskFormLayout.setVerticalSpacing(8)
            self.taskFormLayout.setHorizontalSpacing(12)
        self._ensure_progress_bar()

    def _ensure_progress_bar(self) -> None:
        if hasattr(self, "_progress_bar") and self._progress_bar:
            return
        if not hasattr(self, "taskDetailLayout"):
            return
        self._progress_bar = QtWidgets.QProgressBar(self)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            "QProgressBar {"
            "background: rgba(120, 140, 160, 30);"
            "border: none;"
            "border-radius: 4px;"
            "}"
            "QProgressBar::chunk {"
            "background: #3fa9f5;"
            "border-radius: 4px;"
            "}"
        )
        self.taskDetailLayout.addWidget(self._progress_bar)

    def _set_progress_value(self, progress_text: str) -> None:
        if not hasattr(self, "_progress_bar") or not self._progress_bar:
            return
        digits = "".join(ch for ch in progress_text if ch.isdigit())
        try:
            value = int(digits) if digits else 0
        except ValueError:
            value = 0
        self._progress_bar.setValue(max(0, min(100, value)))

    def apply_placeholders(self) -> None:
        for name in ["lblMapPlaceholder", "lblVideoPlaceholder", "lblRadarPlaceholder"]:
            w = getattr(self, name, None)
            if w:
                w.setStyleSheet(
                    "background: rgba(255, 255, 255, 90);"
                    "border: none;"
                    "border-radius: 16px;"
                    "padding: 8px;"
                )

    def apply_controls(self) -> None:
        accent = ThemeColor.PRIMARY.color()
        r, g, b, _ = accent.getRgb()
        btn_qss = """
        QPushButton {
            border-radius: 10px;
            border: 1px solid rgba(%d, %d, %d, 90);
            background-color: rgba(255, 255, 255, 210);
            padding: 6px 14px;
        }
        QPushButton:hover {
            border: 1px solid rgba(%d, %d, %d, 160);
            background-color: rgba(%d, %d, %d, 26);
        }
        QPushButton:pressed {
            background-color: rgba(%d, %d, %d, 40);
            padding-top: 7px;
        }
        """ % (r, g, b, r, g, b, r, g, b, r, g, b)

        for name in ["btnStart", "btnPause"]:
            btn = getattr(self, name, None)
            if btn:
                btn.setStyleSheet(btn_qss)
                shadow = QGraphicsDropShadowEffect(btn)
                shadow.setBlurRadius(18)
                shadow.setOffset(0, 4)
                shadow.setColor(QColor(0, 0, 0, 35))
                btn.setGraphicsEffect(shadow)

        if hasattr(self, "btnEStop"):
            self.btnEStop.setStyleSheet(
                "QPushButton {"
                "border-radius: 12px;"
                "border: 1px solid rgba(255, 120, 120, 160);"
                "background-color: rgba(255, 235, 235, 220);"
                "color: #d14c4c;"
                "font-weight: 600;"
                "}"
                "QPushButton:hover {"
                "border: 1px solid rgba(255, 90, 90, 200);"
                "background-color: rgba(255, 220, 220, 240);"
                "}"
                "QPushButton:pressed {"
                "background-color: rgba(255, 205, 205, 255);"
                "padding-top: 7px;"
                "}"
            )
            shadow = QGraphicsDropShadowEffect(self.btnEStop)
            shadow.setBlurRadius(22)
            shadow.setOffset(0, 5)
            shadow.setColor(QColor(0, 0, 0, 40))
            self.btnEStop.setGraphicsEffect(shadow)

        sidebar_btns = [
            "btnMapBuild",
            "btnPatrol",
            "btnDetect",
            "btnTrack",
            "btnExplore",
            "btnAvoid",
            "btnAirGround",
            "btnHumanMachine",
        ]
        side_qss = """
        QPushButton {
            border-radius: 10px;
            border: 1px solid rgba(0, 0, 0, 10);
            background-color: rgba(255, 255, 255, 200);
            padding: 6px 10px;
            color: #3b4552;
            font-size: 12px;
        }
        QPushButton:hover {
            border: 1px solid rgba(%d, %d, %d, 140);
            background-color: rgba(%d, %d, %d, 26);
        }
        QPushButton:pressed {
            background-color: rgba(%d, %d, %d, 40);
            padding-top: 7px;
        }
        """ % (r, g, b, r, g, b, r, g, b)

        for name in sidebar_btns:
            btn = getattr(self, name, None)
            if btn:
                btn.setStyleSheet(side_qss)

        self._sidebar_btns = [getattr(self, n, None) for n in sidebar_btns if getattr(self, n, None)]
        for btn in self._sidebar_btns:
            btn.setMinimumSize(0, 48)
            btn.setMaximumHeight(48)
            btn.setStyleSheet(side_qss)

        self._side_active_qss = """
        QPushButton {
            border-radius: 10px;
            border: 1px solid rgba(%d, %d, %d, 160);
            background-color: rgba(%d, %d, %d, 26);
            color: #2f3a46;
            font-size: 12px;
            font-weight: 600;
        }
        """ % (r, g, b, r, g, b)

        self._side_default_qss = side_qss

    def bind_sidebar(self) -> None:
        if not hasattr(self, "_sidebar_btns"):
            return
        for btn in self._sidebar_btns:
            btn.clicked.connect(lambda _, b=btn: self.set_active_module(b.objectName()))

        if not self._embedded:
            btn_patrol = getattr(self, "btnPatrol", None)
            if btn_patrol:
                btn_patrol.clicked.connect(self.open_hover_cruise)

        if not self._embedded:
            btn_map = getattr(self, "btnMapBuild", None)
            if btn_map:
                btn_map.clicked.connect(self.open_map_build)

    def set_active_module(self, name: str) -> None:
        target = self._force_active_btn_name or name
        for btn in getattr(self, "_sidebar_btns", []):
            if btn.objectName() == target:
                btn.setStyleSheet(self._side_active_qss)
            else:
                btn.setStyleSheet(self._side_default_qss)

        # Blend the active module with the right content area.
        accent = ThemeColor.PRIMARY.color()
        r, g, b, _ = accent.getRgb()
        active_qss = (
            "QFrame {"
            "background: rgba(255, 255, 255, 200);"
            "border: none;"
            "border-radius: 18px;"
            "}"
        )
        for frame_name in ["frameMap", "frameTaskDetail"]:
            frame = getattr(self, frame_name, None)
            if frame:
                frame.setStyleSheet(active_qss)

    def open_hover_cruise(self) -> None:
        if not hasattr(self, "_hover_cruise_page") or self._hover_cruise_page is None:
            self._hover_cruise_page = HoverCruisePage(self)
            self._hover_cruise_page.resize(self.size())
            self._hover_cruise_page.setMinimumSize(self.size())
        self._switch_to(self._hover_cruise_page, "btnPatrol")

    def open_map_build(self) -> None:
        # Ensure we stay on the main TaskManagement page.
        if hasattr(self, "_hover_cruise_page") and self._hover_cruise_page:
            self._switch_to(self, "btnMapBuild", hide_from=self._hover_cruise_page)
        else:
            self.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_hover_cruise_page") and self._hover_cruise_page:
            if self._hover_cruise_page.isVisible():
                self._hover_cruise_page.resize(self.size())
        if self._embedded and self.parent() and self.size() != self.parent().size():
            self.resize(self.parent().size())

    def _apply_embedded_layout(self) -> None:
        # Hide shell elements; keep only mainArea content.
        if hasattr(self, "titleBar"):
            self.titleBar.hide()
        if hasattr(self, "sideBar"):
            self.sideBar.hide()
        if hasattr(self, "rootLayout"):
            self.rootLayout.setContentsMargins(0, 0, 0, 0)
            self.rootLayout.setSpacing(0)
        if hasattr(self, "bodyLayout"):
            self.bodyLayout.setContentsMargins(0, 0, 0, 0)
            self.bodyLayout.setSpacing(0)

    def _switch_to(self, target, active_btn: str, hide_from=None) -> None:
        if hide_from is None:
            hide_from = self
        self.set_active_module(active_btn)
        self._fade_out_in(hide_from, target)

    def _fade_out_in(self, from_widget, to_widget) -> None:
        for w in (from_widget, to_widget):
            if w.graphicsEffect() is None or not isinstance(w.graphicsEffect(), QGraphicsOpacityEffect):
                w.setGraphicsEffect(QGraphicsOpacityEffect(w))

        out_eff = from_widget.graphicsEffect()
        in_eff = to_widget.graphicsEffect()

        out_anim = QPropertyAnimation(out_eff, b"opacity", from_widget)
        out_anim.setDuration(180)
        out_anim.setStartValue(1.0)
        out_anim.setEndValue(0.0)
        out_anim.setEasingCurve(QEasingCurve.OutCubic)

        in_anim = QPropertyAnimation(in_eff, b"opacity", to_widget)
        in_anim.setDuration(220)
        in_anim.setStartValue(0.0)
        in_anim.setEndValue(1.0)
        in_anim.setEasingCurve(QEasingCurve.OutCubic)

        def _after_out():
            from_widget.hide()
            to_widget.show()
            in_anim.start()

        out_anim.finished.connect(_after_out)
        out_anim.start()
        self._fade_out_anim = out_anim
        self._fade_in_anim = in_anim

    def _icon_label(self, icon: FIF, size: int = 16) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel()
        accent = ThemeColor.PRIMARY.color()
        lbl.setPixmap(icon.icon(accent).pixmap(size, size))
        lbl.setFixedSize(size, size)
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _replace_placeholder(self, placeholder: QtWidgets.QLabel, icon: FIF, text: str) -> QtWidgets.QLabel:
        parent_layout = placeholder.parentWidget().layout()
        index = parent_layout.indexOf(placeholder)
        placeholder.setVisible(False)

        box = QtWidgets.QFrame(placeholder.parentWidget())
        box.setStyleSheet(
            "QFrame {"
            "background: rgba(255, 255, 255, 90);"
            "border: none;"
            "border-radius: 16px;"
            "}"
        )
        layout = QtWidgets.QHBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(self._icon_label(icon))
        text_label = QtWidgets.QLabel(text)
        text_label.setStyleSheet("color: #3b4552; font-size: 12px;")
        layout.addWidget(text_label)
        layout.addStretch(1)

        parent_layout.insertWidget(index, box)
        return text_label

    def apply_demo_content(self) -> None:
        self.set_map_preview("Route preview - 6 waypoints")
        self.set_video_preview("Camera feed placeholder")
        self.set_radar_preview("Radar scan placeholder")
        self.set_task_info(
            range_text="2.4 km",
            area_text="1.2 km^2",
            progress_text="68%",
        )
    def set_map_preview(self, text: str) -> None:
        placeholder = getattr(self, "lblMapPlaceholder", None)
        if not placeholder:
            return
        if not hasattr(self, "_map_preview_label"):
            self._map_preview_label = self._replace_placeholder(placeholder, FIF.GLOBE, text)
        else:
            self._map_preview_label.setText(text)

    def set_video_preview(self, text: str) -> None:
        placeholder = getattr(self, "lblVideoPlaceholder", None)
        if not placeholder:
            return
        if not hasattr(self, "_video_preview_label"):
            self._video_preview_label = self._replace_placeholder(placeholder, FIF.CAMERA, text)
        else:
            self._video_preview_label.setText(text)

    def set_radar_preview(self, text: str) -> None:
        placeholder = getattr(self, "lblRadarPlaceholder", None)
        if not placeholder:
            return
        if not hasattr(self, "_radar_preview_label"):
            self._radar_preview_label = self._replace_placeholder(placeholder, FIF.PROJECTOR, text)
        else:
            self._radar_preview_label.setText(text)

    def set_task_info(self, range_text: str, area_text: str, progress_text: str) -> None:
        if hasattr(self, "lblMapRangeVal"):
            self.lblMapRangeVal.setText(range_text)
            self.lblMapRangeVal.setStyleSheet("color: #2f3a46; font-size: 12px; border: none;")
        if hasattr(self, "lblMapAreaVal"):
            self.lblMapAreaVal.setText(area_text)
            self.lblMapAreaVal.setStyleSheet("color: #2f3a46; font-size: 12px; border: none;")
        if hasattr(self, "lblProgressVal"):
            self.lblProgressVal.setText(progress_text)
            self.lblProgressVal.setStyleSheet("color: #1f2b38; font-size: 14px; font-weight: 700; border: none;")
            self._set_progress_value(progress_text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        radius = 16
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = TaskManagementPage()
    w.resize(980, 680)
    w.show()
    sys.exit(app.exec_())

