from __future__ import annotations

# Compatibility shim: some modules still import `app.ui_loader`.
from .UiLoader import load_ui, resource_path

__all__ = ["resource_path", "load_ui"]
