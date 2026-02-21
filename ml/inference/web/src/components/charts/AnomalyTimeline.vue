<script setup lang="ts">
import { computed } from 'vue'

interface TimelineAnomaly {
  id: string
  metric: string
  agent?: string
  agentName?: string
  value: number | string
  unit?: string
  deviation: string
  severity: string
  time: string
  timestamp: number
}

const props = defineProps<{
  title?: string
  anomalies: TimelineAnomaly[]
  startTime: number
  endTime: number
}>()

const emit = defineEmits<{
  'click': [anomaly: TimelineAnomaly]
  'anomaly-click': [anomaly: TimelineAnomaly]
}>()

const timelineMarkers = computed(() => {
  const markers = []
  const duration = props.endTime - props.startTime
  for (let i = 0; i <= 4; i++) {
    const time = new Date(props.startTime + (duration / 4) * i)
    markers.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }))
  }
  return markers
})

function getPosition(timestamp: number) {
  const duration = props.endTime - props.startTime
  return ((timestamp - props.startTime) / duration) * 100
}

function getSeverityStyle(severity: string) {
  switch (severity) {
    case 'critical': return 'var(--status-red)'
    case 'high': return 'var(--status-amber)'
    case 'warning': return '#eab308'
    case 'medium': return '#eab308'
    case 'info': case 'low': return 'var(--status-blue)'
    default: return 'var(--text-tertiary)'
  }
}

function handleClick(anomaly: TimelineAnomaly) {
  emit('click', anomaly)
  emit('anomaly-click', anomaly)
}
</script>

<template>
  <div class="bento-card p-6">
    <h3 v-if="title" class="text-lg font-medium mb-4" style="color: var(--text-primary);">{{ title }}</h3>
    <h3 v-else class="text-lg font-medium mb-4" style="color: var(--text-primary);">Anomaly Timeline</h3>
    
    <div class="relative h-20 rounded-lg" style="background: var(--bg-elevated); border: 1px solid var(--border-primary);">
      <!-- Time markers -->
      <div class="absolute bottom-0 left-0 right-0 flex justify-between px-2 text-xs" style="color: var(--text-tertiary);">
        <span v-for="(marker, i) in timelineMarkers" :key="i">{{ marker }}</span>
      </div>
      
      <!-- Anomaly dots -->
      <div
        v-for="anomaly in anomalies"
        :key="anomaly.id"
        :style="{ left: `${getPosition(anomaly.timestamp)}%` }"
        class="absolute top-1/2 transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
        @click="handleClick(anomaly)"
      >
        <div 
          class="w-4 h-4 rounded-full"
          :style="`background: ${getSeverityStyle(anomaly.severity)};`"
        ></div>
        <div 
          class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10"
          style="background: var(--bg-elevated); color: var(--text-primary); border: 1px solid var(--border-primary);"
        >
          {{ anomaly.metric }}: {{ anomaly.value }}{{ anomaly.unit || '' }} ({{ anomaly.deviation }})
        </div>
      </div>
      
      <!-- Empty state -->
      <div v-if="anomalies.length === 0" class="absolute inset-0 flex items-center justify-center">
        <p class="text-sm" style="color: var(--text-tertiary);">No anomalies in this time range</p>
      </div>
    </div>
  </div>
</template>
