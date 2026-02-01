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

**Docker:**
```bash
docker run -d -p 8080:8080 ghcr.io/pyjeebz/helios/inference:latest
```

**Kubernetes (Helm):**
```bash
helm repo add helios https://pyjeebz.github.io/helios
helm install helios helios/helios
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
| **Multi-Cloud Support** | GCP Cloud Monitoring, AWS CloudWatch, Azure Monitor, Prometheus |
| **CLI Tools** | `helios` CLI for predictions, anomaly detection, and recommendations |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HELIOS PLATFORM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────────┐     │
│  │   Helios Agent   │───▶│   ML Pipeline   │───▶│  Inference Service  │     │
│  │   (pluggable)    │    │   (training)    │    │     (FastAPI)       │     │
│  │                  │    │                 │    │                     │     │
│  │ • GCP Monitoring │    │ • Baseline      │    │ POST /predict       │     │
│  │ • AWS CloudWatch │    │ • Prophet       │    │ POST /detect        │     │
│  │ • Azure Monitor  │    │ • XGBoost       │    │ POST /recommend     │     │
│  │ • Prometheus     │    │                 │    │ GET  /metrics       │     │
│  └──────────────────┘    └─────────────────┘    └──────────┬──────────┘     │
│                                                             │                │
│           ┌─────────────────────────────────────────────────┼────────────┐   │
│           │                                                 │            │   │
│           ▼                                                 ▼            ▼   │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  ┌───────────┐     │
│    │     GCS     │    │    KEDA     │    │ Helios CLI  │  │  Grafana  │     │
│    │   (models)  │    │ (autoscale) │    │  (commands) │  │(dashboard)│     │
│    └─────────────┘    └─────────────┘    └─────────────┘  └───────────┘     │
│                                                                              │
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
│   │   └── sources/             # Pluggable metric sources
│   │       ├── prometheus.py    # Prometheus backend
│   │       ├── cloudwatch.py    # AWS CloudWatch
│   │       ├── azure_monitor.py # Azure Monitor
│   │       └── gcp_monitoring.py# GCP Cloud Monitoring
│   └── pyproject.toml
│
├── cli/                         # Helios CLI
│   ├── src/helios_cli/
│   │   └── commands/            # predict, detect, recommend
│   └── pyproject.toml
│
├── ml/                          # Machine Learning
│   ├── config.py                # Configuration
│   ├── train.py                 # Training pipeline
│   ├── models/                  # ML models
│   │   ├── baseline.py          # Moving Average + Trend
│   │   ├── prophet_model.py     # Prophet forecasting
│   │   └── xgboost_anomaly.py   # XGBoost anomaly detection
│   └── inference/               # Inference service
│       ├── app.py               # FastAPI application
│       ├── model_manager.py     # Model loading & serving
│       └── Dockerfile
│
├── infra/                       # Infrastructure
│   ├── terraform/gcp/           # GCP Terraform modules
│   └── kubernetes/              # K8s manifests
│       ├── helios-inference/    # Inference deployment
│       └── monitoring/          # Prometheus + Grafana
│
├── charts/helios/               # Helm chart
└── docs/                        # Documentation
```

---

## 🤖 Helios Agent

The Helios Agent collects metrics from multiple backends and forwards them to the inference service.

### Installation

```bash
# Base installation
pip install helios-agent

# With cloud backends
pip install helios-agent[gcp]      # + GCP Cloud Monitoring
pip install helios-agent[aws]      # + AWS CloudWatch
pip install helios-agent[azure]    # + Azure Monitor
pip install helios-agent[all]      # All backends
```

### Configuration

Create `helios-agent.yaml`:

```yaml
agent:
  collection_interval: 60
  log_level: INFO

sources:
  # GCP Cloud Monitoring
  - type: gcp-monitoring
    enabled: true
    config:
      project_id: your-gcp-project-id
      metrics:
        - kubernetes.io/container/cpu/limit_utilization
        - kubernetes.io/container/memory/limit_utilization
      filters:
        namespace: your-namespace

  # Prometheus
  - type: prometheus
    enabled: true
    config:
      url: http://prometheus:9090
      queries:
        - name: cpu_usage
          query: rate(container_cpu_usage_seconds_total[5m])

helios:
  endpoint: http://helios-inference:8080
```

