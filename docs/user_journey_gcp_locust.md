# User Journey: GCP & Locust Load Testing

This guide simulates a real-world "Developer" scenario:
1.  **You have an app on GCP.**
2.  **You monitor it with Prescale.**
3.  **You stress-test it with Locust.**
4.  **You watch Prescale react (Predictions, Anomalies, Recommendations).**

---

## Prerequisites (The "Third Party" Setup)

1.  **Google Cloud Project**: You need a project ID (e.g., `my-cool-project`).
2.  **GCP CLI (`gcloud`)**: Installed and authenticated.
3.  **Python 3.10+**: For running Prescale.

### Authentication
Run this once to let Prescale access your GCP metrics:
```bash
gcloud auth application-default login
```

---

## Step 1: Deploy a Target Service (The "App")

First, we need something to monitor. Let's deploy a simple "Hello World" service to **Cloud Run**.

```bash
# Deploy a sample container (Google's "hello-cloud-run")
gcloud run deploy prescale-demo-target \
  --image=gcr.io/cloudrun/hello \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated
```
*Take note of the URL provided (e.g., `https://prescale-demo-target-xyz.a.run.app`).*

---

## Step 2: Configure Prescale Backend (The "Brain")

We need to tell Prescale to pull metrics from GCP for its ML models.

### 1. Set Environment Variables
In your terminal (PowerShell or Bash), configure the backend to use GCP as the data source.

**PowerShell:**
```powershell
$env:GOOGLE_CLOUD_PROJECT = "YOUR_PROJECT_ID_HERE"
$env:RETRAIN_DATA_SOURCE = "gcp"

# Important: Lower requirements for testing so we don't have to wait 24h
$env:RETRAIN_MIN_DATA_POINTS = "12"  # Only require 1 hour of data (5-min intervals)
$env:RETRAIN_TRAINING_HOURS = "1"    # Fetch last 1 hour
```

### 2. Run the Backend
```powershell
# From prescale root directory
python -m ml.inference.app
```

### 3. Run the Frontend (New Terminal)
```powershell
cd ml/inference/web
npm run dev
```

---

## Step 3: Configure Prescale Agent (The "Eyes")

Now, we point the agent at your Cloud Run service.

### 1. Edit `prescale-agent-gcp.yaml`
Update the `metrics` and `credentials` sections.

```yaml
endpoint:
  url: "http://localhost:8080"

sources:
  - name: gcp-demo-target
    type: gcp_monitoring
    enabled: true
    interval_seconds: 60
    credentials:
      project_id: "YOUR_PROJECT_ID_HERE"
    
    # Cloud Run Metrics
    metrics:
      - "run.googleapis.com/container/cpu/utilizations"
      - "run.googleapis.com/container/memory/utilizations"
      - "run.googleapis.com/request_count"
    
    labels:
      service_name: "prescale-demo-target"
      location: "us-central1"
```

### 2. Run the Agent
```powershell
prescale-agent --config prescale-agent-gcp.yaml
```

**Check Dashboard**: Go to `http://localhost:3000/agents`. You should see `gcp-demo-target` is **Online**.

---

## Step 4: Establish a Baseline (Wait ~5-10 mins)

Prescale needs data to learn what "normal" looks like.
1.  Let the agent run for 5-10 minutes.
2.  Go to **Dashboard** -> **Model Training**.
3.  Click **"Retrain Now"**.
4.  If successful, you'll see "Last Run: Completed" and data points > 0.

*Note: If it says "Skipped (Insufficient data)", wait another 5 minutes and try again.*

---

## Step 5: The Attack (Locust Load Test)

Now we disrupt the system to trigger predictions and anomalies.

### 1. Install Locust
```bash
pip install locust
```

### 2. Create `locustfile.py`
Save this file in your root folder:

```python
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def index(self):
        self.client.get("/")
```

### 3. Launch the Attack
Run Locust pointing at your Cloud Run URL:
```bash
locust -f locustfile.py --host https://prescale-demo-target-xyz.a.run.app
```

1.  Open `http://localhost:8089` (Locust Interface).
2.  Start with **10 users**, Spawn rate **1**.
3.  Let it run for 2 minutes (Baseline traffic).
4.  **Ramp Up**: Edit the test to **500 users**, Spawn rate **50**. This causes a massive spike.

---

## Step 6: Verify Prescale Features

Go back to `http://localhost:3000`.

### 1. Predictions
*   Go to the **Predictions** tab.
*   You should see the forecast (green line) expecting low/stable traffic.
*   The actual values (blue line) will skyrocket above the confidence interval.

### 2. Anomalies
*   Wait ~1-2 minutes for the agent to report the spike.
*   Go to the **Anomalies** tab.
*   You should see a **High/Critical Severity** anomaly for `request_count` or `cpu/utilizations`.
*   Description: "Value X is significantly higher than expected Y".

### 3. Recommendations
*   Go to the **Dashboard**.
*   Look at the "AI Recommendations" card.
*   You might see: "Scale UP prescale-demo-target to 5 replicas (Reason: High CPU utilization predicted)".

---

## Summary
You have successfully:
1.  Deployed a cloud service.
2.  Connected Prescale (Backend & Agent) to it.
3.  Simulated a traffic surge with Locust.
4.  Confirmed Prescale detected the anomaly and offered a recommendation.
