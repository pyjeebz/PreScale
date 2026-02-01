#!/usr/bin/env python3
# probe_metrics.py
# Usage: python probe_metrics.py --project YOUR_PROJECT --hours 1

import argparse, json
from datetime import datetime, timedelta
from google.cloud import monitoring_v3

METRIC_CANDIDATES = {
  "rps": [
    "prometheus.googleapis.com/locust_requests_total",
    "prometheus.googleapis.com/http_server_requests_total",
    "prometheus.googleapis.com/requests_total",
  ],
  "latency_histogram": [
    "prometheus.googleapis.com/locust_request_latency_seconds",
    "prometheus.googleapis.com/http_server_request_latency_seconds",
    "prometheus.googleapis.com/request_latency_seconds",
  ],
  "cpu": [
    "kubernetes.io/container/cpu/core_usage_time",
    "kubernetes.io/container/cpu/usage_time",
  ],
  "memory": [
    "kubernetes.io/container/memory/used_bytes",
    "kubernetes.io/container/memory/working_set_bytes",
  ],
  "db_connections": [
    "cloudsql.googleapis.com/database/postgresql/num_backends",
    "cloudsql.googleapis.com/database/connections",
  ],
}

def probe(project: str, hours: int = 1, namespace: str | None = None):
  client = monitoring_v3.MetricServiceClient()
  now = datetime.utcnow()
  interval = monitoring_v3.TimeInterval({
    "end_time": {"seconds": int(now.timestamp())},
    "start_time": {"seconds": int((now - timedelta(hours=hours)).timestamp())},
  })

  results = {}
  for friendly, candidates in METRIC_CANDIDATES.items():
    results[friendly] = []
    for metric_type in candidates:
      # Build filter; optionally restrict to namespace if provided
      if namespace:
        filter_expr = f'metric.type="{metric_type}" AND resource.labels.namespace_name="{namespace}"'
      else:
        filter_expr = f'metric.type="{metric_type}"'

      series = client.list_time_series(
        request={
          "name": f"projects/{project}",
          "filter": filter_expr,
          "interval": interval,
          "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.HEADERS,
          "page_size": 5,
        }
      )

      pts = 0
      resources = set()
      for ts in series:
        pts += len(ts.points)
        resources.add(tuple(sorted(ts.resource.labels.items())))
      results[friendly].append({
        "metric_type": metric_type,
        "series_found": pts > 0,
        "points_count": pts,
        "resources_sample": [dict(r) for r in list(resources)[:3]],
      })
  print(json.dumps(results, indent=2))

if __name__ == "__main__":
  p = argparse.ArgumentParser()
  p.add_argument("--project", required=True)
  p.add_argument("--hours", type=int, default=1)
  p.add_argument("--namespace", default=None, help="K8s namespace to filter (e.g. saleor)")
  args = p.parse_args()
  probe(args.project, args.hours, args.namespace)