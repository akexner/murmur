"""SQLite history. Audio files are the source of truth; rows only point to them."""
import sqlite3
import threading
import time

from . import paths

COLUMNS = ["id", "created", "duration", "status", "path", "text", "raw", "model", "lang",
           "starred", "error", "trashed", "trashed_at", "trash_path", "note"]


class Store:
    def __init__(self):
        self._lock = threading.RLock()
        self._db = sqlite3.connect(paths.db_path(), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("""CREATE TABLE IF NOT EXISTS recs(
            id TEXT PRIMARY KEY, created REAL, duration REAL DEFAULT 0, status TEXT,
            path TEXT DEFAULT '', text TEXT DEFAULT '', raw TEXT DEFAULT '', model TEXT DEFAULT '',
            lang TEXT DEFAULT '', starred INTEGER DEFAULT 0, error TEXT DEFAULT '',
            trashed INTEGER DEFAULT 0, trashed_at REAL DEFAULT 0, trash_path TEXT DEFAULT '',
            note TEXT DEFAULT '')""")
        self._db.commit()

    def create(self, rid, path, status="recording"):
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO recs(id,created,status,path) VALUES(?,?,?,?)",
                             (rid, time.time(), status, path))
            self._db.commit()

    def update(self, rid, **kw):
        if not kw:
            return
        for k in kw:
            if k not in COLUMNS:
                raise KeyError(k)
        with self._lock:
            sets = ",".join(f"{k}=?" for k in kw)
            self._db.execute(f"UPDATE recs SET {sets} WHERE id=?", (*kw.values(), rid))
            self._db.commit()

    def get(self, rid):
        with self._lock:
            r = self._db.execute("SELECT * FROM recs WHERE id=?", (rid,)).fetchone()
            return dict(r) if r else None

    def delete(self, rid):
        with self._lock:
            self._db.execute("DELETE FROM recs WHERE id=?", (rid,))
            self._db.commit()

    def list(self, q="", trashed=False, attention=False, limit=300):
        sql = "SELECT * FROM recs WHERE trashed=?"
        args = [1 if trashed else 0]
        if q:
            sql += " AND text LIKE ?"
            args.append(f"%{q}%")
        if attention:
            sql += " AND status IN ('pending','failed','transcribing','recording','empty')"
        sql += " ORDER BY created DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            return [dict(r) for r in self._db.execute(sql, args).fetchall()]

    def by_status(self, *statuses):
        marks = ",".join("?" * len(statuses))
        with self._lock:
            return [dict(r) for r in self._db.execute(
                f"SELECT * FROM recs WHERE status IN ({marks}) ORDER BY created", statuses).fetchall()]

    def expired_candidates(self, older_than):
        with self._lock:
            return [dict(r) for r in self._db.execute(
                "SELECT * FROM recs WHERE status IN ('done','empty') AND starred=0 AND trashed=0 "
                "AND path!='' AND created<?", (older_than,)).fetchall()]

    def purgeable(self, trashed_before):
        with self._lock:
            return [dict(r) for r in self._db.execute(
                "SELECT * FROM recs WHERE trash_path!='' AND trashed_at<?", (trashed_before,)).fetchall()]

    def attention_count(self):
        with self._lock:
            return self._db.execute(
                "SELECT COUNT(*) FROM recs WHERE trashed=0 AND status IN ('pending','failed','empty')"
            ).fetchone()[0]
