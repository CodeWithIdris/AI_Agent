import json
from pathlib import Path
import streamlit as st

from ai_agent.agent import AIAgent
from ai_agent.config import Config
from ai_agent.tools.file_ops import list_files, read_file
from ai_agent.tools.code_ops import search_files

# Page Configuration
st.set_page_config(
    page_title="AI Agent - CodeWithIdris",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "agent" not in st.session_state:
    try:
        st.session_state.agent = AIAgent()
    except Exception as err:
        st.error(f"Initialization Error: {err}")
        st.stop()

agent: AIAgent = st.session_state.agent
memories_dict = agent.memory.load()


# Sidebar Command Center
with st.sidebar:
    st.title("🤖 AI Agent")
    st.markdown("Created by **[CodeWithIdris](https://github.com/CodeWithIdris)**")
    st.caption(f"Model: `{Config.DEFAULT_MODEL}`")
    st.divider()

    # Navigation Tabs
    tab_memory, tab_search, tab_files, tab_tools = st.tabs(["🧠 Memory", "🔍 Search", "📁 Files", "🛠️ Tools"])

    # Tab 1: Memory Manager
    with tab_memory:
        st.caption("Durable Key-Value Memories")
        if memories_dict:
            st.json(memories_dict)
            st.download_button(
                "📥 Export JSON",
                data=json.dumps(memories_dict, indent=2),
                file_name="agent-memory.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.info("No durable memories stored yet.")

        st.divider()
        st.markdown("**Add Memory**")
        with st.form("add_mem_form", clear_on_submit=True):
            k = st.text_input("Key", placeholder="e.g. user_preference")
            v = st.text_input("Value", placeholder="e.g. prefers Python")
            if st.form_submit_button("Save Memory", use_container_width=True) and k and v:
                agent.memory.remember(k, v)
                st.success(f"Saved: {k}")
                st.rerun()

        if memories_dict:
            st.markdown("**Delete Memory**")
            del_k = st.selectbox("Select key to delete", options=list(memories_dict.keys()))
            if st.button("Delete Key", use_container_width=True):
                agent.memory.forget(del_k)
                st.warning(f"Deleted '{del_k}'")
                st.rerun()

    # Tab 2: Code Search / Grep
    with tab_search:
        st.caption("Search across codebase files")
        query = st.text_input("Keyword", placeholder="e.g. AIAgent")
        if st.button("Search Code", use_container_width=True):
            if query:
                res = search_files(query, ".")
                st.text_area("Results", value=res, height=300)
            else:
                st.warning("Please enter a keyword.")

    # Tab 3: File Explorer
    with tab_files:
        st.caption("Workspace File Viewer")
        tree = list_files(".")
        st.text_area("Workspace Tree", value=tree, height=140, disabled=True)

        st.divider()
        inspect_file = st.text_input("File path", placeholder="e.g. main.py or README.md")
        if st.button("View Source", use_container_width=True):
            if inspect_file:
                content = read_file(inspect_file)
                ext = Path(inspect_file).suffix.lstrip(".") or "text"
                st.code(content, language=ext)
            else:
                st.warning("Please enter a file path.")

    # Tab 4: Available Tools
    with tab_tools:
        st.caption("9 Registered System Tools")
        signatures = [
            "run_terminal_command(command)",
            "search_files(keyword, path='.')",
            "create_file(path, content)",
            "read_file(path)",
            "list_files(path='.')",
            "edit_file(path, old_str, new_str)",
            "remember(key, value)",
            "recall(key='')",
            "forget(key)",
        ]
        for sig in signatures:
            st.code(sig, language="python")

    st.divider()
    if st.button("🧹 Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        agent.clear_history()
        st.rerun()


# Main View Header
st.title("🤖 AI Agent Assistant")
st.caption("Autonomous Coding & Workspace Assistant powered by Qwen-27B")

# Stat Metrics Row
m1, m2, m3, m4 = st.columns(4)
m1.metric("Active Model", "Qwen-27B")
m2.metric("Available Tools", "9 Tools")
m3.metric("Durable Memories", f"{len(memories_dict)} Items")
m4.metric("Session Messages", f"{len(st.session_state.messages)}")

st.divider()

# Quick Prompt Action Chips
st.markdown("**Quick Actions:**")
q1, q2, q3, q4 = st.columns(4)

with q1:
    if st.button("List Workspace Files", use_container_width=True):
        st.session_state.pending_prompt = "List all files in the current workspace directory using list_files('.')"
with q2:
    if st.button(" Run Git Status", use_container_width=True):
        st.session_state.pending_prompt = "Run the terminal command 'git status' using run_terminal_command('git status')"
with q3:
    if st.button(" Search for AIAgent", use_container_width=True):
        st.session_state.pending_prompt = "Search the codebase for 'AIAgent' using search_files('AIAgent')"
with q4:
    if st.button(" Recall Memories", use_container_width=True):
        st.session_state.pending_prompt = "Recall all stored memories using recall('')"

st.markdown("")

# Render Chat Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                with st.expander(f" Tool Call: `{tc['name']}`"):
                    st.write(f"**Arguments**: `{tc['args']}`")
                    st.code(tc["result"], language="text")


# Prompt Handling
user_input = st.chat_input("Ask the AI Agent to run commands, edit files, search code, or remember facts...")

if st.session_state.pending_prompt:
    user_input = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        turn_tools = []

        def ui_callback(response: str, tool_name: str, args: list, result: str):
            turn_tools.append({"name": tool_name, "args": args, "result": result})
            with st.status(f"Executing `{tool_name}`...", expanded=False) as status:
                st.write(f"**Arguments**: `{args}`")
                st.code(result, language="text")
                status.update(label=f"Executed `{tool_name}`", state="complete")

        with st.spinner("Agent thinking..."):
            try:
                final_response = agent.process_turn(user_input, callback=ui_callback)
                st.markdown(final_response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_response,
                    "tool_calls": turn_tools,
                })
                st.rerun()
            except Exception as err:
                st.error(f"Error processing request: {err}")
