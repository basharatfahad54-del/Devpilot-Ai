from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    status: str
    result: str
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    approval_decision: Optional[str] = None


class TaskRecord(BaseModel):
    task_id: str
    user_request: str
    plan: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    final_summary: Optional[str] = None
    tool_calls: list[ToolCallRecord] = []
