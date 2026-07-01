from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from modules.basic_control.pages.content_page import ContentPage


def create_basic_control_page(parent=None) -> ContentPage:
    """Factory used by the main shell to open basic control page."""
    return ContentPage(parent)


def main() -> int:
    app = QApplication(sys.argv)
    page = create_basic_control_page()
    page.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
