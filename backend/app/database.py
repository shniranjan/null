"""
Null — SQLite Database Layer

Schema:
  users          — local user accounts and hashed passwords
  pools          — saved XCP-ng pool connection profiles
  audit_log      — immutable record of every management action
  user_prefs     — key-value per-user preferences
  notifications  — acknowledged/dismissed system messages
"""

import sqlite3
import os
from datetime import datetime, timezone
from app.config import settings


def get_db() -> sqlite3.Connection:
    """Return a connection to the SQLite database with WAL mode and foreign keys."""
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist. Idempotent — safe to call on every startup."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password_hash TEXT  NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'admin',
            created_at  TEXT    NOT NULL,
            last_login  TEXT
        );

        CREATE TABLE IF NOT EXISTS pools (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            host        TEXT    NOT NULL,
            port        INTEGER NOT NULL DEFAULT 443,
            verify_ssl  INTEGER NOT NULL DEFAULT 0,
            username    TEXT    NOT NULL DEFAULT 'root',
            password_enc TEXT   NOT NULL DEFAULT '',
            last_connected TEXT,
            status      TEXT    DEFAULT 'disconnected'
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            username    TEXT    NOT NULL,
            pool_id     INTEGER,
            pool_name   TEXT,
            action      TEXT    NOT NULL,
            target_type TEXT,
            target_name TEXT,
            target_ref  TEXT,
            details     TEXT,
            timestamp   TEXT    NOT NULL,
            FOREIGN KEY (user_id)  REFERENCES users(id),
            FOREIGN KEY (pool_id)  REFERENCES pools(id)
        );

        CREATE TABLE IF NOT EXISTS user_prefs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            key         TEXT    NOT NULL,
            value       TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, key)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            xapi_message_ref TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()
