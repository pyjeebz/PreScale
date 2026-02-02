import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useDeploymentsStore } from './deployments'

export interface Prediction {
  metric_name: string
  agent_id: string
  deployment_id: string
  current_value: number
  predicted_values: number[]
  timestamps: string[]
  confidence: number
  trend: 'increasing' | 'decreasing' | 'stable'
  predicted_peak: number
  peak_time: string
}

export const usePredictionsStore = defineStore('predictions', () => {
  const api = useApi()
  const deploymentsStore = useDeploymentsStore()
  
  const currentPrediction = ref<Prediction | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function getPrediction(params: {
    metric_name: string
    agent_id?: string
    horizon_hours?: number
  }) {
    const deploymentId = deploymentsStore.currentDeploymentId
    if (!deploymentId) return

    isLoading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams({
        deployment: deploymentId,
        metric_name: params.metric_name,
        ...(params.agent_id && { agent_id: params.agent_id }),
        ...(params.horizon_hours && { horizon_hours: params.horizon_hours.toString() })
      })
      
      const data = await api.get<Prediction>(`/api/predict?${queryParams}`)
      currentPrediction.value = data
      return data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to get prediction'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function clearPrediction() {
    currentPrediction.value = null
  }

  return {
    currentPrediction,
    isLoading,
    error,
    getPrediction,
    clearPrediction
  }
})
