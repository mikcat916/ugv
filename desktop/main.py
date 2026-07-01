# main.py
from __future__ import annotations

import sys


def _import_runtime():
    try:
        from PyQt5.QtCore import QCoreApplication, Qt
        from PyQt5.QtWidgets import QApplication
        from app.login import LoginPage
        from app.MainInterface import MainInterface
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        package = missing.split(".")[0]
        hints = {
            "PyQt5": "pip install PyQt5 PyQtWebEngine",
            "qfluentwidgets": "pip install PyQt-Fluent-Widgets",
            "pymysql": "pip install pymysql",
            "mysql": "pip install mysql-connector-python",
        }
        hint = hints.get(package, f"pip install {package}")
        print(
            "Application startup failed: missing dependency "
            f"`{missing}`.\n"
            "Activate the correct environment, then install dependencies with:\n"
            "  pip install -r requirements.txt\n"
            f"Or install the missing package directly with:\n  {hint}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    return QCoreApplication, Qt, QApplication, LoginPage, MainInterface


def main() -> int:
    QCoreApplication, Qt, QApplication, LoginPage, MainInterface = _import_runtime()

    # Required for QtWebEngine widgets (set before QApplication is created)
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    login = LoginPage()
    main_win = MainInterface()

    def open_main():
        login.close()
        main_win.show()

    login.login_success.connect(open_main)
    login.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
