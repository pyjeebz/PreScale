<script setup lang="ts">
defineProps<{
  size?: 'sm' | 'md' | 'lg'
}>()
</script>

<template>
  <div class="flex items-center justify-center">
    <div
      :class="[
        'animate-spin rounded-full border-2 border-slate-200 dark:border-slate-700 border-t-helios-500',
        size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-10 h-10' : 'w-6 h-6'
      ]"
    ></div>
  </div>
</template>
