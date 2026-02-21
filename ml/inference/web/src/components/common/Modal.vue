<script setup lang="ts">
import { TransitionRoot, TransitionChild, Dialog, DialogPanel, DialogTitle } from '@headlessui/vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'

defineProps<{
  open: boolean
  title: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}>()

const emit = defineEmits<{
  close: []
}>()

const sizeClasses: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
}
</script>

<template>
  <TransitionRoot appear :show="open" as="template">
    <Dialog as="div" class="relative z-50" @close="emit('close')">
      <TransitionChild
        as="template"
        enter="duration-300 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-200 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4">
          <TransitionChild
            as="template"
            enter="duration-300 ease-out"
            enter-from="opacity-0 scale-95"
            enter-to="opacity-100 scale-100"
            leave="duration-200 ease-in"
            leave-from="opacity-100 scale-100"
            leave-to="opacity-0 scale-95"
          >
            <DialogPanel
              :class="['w-full transform overflow-hidden rounded-xl p-6 shadow-xl transition-all', sizeClasses[size || 'md']]"
              style="background: var(--bg-elevated); border: 1px solid var(--border-primary);"
            >
              <div class="flex items-center justify-between mb-4">
                <DialogTitle class="text-lg font-semibold" style="color: var(--text-primary);">
                  {{ title }}
                </DialogTitle>
                <button
                  @click="emit('close')"
                  class="transition-colors"
                  style="color: var(--text-tertiary);"
                >
                  <XMarkIcon class="w-5 h-5" />
                </button>
              </div>
              <slot />
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
