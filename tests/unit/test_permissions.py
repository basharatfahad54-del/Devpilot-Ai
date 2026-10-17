from src.devpilot.security.permissions import ApprovalManager


def test_read_does_not_require_approval():
    assert not ApprovalManager().requires_approval("read", "low")


def test_write_create_requires_approval():
    assert ApprovalManager().requires_approval("write_create", "medium")


def test_execute_requires_approval():
    assert ApprovalManager().requires_approval("execute", "medium")


def test_high_risk_always_requires_approval():
    assert ApprovalManager().requires_approval("read", "high")


def test_require_approval_disabled():
    assert not ApprovalManager(require_approval=False).requires_approval("execute", "medium")


def test_approve_and_deny_record_decisions():
    am = ApprovalManager()
    am.request_approval("act-1", {"tool": "write_file"})
    assert am.get_decision("act-1") == "pending"
    am.approve("act-1")
    assert am.get_decision("act-1") == "approved"
