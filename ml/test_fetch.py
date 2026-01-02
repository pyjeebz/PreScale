"""Test fetching real GKE metrics."""
import os
from google.cloud import monitoring_v3
from datetime import datetime, timedelta
import pandas as pd

client = monitoring_v3.MetricServiceClient()
project_id = os.environ.get("GCP_PROJECT_ID", "your-gcp-project-id")
project_name = f"projects/{project_id}"

# Time range
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=1)

# Test fetching CPU limit utilization (GAUGE metric)
print("=== Fetching kubernetes.io/container/cpu/limit_utilization ===")
interval = monitoring_v3.TimeInterval(
    end_time={"seconds": int(end_time.timestamp())},
    start_time={"seconds": int(start_time.timestamp())},
)

aggregation = monitoring_v3.Aggregation(
    alignment_period={"seconds": 300},  # 5 minutes
    per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
)

request = monitoring_v3.ListTimeSeriesRequest(
    name=project_name,
    filter='metric.type = "kubernetes.io/container/cpu/limit_utilization" AND resource.labels.namespace_name = "saleor"',
    interval=interval,
    aggregation=aggregation,
    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
)

records = []
for ts in client.list_time_series(request=request):
    container = ts.resource.labels.get("container_name", "unknown")
    for point in ts.points:
        # Handle DatetimeWithNanoseconds
        timestamp = point.interval.end_time
        if hasattr(timestamp, 'replace'):
            timestamp = timestamp.replace(tzinfo=None)
        records.append({
            "timestamp": timestamp,
            "container": container,
            "cpu_utilization": point.value.double_value,
        })

if records:
    df = pd.DataFrame(records)
    print(f"\nFound {len(df)} data points!")
    print(df.groupby("timestamp")["cpu_utilization"].mean().head(10))
else:
    print("No data found")

# Test memory
print("\n=== Fetching kubernetes.io/container/memory/used_bytes ===")
request = monitoring_v3.ListTimeSeriesRequest(
    name=project_name,
    filter='metric.type = "kubernetes.io/container/memory/used_bytes" AND resource.labels.namespace_name = "saleor"',
    interval=interval,
    aggregation=aggregation,
    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
)

records = []
for ts in client.list_time_series(request=request):
    container = ts.resource.labels.get("container_name", "unknown")
    for point in ts.points:
        timestamp = point.interval.end_time
        if hasattr(timestamp, 'replace'):
            timestamp = timestamp.replace(tzinfo=None)
        records.append({
            "timestamp": timestamp,
            "container": container,
            "memory_bytes": point.value.int64_value,
        })

if records:
    df = pd.DataFrame(records)
    df["memory_mb"] = df["memory_bytes"] / (1024 * 1024)
    print(f"\nFound {len(df)} data points!")
    print(df.groupby("timestamp")["memory_mb"].mean().head(10))
else:
    print("No data found")

# Test Cloud SQL CPU
print("\n=== Fetching cloudsql.googleapis.com/database/cpu/utilization ===")
request = monitoring_v3.ListTimeSeriesRequest(
    name=project_name,
    filter='metric.type = "cloudsql.googleapis.com/database/cpu/utilization"',
    interval=interval,
    aggregation=aggregation,
    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
)

records = []
for ts in client.list_time_series(request=request):
    for point in ts.points:
        timestamp = point.interval.end_time
        if hasattr(timestamp, 'replace'):
            timestamp = timestamp.replace(tzinfo=None)
        records.append({
            "timestamp": timestamp,
            "db_cpu_utilization": point.value.double_value,
        })

if records:
    df = pd.DataFrame(records)
    print(f"\nFound {len(df)} data points!")
    print(df.head(10))
else:
    print("No data found")
