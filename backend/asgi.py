"""
Single ASGI entrypoint for every deployment target.

Vercel (`@vercel/python`), Render, Fly, and local uvicorn all load `app` from
this module, so there is exactly one production code path.

The sys.path insertion is what makes `from app.main import app` resolve in a
monorepo: Vercel executes this file with the repository root as the working
directory, so `backend/` is not importable by default.

Local:  uvicorn asgi:app --reload --port 8001   (from the backend/ directory)
Render: uvicorn asgi:app --host 0.0.0.0 --port $PORT
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

__all__ = ["app"]
