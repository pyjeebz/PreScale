import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useDeploymentsStore } from './deployments'

export interface Anomaly {
  id: string
  deployment_id: string
  agent_id: string
  metric_name: string
  timestamp: string
  expected_value: number
  actual_value: number
  deviation: number
  severity: 'critical' | 'warning' | 'info'
  acknowledged: boolean
  resolved: boolean
}

export const useAnomaliesStore = defineStore('anomalies', () => {
  const api = useApi()
  const deploymentsStore = useDeploymentsStore()
  
  const anomalies = ref<Anomaly[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAnomalies(deploymentId?: string) {
    const depId = deploymentId || deploymentsStore.currentDeploymentId
    if (!depId) return

    isLoading.value = true
    error.value = null
    try {
      const data = await api.get<Anomaly[]>(`/api/anomalies?deployment=${depId}`)
      anomalies.value = data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch anomalies'
    } finally {
      isLoading.value = false
    }
  }

  async function acknowledgeAnomaly(id: string) {
    try {
      await api.post(`/api/anomalies/${id}/acknowledge`)
      const anomaly = anomalies.value.find(a => a.id === id)
      if (anomaly) {
        anomaly.acknowledged = true
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to acknowledge anomaly'
      throw e
    }
  }

  async function resolveAnomaly(id: string) {
    try {
      await api.post(`/api/anomalies/${id}/resolve`)
      const anomaly = anomalies.value.find(a => a.id === id)
      if (anomaly) {
        anomaly.resolved = true
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to resolve anomaly'
      throw e
    }
  }

  return {
    anomalies,
    isLoading,
    error,
    fetchAnomalies,
    acknowledgeAnomaly,
    resolveAnomaly
  }
})
