import asyncio
import sys
import click
from dotenv import load_dotenv

from cascade.services.api_client import ModelClient
from cascade.ui.app import CascadeRepl

@click.command()
@click.option('--provider', default='glm',
    type=click.Choice(['glm', 'anthropic', 'openai', 'deepseek', 'kimi', 'gemini', 'qwen']))
@click.option('--model', default='glm-4.6v-flash', help='Model identifier')
@click.option('--verbose', is_flag=True, help='Verbose output')
def chat(provider, model, verbose):
    """Start an interactive chat session."""
    load_dotenv()
    try:
        client = ModelClient(provider=provider, model_name=model)
        repl = CascadeRepl(client)
        asyncio.run(repl.run())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting chat: {e}", err=True)
        sys.exit(1)
