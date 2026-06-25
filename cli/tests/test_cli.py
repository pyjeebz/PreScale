"""Tests for the PreScale CLI surface."""

from click.testing import CliRunner

from prescale_cli.main import cli, main


def test_imports():
    assert cli is not None
    assert main is not None


def test_version_string():
    from prescale_cli import __version__
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) >= 2


def test_version_option():
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "prescale" in result.output.lower()


def test_group_help_lists_run():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "load" in result.output.lower()


def test_run_help_has_key_options():
    result = CliRunner().invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "--max-users" in result.output
    assert "--i-own-this" in result.output


def test_run_rejects_non_url():
    result = CliRunner().invoke(cli, ["run", "not-a-url"])
    assert result.exit_code == 1
