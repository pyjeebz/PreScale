"""
AWS CloudWatch Data Fetcher for ML Training.

Mirrors CloudMonitoringFetcher but for AWS CloudWatch metrics.
Returns same DataFrame format for seamless integration with HeliosTrainingPipeline.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default CloudWatch metrics to fetch for training
DEFAULT_METRICS = {
    # EC2
    "AWS/EC2": ["CPUUtilization", "NetworkIn", "NetworkOut"],
    # RDS
    "AWS/RDS": ["CPUUtilization", "DatabaseConnections", "FreeableMemory"],
    # ELB
    "AWS/ApplicationELB": ["RequestCount", "TargetResponseTime"],
}


class CloudWatchFetcher:
    """Fetches metrics from AWS CloudWatch for ML training.

    Supports:
    - EC2 instance metrics (CPU, network)
    - RDS database metrics
    - Application Load Balancer metrics

    Returns DataFrames in the same format as CloudMonitoringFetcher
    for drop-in compatibility with HeliosTrainingPipeline.
    """

    def __init__(
        self,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize the CloudWatch fetcher.

        Args:
            region: AWS region. Defaults to us-east-1.
            aws_access_key_id: Optional AWS access key (uses default creds if not set).
            aws_secret_access_key: Optional AWS secret key.
        """
        self._region = region or "us-east-1"
        self._access_key = aws_access_key_id
        self._secret_key = aws_secret_access_key
        self._client = None

    def _get_client(self):
        """Get or create CloudWatch client."""
        if self._client is None:
            try:
                import boto3

                kwargs = {"region_name": self._region}
                if self._access_key and self._secret_key:
                    kwargs["aws_access_key_id"] = self._access_key
                    kwargs["aws_secret_access_key"] = self._secret_key

                self._client = boto3.client("cloudwatch", **kwargs)
            except ImportError:
                raise RuntimeError("boto3 is required for CloudWatch: pip install boto3")

        return self._client

    def fetch_metric(
        self,
        namespace: str,
        metric_name: str,
        hours: int = 6,
        period: int = 300,
        dimensions: Optional[list[dict]] = None,
    ) -> pd.DataFrame:
        """Fetch a single CloudWatch metric as a DataFrame.

        Args:
            namespace: AWS namespace (e.g., "AWS/EC2")
            metric_name: Metric name (e.g., "CPUUtilization")
            hours: Hours of historical data
            period: Aggregation period in seconds (default 5 min)
            dimensions: Optional dimension filters

        Returns:
            DataFrame with timestamp and value columns
        """
        client = self._get_client()

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        kwargs = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "StartTime": start_time,
            "EndTime": end_time,
            "Period": period,
            "Statistics": ["Average"],
        }

        if dimensions:
            kwargs["Dimensions"] = dimensions

        try:
            response = client.get_metric_statistics(**kwargs)
            datapoints = response.get("Datapoints", [])

            if not datapoints:
                logger.warning(f"No data for {namespace}/{metric_name}")
                return pd.DataFrame()

            # Sort by timestamp
            datapoints.sort(key=lambda x: x["Timestamp"])

            records = []
            for dp in datapoints:
                records.append({
                    "timestamp": dp["Timestamp"].replace(tzinfo=None),
                    "value": dp.get("Average", 0.0),
                })

            return pd.DataFrame(records)

        except Exception as e:
            logger.error(f"Error fetching {namespace}/{metric_name}: {e}")
            return pd.DataFrame()

    def fetch_all_metrics(
        self,
        hours: int = 6,
        dimensions: Optional[dict[str, list[dict]]] = None,
    ) -> pd.DataFrame:
        """Fetch all default metrics and combine into a single DataFrame.

        This is the main method for ML training data.

        Args:
            hours: Hours of historical data
            dimensions: Optional per-namespace dimensions
                        e.g., {"AWS/EC2": [{"Name": "InstanceId", "Value": "i-xxx"}]}

        Returns:
            Combined DataFrame ready for feature engineering
        """
        all_dfs = []
        columns_map = {}

        for namespace, metrics in DEFAULT_METRICS.items():
            ns_dims = None
            if dimensions and namespace in dimensions:
                ns_dims = dimensions[namespace]

            for metric_name in metrics:
                df = self.fetch_metric(
                    namespace=namespace,
                    metric_name=metric_name,
                    hours=hours,
                    dimensions=ns_dims,
                )

                if df.empty:
                    continue

                # Normalize column name: AWS/EC2/CPUUtilization -> ec2_cpu_utilization
                ns_short = namespace.split("/")[-1].lower()
                col_name = f"{ns_short}_{self._camel_to_snake(metric_name)}"

                df = df.rename(columns={"value": col_name})
                columns_map[metric_name] = col_name
                all_dfs.append(df)

        if not all_dfs:
            logger.warning("No CloudWatch data retrieved")
            return pd.DataFrame()

        # Merge all on timestamp
        result = all_dfs[0]
        for df in all_dfs[1:]:
            result = pd.merge(result, df, on="timestamp", how="outer")

        # Round timestamps to nearest 5 minutes
        result["timestamp"] = pd.to_datetime(result["timestamp"])
        result["timestamp"] = result["timestamp"].dt.round("5min")

        # Group by rounded timestamp and take mean
        result = result.groupby("timestamp").mean().reset_index()
        result = result.sort_values("timestamp").reset_index(drop=True)

        logger.info(
            f"CloudWatch: fetched {len(result)} records, "
            f"{len(result.columns) - 1} metrics over {hours}h"
        )
        return result

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        return s
