# Helios on AWS: Testing Guide

This guide explains how to configure and test the Helios ML Retraining service with AWS CloudWatch.

## Prerequisites

1.  **AWS Account**: Access to an AWS account with CloudWatch metrics.
2.  **Permissions**: User/Role needs `CloudWatchReadOnlyAccess` or `cloudwatch:GetMetricStatistics`.
3.  **Data**: The account should have EC2, RDS, or ELB metrics available.

## Configuration

The Helios Inference Service uses **Environment Variables** for configuration.

### 1. Set Environment Variables

Run these commands in PowerShell to configure the service for AWS:

```powershell
# 1. Select CloudWatch as Data Source (REQUIRED)
$env:RETRAIN_DATA_SOURCE = "cloudwatch"
$env:RETRAIN_ENABLED = "true"

# 2. AWS Credentials & Region
# Option A: Use standard AWS Env Vars (Recommended for local test)
$env:AWS_ACCESS_KEY_ID = "AKIA..."
$env:AWS_SECRET_ACCESS_KEY = "secret..."
$env:AWS_DEFAULT_REGION = "us-east-1"  # Change to your region

# Option B: Use AWS Profile (if you have ~/.aws/credentials)
# $env:AWS_PROFILE = "default"
# $env:AWS_DEFAULT_REGION = "us-east-1"
```

### 2. Verify Credentials

Ensure you can list metrics (requires AWS CLI installed, optional but good for verification):

```bash
aws cloudwatch list-metrics --namespace AWS/EC2
```

## Running the Service

Start the inference service:

```powershell
# In c:\Users\Windows\Desktop\helios
$env:PORT = "8001"
python -m ml.inference.app
```

You should see logs indicating the scheduler started:
`INFO: Retraining scheduler started: every 6h, source=cloudwatch`

## Triggering a Test

### Option A: Using the Dashboard

1.  Start the frontend:
    ```bash
    cd ml/inference/web
    npm run dev
    ```
2.  Open `http://localhost:3000`.
3.  The **Model Training** card should show "Data Source: cloudwatch".
4.  Click **Retrain Now**.

### Option B: Using PowerShell / curl

```powershell
# Trigger a retrain (fetch last 24h of data)
Invoke-RestMethod -Uri "http://localhost:8001/api/retrain/trigger" -Method Post -Body '{"hours": 24}' -ContentType "application/json"

# Check status
Invoke-RestMethod -Uri "http://localhost:8001/api/retrain/status"
```

## Troubleshooting

-   **"No data returned"**:
    -   Verify your `AWS_DEFAULT_REGION` matches where your resources are.
    -   The fetcher looks for specific metrics by default:
        -   `AWS/EC2`: `CPUUtilization`, `NetworkIn`, `NetworkOut`
        -   `AWS/RDS`: `CPUUtilization`
    -   If your account is new/empty, you might not have these metrics. Launch an EC2 instance to generate data.

-   **"boto3 not installed"**:
    -   Run `pip install boto3`.

-   **Authentication Errors**:
    -   Double-check your Access Key and Secret Key.
    -   Ensure the IAM user has `CloudWatchReadOnlyAccess`.
