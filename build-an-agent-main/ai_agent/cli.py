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


def cli_approval_hook(tool_name: str, args: list) -> bool:
    """CLI prompt for user approval before executing dangerous tools in CONFIRM_DANGEROUS mode."""
    formatted_args = ", ".join(repr(a) for a in args)
    print(f"\n{BOLD}{RED}🛡️ [SAFETY INTERCEPT]{RESET} Agent proposed executing dangerous tool:")
    print(f"  Tool: {BOLD}{tool_name}{RESET}")
    print(f"  Args: {formatted_args}")
    choice = input(f"{YELLOW}Approve execution? [y/N]: {RESET}").strip().lower()
    return choice in ("y", "yes")


def display_help() -> None:
    """Print available interactive CLI slash commands."""
    print(f"{YELLOW}Available Commands:{RESET}")
    print("  /help              - Display this help message")
    print("  /plan [goal]       - Run two-phase plan-first autonomous task executor")
    print("  /outline [file]    - View AST-based code outline of classes and functions")
    print("  /symbol [name]     - Search codebase for symbol definitions (class, def, const)")
    print("  /refs [name]       - Find references and calls to symbol across codebase")
    print("  /review [path]     - Run automated security vulnerability and code quality audit")
    print("  /undo              - One-click rollback of the agent's last file modification")
    print("  /diff              - View live Git diff of workspace changes")
    print("  /debug [command]   - Run autonomous self-healing debugger (e.g. /debug pytest)")
    print("  /export [path]     - Export executive session transcript and cost report to markdown")
    print("  /provider [name]   - View active provider or switch (e.g. /provider gemini)")
    print("  /model [name]      - View or switch active model")
    print("  /mode [mode]       - View or switch safety mode (AUTONOMOUS or CONFIRM_DANGEROUS)")
    print("  /tokens            - View session token telemetry and latency")
    print("  /memory            - Display current durable memory state")
    print("  /clear             - Clear current conversation history")
    print("  /exit              - Exit the application\n")


def display_tokens(agent: AIAgent) -> None:
    """Display session token usage, latency and cost metrics."""
    m = agent.metrics
    print(f"{MAGENTA}Session Telemetry:{RESET}")
    print(f"  Turns Executed:     {m['turns_count']}")
    print(f"  Prompt Tokens:      {m['prompt_tokens']}")
    print(f"  Completion Tokens:  {m['completion_tokens']}")
    print(f"  Total Tokens:       {m['total_tokens']}")
    print(f"  Estimated Cost:     ${m['estimated_cost_usd']:.6f} USD")
    print(f"  Last Turn Latency:  {m['last_latency_seconds']}s")
    print(f"  Safety Mode:        {agent.safety_mode}\n")


