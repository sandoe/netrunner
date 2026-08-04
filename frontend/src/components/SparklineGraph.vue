<template>
  <div class="sparkline-wrapper">
    <svg viewBox="0 0 100 20" preserveAspectRatio="none" class="sparkline-svg">
      <defs>
        <filter :id="'glow-' + id">
          <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      <!-- Background grid lines -->
      <line x1="0" y1="10" x2="100" y2="10" stroke="rgba(255,255,255,0.1)" stroke-width="0.2" />
      <line x1="0" y1="5" x2="100" y2="5" stroke="rgba(255,255,255,0.05)" stroke-width="0.2" />
      <line x1="0" y1="15" x2="100" y2="15" stroke="rgba(255,255,255,0.05)" stroke-width="0.2" />

      <polyline
        :points="pointsString"
        fill="none"
        :stroke="color"
        stroke-width="0.8"
        :filter="'url(#glow-' + id + ')'"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: number[] // Array of values, typically 0-100
  color: string
}>()

// Generate unique ID for filter to avoid conflicts
const id = Math.random().toString(36).substring(2, 9)

const pointsString = computed(() => {
  if (!props.data || props.data.length === 0) return ''
  const len = props.data.length
  const maxVal = Math.max(...props.data, 100) // Assumes values are roughly 0-100 or scales to max

  return props.data.map((val, i) => {
    const x = (i / (len - 1)) * 100
    // Invert Y because SVG 0,0 is top-left
    const y = 20 - ((val / maxVal) * 20)
    return `${x},${y}`
  }).join(' ')
})
</script>

<style scoped>
.sparkline-wrapper {
  width: 100%;
  height: 100px;
  position: relative;
}

.sparkline-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
  /* Add subtle scroll animation */
  animation: scroll-pulse 2s infinite alternate;
}

@keyframes scroll-pulse {
  0% { opacity: 0.8; }
  100% { opacity: 1; }
}
</style>
