import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import json

import streamlit as st

from devpilot.config import (
    get_config_summary,
)
from devpilot.history.store import HistoryStore
from devpilot.llm.openrouter import OpenRouterProvider
from devpilot.tools.read_file import ReadFileTool
from devpilot.tools.registry import ToolRegistry
from devpilot.tools.safe_terminal import SafeTerminalTool
from devpilot.tools.search_project import SearchProjectTool
from devpilot.tools.write_file import WriteFileTool

st.set_page_config(
    page_title="DevPilot AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Modern vibrant dark theme
st.markdown(
    """
<style>
    .stApp {
        background: linear-gradient(180deg, #0f1026 0%, #0b0d1f 100%);
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #a78bfa 0%, #60a5fa 50%, #22d3ee 100%);
        background-clip: text;
        -webkit-background-clip: text;
        color: transparent;
        margin-bottom: 0.25rem;
    }
    .subheader {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: -0.5rem;
    }
    .card {
        background: linear-gradient(145deg, rgba(99, 102, 241, 0.18) 0%, rgba(15, 16, 38, 0.8) 100%);
        border: 1px solid rgba(139, 92, 246, 0.45);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.25), inset 0 1px 0 rgba(226, 232, 255, 0.08);
        backdrop-filter: blur(6px);
    }
    .card-alt {
        background: linear-gradient(145deg, rgba(14, 165, 233, 0.16) 0%, rgba(15, 16, 38, 0.8) 100%);
        border: 1px solid rgba(56, 189, 248, 0.45);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        box-shadow: 0 10px 30px rgba(14, 165, 233, 0.22), inset 0 1px 0 rgba(224, 242, 254, 0.08);
    }
    .status-ok { color: #86efac; }
    .status-warn { color: #fde68a; }
    .status-bad { color: #fca5a5; }
    .tool-chip {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        background: rgba(168, 85, 247, 0.25);
        border: 1px solid rgba(192, 132, 252, 0.6);
        color: #e9d5ff;
        font-size: 0.8rem;
        margin-right: 0.35rem;
    }
    .stTextArea textarea, .stTextInput input {
        background: rgba(15, 16, 38, 0.8) !important;
        color: #f1f5f9 !important;
        border: 1px solid rgba(139, 92, 246, 0.5) !important;
        border-radius: 10px !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #8b5cf6 0%, #06b6d4 100%) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(192, 132, 252, 0.7) !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #a78bfa 0%, #22d3ee 100%) !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.35) !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown('<div class="main-header">DevPilot AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subheader">Autonomous AI Developer Agent</div>', unsafe_allow_html=True)
    st.divider()
    cfg = get_config_summary()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"**Model:** {cfg['model']}")
    st.markdown(f"**Workspace:** {cfg['workspace']}")
    st.markdown(
        f"**API Key:** <span class='{'status-ok' if cfg['has_api_key'] else 'status-warn'}'>{'Configured' if cfg['has_api_key'] else 'Missing'}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"**Max Steps:** {cfg['max_steps']}")
    st.markdown(f"**Require Approval:** {'Yes' if cfg['require_approval'] else 'No'}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**Tools**")
    st.markdown("<span class='tool-chip'>read_file</span> <span class='tool-chip'>write_file</span> <span class='tool-chip'>search_project</span> <span class='tool-chip'>safe_terminal</span>", unsafe_allow_html=True)

# State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "task_id" not in st.session_state:
    st.session_state.task_id = None
if "tool_history" not in st.session_state:
    st.session_state.tool_history = []
if "history" not in st.session_state:
    st.session_state.history = HistoryStore()

# Main
col_left, col_right = st.columns([1.1, 0.9])
with col_left:
    st.markdown('<div class="card-alt">', unsafe_allow_html=True)
    st.subheader("New Task")
    task = st.text_area(
        "Describe your task",
        height=110,
        placeholder="Build a feature, fix a bug, write tests...",
    )
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        start = st.button("✨ Generate & Execute", use_container_width=True)
    with c2:
        clear = st.button("Clear", use_container_width=True)
    with c3:
        show_hist = st.button("History", use_container_width=True)
    if clear:
        st.session_state.messages = []
        st.session_state.tool_history = []
        st.session_state.task_id = None
    if show_hist:
        tasks = st.session_state.history.list_tasks(8)
        if tasks:
            for t in tasks:
                with st.expander(f"{t['task_id'][:8]} • {t['status']}"):
                    st.text(t["user_request"])
        else:
            st.info("No history yet")
    if start and task.strip():
        st.session_state.messages = []
        st.session_state.tool_history = []
        tid = st.session_state.history.create_task(task, plan="Planning...", status="PLANNING")
        st.session_state.task_id = tid
        st.session_state.messages.append(("user", task))
        provider = OpenRouterProvider()
        if not provider.api_key:
            msg = "❌ No API key found. Set OPENROUTER_API_KEY in .env to enable LLM responses."
            st.session_state.messages.append(("assistant", msg))
            st.session_state.history.update_task(tid, status="FAILED", final_summary="Missing API key")
        else:
            try:
                registry = ToolRegistry()
                for cls in [ReadFileTool, WriteFileTool, SearchProjectTool, SafeTerminalTool]:
                    registry.register(cls)
                messages = [
                    {"role": "system", "content": "You are DevPilot AI. Think step by step, use tools safely, keep answers concise."},
                    {"role": "user", "content": f"Task: {task}\nTools: {json.dumps(registry.list())}"},
                ]
                resp = provider.generate(messages)
                st.session_state.messages.append(("assistant", resp.content or "Ready."))
                st.session_state.history.update_task(tid, plan=resp.content[:400] if resp.content else "", status="EXECUTING")
                if resp.tool_calls:
                    for tc in resp.tool_calls:
                        fn = tc.get("function", {}) or {}
                        name = fn.get("name") or tc.get("name")
                        args_raw = fn.get("arguments", "{}")
                        try:
                            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                        except Exception:
                            args = {"raw": args_raw}
                        st.session_state.tool_history.append({"tool": name or "unknown", "args": args, "status": "queued"})
            except Exception as e:
                st.session_state.messages.append(("assistant", f"Error: {e}"))
                st.session_state.history.update_task(tid, status="FAILED", final_summary=str(e))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Conversation")
    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(content)
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="card-alt">', unsafe_allow_html=True)
    st.subheader("Tool Timeline")
    if st.session_state.tool_history:
        for i, th in enumerate(st.session_state.tool_history):
            with st.expander(f"{i+1}. {th['tool']}"):
                st.json(th["args"])
                st.caption(th["status"])
    else:
        st.info("No tool calls yet")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Status")
    if st.session_state.task_id:
        t = st.session_state.history.get_task(st.session_state.task_id)
        if t:
            st.markdown(f"**ID:** `{t['task_id'][:10]}`")
            st.markdown(f"**Status:** {t['status']}")
            st.markdown(f"**Plan:** {t['plan'][:180] if t['plan'] else '—'}")
    st.markdown('</div>', unsafe_allow_html=True)
