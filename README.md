# Helios

**Predictive Infrastructure Intelligence Platform**

[![CI](https://github.com/pyjeebz/helios/actions/workflows/ci.yml/badge.svg)](https://github.com/pyjeebz/helios/actions/workflows/ci.yml)
[![Release](https://github.com/pyjeebz/helios/actions/workflows/release.yml/badge.svg)](https://github.com/pyjeebz/helios/actions/workflows/release.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Helios uses machine learning to forecast infrastructure demand and provide proactive scaling recommendations, reducing reactive incidents and optimizing resource utilization.

## 🚀 Quick Start

### Local Development (No Cloud Required)

```bash
# Clone and setup
git clone https://github.com/pyjeebz/helios.git
cd helios

# Option 1: Docker Compose (recommended)
docker compose up -d inference
curl http://localhost:8080/health

# Option 2: Run directly with Python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r ml/inference/requirements.txt
cd ml && python -m uvicorn inference.app:app --port 8080
```

### One-Click Cloud Deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pyjeebz/helios)

**Docker Hub:**
```bash
docker run -d -p 8080:8080 ghcr.io/pyjeebz/helios/inference:latest
```

**Kubernetes (Helm):**
```bash
helm repo add helios https://pyjeebz.github.io/helios
helm install helios helios/helios
```

**Python Agent:**
```bash
pip install helios-agent
helios-agent init
helios-agent run
```

---

## 🎯 Overview

Helios analyzes real-time metrics from your infrastructure, predicts future resource demands, detects anomalies, and provides actionable scaling recommendations—before problems occur.

### Key Features

| Feature | Description |
|---------|-------------|
| **Traffic Forecasting** | Predict CPU, memory, and request rates up to 1 hour ahead |
| **Anomaly Detection** | Real-time detection of unusual patterns using XGBoost |
| **Scaling Recommendations** | Actionable advice for replica counts and resource limits |
| **Multi-Cloud Support** | Works on GKE, EKS, AKS, or any Kubernetes cluster |
| **Prometheus Native** | Exposes metrics in Prometheus format for easy integration |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HELIOS PLATFORM                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────────┐    │
│  │ Metrics Adapter  │───▶│ ML Pipeline     │───▶│ Inference Service   │    │
│  │ (pluggable)      │    │ (training)      │    │ (FastAPI)           │    │
│  │ • GCP            │    │                 │    │ /predict            │    │
│  │ • AWS            │    │ • Baseline      │    │ /detect             │    │
│  │ • Azure          │    │ • Prophet       │    │ /recommend          │    │
│  │ • Prometheus     │    │ • XGBoost       │    │ /metrics            │    │
│  └──────────────────┘    └─────────────────┘    └──────────┬──────────┘    │
│                                                            │               │
│         ┌──────────────────────────────────────────────────┼───────────┐   │
│         │                                                  │           │   │
│         ▼                                                  ▼           ▼   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  ┌───────────┐    │
│  │ Prometheus  │    │ Alertmanager│    │ KEDA        │  │ Grafana   │    │
│  │ (scraping)  │    │ (alerts)    │    │ (autoscale) │  │ (dashboard│    │
│  └─────────────┘    └─────────────┘    └─────────────┘  └───────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
helios/
├── agent/                       # Helios Agent (metrics collection)
│   ├── src/helios_agent/
│   │   ├── agent.py             # Main agent orchestrator
│   │   ├── cli.py               # Command-line interface
│   │   ├── config.py            # Configuration loader
│   │   ├── client.py            # Helios API client
│   │   └── sources/             # Pluggable metric sources
│   │       ├── base.py          # MetricsSource interface
│   │       ├── registry.py      # Source registration
│   │       ├── system.py        # Local system metrics
│   │       ├── prometheus.py    # Prometheus backend
│   │       ├── datadog.py       # Datadog backend
│   │       ├── cloudwatch.py    # AWS CloudWatch
│   │       ├── azure_monitor.py # Azure Monitor
│   │       └── gcp_monitoring.py# GCP Cloud Monitoring
│   └── pyproject.toml
│
├── ml/                          # Machine Learning
│   ├── config.py                # Configuration
│   ├── train.py                 # Training pipeline
│   ├── pipeline/                # Data processing
│   │   ├── data_fetcher.py      # Cloud metrics fetcher
│   │   └── feature_engineering.py
│   ├── models/                  # ML models
│   │   ├── baseline.py          # Moving Average + Trend
│   │   ├── prophet_model.py     # Prophet forecasting
│   │   └── xgboost_anomaly.py   # XGBoost anomaly detection
│   └── inference/               # Inference service (Phase 5)
│       ├── app.py               # FastAPI application
│       └── ...
│
├── infra/                       # Infrastructure
│   ├── terraform/               # IaC for GCP/AWS/Azure
│   │   └── gcp/
│   │       ├── main.tf
│   │       └── modules/
│   │           ├── gke/         # Kubernetes cluster
│   │           ├── cloudsql/    # PostgreSQL database
│   │           ├── redis/       # Memorystore cache
│   │           └── ...
│   └── kubernetes/              # K8s manifests
│       ├── saleor/              # Demo application
│       ├── locust/              # Load testing
│       ├── monitoring/          # Prometheus + Grafana
│       └── helios-inference/    # ML inference service
│
├── loadtest/                    # Load testing
│   └── locustfiles/             # Locust scenarios
│       ├── locustfile.py        # Main test file
│       └── personas/            # User personas
│
└── docs/                        # Documentation
    └── architecture/
        └── ARCHITECTURE.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Kubernetes cluster (GKE, EKS, AKS, or local)
- kubectl configured
- Terraform (for infrastructure provisioning)
- Google Cloud SDK (for GCP deployment)

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/helios.git
cd helios
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r ml/requirements.txt
```

### 2. Configure Your Project

Use the setup script to configure Helios with your GCP project:

```bash
# Linux/Mac
./scripts/setup.sh YOUR_GCP_PROJECT_ID

# Windows PowerShell
.\scripts\setup.ps1 -ProjectId YOUR_GCP_PROJECT_ID
```

This will:
- Create a `.env` file with your project configuration
- Update Kubernetes manifests with your project ID
- Set up all required environment variables

Alternatively, configure manually:

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your values
# GCP_PROJECT_ID=your-project-id
# GCP_REGION=us-central1
```

### 3. Authenticate with Cloud Provider

```bash
# For GCP
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud auth application-default login

# For AWS
export AWS_PROFILE=your-profile

# For Azure
az login
```

### 3. Train Models

```bash
cd ml
python train.py
```

### 4. Deploy Infrastructure

```bash
cd infra/terraform/gcp
terraform init
terraform apply
```

### 5. Deploy Inference Service

```bash
kubectl apply -k infra/kubernetes/helios-inference/
```

---

## 🤖 Helios Agent

The Helios Agent is a unified metrics collection daemon that can pull metrics from multiple backends and forward them to the Helios platform.

### Installation

```bash
# Base installation (system metrics + Prometheus)
pip install helios-agent

# With specific backends
pip install helios-agent[datadog]      # + Datadog support
pip install helios-agent[aws]          # + AWS CloudWatch
pip install helios-agent[azure]        # + Azure Monitor
pip install helios-agent[gcp]          # + GCP Cloud Monitoring
pip install helios-agent[all]          # All backends
```

### Supported Metrics Sources

| Source | Description | Requirements |
|--------|-------------|--------------|
| `system` | Local CPU, memory, disk, network via psutil | Built-in |
| `prometheus` | Query any Prometheus server | Built-in |
| `datadog` | Pull metrics from Datadog API | `pip install helios-agent[datadog]` |
| `cloudwatch` | AWS CloudWatch metrics | `pip install helios-agent[aws]` |
| `azure_monitor` | Azure Monitor metrics | `pip install helios-agent[azure]` |
| `gcp_monitoring` | Google Cloud Monitoring | `pip install helios-agent[gcp]` |

### Quick Start

```bash
# Generate a configuration file
helios-agent init

# List available metric sources
helios-agent sources

# Test configured sources
helios-agent test

# Run the agent (continuous collection)
helios-agent run

# Check agent status
helios-agent status
```

### Configuration

Create a `helios-agent.yaml` file:

```yaml
agent:
  collection_interval: 60      # seconds
  batch_size: 100
  log_level: INFO

sources:
  # Local system metrics (always recommended)
  - type: system
    enabled: true
    config:
      collect_cpu: true
      collect_memory: true
      collect_disk: true
      collect_network: true

  # Prometheus server
  - type: prometheus
    enabled: true
    config:
      url: http://prometheus:9090
      queries:
        - name: container_cpu
          query: rate(container_cpu_usage_seconds_total[5m])
        - name: container_memory
          query: container_memory_usage_bytes

  # AWS CloudWatch
  - type: cloudwatch
    enabled: false
    config:
      region: us-east-1
      namespace: AWS/EC2
      metrics:
        - CPUUtilization
        - NetworkIn
        - NetworkOut

  # Datadog
  - type: datadog
    enabled: false
    config:
      api_key: ${DATADOG_API_KEY}
      app_key: ${DATADOG_APP_KEY}
      queries:
        - avg:system.cpu.user{*}

helios:
  endpoint: http://localhost:8080
  api_key: ${HELIOS_API_KEY}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HELIOS_CONFIG_FILE` | Path to config file | `./helios-agent.yaml` |
| `HELIOS_ENDPOINT` | Helios API endpoint | `http://localhost:8080` |
| `HELIOS_API_KEY` | API key for authentication | - |
| `DATADOG_API_KEY` | Datadog API key | - |
| `DATADOG_APP_KEY` | Datadog application key | - |
| `AWS_REGION` | AWS region for CloudWatch | - |

### CLI Commands

```bash
# Initialize configuration
helios-agent init [--output FILE]

# Run agent with custom config
helios-agent run --config /path/to/config.yaml

# List registered source plugins
helios-agent sources

# Test all configured sources
helios-agent test

# Show agent status
helios-agent status

# Run single collection (for testing)
helios-agent run --once
```

### Creating Custom Sources

You can create custom metric sources by implementing the `MetricsSource` interface:

```python
from helios_agent.sources import MetricsSource, register_source, MetricSample

@register_source("custom")
class CustomSource(MetricsSource):
    """Custom metrics source."""
    
    async def initialize(self) -> None:
        # Connect to your data source
        pass
    
    async def collect(self) -> CollectionResult:
        # Fetch and return metrics
        samples = [
            MetricSample(
                name="custom_metric",
                value=42.0,
                labels={"env": "prod"}
            )
        ]
        return CollectionResult(samples=samples)
    
    async def health_check(self) -> bool:
        return True
    
    async def close(self) -> None:
        # Cleanup
        pass
```

---

## 📊 ML Models

### Model Performance (167 data points, 24-hour training)

| Model | MAE | MAPE | Notes |
|-------|-----|------|-------|
| **Baseline (MA+Trend)** | 2.5M | 2.6% | Simple, fast, reliable |
| **Prophet** | 25M | 21.1% | Better with more data, seasonality |
| **XGBoost Anomaly** | - | 0.69% rate | 1 anomaly detected |

### Feature Engineering

- **Lag features**: 1, 3, 6, 12 periods
- **Rolling statistics**: mean, std, min, max (windows: 3, 6, 12)
- **Time features**: hour, day_of_week, is_weekend, sin/cos encoding
- **Percent changes**: 1, 3 periods

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/models` | GET | List loaded models |
| `/predict` | POST | Forecast future metrics |
| `/detect` | POST | Anomaly detection scoring |
| `/recommend` | POST | Scaling recommendations |
| `/metrics` | GET | Prometheus metrics |

### Example: Get Predictions

```bash
curl -X POST http://helios-inference:8080/predict \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": {
      "cpu_utilization": 0.45,
      "memory_utilization": 0.62,
      "db_connections": 15
    },
    "periods": 12
  }'
```

### Example: Detect Anomalies

```bash
curl -X POST http://helios-inference:8080/detect \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": {
      "cpu_utilization": 0.95,
      "memory_utilization": 0.88,
      "db_connections": 150
    }
  }'
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | GCP project (for Cloud Monitoring) | - |
| `METRICS_LOOKBACK_HOURS` | Hours of historical data | 24 |
| `AGGREGATION_INTERVAL` | Metric aggregation (minutes) | 5 |
| `ANOMALY_THRESHOLD_SIGMA` | Standard deviations for anomaly | 2.5 |

### Scaling Thresholds

```yaml
scaling:
  cpu_scale_up_threshold: 0.80
  cpu_scale_down_threshold: 0.20
  memory_warning_threshold: 0.85
  min_replicas: 1
  max_replicas: 10
```

---

## 📈 Roadmap

### Completed

- [x] **Phase 1**: Infrastructure setup (Terraform + GKE)
- [x] **Phase 2**: Demo application (Saleor e-commerce)
- [x] **Phase 3**: Observability (Prometheus + Grafana)
- [x] **Phase 4**: ML pipeline (Baseline, Prophet, XGBoost)

### In Progress

- [ ] **Phase 5**: Inference service & auto-scaling integration
  - [ ] FastAPI inference service
  - [ ] Real-time scoring loop
  - [ ] KEDA predictive autoscaling
  - [ ] Grafana dashboards
  - [ ] Alertmanager integration

### Future

- [ ] **Phase 6**: Multi-cloud adapters (AWS, Azure)
- [ ] **Phase 7**: Deep learning models (LSTM, Transformer)
- [ ] **Phase 8**: Kubernetes operator

---

## 🧪 Testing

### Run Unit Tests

```bash
cd ml
pytest tests/
```

### Run Load Tests

```bash
# Deploy Locust to cluster
kubectl apply -k infra/kubernetes/locust/base

# Port-forward to UI
kubectl port-forward -n loadtest svc/locust-master 8089:8089

# Start test via API
curl -X POST http://localhost:8089/swarm \
  -d "user_count=100&spawn_rate=10&host=http://saleor-api.saleor.svc"
```

---

## 📝 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request
