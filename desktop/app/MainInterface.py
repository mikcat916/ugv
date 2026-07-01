# app/MainInterface.py
from __future__ import annotations

import re
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QPushButton, QMessageBox, QStyle
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtCore import QSize, Qt, QPoint, QEvent
from qfluentwidgets import FluentIcon as FIF, ThemeColor

try:
    from .UiLoader import resource_path
    from UI.generated.MainInterface import Ui_Form
    from modules.basic_control.main import create_basic_control_page
    from modules.status_monitoring.main import create_status_monitoring_page
    from modules.task_management.main import create_task_management_page
    from modules.asset_management.main import create_asset_management_window
except ImportError:  # allow running as a script
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from app.UiLoader import resource_path
    from UI.generated.MainInterface import Ui_Form
    from modules.basic_control.main import create_basic_control_page
    from modules.status_monitoring.main import create_status_monitoring_page
    from modules.task_management.main import create_task_management_page
    from modules.asset_management.main import create_asset_management_window


def add_shadow(w: QWidget, blur=45, dx=0, dy=8, alpha=60, color=None):
    """Add a soft shadow around a widget."""
    eff = QGraphicsDropShadowEffect(w)
    eff.setBlurRadius(blur)
    eff.setOffset(dx, dy)
    base = color or QColor(0, 0, 0)
    eff.setColor(QColor(base.red(), base.green(), base.blue(), alpha))
    w.setGraphicsEffect(eff)


def resolve_image_path(name: str) -> str | None:
    """Resolve an image filename from common project folders."""
    candidates = [
        resource_path(f"assets/{name}"),
        resource_path(f"assets/images/{name}"),
        resource_path(f"UI/{name}"),
        resource_path(f"ui/{name}"),
    ]
    for p in candidates:
        if Path(p).exists():
            return Path(p).resolve().as_posix()
    return None


