import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize, QRectF
from PyQt5.QtGui import QColor, QPainterPath, QRegion
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from qfluentwidgets import FluentIcon as FIF, ThemeColor

from modules.task_management.ui.generated.IntelligentObstacleAvoidance import Ui_TaskExecPage


class IntelligentObstacleAvoidancePage(QtWidgets.QWidget, Ui_TaskExecPage):
    def __init__(self, parent=None, embedded: bool = False):
        super().__init__(parent)
        self.setupUi(self)

        self._embedded = embedded
        if parent and embedded:
            self.resize(parent.size())
            self.setMinimumSize(parent.size())

        self._force_active_btn_name = "btnAvoidance"

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
        self.bind_sidebar()
        self.apply_demo_content()
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
        if self._embedded:
            for name in ["btnBack", "btnPin", "btnClose", "labelTitle"]:
                w = getattr(self, name, None)
                if w:
                    w.hide()
            return

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
        if hasattr(self, "btnPin"):
            self.btnPin.setIcon(FIF.FULL_SCREEN.icon(accent))
            self.btnPin.setIconSize(QSize(18, 18))
            self.btnPin.setStyleSheet(btn_style)
            self.btnPin.clicked.connect(self._toggle_maximize)
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
        for name in [
            "frameVideo",
            "frame2D",
            "frameAvoidanceSetting",
            "frameTaskInfo",
        ]:
            frame = getattr(self, name, None)
            if frame:
                self._apply_card_style(frame)

        side = getattr(self, "frameSidebar", None)
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

    def apply_titles(self) -> None:
        title_qss = """
        QLabel {
            color: #5f6b7a;
            font-size: 12px;
            font-weight: 600;
        }
        """
        for name in ["labelTitle", "labelVideoTitle", "label2DTitle", "labelAvoidTitle"]:
            lbl = getattr(self, name, None)
            if lbl:
                lbl.setStyleSheet(title_qss)

        if hasattr(self, "labelTitle"):
            self.labelTitle.setText("\u4efb\u52a1\u6267\u884c\u7ba1\u7406")
        if hasattr(self, "labelVideoTitle"):
            self.labelVideoTitle.setText("\u5b9e\u65f6\u89c6\u9891\u753b\u9762")
        if hasattr(self, "label2DTitle"):
            self.label2DTitle.setText("\u5b9e\u65f62D\u753b\u9762")
        if hasattr(self, "labelAvoidTitle"):
            self.labelAvoidTitle.setText("\u907f\u969c\u8bbe\u7f6e")

        self._setup_task_info_panel()

    def _setup_task_info_panel(self) -> None:
        if hasattr(self, "_task_info_ready") and self._task_info_ready:
            return
        self._task_info_ready = True

        for name in ["labelTaskName", "labelTaskType", "labelTaskDistance", "labelTaskProgress"]:
            w = getattr(self, name, None)
            if w:
                w.hide()

        if not hasattr(self, "taskInfoLayout"):
            return

        self.taskInfoLayout.setSpacing(10)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.lblTaskNameKey = QtWidgets.QLabel("\u4efb\u52a1\u540d\u79f0", self.frameTaskInfo)
        self.lblTaskTypeKey = QtWidgets.QLabel("\u4efb\u52a1\u7c7b\u578b", self.frameTaskInfo)
        self.lblTraveledKey = QtWidgets.QLabel("\u5df2\u884c\u9a76", self.frameTaskInfo)
        self.lblProgressKey = QtWidgets.QLabel("\u5b8c\u6210\u5ea6", self.frameTaskInfo)

        key_style = "color: #7a8796; font-size: 12px;"
        for lbl in [self.lblTaskNameKey, self.lblTaskTypeKey, self.lblTraveledKey, self.lblProgressKey]:
            lbl.setStyleSheet(key_style)

        self.lblTaskNameVal = QtWidgets.QLabel("Avoid-01", self.frameTaskInfo)
        self.lblTaskTypeVal = QtWidgets.QLabel("\u667a\u80fd\u907f\u969c", self.frameTaskInfo)
        self.lblTraveledVal = QtWidgets.QLabel("0.6 km", self.frameTaskInfo)
        self.lblProgressVal = QtWidgets.QLabel("58%", self.frameTaskInfo)

        val_style = "color: #2f3a46; font-size: 12px; border: none;"
        for lbl in [self.lblTaskNameVal, self.lblTaskTypeVal, self.lblTraveledVal]:
            lbl.setStyleSheet(val_style)
        self.lblProgressVal.setStyleSheet("color: #1f2b38; font-size: 14px; font-weight: 700; border: none;")

        grid.addWidget(self.lblTaskNameKey, 0, 0)
        grid.addWidget(self.lblTaskNameVal, 0, 1)
        grid.addWidget(self.lblTaskTypeKey, 1, 0)
        grid.addWidget(self.lblTaskTypeVal, 1, 1)
        grid.addWidget(self.lblTraveledKey, 2, 0)
        grid.addWidget(self.lblTraveledVal, 2, 1)
        grid.addWidget(self.lblProgressKey, 3, 0)
        grid.addWidget(self.lblProgressVal, 3, 1)

        self.taskInfoLayout.addLayout(grid)

        self._progress_bar = QtWidgets.QProgressBar(self.frameTaskInfo)
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
        self.taskInfoLayout.addWidget(self._progress_bar)
        self._set_progress_value("58%")

    def _set_progress_value(self, progress_text: str) -> None:
        if not hasattr(self, "_progress_bar") or not self._progress_bar:
            return
        digits = "".join(ch for ch in progress_text if ch.isdigit())
        try:
            value = int(digits) if digits else 0
        except ValueError:
            value = 0
        self._progress_bar.setValue(max(0, min(100, value)))

    def _icon_label(self, icon: FIF, size: int = 16) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel()
        accent = ThemeColor.PRIMARY.color()
        lbl.setPixmap(icon.icon(accent).pixmap(size, size))
        lbl.setFixedSize(size, size)
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _insert_placeholder(self, layout: QtWidgets.QVBoxLayout, text: str, icon: FIF) -> QtWidgets.QLabel:
        box = QtWidgets.QFrame()
        box.setStyleSheet(
            "QFrame {"
            "background: rgba(255, 255, 255, 90);"
            "border: none;"
            "border-radius: 16px;"
            "}"
        )
        h = QtWidgets.QHBoxLayout(box)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(8)
        h.addWidget(self._icon_label(icon))
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("color: #3b4552; font-size: 12px;")
        h.addWidget(label)
        h.addStretch(1)
        layout.insertWidget(1, box)
        return label

    def apply_placeholders(self) -> None:
        if hasattr(self, "videoLayout") and not hasattr(self, "_video_placeholder"):
            self._video_placeholder = self._insert_placeholder(
                self.videoLayout, "\u907f\u969c\u89c6\u9891\u5360\u4f4d", FIF.CAMERA
            )
        if hasattr(self, "layout2D") and not hasattr(self, "_map2d_placeholder"):
            self._map2d_placeholder = self._insert_placeholder(
                self.layout2D, "\u73af\u5883\u611f\u77e5\u5360\u4f4d", FIF.GLOBE
            )
        if hasattr(self, "avoidLayout") and not hasattr(self, "_setting_placeholder"):
            self._setting_placeholder = self._insert_placeholder(
                self.avoidLayout, "\u907f\u969c\u7b56\u7565\u914d\u7f6e\u5360\u4f4d", FIF.SETTING
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
            "btnFixedPatrol",
            "btnTargetDetect",
            "btnTargetTrack",
            "btnAutoExplore",
            "btnAvoidance",
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

    def set_active_module(self, name: str) -> None:
        target = self._force_active_btn_name or name
        for btn in getattr(self, "_sidebar_btns", []):
            btn.setStyleSheet(self._side_active_qss if btn.objectName() == target else self._side_default_qss)

    def apply_demo_content(self) -> None:
        self.lblTaskNameVal.setText("Avoid-01")
        self.lblTaskTypeVal.setText("\u667a\u80fd\u907f\u969c")
        self.lblTraveledVal.setText("0.6 km")
        self.lblProgressVal.setText("58%")
        self._set_progress_value("58%")

    def _apply_embedded_layout(self) -> None:
        if hasattr(self, "frameSidebar"):
            self.frameSidebar.hide()
        if hasattr(self, "rootLayout"):
            self.rootLayout.setContentsMargins(0, 0, 0, 0)
            self.rootLayout.setSpacing(0)
        if hasattr(self, "mainLayout"):
            self.mainLayout.setContentsMargins(0, 0, 0, 0)
            self.mainLayout.setSpacing(0)
        if hasattr(self, "contentRootLayout"):
            self.contentRootLayout.setContentsMargins(0, 0, 0, 0)
            self.contentRootLayout.setSpacing(14)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        radius = 16
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = IntelligentObstacleAvoidancePage()
    w.resize(1100, 720)
    w.show()
    sys.exit(app.exec_())

