from click.testing import CliRunner
from cascade.cli.main import cli

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'cascade' in result.output.lower()

def test_chat_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['chat', '--help'])
    assert result.exit_code == 0
    assert '--provider' in result.output
