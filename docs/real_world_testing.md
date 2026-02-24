# Real-World Scenario Testing Guide for Prescale

This guide explains how to validate Prescale in a realistic environment by running the agent on a separate machine (or simulated VM) and generating synthetic load.

## 1. Prerequisites
- **Prescale Server**: Identifying your machine's IP address.
- **Target Machine**: A Linux VM (Ubuntu/Debian recommended) or a Docker container to act as the "Production Server".
- **Traffic Generator**: `stress-ng` (Linux) or similar.

---

## 2. Server Setup (Your Dev Machine)
Ensure Prescale is running and accessible from outside localhost.

1. **Find your Local IP**:
   ```bash
   # Windows PowerShell
   ipconfig
   # Look for IPv4 Address (e.g., 192.168.1.50)
   ```

2. **Start Prescale Backend**:
   Ensure it listens on `0.0.0.0` (all interfaces), not just `127.0.0.1`.
   ```bash
   # In c:\Users\Windows\Desktop\prescale
   $env:HOST="0.0.0.0"
   $env:PORT="8080"
   python -m prescale.ml.inference.app
   ```
   *Note: If using `uvicorn` directly, add `--host 0.0.0.0`.*

---

## 3. Agent Setup (The "Real World" Server)

### Option A: Using Docker (Quickest)
If you have Docker, you can simulate a separate server instantly.

1. **Run the Agent Container**:
   Replace `YOUR_PC_IP` with your actual IP (e.g., `192.168.1.50`).
   ```bash
   docker run -d --name production-db-node \
     -e PRESCALE_ENDPOINT="http://YOUR_PC_IP:8080" \
     -e PRESCALE_DEPLOYMENT="production-cluster" \
     --network host \
     prescale-agent:latest
   ```

### Option B: Using a Linux VM/VPS
If you have a cloud VM (AWS/GCP) or local VM (VirtualBox/WSL2).

1. **Install Python & Pip**:
   ```bash
   sudo apt update && sudo apt install -y python3-pip stress-ng
   ```

2. **Install Prescale Agent**:
   ```bash
   pip install prescale-agent
   ```

3. **Run the Agent**:
   ```bash
   export PRESCALE_ENDPOINT="http://YOUR_PC_IP:8080"
   export PRESCALE_DEPLOYMENT="production-cluster"
   prescale-agent run
   ```

---

## 4. Scenario: The "Memory Leak" Simulation
Let's trick Prescale into thinking there's an anomaly.

1. **Go to Prescale Dashboard**:
   - Create a new deployment called `production-cluster` (if not auto-created).
   - Verify the agent `production-db-node` is **Online**.

2. **Generate Normal Load (Baseline)**:
   Let the agent run for ~5 minutes to establish a baseline.
   - CPU: ~10-20%
   - Memory: Stable.

3. **Trigger the Incident**:
   Run `stress-ng` on the target machine (or inside the Docker container) to simulate a memory leak and CPU spike.

   ```bash
   # Simulate high load: 2 CPU cores, growing memory usage
   stress-ng --cpu 2 --vm 1 --vm-bytes 500M --timeout 60s
   ```

4. **Observe in Prescale**:
   - **Real-time**: Watch the **Dashboard** CPU/Memory gauges spike.
   - **Predictions**: See the **Predictions** graph diverge from the baseline (green line).
   - **Anomalies**: Wait ~1-2 minutes. Go to the **Anomalies** tab. You should see a `Critical` or `High` severity anomaly detected for `cpu_percent` or `memory_percent`.

---

## 5. Scenario: Network Failure
Simulate an agent disconnection to test resilience.

1. **Kill the Agent**:
   - Docker: `docker stop production-db-node`
   - Linux: `Ctrl+C` or `kill <pid>`
2. **Observe**:
   - The Agent status on the **Agents** page should turn **Offline** (Red) after the heartbeat timeout (usually ~30-60s).

## Summary
By separating the Agent from the Server and injecting synthetic faults (`stress-ng`), you demonstrate Prescale's true value: **Observability without access to the machine itself.**
