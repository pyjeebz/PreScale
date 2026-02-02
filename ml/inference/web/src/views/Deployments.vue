<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { CubeIcon, PlusIcon } from '@heroicons/vue/24/outline'
import { useDeploymentsStore, type Deployment } from '@/stores/deployments'
import EmptyState from '@/components/common/EmptyState.vue'
import Badge from '@/components/common/Badge.vue'
import Modal from '@/components/common/Modal.vue'

const deploymentsStore = useDeploymentsStore()

const showCreateModal = ref(false)
const newDeployment = ref({
  name: '',
  description: '',
  environment: 'development' as const
})

const environmentOptions = [
  { value: 'development', label: 'Development', color: 'info' },
  { value: 'staging', label: 'Staging', color: 'warning' },
  { value: 'production', label: 'Production', color: 'success' }
]

async function createDeployment() {
  try {
    await deploymentsStore.createDeployment(newDeployment.value)
    showCreateModal.value = false
    newDeployment.value = { name: '', description: '', environment: 'development' }
  } catch (e) {
    console.error('Failed to create deployment:', e)
  }
}

function getEnvironmentBadge(env: string) {
  switch (env) {
    case 'production':
      return 'success'
    case 'staging':
      return 'warning'
    default:
      return 'info'
  }
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

onMounted(() => {
  deploymentsStore.fetchDeployments()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">Deployments</h1>
        <p class="text-slate-500 dark:text-slate-400">
          Manage your deployment environments
        </p>
      </div>
      
      <button @click="showCreateModal = true" class="btn-primary flex items-center gap-2">
        <PlusIcon class="w-5 h-5" />
        New Deployment
      </button>
    </div>
    
    <!-- Empty State -->
    <EmptyState
      v-if="deploymentsStore.deployments.length === 0"
      title="No deployments yet"
      description="Create your first deployment to start monitoring your infrastructure."
      action-label="Create Deployment"
      :icon="CubeIcon"
      @action="showCreateModal = true"
    />
    
    <!-- Deployments Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="deployment in deploymentsStore.deployments"
        :key="deployment.id"
        :class="[
          'card p-6 cursor-pointer hover:border-helios-300 dark:hover:border-helios-700 transition-colors',
          deployment.id === deploymentsStore.currentDeploymentId ? 'ring-2 ring-helios-500' : ''
        ]"
        @click="deploymentsStore.setCurrentDeployment(deployment.id)"
      >
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-helios-100 dark:bg-helios-900/30 flex items-center justify-center">
              <CubeIcon class="w-5 h-5 text-helios-600 dark:text-helios-400" />
            </div>
            <div>
              <h3 class="font-medium text-slate-900 dark:text-white">{{ deployment.name }}</h3>
              <Badge :variant="getEnvironmentBadge(deployment.environment)" size="sm">
                {{ deployment.environment }}
              </Badge>
            </div>
          </div>
        </div>
        
        <p v-if="deployment.description" class="text-sm text-slate-500 dark:text-slate-400 mb-4">
          {{ deployment.description }}
        </p>
        
        <div class="grid grid-cols-2 gap-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">Agents</p>
            <p class="text-lg font-semibold text-slate-900 dark:text-white">
              {{ deployment.agents_online }} / {{ deployment.agents_count }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">Created</p>
            <p class="text-sm text-slate-900 dark:text-white">
              {{ formatDate(deployment.created_at) }}
            </p>
          </div>
        </div>
      </div>
      
      <!-- Add New Card -->
      <div
        class="card p-6 border-dashed cursor-pointer hover:border-helios-300 dark:hover:border-helios-700 transition-colors flex flex-col items-center justify-center text-center"
        @click="showCreateModal = true"
      >
        <div class="w-12 h-12 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center mb-3">
          <PlusIcon class="w-6 h-6 text-slate-400" />
        </div>
        <p class="text-sm font-medium text-slate-600 dark:text-slate-300">Create New Deployment</p>
      </div>
    </div>
    
    <!-- Create Deployment Modal -->
    <Modal :open="showCreateModal" title="Create Deployment" @close="showCreateModal = false">
      <form @submit.prevent="createDeployment" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Deployment Name
          </label>
          <input
            v-model="newDeployment.name"
            type="text"
            class="input"
            placeholder="e.g., ecommerce-prod"
            required
          />
          <p class="mt-1 text-xs text-slate-500">Only lowercase letters, numbers, and hyphens</p>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Description
          </label>
          <input
            v-model="newDeployment.description"
            type="text"
            class="input"
            placeholder="e.g., Production e-commerce platform"
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Environment
          </label>
          <div class="flex gap-2">
            <button
              v-for="env in environmentOptions"
              :key="env.value"
              type="button"
              @click="newDeployment.environment = env.value as any"
              :class="[
                'flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-colors',
                newDeployment.environment === env.value
                  ? 'border-helios-500 bg-helios-50 dark:bg-helios-900/20 text-helios-700 dark:text-helios-300'
                  : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500'
              ]"
            >
              {{ env.label }}
            </button>
          </div>
        </div>
        
        <div class="flex justify-end gap-3 pt-4">
          <button type="button" @click="showCreateModal = false" class="btn-secondary">
            Cancel
          </button>
          <button type="submit" class="btn-primary">
            Create Deployment
          </button>
        </div>
      </form>
    </Modal>
  </div>
</template>
