import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import BASE_DIR

HISTORY_DB = BASE_DIR / "devpilot_history.db"


class HistoryStore:
    def __init__(self, db_path: Path = HISTORY_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    user_request TEXT NOT NULL,
                    plan TEXT,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    final_summary TEXT
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    duration_ms INTEGER,
                    approval_decision TEXT,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                )"""
            )

    def create_task(self, user_request: str, plan: str = "", status: str = "IDLE") -> str:
        task_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, user_request, plan, status, start_time) VALUES (?, ?, ?, ?, ?)",
                (task_id, user_request, plan, status, datetime.utcnow().isoformat()),
            )
        return task_id

    def update_task(self, task_id: str, **kwargs):
        if not kwargs:
            return
        fields = []
        values = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            values.append(v if not isinstance(v, datetime) else v.isoformat())
        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE task_id = ?"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, values)

    def add_tool_call(self, task_id: str, tool_name: str, arguments: Dict[str, Any],
                      status: str, result: str = "", error: Optional[str] = None,
                      duration_ms: Optional[int] = None, approval_decision: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO tool_calls (task_id, tool_name, arguments, status, result, error, duration_ms, approval_decision)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, tool_name, json.dumps(arguments), status, result[:10000], 
                 (error[:5000] if error else None), duration_ms, approval_decision),
            )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            if not task:
                return None
            tools = conn.execute("SELECT * FROM tool_calls WHERE task_id = ? ORDER BY id", (task_id,)).fetchall()
            return {
                **dict(task),
                "tool_calls": [dict(t) for t in tools],
            }

    def list_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks ORDER BY start_time DESC LIMIT ?", (limit,))
            tasks = cursor.fetchall()
            return [dict(t) for t in tasks]
