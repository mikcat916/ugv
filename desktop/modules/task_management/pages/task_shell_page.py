import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from qfluentwidgets import FluentIcon as FIF, ThemeColor

from modules.task_management.pages.taskmanagement_page import TaskManagementPage
from modules.task_management.pages.hover_cruise_page import HoverCruisePage
from modules.task_management.pages.target_recognition_page import TargetRecognitionPage
from modules.task_management.pages.target_tracking_page import TargetTrackingPage
from modules.task_management.pages.autonomous_exploration_page import AutonomousExplorationPage
from modules.task_management.pages.intelligent_obstacle_avoidance_page import IntelligentObstacleAvoidancePage


class TaskShellPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskShellPage")

        if parent:
            self.resize(parent.size())
            self.setMinimumSize(parent.size())

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        self._build_ui()
        self._apply_styles()
        self._bind_nav()

        self._show_page("map")

    def _build_ui(self) -> None:
        self.rootLayout = QtWidgets.QVBoxLayout(self)
        self.rootLayout.setContentsMargins(14, 14, 14, 14)
        self.rootLayout.setSpacing(12)

        self.titleBar = QtWidgets.QFrame(self)
        self.titleBarLayout = QtWidgets.QHBoxLayout(self.titleBar)
        self.titleBarLayout.setContentsMargins(10, 6, 10, 6)
        self.titleBarLayout.setSpacing(10)

        self.btnBack = QtWidgets.QToolButton(self.titleBar)
        self.btnBack.setMinimumSize(40, 40)
        self.titleBarLayout.addWidget(self.btnBack)
        self.titleBarLayout.addStretch(1)
        self.lblTitle = QtWidgets.QLabel(self.titleBar)
        self.lblTitle.setAlignment(Qt.AlignCenter)
        self.lblTitle.setText("\u4efb\u52a1\u6267\u884c\u7ba1\u7406")
        self.titleBarLayout.addWidget(self.lblTitle)
        self.titleBarLayout.addStretch(1)
        self.btnMax = QtWidgets.QToolButton(self.titleBar)
        self.btnMax.setMinimumSize(40, 40)
        self.titleBarLayout.addWidget(self.btnMax)
        self.btnClose = QtWidgets.QToolButton(self.titleBar)
        self.btnClose.setMinimumSize(40, 40)
        self.titleBarLayout.addWidget(self.btnClose)

        self.rootLayout.addWidget(self.titleBar)

        self.bodyLayout = QtWidgets.QHBoxLayout()
        self.bodyLayout.setContentsMargins(0, 0, 0, 0)
        self.bodyLayout.setSpacing(14)

        self.sideBar = QtWidgets.QFrame(self)
        self.sideBarLayout = QtWidgets.QVBoxLayout(self.sideBar)
        self.sideBarLayout.setContentsMargins(10, 10, 10, 10)
        self.sideBarLayout.setSpacing(10)

        self.btnMapBuild = QtWidgets.QPushButton("\u5730\u56fe\u6784\u5efa", self.sideBar)
        self.btnPatrol = QtWidgets.QPushButton("\u5b9a\u70b9\u5de1\u822a", self.sideBar)
        self.btnDetect = QtWidgets.QPushButton("\u76ee\u6807\u8bc6\u522b", self.sideBar)
        self.btnTrack = QtWidgets.QPushButton("\u76ee\u6807\u8ddf\u8e2a", self.sideBar)
        self.btnExplore = QtWidgets.QPushButton("\u81ea\u4e3b\u63a2\u7d22", self.sideBar)
        self.btnAvoid = QtWidgets.QPushButton("\u667a\u80fd\u907f\u969c", self.sideBar)
        self.btnAirGround = QtWidgets.QPushButton("\u7a7a\u5730\u534f\u540c", self.sideBar)
        self.btnHumanMachine = QtWidgets.QPushButton("\u4eba\u673a\u534f\u540c", self.sideBar)

        for btn in [
            self.btnMapBuild,
            self.btnPatrol,
            self.btnDetect,
            self.btnTrack,
            self.btnExplore,
            self.btnAvoid,
            self.btnAirGround,
            self.btnHumanMachine,
        ]:
            btn.setMinimumSize(0, 48)
            btn.setMaximumHeight(48)
            self.sideBarLayout.addWidget(btn)

        self.sideBarLayout.addStretch(1)
        self.bodyLayout.addWidget(self.sideBar)

        self.stack = QtWidgets.QStackedWidget(self)
        self.page_map = TaskManagementPage(self.stack, embedded=True)
        self.page_patrol = HoverCruisePage(self.stack, embedded=True)
        self.page_detect = TargetRecognitionPage(self.stack, embedded=True)
        self.page_track = TargetTrackingPage(self.stack, embedded=True)
        self.page_explore = AutonomousExplorationPage(self.stack, embedded=True)
        self.page_avoid = IntelligentObstacleAvoidancePage(self.stack, embedded=True)
        self.stack.addWidget(self.page_map)
        self.stack.addWidget(self.page_patrol)
        self.stack.addWidget(self.page_detect)
        self.stack.addWidget(self.page_track)
        self.stack.addWidget(self.page_explore)
        self.stack.addWidget(self.page_avoid)
        self.bodyLayout.addWidget(self.stack, 1)

        self.rootLayout.addLayout(self.bodyLayout)

    def _apply_styles(self) -> None:
        accent = ThemeColor.PRIMARY.color()
        r, g, b, _ = accent.getRgb()
        self.setStyleSheet(
            """
            QWidget#TaskShellPage {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f3f8ff,
                    stop:0.5 #f6f7fb,
                    stop:1 #f1f1f1
                );
                border: none;
            }
            QWidget {
                border: none;
            }
            """
        )

        self.titleBar.setStyleSheet(
            "QFrame {"
            "background: rgba(255, 255, 255, 160);"
            "border-radius: 12px;"
            "}"
        )
        self.lblTitle.setStyleSheet("color: #5f6b7a; font-size: 13px; font-weight: 600;")

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
        self.btnBack.setIcon(FIF.LEFT_ARROW.icon(accent))
        self.btnBack.setIconSize(QSize(18, 18))
        self.btnBack.setStyleSheet(btn_style)
        self.btnMax.setIcon(FIF.FULL_SCREEN.icon(accent))
        self.btnMax.setIconSize(QSize(18, 18))
        self.btnMax.setStyleSheet(btn_style)
        self.btnClose.setIcon(FIF.CLOSE.icon(accent))
        self.btnClose.setIconSize(QSize(18, 18))
        self.btnClose.setStyleSheet(btn_style)

        self.sideBar.setStyleSheet(
            "QFrame {"
            "background: rgba(255, 255, 255, 150);"
            "border-radius: 16px;"
            "}"
        )
        shadow = QGraphicsDropShadowEffect(self.sideBar)
        shadow.setBlurRadius(26)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.sideBar.setGraphicsEffect(shadow)

        self._side_default_qss = """
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

        for btn in self._all_nav_buttons():
            btn.setStyleSheet(self._side_default_qss)

    def _bind_nav(self) -> None:
        self.btnClose.clicked.connect(self.close)
        self.btnMax.clicked.connect(self._toggle_maximize)
        self.btnBack.clicked.connect(self.close)

        self.btnMapBuild.clicked.connect(lambda: self._show_page("map"))
        self.btnPatrol.clicked.connect(lambda: self._show_page("patrol"))
        self.btnDetect.clicked.connect(lambda: self._show_page("detect"))
        self.btnTrack.clicked.connect(lambda: self._show_page("track"))
        self.btnExplore.clicked.connect(lambda: self._show_page("explore"))
        self.btnAvoid.clicked.connect(lambda: self._show_page("avoid"))

    def _all_nav_buttons(self):
        return [
            self.btnMapBuild,
            self.btnPatrol,
            self.btnDetect,
            self.btnTrack,
            self.btnExplore,
            self.btnAvoid,
            self.btnAirGround,
            self.btnHumanMachine,
        ]

    def _show_page(self, key: str) -> None:
        if key == "map":
            self.stack.setCurrentWidget(self.page_map)
            self._set_active_btn(self.btnMapBuild)
        elif key == "patrol":
            self.stack.setCurrentWidget(self.page_patrol)
            self._set_active_btn(self.btnPatrol)
        elif key == "detect":
            self.stack.setCurrentWidget(self.page_detect)
            self._set_active_btn(self.btnDetect)
        elif key == "track":
            self.stack.setCurrentWidget(self.page_track)
            self._set_active_btn(self.btnTrack)
        elif key == "explore":
            self.stack.setCurrentWidget(self.page_explore)
            self._set_active_btn(self.btnExplore)
        elif key == "avoid":
            self.stack.setCurrentWidget(self.page_avoid)
            self._set_active_btn(self.btnAvoid)

    def _set_active_btn(self, active_btn) -> None:
        for btn in self._all_nav_buttons():
            btn.setStyleSheet(self._side_active_qss if btn is active_btn else self._side_default_qss)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

