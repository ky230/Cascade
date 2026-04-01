import click
from cascade.cli.commands.chat import chat

@click.group()
@click.version_option(version="0.2.0", prog_name="Cascade")
def cli():
    """Cascade — HEP Agentic Orchestrator"""
    pass

cli.add_command(chat)

def main():
    cli()

if __name__ == "__main__":
    main()