def handle_slash_command(user_input: str, agent: AIAgent) -> bool:
    """
    Dispatch and execute CLI slash commands.
    Returns True if the input was handled as a slash command, False otherwise.
    """
    cmd_lower = user_input.lower()

    if cmd_lower == "/clear":
        agent.clear_history()
        print(f"{GREEN}Conversation history cleared.{RESET}\n")
        return True

    if cmd_lower == "/memory":
        memories = agent.memory.recall()
        print(f"{MAGENTA}Current Memory State:{RESET}\n{memories}\n")
        return True

    if cmd_lower == "/help":
        display_help()
        return True

    if cmd_lower == "/tokens":
        display_tokens(agent)
        return True

    if cmd_lower == "/undo":
        print(f"{YELLOW}Reverting last file change...{RESET}")
        undo_res = agent.undo()
        print(f"{GREEN}{undo_res}{RESET}\n")
        return True

    if cmd_lower == "/diff":
        print(f"{CYAN}Fetching workspace Git diff...{RESET}")
        diff_res = agent.diff()
        print(f"{GREEN}{diff_res}{RESET}\n")
        return True

    parts = user_input.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/outline":
        if not arg:
            print(f"{YELLOW}Usage: /outline <path/to/file.py>{RESET}\n")
        else:
            outline_res = agent.tools.execute("get_code_outline", arg)
            print(f"{CYAN}{outline_res}{RESET}\n")
        return True

    if cmd == "/symbol":
        if not arg:
            print(f"{YELLOW}Usage: /symbol <symbol_name>{RESET}\n")
        else:
            sym_res = agent.tools.execute("find_symbol", arg)
            print(f"{CYAN}{sym_res}{RESET}\n")
        return True

    if cmd == "/refs":
        if not arg:
            print(f"{YELLOW}Usage: /refs <symbol_name>{RESET}\n")
        else:
            ref_res = agent.tools.execute("find_references", arg)
            print(f"{CYAN}{ref_res}{RESET}\n")
        return True

    if cmd == "/review":
        target_p = arg or "."
        print(f"{BOLD}{MAGENTA}Running Code Review & Security Audit on `{target_p}`...{RESET}\n")
        review_report = agent.review_code(target_p)
        print(f"{CYAN}{review_report}{RESET}\n")
        return True

    if cmd == "/plan":
        if not arg:
            print(f"{YELLOW}Usage: /plan <describe what you want to achieve>{RESET}\n")
        else:
            print(f"{BOLD}{MAGENTA}Starting Two-Phase Plan-First Execution for:{RESET} {arg}\n")
            plan_res = agent.plan_and_execute(arg, callback=tool_callback, approval_hook=cli_approval_hook)
            print(f"\n{BOLD}{GREEN}Plan-First Result:{RESET}\n{plan_res}\n")
        return True

    if cmd == "/export":
        target_f = arg or "agent-session-report.md"
        exp_res = agent.export_session_report(target_f)
        print(f"{GREEN}{exp_res}{RESET}\n")
        return True

    if cmd == "/debug":
        test_cmd = arg or "pytest"
        print(f"{MAGENTA}Starting Autonomous Self-Healing Debugger on `{test_cmd}`...{RESET}\n")
        report = agent.auto_debug(command=test_cmd, callback=tool_callback)
        print(f"\n{BOLD}{GREEN}Debugger Report:{RESET}\n{report}\n")
        return True

    if cmd == "/mode":
        if not arg:
            print(f"{CYAN}Active Safety Mode:{RESET} {agent.safety_mode}\n")
        else:
            new_mode = arg.upper()
            if new_mode in ("AUTONOMOUS", "CONFIRM_DANGEROUS"):
                agent.safety_mode = new_mode
                print(f"{GREEN}Switched safety mode to '{agent.safety_mode}'{RESET}\n")
            else:
                print(f"{RED}Invalid mode. Use 'AUTONOMOUS' or 'CONFIRM_DANGEROUS'.{RESET}\n")
        return True

    if cmd == "/provider":
        if not arg:
            print(f"{CYAN}Active Provider:{RESET} {agent.provider} (Base URL: {agent.base_url})\n")
        else:
            new_prov = arg.lower()
            try:
                agent.switch_provider(new_prov)
                print(f"{GREEN}Switched provider to '{agent.provider}' (Model: {agent.model}){RESET}\n")
            except Exception as err:
                print(f"{RED}Provider switch error:{RESET} {err}\n")
        return True

    if cmd == "/model":
        if not arg:
            print(f"{CYAN}Active Model:{RESET} {agent.model} (Provider: {agent.provider})\n")
        else:
            try:
                agent.switch_provider(agent.provider, model=arg)
                print(f"{GREEN}Switched model to '{agent.model}'{RESET}\n")
            except Exception as err:
                print(f"{RED}Model switch error:{RESET} {err}\n")
        return True

    return False


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

            if user_input.lower() in ("/exit", "/quit"):
                print(f"{YELLOW}Goodbye!{RESET}")
                break

            if user_input.startswith("/"):
                handled = handle_slash_command(user_input, agent)
                if handled:
                    continue

            # Process AI Agent Turn
            final_response = agent.process_turn(user_input, callback=tool_callback, approval_hook=cli_approval_hook)
            print(f"{BOLD}{YELLOW}Agent{RESET}: {final_response}\n")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Session ended by user. Goodbye!{RESET}")
            break
        except Exception as err:
            print(f"{RED}Error:{RESET} {err}\n")


if __name__ == "__main__":
    main()
