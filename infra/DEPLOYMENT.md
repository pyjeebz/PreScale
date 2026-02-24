# Prescale Deployment Guide

Complete guide for deploying Prescale infrastructure and services.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GKE Cluster                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     prescale namespace                         │   │
│  │  ┌─────────────────┐    ┌─────────────────┐                 │   │
│  │  │ Prescale Inference│    │  Init Container │                 │   │
│  │  │   (FastAPI)     │◄───│  (GCS Download) │                 │   │
│  │  │                 │    └─────────────────┘                 │   │
│  │  │ • /predict      │                                        │   │
│  │  │ • /detect       │         ┌─────────────────┐            │   │
│  │  │ • /recommend    │◄────────│   LoadBalancer  │◄─── Internet│
│  │  │ • /metrics      │         │    Service      │            │   │
│  │  └─────────────────┘         └─────────────────┘            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   monitoring namespace                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │ Prometheus  │  │   Grafana   │  │Alertmanager │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        GCP Services                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐     │
│  │     GCS     │  │   Cloud     │  │    Cloud Monitoring     │     │
│  │   (models)  │  │   Build     │  │     (metrics source)    │     │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- GCP project with billing enabled
- gcloud CLI installed and configured
- kubectl installed
- Terraform >= 1.0 (optional, for infrastructure provisioning)

---

## Step 1: GCP Setup

```bash
# Set project ID
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# Authenticate
gcloud auth login
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable \
  container.googleapis.com \
  cloudbuild.googleapis.com \
  monitoring.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com
```

---

## Step 2: Infrastructure Provisioning

### Option A: Terraform (Recommended)

```bash
cd infra/terraform/gcp

# Initialize
terraform init

# Plan
terraform plan \
  -var="project_id=$GCP_PROJECT_ID" \
  -var="region=$GCP_REGION"

# Apply
terraform apply \
  -var="project_id=$GCP_PROJECT_ID" \
  -var="region=$GCP_REGION"
```

This creates:
- ✅ GKE Cluster
- ✅ GCS Bucket for models
- ✅ Service accounts with Workload Identity
- ✅ VPC and networking

### Option B: Manual Setup

```bash
# Create GKE cluster
gcloud container clusters create prescale-cluster \
  --region $GCP_REGION \
  --num-nodes 2 \
  --machine-type e2-medium \
  --enable-workload-identity \
  --workload-pool=${GCP_PROJECT_ID}.svc.id.goog

# Get credentials
gcloud container clusters get-credentials prescale-cluster --region $GCP_REGION

# Create GCS bucket
gsutil mb -l $GCP_REGION gs://${GCP_PROJECT_ID}-prescale-models
gsutil uniformbucketlevelaccess set on gs://${GCP_PROJECT_ID}-prescale-models
```

---

## Step 3: Build Container Image

```bash
# From project root
cd /path/to/prescale

# Build with Cloud Build
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_TAG_NAME=latest

# Verify image
gcloud container images list --repository=gcr.io/$GCP_PROJECT_ID
```

---

## Step 4: Upload ML Models

```bash
# Train models (if not already done)
cd ml
python train.py --namespace your-namespace --hours 24

# Upload to GCS
gsutil cp artifacts/cpu_forecaster/1.0.0/model.pkl \
  gs://${GCP_PROJECT_ID}-prescale-models/cpu_forecaster/1.0.0/model.pkl

gsutil cp artifacts/prophet_model.joblib \
  gs://${GCP_PROJECT_ID}-prescale-models/prophet_model.joblib

gsutil cp -r artifacts/anomaly_detector/ \
  gs://${GCP_PROJECT_ID}-prescale-models/anomaly_detector/
```

---

## Step 5: Deploy Prescale Inference

### Update Configuration

Edit `infra/kubernetes/prescale-inference/deployment.yaml`:

