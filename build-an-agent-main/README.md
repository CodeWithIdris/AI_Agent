# AI Agent System 🚀

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/Developer-CodeWithIdris-purple.svg)](https://github.com/CodeWithIdris)

A production-grade, modular, and extensible **Autonomous AI Agent System** built in Python. Designed to inspect, read, and edit local files while maintaining durable key-value memory across sessions.

Developed and maintained by **[CodeWithIdris](https://github.com/CodeWithIdris)**.

---

## 🌟 Key Features

* 🛠️ **Modular Tool Ecosystem**: Extensible registry supporting file system navigation, editing, and durable memory tools.
* 🧠 **Durable Memory Persistence**: Automatic JSON memory persistence (`.agent-memory.json`) for user preferences and facts across sessions.
* ⚡ **Safe AST Tool Parser**: Parses Python-style tool calls and cleans markdown code block fences reliably.
* 🔒 **Crash-Proof Execution**: Comprehensive error handling for file I/O, binary file protection, UTF-8 safety, and invalid API payload prevention.
* 💻 **Interactive CLI Interface**: ANSI-colored terminal interface with built-in commands (`/help`, `/memory`, `/clear`, `/exit`).

---

## 📁 Repository Architecture

```text
AI_Agent/
├── ai_agent/                 # Main Production Package
│   ├── __init__.py           # Package exports & metadata
│   ├── config.py             # Centralized environment & model configuration
│   ├── memory.py             # Durable JSON Memory Manager
│   ├── agent.py              # Core AIAgent orchestrator & LLM loop
│   ├── cli.py                # Interactive CLI runner
│   └── tools/                # Modular Tool Registry & Implementations
│       ├── __init__.py       # Tool Registry manager
│       ├── file_ops.py       # File system operations (read, list, edit)
│       └── parser.py         # AST parser for LLM tool calls
├── main.py                   # Production Entrypoint Script
├── pyproject.toml            # Project configuration & package metadata
├── requirements.txt          # Python dependencies
└── README.md                 # System Documentation
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/CodeWithIdris/AI_Agent.git
cd AI_Agent
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
HF_TOKEN=your_huggingface_api_token_here
AGENT_MODEL=Qwen/Qwen3.8-27B
```

### 3. Run the AI Agent System

```bash
python main.py
```

---

## 🛠️ Built-in Tools

| Tool Signature | Description |
| :--- | :--- |
| `list_files(path='.')` | Lists directory contents with `[DIR]` and `[FILE]` indicators. |
| `read_file(path)` | Reads text content safely with UTF-8 encoding & binary protection. |
| `edit_file(path, old_str, new_str)` | Replaces text in a file or creates a new file if missing. |
| `remember(key, value)` | Stores a key-value pair in persistent memory. |
| `recall(key='')` | Retrieves a specific memory or dumps all stored memories. |
| `forget(key)` | Deletes a key-value pair from persistent memory. |

---

## 🎮 CLI Commands

During an interactive session, you can run:

* `/memory` — Display current durable memory state.
* `/clear`  — Clear current conversation history.
* `/help`   — Show available commands.
* `/exit`   — Exit the CLI runner safely.

---

## 👨‍💻 Developer & Author

* **Author**: [CodeWithIdris](https://github.com/CodeWithIdris)
* **GitHub**: [https://github.com/CodeWithIdris](https://github.com/CodeWithIdris)

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.