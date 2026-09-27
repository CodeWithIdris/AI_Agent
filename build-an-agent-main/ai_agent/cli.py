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
                print("  /help   - Display this help message")
                print("  /memory - Display current durable memory state")
                print("  /clear  - Clear current conversation history")
                print("  /exit   - Exit the application\n")
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
