import json
import time
from typing import List, Dict, Any, Tuple, Optional, Callable
import openai
from openai import OpenAI

from .config import Config
from .memory import MemoryManager
from .tools import ToolRegistry, parse_tool_call


class AIAgent:
    """
    Universal Autonomous AI Agent orchestrating inference across multiple LLM providers,
    dynamic tool calls, execution telemetry, and durable memory.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        # Resolve configuration for provider
        self.cfg = Config.get_provider_config(
            provider=provider, model=model, base_url=base_url, api_key=api_key
        )
        Config.validate(
            provider=self.cfg["provider"],
            base_url=self.cfg["base_url"],
            api_key=self.cfg["api_key"],
        )

        self.provider = self.cfg["provider"]
        self.model = self.cfg["model"]
        self.base_url = self.cfg["base_url"]
        self.api_key = self.cfg["api_key"]

        self._init_client()

        self.memory = memory_manager or MemoryManager(Config.MEMORY_FILE)
        self.tools = ToolRegistry()

        # Bind persistent memory tools to the registry
        self.tools.register("remember", self.memory.remember)
        self.tools.register("recall", self.memory.recall)
        self.tools.register("forget", self.memory.forget)

        self.history: List[Dict[str, Any]] = []

        # Execution Telemetry
        self.metrics: Dict[str, Any] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "turns_count": 0,
            "last_latency_seconds": 0.0,
        }

    def _init_client(self) -> None:
        """Initialize or re-initialize OpenAI-compatible client."""
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "local",
            timeout=60.0,
            max_retries=3,
        )

    def switch_provider(
        self,
        provider: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Switch active LLM provider and model on the fly without losing state."""
        self.cfg = Config.get_provider_config(
            provider=provider, model=model, base_url=base_url, api_key=api_key
        )
        Config.validate(
            provider=self.cfg["provider"],
            base_url=self.cfg["base_url"],
            api_key=self.cfg["api_key"],
        )
        self.provider = self.cfg["provider"]
        self.model = self.cfg["model"]
        self.base_url = self.cfg["base_url"]
        self.api_key = self.cfg["api_key"]
        self._init_client()

    def build_system_prompt(self) -> str:
        """Construct dynamic system prompt with registered tool signatures and live memory dump."""
        live_memory = self.memory.recall()
        signatures = self.tools.get_prompt_signatures()
        tool_count = len(self.tools.registered_tools)

        return (
            "You are a professional AI software engineer and autonomous assistant created by Idris (https://github.com/CodeWithIdris). "
            f"You have full access to these {tool_count} system tools: "
            f"{signatures}. "
            "When the user asks you to perform a task, inspect code, run terminal commands, manage files, or manage memories, "
            "reply ONLY with a valid tool call (e.g. recall('') or list_files('.') or run_terminal_command('git status')). "
            f"Do NOT claim you lack access to tools — all {tool_count} tools are fully registered and active in your execution environment. "
            "Current Memory State:\n"
            f"{live_memory}"
        )

    def run_inference(self, max_retries: int = 3) -> Tuple[str, List[Tuple[str, Any]]]:
        """
        Execute chat completion request with API retries, telemetry tracking, and dynamic schemas.
        Returns a tuple: (content_string, list_of_tool_calls_from_api)
        """
        messages = [{"role": "system", "content": self.build_system_prompt()}] + self.history

        last_error = None
        tools_schema = self.tools.get_openai_schemas()
        start_time = time.perf_counter()

        for attempt in range(1, max_retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools_schema if tools_schema else None,
                )
                self.metrics["last_latency_seconds"] = round(time.perf_counter() - start_time, 2)

                # Track token usage if reported by provider
                if hasattr(completion, "usage") and completion.usage:
                    self.metrics["prompt_tokens"] += getattr(completion.usage, "prompt_tokens", 0) or 0
                    self.metrics["completion_tokens"] += getattr(completion.usage, "completion_tokens", 0) or 0
                    self.metrics["total_tokens"] += getattr(completion.usage, "total_tokens", 0) or 0

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
                raise Exception(f"API Request error ({self.provider}/{self.model}): {err}")

        raise Exception(f"API endpoint connection error after {max_retries} attempts: {last_error}")

    def process_turn(
        self,
        user_input: str,
        callback: Optional[Callable[[str, str, Any, str], None]] = None,
        max_steps: int = 15,
    ) -> str:
        """
        Process a user message through the agent tool-execution loop.
        If a callback is provided, it receives status updates (response, tool_name, args, result).
        """
        self.history.append({"role": "user", "content": user_input})
        self.metrics["turns_count"] += 1
        step_count = 0

        while step_count < max_steps:
            step_count += 1
            try:
                content, native_tool_calls = self.run_inference()
            except Exception as err:
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return (
                    f"⚠️ **Connection Error** with provider `{self.provider}` ({self.model}). "
                    f"\n\n*Details*: `{err}`\n\nPlease check your provider configuration or connection."
                )

            # Strategy A: Check OpenAI Native Tool Calls from API
            if native_tool_calls:
                for tool_name, args in native_tool_calls:
                    if self.tools.is_registered(tool_name):
                        result = self.tools.execute(tool_name, args)
                        response_str = content or f"Calling `{tool_name}`..."
                        if callback:
                            callback(response_str, tool_name, args, result)
                        self.history.append({"role": "assistant", "content": response_str})
                        self.history.append({"role": "user", "content": f"Tool result for {tool_name}: {result}"})
                continue

            # Strategy B: Check Parsed Tool Calls from content string (AST / JSON / Markdown)
            tool_name, args = parse_tool_call(content)
            if tool_name and self.tools.is_registered(tool_name):
                result = self.tools.execute(tool_name, args)
                if callback:
                    callback(content, tool_name, args, result)
                self.history.append({"role": "assistant", "content": content})
                self.history.append({"role": "user", "content": f"Tool result for {tool_name}: {result}"})
                continue

            # Strategy C: Explicit User Prompt Fallback Parsing
            # If model hallucinated conversational text refusing to call a tool, parse explicit tool calls directly from user prompt!
            prompt_tool_name, prompt_args = parse_tool_call(user_input)
            if step_count == 1 and prompt_tool_name and self.tools.is_registered(prompt_tool_name):
                result = self.tools.execute(prompt_tool_name, prompt_args)
                fallback_resp = f"Executing requested tool `{prompt_tool_name}`..."
                if callback:
                    callback(fallback_resp, prompt_tool_name, prompt_args, result)
                self.history.append({"role": "assistant", "content": fallback_resp})
                self.history.append({"role": "user", "content": f"Tool result for {prompt_tool_name}: {result}"})
                continue

            # If no tool call detected in any strategy, return final conversational output
            final_response = content or "Task completed."
            self.history.append({"role": "assistant", "content": final_response})
            return final_response

        fallback_msg = "Task completed (maximum tool execution steps reached)."
        self.history.append({"role": "assistant", "content": fallback_msg})
        return fallback_msg

    def clear_history(self) -> None:
        """Clear current conversation history."""
        self.history.clear()
