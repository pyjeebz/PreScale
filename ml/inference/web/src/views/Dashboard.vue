<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ServerStackIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  ChartBarIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  CpuChipIcon
} from '@heroicons/vue/24/outline'
import { useDeploymentsStore } from '@/stores/deployments'
import { useAgentsStore } from '@/stores/agents'
import { CubeIcon } from '@heroicons/vue/24/outline'
import EmptyState from '@/components/common/EmptyState.vue'
import { mlApi, type Recommendation, type RetrainStatus } from '@/services/api'

const deploymentsStore = useDeploymentsStore()
const agentsStore = useAgentsStore()

const recommendations = ref<Recommendation[]>([])
const anomalyCount = ref(0)
const loadingRecs = ref(false)
const retrainStatus = ref<RetrainStatus | null>(null)
const retraining = ref(false)
const retrainHours = ref(24)

async function fetchRecommendations() {
  if (!deploymentsStore.currentDeployment) return
  loadingRecs.value = true
  try {
    const response = await mlApi.recommend({
      workload: deploymentsStore.currentDeployment.name,
      namespace: 'default',
      current_state: {
        replicas: 2,
        cpu_request: '100m',
        memory_request: '256Mi'
      }
    })
    recommendations.value = response.recommendations || []
  } catch (e) {
    console.error('Failed to fetch recommendations:', e)
  } finally {
    loadingRecs.value = false
  }
}

async function fetchRetrainStatus() {
  try {
    retrainStatus.value = await mlApi.getRetrainStatus()
  } catch (e) {
    console.error('Failed to fetch retrain status:', e)
  }
}

async function triggerRetrain() {
  retraining.value = true
  try {
    await mlApi.triggerRetrain(retrainHours.value)
    await fetchRetrainStatus()
  } catch (e) {
    console.error('Retrain failed:', e)
  } finally {
    retraining.value = false
  }
}

onMounted(async () => {
  await deploymentsStore.fetchDeployments()
  fetchRetrainStatus()
  if (deploymentsStore.currentDeploymentId) {
    await agentsStore.fetchAgents()
    await fetchRecommendations()
  }
})

