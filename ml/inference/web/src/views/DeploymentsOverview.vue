<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useDeploymentsStore, type Deployment } from '@/stores/deployments'
import { PlusIcon, ServerStackIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/vue/24/outline'

const deploymentsStore = useDeploymentsStore()

const showCreateModal = ref(false)
const newDeployment = ref({
  name: '',
  description: '',
  environment: 'production' as 'development' | 'staging' | 'production'
})
const creating = ref(false)

function getEnvironmentStyle(env: string) {
  switch (env) {
    case 'production': return { color: 'var(--status-green)', bg: 'rgba(34, 197, 94, 0.1)' }
    case 'staging': return { color: 'var(--status-amber)', bg: 'rgba(245, 158, 11, 0.1)' }
    case 'development': return { color: 'var(--status-blue)', bg: 'rgba(59, 130, 246, 0.1)' }
    default: return { color: 'var(--text-tertiary)', bg: 'var(--bg-card)' }
  }
}

function getHealthStatus(dep: Deployment) {
  const ratio = dep.agents_online / Math.max(dep.agents_count, 1)
  if (ratio >= 0.9) return { label: 'Excellent', color: 'var(--status-green)' }
  if (ratio >= 0.5) return { label: 'Good', color: 'var(--status-amber)' }
  return { label: 'Degraded', color: 'var(--status-red)' }
}

async function createDeployment() {
  if (!newDeployment.value.name.trim()) return
  
  creating.value = true
  try {
    await deploymentsStore.createDeployment({
      name: newDeployment.value.name.trim(),
      description: newDeployment.value.description.trim(),
      environment: newDeployment.value.environment
    })
    showCreateModal.value = false
    newDeployment.value = { name: '', description: '', environment: 'production' }
  } catch (e) {
    console.error('Failed to create deployment:', e)
  } finally {
    creating.value = false
  }
}

function selectDeployment(dep: Deployment) {
  deploymentsStore.setCurrentDeployment(dep.id)
}

onMounted(() => {
  deploymentsStore.fetchDeployments()
})
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold" style="color: var(--text-primary);">Deployments</h1>
        <p class="mt-1" style="color: var(--text-tertiary);">Manage your monitored environments</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary flex items-center gap-2">
        <PlusIcon class="w-5 h-5" />
        Add Deployment
      </button>
    </div>

    <!-- Deployments Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="dep in deploymentsStore.deployments"
        :key="dep.id"
        class="bento-card p-5 cursor-pointer transition-all"
        :style="deploymentsStore.currentDeploymentId === dep.id 
          ? 'border-color: var(--accent-500); box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);' 
          : ''"
        @click="selectDeployment(dep)"
      >
        <!-- Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div 
              class="w-3 h-3 rounded-full"
              :style="dep.agents_online > 0 ? 'background: var(--status-green);' : 'background: var(--text-tertiary);'"
            ></div>
            <h3 class="font-semibold" style="color: var(--text-primary);">{{ dep.name }}</h3>
          </div>
          <span 
            class="px-2 py-0.5 rounded text-xs font-medium"
            :style="`background: ${getEnvironmentStyle(dep.environment).bg}; color: ${getEnvironmentStyle(dep.environment).color};`"
          >
            {{ dep.environment }}
          </span>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-4 mb-4">
          <div>
            <div class="text-2xl font-bold" style="color: var(--text-primary);">{{ dep.agents_online }}</div>
            <div class="text-xs" style="color: var(--text-tertiary);">Agents Online</div>
          </div>
          <div>
            <div class="text-2xl font-bold" style="color: var(--text-primary);">0</div>
            <div class="text-xs" style="color: var(--text-tertiary);">Anomalies</div>
          </div>
          <div>
            <div class="text-sm font-medium" :style="`color: ${getHealthStatus(dep).color};`">
              {{ getHealthStatus(dep).label }}
            </div>
            <div class="text-xs" style="color: var(--text-tertiary);">Health</div>
          </div>
        </div>

        <!-- Actions -->
        <div class="pt-4" style="border-top: 1px solid var(--border-primary);">
          <RouterLink
            :to="{ path: '/', query: { deployment: dep.id } }"
            class="text-sm transition-colors"
            style="color: var(--accent-400);"
            @click.stop
          >
            View Dashboard →
          </RouterLink>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-if="deploymentsStore.deployments.length === 0 && !deploymentsStore.loading"
        class="col-span-full flex flex-col items-center justify-center py-12 text-center"
      >
        <ServerStackIcon class="w-12 h-12 mb-4" style="color: var(--text-tertiary);" />
        <h3 class="text-lg font-medium mb-2" style="color: var(--text-primary);">No deployments yet</h3>
        <p class="mb-4" style="color: var(--text-tertiary);">Create your first deployment to start monitoring.</p>
        <button @click="showCreateModal = true" class="btn-primary flex items-center gap-2">
          <PlusIcon class="w-5 h-5" />
          Create Deployment
        </button>
      </div>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="showCreateModal = false"></div>
        <div class="relative rounded-xl shadow-xl p-6 w-full max-w-md m-4" style="background: var(--bg-elevated); border: 1px solid var(--border-primary);">
          <h2 class="text-xl font-bold mb-4" style="color: var(--text-primary);">Create Deployment</h2>
          
          <form @submit.prevent="createDeployment" class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-1" style="color: var(--text-secondary);">
                Deployment Name
              </label>
              <input
                v-model="newDeployment.name"
                type="text"
                placeholder="e.g., ecommerce-prod"
                class="input w-full"
                required
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-1" style="color: var(--text-secondary);">
                Description (optional)
              </label>
              <input
                v-model="newDeployment.description"
                type="text"
                placeholder="Production e-commerce platform on GKE"
                class="input w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-2" style="color: var(--text-secondary);">
                Environment
              </label>
              <div class="flex gap-4">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input v-model="newDeployment.environment" type="radio" value="development" class="accent-indigo-500" />
                  <span class="text-sm" style="color: var(--text-secondary);">Development</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input v-model="newDeployment.environment" type="radio" value="staging" class="accent-indigo-500" />
                  <span class="text-sm" style="color: var(--text-secondary);">Staging</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input v-model="newDeployment.environment" type="radio" value="production" class="accent-indigo-500" />
                  <span class="text-sm" style="color: var(--text-secondary);">Production</span>
                </label>
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button type="button" @click="showCreateModal = false" class="btn-secondary">
                Cancel
              </button>
              <button type="submit" class="btn-primary" :disabled="creating">
                {{ creating ? 'Creating...' : 'Create Deployment' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>
