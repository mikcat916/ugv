from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget
import random
from pathlib import Path


class ContentPage(QWidget):
    def __init__(self, ui_path=None):
        super().__init__()

        # 默认就加载同目录下的 content.ui（最稳）
        if ui_path is None:
            ui_path = Path(__file__).resolve().parent / "content.ui"
        else:
            ui_path = Path(ui_path).resolve()

        uic.loadUi(str(ui_path), self)

        # Apply GlassFrame style to the four panels
        try:
            from Beautify.control_content_widgets.glass_frame import GlassFrame
        except Exception:
            GlassFrame = None

        if GlassFrame:
            for name in ["frameVideo", "frameMap", "frameDriveInfo", "frameEStop"]:
                old = getattr(self, name, None)
                if not old:
                    continue
                new = GlassFrame(self)
                new.setObjectName(old.objectName())
                layout = old.parentWidget().layout()
                if layout:
                    layout.replaceWidget(old, new)
                    old.setParent(None)

        self._t = QTimer(self)
        self._t.timeout.connect(self._mock_update)
        self._t.start(200)

    def _mock_update(self):
        if hasattr(self, "speedBarPlaceholder"):
            self.speedBarPlaceholder.setValue(random.randint(0, 100))
        if hasattr(self, "batteryBarPlaceholder"):
            self.batteryBarPlaceholder.setValue(random.randint(0, 100))

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
from UI.content import Ui_Form   # 这里导入你的 content.py 生成的 Ui_Form


class ContentPage(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # 这句执行完，btnUp/btnDown... 才存在

        self.apply_dpad_style()   # ✅ 就在这里调用

    def apply_dpad_style(self):
        qss = """
        QPushButton#btnUp, QPushButton#btnDown, QPushButton#btnLeft, QPushButton#btnRight {
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 170);
            background-color: rgba(255, 255, 255, 120);
            padding: 0px;
        }
        QPushButton#btnUp:hover, QPushButton#btnDown:hover, QPushButton#btnLeft:hover, QPushButton#btnRight:hover {
            background-color: rgba(255, 255, 255, 160);
            border: 1px solid rgba(255, 255, 255, 220);
        }
        QPushButton#btnUp:pressed, QPushButton#btnDown:pressed, QPushButton#btnLeft:pressed, QPushButton#btnRight:pressed {
            background-color: rgba(255, 255, 255, 190);
            padding-top: 2px;
        }
        """
        self.setStyleSheet(self.styleSheet() + "\n" + qss)

        for btn in (self.btnUp, self.btnDown, self.btnLeft, self.btnRight):
            shadow = QGraphicsDropShadowEffect(btn)
            shadow.setBlurRadius(25)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 45))
            btn.setGraphicsEffect(shadow)

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
from UI.content import Ui_Form   # 这里导入你的 content.py 生成的 Ui_Form


class ContentPage(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # 这句执行完，btnUp/btnDown... 才存在

        self.apply_dpad_style()   # ✅ 就在这里调用

    def apply_dpad_style(self):
        qss = """
        QPushButton#btnUp, QPushButton#btnDown, QPushButton#btnLeft, QPushButton#btnRight {
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 170);
            background-color: rgba(255, 255, 255, 120);
            padding: 0px;
        }
        QPushButton#btnUp:hover, QPushButton#btnDown:hover, QPushButton#btnLeft:hover, QPushButton#btnRight:hover {
            background-color: rgba(255, 255, 255, 160);
            border: 1px solid rgba(255, 255, 255, 220);
        }
        QPushButton#btnUp:pressed, QPushButton#btnDown:pressed, QPushButton#btnLeft:pressed, QPushButton#btnRight:pressed {
            background-color: rgba(255, 255, 255, 190);
            padding-top: 2px;
        }
        """
        for btn in (self.btnUp, self.btnDown, self.btnLeft, self.btnRight):
            btn.setStyleSheet(qss)
            shadow = QGraphicsDropShadowEffect(btn)
            shadow.setBlurRadius(25)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 45))
            btn.setGraphicsEffect(shadow)