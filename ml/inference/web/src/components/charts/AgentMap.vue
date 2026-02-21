<script setup lang="ts">
import { GlobeAltIcon } from '@heroicons/vue/24/outline'

interface MapAgent {
  id: string
  hostname: string
  status: 'online' | 'warning' | 'offline'
  region: string
  location?: string
}

defineProps<{
  title: string
  agents: MapAgent[]
}>()

const regionCoords: Record<string, { x: number; y: number }> = {
  'us-east-1': { x: 25, y: 40 },
  'us-west-1': { x: 10, y: 40 },
  'us-west-2': { x: 12, y: 35 },
  'eu-west-1': { x: 48, y: 30 },
  'eu-central-1': { x: 52, y: 32 },
  'ap-southeast-1': { x: 75, y: 55 },
  'ap-northeast-1': { x: 85, y: 35 },
  default: { x: 50, y: 50 }
}

function getCoords(region: string) {
  return regionCoords[region] || regionCoords.default
}

function getStatusColor(status: string) {
  switch (status) {
    case 'online': return 'var(--status-green)'
    case 'warning': return 'var(--status-amber)'
    case 'offline': return 'var(--status-red)'
    default: return 'var(--text-tertiary)'
  }
}
</script>

<template>
  <div class="bento-card p-6">
    <div class="flex items-center gap-2 mb-4">
      <GlobeAltIcon class="w-5 h-5" style="color: var(--text-tertiary);" />
      <h3 class="text-lg font-medium" style="color: var(--text-primary);">{{ title }}</h3>
    </div>
    
    <div class="relative h-64 rounded-lg overflow-hidden" style="background: var(--bg-elevated); border: 1px solid var(--border-primary);">
      <!-- Simple world map outline -->
      <svg class="absolute inset-0 w-full h-full opacity-10" viewBox="0 0 100 60">
        <ellipse cx="50" cy="30" rx="45" ry="25" fill="none" stroke="currentColor" stroke-width="0.5" style="color: var(--text-tertiary);"/>
      </svg>
      
      <!-- Agent dots -->
      <div
        v-for="agent in agents"
        :key="agent.id"
        :style="{
          left: `${getCoords(agent.region).x}%`,
          top: `${getCoords(agent.region).y}%`
        }"
        class="absolute transform -translate-x-1/2 -translate-y-1/2 group"
      >
        <div 
          class="w-3 h-3 rounded-full animate-pulse"
          :style="`background: ${getStatusColor(agent.status)};`"
        ></div>
        <div 
          class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10"
          style="background: var(--bg-elevated); color: var(--text-primary); border: 1px solid var(--border-primary);"
        >
          {{ agent.hostname }} ({{ agent.region }})
        </div>
      </div>
      
      <!-- Empty state -->
      <div v-if="agents.length === 0" class="absolute inset-0 flex items-center justify-center">
        <p class="text-sm" style="color: var(--text-tertiary);">No agents to display</p>
      </div>
    </div>
    
    <!-- Legend -->
    <div class="flex items-center gap-4 mt-4 text-xs" style="color: var(--text-tertiary);">
      <div class="flex items-center gap-1">
        <div class="w-2 h-2 rounded-full" style="background: var(--status-green);"></div>
        <span>Online</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-2 h-2 rounded-full" style="background: var(--status-amber);"></div>
        <span>Warning</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-2 h-2 rounded-full" style="background: var(--status-red);"></div>
        <span>Offline</span>
      </div>
    </div>
  </div>
</template>
