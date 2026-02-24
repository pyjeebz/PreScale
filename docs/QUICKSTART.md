# Prescale Quick Start Guide

Get Prescale running in minutes with this step-by-step guide.

## Prerequisites

- Python 3.11+
- Docker (for local development)
- kubectl (for Kubernetes deployment)
- gcloud CLI (for GCP deployment)

---

## Option 1: Local Development (Docker)

The fastest way to try Prescale locally.

```bash
# Clone the repository
git clone https://github.com/pyjeebz/prescale.git
cd prescale

# Start inference service
docker compose up -d inference

# Verify it's running
curl http://localhost:8080/health
# {"status": "healthy", "models_loaded": 3}

# Test prediction endpoint
curl -X POST http://localhost:8080/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"deployment": "test", "namespace": "default", "metric": "cpu", "periods": 6}'
```

---

## Option 2: GCP Deployment (Production)

Deploy Prescale to Google Kubernetes Engine with GCP Cloud Monitoring integration.

### Step 1: Setup GCP Project

```bash
# Set your project ID
export GCP_PROJECT_ID="your-gcp-project-id"

# Authenticate
gcloud auth login
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable \
  container.googleapis.com \
  cloudbuild.googleapis.com \
  monitoring.googleapis.com \
  storage.googleapis.com
```

### Step 2: Create GKE Cluster (if needed)

```bash
# Create cluster
gcloud container clusters create prescale-cluster \
  --region us-central1 \
  --num-nodes 2 \
  --machine-type e2-medium

# Get credentials
gcloud container clusters get-credentials prescale-cluster --region us-central1
```

### Step 3: Create GCS Bucket for Models

```bash
# Create bucket
gsutil mb gs://${GCP_PROJECT_ID}-prescale-models

# Enable uniform bucket-level access
gsutil uniformbucketlevelaccess set on gs://${GCP_PROJECT_ID}-prescale-models
```

### Step 4: Train Models (Optional)

Train on your GCP Cloud Monitoring data:

```bash
# Setup Python environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r ml/requirements.txt

# Train models
cd ml
python train.py --namespace your-namespace --hours 24

# Upload to GCS
gsutil cp -r artifacts/* gs://${GCP_PROJECT_ID}-prescale-models/
```

### Step 5: Deploy Inference Service

```bash
# Build container image
gcloud builds submit --config cloudbuild.yaml

# Update deployment with your project ID
sed -i "s/GCP_PROJECT_ID/$GCP_PROJECT_ID/g" infra/kubernetes/prescale-inference/deployment.yaml

# Deploy to GKE
kubectl create namespace prescale
kubectl apply -f infra/kubernetes/prescale-inference/

# Wait for deployment
kubectl wait --for=condition=available deployment/prescale-inference -n prescale --timeout=300s

# Get external IP
kubectl get svc prescale-inference -n prescale
```

### Step 6: Install CLI & Agent

```bash
# Install CLI
pip install prescale-cli

# Install agent with GCP support
pip install prescale-agent[gcp]
```

### Step 7: Configure Agent

Create `prescale-agent.yaml`:

```yaml
agent:
  collection_interval: 60
  log_level: INFO

sources:
  - type: gcp-monitoring
    enabled: true
    config:
      project_id: your-gcp-project-id
      metrics:
        - kubernetes.io/container/cpu/limit_utilization
        - kubernetes.io/container/memory/limit_utilization
      filters:
        namespace: your-namespace

prescale:
  endpoint: http://EXTERNAL_IP:8080  # Replace with actual IP
```

### Step 8: Run Agent

```bash
# Test collection
prescale-agent run --config prescale-agent.yaml --once

# Run continuously
prescale-agent run --config prescale-agent.yaml
```

### Step 9: Use CLI

```bash
# Set endpoint
export PRESCALE_ENDPOINT="http://EXTERNAL_IP:8080"

# Get predictions
prescale predict cpu --deployment your-app --namespace your-namespace

# Detect anomalies
prescale detect --deployment your-app --namespace your-namespace

# Get recommendations
prescale recommend --deployment your-app --namespace your-namespace --replicas 2
```

---

## Option 3: Helm Installation

For existing Kubernetes clusters:

```bash
# Add Helm repo
helm repo add prescale https://pyjeebz.github.io/prescale
helm repo update

# Install
helm install prescale prescale/prescale \
  --namespace prescale \
  --create-namespace \
  --set inference.image.tag=latest

# Verify
kubectl get pods -n prescale
```

---

## Verify Installation

### Check Service Health

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "models_loaded": 3,
  "models": ["baseline", "prophet", "xgboost"]
}
```

### Check Models

```bash
curl http://localhost:8080/models
```

### Test Prediction

```bash
curl -X POST http://localhost:8080/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "deployment": "test-app",
    "namespace": "default",
    "metric": "cpu",
    "periods": 12
  }'
```

---

## Next Steps

1. **Configure Alerting**: Set up Prometheus alerts based on Prescale predictions
2. **Enable KEDA**: Use predictions for predictive autoscaling
3. **Grafana Dashboards**: Import Prescale dashboards for visualization
4. **Web Dashboard**: Deploy the upcoming web UI for ClickOps management

---

## Troubleshooting

### Models Not Loading

```bash
# Check pod logs
kubectl logs -n prescale deploy/prescale-inference

# Verify GCS bucket access
gsutil ls gs://your-bucket/
```

### Agent Not Collecting

```bash
# Test with --once flag
prescale-agent run --config prescale-agent.yaml --once

# Check GCP permissions
gcloud projects get-iam-policy $GCP_PROJECT_ID
```

### Connection Refused

```bash
# Check service is running
kubectl get svc -n prescale

# Verify endpoint
curl http://your-endpoint:8080/health
```

---

## Support

- GitHub Issues: https://github.com/pyjeebz/prescale/issues
- Documentation: https://github.com/pyjeebz/prescale/tree/main/docs
