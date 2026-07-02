# app/login.py
from __future__ import annotations

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, Qt, QTimer, QEvent, QSize
from PyQt5.QtCore import QSequentialAnimationGroup
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtGui import QIcon
from qfluentwidgets import ThemeColor, TransparentToolButton
from qfluentwidgets import FluentIcon as FIF

try:
    from .backend_config import backend_url, check_backend_health
    from .UiLoader import resource_path
    from UI.generated.login import Ui_Form
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from app.backend_config import backend_url, check_backend_health
    from app.UiLoader import resource_path
    from UI.generated.login import Ui_Form


USE_FLUENT_BUTTONS = True
if USE_FLUENT_BUTTONS:
    from qfluentwidgets import PushButton


def replace_widget(old: QWidget, new: QWidget):
    parent = old.parentWidget()
    layout = parent.layout()
    if layout is None:
        raise RuntimeError("父控件没有 layout，无法 replaceWidget，请确认 Designer 里用了布局")

    layout.replaceWidget(old, new)
    new.setObjectName(old.objectName())
    old.setParent(None)


class LoginPage(QWidget):
    login_success = pyqtSignal()
    """
    合并版：LoginPage 里同时包含 UI 绑定 + 登录业务逻辑（密码输入/回退/校验）。
    """
    def __init__(self):
        super().__init__()
        ui = Ui_Form()
        ui.setupUi(self)
        self.ui = ui
        self.setWindowIcon(QIcon(resource_path("assets/app.ico")))

        # ===== 业务状态（原 login_logic.py 的内容）=====
        self.max_len = 6
        self.password = ""
        self._pending_login = False
        self._login_delay_ms = 450
        self.backend_url = backend_url()
        self.backend_status_label = None
        self.backend_reconnect_button = None

        # ===== UI 初始化 =====
        self.apply_fluent_dot_style()
        self.setup_window_controls()
        self.setup_backend_status()

        if USE_FLUENT_BUTTONS:
            for i in range(10):
                old = self.findChild(QWidget, f"btn{i}")
                if old:
                    new_btn = PushButton(old.text(), self)
                    replace_widget(old, new_btn)

        back_old = self.findChild(QWidget, "btnBack")
        if back_old:
            new_back = TransparentToolButton(FIF.LEFT_ARROW, self)
            new_back.setFixedSize(back_old.size())
            replace_widget(back_old, new_back)

        # 绑定按钮
        for i in range(10):
            btn = self.findChild(QWidget, f"btn{i}")
            if btn:
                btn.clicked.connect(lambda _, n=i: self.on_digit(n))

        back_btn = self.findChild(QWidget, "btnBack")
        if back_btn:
            back_btn.clicked.connect(self.on_backspace)

        self.update_dots()
        QTimer.singleShot(200, lambda: self.check_backend_connection(show_dialog=True))

        if self.is_complete():
            if self.verify():
                self.login_success.emit()
            else:
                self.password = ""
                self.update_dots()

    # ===== 业务方法 =====
    def verify(self) -> bool:
        """
        TODO: 写你的密码验证规则
        """
        return self.password == "123456"

    def is_complete(self) -> bool:
        return len(self.password) >= self.max_len

    # ===== UI/交互 =====
    def on_digit(self, n: int):
        if self._pending_login:
            return
        if len(self.password) >= self.max_len:
            return
        self.password += str(n)
        self.update_dots()

        # ???6?????
        if self.is_complete():
            if self.verify():
                self._pending_login = True
                self._set_inputs_enabled(False)
                self._play_success_anim()
                QTimer.singleShot(self._login_delay_ms, self._emit_login)
            else:
                self.password = ""
                self.update_dots()
                self._shake_dots()

        # 可选：输入满 6 位自动验证
        # if self.is_complete():
        #     ok = self.verify()
        #     print("login ok?", ok)

    def on_backspace(self):
        if self._pending_login:
            return
        if not self.password:
            return
        self.password = self.password[:-1]
        self.update_dots()

    def _emit_login(self):
        self.login_success.emit()

    def setup_backend_status(self) -> None:
        layout = getattr(self.ui, "verticalLayout_2", None)
        if layout is None:
            return

        panel = QtWidgets.QFrame(self)
        panel.setObjectName("backendStatusPanel")
        panel.setStyleSheet(
            "QFrame#backendStatusPanel {"
            "background: rgba(255, 255, 255, 170);"
            "border: 1px solid rgba(11, 74, 168, 38);"
            "border-radius: 10px;"
            "}"
            "QLabel#backendStatusLabel { color: #0b1a3a; font-size: 12px; }"
        )
        row = QtWidgets.QHBoxLayout(panel)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(8)

        self.backend_status_label = QtWidgets.QLabel(f"后端：{self.backend_url}，检查中...", panel)
        self.backend_status_label.setObjectName("backendStatusLabel")
        self.backend_status_label.setWordWrap(True)
        row.addWidget(self.backend_status_label, 1)

        button_cls = PushButton if USE_FLUENT_BUTTONS else QtWidgets.QPushButton
        self.backend_reconnect_button = button_cls("重新连接", panel)
        self.backend_reconnect_button.setFixedHeight(30)
        self.backend_reconnect_button.clicked.connect(lambda: self.check_backend_connection(show_dialog=True))
        row.addWidget(self.backend_reconnect_button)

        layout.insertWidget(1, panel)

    def check_backend_connection(self, show_dialog: bool = False) -> bool:
        if self.backend_reconnect_button:
            self.backend_reconnect_button.setEnabled(False)
        result = check_backend_health(self.backend_url)
        ok = bool(result.get("ok"))
        if self.backend_status_label:
            if ok:
                mysql_text = "数据库在线" if result.get("mysqlReady") else "数据库未就绪"
                self.backend_status_label.setText(f"后端：{result['url']}，已连接，{mysql_text}")
                self.backend_status_label.setStyleSheet("color: #087f5b; font-size: 12px;")
            else:
                self.backend_status_label.setText(f"后端：{result['url']}，连接失败：{result.get('message')}")
                self.backend_status_label.setStyleSheet("color: #b42318; font-size: 12px;")
        if self.backend_reconnect_button:
            self.backend_reconnect_button.setEnabled(True)
        if show_dialog and not ok:
            QMessageBox.warning(self, "后端连接失败", f"无法连接后端：\n{result['url']}\n\n原因：{result.get('message')}")
        return ok

    def _set_inputs_enabled(self, enabled: bool) -> None:
        for i in range(10):
            btn = self.findChild(QWidget, f"btn{i}")
            if btn:
                btn.setEnabled(enabled)
        back_btn = self.findChild(QWidget, "btnBack")
        if back_btn:
            back_btn.setEnabled(enabled)

    def _shake_dots(self) -> None:
        target = getattr(self.ui, "dotsWrap", None)
        if target is None:
            target = getattr(self.ui, "dotsRow", None)
        if target is None:
            return

        base = target.pos()
        offsets = [QPoint(-6, 0), QPoint(6, 0), QPoint(-4, 0), QPoint(4, 0), QPoint(0, 0)]

        group = QSequentialAnimationGroup(target)
        for off in offsets:
            anim = QPropertyAnimation(target, b"pos", target)
            anim.setDuration(45)
            anim.setEasingCurve(QEasingCurve.InOutSine)
            anim.setStartValue(base)
            anim.setEndValue(base + off)
            group.addAnimation(anim)
        group.start()
        self._shake_anim = group

    def _play_success_anim(self) -> None:
        target = getattr(self.ui, "dotsWrap", None)
        if target is None:
            target = getattr(self.ui, "dotsRow", None)
        if target is None:
            return

        base = target.pos()
        offsets = [QPoint(0, 2), QPoint(0, -1), QPoint(0, 0)]
        group = QSequentialAnimationGroup(target)
        for off in offsets:
            anim = QPropertyAnimation(target, b"pos", target)
            anim.setDuration(90)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(base)
            anim.setEndValue(base + off)
            group.addAnimation(anim)
        group.start()
        self._success_anim = group

    def setup_window_controls(self) -> None:
        # Replace native title bar with Fluent-style buttons
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_StyledBackground, True)

        top_bar = QtWidgets.QFrame(self)
        top_bar.setObjectName("loginTopBar")
        top_bar.setFixedHeight(36)
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(6)
        top_layout.addStretch(1)

        btn_style = (
            "QToolButton {"
            "border-radius: 8px;"
            "border: 1px solid rgba(0, 0, 0, 12);"
            "background-color: rgba(255, 255, 255, 120);"
            "}"
            "QToolButton:hover {"
            "border: 1px solid rgba(0, 0, 0, 22);"
            "background-color: rgba(255, 255, 255, 150);"
            "}"
            "QToolButton:pressed {"
            "background-color: rgba(255, 255, 255, 170);"
            "}"
        )

        self.btnMinWin = TransparentToolButton(FIF.MINIMIZE, top_bar)
        self.btnMinWin.setFixedSize(28, 28)
        self.btnMinWin.setIconSize(QSize(16, 16))
        self.btnMinWin.setStyleSheet(btn_style)
        top_layout.addWidget(self.btnMinWin)

        self.btnMaxWin = TransparentToolButton(FIF.FULL_SCREEN, top_bar)
        self.btnMaxWin.setFixedSize(28, 28)
        self.btnMaxWin.setIconSize(QSize(16, 16))
        self.btnMaxWin.setStyleSheet(btn_style)
        top_layout.addWidget(self.btnMaxWin)

        self.btnCloseWin = TransparentToolButton(FIF.CLOSE, top_bar)
        self.btnCloseWin.setFixedSize(28, 28)
        self.btnCloseWin.setIconSize(QSize(16, 16))
        self.btnCloseWin.setStyleSheet(btn_style)
        top_layout.addWidget(self.btnCloseWin)

        layout = getattr(self.ui, "verticalLayout_2", None)
        if layout is not None:
            layout.insertWidget(0, top_bar)

        self.btnMinWin.clicked.connect(self.showMinimized)
        self.btnMaxWin.clicked.connect(self._toggle_maximize)
        self.btnCloseWin.clicked.connect(self.close)

        top_bar.installEventFilter(self)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def eventFilter(self, obj, event):
        if hasattr(self, "loginTopBar") and obj is self.loginTopBar:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.MouseMove and event.buttons() & Qt.LeftButton:
                if hasattr(self, "_drag_pos"):
                    self.move(event.globalPos() - self._drag_pos)
                return True
        return super().eventFilter(obj, event)

    def apply_fluent_dot_style(self):
        accent = ThemeColor.PRIMARY.color()
        r, g, b, _ = accent.getRgb()

        dot_qss = f"""
        *#dot1, *#dot2, *#dot3, *#dot4, *#dot5, *#dot6 {{
            background: transparent;
            border: 2px solid rgba(0,0,0,90);
            border-radius: 11px;
        }}

        *#dot1[dotState="filled"],
        *#dot2[dotState="filled"],
        *#dot3[dotState="filled"],
        *#dot4[dotState="filled"],
        *#dot5[dotState="filled"],
        *#dot6[dotState="filled"] {{
            background: rgb({r},{g},{b});
            border: 2px solid rgb({r},{g},{b});
            border-radius: 11px;
        }}
        """
        self.setStyleSheet(self.styleSheet() + dot_qss)

    def update_dots(self):
        filled = len(self.password)

        accent = ThemeColor.PRIMARY.color()
        r, g, b, _ = accent.getRgb()

        for i in range(1, 7):
            dot = self.findChild(QWidget, f"dot{i}")
            if not dot:
                continue

            if i <= filled:
                dot.setStyleSheet(f"""
                    background: rgb({r},{g},{b});
                    border: 2px solid rgb({r},{g},{b});
                    border-radius: 11px;
                """)
            else:
                dot.setStyleSheet("""
                    background: transparent;
                    border: 2px solid rgba(0,0,0,90);
                    border-radius: 11px;
                """)
