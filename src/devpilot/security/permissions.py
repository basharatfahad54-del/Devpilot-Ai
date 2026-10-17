from enum import Enum
from typing import Any, Dict


class PermissionLevel(Enum):
    READ = "read"
    WRITE_CREATE = "write_create"
    WRITE_OVERWRITE = "write_overwrite"
    EXECUTE = "execute"
    INSTALL = "install"
    DESTRUCTIVE = "destructive"


# Anything at or above these levels changes state on disk or the system,
# so it must pass the approval gate. Pure reads never do.
APPROVAL_REQUIRED = {
    PermissionLevel.WRITE_CREATE.value,
    PermissionLevel.WRITE_OVERWRITE.value,
    PermissionLevel.EXECUTE.value,
    PermissionLevel.INSTALL.value,
    PermissionLevel.DESTRUCTIVE.value,
}


class ApprovalManager:
    def __init__(self, require_approval: bool = True):
        self.require_approval = require_approval
        self.pending = {}
        self.decisions = {}

    def requires_approval(self, permission: str, risk_level: str) -> bool:
        if not self.require_approval:
            return False
        if risk_level == "high":
            return True
        return permission in APPROVAL_REQUIRED

    def request_approval(self, action_id: str, details: Dict[str, Any]) -> bool:
        self.pending[action_id] = details
        return False

    def approve(self, action_id: str) -> None:
        if action_id in self.pending:
            self.decisions[action_id] = "approved"
            del self.pending[action_id]

    def deny(self, action_id: str) -> None:
        if action_id in self.pending:
            self.decisions[action_id] = "denied"
            del self.pending[action_id]

    def get_decision(self, action_id: str) -> str:
        return self.decisions.get(action_id, "pending")
