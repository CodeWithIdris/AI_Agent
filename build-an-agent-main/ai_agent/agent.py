import json
import time
from typing import List, Dict, Any, Tuple
import openai
from openai import OpenAI

from .config import Config
from .memory import MemoryManager
from .tools import ToolRegistry, parse_tool_call


OPENAI_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Return a newline-separated listing of files and directories at path.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Return the text contents of a file at the given path.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace the first occurrence of old_str with new_str in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_str": {"type": "string"},
                    "new_str": {"type": "string"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file at specified path with content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for a keyword pattern across files in directory (grep).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute a shell command locally in workspace.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Store a durable memory value under key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Return one remembered value or all stored memories.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string", "default": ""}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget",
            "description": "Remove a durable memory value by key.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
    },
]


class AIAgent:
    """Core autonomous AI Agent orchestrating inference, tool calls, and durable memory."""

    def __init__(self, model: str = None, memory_manager: MemoryManager = None):
        Config.validate()
        self.model = model or Config.DEFAULT_MODEL
        self.client = OpenAI(
            base_url=Config.BASE_URL,
            api_key=Config.API_KEY,
            timeout=45.0,
            max_retries=3,
        )
        self.memory = memory_manager or MemoryManager(Config.MEMORY_FILE)
        self.tools = ToolRegistry()

        # Bind memory tools to registry
        self.tools.register("remember", self.memory.remember)
        self.tools.register("recall", self.memory.recall)
        self.tools.register("forget", self.memory.forget)

        self.history: List[Dict[str, str]] = []

    def build_system_prompt(self) -> str:
        """Construct dynamic system prompt with tool signatures and live memory dump."""
        live_memory = self.memory.recall()
        return (
            "You are a professional AI software engineer and autonomous assistant created by Idris (https://github.com/CodeWithIdris). "
            "You have full access to these system tools: "
            "list_files(path='.'), read_file(path), edit_file(path, old_str, new_str), "
            "create_file(path, content), search_files(keyword, path='.'), "
            "run_terminal_command(command), remember(key, value), recall(key=''), forget(key). "
            "When the user asks you to perform a task, inspect code, run terminal commands, or manage memories, "
            "reply ONLY with a valid tool call (e.g. recall('') or list_files('.') or run_terminal_command('git status')). "
            "Do NOT claim you lack access to tools — all 9 tools are fully registered and active in your execution environment. "
            "Current Memory State:\n"
            f"{live_memory}"
        )

    def run_inference(self, max_retries: int = 3) -> Tuple[str, List[Tuple[str, Any]]]:
        """
        Execute chat completion request with API retries.
        Returns a tuple: (content_string, list_of_tool_calls_from_api)
        """
        messages = [{"role": "system", "content": self.build_system_prompt()}] + self.history

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=OPENAI_TOOLS_SCHEMA,
                )
                msg = completion.choices[0].message
                content = (msg.content or "").strip()

                native_tool_calls = []
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        try:
                            tool_args = json.loads(tc.function.arguments)
                        except Exception:
                            tool_args = []
                        native_tool_calls.append((tool_name, tool_args))

                return content, native_tool_calls

            except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as err:
                last_error = err
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)
            except Exception as err:
                raise Exception(f"API Request error: {err}")

        raise Exception(f"API endpoint connection error after {max_retries} attempts: {last_error}")

    def process_turn(self, user_input: str, callback=None, max_steps: int = 15) -> str:
        """
        Process a user message through the agent tool-execution loop.
        If a callback is provided, it receives status updates (response, tool_name, args, result).
        """
        self.history.append({"role": "user", "content": user_input})
        step_count = 0

        while step_count < max_steps:
            step_count += 1
            try:
                content, native_tool_calls = self.run_inference()
            except Exception as err:
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return (
                    "⚠️ **Connection Error**: Unable to establish a connection with the Hugging Face API router. "
                    f"\n\n*Details*: `{err}`\n\nPlease try again."
                )

            # Strategy A: Check OpenAI Native Tool Calls from API
            if native_tool_calls:
                for tool_name, args in native_tool_calls:
                    if self.tools.is_registered(tool_name):
                        result = self.tools.execute(tool_name, args)
                        response_str = content or f"Calling `{tool_name}`..."
                        if callback:
                            callback(response_str, tool_name, args if isinstance(args, list) else [args], result)
                        self.history.append({"role": "assistant", "content": response_str})
                        self.history.append({"role": "user", "content": f"Tool result for {tool_name}: {result}"})
                continue

            # Strategy B: Check Parsed Tool Calls from content string (AST / JSON / Markdown)
            tool_name, args = parse_tool_call(content)
            if tool_name and self.tools.is_registered(tool_name):
                result = self.tools.execute(tool_name, args)
                if callback:
                    callback(content, tool_name, args if isinstance(args, list) else [args], result)
                self.history.append({"role": "assistant", "content": content})
                self.history.append({"role": "user", "content": f"Tool result for {tool_name}: {result}"})
                continue

            # Strategy C: Explicit User Prompt Fallback Parsing
            # If model hallucinated and returned text refusing to call a tool, parse explicit tool calls directly from user prompt!
            prompt_tool_name, prompt_args = parse_tool_call(user_input)
            if step_count == 1 and prompt_tool_name and self.tools.is_registered(prompt_tool_name):
                result = self.tools.execute(prompt_tool_name, prompt_args)
                fallback_resp = f"Executing requested tool `{prompt_tool_name}`..."
                if callback:
                    callback(fallback_resp, prompt_tool_name, prompt_args if isinstance(prompt_args, list) else [prompt_args], result)
                self.history.append({"role": "assistant", "content": fallback_resp})
                self.history.append({"role": "user", "content": f"Tool result for {prompt_tool_name}: {result}"})
                continue

            # If no tool call detected in any strategy, return final conversational output
            final_response = content or "Task completed."
            self.history.append({"role": "assistant", "content": final_response})
            return final_response

        fallback_msg = "Task completed."
        self.history.append({"role": "assistant", "content": fallback_msg})
        return fallback_msg

    def clear_history(self) -> None:
        """Clear current conversation history."""
        self.history.clear()
