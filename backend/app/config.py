"""
Null — Backend Configuration

Environment variables (loaded from .env or Docker environment):
  XCPNG_MANAGER_SECRET  — JWT signing secret (required for multi-user auth)
  XCPNG_DB_PATH         — SQLite database path (default: /opt/data/xcpng-gui/data/null.db)
  XCPNG_DEFAULT_POOL    — Default pool host:port (optional)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings:
    # ── Security ──────────────────────────────────────────────────────
    secret_key: str = os.getenv(
        "XCPNG_MANAGER_SECRET",
        "change-me-in-production-use-a-strong-random-secret",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(
        os.getenv("XCPNG_TOKEN_EXPIRE", "480")  # 8 hours
    )

    # ── Database ──────────────────────────────────────────────────────
    db_path: str = os.getenv(
        "XCPNG_DB_PATH",
        str(BASE_DIR / "data" / "null.db"),
    )

    # ── CORS ──────────────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
    ]

    # ── Server ────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
