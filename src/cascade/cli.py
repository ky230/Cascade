import argparse
import asyncio
import os
from dotenv import load_dotenv
from cascade.core.agent import Agent
from cascade.ui.banner import render_banner, render_status_bar
from cascade.ui.spinner import Spinner
from cascade.ui.colors import BLUE, CYAN, DIM, RED, RESET, BOLD


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
            # Input box
            width = min(shutil.get_terminal_size().columns - 2, 80)
            print(f"{DIM}╭{'─' * width}╮{RESET}")
            user_input = input(f"{DIM}│{RESET} {CYAN}{BOLD}>{RESET} ")
            print(f"{DIM}╰{'─' * width}╯{RESET}")

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
            print(f"\n{BLUE}{BOLD}Cascade>{RESET} {response}")
            print(f"{DIM}({elapsed:.1f}s){RESET}\n")

        except KeyboardInterrupt:
            print(f"\n\n{DIM}Exiting Cascade. Goodbye! 👋{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[Error]{RESET} {str(e)}\n")


if __name__ == "__main__":
    main()
