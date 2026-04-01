import argparse
import asyncio
import os
import sys
try:
    import readline
except ImportError:
    pass
from dotenv import load_dotenv
from cascade.core.agent import Agent
from cascade.ui.banner import render_banner, render_status_bar
from cascade.ui.spinner import Spinner
from cascade.ui.colors import BLUE, CYAN, LIGHT_CYAN, DIM, RED, RESET, BOLD


def main():
    load_dotenv()
    default_provider = os.getenv("CASCADE_DEFAULT_PROVIDER", "openai")
    default_model = os.getenv("CASCADE_DEFAULT_MODEL", "gpt-4o")

    parser = argparse.ArgumentParser(description="Cascade: CLI Agentic Orchestrator for HEP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session.")
    chat_parser.add_argument("--provider", type=str, default=default_provider)
    chat_parser.add_argument("--model", type=str, default=default_model)

    args = parser.parse_args()

    if args.command == "chat":
        asyncio.run(interactive_chat(args.provider, args.model))


async def interactive_chat(provider: str, model: str):
    import shutil

    # Welcome banner
    print(render_banner())
    print(render_status_bar(provider, model))
    print(f"\n  {DIM}Type {BOLD}exit{RESET}{DIM} or {BOLD}quit{RESET}{DIM} to end. {BOLD}Ctrl+C{RESET}{DIM} to interrupt.{RESET}\n")

    agent = Agent(provider=provider, model_name=model)

    while True:
        try:
            # Calculate exactly the same width as the status bar for a unified look
            left_clean = f" ⚛  HEP Agentic Orchestrator v0.1.0 "
            sep_clean = " │ "
            right_clean = f" {provider}  ──  {model} "
            width = len(left_clean) + len(sep_clean) + len(right_clean)

            # Input box — fully enclosed before typing
            top    = f" {DIM}╭{'─' * width}╮{RESET}"
            middle = f" {DIM}│{RESET}{' ' * width}{DIM}│{RESET}"
            bottom = f" {DIM}╰{'─' * width}╯{RESET}"

            print(top)
            print(middle)
            print(bottom, flush=True)

            # Move cursor UP 2 lines to the middle row, start of line
            sys.stdout.write("\033[2A\r")
            sys.stdout.flush()

            # Construct readline-safe prompt with \001 and \002 markers
            # macOS libedit often strips 256-color (38;5) inside markers, so we use standard cyan (\033[36m)
            CYAN_BASIC = "\033[36m"
            prompt = (
                f" \001{DIM}\002│\001{RESET}\002 "
                f"\001{CYAN_BASIC}{BOLD}\002>\001{RESET}\002 "
            )
            user_input = input(prompt)

            # Move cursor DOWN 2 lines, past the bottom border
            sys.stdout.write("\033[2B")
            sys.stdout.flush()

            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{DIM}Exiting Cascade. Goodbye! 👋{RESET}")
                break
            if not user_input.strip():
                continue

            # Spinner during API call
            spinner = Spinner(message="Thinking")
            spinner.start()

            response = await agent.chat(user_input)

            elapsed = spinner.stop()

            # Colored response
            print(f"\n{LIGHT_CYAN}{BOLD}✧ Cascade{RESET}  {response}")
            print(f"{DIM}({elapsed:.1f}s){RESET}\n")

        except KeyboardInterrupt:
            print(f"\n\n{DIM}Exiting Cascade. Goodbye! 👋{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[Error]{RESET} {str(e)}\n")


if __name__ == "__main__":
    main()
