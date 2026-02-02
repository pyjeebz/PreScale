<script setup lang="ts">
import { ref } from 'vue'
import { ChartBarIcon } from '@heroicons/vue/24/outline'

const selectedMetric = ref('cpu_utilization')
const selectedAgent = ref('all')
const selectedHorizon = ref('24')

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
          <button class="btn-primary w-full">
            Generate Prediction
          </button>
        </div>
      </div>
    </div>
    
    <!-- Prediction Chart Placeholder -->
    <div class="card p-6">
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
    
    <!-- Prediction Summary Placeholder -->
    <div class="card p-6">
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
