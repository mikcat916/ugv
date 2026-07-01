from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from modules.sensor_data.pages.sensor_data_page import SensorDataPage


def create_sensor_data_page(parent=None) -> SensorDataPage:
    return SensorDataPage(parent)


def main() -> int:
    app = QApplication(sys.argv)
    page = create_sensor_data_page()
    page.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
