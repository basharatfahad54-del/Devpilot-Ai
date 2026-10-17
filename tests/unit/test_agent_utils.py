from src.devpilot.agent import redact_args


def test_redacts_sensitive_keys():
    out = redact_args({"api_key": "sk-or-v1-abc", "path": "main.py", "nested": {"token": "t"}})
    assert out["api_key"] == "***REDACTED***"
    assert out["nested"]["token"] == "***REDACTED***"
    assert out["path"] == "main.py"


def test_passthrough_when_nothing_sensitive():
    args = {"command": "pytest -q", "path": "a.txt"}
    assert redact_args(args) == args
