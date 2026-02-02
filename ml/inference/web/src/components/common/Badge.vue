<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  variant?: 'success' | 'warning' | 'error' | 'info' | 'default'
  size?: 'sm' | 'md'
}>()

const classes = computed(() => {
  const variants = {
    success: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    error: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    default: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
  }
  
  const sizes = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1'
  }
  
  return [
    'inline-flex items-center font-medium rounded-full',
    variants[props.variant || 'default'],
    sizes[props.size || 'sm']
  ]
})
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
