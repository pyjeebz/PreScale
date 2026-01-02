"""Check what data exists in Cloud Monitoring."""
import os
from google.cloud import monitoring_v3
from datetime import datetime, timedelta

client = monitoring_v3.MetricServiceClient()
project_id = os.environ.get("GCP_PROJECT_ID", "your-gcp-project-id")
project_name = f"projects/{project_id}"

end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=12)

interval = monitoring_v3.TimeInterval(
    end_time={"seconds": int(end_time.timestamp())},
    start_time={"seconds": int(start_time.timestamp())},
)

# Check CPU metrics without namespace filter
print("=== All CPU limit_utilization data (last 12 hours) ===")
request = monitoring_v3.ListTimeSeriesRequest(
    name=project_name,
    filter='metric.type = "kubernetes.io/container/cpu/limit_utilization"',
    interval=interval,
    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.HEADERS,
)

count = 0
namespaces = set()
for ts in client.list_time_series(request=request):
    ns = ts.resource.labels.get("namespace_name", "unknown")
    namespaces.add(ns)
    count += 1

print(f"Total time series found: {count}")
print(f"Namespaces with data: {namespaces}")

# Check what resources exist
print("\n=== Checking gke_container resources ===")
request = monitoring_v3.ListTimeSeriesRequest(
    name=project_name,
    filter='resource.type = "gke_container"',
    interval=interval,
    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.HEADERS,
)

count = 0
for ts in client.list_time_series(request=request):
    count += 1
    if count <= 3:
        print(f"  Resource: {ts.resource.type}")
        print(f"  Labels: {dict(ts.resource.labels)}")
        print()
    
print(f"Total gke_container series: {count}")

# Check k8s_container resource type
print("\n=== Checking k8s_container resources ===")
request = monitoring_v3.ListTimeSeriesRequest(
    name=project_name,
    filter='resource.type = "k8s_container"',
    interval=interval,
    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.HEADERS,
)

count = 0
for ts in client.list_time_series(request=request):
    count += 1
    if count <= 3:
        print(f"  Resource: {ts.resource.type}")
        print(f"  Labels: {dict(ts.resource.labels)}")
        print()
    
print(f"Total k8s_container series: {count}")