watch(() => deploymentsStore.currentDeploymentId, async (newId) => {
  if (newId) {
    await agentsStore.fetchAgents()
    await fetchRecommendations()
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-semibold" style="color: var(--text-primary);">Dashboard</h1>
      <p style="color: var(--text-tertiary);">
        AI-powered insights for your infrastructure
      </p>
    </div>
    
    <!-- Empty State if no deployment -->
    <EmptyState
      v-if="!deploymentsStore.currentDeployment"
      title="No deployments yet"
      description="Create your first deployment to start getting AI insights."
      action-label="Create Deployment"
      :icon="CubeIcon"
      @action="$router.push('/deployments')"
    />
    
    <template v-else>
      <!-- Quick Stats -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Agents Status -->
        <div class="bento-card p-5 flex items-center gap-4">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center" style="background: rgba(34, 197, 94, 0.1);">
            <ServerStackIcon class="w-6 h-6" style="color: var(--status-green);" />
          </div>
          <div>
            <p class="text-2xl font-bold" style="color: var(--text-primary);">
              {{ agentsStore.onlineAgents.length }}
            </p>
            <p class="text-sm" style="color: var(--text-tertiary);">Agents Online</p>
          </div>
        </div>
        
        <!-- Anomalies -->
        <div class="bento-card p-5 flex items-center gap-4">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center" 
            :style="anomalyCount > 0 
              ? 'background: rgba(239, 68, 68, 0.1);' 
              : 'background: var(--bg-card);'"
          >
            <ExclamationTriangleIcon class="w-6 h-6" 
              :style="anomalyCount > 0 
                ? 'color: var(--status-red);' 
                : 'color: var(--text-tertiary);'" 
            />
          </div>
          <div>
            <p class="text-2xl font-bold" style="color: var(--text-primary);">
              {{ anomalyCount }}
            </p>
            <p class="text-sm" style="color: var(--text-tertiary);">Active Anomalies</p>
          </div>
        </div>
        
        <!-- Recommendations -->
        <div class="bento-card p-5 flex items-center gap-4">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center"
            :style="recommendations.length > 0 
              ? 'background: rgba(245, 158, 11, 0.1);' 
              : 'background: var(--bg-card);'"
          >
            <LightBulbIcon class="w-6 h-6" 
              :style="recommendations.length > 0 
                ? 'color: var(--status-amber);' 
                : 'color: var(--text-tertiary);'" 
            />
          </div>
          <div>
            <p class="text-2xl font-bold" style="color: var(--text-primary);">
              {{ recommendations.length }}
            </p>
            <p class="text-sm" style="color: var(--text-tertiary);">Recommendations</p>
          </div>
        </div>
      </div>
      
      <!-- Quick Actions -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Predictions Card -->
        <RouterLink 
          to="/predictions" 
          class="bento-card p-6 transition-all group block"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(99, 102, 241, 0.1);">
              <ChartBarIcon class="w-5 h-5" style="color: var(--accent-400);" />
            </div>
            <ArrowRightIcon class="w-5 h-5 transition-colors" style="color: var(--text-tertiary);" />
          </div>
          <h3 class="font-semibold mb-1" style="color: var(--text-primary);">Predictions</h3>
          <p class="text-sm" style="color: var(--text-tertiary);">Forecast CPU, memory, and resource usage</p>
        </RouterLink>
        
        <!-- Anomalies Card -->
        <RouterLink 
          to="/anomalies" 
          class="bento-card p-6 transition-all group block"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(239, 68, 68, 0.1);">
              <ExclamationTriangleIcon class="w-5 h-5" style="color: var(--status-red);" />
            </div>
            <ArrowRightIcon class="w-5 h-5 transition-colors" style="color: var(--text-tertiary);" />
          </div>
          <h3 class="font-semibold mb-1" style="color: var(--text-primary);">Anomalies</h3>
          <p class="text-sm" style="color: var(--text-tertiary);">Detect unusual patterns in your metrics</p>
        </RouterLink>
        
        <!-- Agents Card -->
        <RouterLink 
          to="/agents" 
          class="bento-card p-6 transition-all group block"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(34, 197, 94, 0.1);">
              <ServerStackIcon class="w-5 h-5" style="color: var(--status-green);" />
            </div>
            <ArrowRightIcon class="w-5 h-5 transition-colors" style="color: var(--text-tertiary);" />
          </div>
          <h3 class="font-semibold mb-1" style="color: var(--text-primary);">Agents</h3>
          <p class="text-sm" style="color: var(--text-tertiary);">Manage data collectors across your infrastructure</p>
        </RouterLink>
      </div>
      
      <!-- Model Training Status -->
      <div class="bento-card p-6">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(139, 92, 246, 0.1);">
              <CpuChipIcon class="w-5 h-5" style="color: #a78bfa;" />
            </div>
            <div>
              <h3 class="text-lg font-medium" style="color: var(--text-primary);">Model Training</h3>
              <p class="text-xs" style="color: var(--text-tertiary);" v-if="retrainStatus">
                Source: <span class="font-medium uppercase">{{ retrainStatus.data_source }}</span>
                · Every {{ retrainStatus.interval_hours }}h
              </p>
            </div>
          </div>
          <span 
            v-if="retrainStatus" 
            class="px-2.5 py-1 text-xs rounded-full font-medium"
            :style="retrainStatus.running 
              ? 'background: rgba(34, 197, 94, 0.1); color: var(--status-green);' 
              : 'background: var(--bg-card); color: var(--text-tertiary); border: 1px solid var(--border-primary);'"
          >
            {{ retrainStatus.running ? 'Scheduler Active' : 'Scheduler Off' }}
          </span>
        </div>

        <!-- Last Run Info -->
        <div v-if="retrainStatus?.last_run" class="mb-4 p-3 rounded-lg" style="background: var(--bg-elevated); border: 1px solid var(--border-primary);">
          <div class="flex items-center justify-between text-sm">
            <span style="color: var(--text-tertiary);">Last Run</span>
            <span class="font-medium"
              :style="
                retrainStatus.last_run.status === 'completed' ? 'color: var(--status-green);' :
                retrainStatus.last_run.status === 'failed' ? 'color: var(--status-red);' :
                retrainStatus.last_run.status === 'skipped' ? 'color: var(--status-amber);' : 'color: var(--text-secondary);'"
            >
              {{ retrainStatus.last_run.status }}
            </span>
          </div>
          <div v-if="retrainStatus.last_run.data_points" class="flex items-center justify-between text-sm mt-1">
            <span style="color: var(--text-tertiary);">Data Points</span>
            <span class="font-medium" style="color: var(--text-secondary);">{{ retrainStatus.last_run.data_points.toLocaleString() }}</span>
          </div>
          <div v-if="retrainStatus.last_run.deployed" class="flex items-center justify-between text-sm mt-1">
            <span style="color: var(--text-tertiary);">Model Deployed</span>
            <CheckCircleIcon class="w-4 h-4" style="color: var(--status-green);" />
          </div>
          <div v-if="retrainStatus.last_run.error" class="mt-2 text-xs" style="color: var(--status-red);">
            {{ retrainStatus.last_run.error }}
          </div>
        </div>
        <div v-else class="mb-4 p-3 rounded-lg text-center text-sm" style="background: var(--bg-elevated); border: 1px solid var(--border-primary); color: var(--text-tertiary);">
          No training runs yet
        </div>

        <!-- Retrain Controls -->
        <div class="flex items-center gap-3">
          <select v-model="retrainHours" class="input flex-1">
            <option :value="6">Last 6 hours</option>
            <option :value="12">Last 12 hours</option>
            <option :value="24">Last 24 hours</option>
            <option :value="48">Last 48 hours</option>
            <option :value="168">Last 7 days</option>
          </select>
          <button 
            @click="triggerRetrain"
            :disabled="retraining"
            class="btn-primary flex items-center gap-2"
          >
            <ArrowPathIcon class="w-4 h-4" :class="{ 'animate-spin': retraining }" />
            {{ retraining ? 'Training...' : 'Retrain Now' }}
          </button>
        </div>
      </div>

      <!-- Recommendations Section -->
      <div class="bento-card p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-medium" style="color: var(--text-primary);">
            AI Recommendations
          </h3>
          <button 
            @click="fetchRecommendations" 
            :disabled="loadingRecs"
            class="text-sm transition-colors cursor-pointer"
            style="color: var(--accent-400);"
          >
            {{ loadingRecs ? 'Loading...' : 'Refresh' }}
          </button>
        </div>
        
        <div v-if="recommendations.length > 0" class="space-y-3">
          <div
            v-for="(rec, idx) in recommendations"
            :key="idx"
            class="p-4 rounded-lg"
            style="background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.15);"
          >
            <div class="flex items-start gap-3">
              <LightBulbIcon class="w-5 h-5 flex-shrink-0 mt-0.5" style="color: var(--status-amber);" />
              <div class="flex-1">
                <p class="font-medium" style="color: var(--text-primary);">
                  {{ rec.workload }}
                </p>
                <div v-for="(action, aidx) in rec.actions" :key="aidx" class="mt-2 text-sm" style="color: var(--text-secondary);">
                  <p>{{ action.reason }}</p>
                  <p class="text-xs mt-1" style="color: var(--text-tertiary);">
                    {{ ((action.confidence ?? 0) * 100).toFixed(0) }}% confidence
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="flex flex-col items-center py-8 text-center">
          <CheckCircleIcon class="w-12 h-12 mb-3" style="color: var(--status-green);" />
          <p class="font-medium" style="color: var(--text-primary);">All systems optimal</p>
          <p class="text-sm mt-1" style="color: var(--text-tertiary);">No recommendations at this time</p>
        </div>
      </div>
    </template>
  </div>
</template>
