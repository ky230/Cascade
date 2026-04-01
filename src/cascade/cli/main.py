import asyncio
import sys
import click
import os
from dotenv import load_dotenv

load_dotenv()

from cascade.services.api_client import ModelClient
from cascade.ui.app import CascadeRepl

@click.command()
@click.version_option(version="0.2.0", prog_name="Cascade")
@click.option('--provider', default=os.getenv('CASCADE_DEFAULT_PROVIDER', 'glm'),
    type=click.Choice(['glm', 'anthropic', 'openai', 'deepseek', 'kimi', 'gemini', 'qwen']))
@click.option('--model', default=os.getenv('CASCADE_DEFAULT_MODEL', 'glm-4.6'), help='Model identifier')
@click.option('--verbose', is_flag=True, help='Verbose output')
def cli(provider, model, verbose):
    """Cascade — HEP Agentic Orchestrator"""
    try:
        client = ModelClient(provider=provider, model_name=model)
        repl = CascadeRepl(client)
        asyncio.run(repl.run())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting cascade: {e}", err=True)
        sys.exit(1)

def main():
    cli()

if __name__ == "__main__":
    main()
