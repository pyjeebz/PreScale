<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import EmptyState from '@/components/common/EmptyState.vue'
import Badge from '@/components/common/Badge.vue'
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">Anomalies</h1>
        <p class="text-slate-500 dark:text-slate-400">
          Detected anomalies in your infrastructure metrics
        </p>
      </div>
      
      <div class="flex items-center gap-2">
        <select class="input w-40">
          <option>All Severities</option>
          <option>Critical</option>
          <option>Warning</option>
          <option>Info</option>
        </select>
        <select class="input w-40">
          <option>Last 24 hours</option>
          <option>Last 7 days</option>
          <option>Last 30 days</option>
        </select>
      </div>
    </div>
    
    <!-- Empty State -->
    <EmptyState
      title="No anomalies detected"
      description="Great news! No anomalies have been detected in your infrastructure. We'll alert you when something unusual is found."
      :icon="ExclamationTriangleIcon"
    />
    
    <!-- Anomalies Table (hidden when empty) -->
    <div class="card hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-slate-50 dark:bg-slate-900">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Severity
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Agent
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Metric
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Expected
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Actual
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Time
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
            <!-- Example row -->
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-900/50">
              <td class="px-6 py-4 whitespace-nowrap">
                <Badge variant="error">Critical</Badge>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-white">
                api-node
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                memory_utilization
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                45-55%
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-red-600 dark:text-red-400">
                92%
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                2 hours ago
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <Badge variant="warning">Active</Badge>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
