# -*- coding: utf-8 -*-
from __future__ import annotations

from PyQt5.QtCore import QEasingCurve, QPoint, QSequentialAnimationGroup, QTimer, Qt, QSize, QRect, QRectF, QEvent
from PyQt5.QtCore import QPropertyAnimation
from PyQt5.QtGui import QColor, QPainterPath, QRegion
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget, QPushButton
from qfluentwidgets import FluentIcon as FIF, ThemeColor

from UI.generated.TaskExecutionManagement import Ui_TaskExecutionManagement


class TaskExecutionManagementPage(QWidget, Ui_TaskExecutionManagement):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(980, 560)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._theme_name = "sky"
        self._is_dragging = False
        self._drag_offset = QPoint()
        self._inspect_area = None
        self._inspect_point = None
        self._inspect_route = None
        self._inspect_mag = None
        self._float_groups = []
        self._float_specs = []
        self._bubble_base_rects = {}
        self._bubble_base_bounds = None
        self._bubble_base_font_px = {}
        self._bubble_container = None
        self._titlebar_bound = False
        self._apply_fluent_style()
        self._setup_titlebar()
        self._setup_bubbles()
        self._ensure_bubble_base()
        self._bind_actions()
        self._pages = {}
        if hasattr(self, "mainFrame"):
            self.mainFrame.setAttribute(Qt.WA_StyledBackground, True)
        if hasattr(self, "titleBar"):
            self.titleBar.setAttribute(Qt.WA_StyledBackground, True)
            self.titleBar.installEventFilter(self)
        if hasattr(self, "lblTitle"):
            self.lblTitle.installEventFilter(self)

    def _apply_fluent_style(self) -> None:
        palettes = {
            "sky": {
                "bg0": "#f6faff",
                "bg1": "#ecf3ff",
                "panel_border": "rgba(34, 64, 112, 18)",
                "title_text": "#243447",
                "bubble_border": "#8fb8ff",
                "bubble_text": "#243447",
                "bubble_bg0": "rgba(255,255,255,212)",
                "bubble_bg1": "rgba(77,140,255,36)",
                "bubble_hover1": "rgba(110,163,255,58)",
                "shadow_rgb": "35,75,140",
            },
            "sunset": {
                "bg0": "#fff7ef",
                "bg1": "#ffeede",
                "panel_border": "rgba(120, 66, 26, 20)",
                "title_text": "#3f2a1f",
                "bubble_border": "#f0b27a",
                "bubble_text": "#3f2a1f",
                "bubble_bg0": "rgba(255,255,255,214)",
                "bubble_bg1": "rgba(255,167,99,36)",
                "bubble_hover1": "rgba(255,145,77,62)",
                "shadow_rgb": "123,62,20",
            },
        }
        theme = palettes.get(self._theme_name, palettes["sky"])
        self.setStyleSheet(
            f"""
            QWidget#TaskExecutionManagement {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme["bg0"]},
                    stop:1 {theme["bg1"]}
                );
                border-radius: 16px;
            }}

            QFrame#titleBar {{
                background: rgba(255, 255, 255, 220);
                border: 1px solid {theme["panel_border"]};
                border-radius: 12px;
            }}

            QLabel#lblTitle {{
                color: {theme["title_text"]};
                font: 600 18px "Microsoft YaHei";
            }}

            QFrame#mainFrame {{
                background: rgba(255, 255, 255, 220);
                border: 1px solid {theme["panel_border"]};
                border-radius: 16px;
            }}

            QPushButton#btnBack,
            QPushButton#btnMax,
            QPushButton#btnClose {{
                border-radius: 8px;
                border: 1px solid {theme["bubble_border"]};
                background: rgba(255, 255, 255, 210);
            }}
            QPushButton#btnBack:hover,
            QPushButton#btnMax:hover,
            QPushButton#btnClose:hover {{
                background: {theme["bubble_hover1"]};
            }}

            QPushButton[bubble="true"] {{
                border: 1px solid {theme["bubble_border"]};
                border-radius: 999px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {theme["bubble_bg0"]},
                    stop:1 {theme["bubble_bg1"]}
                );
                color: {theme["bubble_text"]};
            }}
            QPushButton[bubble="true"]:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 {theme["bubble_hover1"]}
                );
            }}
            """
        )

    def _setup_titlebar(self) -> None:
        if self._theme_name == "sunset":
            accent = QColor("#f0b27a")
        else:
            accent = ThemeColor.PRIMARY.color()
        icon_size = QSize(18, 18)

        for name, icon in {
            "btnBack": FIF.LEFT_ARROW,
            "btnMax": FIF.FULL_SCREEN,
            "btnClose": FIF.CLOSE,
        }.items():
            btn = getattr(self, name, None)
            if not btn:
                continue
            btn.setText("")
            btn.setIcon(icon.icon(accent))
            btn.setIconSize(icon_size)
            btn.setCursor(Qt.PointingHandCursor)

        if not self._titlebar_bound:
            if hasattr(self, "btnBack"):
                self.btnBack.clicked.connect(self.close)
            if hasattr(self, "btnMax"):
                self.btnMax.clicked.connect(self._toggle_fullscreen)
            if hasattr(self, "btnClose"):
                self.btnClose.clicked.connect(self.close)
            self._titlebar_bound = True

    def _toggle_fullscreen(self) -> None:
        win = self.window()
        if win.isFullScreen():
            win.showNormal()
        else:
            win.showFullScreen()

    def _setup_bubbles(self) -> None:
        # Remove legacy stylesheet from .ui to avoid overriding fluent bubble style.
        if hasattr(self, "canvasArea"):
            self.canvasArea.setStyleSheet("")

        bubble_names = [
            "btnMapBuild",
            "btnTargetIdentify",
            "btnObstacleAvoid",
            "btnWaitDev",
            "btnTargetTrack",
            "btnFixedPatrol",
            "btnExploreAuto",
            "bubbleSmall1",
            "bubbleSmall2",
            "bubbleSmall3",
            "bubbleSmall4",
            "bubbleSmall5",
        ]

        self._bubble_names = bubble_names
        for idx, name in enumerate(bubble_names):
            btn = getattr(self, name, None)
            if not isinstance(btn, QPushButton):
                continue
            # Keep style controlled by this page, not by fixed radius from .ui
            btn.setStyleSheet("")
            btn.setProperty("bubble", True)
            btn.setCursor(Qt.PointingHandCursor)
            self._add_shadow(btn, blur=18, alpha=70)
            # Small, subtle float animation with different phases.
            amplitude = 6 if "bubbleSmall" in name else 8
            duration = 2400 + idx * 120
            delay = idx * 150
            self._float_specs.append((btn, amplitude, duration, delay))

        self._restart_float_animations()

    def _restart_float_animations(self) -> None:
        for group in self._float_groups:
            group.stop()
        self._float_groups.clear()
        for btn, amplitude, duration, delay in self._float_specs:
            self._float_button(btn, amplitude, duration, delay)

    def _bind_actions(self) -> None:
        mapping = {
            "btnMapBuild": "map",
            "btnTargetIdentify": "detect",
            "btnObstacleAvoid": "avoid",
            "btnWaitDev": "wait",
            "btnTargetTrack": "track",
            "btnFixedPatrol": "patrol",
            "btnExploreAuto": "explore",
        }

        for name, key in mapping.items():
            btn = getattr(self, name, None)
            if not isinstance(btn, QPushButton):
                continue
            btn.clicked.connect(lambda _, k=key: self._open_page(k))

    def _open_page(self, key: str) -> None:
        if key == "wait":
            btn = getattr(self, "btnWaitDev", None)
            if btn:
                btn.setText("待开发")
            return

        if key not in self._pages:
            if key == "map":
                from modules.task_management.pages.taskmanagement_page import TaskManagementPage

                self._pages[key] = TaskManagementPage()
            elif key == "patrol":
                self._open_inspect_mag()
                return
            elif key == "detect":
                from modules.task_management.pages.TargetRecognition_new_page import TargetRecognitionNewPage

                self._pages[key] = TargetRecognitionNewPage()
            elif key == "track":
                from modules.task_management.pages.target_tracking_page import TargetTrackingPage

                self._pages[key] = TargetTrackingPage()
            elif key == "explore":
                from modules.task_management.pages.autonomous_exploration_page import AutonomousExplorationPage

                self._pages[key] = AutonomousExplorationPage()
            elif key == "avoid":
                from modules.task_management.pages.intelligent_obstacle_avoidance_page import (
                    IntelligentObstacleAvoidancePage,
                )

                self._pages[key] = IntelligentObstacleAvoidancePage()

        page = self._pages.get(key)
        if page:
            page.show()
            page.raise_()
            page.activateWindow()

    def _open_inspect_mag(self) -> None:
        from MICCProject1.scripts.BLL_InspectMag import BLL_InspectMag

        if self._inspect_mag is None or not self._inspect_mag.isVisible():
            self._inspect_mag = BLL_InspectMag()
        self._inspect_mag.show()
        self._inspect_mag.raise_()
        self._inspect_mag.activateWindow()

    def _open_inspect_area(self) -> None:
        from MICCProject1.scripts.BLL_InspectArea import BLL_InspectArea

        if self._inspect_area is None or not self._inspect_area.isVisible():
            self._inspect_area = BLL_InspectArea(
                on_next=self._open_inspect_point,
                on_close=self._close_inspect_flow,
                on_jump=self._jump_inspect_step,
            )
        self._inspect_area.show()
        self._inspect_area.raise_()
        self._inspect_area.activateWindow()

    def _open_inspect_point(self) -> None:
        from MICCProject1.scripts.BLL_InspectPoint_V4 import BLL_InspectPoint

        if self._inspect_point is None or not self._inspect_point.isVisible():
            self._inspect_point = BLL_InspectPoint(
                on_prev=self._open_inspect_area,
                on_next=self._open_inspect_route,
                on_close=self._close_inspect_flow,
                on_jump=self._jump_inspect_step,
            )
        self._inspect_point.show()
        self._inspect_point.raise_()
        self._inspect_point.activateWindow()

    def _open_inspect_route(self) -> None:
        from MICCProject1.scripts.BLL_InspectRoute_V1 import BLL_InspectRoute

        if self._inspect_route is None or not self._inspect_route.isVisible():
            self._inspect_route = BLL_InspectRoute(
                on_prev=self._open_inspect_point,
                on_close=self._close_inspect_flow,
                on_jump=self._jump_inspect_step,
            )
        self._inspect_route.show()
        self._inspect_route.raise_()
        self._inspect_route.activateWindow()

    def _close_inspect_flow(self) -> None:
        for w in (self._inspect_mag, self._inspect_area, self._inspect_point, self._inspect_route):
            try:
                if w:
                    w.close()
            except Exception:
                pass

    def _jump_inspect_step(self, index: int) -> None:
        if index == 0:
            self._open_inspect_area()
        elif index == 1:
            self._open_inspect_point()
        elif index == 2:
            self._open_inspect_route()

    def _add_shadow(self, widget: QWidget, blur=18, dx=0, dy=6, alpha=60) -> None:
        palettes = {
            "sky": QColor(35, 75, 140, alpha),
            "sunset": QColor(123, 62, 20, alpha),
        }
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(dx, dy)
        shadow.setColor(palettes.get(self._theme_name, QColor(35, 75, 140, alpha)))
        widget.setGraphicsEffect(shadow)

    def _ensure_bubble_base(self) -> None:
        if self._bubble_base_bounds is not None:
            return

        if hasattr(self, "canvasArea"):
            self._bubble_container = self.canvasArea
        elif hasattr(self, "bubbleCanvas"):
            self._bubble_container = self.bubbleCanvas
        else:
            self._bubble_container = getattr(self, "mainFrame", self)

        min_x = None
        min_y = None
        max_x = None
        max_y = None
        for name in getattr(self, "_bubble_names", []):
            btn = getattr(self, name, None)
            if isinstance(btn, QPushButton):
                rect = btn.geometry()
                self._bubble_base_rects[name] = rect
                if btn.text().strip():
                    base_px = max(16, int(min(rect.width(), rect.height()) * 0.11))
                    self._bubble_base_font_px[name] = base_px
                if min_x is None:
                    min_x, min_y = rect.x(), rect.y()
                    max_x, max_y = rect.x() + rect.width(), rect.y() + rect.height()
                else:
                    min_x = min(min_x, rect.x())
                    min_y = min(min_y, rect.y())
                    max_x = max(max_x, rect.x() + rect.width())
                    max_y = max(max_y, rect.y() + rect.height())

        if min_x is None:
            return

        self._bubble_base_bounds = QRect(
            min_x,
            min_y,
            max(1, max_x - min_x),
            max(1, max_y - min_y),
        )

    def _update_bubble_layout(self) -> None:
        self._ensure_bubble_base()
        if not self._bubble_base_bounds or not self._bubble_base_rects:
            return

        container = self._bubble_container
        if container is None:
            return

        avail_w = container.width()
        avail_h = container.height()
        if avail_w <= 0 or avail_h <= 0:
            return

        margin = 20
        base_w = self._bubble_base_bounds.width()
        base_h = self._bubble_base_bounds.height()
        fit_w = max(1, avail_w - margin * 2)
        fit_h = max(1, avail_h - margin * 2)
        scale = min(fit_w / base_w, fit_h / base_h)
        if scale <= 0:
            return

        origin_x = int((avail_w - base_w * scale) / 2)
        origin_y = int((avail_h - base_h * scale) / 2)

        for name, base_rect in self._bubble_base_rects.items():
            btn = getattr(self, name, None)
            if not isinstance(btn, QPushButton):
                continue
            x = origin_x + int((base_rect.x() - self._bubble_base_bounds.x()) * scale)
            y = origin_y + int((base_rect.y() - self._bubble_base_bounds.y()) * scale)
            w = max(1, int(base_rect.width() * scale))
            h = max(1, int(base_rect.height() * scale))
            btn.setGeometry(QRect(x, y, w, h))
            # Keep buttons circular after resize/fullscreen.
            btn.setStyleSheet(f"border-radius: {int(min(w, h) / 2)}px;")
            if name in self._bubble_base_font_px:
                font = btn.font()
                # Scale up text in fullscreen, but keep a safe cap for readability.
                px = int(self._bubble_base_font_px[name] * (0.75 + 0.25 * scale))
                px = max(16, min(px, int(min(w, h) * 0.24), 38))
                font.setPixelSize(px)
                btn.setFont(font)

        self._restart_float_animations()

    def _float_button(self, btn: QPushButton, amplitude: int, duration: int, delay_ms: int) -> None:
        base = btn.pos()

        up = QPropertyAnimation(btn, b"pos", self)
        up.setStartValue(base)
        up.setEndValue(QPoint(base.x(), base.y() - amplitude))
        up.setDuration(duration)
        up.setEasingCurve(QEasingCurve.InOutSine)

        down = QPropertyAnimation(btn, b"pos", self)
        down.setStartValue(QPoint(base.x(), base.y() - amplitude))
        down.setEndValue(base)
        down.setDuration(duration)
        down.setEasingCurve(QEasingCurve.InOutSine)

        group = QSequentialAnimationGroup(self)
        group.addAnimation(up)
        group.addAnimation(down)
        group.setLoopCount(-1)

        self._float_groups.append(group)
        group.start()

    def eventFilter(self, obj, event):
        title_bar = getattr(self, "titleBar", None)
        title_label = getattr(self, "lblTitle", None)
        if obj in (title_bar, title_label):
            event_type = event.type()
            if event_type == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if self._can_start_drag(event.globalPos()):
                    self._is_dragging = True
                    self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
                    event.accept()
                    return True
            elif event_type == QEvent.MouseMove and self._is_dragging and (event.buttons() & Qt.LeftButton):
                self.move(event.globalPos() - self._drag_offset)
                event.accept()
                return True
            elif event_type == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._is_dragging = False
            elif event_type == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                if self._can_start_drag(event.globalPos()):
                    self._toggle_fullscreen()
                    event.accept()
                    return True
        return super().eventFilter(obj, event)

    def _can_start_drag(self, global_pos: QPoint) -> bool:
        if self.isFullScreen() or self.isMaximized():
            return False
        title_bar = getattr(self, "titleBar", None)
        if title_bar is None:
            return False
        pos_in_title = title_bar.mapFromGlobal(global_pos)
        child = title_bar.childAt(pos_in_title)
        return not isinstance(child, QPushButton)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self.isVisible():
            return
        self._update_bubble_layout()
        self._apply_container_masks()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Delay one cycle to ensure container size is final after first show/fullscreen.
        QTimer.singleShot(0, self._update_bubble_layout)
        QTimer.singleShot(0, self._apply_container_masks)

    def _apply_container_masks(self) -> None:
        if hasattr(self, "titleBar"):
            self._apply_round_mask(self.titleBar, 12)
        if hasattr(self, "mainFrame"):
            self._apply_round_mask(self.mainFrame, 16)

    @staticmethod
    def _apply_round_mask(widget: QWidget, radius: int) -> None:
        rect = widget.rect()
        if rect.width() <= 1 or rect.height() <= 1:
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        widget.setMask(region)

    def set_theme(self, name: str) -> None:
        normalized = (name or "").strip().lower()
        if normalized not in {"sky", "sunset"}:
            normalized = "sky"
        self._theme_name = normalized
        self._apply_fluent_style()
        self._setup_titlebar()
        self._update_bubble_layout()
