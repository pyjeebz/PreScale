<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { ChartBarIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import PredictionChart from '@/components/charts/PredictionChart.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { useAgentsStore } from '@/stores/agents'
import { useDeploymentsStore } from '@/stores/deployments'
import { mlApi } from '@/services/api'

const agentsStore = useAgentsStore()
const deploymentsStore = useDeploymentsStore()

const selectedAgent = ref('')
const selectedMetric = ref('cpu_percent')
const selectedHorizon = ref('24')
const loading = ref(false)
const error = ref<string | null>(null)
const showPrediction = ref(false)
const prediction = ref<any>(null)
let refreshInterval: number | null = null

const metrics = [
  { value: 'cpu_percent', label: 'CPU Usage (%)' },
  { value: 'memory_percent', label: 'Memory Usage (%)' },
  { value: 'disk_percent', label: 'Disk Usage (%)' },
  { value: 'network_bytes_sent', label: 'Network Sent' },
  { value: 'network_bytes_recv', label: 'Network Received' }
]

const horizons = [
  { value: '1', label: '1 hour' },
  { value: '6', label: '6 hours' },
  { value: '12', label: '12 hours' },
  { value: '24', label: '24 hours' },
  { value: '48', label: '48 hours' },
  { value: '168', label: '7 days' }
]

const historicalData = ref<number[]>([])
const forecastData = ref<number[]>([])
const upperBound = ref<number[]>([])
const lowerBound = ref<number[]>([])

// Fetch historical data from metrics API
async function fetchHistoricalData() {
  if (!selectedAgent.value) return
  try {
    const response = await mlApi.getMetrics(selectedAgent.value, selectedMetric.value)
    if (response && response.values) {
      historicalData.value = response.values
    }
  } catch (e) {
    console.error('Failed to fetch historical data:', e)
    historicalData.value = []
  }
}

// Call real ML prediction API
async function generatePrediction() {
  if (!selectedAgent.value) {
    error.value = 'Please select an agent'
    return
  }
  
  loading.value = true
  error.value = null
  showPrediction.value = false
  
  try {
    await fetchHistoricalData()
    
    const response = await mlApi.predict({
      metric: selectedMetric.value,
      horizon_hours: parseInt(selectedHorizon.value),
      agent_id: selectedAgent.value
    })
    
    prediction.value = response
    forecastData.value = response.forecast || []
    upperBound.value = response.upper_bound || []
    lowerBound.value = response.lower_bound || []
    showPrediction.value = true
    
    if (!refreshInterval) {
      refreshInterval = window.setInterval(generatePrediction, 300000) as number
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to generate prediction'
    console.error('Prediction failed:', e)
  } finally {
    loading.value = false
  }
}

const labels = computed(() => {
  const now = new Date()
  const allLabels: string[] = []
  
  for (let i = 23; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 3600000)
    allLabels.push(time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
  }
  
  const h = parseInt(selectedHorizon.value)
  for (let i = 1; i <= h; i++) {
    const time = new Date(now.getTime() + i * 3600000)
    allLabels.push(time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
  }
  
  return allLabels
})

const predictionSummary = computed(() => {
  if (!prediction.value) return null
  return {
    peak: prediction.value.peak_value?.toFixed(1) || '—',
    average: prediction.value.avg_value?.toFixed(1) || '—',
    model: prediction.value.model || 'ensemble',
    horizon: horizons.find(h => h.value === selectedHorizon.value)?.label || ''
  }
})

const currentValue = computed(() => {
  if (historicalData.value.length === 0) return null
  return historicalData.value[historicalData.value.length - 1]
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-semibold" style="color: var(--text-primary);">Predictions</h1>
      <p style="color: var(--text-tertiary);">
        ML-powered forecasting for your infrastructure metrics
      </p>
    </div>
    
    <!-- Error -->
    <div v-if="error" class="p-4 rounded-lg" style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.15);">
      <p class="text-sm" style="color: var(--status-red);">{{ error }}</p>
    </div>
    
    <!-- Prediction Form -->
    <div class="bento-card p-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1" style="color: var(--text-secondary);">Agent</label>
          <select v-model="selectedAgent" class="input">
            <option value="">Select agent...</option>
            <option 
              v-for="agent in agentsStore.currentDeploymentAgents" 
              :key="agent.id" 
              :value="agent.id"
            >
              {{ agent.hostname }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1" style="color: var(--text-secondary);">Metric</label>
          <select v-model="selectedMetric" class="input">
            <option v-for="m in metrics" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1" style="color: var(--text-secondary);">Horizon</label>
          <select v-model="selectedHorizon" class="input">
            <option v-for="h in horizons" :key="h.value" :value="h.value">{{ h.label }}</option>
          </select>
        </div>
        <div class="flex items-end">
          <button 
            @click="generatePrediction"
            :disabled="loading"
            class="btn-primary w-full flex items-center justify-center gap-2"
          >
            <ArrowPathIcon v-if="loading" class="w-4 h-4 animate-spin" />
            {{ loading ? 'Generating...' : 'Generate Prediction' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Prediction Chart -->
    <PredictionChart
      v-if="showPrediction"
      :title="metrics.find(m => m.value === selectedMetric)?.label + ' Forecast'"
      :labels="labels"
      :historical="historicalData"
      :forecast="forecastData"
      :upper-bound="upperBound"
      :lower-bound="lowerBound"
    />
    
    <!-- Empty State -->
    <div v-if="!showPrediction" class="bento-card p-12 text-center">
      <div class="w-16 h-16 mx-auto mb-4 rounded-xl flex items-center justify-center" style="background: rgba(99, 102, 241, 0.1);">
        <ChartBarIcon class="w-8 h-8" style="color: var(--accent-400);" />
      </div>
      <p style="color: var(--text-secondary);">Select parameters and click "Generate Prediction"</p>
      <p class="text-sm mt-1" style="color: var(--text-tertiary);">Historical data + ML forecast will appear here</p>
    </div>
    
    <!-- Prediction Summary -->
    <div v-if="showPrediction && prediction" class="bento-card p-6">
      <h3 class="text-lg font-medium mb-4" style="color: var(--text-primary);">Prediction Summary</h3>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Current</p>
          <p class="text-2xl font-semibold" style="color: var(--accent-400);">{{ currentValue?.toFixed(1) || '—' }}%</p>
        </div>
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Peak Forecast</p>
          <p class="text-2xl font-semibold" style="color: var(--status-amber);">{{ predictionSummary?.peak || '—' }}%</p>
        </div>
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Model</p>
          <p class="text-2xl font-semibold" style="color: var(--text-primary);">{{ predictionSummary?.model || '—' }}</p>
        </div>
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Confidence</p>
          <p class="text-2xl font-semibold" style="color: var(--status-green);">{{ (prediction.confidence * 100).toFixed(0) }}%</p>
        </div>
      </div>
    </div>
    
    <!-- Empty Prediction Summary -->
    <div v-else class="bento-card p-6">
      <h3 class="text-lg font-medium mb-4" style="color: var(--text-primary);">Prediction Summary</h3>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Current</p>
          <p class="text-2xl font-semibold" style="color: var(--text-primary);">—</p>
        </div>
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Peak Forecast</p>
          <p class="text-2xl font-semibold" style="color: var(--text-primary);">—</p>
        </div>
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Model</p>
          <p class="text-2xl font-semibold" style="color: var(--text-primary);">—</p>
        </div>
        <div>
          <p class="text-sm" style="color: var(--text-tertiary);">Confidence</p>
          <p class="text-2xl font-semibold" style="color: var(--text-primary);">—</p>
        </div>
      </div>
    </div>
  </div>
</template>
