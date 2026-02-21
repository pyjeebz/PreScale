<script setup lang="ts">
defineProps<{
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
}>()

const variantStyles = {
  default: { bg: 'var(--bg-card)', color: 'var(--text-secondary)' },
  success: { bg: 'rgba(34, 197, 94, 0.1)', color: 'var(--status-green)' },
  warning: { bg: 'rgba(245, 158, 11, 0.1)', color: 'var(--status-amber)' },
  error: { bg: 'rgba(239, 68, 68, 0.1)', color: 'var(--status-red)' },
  info: { bg: 'rgba(59, 130, 246, 0.1)', color: 'var(--status-blue)' },
}
</script>

<template>
  <span
    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    :style="`background: ${variantStyles[variant || 'default'].bg}; color: ${variantStyles[variant || 'default'].color};`"
  >
    <slot />
  </span>
</template>
