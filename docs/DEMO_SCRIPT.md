# Demo Script

A 2–3 minute recording that exercises the full loop and every safety control.

1. Show config (`.env.example`) and confirm `.env` is not committed.
2. Run the happy path — plan, a free read, an approved write:
   ```bash
   python cli.py run "Read demo_input.txt, then create a file named greeting.txt with exactly the same content"
   ```
   Point out: the LLM-generated plan, the green `read_file` (no prompt), the yellow permission prompt, and the green `write_file` after approving with `y`.
3. Run the safety path — the model attempts a blocked command:
   ```bash
   python cli.py run "Use the safe_terminal tool to fetch https://example.com with curl" --yes
   ```
   Point out: red `blocked` lines from the allowlist (approval cannot override it) and how the model recovers and explains the policy.
4. Run the audit trail:
   ```bash
   python cli.py history
   python cli.py inspect <task_id>
   ```
   Point out: status, per-tool status, approval decision, and timing stored in SQLite.
5. Run the tests (no API key required):
   ```bash
   pytest -q
   ```
6. Optional: the Streamlit dashboard for a visual view.
   ```bash
   streamlit run app.py
   ```
