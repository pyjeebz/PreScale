<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useDeploymentsStore } from '@/stores/deployments'
import { ClipboardDocumentIcon, CheckIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const deploymentsStore = useDeploymentsStore()

const deploymentId = computed(() => 
  (route.query.deployment as string) || deploymentsStore.currentDeploymentId
)
const deployment = computed(() =>
  deploymentsStore.deployments.find(d => d.id === deploymentId.value)
)

const connectedAgents = ref(0)
const waitingForAgent = ref(true)
let pollInterval: ReturnType<typeof setInterval> | null = null

const copiedPip = ref(false)
const copiedStart = ref(false)

const heliosEndpoint = computed(() => {
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

import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">
        Install Helios Agent
      </h1>
      <p style="color: var(--text-tertiary);">
        Run this command on each server you want to monitor.
      </p>
    </div>

    <!-- Deployment Selector -->
    <div v-if="deploymentsStore.deployments.length > 1" class="mb-6">
      <label class="block text-sm font-medium mb-2" style="color: var(--text-secondary);">
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
    <div class="bento-card p-6 mb-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm" style="background: rgba(99, 102, 241, 0.1); color: var(--accent-400);">
          1
        </div>
        <h2 class="text-lg font-semibold" style="color: var(--text-primary);">Install the Agent</h2>
      </div>
      
      <div class="relative">
        <pre class="p-4 rounded-lg font-mono text-sm overflow-x-auto" style="background: var(--bg-code); color: #4ade80;">{{ installCommand }}</pre>
        <button
          @click="copyToClipboard(installCommand, 'pip')"
          class="absolute top-3 right-3 p-1.5 rounded transition-colors cursor-pointer"
          style="background: rgba(255,255,255,0.1); color: var(--text-tertiary);"
        >
          <CheckIcon v-if="copiedPip" class="w-4 h-4" style="color: var(--status-green);" />
          <ClipboardDocumentIcon v-else class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Step 2: Start -->
    <div class="bento-card p-6 mb-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm" style="background: rgba(99, 102, 241, 0.1); color: var(--accent-400);">
          2
        </div>
        <h2 class="text-lg font-semibold" style="color: var(--text-primary);">Start the Agent</h2>
      </div>
      
      <div class="relative mb-4">
        <pre class="p-4 rounded-lg font-mono text-sm overflow-x-auto whitespace-pre-wrap" style="background: var(--bg-code); color: #4ade80;">{{ startCommand }}</pre>
        <button
          @click="copyToClipboard(startCommand.replace(/\\\n\s*/g, ' '), 'start')"
          class="absolute top-3 right-3 p-1.5 rounded transition-colors cursor-pointer"
          style="background: rgba(255,255,255,0.1); color: var(--text-tertiary);"
        >
          <CheckIcon v-if="copiedStart" class="w-4 h-4" style="color: var(--status-green);" />
          <ClipboardDocumentIcon v-else class="w-4 h-4" />
        </button>
      </div>

      <details class="text-sm">
        <summary class="cursor-pointer transition-colors" style="color: var(--text-tertiary);">
          Or use environment variables
        </summary>
        <pre class="mt-3 p-4 rounded-lg font-mono text-sm overflow-x-auto whitespace-pre-wrap" style="background: var(--bg-code); color: #4ade80;">{{ envVarsCommand }}</pre>
      </details>
    </div>

    <!-- Status -->
    <div class="bento-card p-5">
      <div class="flex items-center gap-3">
        <template v-if="waitingForAgent">
          <ArrowPathIcon class="w-5 h-5 animate-spin" style="color: var(--text-tertiary);" />
          <span style="color: var(--text-tertiary);">Waiting for agents to connect...</span>
        </template>
        <template v-else>
          <div class="w-3 h-3 rounded-full status-pulse" style="background: var(--status-green);"></div>
          <span class="font-medium" style="color: var(--status-green);">
            {{ connectedAgents }} Agent{{ connectedAgents > 1 ? 's' : '' }} Connected!
          </span>
        </template>
      </div>

      <div v-if="!waitingForAgent" class="mt-4 pt-4 flex gap-3" style="border-top: 1px solid var(--border-primary);">
        <RouterLink to="/agents" class="btn-secondary text-sm">
          + Add More Agents
        </RouterLink>
        <RouterLink to="/" class="btn-primary text-sm">
          Go to Dashboard →
        </RouterLink>
      </div>
    </div>
  </div>
</template>
