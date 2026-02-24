# Prescale Examples

Demo environments and examples for testing Prescale capabilities.

> **Note**: These are for testing and demos only, not part of the core Prescale product.

## Contents

### demo-environment/

A complete test environment with:

| Component | Description |
|-----------|-------------|
| `kubernetes/` | K8s manifests for demo apps |
| `loadtest/` | Locust load testing scripts |
| `data/` | Sample metrics data |

## Quick Start

### Deploy Load Test Environment

```bash
# Create namespace
kubectl create namespace loadtest

# Deploy Locust load testing
kubectl apply -f demo-environment/kubernetes/locust/

# Wait for pods
kubectl wait --for=condition=ready pod -l app=locust-master -n loadtest --timeout=120s
```

### Access Locust UI

```bash
# Port-forward (or use LoadBalancer)
kubectl port-forward svc/locust-master 8089:8089 -n loadtest

# Open http://localhost:8089
```

### Run Load Test

1. Open Locust UI at http://localhost:8089
2. Set target host (e.g., `http://your-app-service`)
3. Configure users: 50 users, spawn rate 5/s
4. Click "Start swarming"

## Using with Prescale

### Collect Metrics from Load Test

```yaml
# prescale-agent.yaml
sources:
  - type: gcp-monitoring
    enabled: true
    config:
      project_id: your-project
      filters:
        namespace: loadtest
```

### Train Models on Load Test Data

```bash
cd ml
python train.py --namespace loadtest --hours 24
```

### Test Predictions

```bash
# After training
prescale predict cpu --deployment locust-worker --namespace loadtest
prescale detect --deployment locust-worker --namespace loadtest
```

## Sample Data

The `data/` directory contains sample metrics for offline testing:

```bash
# Use sample data for training without cloud access
python train.py --data-file examples/demo-environment/data/sample_metrics.json
```

## What Ships to Customers

Customers receive only the **core Prescale product**:

- ✅ Prescale Agent
- ✅ Prescale CLI
- ✅ Inference Service
- ✅ Helm Charts
- ✅ Documentation

These demo environments are for internal development and testing only.
