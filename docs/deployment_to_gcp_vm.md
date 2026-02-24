# Deploying Prescale to a Google Cloud (GCP) VM

Yes, you can absolutely run Prescale on a GCP VM! This guide walks you through setting up a "Command Center" instance in the cloud.

## 1. Create a VM Instance

You can use the Google Cloud Console or the `gcloud` CLI.

**Recommended Specs:**
- **Machine Type**: `e2-medium` (2 vCPU, 4GB RAM) - Good balance for dev/test.
- **OS**: Ubuntu 22.04 LTS.
- **Firewall**: Allow HTTP/HTTPS.

### Using CLI (Quickest)
```bash
gcloud compute instances create prescale-server \
    --project=YOUR_PROJECT_ID \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server,https-server,prescale-web
```

---

## 2. Configure Firewall Rules

By default, GCP blocks external ports. We need to open:
- **8080**: Prescale Backend API
- **3000**: Prescale Frontend (Web UI)

```bash
gcloud compute firewall-rules create allow-prescale \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:8080,tcp:3000 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=prescale-web
```

---

## 3. Install Dependencies

SSH into your new VM:
```bash
gcloud compute ssh prescale-server
```

Run the following inside the VM:

```bash
# Update and install system tools
sudo apt update && sudo apt install -y git python3-pip python3-venv nodejs npm

# Install global node tools (optional but recommended)
sudo npm install -g n
sudo n stable
```

---

## 4. Deploy Prescale

### A. Clone the Repository
```bash
git clone https://github.com/your-username/prescale.git
cd prescale
```
*(Note: If using a private repo, you may need to set up an SSH key or use a Personal Access Token)*

### B. Setup Backend
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install prescale-agent  # If agent is needed on the server itself

# Run Backend (Background)
export PORT=8080
export HOST=0.0.0.0
nohup python3 -m prescale.ml.inference.app > backend.log 2>&1 &
```

### C. Setup Frontend
```bash
cd ml/inference/web

# Install dependencies
npm install

# Build for production (Recommended)
npm run build
npm run preview -- --host 0.0.0.0 --port 3000
# OR for development mode
# npm run dev -- --host 0.0.0.0 --port 3000
```

---

## 5. Access Your Prescale Instance

1.  Find your VM's **External IP**:
    ```bash
    gcloud compute instances list
    ```
2.  Open your browser:
    - **Dashboard**: `http://<EXTERNAL_IP>:3000`
    - **API Docs**: `http://<EXTERNAL_IP>:8080/docs`

## 6. Making it "Production Ready" (Optional)

For a persistent setup, consider:
1.  **Process Management**: Use `systemd` or `Supervisor` to keep the Python backend running.
2.  **Reverse Proxy**: Use **Nginx** or **Caddy** to forward port 80 to 3000/8080 so you don't need to type ports in the URL.
3.  **Docker**: Containerize the app for easier deployment (see `Dockerfile` if available).
