<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  icon?: any
  actionLabel?: string
}>()

defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="card p-8 text-center">
    <div v-if="icon" class="mx-auto w-12 h-12 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center mb-4">
      <component :is="icon" class="w-6 h-6 text-slate-400" />
    </div>
    <h3 class="text-lg font-medium text-slate-900 dark:text-white">{{ title }}</h3>
    <p v-if="description" class="mt-2 text-sm text-slate-500 dark:text-slate-400">{{ description }}</p>
    <button
      v-if="actionLabel"
      @click="$emit('action')"
      class="mt-4 btn-primary"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>
