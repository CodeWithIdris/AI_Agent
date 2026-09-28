# AI Agent System 🚀

> **"A Zero-Bloat, Multi-Provider Autonomous Coding Agent with Dual CLI & Streamlit Cockpit, Human-in-the-Loop Safety, and Self-Healing Debugging."**

[![CI Status](https://github.com/CodeWithIdris/AI_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/CodeWithIdris/AI_Agent/actions)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)
[![Developer](https://img.shields.io/badge/Developer-CodeWithIdris-purple.svg)](https://github.com/CodeWithIdris)

---

## 🌟 Overview & System Highlights

Most AI Agents on GitHub suffer from heavy framework bloat or vendor lock-in. **AI Agent** is built with zero framework bloat using standard OpenAI-compatible protocol definitions, pure Python stdlib execution tools, and sub-second startup latency.

### 📊 Competitive Comparison Matrix

| Feature | LangChain / CrewAI | AutoGen | Aider | **AI Agent (This Repo)** |
| :--- | :--- | :--- | :--- | :--- |
| **Framework Overhead** | 50+ Heavy Dependencies | Complex Graph Wiring | Heavy CLI package | **Zero-Bloat Core** (<1s startup) |
| **Provider Freedom** | Config-heavy wrappers | OpenAI / Azure focused | Vendor constrained | **Universal Plug-and-Play** (Ollama, Gemini, DeepSeek, Groq, OpenAI, HF) |
| **User Safety** | Blind tool execution | Custom functions required | Git auto-commits | **Human-in-the-Loop Guardrails** (`AUTONOMOUS` vs `CONFIRM_DANGEROUS`) |
| **Self-Correction** | Standard loop | Multi-agent conversation | Chat edit loop | **Autonomous Self-Healing Loop** (`/debug pytest`) |
| **Dual Interface** | CLI or Web | Scripting / Web UI | Terminal CLI | **Dual Cockpit**: Streamlit Web Dashboard & ANSI Terminal CLI |
| **Token Observability** | External loggers | Manual callbacks | Basic summary | **Live Cost ($) & Latency Dashboard** |

---

## 🚀 Concrete Architectural Capabilities

### 🌐 1. Universal Provider Switcher (Local LLMs + Cloud)
Switch seamlessly on the fly between local models and top cloud LLMs via standard OpenAI API format:
- **Local (Offline)**: Ollama (`http://localhost:11434/v1`) with `qwen2.5-coder:7b`, `llama3.1`, etc. (No API key needed!)
- **Google Gemini**: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`
- **DeepSeek**: `deepseek-chat`, `deepseek-coder`
- **Groq Cloud**: `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`
- **OpenAI**: `gpt-4o-mini`, `gpt-4o`, `o3-mini`
- **Hugging Face Router**: `Qwen/Qwen3.8-27B`, `Qwen2.5-Coder-32B-Instruct`

### 🛡️ 2. Human-in-the-Loop Safety & Guardrails Mode
Prevent unintended terminal executions or destructive file edits with execution safety modes:
- `AUTONOMOUS`: Standard mode for rapid prototyping and tool execution.
- `CONFIRM_DANGEROUS`: Prompts user before executing terminal commands (`run_terminal_command`) or modifying files (`edit_file`, `delete_file`, `create_file`).

### 🩺 3. Autonomous Self-Healing Code & Debugger (`auto_debug`)
High-level diagnostic tool that runs your workspace test suite (`pytest`), extracts structured tracebacks, reads failing files, applies AST patches, and verifies fixes iteratively until green.

### 💰 4. Token & Cost Observability Dashboard
Real-time token usage telemetry tracking prompt tokens, completion tokens, total tokens, model pricing conversion ($ USD), and turn latency metrics displayed directly in the Streamlit metric cards and CLI `/tokens` command.

---

## 📁 Repository Architecture

```text
AI_Agent/
├── .github/
│   └── workflows/
│       └── ci.yml            # Multi-version Python GitHub Actions CI runner
├── ai_agent/                 # Main Production Package
│   ├── __init__.py           # Package exports & version metadata
│   ├── config.py             # Centralized environment, provider & pricing config
│   ├── memory.py             # Durable JSON Memory Manager
│   ├── agent.py              # Core AIAgent orchestrator, safety & LLM loop
│   ├── cli.py                # Interactive ANSI terminal CLI runner
│   └── tools/                # Modular Tool Registry & Implementations
│       ├── __init__.py       # Tool Registry manager & schema generator
│       ├── file_ops.py       # File system operations (read, list, edit)
│       ├── code_ops.py       # Code operations (create_file, search_files)
│       ├── system_ops.py     # System commands (run_terminal_command)
│       ├── debug_ops.py      # Pytest failure parsing & diagnostic test runner
│       └── parser.py         # AST parser for LLM tool calls
├── tests/                    # Comprehensive Pytest Suite
│   ├── test_agent.py         # Agent orchestrator unit tests
│   ├── test_debug.py         # Diagnostic parser and self-healing tests
│   ├── test_memory.py        # Durable memory manager tests
│   ├── test_parser.py        # AST tool parser unit tests
│   ├── test_safety.py        # Guardrails safety mode & cost metric tests
│   └── test_tools.py         # Tool registry and I/O execution tests
├── app.py                    # Streamlit Web Application Frontend Cockpit
├── main.py                   # CLI Entrypoint Script
├── pyproject.toml            # Package metadata & pytest configuration
├── requirements.txt          # Production & dev dependencies
└── README.md                 # System Documentation
```

---

## ⚡ Quick Start Guide

### 1. Clone & Install

```bash
git clone https://github.com/CodeWithIdris/AI_Agent.git
cd AI_Agent
pip install -e .[dev]
```

### 2. Configure Environment (Optional)

Create a `.env` file in the project root:

```env
# Cloud API Tokens (Ollama requires no token)
HF_TOKEN=your_huggingface_api_token_here
GEMINI_API_KEY=your_gemini_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Default Settings
AGENT_PROVIDER=huggingface
AGENT_MODEL=Qwen/Qwen3.8-27B
AGENT_SAFETY_MODE=AUTONOMOUS
```

### 3. Launch Streamlit Web Cockpit

```bash
python -m streamlit run app.py
```

### 4. Launch Interactive Terminal CLI

```bash
python main.py
```

---

## 🛠️ Built-in Tool Signature Reference

| Tool Signature | Description |
| :--- | :--- |
| `run_terminal_command(command)` | Safe execution of terminal shell commands (`python`, `pip`, `git`, etc.). |
| `run_tests_with_diagnostics(command='pytest')` | Executes test suite, extracts tracebacks, and reports line failures. |
| `search_files(keyword, path='.')` | Searches workspace codebase files for string patterns (grep). |
| `create_file(path, content)` | Creates a new file at specified path with given content. |
| `list_files(path='.')` | Lists directory structure with `[DIR]` and `[FILE]` indicators. |
| `read_file(path, start_line=1, end_line=None)` | Reads text content safely with line pagination & binary protection. |
| `edit_file(path, old_str, new_str)` | Replaces text in a file or creates a new file if missing. |
| `delete_file(path)` | Safely removes a file from the workspace. |
| `remember(key, value)` | Stores a key-value pair in persistent memory. |
| `recall(key='')` | Retrieves a specific memory or dumps all stored memories. |
| `forget(key)` | Deletes a key-value pair from persistent memory. |

---

## 🖥️ Interactive CLI Slash Commands

| Command | Purpose |
| :--- | :--- |
| `/help` | Displays available CLI slash commands. |
| `/mode [AUTONOMOUS\|CONFIRM_DANGEROUS]` | View or toggle execution guardrails mode. |
| `/debug [command]` | Triggers autonomous self-healing debugger loop on test suite. |
| `/provider [name]` | View active LLM provider or switch (e.g. `/provider gemini`). |
| `/model [name]` | View or switch active model on the fly. |
| `/tokens` | Display token usage, estimated USD cost, and turn latency telemetry. |
| `/memory` | View stored durable key-value memory state. |
| `/clear` | Reset current conversation turn history. |
| `/exit` | Exit the CLI session. |

---

## 🧪 Verification & Testing

Run the full pytest suite to verify system integrity:

```bash
pytest
```

---

## 👨‍💻 Author & Maintained By

* **Developer**: [CodeWithIdris](https://github.com/CodeWithIdris)
* **Repository**: [https://github.com/CodeWithIdris/AI_Agent](https://github.com/CodeWithIdris/AI_Agent)

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.