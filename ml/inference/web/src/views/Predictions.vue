<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChartBarIcon } from '@heroicons/vue/24/outline'
import PredictionChart from '@/components/charts/PredictionChart.vue'

const selectedMetric = ref('cpu_utilization')
const selectedAgent = ref('all')
const selectedHorizon = ref('24')
const showPrediction = ref(false)

const metrics = [
  { value: 'cpu_utilization', label: 'CPU Utilization' },
  { value: 'memory_utilization', label: 'Memory Utilization' },
  { value: 'memory_bytes', label: 'Memory Bytes' },
  { value: 'db_cpu', label: 'Database CPU' },
  { value: 'db_memory', label: 'Database Memory' },
  { value: 'db_connections', label: 'Database Connections' }
]

const horizons = [
  { value: '6', label: '6 hours' },
  { value: '12', label: '12 hours' },
  { value: '24', label: '24 hours' },
  { value: '48', label: '48 hours' },
  { value: '168', label: '7 days' }
]

// Demo prediction data
const generateHistoricalData = () => {
  const data: number[] = []
  let value = 40 + Math.random() * 20
  for (let i = 0; i < 24; i++) {
    value += (Math.random() - 0.5) * 10
    value = Math.max(20, Math.min(80, value))
    data.push(value)
  }
  return data
}

const generateForecastData = (lastValue: number, steps: number) => {
  const data: number[] = []
  let value = lastValue
  const trend = Math.random() > 0.5 ? 1 : -1
  for (let i = 0; i < steps; i++) {
    value += trend * (Math.random() * 3) + (Math.random() - 0.5) * 5
    value = Math.max(10, Math.min(95, value))
    data.push(value)
  }
  return data
}

const historicalData = ref<number[]>([])
const forecastData = ref<number[]>([])
const upperBound = ref<number[]>([])
const lowerBound = ref<number[]>([])

const generatePrediction = () => {
  const historical = generateHistoricalData()
  const horizonHours = parseInt(selectedHorizon.value)
  const forecast = generateForecastData(historical[historical.length - 1], horizonHours)
  
  historicalData.value = historical
  forecastData.value = forecast
  upperBound.value = forecast.map(v => Math.min(100, v + 10 + Math.random() * 5))
  lowerBound.value = forecast.map(v => Math.max(0, v - 10 - Math.random() * 5))
  showPrediction.value = true
}

const labels = computed(() => {
  const now = new Date()
  const allLabels: string[] = []
  
  // Historical labels (past 24 hours)
  for (let i = 23; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 3600000)
    allLabels.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }))
  }
  
  // Forecast labels
  const horizonHours = parseInt(selectedHorizon.value)
  for (let i = 1; i <= horizonHours; i++) {
    const time = new Date(now.getTime() + i * 3600000)
    allLabels.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }))
  }
  
  return allLabels
})

const prediction = computed(() => {
  if (!showPrediction.value || forecastData.value.length === 0) return null
  
  const peak = Math.max(...forecastData.value)
  const peakIndex = forecastData.value.indexOf(peak)
  const peakTime = new Date(Date.now() + (peakIndex + 1) * 3600000)
  
  return {
    peakValue: peak,
    peakTime: peakTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
    confidence: 0.85 + Math.random() * 0.1,
    horizon: horizons.find(h => h.value === selectedHorizon.value)?.label || ''
  }
})

const currentValue = computed(() => {
  if (historicalData.value.length === 0) return null
  return historicalData.value[historicalData.value.length - 1]
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">Predictions</h1>
      <p class="text-slate-500 dark:text-slate-400">
        Forecast future resource utilization using ML models
      </p>
    </div>
    
    <!-- Prediction Form -->
    <div class="card p-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Agent</label>
          <select v-model="selectedAgent" class="input">
            <option value="all">All Agents</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Metric</label>
          <select v-model="selectedMetric" class="input">
            <option v-for="metric in metrics" :key="metric.value" :value="metric.value">
              {{ metric.label }}
            </option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Horizon</label>
          <select v-model="selectedHorizon" class="input">
            <option v-for="horizon in horizons" :key="horizon.value" :value="horizon.value">
              {{ horizon.label }}
            </option>
          </select>
        </div>
        
        <div class="flex items-end">
          <button @click="generatePrediction" class="btn-primary w-full">
            Generate Prediction
          </button>
        </div>
      </div>
    </div>
    
    <!-- Prediction Chart -->
    <PredictionChart
      v-if="showPrediction"
      :title="metrics.find(m => m.value === selectedMetric)?.label + ' Forecast'"
      :subtitle="`${selectedHorizon}-hour forecast with 95% confidence interval`"
      :historical-data="historicalData"
      :forecast-data="forecastData"
      :upper-bound="upperBound"
      :lower-bound="lowerBound"
      :labels="labels"
      :prediction="prediction"
    />
    
    <!-- Empty State -->
    <div v-else class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-medium text-slate-900 dark:text-white">
          {{ metrics.find(m => m.value === selectedMetric)?.label }} Forecast
        </h3>
      </div>
      
      <div class="h-80 flex flex-col items-center justify-center text-slate-400">
        <ChartBarIcon class="w-12 h-12 mb-4" />
        <p>Select parameters and click "Generate Prediction"</p>
        <p class="text-sm mt-1">Historical data + ML forecast will appear here</p>
      </div>
    </div>
    
    <!-- Prediction Summary -->
    <div v-if="showPrediction && prediction" class="card p-6">
      <h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Prediction Summary</h3>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Current Value</p>
          <p class="text-2xl font-semibold text-slate-900 dark:text-white">{{ currentValue?.toFixed(1) }}%</p>
        </div>
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Predicted Peak</p>
          <p class="text-2xl font-semibold text-helios-600">{{ prediction.peakValue?.toFixed(1) }}%</p>
        </div>
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Peak Time</p>
          <p class="text-2xl font-semibold text-slate-900 dark:text-white">{{ prediction.peakTime }}</p>
        </div>
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Confidence</p>
          <p class="text-2xl font-semibold text-green-600">{{ (prediction.confidence * 100).toFixed(0) }}%</p>
        </div>
      </div>
    </div>
    
    <!-- Empty Prediction Summary -->
    <div v-else class="card p-6">
      <h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Prediction Summary</h3>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Current Value</p>
          <p class="text-2xl font-semibold text-slate-900 dark:text-white">—</p>
        </div>
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Predicted Peak</p>
          <p class="text-2xl font-semibold text-slate-900 dark:text-white">—</p>
        </div>
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Peak Time</p>
          <p class="text-2xl font-semibold text-slate-900 dark:text-white">—</p>
        </div>
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Confidence</p>
          <p class="text-2xl font-semibold text-slate-900 dark:text-white">—</p>
        </div>
      </div>
    </div>
  </div>
</template>
