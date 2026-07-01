import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize, QRectF, QPointF
from PyQt5.QtGui import QColor, QPainterPath, QRegion, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from qfluentwidgets import FluentIcon as FIF, ThemeColor

from modules.status_monitoring.ui.generated.RCMonitoring import Ui_Form


class RCMonitoringPage(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        self.apply_background()
        self.setup_topbar()
        self.apply_cards()
        self.apply_placeholders()
        self.apply_titles()
        self.apply_topbar_buttons()
        self.apply_demo_content()

    def setup_topbar(self) -> None:
        grid = getattr(self, "gridMain", None)
        if not grid:
            return

        self.frameTopBar = QtWidgets.QFrame(self)
        self.frameTopBar.setObjectName("frameTopBar")
        top_layout = QtWidgets.QHBoxLayout(self.frameTopBar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        btn_back = getattr(self, "btnBack", None)
        if btn_back is None:
            btn_back = QtWidgets.QToolButton(self.frameTopBar)
            btn_back.setObjectName("btnBack")
        if hasattr(self, "gridTop"):
            self.gridTop.removeWidget(btn_back)
        btn_back.setParent(self.frameTopBar)
        btn_back.setMinimumSize(36, 36)
        top_layout.addWidget(btn_back, 0, Qt.AlignLeft)
        top_layout.addStretch(1)

        self.btnMin = QtWidgets.QToolButton(self.frameTopBar)
        self.btnMin.setObjectName("btnMin")
        self.btnMin.setMinimumSize(36, 36)
        top_layout.addWidget(self.btnMin, 0, Qt.AlignRight)

        self.btnMax = QtWidgets.QToolButton(self.frameTopBar)
        self.btnMax.setObjectName("btnMax")
        self.btnMax.setMinimumSize(36, 36)
        top_layout.addWidget(self.btnMax, 0, Qt.AlignRight)

        self.btnClose = QtWidgets.QToolButton(self.frameTopBar)
        self.btnClose.setObjectName("btnClose")
        self.btnClose.setMinimumSize(36, 36)
        top_layout.addWidget(self.btnClose, 0, Qt.AlignRight)

        grid_top = getattr(self, "gridTop", None)
        grid_bottom = getattr(self, "gridBottom", None)
        if grid_top is not None:
            grid.removeItem(grid_top)
        if grid_bottom is not None:
            grid.removeItem(grid_bottom)

        grid.addWidget(self.frameTopBar, 0, 0)
        if grid_top is not None:
            grid.addLayout(grid_top, 1, 0)
        if grid_bottom is not None:
            grid.addLayout(grid_bottom, 2, 0)

        grid.setRowStretch(0, 0)
        grid.setRowStretch(1, 3)
        grid.setRowStretch(2, 2)

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
        """
        self.setStyleSheet(self.styleSheet() + "\n" + qss)

    def _apply_card_style(self, widget) -> None:
        widget.setStyleSheet(
            "QFrame {"
            "background: rgba(255, 255, 255, 180);"
            "border: 1px solid rgba(255, 255, 255, 140);"
            "border-radius: 16px;"
            "}"
        )
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 45))
        widget.setGraphicsEffect(shadow)

    def apply_cards(self) -> None:
        for name in [
            "frameStatus",
            "frameSpeedChart",
            "frameRealtimePos",
            "frameCompute",
            "frameEnergy",
            "frameComm",
            "frameDisk",
        ]:
            frame = getattr(self, name, None)
            if frame:
                self._apply_card_style(frame)

    def apply_placeholders(self) -> None:
        for name in [
            "statusPlaceholder",
            "speedChartPlaceholder",
            "realtimePosPlaceholder",
            "computePlaceholder",
            "energyPlaceholder",
            "commPlaceholder",
            "diskPlaceholder",
        ]:
            w = getattr(self, name, None)
            if w:
                w.setStyleSheet(
                    "background: rgba(255, 255, 255, 90);"
                    "border: 1px solid rgba(255, 255, 255, 120);"
                    "border-radius: 14px;"
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
            "labelStatusTitle",
            "labelSpeedTitle",
            "labelRealtimePosTitle",
            "labelComputeTitle",
            "labelEnergyTitle",
            "labelCommTitle",
            "labelDiskTitle",
        ]:
            lbl = getattr(self, name, None)
            if lbl:
                lbl.setStyleSheet(title_qss)

    def apply_demo_content(self) -> None:
        self._status_items = [
            ("OK", "All systems nominal"),
            ("INFO", "Telemetry linked"),
            ("OK", "Sensors synced"),
        ]
        self._speed_series = [12, 18, 22, 30, 26, 34, 28, 36, 42, 38, 44, 50]

        self._compute_usage = {"CPU": 38, "GPU": 22, "RAM": 64}
        self._energy_stats = {"Battery": 76, "Power": 48, "Temp": 42}
        self._comm_stats = {"Signal": 82, "Latency": 24, "Bandwidth": 18}
        self._disk_stats = {"Usage": 63, "Read": 120, "Write": 88}

        self.set_status_items(self._status_items)
        self.set_speed_series(self._speed_series)
        self.set_realtime_text("Map preview")
        self.set_compute_usage(**self._compute_usage)
        self.set_energy_stats(**self._energy_stats)
        self.set_comm_stats(**self._comm_stats)
        self.set_disk_stats(**self._disk_stats)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget:
                widget.deleteLater()
            if child_layout:
                self._clear_layout(child_layout)

    def _ensure_layout(self, widget) -> QtWidgets.QVBoxLayout:
        layout = widget.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._clear_layout(layout)
        return layout

    def _icon_label(self, icon: FIF, size: int = 16) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel()
        accent = ThemeColor.PRIMARY.color()
        lbl.setPixmap(icon.icon(accent).pixmap(size, size))
        lbl.setFixedSize(size, size)
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _make_stat_row(self, name: str, value: str) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QtWidgets.QLabel(name)
        label.setStyleSheet("color: #5f6b7a; font-size: 12px;")
        value_label = QtWidgets.QLabel(value)
        value_label.setStyleSheet("color: #2f3a46; font-size: 12px; font-weight: 600;")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(value_label)
        return row

    def set_status_items(self, items) -> None:
        w = getattr(self, "statusPlaceholder", None)
        if not w:
            return
        layout = self._ensure_layout(w)

        for level, text in items:
            row = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            icon = FIF.ACCEPT if level == "OK" else FIF.INFO
            row_layout.addWidget(self._icon_label(icon))

            lbl = QtWidgets.QLabel(text)
            lbl.setStyleSheet("color: #3b4552; font-size: 12px;")
            row_layout.addWidget(lbl)
            row_layout.addStretch(1)
            layout.addWidget(row)

    def set_speed_series(self, values) -> None:
        w = getattr(self, "speedChartPlaceholder", None)
        if not w:
            return
        layout = self._ensure_layout(w)
        self.speedChartLabel = QtWidgets.QLabel()
        self.speedChartLabel.setMinimumHeight(140)
        self.speedChartLabel.setStyleSheet("background: transparent;")
        layout.addWidget(self.speedChartLabel, 1)
        self._render_speed_chart(values)

    def _render_speed_chart(self, values) -> None:
        if not hasattr(self, "speedChartLabel"):
            return
        label = self.speedChartLabel
        width = max(label.width(), 320)
        height = max(label.height(), 140)

        pix = QPixmap(width, height)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(ThemeColor.PRIMARY.color(), 2)
        painter.setPen(pen)

        if values:
            max_val = max(values)
            min_val = min(values)
            span = max(max_val - min_val, 1)
            step = width / max(len(values) - 1, 1)
            points = []
            for i, v in enumerate(values):
                x = i * step
                y = height - (v - min_val) / span * (height - 16) - 8
                points.append((x, y))
            for i in range(1, len(points)):
                p1 = QPointF(points[i - 1][0], points[i - 1][1])
                p2 = QPointF(points[i][0], points[i][1])
                painter.drawLine(p1, p2)

        painter.end()
        label.setPixmap(pix)

    def set_realtime_text(self, text: str) -> None:
        w = getattr(self, "realtimePosPlaceholder", None)
        if not w:
            return
        layout = self._ensure_layout(w)
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(self._icon_label(FIF.PIN))
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet("color: #3b4552; font-size: 12px;")
        row_layout.addWidget(lbl)
        row_layout.addStretch(1)
        layout.addWidget(row)

    def _set_stat_block(self, placeholder_name: str, stats: list[tuple[str, str]]) -> None:
        w = getattr(self, placeholder_name, None)
        if not w:
            return
        layout = self._ensure_layout(w)
        for name, value in stats:
            layout.addWidget(self._make_stat_row(name, value))

    def set_compute_usage(self, CPU: int, GPU: int, RAM: int) -> None:
        self._set_stat_block(
            "computePlaceholder",
            [("CPU", f"{CPU}%"), ("GPU", f"{GPU}%"), ("RAM", f"{RAM}%")],
        )

    def set_energy_stats(self, Battery: int, Power: int, Temp: int) -> None:
        self._set_stat_block(
            "energyPlaceholder",
            [("Battery", f"{Battery}%"), ("Power", f"{Power}W"), ("Temp", f"{Temp}C")],
        )

    def set_comm_stats(self, Signal: int, Latency: int, Bandwidth: int) -> None:
        self._set_stat_block(
            "commPlaceholder",
            [("Signal", f"{Signal}%"), ("Latency", f"{Latency}ms"), ("Bandwidth", f"{Bandwidth}Mb/s")],
        )

    def set_disk_stats(self, Usage: int, Read: int, Write: int) -> None:
        self._set_stat_block(
            "diskPlaceholder",
            [("Usage", f"{Usage}%"), ("Read", f"{Read}MB/s"), ("Write", f"{Write}MB/s")],
        )
    def apply_topbar_buttons(self) -> None:
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

        btn_back = getattr(self, "btnBack", None)
        if btn_back:
            btn_back.setIcon(FIF.LEFT_ARROW.icon(accent))
            btn_back.setIconSize(QSize(18, 18))
            btn_back.setStyleSheet(btn_style)
            btn_back.clicked.connect(self.close)

        for name, icon in [
            ("btnMin", FIF.MINIMIZE),
            ("btnMax", FIF.FULL_SCREEN),
            ("btnClose", FIF.CLOSE),
        ]:
            btn = getattr(self, name, None)
            if not btn:
                continue
            btn.setIcon(icon.icon(accent))
            btn.setIconSize(QSize(18, 18))
            btn.setStyleSheet(btn_style)

        if getattr(self, "btnMin", None):
            self.btnMin.clicked.connect(self._minimize_window)
        if getattr(self, "btnMax", None):
            self.btnMax.clicked.connect(self._toggle_maximize)
        if getattr(self, "btnClose", None):
            self.btnClose.clicked.connect(self.close)

    def _minimize_window(self) -> None:
        self.window().showMinimized()

    def _toggle_maximize(self) -> None:
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        radius = 16
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        if hasattr(self, "_speed_series"):
            self._render_speed_chart(self._speed_series)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = RCMonitoringPage()
    w.resize(1080, 720)
    w.show()
    sys.exit(app.exec_())
