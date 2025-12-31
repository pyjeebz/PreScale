# Helios Architecture Design

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              HELIOS PLATFORM                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Ingestion  │───▶│   Storage    │───▶│  Forecasting │───▶│   Decision   │  │
│  │    Layer     │    │    Layer     │    │    Engine    │    │    Engine    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘  │
│         ▲                                                            │          │
│         │                                                            ▼          │
│  ┌──────────────┐                                          ┌──────────────┐    │
│  │   Collectors │                                          │   Output     │    │
│  │   (Agents)   │                                          │   Layer      │    │
│  └──────────────┘                                          └──────────────┘    │
│         ▲                                                            │          │
└─────────│────────────────────────────────────────────────────────────│──────────┘
          │                                                            │
          │                                                            ▼
┌─────────────────────┐                                    ┌─────────────────────┐
│   Customer Stack    │                                    │   Target Systems    │
│  (Saleor on GKE)    │                                    │  (HPA/Terraform)    │
└─────────────────────┘                                    └─────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Ingestion Layer

**Purpose:** Collect, normalize, and align metrics from multiple sources.

```
┌─────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Prometheus  │  │  OpenTel    │  │   Custom    │             │
│  │  Scraper    │  │  Receiver   │  │   Agents    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│                 ┌─────────────────┐                             │
│                 │   Normalizer    │                             │
│                 │  (Schema Map)   │                             │
│                 └────────┬────────┘                             │
│                          ▼                                      │
│                 ┌─────────────────┐                             │
│                 │ Time Alignment  │                             │
│                 │   (Bucketing)   │                             │
│                 └────────┬────────┘                             │
│                          ▼                                      │
│                 ┌─────────────────┐                             │
│                 │  Kafka/Buffer   │                             │
│                 └─────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**

| Component | Responsibility |
|-----------|----------------|
| **Prometheus Scraper** | Pull metrics from Prometheus endpoints |
| **OpenTelemetry Receiver** | Receive OTLP traces and metrics |
| **Custom Agents** | Collect app-specific metrics (DB connections, queue depth) |
| **Normalizer** | Map diverse metric names to canonical schema |
| **Time Alignment** | Bucket metrics into consistent time windows (e.g., 15s, 1m) |
| **Buffer (Kafka)** | Decouple ingestion from processing, handle backpressure |

**Metrics Collected:**

```yaml
infrastructure:
  - cpu_utilization
  - memory_utilization
  - network_io
  - disk_io

application:
  - requests_per_second (QPS)
  - latency_p50, p95, p99
  - error_rate
  - active_connections

database:
  - connection_pool_usage
  - query_latency
  - replication_lag
  - lock_wait_time

cache:
  - hit_rate
  - eviction_rate
  - memory_usage

business:
  - active_users
  - cart_additions
  - checkout_starts
  - order_completions
```

---

### 2.2 Storage Layer

**Purpose:** Persist time-series data, model artifacts, and configuration.

```
┌─────────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   TimescaleDB                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │  Raw        │  │  Aggregated │  │  Forecasts  │     │   │
│  │  │  Metrics    │  │  Metrics    │  │  History    │     │   │
│  │  │  (hypertable)│ │  (continuous)│ │             │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │     PostgreSQL      │    │    Object Store     │            │
│  │  ┌───────────────┐  │    │  ┌───────────────┐  │            │
│  │  │ Applications  │  │    │  │ Model Weights │  │            │
│  │  │ Configurations│  │    │  │ Checkpoints   │  │            │
│  │  │ Scaling Rules │  │    │  │ Training Data │  │            │
│  │  └───────────────┘  │    │  └───────────────┘  │            │
│  └─────────────────────┘    └─────────────────────┘            │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │       Redis         │                                        │
│  │  ┌───────────────┐  │                                        │
│  │  │ Latest Values │  │                                        │
│  │  │ Active Alerts │  │                                        │
│  │  │ Rate Limits   │  │                                        │
│  │  └───────────────┘  │                                        │
│  └─────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Data Retention Policy:**

| Data Type | Resolution | Retention |
|-----------|------------|-----------|
| Raw metrics | 15 seconds | 7 days |
| Aggregated (1m) | 1 minute | 30 days |
| Aggregated (1h) | 1 hour | 1 year |
| Forecasts | Per prediction | 90 days |
| Model artifacts | Per version | Indefinite |

---

### 2.3 Forecasting Engine

**Purpose:** Learn patterns and predict future demand.

