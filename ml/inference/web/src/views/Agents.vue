<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ServerStackIcon, PlusIcon, PauseIcon, PlayIcon } from '@heroicons/vue/24/outline'
import { useAgentsStore } from '@/stores/agents'
import { useDeploymentsStore } from '@/stores/deployments'
import EmptyState from '@/components/common/EmptyState.vue'
import AgentMap from '@/components/charts/AgentMap.vue'

const agentsStore = useAgentsStore()
const deploymentsStore = useDeploymentsStore()
const showInstallModal = ref(false)
const viewMode = ref<'table' | 'map'>('table')

const mapAgents = computed(() =>
  agentsStore.currentDeploymentAgents.map(agent => ({
    id: agent.id,
    hostname: agent.hostname,
    status: agent.status as 'online' | 'warning' | 'offline',
    region: agent.region || 'us-east-1',
    location: agent.location
  }))
)

onMounted(async () => {
  if (deploymentsStore.currentDeploymentId) {
    await agentsStore.fetchAgents()
  }
})

function getStatusBadge(status: string) {
  switch (status) {
    case 'online':
      return { text: 'Online', color: 'var(--status-green)', bg: 'rgba(34, 197, 94, 0.1)' }
    case 'warning':
      return { text: 'Warning', color: 'var(--status-amber)', bg: 'rgba(245, 158, 11, 0.1)' }
    case 'offline':
      return { text: 'Offline', color: 'var(--status-red)', bg: 'rgba(239, 68, 68, 0.1)' }
    default:
      return { text: status, color: 'var(--text-tertiary)', bg: 'var(--bg-card)' }
  }
}

function formatLastSeen(date: string) {
  if (!date) return '—'
  const d = new Date(date)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function togglePause(agentId: string, currentlyPaused: boolean) {
  // TODO: Implement pause/resume
}

function changeInterval(agentId: string, event: Event) {
  // TODO: Implement interval change
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold" style="color: var(--text-primary);">Agents</h1>
        <p style="color: var(--text-tertiary);">
          Manage agents collecting metrics from your infrastructure
        </p>
      </div>
      
      <div class="flex items-center gap-3">
        <!-- View Toggle -->
        <div class="flex items-center rounded-lg p-1" style="background: var(--bg-elevated); border: 1px solid var(--border-primary);">
          <button 
            @click="viewMode = 'table'"
            class="px-3 py-1 text-sm rounded-md transition-all cursor-pointer"
            :style="viewMode === 'table' 
              ? 'background: var(--accent-500); color: #fff;' 
              : 'color: var(--text-tertiary);'"
          >
            Table
          </button>
          <button 
            @click="viewMode = 'map'"
            class="px-3 py-1 text-sm rounded-md transition-all cursor-pointer"
            :style="viewMode === 'map' 
              ? 'background: var(--accent-500); color: #fff;' 
              : 'color: var(--text-tertiary);'"
          >
            Map
          </button>
        </div>
        
        <button @click="showInstallModal = true" class="btn-primary flex items-center gap-2">
          <PlusIcon class="w-5 h-5" />
          Add Agent
        </button>
      </div>
    </div>
    
    <!-- Agent Map View -->
    <AgentMap
      v-if="viewMode === 'map' && agentsStore.currentDeploymentAgents.length > 0"
      title="Agent Locations"
      :agents="mapAgents"
    />
    
    <!-- Empty State -->
    <EmptyState
      v-if="agentsStore.currentDeploymentAgents.length === 0"
      title="No agents connected"
      description="Install an agent on your servers to start collecting metrics."
      action-label="Install Agent"
      :icon="ServerStackIcon"
      @action="showInstallModal = true"
    />
    
    <!-- Agents Table -->
    <div v-else-if="viewMode === 'table'" class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="table-header">
            <tr>
              <th>Agent</th>
              <th>Status</th>
              <th>Metrics</th>
              <th>Last Seen</th>
              <th>Location</th>
              <th>Interval</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="agent in agentsStore.currentDeploymentAgents"
              :key="agent.id"
              class="table-row"
            >
              <td>
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background: var(--bg-elevated); border: 1px solid var(--border-primary);">
                    <ServerStackIcon class="w-4 h-4" style="color: var(--text-tertiary);" />
                  </div>
                  <div>
                    <div class="font-medium" style="color: var(--text-primary);">{{ agent.hostname }}</div>
                    <div class="text-xs" style="color: var(--text-tertiary);">{{ agent.id.slice(0, 8) }}</div>
                  </div>
                </div>
              </td>
              <td>
                <span 
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
                  :style="`background: ${getStatusBadge(agent.status).bg}; color: ${getStatusBadge(agent.status).color};`"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :style="`background: ${getStatusBadge(agent.status).color};`"></span>
                  {{ getStatusBadge(agent.status).text }}
                </span>
              </td>
              <td style="color: var(--text-secondary);">
                {{ agent.metrics?.join(', ') || '—' }}
              </td>
              <td style="color: var(--text-secondary);">
                {{ formatLastSeen(agent.last_seen) }}
              </td>
              <td style="color: var(--text-secondary);">
                {{ agent.location || agent.region || '—' }}
              </td>
              <td>
                <select 
                  :value="agent.collection_interval || 60"
                  @change="changeInterval(agent.id, $event)"
                  class="input py-1 px-2 text-xs w-20"
                >
                  <option :value="10">10s</option>
                  <option :value="30">30s</option>
                  <option :value="60">60s</option>
                  <option :value="120">2m</option>
                  <option :value="300">5m</option>
                </select>
              </td>
              <td class="text-right">
                <button
                  @click="togglePause(agent.id, agent.paused)"
                  class="p-1.5 rounded-lg transition-colors cursor-pointer"
                  style="color: var(--text-tertiary);"
                  :title="agent.paused ? 'Resume' : 'Pause'"
                >
                  <PlayIcon v-if="agent.paused" class="w-4 h-4" />
                  <PauseIcon v-else class="w-4 h-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
