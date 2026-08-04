<template>
  <canvas ref="canvas" class="matrix-canvas"></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  defconLevel: number
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
let animationId: number

onMounted(() => {
  const cvs = canvas.value
  if (!cvs) return
  const ctx = cvs.getContext('2d')
  if (!ctx) return

  // Make canvas full screen
  cvs.width = window.innerWidth
  cvs.height = window.innerHeight

  const hexCharacters = "0123456789ABCDEF!@#$%^&*()_+-=[]{}|;':,./<>?"
  const fontSize = 14
  const columns = cvs.width / fontSize

  const drops: number[] = []
  for (let x = 0; x < columns; x++) {
    drops[x] = Math.random() * -100 // Start at random negative offsets
  }

  const draw = () => {
    // Fill with semi-transparent black to create fade effect
    // Darker for higher DEFCON (1)
    const fadeAlpha = props.defconLevel === 1 ? 0.2 : 0.05
    ctx.fillStyle = `rgba(10, 15, 30, ${fadeAlpha})`
    ctx.fillRect(0, 0, cvs.width, cvs.height)

    // Determine color based on DEFCON
    let textColor = '#00f0ff' // DEFCON 5
    if (props.defconLevel === 3) textColor = '#ffaa00'
    if (props.defconLevel <= 2) textColor = '#ff3366'

    ctx.fillStyle = textColor
    ctx.font = `${fontSize}px 'Fira Code', monospace`

    for (let i = 0; i < drops.length; i++) {
      const text = hexCharacters.charAt(Math.floor(Math.random() * hexCharacters.length))
      ctx.fillText(text, i * fontSize, drops[i] * fontSize)

      if (drops[i] * fontSize > cvs.height && Math.random() > 0.975) {
        drops[i] = 0
      }
      drops[i]++
    }
    animationId = requestAnimationFrame(draw)
  }

  draw()

  const handleResize = () => {
    cvs.width = window.innerWidth
    cvs.height = window.innerHeight
    const newColumns = cvs.width / fontSize
    while (drops.length < newColumns) {
      drops.push(Math.random() * -100)
    }
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', () => {})
})
</script>

<style scoped>
.matrix-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  opacity: 0.15;
}
</style>