```
┌─────────────────────────────────────────────────────────────────┐
│                    FORECASTING ENGINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Feature Pipeline                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ Temporal │ │  Lag     │ │ Rolling  │ │ Calendar │   │   │
│  │  │ Features │ │ Features │ │ Stats    │ │ Features │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Model Registry                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │   Prophet    │  │    LSTM      │  │  Transformer │  │   │
│  │  │  (baseline)  │  │  (sequence)  │  │  (advanced)  │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Ensemble Layer                          │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │  Model Selection │ Weighted Average │ Confidence   │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Output: Forecasts                      │   │
│  │  { metric, horizon, value, confidence_lower/upper }     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Forecasting Horizons:**

| Horizon | Use Case | Model Priority |
|---------|----------|----------------|
| 5 min | Immediate response | LSTM (low latency) |
| 15 min | Pre-warming | Ensemble |
| 30 min | Scaling decisions | Prophet + LSTM |
| 60 min | Capacity planning | Prophet |

**Feature Engineering:**

```python
# Temporal features
- hour_of_day (0-23)
- day_of_week (0-6)
- is_weekend (bool)
- is_holiday (bool)
- minutes_since_midnight

# Lag features
- metric_lag_5m
- metric_lag_15m
- metric_lag_1h
- metric_lag_24h
- metric_lag_7d

# Rolling statistics
- rolling_mean_15m
- rolling_std_15m
- rolling_mean_1h
- rolling_max_1h

# Cross-metric correlations
- search_to_checkout_ratio
- error_rate_change
- latency_trend
```

---

### 2.4 Decision Engine

**Purpose:** Convert forecasts into actionable scaling recommendations.

```
┌─────────────────────────────────────────────────────────────────┐
│                     DECISION ENGINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Input Processor                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │  Forecasts  │  │   Current   │  │   Config    │     │   │
│  │  │             │  │   State     │  │   (SLOs)    │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Capacity Calculator                     │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │ predicted_load → required_capacity → replica_count │ │   │
│  │  │                                                    │ │   │
│  │  │ Considers:                                         │ │   │
│  │  │   • Per-replica throughput                         │ │   │
│  │  │   • Safety margin (headroom %)                     │ │   │
│  │  │   • Startup time (pre-scale buffer)                │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Policy Enforcer                        │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │ • Min/Max replica bounds                           │ │   │
│  │  │ • Max scale-up/down per action                     │ │   │
│  │  │ • Cooldown periods                                 │ │   │
│  │  │ • Budget constraints                               │ │   │
│  │  │ • Time-of-day restrictions                         │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Recommendation Output                     │   │
│  │  {                                                       │   │
│  │    "application": "saleor-api",                         │   │
│  │    "action": "scale_up",                                │   │
│  │    "current_replicas": 3,                               │   │
│  │    "recommended_replicas": 5,                           │   │
│  │    "execute_at": "2025-01-01T14:25:00Z",               │   │
│  │    "confidence": 0.87,                                  │   │
│  │    "reasoning": "Predicted QPS surge in 15 min"         │   │
│  │  }                                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Decision Logic:**

```
1. FORECAST ANALYSIS
   - Get forecasts for all horizons
   - Weight by confidence
   - Detect anomalies/spikes

2. CAPACITY MAPPING
   required_replicas = ceil(
     (predicted_qps × (1 + headroom_pct)) / per_replica_capacity
   )

3. TIMING CALCULATION
   scale_lead_time = replica_startup_time + safety_buffer
   execute_at = spike_time - scale_lead_time

4. POLICY ENFORCEMENT
   - Clamp to min/max bounds
   - Respect max_change_per_action
   - Check cooldown timers
   - Validate budget

5. OUTPUT RECOMMENDATION
   - Include reasoning
   - Attach confidence score
   - Set expiration time
```

---

### 2.5 Output Layer

**Purpose:** Deliver recommendations through multiple interfaces.

```
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │    REST API     │  │    gRPC API     │  │   Webhooks      │ │
│  │                 │  │                 │  │                 │ │
│  │ /forecasts      │  │ Forecast.Get    │  │ POST to         │ │
│  │ /recommendations│  │ Recommend.Get   │  │ configured      │ │
│  │ /applications   │  │ App.Configure   │  │ endpoints       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Terraform     │  │  Kubernetes     │  │   Dashboard     │ │
│  │   Provider      │  │  Operator       │  │   (WebSocket)   │ │
│  │                 │  │  (Future)       │  │                 │ │
│  │ helios_scaling  │  │ HeliosPolicy    │  │ Real-time       │ │
│  │ resource        │  │ CRD             │  │ visualizations  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

### 3.1 Ingestion Flow

```
[Prometheus] ──scrape──▶ [Scraper] ──normalize──▶ [Kafka] ──consume──▶ [TimescaleDB]
                              │