```yaml
# Update image
image: gcr.io/YOUR_PROJECT_ID/prescale-inference:latest

# Update GCS bucket in init container
command:
  - gsutil
  - cp
  - -r
  - gs://YOUR_PROJECT_ID-prescale-models/*
  - /models/
```

### Deploy

```bash
# Create namespace
kubectl create namespace prescale

# Apply manifests
kubectl apply -f infra/kubernetes/prescale-inference/

# Wait for deployment
kubectl wait --for=condition=available \
  deployment/prescale-inference -n prescale --timeout=300s

# Check pods
kubectl get pods -n prescale

# Check logs
kubectl logs -n prescale deploy/prescale-inference
```

### Verify Deployment

```bash
# Get external IP
kubectl get svc prescale-inference -n prescale

# Test health endpoint
curl http://EXTERNAL_IP:8080/health

# Test models endpoint
curl http://EXTERNAL_IP:8080/models
```

---

## Step 6: Deploy Monitoring (Optional)

```bash
# Create namespace
kubectl create namespace monitoring

# Deploy Prometheus + Grafana
kubectl apply -f infra/kubernetes/monitoring/

# Port-forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Access at http://localhost:3000 (admin/admin)
```

---

## Step 7: Configure Prescale Agent

Create `prescale-agent.yaml`:

```yaml
agent:
  collection_interval: 60
  log_level: INFO

sources:
  - type: gcp-monitoring
    enabled: true
    config:
      project_id: YOUR_PROJECT_ID
      metrics:
        - kubernetes.io/container/cpu/limit_utilization
        - kubernetes.io/container/memory/limit_utilization
      filters:
        namespace: your-workload-namespace

prescale:
  endpoint: http://EXTERNAL_IP:8080
```

Run the agent:

```bash
pip install prescale-agent[gcp]
prescale-agent run --config prescale-agent.yaml
```

---

## Kubernetes Manifests Reference

### Deployment

```yaml
# infra/kubernetes/prescale-inference/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prescale-inference
  namespace: prescale
spec:
  replicas: 2
  selector:
    matchLabels:
      app: prescale-inference
  template:
    spec:
      initContainers:
        - name: model-downloader
          image: gcr.io/google.com/cloudsdktool/cloud-sdk:slim
          command: ["gsutil", "cp", "-r", "gs://BUCKET/*", "/models/"]
          volumeMounts:
            - name: models
              mountPath: /models
      containers:
        - name: inference
          image: gcr.io/PROJECT/prescale-inference:latest
          ports:
            - containerPort: 8080
          env:
            - name: MODEL_PATH
              value: /models
          volumeMounts:
            - name: models
              mountPath: /models
      volumes:
        - name: models
          emptyDir: {}
```

### Service

```yaml
# infra/kubernetes/prescale-inference/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: prescale-inference
  namespace: prescale
spec:
  type: LoadBalancer
  ports:
    - port: 8080
      targetPort: 8080
  selector:
    app: prescale-inference
```

---

## Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: prescale-inference-hpa
  namespace: prescale
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: prescale-inference
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## Troubleshooting

### Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs -n prescale deploy/prescale-inference --previous

# Common issues:
# - Models not found: Check GCS bucket permissions
# - OOM: Increase memory limits
```

### Models Not Loading

```bash
# Check init container logs
kubectl logs -n prescale POD_NAME -c model-downloader

# Verify GCS access
kubectl exec -n prescale deploy/prescale-inference -- gsutil ls gs://your-bucket/
```

### Service Not Accessible

```bash
# Check service
kubectl describe svc prescale-inference -n prescale

# Check endpoints
kubectl get endpoints prescale-inference -n prescale
```

---

## Cleanup

```bash
# Delete Kubernetes resources
kubectl delete namespace prescale

# Delete GKE cluster (if using manual setup)
gcloud container clusters delete prescale-cluster --region $GCP_REGION

# Delete GCS bucket
gsutil rm -r gs://${GCP_PROJECT_ID}-prescale-models

# Or with Terraform
cd infra/terraform/gcp
terraform destroy
```
