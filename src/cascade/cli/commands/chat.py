import asyncio
import click
from dotenv import load_dotenv

@click.command()
@click.option('--provider', default='glm',
    type=click.Choice(['glm', 'anthropic', 'openai', 'deepseek', 'kimi']))
@click.option('--model', default='glm-4.6v-flash', help='Model identifier')
@click.option('--verbose', is_flag=True, help='Verbose output')
def chat(provider, model, verbose):
    """Start an interactive chat session."""
    load_dotenv()
    # Temporary placeholder until UI is rebuilt
    click.echo(f"Starting chat with {provider} {model}...")
