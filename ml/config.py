"""
Helios ML Configuration

Central configuration for GCP project, metrics, and model parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GCPConfig:
    """GCP-specific configuration."""
    project_id: str = "gen-lang-client-0702968356"
    region: str = "us-central1"
    gke_cluster: str = "helios-dev-gke"


@dataclass
class MetricsConfig:
    """Metrics to fetch from Cloud Monitoring."""
    
    # GKE Container metrics (auto-collected)
    container_metrics: List[str] = field(default_factory=lambda: [
        "kubernetes.io/container/cpu/core_usage_time",
        "kubernetes.io/container/memory/used_bytes",
        "kubernetes.io/container/restart_count",
    ])
    
    # Cloud SQL metrics (auto-collected)
    cloudsql_metrics: List[str] = field(default_factory=lambda: [
        "cloudsql.googleapis.com/database/cpu/utilization",
        "cloudsql.googleapis.com/database/memory/utilization",
        "cloudsql.googleapis.com/database/postgresql/num_backends",
    ])
    
    # Redis/Memorystore metrics (auto-collected)
    redis_metrics: List[str] = field(default_factory=lambda: [
        "redis.googleapis.com/stats/memory/usage_ratio",
        "redis.googleapis.com/stats/connected_clients",
    ])
    
    # Prometheus metrics via GKE Managed Prometheus
    prometheus_metrics: List[str] = field(default_factory=lambda: [
        "prometheus.googleapis.com/locust_requests_total/counter",
        "prometheus.googleapis.com/locust_request_latency_seconds/histogram",
        "prometheus.googleapis.com/locust_users/gauge",
    ])


@dataclass
class ModelConfig:
    """Model hyperparameters."""
    
    # Baseline model
    moving_average_window: int = 12  # 12 x 5min = 1 hour
    trend_window: int = 24  # For linear trend calculation
    
    # Prophet model
    prophet_seasonality_mode: str = "multiplicative"
    prophet_changepoint_prior_scale: float = 0.05
    prophet_forecast_periods: int = 12  # Forecast 12 periods ahead
    
    # XGBoost anomaly detector
    xgb_n_estimators: int = 100
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.1
    anomaly_threshold_sigma: float = 2.5  # Standard deviations


@dataclass
class HeliosConfig:
    """Main configuration container."""
    gcp: GCPConfig = field(default_factory=GCPConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    
    # Data settings
    default_lookback_hours: int = 24  # 24 hours for more data
    aggregation_interval_minutes: int = 5


# Global config instance
config = HeliosConfig()
