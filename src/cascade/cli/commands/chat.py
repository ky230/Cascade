import asyncio
import sys
import click
import os
from dotenv import load_dotenv

load_dotenv()

from cascade.services.api_client import ModelClient
from cascade.ui.app import CascadeRepl

@click.command()
@click.option('--provider', default=os.getenv('CASCADE_DEFAULT_PROVIDER', 'glm'),
    type=click.Choice(['glm', 'anthropic', 'openai', 'deepseek', 'kimi', 'gemini', 'qwen']))
@click.option('--model', default=os.getenv('CASCADE_DEFAULT_MODEL', 'glm-4-flash'), help='Model identifier')
@click.option('--verbose', is_flag=True, help='Verbose output')
def chat(provider, model, verbose):
    """Start an interactive chat session."""
    try:
        client = ModelClient(provider=provider, model_name=model)
        repl = CascadeRepl(client)
        asyncio.run(repl.run())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting chat: {e}", err=True)
        sys.exit(1)