[OTLP Agent] ──push────▶ [Receiver] ──normalize──┘
                              │
[Custom SDK] ──push────▶ [Agent] ────normalize───┘
```

### 3.2 Forecasting Flow

```
[TimescaleDB] ──query──▶ [Feature Pipeline] ──features──▶ [Models] ──predictions──▶ [Ensemble]
                                                                                        │
                                                                                        ▼
                                                                               [Forecast Store]
```

### 3.3 Decision Flow

```
[Forecast Store] ──read──▶ [Decision Engine] ──apply rules──▶ [Recommendation]
        │                         │                                   │
        │                         ▼                                   │
        │              [Current State Query]                          │
        │                         │                                   │
        └─────────────────────────┘                                   │
                                                                      ▼
                                                              [Output Layer]
                                                                      │
                                              ┌───────────────────────┼───────────────────────┐
                                              ▼                       ▼                       ▼
                                          [REST API]            [Terraform]             [Webhook]
```

---

## 4. Technology Stack

### 4.1 Core Services

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **API Gateway** | Go + Chi | High performance, simple routing |
| **Ingestion Service** | Go | Efficient concurrent processing |
| **Forecasting Service** | Python + FastAPI | ML ecosystem (Prophet, PyTorch) |
| **Decision Service** | Go | Low latency, deterministic |
| **Scheduler** | Go + cron | Job orchestration |

### 4.2 Data Stores

| Store | Technology | Purpose |
|-------|------------|---------|
| **Time-series** | TimescaleDB | Metrics storage, continuous aggregates |
| **Relational** | PostgreSQL | Config, applications, rules |
| **Cache** | Redis | Hot data, rate limiting |
| **Queue** | Apache Kafka | Ingestion buffer, event streaming |
| **Object Store** | MinIO / GCS | Model artifacts |

### 4.3 Infrastructure

| Concern | Technology |
|---------|------------|
| **Container Runtime** | Docker |
| **Orchestration** | Kubernetes (GKE) |
| **Service Mesh** | (Optional) Istio |
| **IaC** | Terraform |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Prometheus + Grafana |

---

## 5. API Design

### 5.1 REST API Endpoints

```yaml
# Applications
POST   /api/v1/applications              # Register application
GET    /api/v1/applications              # List applications
GET    /api/v1/applications/{id}         # Get application details
PUT    /api/v1/applications/{id}         # Update application config
DELETE /api/v1/applications/{id}         # Remove application

# Metrics Ingestion
POST   /api/v1/ingest/metrics            # Push metrics batch
POST   /api/v1/ingest/events             # Push events

# Forecasts
GET    /api/v1/forecasts/{app_id}        # Get forecasts for app
GET    /api/v1/forecasts/{app_id}/history # Historical forecasts

# Recommendations
GET    /api/v1/recommendations/{app_id}  # Current recommendations
GET    /api/v1/recommendations/{app_id}/history # Past recommendations
POST   /api/v1/recommendations/{id}/ack  # Acknowledge recommendation

# Health & Status
GET    /health                           # Health check
GET    /ready                            # Readiness check
GET    /metrics                          # Prometheus metrics
```

### 5.2 Core Data Models

```typescript
// Application
interface Application {
  id: string;
  name: string;
  namespace: string;
  scaling_config: ScalingConfig;
  slo_config: SLOConfig;
  created_at: timestamp;
  updated_at: timestamp;
}

interface ScalingConfig {
  min_replicas: number;
  max_replicas: number;
  target_cpu_utilization: number;
  per_replica_capacity_qps: number;
  scale_up_cooldown_seconds: number;
  scale_down_cooldown_seconds: number;
  max_scale_up_per_action: number;
  max_scale_down_per_action: number;
  headroom_percent: number;
}

interface SLOConfig {
  target_latency_p99_ms: number;
  target_error_rate_percent: number;
  target_availability_percent: number;
}

// Metric
interface Metric {
  application_id: string;
  name: string;
  value: number;
  timestamp: timestamp;
  labels: Record<string, string>;
}

// Forecast
interface Forecast {
  id: string;
  application_id: string;
  metric: string;
  horizon_minutes: number;
  predicted_value: number;
  confidence_lower: number;
  confidence_upper: number;
  confidence_score: number;
  model_version: string;
  created_at: timestamp;
  valid_until: timestamp;
}

