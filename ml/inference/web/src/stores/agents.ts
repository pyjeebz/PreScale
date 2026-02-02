import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useDeploymentsStore } from './deployments'

export interface Agent {
  id: string
  deployment_id: string
  hostname: string
  platform: string
  last_seen: string
  status: 'online' | 'offline' | 'warning'
  metrics: string[]
  metrics_count: number
  location?: string
  region?: string
  latitude?: number
  longitude?: number
  ip_address?: string
}

export const useAgentsStore = defineStore('agents', () => {
  const api = useApi()
  const deploymentsStore = useDeploymentsStore()
  
  const agents = ref<Agent[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const currentDeploymentAgents = computed(() => 
    agents.value.filter(a => a.deployment_id === deploymentsStore.currentDeploymentId)
  )

  const onlineAgents = computed(() => 
    currentDeploymentAgents.value.filter(a => a.status === 'online')
  )

  const offlineAgents = computed(() => 
    currentDeploymentAgents.value.filter(a => a.status === 'offline')
  )

  const warningAgents = computed(() => 
    currentDeploymentAgents.value.filter(a => a.status === 'warning')
  )

  async function fetchAgents(deploymentId?: string) {
    const depId = deploymentId || deploymentsStore.currentDeploymentId
    if (!depId) return

    isLoading.value = true
    error.value = null
    try {
      const data = await api.get<Agent[]>(`/api/deployments/${depId}/agents`)
      
      // Update agents for this deployment
      agents.value = [
        ...agents.value.filter(a => a.deployment_id !== depId),
        ...data
      ]
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch agents'
    } finally {
      isLoading.value = false
    }
  }

  async function deleteAgent(id: string) {
    isLoading.value = true
    error.value = null
    try {
      await api.delete(`/api/agents/${id}`)
      agents.value = agents.value.filter(a => a.id !== id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete agent'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function getAgentById(id: string) {
    return agents.value.find(a => a.id === id)
  }

  return {
    agents,
    currentDeploymentAgents,
    onlineAgents,
    offlineAgents,
    warningAgents,
    isLoading,
    error,
    fetchAgents,
    deleteAgent,
    getAgentById
  }
})
