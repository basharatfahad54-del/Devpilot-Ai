import tempfile
from pathlib import Path

from src.devpilot.history.store import HistoryStore


def test_history_persistence():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        store = HistoryStore(db)
        tid = store.create_task("test request")
        assert tid
        task = store.get_task(tid)
        assert task is not None
        assert task["user_request"] == "test request"
        tasks = store.list_tasks()
        assert len(tasks) >= 1
