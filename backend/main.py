from __future__ import annotations

# Keep the public import path stable for `uvicorn main:app` while the actual
# FastAPI application and route registration live in app_core.py.
from app_core import *  # noqa: F401,F403
