"""Command-line interface for Cascade."""
import argparse
import asyncio
from dotenv import load_dotenv

from cascade.ui.app import CascadeRepl


def main():
    """Main CLI entrypoint."""
    # Load environment variables
    load_dotenv()

    parser = argparse.ArgumentParser(description="Cascade — HEP Agentic Orchestrator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session")
    chat_parser.add_argument(
        "--provider",
        type=str,
        default="glm",
        choices=["glm", "anthropic", "openai", "bedrock"],
        help="LLM provider to use",
    )
    chat_parser.add_argument(
        "--model",
        type=str,
        default="glm-4.6v-flash",
        help="Model string corresponding to the provider",
    )

    args = parser.parse_args()

    if args.command == "chat":
        repl = CascadeRepl(provider=args.provider, model=args.model)
        try:
            asyncio.run(repl.run())
        except KeyboardInterrupt:
            pass
        except EOFError:
            pass
        print("\nGoodbye!")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
