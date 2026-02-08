<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useDeploymentsStore } from '@/stores/deployments'
import { ClipboardDocumentIcon, CheckIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const deploymentsStore = useDeploymentsStore()

// Get deployment from route or current selection
const deploymentId = computed(() => 
  (route.query.deployment as string) || deploymentsStore.currentDeploymentId
)
const deployment = computed(() =>
  deploymentsStore.deployments.find(d => d.id === deploymentId.value)
)

// Agent connection status
const connectedAgents = ref(0)
const waitingForAgent = ref(true)
let pollInterval: ReturnType<typeof setInterval> | null = null

// Copy button states
const copiedPip = ref(false)
const copiedStart = ref(false)

const heliosEndpoint = computed(() => {
  // Backend API runs on port 8080
  const origin = window.location.origin
  return origin.replace(':3000', ':8080')
})

const installCommand = 'pip install helios-agent'

const startCommand = computed(() => {
  const depName = deployment.value?.name || 'my-deployment'
  return `helios-agent run \\
  --deployment ${depName} \\
  --endpoint ${heliosEndpoint.value}`
})

const envVarsCommand = computed(() => {
  const depName = deployment.value?.name || 'my-deployment'
  return `export HELIOS_DEPLOYMENT=${depName}
export HELIOS_ENDPOINT=${heliosEndpoint.value}
helios-agent run`
})

async function copyToClipboard(text: string, type: 'pip' | 'start') {
  await navigator.clipboard.writeText(text)
  if (type === 'pip') {
    copiedPip.value = true
    setTimeout(() => copiedPip.value = false, 2000)
  } else {
    copiedStart.value = true
    setTimeout(() => copiedStart.value = false, 2000)
  }
}

async function checkAgents() {
  if (!deploymentId.value) return
  
  try {
    const response = await fetch(`/api/v1/deployments/${deploymentId.value}/agents`)
    if (response.ok) {
      const agents = await response.json()
      const online = agents.filter((a: any) => a.status === 'online').length
      if (online > connectedAgents.value) {
        connectedAgents.value = online
        waitingForAgent.value = false
      }
    }
  } catch (e) {
    console.error('Failed to check agents:', e)
  }
}

onMounted(() => {
  deploymentsStore.fetchDeployments()
  pollInterval = setInterval(checkAgents, 3000)
  checkAgents()
})

// Cleanup on unmount
import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">
        Install Helios Agent
      </h1>
      <p class="text-slate-600 dark:text-slate-400">
        Run this command on each server you want to monitor.
      </p>
    </div>

    <!-- Deployment Selector -->
    <div v-if="deploymentsStore.deployments.length > 1" class="mb-6">
      <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
        Deployment
      </label>
      <select
        :value="deploymentId"
        @change="deploymentsStore.setCurrentDeployment(($event.target as HTMLSelectElement).value)"
        class="input w-full max-w-xs"
      >
        <option
          v-for="dep in deploymentsStore.deployments"
          :key="dep.id"
          :value="dep.id"
        >
          {{ dep.name }}
        </option>
      </select>
    </div>

    <!-- Step 1: Install -->
    <div class="card mb-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-full bg-helios-100 dark:bg-helios-900/30 flex items-center justify-center text-helios-600 dark:text-helios-400 font-semibold text-sm">
          1
        </div>
        <h2 class="text-lg font-semibold text-slate-900 dark:text-white">Install the Agent</h2>
      </div>
      
      <div class="relative">
        <pre class="bg-slate-900 dark:bg-slate-950 text-green-400 p-4 rounded-lg font-mono text-sm overflow-x-auto">{{ installCommand }}</pre>
        <button
          @click="copyToClipboard(installCommand, 'pip')"
          class="absolute top-3 right-3 p-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
        >
          <CheckIcon v-if="copiedPip" class="w-4 h-4 text-green-400" />
          <ClipboardDocumentIcon v-else class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Step 2: Start -->
    <div class="card mb-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-full bg-helios-100 dark:bg-helios-900/30 flex items-center justify-center text-helios-600 dark:text-helios-400 font-semibold text-sm">
          2
        </div>
        <h2 class="text-lg font-semibold text-slate-900 dark:text-white">Start the Agent</h2>
      </div>
      
      <div class="relative mb-4">
        <pre class="bg-slate-900 dark:bg-slate-950 text-green-400 p-4 rounded-lg font-mono text-sm overflow-x-auto whitespace-pre-wrap">{{ startCommand }}</pre>
        <button
          @click="copyToClipboard(startCommand.replace(/\\\n\s*/g, ' '), 'start')"
          class="absolute top-3 right-3 p-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
        >
          <CheckIcon v-if="copiedStart" class="w-4 h-4 text-green-400" />
          <ClipboardDocumentIcon v-else class="w-4 h-4" />
        </button>
      </div>

      <details class="text-sm">
        <summary class="text-slate-500 dark:text-slate-400 cursor-pointer hover:text-slate-700 dark:hover:text-slate-300">
          Or use environment variables
        </summary>
        <pre class="mt-3 bg-slate-900 dark:bg-slate-950 text-green-400 p-4 rounded-lg font-mono text-sm overflow-x-auto whitespace-pre-wrap">{{ envVarsCommand }}</pre>
      </details>
    </div>

    <!-- Status -->
    <div class="card">
      <div class="flex items-center gap-3">
        <template v-if="waitingForAgent">
          <ArrowPathIcon class="w-5 h-5 text-slate-400 animate-spin" />
          <span class="text-slate-600 dark:text-slate-400">Waiting for agents to connect...</span>
        </template>
        <template v-else>
          <div class="w-3 h-3 rounded-full bg-green-500"></div>
          <span class="text-green-600 dark:text-green-400 font-medium">
            {{ connectedAgents }} Agent{{ connectedAgents > 1 ? 's' : '' }} Connected!
          </span>
        </template>
      </div>

      <div v-if="!waitingForAgent" class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 flex gap-3">
        <RouterLink to="/agents" class="btn btn-secondary text-sm">
          + Add More Agents
        </RouterLink>
        <RouterLink to="/" class="btn btn-primary text-sm">
          Go to Dashboard →
        </RouterLink>
      </div>
    </div>
  </div>
</template>
