import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from app.core.ids import new_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    code            TEXT UNIQUE NOT NULL,
    current_item_id TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    position    INTEGER NOT NULL,
    url         TEXT NOT NULL,
    title       TEXT,
    status      TEXT NOT NULL DEFAULT 'queued',
    progress    REAL NOT NULL DEFAULT 0,
    duration    REAL,
    filename    TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_session ON items(session_id, position);
"""

ITEM_FIELDS = {
    "url",
    "title",
    "status",
    "progress",
    "duration",
    "filename",
    "error",
    "position",
}


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_session(self, code: str) -> dict:
        session_id = new_id()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO sessions (id, code, created_at) VALUES (?, ?, ?)",
                (session_id, code, utcnow()),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return _row(row)

    def get_session_by_code(self, code: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE code = ?", (code.upper(),)
            ).fetchone()
        return _row(row)

    def list_sessions(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM sessions").fetchall()
        return [dict(r) for r in rows]

    def set_current_item(self, session_id: str, item_id: str | None) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE sessions SET current_item_id = ? WHERE id = ?",
                (item_id, session_id),
            )

    def add_item(self, session_id: str, url: str, title: str | None = None) -> dict:
        item_id = new_id()
        now = utcnow()
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS pos FROM items "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            conn.execute(
                "INSERT INTO items "
                "(id, session_id, position, url, title, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'queued', ?, ?)",
                (item_id, session_id, row["pos"], url, title, now, now),
            )
        return self.get_item(item_id)

    def get_item(self, item_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM items WHERE id = ?", (item_id,)
            ).fetchone()
        return _row(row)

    def get_items(self, session_id: str) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM items WHERE session_id = ? ORDER BY position",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_item(self, item_id: str, **fields) -> dict | None:
        updates = {k: v for k, v in fields.items() if k in ITEM_FIELDS}
        if not updates:
            return self.get_item(item_id)
        updates["updated_at"] = utcnow()
        assignments = ", ".join(f"{k} = ?" for k in updates)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                f"UPDATE items SET {assignments} WHERE id = ?",
                (*updates.values(), item_id),
            )
        return self.get_item(item_id)

    def delete_item(self, session_id: str, item_id: str) -> bool:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "DELETE FROM items WHERE id = ? AND session_id = ?",
                (item_id, session_id),
            )
        return cur.rowcount > 0

    def reorder_items(self, session_id: str, ordered_ids: list[str]) -> None:
        known = {i["id"] for i in self.get_items(session_id)}
        now = utcnow()
        with closing(self._connect()) as conn, conn:
            for position, item_id in enumerate(ordered_ids):
                if item_id in known:
                    conn.execute(
                        "UPDATE items SET position = ?, updated_at = ? "
                        "WHERE id = ? AND session_id = ?",
                        (position, now, item_id, session_id),
                    )

    def complete_current(self, session_id: str) -> dict | None:
        session = self.get_session(session_id)
        if not session or not session["current_item_id"]:
            return session
        current = self.get_item(session["current_item_id"])
        if not current:
            return session
        self.update_item(current["id"], status="done", progress=1.0)
        items = self.get_items(session_id)
        following = next(
            (i for i in items if i["position"] > current["position"]), None
        )
        self.set_current_item(session_id, following["id"] if following else None)
        return self.get_session(session_id)
