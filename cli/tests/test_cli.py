"""Tests for the PreScale CLI surface."""

import json

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
    assert "--path" in result.output
    assert "--from-sitemap" in result.output
    assert "--max-rps" in result.output
    assert "--ignore-robots" in result.output
    assert "--html" in result.output


def test_run_rejects_non_url():
    result = CliRunner().invoke(cli, ["run", "not-a-url"])
    assert result.exit_code == 1


def test_group_help_lists_audit():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "audit" in result.output


def test_audit_help():
    result = CliRunner().invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "url" in result.output.lower()


def test_audit_rejects_non_url():
    result = CliRunner().invoke(cli, ["audit", "not-a-url"])
    assert result.exit_code == 1


def test_schema_command_outputs_valid_json():
    result = CliRunner().invoke(cli, ["schema"])
    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["title"] == "PreScale Result"
    assert doc["properties"]["schema_version"]["const"] == 1
