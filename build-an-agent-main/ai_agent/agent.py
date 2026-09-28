import os
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

    DANGEROUS_TOOLS = {"run_terminal_command", "edit_file", "delete_file", "create_file"}

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        safety_mode: Optional[str] = None,
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
        self.safety_mode = (safety_mode or os.getenv("AGENT_SAFETY_MODE", "AUTONOMOUS")).upper()

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
            "estimated_cost_usd": 0.0,
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

                # Track token usage and cost if reported by provider
                if hasattr(completion, "usage") and completion.usage:
                    p_tok = getattr(completion.usage, "prompt_tokens", 0) or 0
                    c_tok = getattr(completion.usage, "completion_tokens", 0) or 0
                    self.metrics["prompt_tokens"] += p_tok
                    self.metrics["completion_tokens"] += c_tok
                    self.metrics["total_tokens"] += (p_tok + c_tok)
                    self.metrics["estimated_cost_usd"] = Config.calculate_cost(
                        self.model, self.metrics["prompt_tokens"], self.metrics["completion_tokens"]
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
                raise Exception(f"API Request error ({self.provider}/{self.model}): {err}")

        raise Exception(f"API endpoint connection error after {max_retries} attempts: {last_error}")

    def _execute_tool_with_safety(
        self,
        tool_name: str,
        args: Any,
        approval_hook: Optional[Callable[[str, Any], bool]] = None,
    ) -> str:
        """Execute tool if registered and authorized by current safety mode."""
        if tool_name in self.DANGEROUS_TOOLS and self.safety_mode == "CONFIRM_DANGEROUS":
            approved = False
            if approval_hook:
                try:
                    approved = approval_hook(tool_name, args)
                except Exception:
                    approved = False
            if not approved:
                return f"⚠️ Security Intercept: Execution of tool '{tool_name}' was REJECTED by user in CONFIRM_DANGEROUS mode."

        # Automatic checkpoint snapshot before mutating file tools
        if tool_name in ("edit_file", "delete_file", "create_file"):
            target_file = None
            if isinstance(args, (list, tuple)) and args:
                target_file = str(args[0])
            elif isinstance(args, dict):
                target_file = str(args.get("path") or args.get("file_path", ""))
            from .tools.git_ops import create_checkpoint
            create_checkpoint(target_file, description=f"Auto-checkpoint before {tool_name}")

        return self.tools.execute(tool_name, args)


    def process_turn(
        self,
        user_input: str,
        callback: Optional[Callable[[str, str, Any, str], None]] = None,
        approval_hook: Optional[Callable[[str, Any], bool]] = None,
        max_steps: int = 15,
    ) -> str:
        """
        Process a user message through the agent tool-execution loop.
        If a callback is provided, it receives status updates (response, tool_name, args, result).
        If approval_hook is provided, it intercepts dangerous tool calls when in CONFIRM_DANGEROUS mode.
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
                        result = self._execute_tool_with_safety(tool_name, args, approval_hook=approval_hook)
                        response_str = content or f"Calling `{tool_name}`..."
                        if callback:
                            callback(response_str, tool_name, args, result)
                        self.history.append({"role": "assistant", "content": response_str})
                        self.history.append({"role": "user", "content": f"Tool result for {tool_name}: {result}"})
                continue

            # Strategy B: Check Parsed Tool Calls from content string (AST / JSON / Markdown)
            tool_name, args = parse_tool_call(content)
            if tool_name and self.tools.is_registered(tool_name):
                result = self._execute_tool_with_safety(tool_name, args, approval_hook=approval_hook)
                if callback:
                    callback(content, tool_name, args, result)
                self.history.append({"role": "assistant", "content": content})
                self.history.append({"role": "user", "content": f"Tool result for {tool_name}: {result}"})
                continue

            # Strategy C: Explicit User Prompt Fallback Parsing
            # If model hallucinated conversational text refusing to call a tool, parse explicit tool calls directly from user prompt!
            prompt_tool_name, prompt_args = parse_tool_call(user_input)
            if step_count == 1 and prompt_tool_name and self.tools.is_registered(prompt_tool_name):
                result = self._execute_tool_with_safety(prompt_tool_name, prompt_args, approval_hook=approval_hook)
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

    def auto_debug(
        self,
        command: str = "pytest",
        max_iterations: int = 3,
        callback: Optional[Callable[[str, str, Any, str], None]] = None,
    ) -> str:
        """
        Autonomous self-healing loop:
        1. Runs test diagnostics.
        2. If failing, feeds the diagnostics to the agent with instructions to read, edit, and fix the bug.
        3. Repeats until tests pass or max iterations reached.
        """
        from .tools.debug_ops import run_tests_with_diagnostics

        initial_diag = run_tests_with_diagnostics(command)
        if "✅ SUCCESS" in initial_diag:
            return f"🎉 Tests are already passing!\n\n{initial_diag}"

        repair_log = [f"🩺 **Autonomous Debugger started for `{command}`**:\n\n{initial_diag}"]
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            prompt = (
                f"AUTONOMOUS SELF-HEALING DEBUGGER (Attempt {iteration}/{max_iterations}):\n"
                f"The test suite command `{command}` failed with the following diagnostic report:\n"
                f"{initial_diag}\n\n"
                "Please inspect the failing source code using `read_file`, locate the root cause, "
                "and apply the exact correction using `edit_file`."
            )

            # Process the repair turn
            agent_response = self.process_turn(prompt, callback=callback, max_steps=8)
            repair_log.append(f"**Attempt {iteration} Action:**\n{agent_response}")

            # Re-run diagnostics
            check_diag = run_tests_with_diagnostics(command)
            if "✅ SUCCESS" in check_diag:
                repair_log.append(f"\n🎉 **Self-Healing Succeeded on Attempt {iteration}!**\n{check_diag}")
                return "\n\n---\n\n".join(repair_log)
            else:
                initial_diag = check_diag

        repair_log.append(
            f"\n⚠️ **Self-Healing reached maximum attempts ({max_iterations})**. Remaining issues:\n{initial_diag}"
        )
        return "\n\n---\n\n".join(repair_log)

    def clear_history(self) -> None:
        """Clear current conversation history."""
        self.history.clear()

    def undo(self) -> str:
        """Undo last file modification by restoring previous checkpoint."""
        from .tools.git_ops import undo_last_change
        return undo_last_change()

    def diff(self) -> str:
        """Get current workspace git diff."""
        from .tools.git_ops import get_git_diff
        return get_git_diff()

    def plan_and_execute(
        self,
        goal: str,
        callback: Optional[Callable[[str, str, Any, str], None]] = None,
        approval_hook: Optional[Callable[[str, Any], bool]] = None,
    ) -> str:
        """
        Two-phase Plan-First Execution:
        Phase 1: Explore and generate structured milestone plan.
        Phase 2: Systematically execute steps until completion.
        """
        plan_prompt = (
            f"You are operating in PLAN-FIRST mode. The user's goal is:\n\n{goal}\n\n"
            "PHASE 1 (PLANNING):\n"
            "1. Inspect workspace structure using `list_files` or `search_files` if needed.\n"
            "2. Produce a clear, numbered implementation checklist with specific tasks.\n"
            "Do not execute any code edits yet in this phase. Output the full plan."
        )
        plan = self.process_turn(plan_prompt, callback=callback, approval_hook=approval_hook)

        execute_prompt = (
            "PHASE 2 (EXECUTION):\n"
            "Now systematically execute the plan step-by-step. Use code tools (`create_file`, `edit_file`, "
            "`run_terminal_command`, `run_tests_with_diagnostics`) to complete each task.\n"
            "Verify all changes before finalizing."
        )
        execution_result = self.process_turn(execute_prompt, callback=callback, approval_hook=approval_hook, max_steps=15)

        return f"📋 **Implementation Plan**:\n{plan}\n\n---\n\n🚀 **Execution Result**:\n{execution_result}"

    def export_session_report(self, file_path: str = "agent-session-report.md") -> str:
        """Generate and save an executive Markdown session report."""
        import datetime
        from pathlib import Path
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        m = self.metrics

        lines = [
            "# AI Agent - Session Execution Report 📊",
            f"*Generated on: {timestamp}*",
            "",
            "## ⚙️ Environment & Provider",
            f"- **Provider**: `{self.provider}`",
            f"- **Model**: `{self.model}`",
            f"- **Safety Mode**: `{self.safety_mode}`",
            "",
            "## 📈 Telemetry & Usage Metrics",
            f"- **Total Turns**: {m['turns_count']}",
            f"- **Prompt Tokens**: {m['prompt_tokens']:,}",
            f"- **Completion Tokens**: {m['completion_tokens']:,}",
            f"- **Total Tokens**: {m['total_tokens']:,}",
            f"- **Estimated Cost**: ${m.get('estimated_cost_usd', 0.0):.6f} USD",
            f"- **Last Turn Latency**: {m['last_latency_seconds']}s",
            "",
            "## 🧠 Active Memories",
        ]

        memories = self.memory.load()
        if memories:
            for k, v in memories.items():
                lines.append(f"- **{k}**: {v}")
        else:
            lines.append("*No durable memories stored.*")

        lines.extend([
            "",
            "## 💬 Conversation Transcript",
            "",
        ])

        for msg in self.history:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "").strip()
            lines.append(f"### {role}:")
            lines.append(content)
            lines.append("")

        report_content = "\n".join(lines)
        out_path = Path(file_path)
        out_path.write_text(report_content, encoding="utf-8")
        return f"✅ Session report saved to `{out_path.resolve()}` ({len(report_content)} bytes)."


