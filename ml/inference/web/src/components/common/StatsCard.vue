<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  value: string | number
  subtitle?: string
  icon?: any
  trend?: 'up' | 'down' | 'stable'
  trendValue?: string
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'slate'
}>()

const colorClasses = computed(() => {
  const colors = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    slate: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
  }
  return colors[props.color || 'blue']
})

const trendColorClasses = computed(() => {
  if (!props.trend) return ''
  const colors = {
    up: 'text-green-600 dark:text-green-400',
    down: 'text-red-600 dark:text-red-400',
    stable: 'text-slate-600 dark:text-slate-400'
  }
  return colors[props.trend]
})

const trendIcon = computed(() => {
  if (!props.trend) return ''
  const icons = {
    up: '↑',
    down: '↓',
    stable: '→'
  }
  return icons[props.trend]
})
</script>

<template>
  <div class="card p-6">
    <div class="flex items-start justify-between">
      <div class="flex-1">
        <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ title }}</p>
        <div class="mt-2 flex items-baseline gap-2">
          <p class="text-3xl font-semibold text-slate-900 dark:text-white">{{ value }}</p>
          <span v-if="trend && trendValue" :class="['text-sm font-medium', trendColorClasses]">
            {{ trendIcon }} {{ trendValue }}
          </span>
        </div>
        <p v-if="subtitle" class="mt-1 text-sm text-slate-500 dark:text-slate-400">{{ subtitle }}</p>
      </div>
      <div v-if="icon" :class="['p-3 rounded-xl', colorClasses]">
        <component :is="icon" class="w-6 h-6" />
      </div>
    </div>
  </div>
</template>
