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

    from prompt_toolkit import PromptSession, HTML
    from prompt_toolkit.styles import Style
    import os

    # Gemini-like UI Style
    pt_style = Style.from_dict({
        'border': 'ansibrightblue',       # LIGHT_BLUE box borders
        'prompt': 'ansicyan bold',        # Cyan '>'
        'placeholder': 'ansiteal',        # Dim placeholder text
        'status-bar': 'ansigray',         # Dim text for status
    })

    session = PromptSession(style=pt_style)
    cwd = os.getcwd()

    while True:
        try:
            # Fixed width mimicking the status banner
            left_clean = f" ⚛  HEP Agentic Orchestrator v0.1.0 "
            sep_clean = " │ "
            right_clean = f" {provider}  ──  {model} "
            width = len(left_clean) + len(sep_clean) + len(right_clean)

            # Manually print the top border before prompt
            top_border = f" \033[94m╭{'─' * width}╮\033[0m"
            print(top_border)

            # Provide the bottom border and status bar via the bottom_toolbar,
            # which prompt_toolkit places at the bottom of the terminal window,
            # ensuring a stable UI without backspace ripping the borders.
            def get_bottom_toolbar():
                # Shorten CWD to match screenshot style "~\..."
                home = os.path.expanduser("~")
                display_cwd = cwd.replace(home, "~")
                if len(display_cwd) > 25:
                    display_cwd = "..." + display_cwd[-22:]
                
                # We calculate padding to fit the status bar neatly under the ~60 char box
                # or we just use simple 5-space padding.
                return HTML(f"<border> ╰{'─' * width}╯</border>\n<status-bar>  {display_cwd}      no sandbox (see /docs)      auto </status-bar>")

            # The actual interactive input. We use HTML to colorize the left margin & prompt
            user_input = session.prompt(
                HTML("<border> │ </border><prompt>&gt; </prompt>"),
                placeholder="Type your message or @path/to/file",
                bottom_toolbar=get_bottom_toolbar,
                wrap_lines=True
            )

            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{DIM}Exiting Cascade. Goodbye! 👋{RESET}")
                break
            if not user_input.strip():
                # On empty input, we should reprint a dummy bottom border so history looks solid
                print(f" \033[94m╰{'─' * width}╯\033[0m", flush=True)
                continue

            # When input is submitted, the bottom toolbar from prompt_toolkit disappears.
            # To leave a clean chat log "box", we print the bottom border manually!
            print(f" \033[94m╰{'─' * width}╯\033[0m\n", flush=True)

            # Spinner during API call
            spinner = Spinner(message="Thinking")
            spinner.start()

            response = await agent.chat(user_input)

            elapsed = spinner.stop()

            # Colored response
            print(f"{LIGHT_CYAN}{BOLD}✧ Cascade{RESET}  {response}")
            print(f"{DIM}({elapsed:.1f}s){RESET}\n")

        except KeyboardInterrupt:
            print(f"\n\n{DIM}Exiting Cascade. Goodbye! 👋{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[Error]{RESET} {str(e)}\n")


if __name__ == "__main__":
    main()
