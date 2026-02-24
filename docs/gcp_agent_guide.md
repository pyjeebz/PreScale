# Prescale Agent on GCP: Usage Guide

This guide explains how to install, configure, and run the Prescale Agent on Google Cloud Platform (GCP) to collect metrics.

## 1. Installation

The Prescale Agent is distributed as a Python package. You can install it with the GCP extra to include necessary dependencies (`google-cloud-monitoring`).

```bash
# Install with GCP support
pip install prescale-agent[gcp]
```

## 2. Authentication

The agent uses **Google Application Default Credentials (ADC)**.

*   **On a GKE Cluster or Compute Engine**: 
    *   Ensure the attached Service Account has the **Monitoring Viewer** (`roles/monitoring.viewer`) IAM role.
    *   No further action is required; the agent auto-detects credentials.

*   **Locally (for testing)**:
    ```bash
    gcloud auth application-default login
    ```

## 3. Configuration

Create a configuration file named `prescale-agent.yaml`.

```yaml
# prescale-agent.yaml

# 1. Prescale Backend Endpoint
endpoint:
  url: "http://localhost:8080"  # URL of your Prescale Inference Service
  api_key: "${PRESCALE_API_KEY}"  # Optional, if auth is enabled

# 2. Configure GCP Source
sources:
  - name: gcp-production
    type: gcp_monitoring
    enabled: true
    project_id: "your-gcp-project-id"  # Optional: defaults to ADC project if omitted
    interval: 60  # Collection interval in seconds
    metrics:
      - "kubernetes.io/container/cpu/limit_utilization"
      - "kubernetes.io/container/memory/limit_utilization"
      - "kubernetes.io/container/memory/used_bytes"
```

## 4. Running the Agent

Run the agent pointing to your configuration file:

```bash
# Set API Key if using variable expansion
export PRESCALE_API_KEY="your-secret-key"

# Start the agent
prescale-agent --config prescale-agent.yaml
```

The agent will start, authenticate with GCP, fetch the configured metrics every 60 seconds, and push them to the Prescale backend.

## 5. Verification

You should see logs indicating successful collection:

```text
INFO:prescale_agent.agent:Starting Prescale Agent v0.2.0...
INFO:prescale_agent.sources.gcp:Connected to GCP Project: your-gcp-project-id
INFO:prescale_agent.agent:Collected 15 metrics from gcp-production
INFO:prescale_agent.client:Successfully pushed batch of 15 metrics to http://localhost:8080
```
