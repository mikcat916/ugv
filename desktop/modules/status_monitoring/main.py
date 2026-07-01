from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from modules.status_monitoring.pages.rc_monitoring_page import RCMonitoringPage


def create_status_monitoring_page(parent=None) -> RCMonitoringPage:
    return RCMonitoringPage(parent)


def main() -> int:
    app = QApplication(sys.argv)
    page = create_status_monitoring_page()
    page.resize(1080, 720)
    page.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
