<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref } from 'vue'
import {
  ServerStackIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  ChartBarIcon
} from '@heroicons/vue/24/outline'
import StatsCard from '@/components/common/StatsCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import MetricChart from '@/components/charts/MetricChart.vue'
import AgentMap from '@/components/charts/AgentMap.vue'
import { useDeploymentsStore } from '@/stores/deployments'
import { useAgentsStore } from '@/stores/agents'
import { CubeIcon } from '@heroicons/vue/24/outline'
import api from '@/services/api'

const deploymentsStore = useDeploymentsStore()
const agentsStore = useAgentsStore()

// Real metrics data
const cpuData = ref<number[]>([])
const memoryData = ref<number[]>([])
const timeLabels = ref<string[]>([])
const latestCpu = ref<number | null>(null)
const latestMemory = ref<number | null>(null)
let refreshInterval: number | null = null

// Fetch metrics from API
const fetchMetrics = async () => {
  // Fetch all metrics without deployment filtering
  try {
    // Fetch CPU metrics
    const cpuResponse = await api.get('/metrics/cpu_utilization', {
      params: { hours: 1, limit: 50 }
    })
    if (cpuResponse.data.data?.length) {
      // Convert from decimal (0.5) to percentage (50)
      cpuData.value = cpuResponse.data.data.map((d: any) => d.value * 100)
      timeLabels.value = cpuResponse.data.data.map((d: any) => {
        const time = new Date(d.timestamp)
        return time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      })
      latestCpu.value = cpuResponse.data.latest?.value ? cpuResponse.data.latest.value * 100 : null
    }
    
    // Fetch Memory metrics
    const memResponse = await api.get('/metrics/memory_utilization', {
      params: { hours: 1, limit: 50 }
    })
    if (memResponse.data.data?.length) {
      // Convert from decimal to percentage
      memoryData.value = memResponse.data.data.map((d: any) => d.value * 100)
      latestMemory.value = memResponse.data.latest?.value ? memResponse.data.latest.value * 100 : null
    }
  } catch (error) {
    console.error('Failed to fetch metrics:', error)
  }
}

// Map agents for AgentMap component
const mapAgents = computed(() => 
  agentsStore.currentDeploymentAgents.map(agent => ({
    id: agent.id,
    hostname: agent.hostname,
    status: agent.status as 'online' | 'warning' | 'offline',
    region: agent.region || 'us-east-1',
    location: agent.location
  }))
)

const stats = computed(() => [
  {
    title: 'Agents Online',
    value: agentsStore.onlineAgents.length,
    subtitle: `${agentsStore.currentDeploymentAgents.length} total`,
    icon: ServerStackIcon,
    color: 'green' as const
  },
  {
    title: 'CPU Usage',
    value: latestCpu.value !== null ? `${latestCpu.value.toFixed(1)}%` : '—',
    subtitle: latestCpu.value !== null ? 'Current utilization' : 'Waiting for data',
    icon: ChartBarIcon,
    color: (latestCpu.value ?? 0) > 80 ? 'red' as const : 'blue' as const
  },
  {
    title: 'Memory Usage',
    value: latestMemory.value !== null ? `${latestMemory.value.toFixed(1)}%` : '—',
    subtitle: latestMemory.value !== null ? 'Current utilization' : 'Waiting for data',
    icon: ExclamationCircleIcon,
    color: (latestMemory.value ?? 0) > 90 ? 'red' as const : 'green' as const
  },
  {
    title: 'Warnings',
    value: agentsStore.warningAgents.length,
    subtitle: agentsStore.warningAgents.length > 0 ? 'Needs attention' : 'All healthy',
    icon: ExclamationTriangleIcon,
    color: agentsStore.warningAgents.length > 0 ? 'yellow' as const : 'slate' as const
  }
])

onMounted(async () => {
  await deploymentsStore.fetchDeployments()
  // Always fetch metrics, regardless of deployment selection
  await fetchMetrics()
  if (deploymentsStore.currentDeploymentId) {
    await agentsStore.fetchAgents()
  }
  // Auto-refresh metrics every 10 seconds
  refreshInterval = window.setInterval(async () => {
    await fetchMetrics()
    if (deploymentsStore.currentDeploymentId) {
      await agentsStore.fetchAgents()
    }
  }, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">Dashboard</h1>
      <p class="text-slate-500 dark:text-slate-400">
        Overview of your infrastructure health and predictions
      </p>
    </div>
    
    <!-- Empty State if no deployment -->
    <EmptyState
      v-if="!deploymentsStore.currentDeployment"
      title="No deployments yet"
      description="Create your first deployment to start monitoring your infrastructure."
      action-label="Create Deployment"
      :icon="CubeIcon"
      @action="$router.push('/deployments')"
    />
    
    <template v-else>
      <!-- Stats Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          v-for="stat in stats"
          :key="stat.title"
          :title="stat.title"
          :value="stat.value"
          :subtitle="stat.subtitle"
          :icon="stat.icon"
          :color="stat.color"
        />
      </div>
      
      <!-- Charts Row -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- CPU Chart -->
        <MetricChart
          title="CPU Utilization"
          :data="cpuData"
          :labels="timeLabels"
          unit="%"
          color="#f97316"
          :filled="true"
        />
        
        <!-- Memory Chart -->
        <MetricChart
          title="Memory Utilization"
          :data="memoryData"
          :labels="timeLabels"
          unit="%"
          color="#3b82f6"
          :filled="true"
        />
      </div>
      
      <!-- Agent Locations & Recommendations -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Agent Locations Map -->
        <AgentMap
          title="Agent Locations"
          :agents="mapAgents"
        />
        
        <!-- Recommendations -->
        <div class="card p-6">
          <h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Recommendations</h3>
          <div class="space-y-4">
            <div class="p-4 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700">
              <p class="text-slate-500 dark:text-slate-400 text-center py-8">
                No recommendations at this time.
                <br />
                <span class="text-sm">Predictions will generate recommendations when issues are forecasted.</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
