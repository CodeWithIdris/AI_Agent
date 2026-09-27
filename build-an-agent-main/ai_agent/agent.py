from typing import List, Dict, Any, Tuple
from openai import OpenAI

from .config import Config
from .memory import MemoryManager
from .tools import ToolRegistry, parse_tool_call


class AIAgent:
    """Core autonomous AI Agent orchestrating inference, tool calls, and durable memory."""

    def __init__(self, model: str = None, memory_manager: MemoryManager = None):
        Config.validate()
        self.model = model or Config.DEFAULT_MODEL
        self.client = OpenAI(
            base_url=Config.BASE_URL,
            api_key=Config.API_KEY,
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
            f"You have access to these tools: {ToolRegistry.get_prompt_signatures()}. "
            "When you need a tool, reply with exactly one Python function tool call and no extra text. "
            "Use memory for durable user preferences, key project details, and facts that should survive session restarts. "
            "Current Memory State:\n"
            f"{live_memory}"
        )

    def run_inference(self) -> str:
        """Execute chat completion request with OpenAI-compatible API."""
        messages = [{"role": "system", "content": self.build_system_prompt()}] + self.history
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return completion.choices[0].message.content.strip()

    def process_turn(self, user_input: str, callback=None) -> str:
        """
        Process a user message through the agent tool-execution loop.
        If a callback is provided, it receives status updates (response, tool_name, result).
        """
        self.history.append({"role": "user", "content": user_input})

        while True:
            response = self.run_inference()

            tool_name, args = parse_tool_call(response)
            if not tool_name or not self.tools.is_registered(tool_name):
                # Conversational output (no tool call requested)
                self.history.append({"role": "assistant", "content": response})
                return response

            # Execute tool call
            result = self.tools.execute(tool_name, *args)

            if callback:
                callback(response, tool_name, args, result)

            self.history.append({"role": "assistant", "content": response})
            self.history.append({
                "role": "user",
                "content": f"Tool result for {tool_name}: {result}"
            })

    def clear_history(self) -> None:
        """Clear current conversation history."""
        self.history.clear()
