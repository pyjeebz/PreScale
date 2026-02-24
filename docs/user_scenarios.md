# Prescale Deployment Scenarios

Prescale is designed to be flexible. Whether you are a solo developer or an enterprise SRE team, you can deploy Prescale to fit your infrastructure.

## Architecture Overview

Prescale consists of two main components:
1.  **Prescale Server (The Brain)**:
    *   **Backend**: Python FastAPI service (Inference, Anomaly Detection).
    *   **Frontend**: Vue.js Web Dashboard.
    *   **Storage**: SQLite (default) or PostgreSQL.
2.  **Prescale Agent (The Eyes)**:
    *   Python service running on *each* server/node you want to monitor.

---

## Scenario 1: The Local Developer & Tester
**Best For:** Evaluating Prescale, developing plugins, or monitoring your local dev machine.

In this setup, everything runs on your laptop.

### Setup
1.  **Backend**: Run via Docker Compose.
    ```bash
    docker-compose up -d inference
    ```
2.  **Frontend**: Run locally with Node.js.
    ```bash
    cd ml/inference/web
    npm run dev
    ```
3.  **Agent**: Run locally to monitor your own machine.
    ```bash
    pip install prescale-agent
    export PRESCALE_ENDPOINT="http://localhost:8080"
    prescale-agent run
    ```

---

## Scenario 2: The "v1" Production Setup (Small Team)
**Best For:** Startups, Homelabs, or specific project monitoring.

You deploy the Prescale Server on a dedicated VM (e.g., AWS EC2, GCP Compute Engine, DigitalOcean Droplet) and install agents on your application servers.

### Architecture
*   **1 x VM (e.g., Ubuntu)**: Runs Prescale Backend + Frontend.
*   **N x App Servers**: Run Prescale Agent.

### Setup
1.  **Provision VM**: follow the [GCP Deployment Guide](deployment_to_gcp_vm.md).
2.  **Network**: Open ports `8080` (API) and `3000` (UI).
3.  **Agents**: On your app servers (DB, Web, Worker), install and point to your VM.
    ```bash
    export PRESCALE_ENDPOINT="http://<YOUR_VM_IP>:8080"
    prescale-agent run
    ```

---

## Scenario 3: The "Cloud Native" Setup (Kubernetes)
**Best For:** Large scale deployments, SRE teams.

Prescale Server runs as a Service in your K8s cluster. Agents run as a **DaemonSet**, ensuring every node in your cluster is automatically monitored.

### Setup
1.  **Prescale Server Deployment**:
    *   Deploy `prescale-backend` Deployment + Service.
    *   Deploy `prescale-frontend` Deployment + Service (LoadBalancer/Ingress).
2.  **Agent DaemonSet**:
    ```yaml
    apiVersion: apps/v1
    kind: DaemonSet
    metadata:
      name: prescale-agent
    spec:
      template:
        spec:
          containers:
          - name: agent
            image: prescale-agent:latest
            env:
            - name: PRESCALE_ENDPOINT
              value: "http://prescale-backend.default.svc.cluster.local:8080"
    ```

---

## Scenario 4: The Hybrid / Multi-Cloud Monitor
**Best For:** Enterprises with on-prem legacy servers AND cloud resources.

Prescale Server acts as a central hub. Agents from different environments connect back to it.

### Architecture
*   **Central Hub**: Prescale Server running in a robust location (e.g., Cluster or Main Region).
*   **Edge Agents**:
    *   **On-Prem Server**: Agent installed via `pip`.
    *   **AWS EC2**: Agent via UserData script.
    *   **GCP VM**: Agent via Startup script.

### Configuration
*   **Public Access**: The Prescale Server needs a public IP or DNS (e.g., `monitor.company.com`).
*   **Security**: Use API Keys (configured in `config.py`) to prevent unauthorized agents from pushing data.
