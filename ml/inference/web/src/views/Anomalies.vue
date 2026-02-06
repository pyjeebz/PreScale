<script setup lang="ts">
import { ref, computed } from 'vue'
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import EmptyState from '@/components/common/EmptyState.vue'
import Badge from '@/components/common/Badge.vue'
import AnomalyTimeline from '@/components/charts/AnomalyTimeline.vue'

const severityFilter = ref('all')
const timeRange = ref('24h')

// Demo anomalies
const demoAnomalies = ref([
  {
    id: '1',
    metric: 'cpu_utilization',
    agent: 'api-server-1',
    value: 92,
    unit: '%',
    deviation: '+3.2σ',
    severity: 'critical' as const,
    time: '2 hours ago',
    timestamp: Date.now() - 2 * 3600000
  },
  {
    id: '2',
    metric: 'memory_utilization',
    agent: 'worker-node-3',
    value: 78,
    unit: '%',
    deviation: '+2.1σ',
    severity: 'warning' as const,
    time: '4 hours ago',
    timestamp: Date.now() - 4 * 3600000
  },
  {
    id: '3',
    metric: 'db_connections',
    agent: 'db-primary',
    value: 450,
    unit: '',
    deviation: '+1.8σ',
    severity: 'info' as const,
    time: '8 hours ago',
    timestamp: Date.now() - 8 * 3600000
  }
])

const showDemoData = ref(false)

const filteredAnomalies = computed(() => {
  if (!showDemoData.value) return []
  if (severityFilter.value === 'all') return demoAnomalies.value
  return demoAnomalies.value.filter(a => a.severity === severityFilter.value)
})

const timelineStartTime = computed(() => Date.now() - 24 * 3600000)
const timelineEndTime = computed(() => Date.now())

const handleAnomalyClick = (anomaly: any) => {
  console.log('Anomaly clicked:', anomaly)
}

const loadDemoData = () => {
  showDemoData.value = true
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">Anomalies</h1>
        <p class="text-slate-500 dark:text-slate-400">
          Detected anomalies in your infrastructure metrics
        </p>
      </div>
      
      <div class="flex items-center gap-2">
        <select v-model="severityFilter" class="input w-40">
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <select v-model="timeRange" class="input w-40">
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
        </select>
        <button v-if="!showDemoData" @click="loadDemoData" class="btn-secondary">
          Load Demo Data
        </button>
      </div>
    </div>
    
    <!-- Anomaly Timeline -->
    <AnomalyTimeline
      v-if="showDemoData"
      title="Anomaly Timeline (Last 24 Hours)"
      :anomalies="filteredAnomalies"
      :start-time="timelineStartTime"
      :end-time="timelineEndTime"
      @anomaly-click="handleAnomalyClick"
    />
    
    <!-- Empty State -->
    <EmptyState
      v-if="!showDemoData"
      title="No anomalies detected"
      description="Great news! No anomalies have been detected in your infrastructure. We'll alert you when something unusual is found."
      :icon="ExclamationTriangleIcon"
    />
    
    <!-- Anomalies Table -->
    <div v-if="showDemoData && filteredAnomalies.length > 0" class="card">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-slate-50 dark:bg-slate-900">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Severity
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Agent
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Metric
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Value
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Deviation
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Time
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
            <tr 
              v-for="anomaly in filteredAnomalies" 
              :key="anomaly.id"
              class="hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer"
              @click="handleAnomalyClick(anomaly)"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <Badge :variant="anomaly.severity === 'critical' ? 'error' : anomaly.severity">
                  {{ anomaly.severity }}
                </Badge>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-white">
                {{ anomaly.agent }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                {{ anomaly.metric }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium" :class="anomaly.severity === 'critical' ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'">
                {{ anomaly.value }}{{ anomaly.unit }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                {{ anomaly.deviation }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                {{ anomaly.time }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
