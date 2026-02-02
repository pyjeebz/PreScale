import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

export interface Deployment {
  id: string
  name: string
  description: string
  environment: 'development' | 'staging' | 'production'
  created_at: string
  agents_count: number
  agents_online: number
  metrics_count: number
}

export const useDeploymentsStore = defineStore('deployments', () => {
  const api = useApi()
  
  const deployments = ref<Deployment[]>([])
  const currentDeploymentId = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const currentDeployment = computed(() => 
    deployments.value.find(d => d.id === currentDeploymentId.value) || null
  )

  async function fetchDeployments() {
    isLoading.value = true
    error.value = null
    try {
      const data = await api.get<Deployment[]>('/api/deployments')
      deployments.value = data
      
      // Set first deployment as current if none selected
      if (!currentDeploymentId.value && data.length > 0) {
        currentDeploymentId.value = data[0].id
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch deployments'
    } finally {
      isLoading.value = false
    }
  }

  async function createDeployment(deployment: Omit<Deployment, 'id' | 'created_at' | 'agents_count' | 'agents_online' | 'metrics_count'>) {
    isLoading.value = true
    error.value = null
    try {
      const data = await api.post<Deployment>('/api/deployments', deployment)
      deployments.value.push(data)
      currentDeploymentId.value = data.id
      return data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create deployment'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteDeployment(id: string) {
    isLoading.value = true
    error.value = null
    try {
      await api.delete(`/api/deployments/${id}`)
      deployments.value = deployments.value.filter(d => d.id !== id)
      
      if (currentDeploymentId.value === id) {
        currentDeploymentId.value = deployments.value[0]?.id || null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete deployment'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function setCurrentDeployment(id: string) {
    currentDeploymentId.value = id
  }

  return {
    deployments,
    currentDeploymentId,
    currentDeployment,
    isLoading,
    error,
    fetchDeployments,
    createDeployment,
    deleteDeployment,
    setCurrentDeployment
  }
})
