import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent
WORKSPACE_DIR = Path(os.getenv("DEVPILOT_WORKSPACE", BASE_DIR / "workspace")).resolve()
LOG_LEVEL = os.getenv("DEVPILOT_LOG_LEVEL", "INFO").upper()
MAX_STEPS = int(os.getenv("DEVPILOT_MAX_STEPS", "10"))
REQUIRE_APPROVAL = os.getenv("DEVPILOT_REQUIRE_APPROVAL", "true").lower() == "true"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Limits
MAX_RESPONSE_SIZE = int(os.getenv("DEVPILOT_MAX_RESPONSE_SIZE", "10000"))
MAX_TOOL_OUTPUT = int(os.getenv("DEVPILOT_MAX_TOOL_OUTPUT", "5000"))
MAX_FILE_SIZE = int(os.getenv("DEVPILOT_MAX_FILE_SIZE", "1048576"))  # 1MB
MAX_SEARCH_RESULTS = int(os.getenv("DEVPILOT_MAX_SEARCH_RESULTS", "100"))
REQUEST_TIMEOUT = int(os.getenv("DEVPILOT_REQUEST_TIMEOUT", "30"))
RETRY_ATTEMPTS = int(os.getenv("DEVPILOT_RETRY_ATTEMPTS", "3"))
RETRY_BACKOFF = float(os.getenv("DEVPILOT_RETRY_BACKOFF", "0.5"))


def ensure_workspace() -> Path:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_DIR


def get_config_summary() -> dict:
    return {
        "workspace": str(WORKSPACE_DIR),
        "model": OPENROUTER_MODEL,
        "has_api_key": bool(OPENROUTER_API_KEY),
        "max_steps": MAX_STEPS,
        "require_approval": REQUIRE_APPROVAL,
        "log_level": LOG_LEVEL,
    }
