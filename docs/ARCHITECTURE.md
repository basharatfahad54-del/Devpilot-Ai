# Architecture

DevPilot AI is a modular agent: a provider-agnostic LLM client, a registry of sandboxed tools, a deterministic permission gate, and a persistent history store, all driven by a single agent loop.

## Modules

- `config.py` — Environment/config (workspace root, model, limits, approval toggle)
- `agent.py` — The agent loop, permission gating, secret redaction, event hooks
- `planner.py` — Plan generation via the LLM with a deterministic fallback
- `llm/` — Provider abstraction and the OpenRouter client (retries, error mapping)
- `tools/` — `read_file`, `write_file`, `search_project`, `safe_terminal`, and the registry
- `security/permissions.py` — Approval policy (reads free; writes/executes gated)
- `history/` — SQLite store for tasks and tool calls
- `ui/` — Streamlit presentation helpers

## Agent loop

```
User request
   │
   ▼
Plan (LLM) ──► messages = [system, user: task + plan]
   │
   ▼
 ┌─────────────────────────────── iteration (≤ DEVPILOT_MAX_STEPS) ─────────────────────────────┐
 │  LLM(messages, tools)                                                                         │
 │     ├─ plain text  ──► final summary ──► status COMPLETED ──► stop                            │
 │     └─ tool_call(s)                                                                           │
 │            ├─ permission gate (write/execute) ──► denied ──► tell model, continue             │
 │            ├─ allowlist/validation ──► blocked ──► tell model, continue                       │
 │            ├─ execute tool in workspace                                                       │
 │            ├─ append result to messages                                                       │
 │            └─ log tool call to SQLite (status, ms, redacted args, approval decision)          │
 └───────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
Summary / FAILED state
```

Key invariants:

- The LLM never touches the disk or shell directly; it can only *propose* tool calls.
- The workspace boundary and shell allowlist are enforced in the tools, independent of approval.
- The approval gate fails closed: no callback means deny.
- History is written between the gate and the next iteration, so a crash leaves a valid audit trail.
