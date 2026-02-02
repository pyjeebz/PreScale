<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

const version = '0.1.0'
</script>

<template>
  <div class="space-y-6 max-w-2xl">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">Settings</h1>
      <p class="text-slate-500 dark:text-slate-400">
        Configure your Helios preferences
      </p>
    </div>
    
    <!-- Appearance -->
    <div class="card p-6">
      <h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Appearance</h3>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Theme
          </label>
          <div class="flex gap-3">
            <button
              @click="themeStore.setTheme(false)"
              :class="[
                'flex-1 p-4 rounded-lg border-2 transition-colors',
                !themeStore.isDark
                  ? 'border-helios-500 bg-helios-50 dark:bg-helios-900/20'
                  : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
              ]"
            >
              <div class="w-full h-16 bg-white rounded border border-slate-200 mb-2"></div>
              <p class="text-sm font-medium text-slate-900 dark:text-white">Light</p>
            </button>
            
            <button
              @click="themeStore.setTheme(true)"
              :class="[
                'flex-1 p-4 rounded-lg border-2 transition-colors',
                themeStore.isDark
                  ? 'border-helios-500 bg-helios-50 dark:bg-helios-900/20'
                  : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
              ]"
            >
              <div class="w-full h-16 bg-slate-800 rounded border border-slate-700 mb-2"></div>
              <p class="text-sm font-medium text-slate-900 dark:text-white">Dark</p>
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Default Preferences -->
    <div class="card p-6">
      <h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Default Preferences</h3>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Default Time Range
          </label>
          <select class="input max-w-xs">
            <option>Last 1 hour</option>
            <option>Last 6 hours</option>
            <option selected>Last 24 hours</option>
            <option>Last 7 days</option>
            <option>Last 30 days</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Auto-refresh Interval
          </label>
          <select class="input max-w-xs">
            <option>Off</option>
            <option>10 seconds</option>
            <option selected>30 seconds</option>
            <option>1 minute</option>
            <option>5 minutes</option>
          </select>
        </div>
      </div>
    </div>
    
    <!-- About -->
    <div class="card p-6">
      <h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">About</h3>
      
      <div class="space-y-3">
        <div class="flex justify-between">
          <span class="text-sm text-slate-600 dark:text-slate-400">Version</span>
          <span class="text-sm font-medium text-slate-900 dark:text-white">{{ version }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-sm text-slate-600 dark:text-slate-400">License</span>
          <span class="text-sm font-medium text-slate-900 dark:text-white">MIT</span>
        </div>
        <div class="flex justify-between">
          <span class="text-sm text-slate-600 dark:text-slate-400">Repository</span>
          <a
            href="https://github.com/pyjeebz/helios"
            target="_blank"
            class="text-sm font-medium text-helios-600 dark:text-helios-400 hover:underline"
          >
            github.com/pyjeebz/helios
          </a>
        </div>
      </div>
      
      <div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Helios is an open-source ML-powered infrastructure forecasting platform.
          Built with ❤️ for the DevOps community.
        </p>
      </div>
    </div>
  </div>
</template>
