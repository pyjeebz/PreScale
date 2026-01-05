# Helios CLI

Command-line interface for Helios - Predictive Infrastructure Intelligence Platform.

## Installation

```bash
pip install helios-cli
```

## Quick Start

```bash
# Check service status
helios status

# Get CPU predictions for a deployment
helios predict cpu --deployment my-app --namespace default

# Detect anomalies
helios detect --deployment my-app

# Get scaling recommendations
helios recommend --deployment my-app
```

## Configuration

### Environment Variables

```bash
export HELIOS_ENDPOINT="http://helios.example.com:8000"
export HELIOS_API_KEY="your-api-key"
```

### Configuration File

```bash
# Interactive setup
helios config init

# Or set individual values
helios config set endpoint http://helios.example.com:8000
helios config set api_key your-api-key

# View current configuration
helios config show
```

## Commands

### `helios predict`

Generate resource predictions.

```bash
# CPU prediction
helios predict cpu --deployment my-app --horizon 24

# Memory prediction  
helios predict memory --deployment my-app --horizon 48
```

Options:
- `--deployment, -d` - Deployment name (required)
- `--namespace, -n` - Kubernetes namespace (default: default)
- `--horizon, -h` - Prediction horizon in hours (default: 24)
- `--interval, -i` - Prediction interval (default: 1h)

### `helios detect`

Detect anomalies in resource metrics.

```bash
helios detect --deployment my-app --sensitivity high
```

Options:
- `--deployment, -d` - Deployment name (required)
- `--namespace, -n` - Kubernetes namespace (default: default)
- `--lookback, -l` - Hours of data to analyze (default: 1)
- `--sensitivity, -s` - Detection sensitivity: low, medium, high (default: medium)

### `helios recommend`

Get scaling recommendations.

```bash
# Balanced recommendations
helios recommend --deployment my-app

# Cost-optimized
helios recommend --deployment my-app --cost-optimize

# Performance-optimized
helios recommend --deployment my-app --performance
```

Options:
- `--deployment, -d` - Deployment name (required)
- `--namespace, -n` - Kubernetes namespace (default: default)
- `--cost-optimize` - Prioritize cost savings
- `--performance` - Prioritize performance

### `helios status`

Check Helios service status.

```bash
helios status
```

### `helios config`

Manage CLI configuration.

```bash
# Show current config
helios config show

# Set values
helios config set endpoint http://localhost:8000
helios config set output json

# Remove values
helios config unset api_key

# Interactive setup
helios config init
```

## Global Options

- `--endpoint, -e` - Helios API endpoint (env: HELIOS_ENDPOINT)
- `--api-key` - API key for authentication (env: HELIOS_API_KEY)
- `--output, -o` - Output format: table, json, yaml (default: table)
- `--version` - Show version
- `--help` - Show help

## Output Formats

```bash
# Default table format
helios predict cpu -d my-app

# JSON output
helios predict cpu -d my-app -o json

# YAML output
helios predict cpu -d my-app -o yaml
```

## License

Apache License 2.0