### Usage

```bash
# Initialize config
helios-agent init

# Run agent (continuous)
helios-agent run --config helios-agent.yaml

# Single collection (testing)
helios-agent run --once
```

---

## 🖥️ Helios CLI

Command-line interface for predictions, anomaly detection, and scaling recommendations.

### Installation

```bash
pip install helios-cli
```

### Commands

```bash
# Predict CPU utilization for a deployment
helios predict cpu --deployment my-app --namespace default

# Detect anomalies
helios detect --deployment my-app --namespace default

# Get scaling recommendations
helios recommend --deployment my-app --namespace default --replicas 2
```

### Configuration

```bash
# Set inference endpoint
export HELIOS_ENDPOINT="http://helios-inference:8080"

# Or use config file
helios config set endpoint http://helios-inference:8080
```

---

## 🧠 ML Training

Train models on your infrastructure metrics:

```bash
cd ml

# Train on GCP Cloud Monitoring data
python train.py --namespace loadtest --hours 24 --target cpu_utilization

# Models saved to artifacts/
# - cpu_forecaster/     (Baseline model)
# - prophet_model.joblib (Prophet model)
# - anomaly_detector/   (XGBoost model)
```

### Model Performance

| Model | Type | Use Case |
|-------|------|----------|
| **Baseline** | Moving Average + Trend | Fast, reliable forecasting |
| **Prophet** | Time-series decomposition | Seasonality detection |
| **XGBoost** | Gradient boosting | Anomaly detection |

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/models` | GET | List loaded models |
| `/api/v1/predict` | POST | Forecast future metrics |
| `/api/v1/detect` | POST | Anomaly detection |
| `/api/v1/recommend` | POST | Scaling recommendations |
| `/api/v1/ingest` | POST | Ingest metrics from agent |
| `/metrics` | GET | Prometheus metrics |

### Example: Get Predictions

```bash
curl -X POST http://localhost:8080/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "deployment": "my-app",
    "namespace": "default",
    "metric": "cpu",
    "periods": 12
  }'
```

### Example: Detect Anomalies

```bash
curl -X POST http://localhost:8080/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{
    "deployment": "my-app",
    "namespace": "default"
  }'
```

### Example: Get Recommendations

```bash
curl -X POST http://localhost:8080/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "deployment": "my-app",
    "namespace": "default",
    "current_replicas": 2
  }'
```

---

## ☸️ Kubernetes Deployment

### Using Helm

```bash
helm repo add helios https://pyjeebz.github.io/helios
helm install helios helios/helios \
  --set inference.image.tag=latest \
  --set gcs.bucket=your-model-bucket
```

### Using kubectl

```bash
# Deploy inference service
kubectl apply -f infra/kubernetes/helios-inference/

# Verify deployment
kubectl get pods -n helios
kubectl logs -n helios deploy/helios-inference
```

### GCS Model Storage

Models are stored in GCS and loaded on pod startup:

```bash
# Create bucket
gsutil mb gs://your-helios-models

# Upload trained models
gsutil cp -r ml/artifacts/* gs://your-helios-models/
```

---

## 📈 Roadmap

### ✅ Completed

- [x] Helios Agent with pluggable backends (GCP, AWS, Azure, Prometheus)
- [x] ML Pipeline (Baseline, Prophet, XGBoost models)
- [x] Inference Service (FastAPI + GCS model loading)
- [x] CLI Tools (predict, detect, recommend)
- [x] Kubernetes Deployment (Helm + manifests)

### 🚧 In Progress

- [ ] Web Dashboard (React/Next.js)
- [ ] KEDA Integration (predictive autoscaling)
- [ ] Automated Model Retraining (CronJob)

### 🔮 Future

- [ ] Multi-cluster support
- [ ] Deep learning models (LSTM, Transformer)
- [ ] Kubernetes Operator

---

## 🧪 Testing

```bash
# Run ML tests
cd ml && pytest tests/

# Test agent
cd agent && pytest

# Test CLI
cd cli && pytest
```

---

## 📝 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request
