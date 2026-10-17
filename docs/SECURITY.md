# Security

DevPilot AI treats the model as untrusted input. Safety is enforced by deterministic code, not by prompt instructions.

- **Workspace boundaries** — File operations resolve the target path and reject anything outside `DEVPILOT_WORKSPACE` (`./workspace` by default). `../` traversal and absolute paths outside the root are refused (`tools/read_file.py`, `tools/write_file.py`).
- **Command allowlisting** — `safe_terminal` is deny-by-default: it runs only allowlisted binaries (`python`, `pytest`, `git`, `ls`, `ruff`, …) and Python scripts the agent authored. Destructive commands (`rm`, `del`, `rmdir`, `format`, `diskpart`, `shutdown`, `curl`, `wget`, `powershell`, `sudo`, `dd`, `mkfs`) are hard-denied, and shell metacharacters (`;`, `&&`, `|`, `>`, backticks) are rejected before execution (`tools/safe_terminal.py`). The deny check matches on the filename stem, so `powershell.exe` does not bypass the `powershell` entry. This is enforced regardless of user approval.
- **Approval gate** — Reads (`read_file`, `search_project`) run without prompting. Writes and executions require an explicit `y` at the CLI. The gate fails closed: if no approval callback is attached, the action is denied (`security/permissions.py`, `agent.py`).
- **Argument limits** — File size (`DEVPILOT_MAX_FILE_SIZE`), tool output (`DEVPILOT_MAX_TOOL_OUTPUT`), search results (`DEVPILOT_MAX_SEARCH_RESULTS`), and command timeout (120s) are all bounded.
- **Secret redaction** — Arguments are scrubbed for keys containing `api_key`, `apikey`, `token`, `secret`, `password`, or `authorization` before being written to history (`agent.py:redact_args`). `search_project` skips `.env`, `id_rsa`, and `id_ed25519`.
- **API keys** — The real `.env` is gitignored; only `.env.example` is committed. The key is read from the environment and never logged.
- **No OS sandbox** — `safe_terminal` runs with the host user's privileges. Process isolation (Docker) is listed as future work, not a current guarantee.

Known limitations are documented in [../README.md](../README.md#limitations--future-work).
