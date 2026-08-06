from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 filename TEXT NOT NULL,
 pipeline_id TEXT,
 fingerprint TEXT NOT NULL,
 status TEXT NOT NULL,
 file_format TEXT,
 row_count INTEGER NOT NULL DEFAULT 0,
 valid_rows INTEGER NOT NULL DEFAULT 0,
 invalid_rows INTEGER NOT NULL DEFAULT 0,
 duplicate_rows INTEGER NOT NULL DEFAULT 0,
 error_count INTEGER NOT NULL DEFAULT 0,
 message TEXT,
 original_path TEXT NOT NULL,
 final_path TEXT,
 created_at TEXT NOT NULL,
 completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
CREATE TABLE IF NOT EXISTS errors(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 file_id INTEGER NOT NULL,
 row_number INTEGER,
 field_name TEXT,
 error_code TEXT NOT NULL,
 message TEXT NOT NULL,
 raw_value TEXT,
 FOREIGN KEY(file_id) REFERENCES files(id)
);
"""

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def connect(path):
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)

def add_file(path, filename, pipeline_id, fingerprint, original_path, file_format=None):
    with connect(path) as conn:
        cur = conn.execute(
            """INSERT INTO files(filename,pipeline_id,fingerprint,status,file_format,original_path,created_at)
               VALUES(?,?,?,'processing',?,?,?)""",
            (filename, pipeline_id, fingerprint, file_format, original_path, now())
        )
        return int(cur.lastrowid)

def finish_file(path, file_id, **values):
    with connect(path) as conn:
        conn.execute(
            """UPDATE files SET status=?,file_format=?,row_count=?,valid_rows=?,invalid_rows=?,
               duplicate_rows=?,error_count=?,message=?,final_path=?,completed_at=? WHERE id=?""",
            (
                values["status"], values.get("file_format"), values.get("row_count",0),
                values.get("valid_rows",0), values.get("invalid_rows",0),
                values.get("duplicate_rows",0), values.get("error_count",0),
                values.get("message",""), values.get("final_path"), now(), file_id
            )
        )

def add_errors(path, file_id, errors):
    if not errors:
        return
    with connect(path) as conn:
        conn.executemany(
            """INSERT INTO errors(file_id,row_number,field_name,error_code,message,raw_value)
               VALUES(?,?,?,?,?,?)""",
            [(file_id,e.get("row_number"),e.get("field_name"),e["error_code"],
              e["message"],None if e.get("raw_value") is None else str(e.get("raw_value")))
             for e in errors]
        )

def accepted_fingerprint(path, fingerprint):
    with connect(path) as conn:
        return conn.execute(
            "SELECT 1 FROM files WHERE fingerprint=? AND status='accepted' LIMIT 1",
            (fingerprint,)
        ).fetchone() is not None

def list_files(path, status=None, query=None, limit=200):
    clauses, params = [], []
    if status:
        clauses.append("status=?"); params.append(status)
    if query:
        clauses.append("(filename LIKE ? OR message LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with connect(path) as conn:
        rows = conn.execute(
            f"SELECT * FROM files {where} ORDER BY id DESC LIMIT ?", params
        ).fetchall()
    return [dict(r) for r in rows]

def get_file(path, file_id):
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["errors"] = [dict(r) for r in conn.execute(
            "SELECT * FROM errors WHERE file_id=? ORDER BY row_number,id", (file_id,)
        ).fetchall()]
        return item

def stats(path):
    with connect(path) as conn:
        total = conn.execute("SELECT COUNT(*) n FROM files").fetchone()["n"]
        accepted = conn.execute("SELECT COUNT(*) n FROM files WHERE status='accepted'").fetchone()["n"]
        quarantined = conn.execute("SELECT COUNT(*) n FROM files WHERE status='quarantined'").fetchone()["n"]
        duplicates = conn.execute("SELECT COUNT(*) n FROM files WHERE status='duplicate'").fetchone()["n"]
        rows = conn.execute("SELECT COALESCE(SUM(row_count),0) n FROM files").fetchone()["n"]
    return {
        "total": int(total), "accepted": int(accepted),
        "quarantined": int(quarantined), "duplicates": int(duplicates),
        "rows": int(rows),
        "success_rate": round(accepted / total * 100, 1) if total else 0.0,
    }

def clear(path):
    with connect(path) as conn:
        conn.execute("DELETE FROM errors")
        conn.execute("DELETE FROM files")
