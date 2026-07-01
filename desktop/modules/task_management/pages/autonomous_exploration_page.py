import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize, QRectF
from PyQt5.QtGui import QColor, QPainterPath, QRegion
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from qfluentwidgets import FluentIcon as FIF, ThemeColor

from modules.task_management.ui.generated.Autonomousexploration import Ui_Form


class AutonomousExplorationPage(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None, embedded: bool = False):
        super().__init__(parent)
        self.setupUi(self)

        self._embedded = embedded
        if parent and embedded:
            self.resize(parent.size())
            self.setMinimumSize(parent.size())

        self._force_active_btn_name = "btnExplore"

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
        QWidget#Form {
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
            self.setStyleSheet(self.styleSheet() + "\n" + "QWidget#Form { border: none; }")

    def apply_topbar(self) -> None:
        if self._embedded:
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
        if hasattr(self, "btnMax"):
            self.btnMax.setIcon(FIF.FULL_SCREEN.icon(accent))
            self.btnMax.setIconSize(QSize(18, 18))
            self.btnMax.setStyleSheet(btn_style)
            self.btnMax.clicked.connect(self._toggle_maximize)
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
        for name in ["cardMap2D", "cardVideo", "cardTaskDetail", "cardControl"]:
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
        for name in ["lblTitle", "lblMap2DTitle", "lblVideoTitle"]:
            lbl = getattr(self, name, None)
            if lbl:
                lbl.setStyleSheet(title_qss)

        for name in ["lblTaskNameKey", "lblTaskTypeKey", "lblTraveledKey", "lblProgressKey"]:
            lbl = getattr(self, name, None)
            if lbl:
                lbl.setStyleSheet("color: #7a8796; font-size: 12px;")

        if hasattr(self, "lblTitle"):
            self.lblTitle.setText("\u4efb\u52a1\u6267\u884c\u7ba1\u7406")
        if hasattr(self, "lblMap2DTitle"):
            self.lblMap2DTitle.setText("\u5b9e\u65f6\u663e\u793a\u5730\u56fe(2D)")
        if hasattr(self, "lblVideoTitle"):
            self.lblVideoTitle.setText("\u5b9e\u65f6\u89c6\u9891\u753b\u9762")
        if hasattr(self, "lblTaskNameKey"):
            self.lblTaskNameKey.setText("\u4efb\u52a1\u540d\u79f0")
        if hasattr(self, "lblTaskTypeKey"):
            self.lblTaskTypeKey.setText("\u4efb\u52a1\u7c7b\u578b")
        if hasattr(self, "lblTraveledKey"):
            self.lblTraveledKey.setText("\u5df2\u884c\u9a76")
        if hasattr(self, "lblProgressKey"):
            self.lblProgressKey.setText("\u4efb\u52a1\u5b8c\u6210\u5ea6")
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
        for name in ["map2DPlaceholder", "videoPlaceholder"]:
            w = getattr(self, name, None)
            if w:
                w.setStyleSheet(
                    "background: rgba(255, 255, 255, 90);"
                    "border: none;"
                    "border-radius: 16px;"
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
            "btnPointPatrol",
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

        self._sidebar_btns = []
        for name in sidebar_btns:
            btn = getattr(self, name, None)
            if btn:
                btn.setStyleSheet(side_qss)
                btn.setMinimumSize(0, 48)
                btn.setMaximumHeight(48)
                self._sidebar_btns.append(btn)

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
        for btn in getattr(self, "_sidebar_btns", []):
            btn.clicked.connect(lambda _, b=btn: self.set_active_module(b.objectName()))

    def set_active_module(self, name: str) -> None:
        target = self._force_active_btn_name or name
        for btn in getattr(self, "_sidebar_btns", []):
            if btn.objectName() == target:
                btn.setStyleSheet(self._side_active_qss)
            else:
                btn.setStyleSheet(self._side_default_qss)

    def _icon_label(self, icon: FIF, size: int = 16) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel()
        accent = ThemeColor.PRIMARY.color()
        lbl.setPixmap(icon.icon(accent).pixmap(size, size))
        lbl.setFixedSize(size, size)
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _replace_placeholder(self, placeholder: QtWidgets.QWidget, icon: FIF, text: str) -> QtWidgets.QLabel:
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
        self.set_map_preview("Exploration area - Sector B")
        self.set_video_preview("Camera feed placeholder")
        self.set_task_info(
            name_text="Explore-02",
            type_text="????",
            traveled_text="1.2 km",
            progress_text="40%",
        )
    def set_map_preview(self, text: str) -> None:
        placeholder = getattr(self, "map2DPlaceholder", None)
        if not placeholder:
            return
        if not hasattr(self, "_map_preview_label"):
            self._map_preview_label = self._replace_placeholder(placeholder, FIF.GLOBE, text)
        else:
            self._map_preview_label.setText(text)

    def set_video_preview(self, text: str) -> None:
        placeholder = getattr(self, "videoPlaceholder", None)
        if not placeholder:
            return
        if not hasattr(self, "_video_preview_label"):
            self._video_preview_label = self._replace_placeholder(placeholder, FIF.CAMERA, text)
        else:
            self._video_preview_label.setText(text)

    def set_task_info(self, name_text: str, type_text: str, traveled_text: str, progress_text: str) -> None:
        if hasattr(self, "lblTaskNameVal"):
            self.lblTaskNameVal.setText(name_text)
            self.lblTaskNameVal.setStyleSheet("color: #2f3a46; font-size: 12px; border: none;")
        if hasattr(self, "lblTaskTypeVal"):
            self.lblTaskTypeVal.setText(type_text)
            self.lblTaskTypeVal.setStyleSheet("color: #2f3a46; font-size: 12px; border: none;")
        if hasattr(self, "lblTraveledVal"):
            self.lblTraveledVal.setText(traveled_text)
            self.lblTraveledVal.setStyleSheet("color: #2f3a46; font-size: 12px; border: none;")
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
        parent = self.parent()
        if parent and parent.isVisible():
            if self.size() != parent.size():
                self.resize(parent.size())

    def _apply_embedded_layout(self) -> None:
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


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = AutonomousExplorationPage()
    w.resize(1200, 720)
    w.show()
    sys.exit(app.exec_())

