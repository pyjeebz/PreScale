<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import EmptyState from '@/components/common/EmptyState.vue'
import AnomalyTimeline from '@/components/charts/AnomalyTimeline.vue'
import { useDeploymentsStore } from '@/stores/deployments'
import { mlApi } from '@/services/api'

const deploymentsStore = useDeploymentsStore()

const severityFilter = ref('all')
const timeRange = ref('1h')
const loading = ref(false)
const error = ref<string | null>(null)
let refreshInterval: number | null = null

interface DisplayAnomaly {
  id: string
  metric: string
  severity: string
  value: string
  deviation: string
  time: string
  timestamp: number
  agentId: string
  agentName: string
}

const detectedAnomalies = ref<DisplayAnomaly[]>([])

const timeRanges = [
  { value: '1h', label: 'Last 1 hour', hours: 1 },
  { value: '24h', label: 'Last 24 hours', hours: 24 },
  { value: '7d', label: 'Last 7 days', hours: 168 },
  { value: '30d', label: 'Last 30 days', hours: 720 }
]

// Fetch metrics and detect anomalies
async function detectAnomalies() {
  if (!deploymentsStore.currentDeploymentId) return
  
  loading.value = true
  error.value = null
  
  try {
    const range = timeRanges.find(r => r.value === timeRange.value)
    const hoursBack = range?.hours || 24
    
    const response = await mlApi.detect({
      hours_back: hoursBack,
      deployment_id: deploymentsStore.currentDeploymentId
    })
    
    if (response && response.anomalies) {
      detectedAnomalies.value = response.anomalies.map((a: any, idx: number) => ({
        id: `anomaly-${idx}`,
        metric: a.metric || 'unknown',
        severity: a.severity || 'medium',
        value: a.value?.toFixed(2) || '—',
        deviation: a.deviation ? `${a.deviation > 0 ? '+' : ''}${a.deviation.toFixed(1)}σ` : '—',
        time: a.timestamp ? new Date(a.timestamp).toLocaleString() : '—',
        timestamp: a.timestamp || Date.now(),
        agentId: a.agent_id || '',
        agentName: a.agent_name || 'unknown'
      }))
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to detect anomalies'
    console.error('Anomaly detection failed:', e)
  } finally {
    loading.value = false
  }
}

const filteredAnomalies = computed(() => {
  if (severityFilter.value === 'all') return detectedAnomalies.value
  return detectedAnomalies.value.filter(a => a.severity === severityFilter.value)
})

const timelineStartTime = computed(() => {
  const range = timeRanges.find(r => r.value === timeRange.value)
  return Date.now() - (range?.hours || 24) * 3600000
})
const timelineEndTime = computed(() => Date.now())

function handleAnomalyClick(anomaly: DisplayAnomaly) {
  console.log('Anomaly clicked:', anomaly)
}

onMounted(() => {
  detectAnomalies()
  refreshInterval = window.setInterval(detectAnomalies, 3600000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

function getSeverityStyle(severity: string) {
  switch (severity) {
    case 'critical':
      return { color: 'var(--status-red)', bg: 'rgba(239, 68, 68, 0.1)' }
    case 'high':
      return { color: 'var(--status-amber)', bg: 'rgba(245, 158, 11, 0.1)' }
    case 'medium':
      return { color: '#eab308', bg: 'rgba(234, 179, 8, 0.1)' }
    case 'low':
      return { color: 'var(--status-blue)', bg: 'rgba(59, 130, 246, 0.1)' }
    default:
      return { color: 'var(--text-tertiary)', bg: 'var(--bg-card)' }
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold" style="color: var(--text-primary);">Anomalies</h1>
        <p style="color: var(--text-tertiary);">
          Detect unusual patterns in your infrastructure metrics
        </p>
      </div>
      
      <div class="flex items-center gap-3">
        <!-- Time Range -->
        <select v-model="timeRange" @change="detectAnomalies" class="input w-40">
          <option v-for="range in timeRanges" :key="range.value" :value="range.value">
            {{ range.label }}
          </option>
        </select>
        
        <!-- Severity Filter -->
        <select v-model="severityFilter" class="input w-32">
          <option value="all">All</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        
        <button @click="detectAnomalies" :disabled="loading" class="btn-primary flex items-center gap-2">
          <ArrowPathIcon class="w-4 h-4" :class="{ 'animate-spin': loading }" />
          Scan
        </button>
      </div>
    </div>
    
    <!-- Error -->
    <div v-if="error" class="p-4 rounded-lg" style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.15);">
      <p class="text-sm" style="color: var(--status-red);">{{ error }}</p>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="bento-card p-12 text-center">
      <ArrowPathIcon class="w-8 h-8 mx-auto animate-spin mb-4" style="color: var(--text-tertiary);" />
      <p style="color: var(--text-tertiary);">Analyzing metrics for anomalies...</p>
    </div>
    
    <!-- Anomaly Timeline -->
    <AnomalyTimeline
      v-if="!loading && filteredAnomalies.length > 0"
      :anomalies="filteredAnomalies"
      :start-time="timelineStartTime"
      :end-time="timelineEndTime"
      @click="handleAnomalyClick"
    />
    
    <!-- Empty State -->
    <EmptyState
      v-if="!loading && filteredAnomalies.length === 0"
      title="No anomalies detected"
      description="Great news! No anomalies have been detected in your infrastructure. We'll alert you when something unusual is found."
      :icon="ExclamationTriangleIcon"
    />
    
    <!-- Anomalies Table -->
    <div v-if="!loading && filteredAnomalies.length > 0" class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="table-header">
            <tr>
              <th>Severity</th>
              <th>Metric</th>
              <th>Agent</th>
              <th>Value</th>
              <th>Deviation</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="anomaly in filteredAnomalies" 
              :key="anomaly.id"
              class="table-row cursor-pointer"
              @click="handleAnomalyClick(anomaly)"
            >
              <td>
                <span 
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium capitalize"
                  :style="`background: ${getSeverityStyle(anomaly.severity).bg}; color: ${getSeverityStyle(anomaly.severity).color};`"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :style="`background: ${getSeverityStyle(anomaly.severity).color};`"></span>
                  {{ anomaly.severity }}
                </span>
              </td>
              <td class="font-medium" style="color: var(--text-primary);">
                {{ anomaly.metric }}
              </td>
              <td style="color: var(--text-secondary);">
                {{ anomaly.agentName }}
              </td>
              <td style="color: var(--text-secondary);">
                {{ anomaly.value }}
              </td>
              <td>
                <span class="font-mono text-sm" :style="`color: ${getSeverityStyle(anomaly.severity).color};`">
                  {{ anomaly.deviation }}
                </span>
              </td>
              <td style="color: var(--text-secondary);">
                {{ anomaly.time }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
