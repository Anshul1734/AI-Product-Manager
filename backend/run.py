"""
Entry point for the refactored AI Product Manager application.
"""
from pathlib import Path

import uvicorn

from dotenv import load_dotenv

# Load backend/.env BEFORE importing settings (Settings() instantiates at import time)
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)

from app.core import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
