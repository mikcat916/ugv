# -*- coding: utf-8 -*-
"""Shared styles for AssetManagement module."""

MAIN_STYLE = """
QMainWindow {
    background-color: #eef3fb;
}

QFrame#rootFrame {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #f7fbff,
        stop:1 #edf2fb
    );
    border: 1px solid rgba(0, 0, 0, 14);
    border-radius: 14px;
}

QFrame#titleBar {
    background: rgba(255, 255, 255, 210);
    border: 1px solid rgba(0, 0, 0, 12);
    border-radius: 12px;
}

QLabel#titleLabel {
    color: #1f2d3d;
    font-size: 14px;
    font-weight: 600;
}

QToolButton#titleBtn, QToolButton#titleBtnClose {
    border-radius: 8px;
    border: 1px solid #72d5ff;
    background: rgba(255, 255, 255, 220);
}

QToolButton#titleBtn:hover, QToolButton#titleBtnClose:hover {
    background: rgba(114, 213, 255, 40);
}

QToolButton#titleBtnClose:hover {
    border-color: #ff8a8a;
    background: rgba(255, 122, 122, 36);
}

QLineEdit#searchEdit {
    background: #ffffff;
    border: 1px solid #c8d6e5;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 18px;
    font-size: 13px;
}

QLineEdit#searchEdit:focus {
    border: 1px solid #72d5ff;
}

QTableWidget {
    background: #ffffff;
    border: 1px solid #dbe7f5;
    border-radius: 10px;
    gridline-color: #edf2fa;
    selection-background-color: #eaf5ff;
    selection-color: #12324d;
    font-size: 13px;
}

QTableWidget::item {
    padding: 9px 8px;
}

QHeaderView::section {
    background: #f6f9ff;
    color: #2f3a46;
    border: none;
    border-right: 1px solid #e8eef8;
    border-bottom: 1px solid #dbe7f5;
    padding: 10px 8px;
    font-size: 13px;
    font-weight: 600;
}

QHeaderView::section:last {
    border-right: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 2px;
}

QScrollBar::handle:vertical {
    background: #c4d4e9;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #9fb8d8;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px 2px 4px;
}

QScrollBar::handle:horizontal {
    background: #c4d4e9;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #9fb8d8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    width: 0;
    height: 0;
}

QStatusBar {
    background: rgba(255, 255, 255, 220);
    border-top: 1px solid #dbe7f5;
    color: #44556b;
    font-size: 12px;
    padding-left: 10px;
}

QMessageBox {
    background-color: #ffffff;
}
"""


DIALOG_STYLE = """
QDialog {
    background-color: #f7fbff;
}

QLabel {
    color: #44556b;
    font-size: 13px;
}

QLabel#titleLabel {
    color: #1f2d3d;
    font-size: 16px;
    font-weight: 600;
    padding: 10px 0;
}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateTimeEdit, QTextEdit {
    border: 1px solid #c8d6e5;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    background-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateTimeEdit:focus, QTextEdit:focus {
    border-color: #72d5ff;
}

QPushButton {
    border: 1px solid #72d5ff;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    background: rgba(255, 255, 255, 220);
}

QPushButton:hover {
    background: rgba(114, 213, 255, 38);
}

QPushButton#saveBtn {
    background: #2d7dff;
    border: none;
    color: white;
}

QPushButton#saveBtn:hover {
    background: #4b90ff;
}

QPushButton#cancelBtn {
    border: 1px solid #c8d6e5;
}

QGroupBox {
    font-size: 14px;
    font-weight: 600;
    color: #1f2d3d;
    border: 1px solid #dbe7f5;
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
"""
