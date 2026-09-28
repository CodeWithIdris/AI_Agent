import sys
from .agent import AIAgent
from .config import Config

# ANSI Color Codes
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    """Display interactive CLI welcome banner."""
    print(f"{BOLD}{CYAN}======================================================{RESET}")
    print(f"{BOLD}{CYAN}            AI AGENT SYSTEM v0.2.0                    {RESET}")
    print(f"{BOLD}{CYAN}   Built by CodeWithIdris (github.com/CodeWithIdris)  {RESET}")
    print(f"{BOLD}{CYAN}======================================================{RESET}")
    print(f"{YELLOW}Type your message or use commands: /help, /memory, /clear, /exit{RESET}\n")


def tool_callback(response: str, tool_name: str, args: list, result: str):
    """Callback for rendering tool execution in CLI."""
    formatted_args = ", ".join(repr(a) for a in args)
    print(f"{YELLOW}Agent:{RESET} {response}")
    print(f"{GREEN}[TOOL EXECUTION]{RESET} {tool_name}({formatted_args}) -> {result}")


def main():
    """Main CLI entry point."""
    print_banner()

    try:
        agent = AIAgent()
    except ValueError as err:
        print(f"{RED}Configuration Error:{RESET} {err}")
        sys.exit(1)

    while True:
        try:
            user_input = input(f"{BOLD}{CYAN}You{RESET}: ").strip()
            if not user_input:
                continue

            # Command Handlers
            if user_input.lower() in ("/exit", "/quit"):
                print(f"{YELLOW}Goodbye!{RESET}")
                break

            if user_input.lower() == "/clear":
                agent.clear_history()
                print(f"{GREEN}Conversation history cleared.{RESET}\n")
                continue

            if user_input.lower() == "/memory":
                memories = agent.memory.recall()
                print(f"{MAGENTA}Current Memory State:{RESET}\n{memories}\n")
                continue

            if user_input.lower() == "/help":
                print(f"{YELLOW}Available Commands:{RESET}")
                print("  /help              - Display this help message")
                print("  /debug [command]   - Run autonomous self-healing debugger (e.g. /debug pytest)")
                print("  /provider [name]   - View active provider or switch (e.g. /provider ollama)")
                print("  /model [name]      - View or switch active model")
                print("  /tokens            - View session token telemetry and latency")
                print("  /memory            - Display current durable memory state")
                print("  /clear             - Clear current conversation history")
                print("  /exit              - Exit the application\n")
                continue

            if user_input.lower().startswith("/debug"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[1].strip() if len(parts) > 1 else "pytest"
                print(f"{MAGENTA}Starting Autonomous Self-Healing Debugger on `{cmd}`...{RESET}\n")
                report = agent.auto_debug(command=cmd, callback=tool_callback)
                print(f"\n{BOLD}{GREEN}Debugger Report:{RESET}\n{report}\n")
                continue


            if user_input.lower().startswith("/provider"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    print(f"{CYAN}Active Provider:{RESET} {agent.provider} (Base URL: {agent.base_url})\n")
                else:
                    new_prov = parts[1].strip().lower()
                    try:
                        agent.switch_provider(new_prov)
                        print(f"{GREEN}Switched provider to '{agent.provider}' (Model: {agent.model}){RESET}\n")
                    except Exception as err:
                        print(f"{RED}Provider switch error:{RESET} {err}\n")
                continue

            if user_input.lower().startswith("/model"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    print(f"{CYAN}Active Model:{RESET} {agent.model} (Provider: {agent.provider})\n")
                else:
                    new_model = parts[1].strip()
                    try:
                        agent.switch_provider(agent.provider, model=new_model)
                        print(f"{GREEN}Switched model to '{agent.model}'{RESET}\n")
                    except Exception as err:
                        print(f"{RED}Model switch error:{RESET} {err}\n")
                continue

            if user_input.lower() == "/tokens":
                m = agent.metrics
                print(f"{MAGENTA}Session Telemetry:{RESET}")
                print(f"  Turns Executed:     {m['turns_count']}")
                print(f"  Prompt Tokens:      {m['prompt_tokens']}")
                print(f"  Completion Tokens:  {m['completion_tokens']}")
                print(f"  Total Tokens:       {m['total_tokens']}")
                print(f"  Last Turn Latency:  {m['last_latency_seconds']}s\n")
                continue


            # Process AI Agent Turn
            final_response = agent.process_turn(user_input, callback=tool_callback)
            print(f"{BOLD}{YELLOW}Agent{RESET}: {final_response}\n")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Session ended by user. Goodbye!{RESET}")
            break
        except Exception as err:
            print(f"{RED}Error:{RESET} {err}\n")


if __name__ == "__main__":
    main()
