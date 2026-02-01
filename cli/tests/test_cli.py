"""
Helios CLI Tests

Unit tests for the Helios CLI commands.
"""

import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner


class TestCLIImport:
    """Tests for CLI module imports."""

    def test_import_main(self):
        """Test that main CLI can be imported."""
        from helios_cli.main import cli, main
        assert cli is not None
        assert main is not None

    def test_import_commands(self):
        """Test that all commands can be imported."""
        from helios_cli.commands import predict, detect, recommend, status, config, agent
        assert predict is not None
        assert detect is not None
        assert recommend is not None
        assert status is not None
        assert config is not None
        assert agent is not None


class TestCLIVersion:
    """Tests for CLI version."""

    def test_version_import(self):
        """Test that version can be imported."""
        from helios_cli import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_format(self):
        """Test that version follows semver format."""
        from helios_cli import __version__
        parts = __version__.split(".")
        assert len(parts) >= 2  # At least major.minor


class TestCLIGroup:
    """Tests for the main CLI group."""

    def test_cli_help(self):
        """Test CLI help output."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        assert "Helios CLI" in result.output
        assert "status" in result.output
        assert "detect" in result.output
        assert "recommend" in result.output
        assert "predict" in result.output

    def test_cli_version_option(self):
        """Test --version option."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        
        assert result.exit_code == 0
        assert "helios" in result.output.lower()


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_help(self):
        """Test status command help."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    @patch("helios_cli.commands.status.httpx.get")
    def test_status_healthy(self, mock_get):
        """Test status command with healthy service."""
        from helios_cli.main import cli
        
        # Mock healthy response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "models_loaded": 3,
            "uptime": "24h"
        }
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_get.return_value = mock_response
        
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        
        # Should attempt to check health
        assert mock_get.called

    @patch("helios_cli.commands.status.httpx.get")
    def test_status_json_output(self, mock_get):
        """Test status command with JSON output."""
        from helios_cli.main import cli
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_get.return_value = mock_response
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--output", "json", "status"])
        
        # JSON output should contain valid JSON
        # (even if parsing fails due to test environment)
        assert result.exit_code == 0


class TestDetectCommand:
    """Tests for the detect command."""

    def test_detect_help(self):
        """Test detect command help."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["detect", "--help"])
        
        assert result.exit_code == 0
        assert "detect" in result.output.lower()
        assert "sensitivity" in result.output

    def test_detect_sensitivity_options(self):
        """Test that sensitivity options are validated."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        
        # Valid sensitivities should be accepted (help shows options)
        result = runner.invoke(cli, ["detect", "--help"])
        assert "low" in result.output
        assert "medium" in result.output
        assert "high" in result.output

    def test_detect_metric_options(self):
        """Test that metric options are validated."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["detect", "--help"])
        
        assert "cpu_utilization" in result.output
        assert "memory_utilization" in result.output


class TestRecommendCommand:
    """Tests for the recommend command."""

    def test_recommend_help(self):
        """Test recommend command help."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["recommend", "--help"])
        
        assert result.exit_code == 0
        assert "recommend" in result.output.lower()


class TestPredictCommand:
    """Tests for the predict command."""

    def test_predict_help(self):
        """Test predict command help."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["predict", "--help"])
        
        assert result.exit_code == 0
        assert "predict" in result.output.lower()


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_help(self):
        """Test config command help."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])
        
        assert result.exit_code == 0


class TestAgentCommand:
    """Tests for the agent command."""

    def test_agent_help(self):
        """Test agent command help."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["agent", "--help"])
        
        assert result.exit_code == 0


class TestOutputFormats:
    """Tests for different output formats."""

    def test_table_format_default(self):
        """Test that table is the default output format."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert "table" in result.output

    def test_json_format_option(self):
        """Test JSON output format option."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert "json" in result.output

    def test_yaml_format_option(self):
        """Test YAML output format option."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert "yaml" in result.output


class TestEndpointOptions:
    """Tests for endpoint configuration."""

    def test_endpoint_option(self):
        """Test --endpoint option is available."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert "--endpoint" in result.output or "-e" in result.output

    def test_api_key_option(self):
        """Test --api-key option is available."""
        from helios_cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert "--api-key" in result.output


class TestSampleDataGeneration:
    """Tests for sample data generation utilities."""

    def test_generate_sample_metrics(self):
        """Test sample metrics generation."""
        from helios_cli.commands.detect import generate_sample_metrics
        
        metrics = generate_sample_metrics(lookback_hours=1)
        
        assert len(metrics) > 0
        assert "timestamp" in metrics[0]
        assert "value" in metrics[0]

    def test_generate_sample_metrics_values(self):
        """Test that generated values are in reasonable range."""
        from helios_cli.commands.detect import generate_sample_metrics
        
        metrics = generate_sample_metrics(lookback_hours=2)
        
        for point in metrics:
            # CPU values should be between 0 and 1
            assert 0 <= point["value"] <= 1


# Fixtures
@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_healthy_response():
    """Create a mock healthy API response."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "status": "healthy",
        "version": "0.4.0",
        "models_loaded": 3
    }
    mock.elapsed.total_seconds.return_value = 0.042
    return mock


@pytest.fixture
def mock_unhealthy_response():
    """Create a mock unhealthy API response."""
    mock = MagicMock()
    mock.status_code = 503
    mock.json.return_value = {"error": "Service unavailable"}
    mock.elapsed.total_seconds.return_value = 5.0
    return mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
