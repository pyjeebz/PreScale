<script setup lang="ts">
import { onMounted, computed } from 'vue'
import {
  ServerStackIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  ChartBarIcon
} from '@heroicons/vue/24/outline'
import StatsCard from '@/components/common/StatsCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { useDeploymentsStore } from '@/stores/deployments'
import { useAgentsStore } from '@/stores/agents'
import { CubeIcon } from '@heroicons/vue/24/outline'

const deploymentsStore = useDeploymentsStore()
const agentsStore = useAgentsStore()

const stats = computed(() => [
  {
    title: 'Agents Online',
    value: agentsStore.onlineAgents.length,
    subtitle: `${agentsStore.currentDeploymentAgents.length} total`,
    icon: ServerStackIcon,
    color: 'green' as const
  },
  {
    title: 'Anomalies Today',
    value: 0,
    subtitle: 'No anomalies detected',
    icon: ExclamationTriangleIcon,
    color: 'blue' as const
  },
  {
    title: 'Warnings',
    value: agentsStore.warningAgents.length,
    subtitle: agentsStore.warningAgents.length > 0 ? 'Needs attention' : 'All healthy',
    icon: ExclamationCircleIcon,
    color: agentsStore.warningAgents.length > 0 ? 'yellow' as const : 'slate' as const
  },
  {
    title: 'Predicted Peak',
    value: '—',
    subtitle: 'No predictions yet',
    icon: ChartBarIcon,
    color: 'blue' as const
  }
])

onMounted(async () => {
  await deploymentsStore.fetchDeployments()
  if (deploymentsStore.currentDeploymentId) {
    await agentsStore.fetchAgents()
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
        <!-- CPU Chart Placeholder -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-slate-900 dark:text-white">CPU Utilization</h3>
            <select class="text-sm bg-transparent border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1">
              <option>Last 24h</option>
              <option>Last 7d</option>
              <option>Last 30d</option>
            </select>
          </div>
          <div class="h-64 flex items-center justify-center text-slate-400">
            <p>Chart will appear when metrics are collected</p>
          </div>
        </div>
        
        <!-- Memory Chart Placeholder -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-slate-900 dark:text-white">Memory Utilization</h3>
            <select class="text-sm bg-transparent border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1">
              <option>Last 24h</option>
              <option>Last 7d</option>
              <option>Last 30d</option>
            </select>
          </div>
          <div class="h-64 flex items-center justify-center text-slate-400">
            <p>Chart will appear when metrics are collected</p>
          </div>
        </div>
      </div>
      
      <!-- Agent Locations & Recommendations -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Agent Locations Map Placeholder -->
        <div class="card p-6">
          <h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Agent Locations</h3>
          <div class="h-64 bg-slate-50 dark:bg-slate-900 rounded-lg flex items-center justify-center text-slate-400">
            <p>World map with agent locations</p>
          </div>
          <div class="mt-4 flex items-center gap-4 text-sm">
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-green-500"></span>
              {{ agentsStore.onlineAgents.length }} Online
            </span>
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
              {{ agentsStore.warningAgents.length }} Warning
            </span>
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-red-500"></span>
              {{ agentsStore.offlineAgents.length }} Offline
            </span>
          </div>
        </div>
        
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