class MainInterface(QWidget):
    def __init__(self):
        super().__init__()
        ui = Ui_Form()
        ui.setupUi(self)
        self.ui = ui
        self._task_theme = "sky"
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowIcon(QIcon(resource_path("assets/app.ico")))
        self.apply_image_paths()
        self.apply_logo_icon()
        self.setup_card_hover_shadow()
        self.bind_module_links()
        self.bind_window_controls()
        self._ensure_max_button()
        self._ensure_task_theme_button()
        self._normalize_window_buttons()

        # 1) Add a soft gradient-like shadow to rootWrap.
        root = self.findChild(QWidget, "rootWrap")
        if root:
            add_shadow(root, blur=55, dy=10, alpha=55)
            parent = root.parentWidget()
            if parent and parent.layout():
                parent.layout().setContentsMargins(18, 18, 18, 18)

        # 2) 如果你发现阴影被裁切：去 Designer 给 rootWrap 的父布局留 margin（20~30）



    def apply_image_paths(self) -> None:
        """Replace qrc urls with real file paths and strip unsupported QSS."""
        mapping = {
            "imgpush": "control2.png",
            "imgpush2": "zhuangtai2.png",
            "imgpush3": "renwu2.png",
            "imgpush4": "chuangan2.png",
            "imgpush5": "tongxin2.png",
            "imgpush6": "zonghe2.png",
        }

        for widget_name, filename in mapping.items():
            btn = self.findChild(QWidget, widget_name)
            if not btn:
                continue

            image_path = resolve_image_path(filename)
            if not image_path:
                print(f"[warn] image not found: {filename}")
                style = btn.styleSheet()
                style = re.sub(r"background-size\s*:[^;]+;", "", style)
                style = re.sub(
                    rf"url\([^)]*{re.escape(filename)}\)",
                    lambda _: "none",
                    style,
                )
                btn.setStyleSheet(style)
                continue

            style = btn.styleSheet()
            style = re.sub(r"background-size\s*:[^;]+;", "", style)
            style = re.sub(
                rf"url\([^)]*{re.escape(filename)}\)",
                lambda _: f'url("{image_path}")',
                style,
            )
            btn.setStyleSheet(style)



    def apply_logo_icon(self) -> None:
        """Set a crisp logo icon on the top-left button."""
        btn = self.findChild(QWidget, "btnpic")
        if not btn:
            return

        icon_path = resolve_image_path("robot.png") or resolve_image_path("app.ico")
        if not icon_path:
            return

        btn.setStyleSheet("border: none;")
        btn.setIcon(QIcon(icon_path))
        size = min(btn.width(), btn.height())
        btn.setIconSize(QSize(int(size * 0.85), int(size * 0.85)))

    def setup_card_hover_shadow(self) -> None:
        """Add subtle hover shadow to image cards."""
        self._card_shadow_targets = []
        for name in ["imgpush", "imgpush2", "imgpush3", "imgpush4", "imgpush5", "imgpush6"]:
            btn = self.findChild(QWidget, name)
            if btn:
                btn.installEventFilter(self)
                self._card_shadow_targets.append(btn)

    def bind_module_links(self) -> None:
        """Bind module entry buttons to their pages."""
        btn_basic = self.findChild(QWidget, "imgpush")
        if btn_basic:
            btn_basic.clicked.connect(self.open_basic_control)

        btn_monitor = self.findChild(QWidget, "imgpush2")
        if btn_monitor:
            btn_monitor.clicked.connect(self.open_rc_monitoring)

        btn_task = self.findChild(QWidget, "imgpush3")
        if btn_task:
            btn_task.clicked.connect(self.open_task_management)

        btn_asset = self.findChild(QWidget, "imgpush6")
        if btn_asset:
            btn_asset.clicked.connect(self.open_asset_management)

    def open_basic_control(self) -> None:
        if not hasattr(self, "_basic_control_page") or self._basic_control_page is None:
            self._basic_control_page = create_basic_control_page(self)
        self._basic_control_page.show()

    def open_rc_monitoring(self) -> None:
        if not hasattr(self, "_rc_monitoring_page") or self._rc_monitoring_page is None:
            self._rc_monitoring_page = create_status_monitoring_page(self)
        self._rc_monitoring_page.show()

    def open_task_management(self) -> None:
        if not hasattr(self, "_task_management_page") or self._task_management_page is None:
            self._task_management_page = create_task_management_page()
        self._apply_task_theme()
        self._task_management_page.show()
        self._task_management_page.raise_()
        self._task_management_page.activateWindow()

    def open_asset_management(self) -> None:
        try:
            if (
                not hasattr(self, "_asset_management_page")
                or self._asset_management_page is None
                or not self._asset_management_page.isVisible()
            ):
                self._asset_management_page = create_asset_management_window()
            self._asset_management_page.show()
            self._asset_management_page.raise_()
            self._asset_management_page.activateWindow()
        except Exception as exc:
            QMessageBox.critical(self, "启动失败", f"无法打开设备综合管理模块:\n{exc}")

    def eventFilter(self, obj, event):
        if hasattr(self, "_card_shadow_targets") and obj in self._card_shadow_targets:
            if event.type() == QEvent.Enter:
                shadow = QGraphicsDropShadowEffect(obj)
                shadow.setBlurRadius(24)
                shadow.setOffset(0, 6)
                shadow.setColor(QColor(0, 0, 0, 60))
                obj.setGraphicsEffect(shadow)
            elif event.type() == QEvent.Leave:
                obj.setGraphicsEffect(None)
        return super().eventFilter(obj, event)

    def bind_window_controls(self) -> None:
        """Hook up minimize and close buttons."""
        btn_min = self.findChild(QWidget, "btnMin")
        if btn_min:
            btn_min.clicked.connect(self.showMinimized)

        btn_exit = self.findChild(QWidget, "btnExit")
        if btn_exit:
            btn_exit.clicked.connect(self.close)

        btn_max = self.findChild(QWidget, "btnMax")
        if btn_max:
            btn_max.clicked.connect(self._toggle_maximize)

    def _ensure_max_button(self) -> None:
        if self.findChild(QWidget, "btnMax"):
            return

        layout = getattr(self.ui, "horizontalLayout_3", None)
        if layout is None:
            return

        btn_max = QPushButton(self.ui.topBar)
        btn_max.setObjectName("btnMax")
        btn_max.setFixedSize(36, 36)

        accent = ThemeColor.PRIMARY.color()
        btn_max.setIcon(FIF.FULL_SCREEN.icon(accent))
        btn_max.setIconSize(QSize(24, 24))

        btn_min = self.findChild(QWidget, "btnMin")
        if btn_min:
            style = btn_min.styleSheet()
            btn_max.setStyleSheet(style.replace("#btnMin", "#btnMax"))
        else:
            btn_max.setStyleSheet(
                "QPushButton#btnMax {"
                "background: transparent;"
                "border: none;"
                "padding: 6px;"
                "}"
                "QPushButton#btnMax:hover {"
                "background: rgba(0,0,0,20);"
                "border-radius: 8px;"
                "}"
                "QPushButton#btnMax:pressed {"
                "background: rgba(0,0,0,35);"
                "}"
            )

        btn_exit = self.findChild(QWidget, "btnExit")
        if btn_exit and btn_exit.parent() is self.ui.topBar:
            idx = layout.indexOf(btn_exit)
            if idx >= 0:
                layout.insertWidget(idx, btn_max)
            else:
                layout.addWidget(btn_max)
        else:
            layout.addWidget(btn_max)

        btn_max.clicked.connect(self._toggle_maximize)

    def _ensure_task_theme_button(self) -> None:
        if self.findChild(QWidget, "btnTaskTheme"):
            return

        layout = getattr(self.ui, "horizontalLayout_3", None)
        if layout is None:
            return

        btn_theme = QPushButton(self.ui.topBar)
        btn_theme.setObjectName("btnTaskTheme")
        btn_theme.setFixedHeight(36)
        btn_theme.setMinimumWidth(62)
        btn_theme.setToolTip("一键切换任务执行管理主题")

        btn_min = self.findChild(QWidget, "btnMin")
        if btn_min:
            style = btn_min.styleSheet()
            btn_theme.setStyleSheet(style.replace("#btnMin", "#btnTaskTheme"))
        else:
            btn_theme.setStyleSheet(
                "QPushButton#btnTaskTheme {"
                "background: transparent;"
                "border: 1px solid rgba(0,0,0,25);"
                "border-radius: 8px;"
                "padding: 4px 10px;"
                "}"
                "QPushButton#btnTaskTheme:hover {"
                "background: rgba(0,0,0,18);"
                "}"
                "QPushButton#btnTaskTheme:pressed {"
                "background: rgba(0,0,0,30);"
                "}"
            )

        self._theme_button = btn_theme
        self._refresh_task_theme_button()
        btn_theme.clicked.connect(self._toggle_task_theme)

        btn_max = self.findChild(QWidget, "btnMax")
        if btn_max and btn_max.parent() is self.ui.topBar:
            idx = layout.indexOf(btn_max)
            if idx >= 0:
                layout.insertWidget(idx, btn_theme)
            else:
                layout.addWidget(btn_theme)
        else:
            layout.addWidget(btn_theme)

    def _normalize_window_buttons(self) -> None:
        layout = getattr(self.ui, "horizontalLayout_3", None)
        top_bar = getattr(self.ui, "topBar", None)
        if layout is None or top_bar is None:
            return

        btn_min = self.findChild(QPushButton, "btnMin")
        if btn_min is None:
            btn_min = QPushButton(top_bar)
            btn_min.setObjectName("btnMin")
            btn_min.clicked.connect(self.showMinimized)
        btn_max = self.findChild(QPushButton, "btnMax")
        if btn_max is None:
            self._ensure_max_button()
            btn_max = self.findChild(QPushButton, "btnMax")
        btn_exit = self.findChild(QPushButton, "btnExit")
        if btn_exit is None:
            btn_exit = QPushButton(top_bar)
            btn_exit.setObjectName("btnExit")
            btn_exit.clicked.connect(self.close)

        if not btn_max:
            return

        for btn in (btn_min, btn_max, btn_exit):
            if btn.parent() is not top_bar:
                btn.setParent(top_bar)
            btn.setFixedSize(36, 36)
            btn.setText("")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton#{btn.objectName()} {{"
                "background: transparent;"
                "border: none;"
                "padding: 6px;"
                "border-radius: 8px;"
                "}"
                f"QPushButton#{btn.objectName()}:hover {{"
                "background: rgba(0,0,0,24);"
                "}"
                f"QPushButton#{btn.objectName()}:pressed {{"
                "background: rgba(0,0,0,38);"
                "}"
            )

        btn_exit.setStyleSheet(
            "QPushButton#btnExit {"
            "background: transparent;"
            "border: none;"
            "padding: 6px;"
            "border-radius: 8px;"
            "}"
            "QPushButton#btnExit:hover {"
            "background: rgba(212, 45, 45, 180);"
            "}"
            "QPushButton#btnExit:pressed {"
            "background: rgba(170, 36, 36, 220);"
            "}"
        )

        style = self.style()
        btn_min.setIcon(style.standardIcon(QStyle.SP_TitleBarMinButton))
        btn_exit.setIcon(style.standardIcon(QStyle.SP_TitleBarCloseButton))
        btn_min.setIconSize(QSize(16, 16))
        btn_max.setIconSize(QSize(16, 16))
        btn_exit.setIconSize(QSize(16, 16))
        btn_min.setToolTip("最小化")
        btn_max.setToolTip("最大化/还原")
        btn_exit.setToolTip("关闭")
        self._sync_max_button_icon()

        btn_theme = self.findChild(QPushButton, "btnTaskTheme")
        for w in (btn_theme, btn_min, btn_max, btn_exit):
            if w and w.parent() is top_bar:
                layout.removeWidget(w)
        if btn_theme:
            layout.addWidget(btn_theme)
        layout.addWidget(btn_min)
        layout.addWidget(btn_max)
        layout.addWidget(btn_exit)

    def _sync_max_button_icon(self) -> None:
        btn_max = self.findChild(QPushButton, "btnMax")
        if not btn_max:
            return
        icon_type = QStyle.SP_TitleBarNormalButton if self.isMaximized() else QStyle.SP_TitleBarMaxButton
        btn_max.setIcon(self.style().standardIcon(icon_type))

    def _refresh_task_theme_button(self) -> None:
        btn = getattr(self, "_theme_button", None)
        if not btn:
            return
        btn.setText("蓝调" if self._task_theme == "sky" else "暖调")

    def _toggle_task_theme(self) -> None:
        self._task_theme = "sunset" if self._task_theme == "sky" else "sky"
        self._refresh_task_theme_button()
        self._apply_task_theme()

    def _apply_task_theme(self) -> None:
        page = getattr(self, "_task_management_page", None)
        if page and hasattr(page, "set_theme"):
            page.set_theme(self._task_theme)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_max_button_icon()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._sync_max_button_icon()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        root = self.findChild(QWidget, "rootWrap")
        if root:
            margin = 18
            rect = self.rect().adjusted(margin, margin, -margin, -margin)
            root.setGeometry(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()


def run_main_interface() -> int:
    """Launch the main interface as a standalone window."""
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MainInterface()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(run_main_interface())
