"""
Helios Agent Tests

Unit tests for the Helios agent, sources, and client.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMetricSample:
    """Tests for MetricSample dataclass."""

    def test_import(self):
        """Test that MetricSample can be imported."""
        from helios_agent.sources.base import MetricSample, MetricType
        assert MetricSample is not None
        assert MetricType is not None

    def test_create_sample(self):
        """Test creating a metric sample."""
        from helios_agent.sources.base import MetricSample, MetricType
        
        sample = MetricSample(
            name="cpu_usage",
            value=65.5,
            timestamp=datetime.now(timezone.utc),
            metric_type=MetricType.GAUGE,
            labels={"host": "server1"},
            source="system"
        )
        
        assert sample.name == "cpu_usage"
        assert sample.value == 65.5
        assert sample.labels == {"host": "server1"}
        assert sample.source == "system"

    def test_to_dict(self):
        """Test converting sample to dictionary."""
        from helios_agent.sources.base import MetricSample, MetricType
        
        ts = datetime.now(timezone.utc)
        sample = MetricSample(
            name="memory_percent",
            value=75.0,
            timestamp=ts,
            metric_type=MetricType.GAUGE,
            labels={"host": "server1"},
            source="system"
        )
        
        d = sample.to_dict()
        
        assert d["name"] == "memory_percent"
        assert d["value"] == 75.0
        assert d["type"] == "gauge"
        assert d["labels"] == {"host": "server1"}
        assert d["source"] == "system"


class TestSourceConfig:
    """Tests for SourceConfig dataclass."""

    def test_import(self):
        """Test that SourceConfig can be imported."""
        from helios_agent.sources.base import SourceConfig
        assert SourceConfig is not None

    def test_create_config(self):
        """Test creating source configuration."""
        from helios_agent.sources.base import SourceConfig
        
        config = SourceConfig(
            name="prometheus-main",
            type="prometheus",
            enabled=True,
            endpoint="http://prometheus:9090"
        )
        
        assert config.name == "prometheus-main"
        assert config.type == "prometheus"
        assert config.enabled is True
        assert config.endpoint == "http://prometheus:9090"

    def test_default_values(self):
        """Test default configuration values."""
        from helios_agent.sources.base import SourceConfig
        
        config = SourceConfig(name="test", type="system")
        
        assert config.enabled is True
        assert config.interval == 15
        assert config.queries == []
        assert config.metrics == []


class TestSourceRegistry:
    """Tests for the source registry."""

    def test_import(self):
        """Test that SourceRegistry can be imported."""
        from helios_agent.sources.registry import SourceRegistry
        assert SourceRegistry is not None

    def test_list_types(self):
        """Test listing registered source types."""
        from helios_agent.sources.registry import SourceRegistry
        
        types = SourceRegistry.list_types()
        
        assert isinstance(types, list)
        assert "system" in types
        # Other sources are conditionally registered based on dependencies

    def test_create_system_source(self):
        """Test creating a system source."""
        from helios_agent.sources.registry import SourceRegistry
        from helios_agent.sources.base import SourceConfig
        
        config = SourceConfig(name="test-system", type="system")
        source = SourceRegistry.create(config)
        
        assert source is not None
        assert source.name == "test-system"
        assert source.source_type == "system"

    def test_create_unknown_source(self):
        """Test creating an unknown source type returns None."""
        from helios_agent.sources.registry import SourceRegistry
        from helios_agent.sources.base import SourceConfig
        
        config = SourceConfig(name="test-unknown", type="nonexistent")
        source = SourceRegistry.create(config)
        
        assert source is None


class TestSystemSource:
    """Tests for SystemSource."""

    def test_import(self):
        """Test that SystemSource can be imported."""
        from helios_agent.sources.system import SystemSource
        assert SystemSource is not None

    def test_source_type(self):
        """Test system source type."""
        from helios_agent.sources.system import SystemSource
        assert SystemSource.source_type == "system"

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test system source initialization."""
        from helios_agent.sources.system import SystemSource
        from helios_agent.sources.base import SourceConfig
        
        config = SourceConfig(name="system-test", type="system")
        source = SystemSource(config)
        
        result = await source.initialize()
        
        assert result is True
        assert source._initialized is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test system source health check."""
        from helios_agent.sources.system import SystemSource
        from helios_agent.sources.base import SourceConfig
        
        config = SourceConfig(name="system-test", type="system")
        source = SystemSource(config)
        
        healthy = await source.health_check()
        
        assert healthy is True

    @pytest.mark.asyncio
    async def test_collect(self):
        """Test system metrics collection."""
        from helios_agent.sources.system import SystemSource
        from helios_agent.sources.base import SourceConfig, CollectionResult
        
        config = SourceConfig(
            name="system-test",
            type="system",
            options={
                "collect_cpu": True,
                "collect_memory": True,
                "collect_disk": True,
                "collect_network": True
            }
        )
        source = SystemSource(config)
        await source.initialize()
        
        result = await source.collect()
        
        assert isinstance(result, CollectionResult)
        assert result.success is True
        assert len(result.metrics) > 0
        assert result.source == "system-test"

    @pytest.mark.asyncio
    async def test_collect_cpu_only(self):
        """Test collecting only CPU metrics."""
        from helios_agent.sources.system import SystemSource
        from helios_agent.sources.base import SourceConfig
        
        config = SourceConfig(
            name="cpu-only",
            type="system",
            options={
                "collect_cpu": True,
                "collect_memory": False,
                "collect_disk": False,
                "collect_network": False
            }
        )
        source = SystemSource(config)
        await source.initialize()
        
        result = await source.collect()
        
        assert result.success is True
        # Should have at least CPU metric
        cpu_metrics = [m for m in result.metrics if "cpu" in m.name]
        assert len(cpu_metrics) > 0
        # Should NOT have memory metrics
        mem_metrics = [m for m in result.metrics if "memory" in m.name]
        assert len(mem_metrics) == 0


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_import(self):
        """Test that AgentConfig can be imported."""
        from helios_agent.config import AgentConfig
        assert AgentConfig is not None

    def test_load_from_dict(self):
        """Test loading config from dictionary."""
        from helios_agent.config import AgentConfig
        
        config_dict = {
            "endpoint": {
                "url": "http://localhost:8080",
                "api_key": "test-key"
            },
            "collection_interval": 30,
            "batch_size": 50,
            "sources": [
                {
                    "name": "local-system",
                    "type": "system",
                    "enabled": True
                }
            ]
        }
        
        config = AgentConfig.from_dict(config_dict)
        
        assert config.endpoint.url == "http://localhost:8080"
        assert config.endpoint.api_key == "test-key"
        assert config.collection_interval == 30
        assert config.batch_size == 50
        assert len(config.sources) == 1


class TestHeliosClient:
    """Tests for HeliosClient."""

    def test_import(self):
        """Test that HeliosClient can be imported."""
        from helios_agent.client import HeliosClient
        assert HeliosClient is not None

    def test_initialization(self):
        """Test client initialization."""
        from helios_agent.client import HeliosClient
        
        client = HeliosClient(
            endpoint="http://localhost:8080",
            api_key="test-key",
            timeout=30
        )
        
        assert client.endpoint == "http://localhost:8080"
        assert client.api_key == "test-key"
        assert client.timeout == 30

    @pytest.mark.asyncio
    async def test_send_metrics_success(self):
        """Test sending metrics successfully."""
        from helios_agent.client import HeliosClient
        from helios_agent.sources.base import MetricSample, MetricType
        
        client = HeliosClient(endpoint="http://localhost:8080")
        
        metrics = [
            MetricSample(
                name="test_metric",
                value=100.0,
                timestamp=datetime.now(timezone.utc),
                metric_type=MetricType.GAUGE,
                source="test"
            )
        ]
        
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"status": "ok"})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_instance = MagicMock()
            mock_session_instance.post = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance
            
            result = await client.send_metrics(metrics)
            
            # Should attempt to send
            assert mock_session_instance.post.called


class TestAgent:
    """Tests for the main Agent class."""

    def test_import(self):
        """Test that Agent can be imported."""
        from helios_agent.agent import Agent
        assert Agent is not None

    def test_initialization(self):
        """Test agent initialization."""
        from helios_agent.agent import Agent
        from helios_agent.config import AgentConfig
        
        config_dict = {
            "endpoint": {"url": "http://localhost:8080"},
            "sources": []
        }
        config = AgentConfig.from_dict(config_dict)
        
        agent = Agent(config)
        
        assert agent.config == config
        assert agent.sources == []
        assert agent._running is False

    @pytest.mark.asyncio
    async def test_setup_no_sources(self):
        """Test agent setup with no sources."""
        from helios_agent.agent import Agent
        from helios_agent.config import AgentConfig
        
        config_dict = {
            "endpoint": {"url": "http://localhost:8080"},
            "sources": []
        }
        config = AgentConfig.from_dict(config_dict)
        
        agent = Agent(config)
        await agent.setup()
        
        assert len(agent.sources) == 0
        assert agent.client is not None

    @pytest.mark.asyncio
    async def test_setup_with_system_source(self):
        """Test agent setup with system source."""
        from helios_agent.agent import Agent
        from helios_agent.config import AgentConfig
        
        config_dict = {
            "endpoint": {"url": "http://localhost:8080"},
            "sources": [
                {
                    "name": "local-system",
                    "type": "system",
                    "enabled": True
                }
            ]
        }
        config = AgentConfig.from_dict(config_dict)
        
        agent = Agent(config)
        await agent.setup()
        
        assert len(agent.sources) == 1
        assert agent.sources[0].name == "local-system"


class TestCLI:
    """Tests for the CLI module."""

    def test_import(self):
        """Test that CLI can be imported."""
        from helios_agent.cli import main
        assert main is not None


# Fixtures
@pytest.fixture
def sample_config():
    """Create sample agent configuration."""
    return {
        "endpoint": {
            "url": "http://localhost:8080",
            "api_key": "test-api-key",
            "timeout": 30
        },
        "collection_interval": 15,
        "batch_size": 100,
        "sources": [
            {
                "name": "system-metrics",
                "type": "system",
                "enabled": True,
                "options": {
                    "collect_cpu": True,
                    "collect_memory": True,
                    "collect_disk": False,
                    "collect_network": False
                }
            }
        ]
    }


@pytest.fixture
def mock_metrics():
    """Create mock metric samples."""
    from helios_agent.sources.base import MetricSample, MetricType
    
    now = datetime.now(timezone.utc)
    return [
        MetricSample(
            name="cpu_usage_percent",
            value=45.5,
            timestamp=now,
            metric_type=MetricType.GAUGE,
            labels={"host": "test-host"},
            source="system"
        ),
        MetricSample(
            name="memory_usage_percent",
            value=62.3,
            timestamp=now,
            metric_type=MetricType.GAUGE,
            labels={"host": "test-host"},
            source="system"
        )
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
