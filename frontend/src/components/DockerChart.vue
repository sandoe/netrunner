<template>
  <div class="metrics-chart">
    <Line v-if="chartData.labels.length" :data="chartData" :options="chartOptions" />
    <div v-else class="chart-loading">Waiting for telemetry data...</div>
  </div>
</template>

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
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps<{
  title: string
  datasets: { label: string; color: string; dataPoints: { time: number; value: number }[] }[]
}>()

const chartData = computed(() => {
  // Use labels from the first dataset (assuming they all share the same poll cycle)
  const labels = (props.datasets[0]?.dataPoints || []).map(p => {
    const d = new Date(p.time * 1000)
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
  })

  return {
    labels,
    datasets: props.datasets.map(ds => ({
      label: ds.label,
      data: ds.dataPoints.map(p => p.value),
      borderColor: ds.color,
      backgroundColor: ds.color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      fill: true,
      tension: 0.4
    }))
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 0
  },
  plugins: {
    legend: {
      display: true,
      labels: {
        color: '#e0e0e0',
        font: { size: 10 }
      }
    },
    tooltip: {
      mode: 'index',
      intersect: false,
      backgroundColor: 'rgba(5, 8, 15, 0.9)',
      titleColor: '#00ff9d',
      bodyColor: '#e0e0e0',
      borderWidth: 1
    }
  },
  scales: {
    x: {
      grid: {
        color: 'rgba(255, 255, 255, 0.05)'
      },
      ticks: {
        color: '#888',
        maxTicksLimit: 5
      }
    },
    y: {
      grid: {
        color: 'rgba(255, 255, 255, 0.05)'
      },
      ticks: {
        color: '#888'
      },
      beginAtZero: true
    }
  }
}
</script>

<style scoped>
.metrics-chart {
  position: relative;
  height: 100%;
  width: 100%;
  min-height: 150px;
}
.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
  font-family: var(--font-co);
  font-size: 12px;
}
</style>
