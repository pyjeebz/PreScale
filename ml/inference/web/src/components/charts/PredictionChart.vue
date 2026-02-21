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
  subtitle?: string
  historicalData: number[]
  forecastData: number[]
  upperBound: number[]
  lowerBound: number[]
  labels: string[]
  prediction?: {
    peakValue: number
    peakTime: string
    confidence: number
    horizon: string
  } | null
}>()

const chartData = computed(() => {
  const historicalLen = props.historicalData.length
  
  const fullForecast = [...Array(historicalLen - 1).fill(null), 
    props.historicalData[historicalLen - 1],
    ...props.forecastData
  ]
  const fullUpper = [...Array(historicalLen - 1).fill(null),
    props.historicalData[historicalLen - 1],
    ...props.upperBound
  ]
  const fullLower = [...Array(historicalLen - 1).fill(null),
    props.historicalData[historicalLen - 1],
    ...props.lowerBound
  ]

  return {
    labels: props.labels,
    datasets: [
      {
        label: 'Historical',
        data: [...props.historicalData, ...Array(props.forecastData.length).fill(null)],
        borderColor: '#6366f1',
        backgroundColor: 'transparent',
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4
      },
      {
        label: 'Forecast',
        data: fullForecast,
        borderColor: '#a78bfa',
        borderDash: [5, 5],
        backgroundColor: 'transparent',
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4
      },
      {
        label: 'Upper Bound',
        data: fullUpper,
        borderColor: 'rgba(139, 92, 246, 0.2)',
        backgroundColor: 'rgba(139, 92, 246, 0.05)',
        fill: '+1',
        tension: 0.4,
        pointRadius: 0
      },
      {
        label: 'Lower Bound',
        data: fullLower,
        borderColor: 'rgba(139, 92, 246, 0.2)',
        backgroundColor: 'transparent',
        tension: 0.4,
        pointRadius: 0
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
      labels: {
        color: '#737373',
        font: { size: 11 },
        filter: (item: any) => item.text !== 'Upper Bound' && item.text !== 'Lower Bound'
      }
    },
    tooltip: {
      backgroundColor: '#111111',
      borderColor: 'rgba(255, 255, 255, 0.06)',
      borderWidth: 1,
      titleColor: '#ffffff',
      bodyColor: '#a3a3a3',
      callbacks: {
        label: (ctx: any) => ctx.parsed.y !== null ? `${ctx.parsed.y.toFixed(1)}%` : ''
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxTicksLimit: 10, color: '#525252' },
      border: { color: 'rgba(255, 255, 255, 0.06)' }
    },
    y: {
      grid: { color: 'rgba(255, 255, 255, 0.04)' },
      ticks: {
        callback: (val: number) => `${val}%`,
        color: '#525252'
      },
      border: { color: 'rgba(255, 255, 255, 0.06)' }
    }
  }
}
</script>

<template>
  <div class="bento-card p-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-medium" style="color: var(--text-primary);">{{ title }}</h3>
        <p v-if="subtitle" class="text-sm" style="color: var(--text-tertiary);">{{ subtitle }}</p>
      </div>
      <div v-if="prediction" class="text-right">
        <span class="text-sm" style="color: var(--text-tertiary);">Confidence: </span>
        <span class="text-sm font-medium" style="color: var(--status-green);">{{ (prediction.confidence * 100).toFixed(0) }}%</span>
      </div>
    </div>
    <div class="h-80">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>
