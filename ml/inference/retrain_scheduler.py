"""
Automated model retraining scheduler.

Background asyncio task that periodically:
1. Fetches historical metrics from the monitoring platform (GCP/AWS)
2. Runs the training pipeline on real data
3. Validates the new model against the current one
4. Hot-swaps models if the new one is better
"""

import asyncio
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from .config import config

logger = logging.getLogger(__name__)


class TrainingRun:
    """Record of a single training run."""

    def __init__(self):
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.status: str = "pending"  # pending | running | completed | failed | skipped
        self.data_source: str = ""
        self.data_points: int = 0
        self.training_hours: int = 0
        self.metrics: dict[str, float] = {}
        self.deployed: bool = False
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "data_source": self.data_source,
            "data_points": self.data_points,
            "training_hours": self.training_hours,
            "metrics": self.metrics,
            "deployed": self.deployed,
            "error": self.error,
        }


class RetrainScheduler:
    """Background scheduler for automated model retraining.

    Fetches real metrics from monitoring platforms (GCP Cloud Monitoring
    or AWS CloudWatch) and retrains models periodically.
    """

    def __init__(self, model_manager=None):
        self._task: Optional[asyncio.Task] = None
        self._model_manager = model_manager
        self._running = False
        self._history: list[TrainingRun] = []
        self._max_history = 20
        self._next_run: Optional[datetime] = None
        self._retrain_lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        """Start the background retraining scheduler."""
        if not config.retraining.enabled:
            logger.info("Retraining scheduler disabled by config")
            return

        self._running = True
        self._task = asyncio.create_task(self._retrain_loop())
        logger.info(
            f"Retraining scheduler started: every {config.retraining.interval_hours}h, "
            f"source={config.retraining.data_source}"
        )

    def stop(self):
        """Stop the scheduler gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Retraining scheduler stopped")

    async def _retrain_loop(self):
        """Main scheduler loop."""
        interval_seconds = config.retraining.interval_hours * 3600

        # Wait a short period on startup to let the server finish initialization
        await asyncio.sleep(10)

        while self._running:
            self._next_run = datetime.now(timezone.utc)

            try:
                await self._execute_retrain(config.retraining.training_hours)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retrain loop error: {e}")
                logger.debug(traceback.format_exc())

            # Sleep until next cycle
            try:
                self._next_run = datetime.now(timezone.utc)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break

    async def trigger_retrain(self, hours: Optional[int] = None) -> TrainingRun:
        """Manually trigger a retrain cycle.

        Args:
            hours: Training window in hours (overrides config)

        Returns:
            TrainingRun with results
        """
        training_hours = hours or config.retraining.training_hours
        return await self._execute_retrain(training_hours)

    async def _execute_retrain(self, training_hours: int) -> TrainingRun:
        """Execute a single retrain cycle."""
        async with self._retrain_lock:
            run = TrainingRun()
            run.started_at = datetime.now(timezone.utc)
            run.status = "running"
            run.data_source = config.retraining.data_source
            run.training_hours = training_hours

            try:
                # Step 1: Fetch training data from monitoring platform
                logger.info(
                    f"Fetching {training_hours}h of metrics from "
                    f"{config.retraining.data_source}..."
                )
                df = await asyncio.to_thread(
                    self._fetch_training_data, training_hours
                )

                if df is None or df.empty:
                    run.status = "skipped"
                    run.error = "No data returned from monitoring platform"
                    logger.warning("Retrain skipped: no data from platform")
                    self._record_run(run)
                    return run

                run.data_points = len(df)

                if run.data_points < config.retraining.min_data_points:
                    run.status = "skipped"
                    run.error = (
                        f"Insufficient data: got {run.data_points}, "
                        f"need {config.retraining.min_data_points}"
                    )
                    logger.warning(f"Retrain skipped: {run.error}")
                    self._record_run(run)
                    return run

                # Step 2: Run training pipeline
                logger.info(f"Training on {run.data_points} data points...")
                result = await asyncio.to_thread(self._run_training, df)

                if result is None:
                    run.status = "failed"
                    run.error = "Training pipeline returned no results"
                    self._record_run(run)
                    return run

                run.metrics = result.get("metrics", {})

                # Step 3: Validate and deploy
                if config.retraining.auto_deploy:
                    deployed = await asyncio.to_thread(
                        self._validate_and_deploy, result
                    )
                    run.deployed = deployed
                    if deployed:
                        # Hot-reload models into memory
                        if self._model_manager:
                            self._model_manager.load_models()
                            logger.info("Models hot-swapped after retraining")

                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                logger.info(
                    f"Retrain completed: {run.data_points} points, "
                    f"deployed={run.deployed}, metrics={run.metrics}"
                )

            except Exception as e:
                run.status = "failed"
                run.error = str(e)
                run.completed_at = datetime.now(timezone.utc)
                logger.error(f"Retrain failed: {e}")
                logger.debug(traceback.format_exc())

            self._record_run(run)
            return run

    def _fetch_training_data(self, hours: int):
        """Fetch training data from the configured monitoring platform.

        Returns:
            pd.DataFrame or None
        """
        source = config.retraining.data_source

        if source == "gcp":
            return self._fetch_from_gcp(hours)
        elif source == "cloudwatch":
            return self._fetch_from_cloudwatch(hours)
        else:
            logger.error(f"Unknown data source: {source}")
            return None

    def _fetch_from_gcp(self, hours: int):
        """Fetch metrics from GCP Cloud Monitoring."""
        try:
            # Use existing CloudMonitoringFetcher from training pipeline
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from pipeline.data_fetcher import CloudMonitoringFetcher

            fetcher = CloudMonitoringFetcher()
            df = fetcher.fetch_all_metrics(hours=hours)
            logger.info(f"GCP: fetched {len(df)} records over {hours}h")
            return df

        except ImportError:
            logger.error(
                "google-cloud-monitoring not installed. "
                "Install with: pip install google-cloud-monitoring"
            )
            return None
        except Exception as e:
            logger.error(f"Error fetching from GCP: {e}")
            return None

    def _fetch_from_cloudwatch(self, hours: int):
        """Fetch metrics from AWS CloudWatch."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from pipeline.cloudwatch_fetcher import CloudWatchFetcher

            fetcher = CloudWatchFetcher()
            df = fetcher.fetch_all_metrics(hours=hours)
            logger.info(f"CloudWatch: fetched {len(df)} records over {hours}h")
            return df

        except ImportError:
            logger.error(
                "boto3 not installed. Install with: pip install boto3"
            )
            return None
        except Exception as e:
            logger.error(f"Error fetching from CloudWatch: {e}")
            return None

    def _run_training(self, df) -> Optional[dict]:
        """Run the training pipeline on fetched data.

        Returns:
            Dict with 'metrics' and 'output_dir' keys, or None on failure
        """
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from pipeline.feature_engineering import FeatureEngineer
            from models.baseline import BaselineModel
            from train import HeliosTrainingPipeline

            # Feature engineering
            fe = FeatureEngineer()
            features_df = fe.transform(df)
            if features_df.empty:
                logger.warning("Feature engineering produced empty DataFrame")
                features_df = df  # Fall back to raw data

            # Determine target column
            numeric_cols = features_df.select_dtypes(include=["number"]).columns
            target = None
            for candidate in ["cpu_utilization", "saleor_cpu", "ec2_cpu_utilization", "rps"]:
                if candidate in numeric_cols:
                    target = candidate
                    break
            if target is None and len(numeric_cols) > 0:
                target = numeric_cols[0]

            if target is None:
                logger.error("No numeric target column found for training")
                return None

            # Train baseline model
            baseline = BaselineModel()
            baseline.fit(features_df[target])

            all_metrics = {}
            if baseline.is_fitted_:
                all_metrics["baseline"] = {
                    "rmse": float(getattr(baseline, "rmse_", 0)),
                    "mae": float(getattr(baseline, "mae_", 0)),
                }

            # Try Prophet
            try:
                from models.prophet_model import ProphetForecaster

                prophet = ProphetForecaster()
                prophet.fit(features_df, value_col=target)
                if hasattr(prophet, "model_") and prophet.model_ is not None:
                    all_metrics["prophet"] = {
                        "rmse": float(getattr(prophet, "rmse_", 0)),
                        "mae": float(getattr(prophet, "mae_", 0)),
                    }
            except Exception as e:
                logger.warning(f"Prophet training skipped: {e}")

            # Try anomaly detector
            try:
                from models.xgboost_anomaly import XGBoostAnomalyDetector

                detector = XGBoostAnomalyDetector()
                
                # Prepare X and y
                y = features_df[target]
                X = features_df.drop(columns=["timestamp", target], errors="ignore")
                X = X.select_dtypes(include=[np.number])
                
                detector.fit(X, y)
                if detector.is_fitted_:
                    all_metrics["anomaly_detector"] = {
                        "threshold": float(getattr(detector, "threshold_", 0)),
                    }
            except Exception as e:
                logger.warning(f"Anomaly detector training skipped: {e}")

            # Save artifacts
            output_dir = Path(__file__).parent.parent / "artifacts"
            output_dir.mkdir(parents=True, exist_ok=True)

            self._save_trained_models(
                output_dir, baseline,
                prophet if "prophet" in all_metrics else None,
                detector if "anomaly_detector" in all_metrics else None,
            )

            return {
                "metrics": all_metrics,
                "output_dir": str(output_dir),
                "target": target,
                "data_points": len(features_df),
            }

        except Exception as e:
            logger.error(f"Training pipeline error: {e}")
            logger.debug(traceback.format_exc())
            return None

    def _save_trained_models(self, output_dir: Path, baseline, prophet=None, detector=None):
        """Save trained models to disk in inference-compatible format."""
        import pickle

        # Save baseline
        if baseline is not None and baseline.is_fitted_:
            baseline_dir = output_dir / "cpu_forecaster" / "1.0.0"
            baseline_dir.mkdir(parents=True, exist_ok=True)
            with open(baseline_dir / "model.pkl", "wb") as f:
                pickle.dump({
                    "type": "baseline",
                    "moving_average": baseline.moving_average_,
                    "trend": baseline.trend_,
                    "std": baseline.std_,
                    "window": baseline.window,
                    "trend_window": getattr(baseline, "trend_window", 6),
                }, f)
            logger.info(f"Saved baseline model to {baseline_dir}")

        # Save Prophet
        if prophet is not None and hasattr(prophet, "model_") and prophet.model_ is not None:
            try:
                import joblib
                prophet_path = output_dir / "prophet_model.joblib"
                joblib.dump({
                    "type": "prophet",
                    "model": prophet.model_,
                }, prophet_path)
                logger.info(f"Saved Prophet model to {prophet_path}")
            except Exception as e:
                logger.warning(f"Failed to save Prophet model: {e}")

        # Save anomaly detector
        if detector is not None and detector.is_fitted_:
            detector_dir = output_dir / "anomaly_detector" / "1.0.0"
            detector_dir.mkdir(parents=True, exist_ok=True)
            with open(detector_dir / "model.pkl", "wb") as f:
                pickle.dump({
                    "type": "xgboost_anomaly",
                    "model": detector.model_,
                    "scaler": detector.scaler_,
                    "threshold": detector.threshold_,
                    "feature_names": detector.feature_names_,
                    "threshold_sigma": detector.threshold_sigma,
                }, f)
            logger.info(f"Saved anomaly detector to {detector_dir}")

    def _validate_and_deploy(self, result: dict) -> bool:
        """Validate new model against current and decide whether to deploy.

        Returns True if new model should replace the current one.
        """
        new_metrics = result.get("metrics", {})

        # If we have no current model to compare against, always deploy
        if not self._model_manager or not self._model_manager.is_loaded:
            logger.info("No current model loaded, deploying new model")
            return True

        # Check baseline improvement
        baseline_metrics = new_metrics.get("baseline", {})
        new_rmse = baseline_metrics.get("rmse")

        if new_rmse is None or new_rmse == 0:
            logger.info("No RMSE available for comparison, deploying new model")
            return True

        # For now, always deploy - in production you'd compare against
        # the current model's RMSE stored in model_info
        current_info = self._model_manager.get_model_info(
            self._model_manager.list_models()[0] if self._model_manager.list_models() else None
        )

        if current_info and hasattr(current_info, "metrics"):
            current_rmse = current_info.metrics.get("rmse", float("inf"))
            improvement = (current_rmse - new_rmse) / current_rmse if current_rmse > 0 else 1.0

            if improvement < config.retraining.min_improvement:
                logger.info(
                    f"New model improvement {improvement:.2%} < required "
                    f"{config.retraining.min_improvement:.0%}, skipping deploy"
                )
                return False

            logger.info(f"Model improved by {improvement:.2%}, deploying")

        return True

    def _record_run(self, run: TrainingRun):
        """Record a training run in history."""
        run.completed_at = run.completed_at or datetime.now(timezone.utc)
        self._history.append(run)

        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_status(self) -> dict:
        """Get scheduler status."""
        last_run = self._history[-1].to_dict() if self._history else None

        return {
            "enabled": config.retraining.enabled,
            "running": self._running,
            "data_source": config.retraining.data_source,
            "interval_hours": config.retraining.interval_hours,
            "training_hours": config.retraining.training_hours,
            "next_run": self._next_run.isoformat() if self._next_run else None,
            "total_runs": len(self._history),
            "last_run": last_run,
        }

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get training run history."""
        return [run.to_dict() for run in reversed(self._history[:limit])]


# Global scheduler instance
retrain_scheduler = RetrainScheduler()
