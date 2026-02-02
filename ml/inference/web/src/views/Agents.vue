<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ServerStackIcon, PlusIcon } from '@heroicons/vue/24/outline'
import { useAgentsStore } from '@/stores/agents'
import { useDeploymentsStore } from '@/stores/deployments'
import EmptyState from '@/components/common/EmptyState.vue'
import Badge from '@/components/common/Badge.vue'
import Modal from '@/components/common/Modal.vue'

const agentsStore = useAgentsStore()
const deploymentsStore = useDeploymentsStore()

const showInstallModal = ref(false)

const installCommand = `pip install helios-agent

# Start the agent
helios-agent start \\
  --deployment ${deploymentsStore.currentDeployment?.id || 'your-deployment'} \\
  --endpoint http://localhost:8000`

onMounted(async () => {
  if (deploymentsStore.currentDeploymentId) {
    await agentsStore.fetchAgents()
  }
})

function getStatusBadge(status: string) {
  switch (status) {
    case 'online':
      return 'success'
    case 'warning':
      return 'warning'
    case 'offline':
      return 'error'
    default:
      return 'default'
  }
}

function formatLastSeen(date: string) {
  const now = new Date()
  const seen = new Date(date)
  const diff = Math.floor((now.getTime() - seen.getTime()) / 1000)
  
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">Agents</h1>
        <p class="text-slate-500 dark:text-slate-400">
          Manage agents collecting metrics from your infrastructure
        </p>
      </div>
      
      <button @click="showInstallModal = true" class="btn-primary flex items-center gap-2">
        <PlusIcon class="w-5 h-5" />
        Add Agent
      </button>
    </div>
    
    <!-- Empty State -->
    <EmptyState
      v-if="agentsStore.currentDeploymentAgents.length === 0"
      title="No agents installed"
      description="Install an agent on your servers to start collecting metrics."
      action-label="Install Agent"
      :icon="ServerStackIcon"
      @action="showInstallModal = true"
    />
    
    <!-- Agents Table -->
    <div v-else class="card">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-slate-50 dark:bg-slate-900">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Agent
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Platform
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Metrics
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Last Seen
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Location
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
            <tr
              v-for="agent in agentsStore.currentDeploymentAgents"
              :key="agent.id"
              class="hover:bg-slate-50 dark:hover:bg-slate-900/50"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                    <ServerStackIcon class="w-4 h-4 text-slate-500" />
                  </div>
                  <div>
                    <p class="text-sm font-medium text-slate-900 dark:text-white">{{ agent.hostname }}</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400">{{ agent.id }}</p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <Badge :variant="getStatusBadge(agent.status)">
                  {{ agent.status }}
                </Badge>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                {{ agent.platform }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                {{ agent.metrics?.join(', ') || '—' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                {{ formatLastSeen(agent.last_seen) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                {{ agent.location || agent.region || '—' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right">
                <button
                  @click="agentsStore.deleteAgent(agent.id)"
                  class="text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                >
                  Remove
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- Install Agent Modal -->
    <Modal :open="showInstallModal" title="Install Agent" size="lg" @close="showInstallModal = false">
      <div class="space-y-4">
        <p class="text-sm text-slate-600 dark:text-slate-300">
          Run these commands on the server you want to monitor:
        </p>
        
        <div class="bg-slate-900 rounded-lg p-4 overflow-x-auto">
          <pre class="text-sm text-slate-300 font-mono whitespace-pre-wrap">{{ installCommand }}</pre>
        </div>
        
        <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <span class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></span>
          Waiting for agent to connect...
        </div>
      </div>
      
      <div class="mt-6 flex justify-end">
        <button @click="showInstallModal = false" class="btn-secondary">
          Close
        </button>
      </div>
    </Modal>
  </div>
</template>
