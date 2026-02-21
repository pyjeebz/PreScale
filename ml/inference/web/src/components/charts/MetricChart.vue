<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend
)

const props = defineProps<{
  title: string
  data: number[]
  labels: string[]
  unit?: string
  color?: string
  filled?: boolean
}>()

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      label: props.title,
      data: props.data,
      borderColor: props.color || '#6366f1',
      backgroundColor: props.filled 
        ? (props.color || '#6366f1') + '15' 
        : 'transparent',
      fill: props.filled || false,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4
    }
  ]
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#111111',
      borderColor: 'rgba(255, 255, 255, 0.06)',
      borderWidth: 1,
      titleColor: '#ffffff',
      bodyColor: '#a3a3a3',
      callbacks: {
        label: (ctx: any) => `${ctx.parsed.y.toFixed(1)}${props.unit || ''}`
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxTicksLimit: 8, color: '#525252' },
      border: { color: 'rgba(255, 255, 255, 0.06)' }
    },
    y: {
      grid: { color: 'rgba(255, 255, 255, 0.04)' },
      ticks: {
        callback: (val: number) => `${val}${props.unit || ''}`,
        color: '#525252'
      },
      border: { color: 'rgba(255, 255, 255, 0.06)' }
    }
  }
}))
</script>

<template>
  <div class="bento-card p-6">
    <h3 class="text-lg font-medium mb-4" style="color: var(--text-primary);">{{ title }}</h3>
    <div class="h-64">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>
