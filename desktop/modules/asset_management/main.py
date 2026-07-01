# -*- coding: utf-8 -*-
"""
设备基本信息管理系统
应用程序入口
"""

import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

try:
    # Preferred path when used as a submodule in the UAV project.
    from modules.asset_management.app.database import DeviceDatabase
    from modules.asset_management.app.main_window import MainWindow
except ImportError:
    # Fallback for direct execution inside this module folder.
    from app.database import DeviceDatabase
    from app.main_window import MainWindow


DEFAULT_MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "device_management",
}


def _load_mysql_config() -> dict:
    """从环境变量读取 MySQL 配置，未设置时使用默认值。"""
    config = dict(DEFAULT_MYSQL_CONFIG)
    config["host"] = os.getenv("MYSQL_HOST", config["host"])
    config["user"] = os.getenv("MYSQL_USER", config["user"])
    config["password"] = os.getenv("MYSQL_PASSWORD", config["password"])
    config["database"] = os.getenv("MYSQL_DATABASE", config["database"])

    port_str = os.getenv("MYSQL_PORT")
    if port_str:
        try:
            config["port"] = int(port_str)
        except ValueError:
            pass

    return config


def _request_mysql_password(config: dict) -> str:
    """弹窗请求 MySQL 密码。"""
    tip = (
        f"请输入 MySQL 用户 {config['user']} 的密码\n"
        f"主机: {config['host']}:{config['port']}\n"
        f"数据库: {config['database']}"
    )
    password, ok = QInputDialog.getText(
        None,
        "MySQL 密码",
        tip,
        QLineEdit.Password,
    )
    return password if ok else ""


def _create_database(config: dict) -> DeviceDatabase:
    """创建数据库连接；若未提供密码导致鉴权失败，则引导输入密码并重试一次。"""
    try:
        return DeviceDatabase(**config)
    except Exception as first_error:
        err_msg = str(first_error)
        no_password = not config.get("password")
        access_denied = "Access denied for user" in err_msg
        using_no_password = "using password: NO" in err_msg

        if no_password and access_denied and using_no_password:
            retry_password = _request_mysql_password(config)
            if retry_password:
                retry_config = dict(config)
                retry_config["password"] = retry_password
                return DeviceDatabase(**retry_config)

        raise


def create_asset_management_window() -> MainWindow:
    """Create AssetManagement main window for embedding into another app."""
    mysql_config = _load_mysql_config()
    db = _create_database(mysql_config)
    return MainWindow(db)


def main():
    """主函数"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("设备信息管理系统")
    app.setFont(QFont("Microsoft YaHei", 9))

    try:
        window = create_asset_management_window()
    except Exception as e:
        mysql_config = _load_mysql_config()
        has_password = "是" if mysql_config.get("password") else "否"
        QMessageBox.critical(
            None,
            "数据库连接失败",
            "无法连接 MySQL 数据库，请检查配置：\n\n"
            f"主机: {mysql_config['host']}\n"
            f"端口: {mysql_config['port']}\n"
            f"用户: {mysql_config['user']}\n"
            f"数据库: {mysql_config['database']}\n"
            f"已配置密码: {has_password}\n\n"
            f"错误信息: {e}",
        )
        return 1

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
