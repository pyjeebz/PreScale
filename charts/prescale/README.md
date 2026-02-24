# Prescale Helm Chart

Predictive Infrastructure Intelligence Platform - ML-powered resource forecasting and anomaly detection for Kubernetes.

## Prerequisites

- Kubernetes 1.23+
- Helm 3.x
- Prometheus (optional, for metrics collection)

## Installation

```bash
# Add the Prescale Helm repository
helm repo add prescale https://pyjeebz.github.io/prescale
helm repo update

# Install Prescale
helm install prescale prescale/prescale --namespace prescale --create-namespace
```

### Install from local chart

```bash
helm install prescale ./charts/prescale --namespace prescale --create-namespace
```

## Configuration

See [values.yaml](values.yaml) for the full list of configurable parameters.

### Common configurations

#### Basic installation

```yaml
# values-basic.yaml
inference:
  enabled: true
  replicaCount: 2

costIntelligence:
  enabled: true
```

#### Production installation

```yaml
# values-production.yaml
inference:
  enabled: true
  replicaCount: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
    requests:
      cpu: 1000m
      memory: 2Gi
  ingress:
    enabled: true
    className: nginx
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt-prod
    hosts:
      - host: prescale.example.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: prescale-tls
        hosts:
          - prescale.example.com

costIntelligence:
  enabled: true
  replicaCount: 2

models:
  persistence:
    enabled: true
    size: 10Gi

prometheus:
  serviceMonitor:
    enabled: true
```

### Install with custom values

```bash
helm install prescale prescale/prescale \
  --namespace prescale \
  --create-namespace \
  -f values-production.yaml
```

## Upgrading

```bash
helm upgrade prescale prescale/prescale --namespace prescale -f values.yaml
```

## Uninstalling

```bash
helm uninstall prescale --namespace prescale
```

## Components

| Component | Description |
|-----------|-------------|
| Inference Service | ML prediction API for CPU/memory forecasting |
| Cost Intelligence | Resource cost analysis and recommendations |

## API Endpoints

### Inference Service (port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Generate resource predictions |
| `/detect` | POST | Detect anomalies in metrics |
| `/recommend` | POST | Get scaling recommendations |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

### Cost Intelligence (port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Analyze resource costs |
| `/recommendations` | GET | Get cost optimization recommendations |
| `/health` | GET | Health check |

## License

Apache License 2.0
