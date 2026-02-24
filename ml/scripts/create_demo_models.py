#!/usr/bin/env python3
"""
Generate Demo Models for Prescale

Creates pre-trained demo models that can be used for testing and evaluation
without requiring users to set up their own data pipelines.

Usage:
    python create_demo_models.py
    python create_demo_models.py --output-dir ./demo_models
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.baseline import BaselineModel
from models.prophet_model import ProphetForecaster
from models.xgboost_anomaly import XGBoostAnomalyDetector


def generate_synthetic_data(hours: int = 168) -> pd.DataFrame:
    """
    Generate synthetic infrastructure metrics data.
    
    Creates realistic-looking time series data with:
    - Daily seasonality (higher usage during business hours)
    - Weekly seasonality (lower on weekends)
    - Random noise
    - Occasional spikes (simulating load)
    
    Args:
        hours: Number of hours of data to generate
        
    Returns:
        DataFrame with timestamp and various metric columns
    """
    np.random.seed(42)
    
    n_points = hours * 12  # 5-minute intervals
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(hours=hours),
        periods=n_points,
        freq="5min"
    )
    
    # Time features for seasonality
    hour_of_day = timestamps.hour + timestamps.minute / 60
    day_of_week = timestamps.dayofweek
    
    # Daily pattern: higher during business hours (9-18)
    daily_pattern = np.where(
        (hour_of_day >= 9) & (hour_of_day <= 18),
        0.7 + 0.2 * np.sin((hour_of_day - 9) / 9 * np.pi),  # Peak at noon
        0.3 + 0.1 * np.sin((hour_of_day - 18) / 15 * np.pi)   # Low overnight
    )
    
    # Weekly pattern: lower on weekends
    weekly_pattern = np.where(
        day_of_week < 5,  # Weekday
        1.0,
        0.5  # Weekend
    )
    
    # Base metrics with patterns
    base = daily_pattern * weekly_pattern
    
    # CPU usage: 30-70% normally
    cpu_usage = 0.3 + 0.4 * base + np.random.randn(n_points) * 0.05
    cpu_usage = np.clip(cpu_usage, 0.1, 0.95)
    
    # Memory usage: more stable, 50-80%
    memory_usage = 0.5 + 0.25 * base + np.random.randn(n_points) * 0.03
    memory_usage = np.clip(memory_usage, 0.3, 0.95)
    
    # Request rate: correlates with CPU
    rps = 500 + 1500 * base + np.random.randn(n_points) * 50
    rps = np.clip(rps, 50, 3000)
    
    # Latency: inversely correlates with capacity headroom
    latency = 50 + 100 * (cpu_usage - 0.3) + np.random.randn(n_points) * 10
    latency = np.clip(latency, 20, 500)
    
    # Error rate: spikes when CPU is high
    error_rate = np.where(
        cpu_usage > 0.8,
        0.05 + np.random.exponential(0.02, n_points),
        0.001 + np.random.exponential(0.001, n_points)
    )
    error_rate = np.clip(error_rate, 0, 0.2)
    
    # Add some anomalies
    anomaly_indices = np.random.choice(n_points, size=10, replace=False)
    for idx in anomaly_indices:
        cpu_usage[idx] = np.random.uniform(0.85, 0.98)
        latency[idx] = np.random.uniform(200, 500)
        error_rate[idx] = np.random.uniform(0.05, 0.15)
    
    return pd.DataFrame({
        "timestamp": timestamps,
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "rps": rps,
        "latency_ms": latency,
        "error_rate": error_rate,
    })


def create_baseline_model(data: pd.DataFrame, output_dir: Path) -> dict:
    """Create and save a baseline model."""
    print("Creating baseline model...")
    
    model = BaselineModel(window=12, trend_window=24)
    model.fit(data["cpu_usage"])
    
    # Save model
    model_path = output_dir / "baseline_model.joblib"
    joblib.dump(model, model_path)
    
    # Get sample prediction for metadata
    pred = model.predict(periods=12)
    
    return {
        "model_type": "baseline",
        "path": str(model_path.name),
        "target": "cpu_usage",
        "window": 12,
        "trend_window": 24,
        "fitted_params": {
            "moving_average": float(model.moving_average_),
            "trend": float(model.trend_),
        }
    }


def create_prophet_model(data: pd.DataFrame, output_dir: Path) -> dict:
    """Create and save a Prophet forecaster."""
    print("Creating Prophet model...")
    
    model = ProphetForecaster(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=True,
    )
    
    df = data[["timestamp", "cpu_usage"]].copy()
    df.columns = ["timestamp", "value"]
    
    model.fit(df, timestamp_col="timestamp", value_col="value")
    
    # Save model
    model_path = output_dir / "prophet_model.joblib"
    joblib.dump(model, model_path)
    
    return {
        "model_type": "prophet",
        "path": str(model_path.name),
        "target": "cpu_usage",
        "seasonality_mode": "multiplicative",
        "weekly_seasonality": True,
        "daily_seasonality": True,
    }


def create_anomaly_detector(data: pd.DataFrame, output_dir: Path) -> dict:
    """Create and save an XGBoost anomaly detector."""
    print("Creating XGBoost anomaly detector...")
    
    model = XGBoostAnomalyDetector(
        n_estimators=50,
        max_depth=4,
        threshold_sigma=2.5,
    )
    
    features = data[["cpu_usage", "memory_usage", "rps", "latency_ms"]]
    target = data["error_rate"]
    
    model.fit(features, target)
    
    # Save model
    model_path = output_dir / "anomaly_detector.joblib"
    joblib.dump(model, model_path)
    
    return {
        "model_type": "xgboost_anomaly",
        "path": str(model_path.name),
        "target": "error_rate",
        "features": ["cpu_usage", "memory_usage", "rps", "latency_ms"],
        "n_estimators": 50,
        "threshold": float(model.threshold_),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate demo models for Prescale")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./demo_models",
        help="Output directory for demo models"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=168,
        help="Hours of synthetic data to generate (default: 168 = 1 week)"
    )
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {args.hours} hours of synthetic data...")
    data = generate_synthetic_data(hours=args.hours)
    
    # Save sample data
    data_path = output_dir / "sample_data.csv"
    data.to_csv(data_path, index=False)
    print(f"Saved sample data to {data_path}")
    
    # Create models
    models_metadata = []
    
    models_metadata.append(create_baseline_model(data, output_dir))
    models_metadata.append(create_prophet_model(data, output_dir))
    models_metadata.append(create_anomaly_detector(data, output_dir))
    
    # Save metadata
    metadata = {
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "data_hours": args.hours,
        "data_points": len(data),
        "models": models_metadata,
    }
    
    metadata_path = output_dir / "models_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✅ Demo models created successfully in {output_dir}")
    print(f"   - {len(models_metadata)} models saved")
    print(f"   - Metadata saved to {metadata_path}")
    print("\nTo use these models:")
    print("  1. Copy to ml/artifacts/demo/")
    print("  2. Or upload to your GCS bucket")


if __name__ == "__main__":
    main()
