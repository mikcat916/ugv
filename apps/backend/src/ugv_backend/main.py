from __future__ import annotations

# Keep the ASGI entrypoint small while the FastAPI application and route
# registration live in app_core.py.
from .app_core import *  # noqa: F401,F403
