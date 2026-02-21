<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  title: string
  description: string
  actionLabel?: string
  icon?: Component
}>()

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="bento-card p-12 text-center">
    <component
      v-if="icon"
      :is="icon"
      class="w-12 h-12 mx-auto mb-4"
      style="color: var(--text-tertiary);"
    />
    <h3 class="text-lg font-medium mb-2" style="color: var(--text-primary);">{{ title }}</h3>
    <p class="mb-6 max-w-sm mx-auto" style="color: var(--text-tertiary);">{{ description }}</p>
    <button
      v-if="actionLabel"
      @click="emit('action')"
      class="btn-primary"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>