// Recommendation
interface Recommendation {
  id: string;
  application_id: string;
  action: "scale_up" | "scale_down" | "no_action";
  current_replicas: number;
  recommended_replicas: number;
  execute_at: timestamp;
  expires_at: timestamp;
  confidence: number;
  reasoning: string;
  triggering_forecasts: string[];
  status: "pending" | "acknowledged" | "executed" | "expired";
  created_at: timestamp;
}
```

---

## 6. Database Schema

### 6.1 TimescaleDB (Metrics)

```sql
-- Raw metrics hypertable
CREATE TABLE metrics (
    time        TIMESTAMPTZ NOT NULL,
    app_id      UUID NOT NULL,
    name        TEXT NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    labels      JSONB
);
SELECT create_hypertable('metrics', 'time');

-- Continuous aggregate for 1-minute rollups
CREATE MATERIALIZED VIEW metrics_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    app_id,
    name,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    COUNT(*) AS sample_count
FROM metrics
GROUP BY bucket, app_id, name;

-- Forecasts table
CREATE TABLE forecasts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id          UUID NOT NULL,
    metric          TEXT NOT NULL,
    horizon_minutes INTEGER NOT NULL,
    predicted_value DOUBLE PRECISION NOT NULL,
    confidence_lower DOUBLE PRECISION,
    confidence_upper DOUBLE PRECISION,
    confidence_score DOUBLE PRECISION,
    model_version   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    valid_until     TIMESTAMPTZ NOT NULL
);
SELECT create_hypertable('forecasts', 'created_at');
```

### 6.2 PostgreSQL (Application Data)

```sql
-- Applications
CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL UNIQUE,
    namespace       TEXT NOT NULL,
    scaling_config  JSONB NOT NULL,
    slo_config      JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Recommendations
CREATE TABLE recommendations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id              UUID REFERENCES applications(id),
    action              TEXT NOT NULL,
    current_replicas    INTEGER NOT NULL,
    recommended_replicas INTEGER NOT NULL,
    execute_at          TIMESTAMPTZ NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    confidence          DOUBLE PRECISION,
    reasoning           TEXT,
    triggering_forecasts UUID[],
    status              TEXT DEFAULT 'pending',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at     TIMESTAMPTZ,
    executed_at         TIMESTAMPTZ
);

-- Scaling events (audit log)
CREATE TABLE scaling_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id          UUID REFERENCES applications(id),
    recommendation_id UUID REFERENCES recommendations(id),
    from_replicas   INTEGER NOT NULL,
    to_replicas     INTEGER NOT NULL,
    source          TEXT NOT NULL, -- 'helios', 'manual', 'hpa'
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 7. Service Architecture

### 7.1 Service Breakdown

```
helios/
├── cmd/
│   ├── api/              # REST API server
│   ├── ingestion/        # Metrics ingestion service
│   ├── scheduler/        # Job scheduler (forecasting, cleanup)
│   └── decision/         # Decision engine service
│
├── internal/
│   ├── api/              # HTTP handlers, middleware
│   ├── ingestion/        # Collectors, normalizers
│   ├── forecast/         # Forecasting logic (Go orchestration)
│   ├── decision/         # Decision engine logic
│   ├── storage/          # Repository interfaces
│   ├── models/           # Domain models
│   └── config/           # Configuration management
│
├── pkg/
│   ├── client/           # Go client SDK
│   └── proto/            # Protobuf definitions
│
├── forecasting/          # Python forecasting service
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── models/       # ML models (Prophet, LSTM)
│   │   ├── features/     # Feature engineering
│   │   └── training/     # Model training pipelines
│   └── requirements.txt
│
├── terraform/
│   ├── modules/          # Reusable TF modules
│   ├── environments/     # Per-environment configs
│   └── provider/         # Helios Terraform provider
│
├── deployments/
│   ├── docker/           # Dockerfiles
│   ├── kubernetes/       # K8s manifests
│   └── docker-compose.yml
│
└── test/
    ├── load/             # Locust load tests
    ├── integration/      # Integration tests
    └── e2e/              # End-to-end tests
```

### 7.2 Service Communication

```
┌────────────┐     HTTP      ┌────────────┐
│   Client   │──────────────▶│  API GW    │
└────────────┘               └─────┬──────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
             ┌──────────┐  ┌──────────┐  ┌──────────┐
             │ Ingestion│  │ Decision │  │ Forecast │
             │ Service  │  │ Service  │  │ Service  │
             └────┬─────┘  └────┬─────┘  └────┬─────┘
                  │             │             │
                  │    gRPC     │    gRPC     │
                  │             │             │
                  └─────────────┴─────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              ┌──────────┐           ┌──────────┐
              │TimescaleDB│          │   Redis  │
              │PostgreSQL │           └──────────┘
              └──────────┘
```

