# Prescale Web Dashboard

Vue.js dashboard for [Prescale](https://github.com/pyjeebz/prescale) - Predictive Infrastructure Intelligence Platform.

## Quick Start

```bash
# Install dependencies
npm install

# Development server (http://localhost:3000)
npm run dev

# Production build (outputs to ../static)
npm run build
```

## Requirements

- Node.js 18+
- Backend running at http://localhost:8080

## Features

| Feature | Route | Description |
|---------|-------|-------------|
| **Dashboard** | `/` | AI insights overview with agents, anomalies, recommendations |
| **Predictions** | `/predictions` | Forecast CPU, memory, and resource usage |
| **Anomalies** | `/anomalies` | Detect unusual patterns in metrics |
| **Agents** | `/agents` | Manage data collection agents |
| **Deployments** | `/deployments` | Create and manage deployments (prod, staging, dev) |
| **Install Agent** | `/install` | Copy-paste commands with live connection status |

## Tech Stack

- **Vue 3** + Composition API
- **TypeScript**
- **Tailwind CSS** for styling
- **Pinia** for state management
- **Vue Router** for navigation
- **Chart.js** via vue-chartjs for charts
- **Heroicons** for icons

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── charts/          # Chart components (MetricChart, PredictionChart, etc.)
│   └── common/          # Common components (Badge, Modal, StatsCard, etc.)
├── router/              # Vue Router configuration
├── services/            # API services
├── stores/              # Pinia stores (deployments, agents, theme)
├── styles/              # Global styles
└── views/               # Page components
    ├── Dashboard.vue
    ├── Predictions.vue
    ├── Anomalies.vue
    ├── Agents.vue
    ├── DeploymentsOverview.vue
    └── AgentInstall.vue
```

## API Proxy

The Vite dev server proxies API requests:

- `/api/v1/*` → `http://localhost:8080/*` (ML endpoints)
- `/api/*` → `http://localhost:8080/api/*` (deployments, agents)

## Development

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build
```

## License

Apache 2.0 - See [LICENSE](../../../LICENSE)
