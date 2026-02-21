<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  title: string
  value: string | number
  subtitle?: string
  icon?: Component
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'slate'
}>()

const colorStyles: Record<string, { bg: string; icon: string }> = {
  blue: { bg: 'rgba(59, 130, 246, 0.1)', icon: 'var(--status-blue)' },
  green: { bg: 'rgba(34, 197, 94, 0.1)', icon: 'var(--status-green)' },
  yellow: { bg: 'rgba(245, 158, 11, 0.1)', icon: 'var(--status-amber)' },
  red: { bg: 'rgba(239, 68, 68, 0.1)', icon: 'var(--status-red)' },
  slate: { bg: 'var(--bg-card)', icon: 'var(--text-tertiary)' },
}
</script>

<template>
  <div class="bento-card p-6">
    <div class="flex items-center gap-4">
      <div
        class="w-12 h-12 rounded-xl flex items-center justify-center"
        :style="`background: ${colorStyles[color || 'blue'].bg};`"
      >
        <component
          v-if="icon"
          :is="icon"
          class="w-6 h-6"
          :style="`color: ${colorStyles[color || 'blue'].icon};`"
        />
      </div>
      <div>
        <p class="text-sm" style="color: var(--text-tertiary);">{{ title }}</p>
        <p class="text-2xl font-semibold" style="color: var(--text-primary);">{{ value }}</p>
        <p v-if="subtitle" class="text-sm" style="color: var(--text-tertiary);">{{ subtitle }}</p>
      </div>
    </div>
  </div>
</template>
