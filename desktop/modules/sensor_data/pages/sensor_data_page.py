from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class SensorDataPage(QWidget):
    """Placeholder page for future sensor data module UI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        label = QLabel("Sensor data module UI is not implemented yet.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
