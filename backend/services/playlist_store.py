"""
Playlist Store - SQLite persistence for the user's playback queue.
"""

import os
import sqlite3
from typing import List, Dict

from config import PROJECT_ROOT

_DB_DIR = PROJECT_ROOT / "memory" / "data"
_DB_PATH = _DB_DIR / "playlist.db"


def _get_conn() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_playlist_db() -> None:
    """Create the playlist table if it doesn't exist."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS playlist (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT DEFAULT '',
                url TEXT DEFAULT '',
                filename TEXT DEFAULT '',
                bvid TEXT DEFAULT '',
                duration TEXT DEFAULT '',
                sub_dir TEXT DEFAULT '',
                position INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_playlist() -> List[Dict]:
    """Return all playlist tracks ordered by position."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM playlist ORDER BY position").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def set_playlist(tracks: List[Dict]) -> None:
    """Replace the entire playlist with the given tracks."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM playlist")
        for i, t in enumerate(tracks):
            conn.execute(
                """
                INSERT INTO playlist (id, title, author, url, filename, bvid, duration, sub_dir, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t.get("id", ""),
                    t.get("title", ""),
                    t.get("author", ""),
                    t.get("url", ""),
                    t.get("filename", ""),
                    t.get("bvid", ""),
                    t.get("duration", ""),
                    t.get("subDir", t.get("sub_dir", "")),
                    i,
                ),
            )
        conn.commit()
    finally:
        conn.close()