---

## 8. Deployment Architecture

### 8.1 Kubernetes Deployment

```yaml
Namespace: helios-system

Deployments:
  - helios-api (2 replicas)
  - helios-ingestion (2 replicas)  
  - helios-decision (2 replicas)
  - helios-forecasting (2 replicas)
  - helios-scheduler (1 replica)

StatefulSets:
  - timescaledb (1 replica, persistent)
  - redis (1 replica, persistent)
  - kafka (3 replicas, persistent)

Services:
  - helios-api (LoadBalancer)
  - helios-ingestion (ClusterIP)
  - helios-decision (ClusterIP)
  - helios-forecasting (ClusterIP)
  - timescaledb (ClusterIP)
  - redis (ClusterIP)
  - kafka (ClusterIP)

ConfigMaps:
  - helios-config

Secrets:
  - helios-db-credentials
  - helios-api-keys
```

### 8.2 Resource Estimates

| Service | CPU Request | Memory Request | Replicas |
|---------|-------------|----------------|----------|
| API | 100m | 128Mi | 2 |
| Ingestion | 200m | 256Mi | 2 |
| Decision | 100m | 128Mi | 2 |
| Forecasting | 500m | 1Gi | 2 |
| Scheduler | 100m | 128Mi | 1 |
| TimescaleDB | 500m | 2Gi | 1 |
| Redis | 100m | 256Mi | 1 |
| Kafka | 500m | 1Gi | 3 |

---

## 9. Security Considerations

### 9.1 Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. API Authentication                                          │
│     • API Keys for service-to-service                           │
│     • JWT tokens for user access                                │
│     • mTLS for internal services                                │
│                                                                  │
│  2. Authorization                                                │
│     • RBAC for API endpoints                                    │
│     • Per-application access control                            │
│     • Audit logging                                             │
│                                                                  │
│  3. Data Protection                                              │
│     • Encryption at rest (database)                             │
│     • Encryption in transit (TLS)                               │
│     • Secret management (Kubernetes Secrets / Vault)            │
│                                                                  │
│  4. Network Security                                             │
│     • Network policies (namespace isolation)                    │
│     • Ingress rules                                             │
│     • Rate limiting                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Observability

### 10.1 Helios Monitoring Itself

```yaml
Metrics (Prometheus):
  - helios_ingestion_rate
  - helios_forecast_latency
  - helios_recommendation_count
  - helios_api_request_duration
  - helios_model_accuracy

Logging (Structured JSON):
  - Request/response logs
  - Decision audit trail
  - Error tracking

Tracing (OpenTelemetry):
  - Request flow through services
  - External call latency
  - Database query timing

Alerting:
  - Ingestion lag > 30s
  - Forecast accuracy drop > 20%
  - API error rate > 1%
  - Decision latency > 500ms
```

---

## 11. Development Phases

### Phase 1: Foundation (Current)
- [ ] Project structure setup
- [ ] Core data models
- [ ] TimescaleDB schema
- [ ] Basic API endpoints
- [ ] Docker Compose for local dev

### Phase 2: Ingestion
- [ ] Prometheus scraper
- [ ] Metric normalization
- [ ] Kafka integration
- [ ] Storage pipeline

### Phase 3: Forecasting
- [ ] Feature pipeline
- [ ] Prophet baseline model
- [ ] Forecast API
- [ ] Model evaluation

### Phase 4: Decision Engine
- [ ] Capacity calculator
- [ ] Policy enforcement
- [ ] Recommendation generation
- [ ] API integration

### Phase 5: Integration
- [ ] Terraform provider
- [ ] Webhook notifications
- [ ] Dashboard basics
- [ ] E2E testing

### Phase 6: Production Readiness
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Documentation
- [ ] Deployment automation

---

## 12. Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **Horizon** | The time window for a forecast (e.g., 15 minutes ahead) |
| **Headroom** | Extra capacity buffer above predicted demand |
| **Cooldown** | Minimum time between scaling actions |
| **SLO** | Service Level Objective (latency, availability targets) |
| **HPA** | Horizontal Pod Autoscaler (Kubernetes) |

### B. References

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Prophet Documentation](https://facebook.github.io/prophet/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [OpenTelemetry](https://opentelemetry.io/)
