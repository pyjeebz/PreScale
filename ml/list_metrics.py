"""List available metrics from Cloud Monitoring."""
import os
from google.cloud import monitoring_v3

client = monitoring_v3.MetricServiceClient()
project_id = os.environ.get("GCP_PROJECT_ID", "your-gcp-project-id")
project_name = f"projects/{project_id}"

# List GKE container metrics
print("=== GKE Container Metrics ===")
request = monitoring_v3.ListMetricDescriptorsRequest(
    name=project_name,
    filter='metric.type = starts_with("kubernetes.io/container")'
)
for m in client.list_metric_descriptors(request=request):
    print(f"  {m.type}")

# List Cloud SQL metrics
print("\n=== Cloud SQL Metrics ===")
request = monitoring_v3.ListMetricDescriptorsRequest(
    name=project_name,
    filter='metric.type = starts_with("cloudsql.googleapis.com")'
)
count = 0
for m in client.list_metric_descriptors(request=request):
    print(f"  {m.type}")
    count += 1
    if count > 10:
        print("  ...")
        break

# List Prometheus metrics
print("\n=== Prometheus (GKE Managed) Metrics ===")
request = monitoring_v3.ListMetricDescriptorsRequest(
    name=project_name,
    filter='metric.type = starts_with("prometheus.googleapis.com")'
)
count = 0
for m in client.list_metric_descriptors(request=request):
    print(f"  {m.type}")
    count += 1
    if count > 15:
        print("  ...")
        break
