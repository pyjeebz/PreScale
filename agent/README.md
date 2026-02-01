# Helios Agent

Metrics collection agent for [Helios](https://github.com/pyjeebz/helios) - Predictive Infrastructure Intelligence Platform.

## Installation

```bash
# Base installation (system metrics + Prometheus)
pip install helios-platform-agent

# With specific backends
pip install helios-platform-agent[gcp]      # + GCP Cloud Monitoring
pip install helios-platform-agent[aws]      # + AWS CloudWatch
pip install helios-platform-agent[azure]    # + Azure Monitor
pip install helios-platform-agent[datadog]  # + Datadog
pip install helios-platform-agent[all]      # All backends
```

## Quick Start

```bash
# Generate configuration file
helios-agent init

# List available metric sources
helios-agent sources

# Test configured sources
helios-agent test

# Run the agent
helios-agent run --config helios-agent.yaml
```

## Configuration

Create a `helios-agent.yaml` file:

```yaml
agent:
  collection_interval: 60
  log_level: INFO

sources:
  # System metrics (always available)
  - type: system
    enabled: true
    config:
      collect_cpu: true
      collect_memory: true

  # GCP Cloud Monitoring
  - type: gcp-monitoring
    enabled: true
    config:
      project_id: your-gcp-project
      metrics:
        - kubernetes.io/container/cpu/limit_utilization
        - kubernetes.io/container/memory/limit_utilization

  # Prometheus
  - type: prometheus
    enabled: false
    config:
      url: http://prometheus:9090
      queries:
        - name: cpu_usage
          query: rate(container_cpu_usage_seconds_total[5m])

helios:
  endpoint: http://helios-inference:8080
```

## Supported Sources

| Source | Description | Extra Install |
|--------|-------------|---------------|
| `system` | Local CPU, memory, disk via psutil | Built-in |
| `prometheus` | Query Prometheus server | Built-in |
| `gcp-monitoring` | GCP Cloud Monitoring | `[gcp]` |
| `cloudwatch` | AWS CloudWatch | `[aws]` |
| `azure-monitor` | Azure Monitor | `[azure]` |
| `datadog` | Datadog API | `[datadog]` |

## CLI Commands

```bash
helios-agent init              # Generate config file
helios-agent run               # Start collecting metrics
helios-agent run --once        # Single collection (testing)
helios-agent sources           # List available sources
helios-agent test              # Test source connections
helios-agent status            # Show agent status
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HELIOS_CONFIG_FILE` | Path to config file (default: `./helios-agent.yaml`) |
| `HELIOS_ENDPOINT` | Helios inference endpoint |
| `HELIOS_API_KEY` | API key for authentication |

## License

Apache 2.0 - See [LICENSE](../LICENSE)
