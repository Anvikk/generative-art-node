import json
import os
import sqlite3
import threading
from typing import Optional, Dict, Any


_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL,
    source_path TEXT NOT NULL,
    output_path TEXT,
    analysis_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_hash)
);
"""


class StateStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def has_processed(self, file_hash: str) -> bool:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT 1 FROM processed_files WHERE file_hash = ?", (file_hash,))
            return cur.fetchone() is not None

    def record_processed(self, file_hash: str, source_path: str, output_path: Optional[str], analysis: Optional[Dict[str, Any]]) -> None:
        analysis_json = json.dumps(analysis or {}, ensure_ascii=False)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_files(file_hash, source_path, output_path, analysis_json) VALUES(?, ?, ?, ?)",
                (file_hash, source_path, output_path, analysis_json),
            )
            conn.commit()

    def get_record(self, file_hash: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT file_hash, source_path, output_path, analysis_json, created_at FROM processed_files WHERE file_hash = ?",
                (file_hash,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "file_hash": row[0],
                "source_path": row[1],
                "output_path": row[2],
                "analysis": json.loads(row[3] or "{}"),
                "created_at": row[4],
            }