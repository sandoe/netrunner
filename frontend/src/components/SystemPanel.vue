<template>
  <div class="system-panel" ref="containerRef">
    <div class="split-pane">
      <div class="pane pane-diag" :style="{ flexBasis: diagSize + '%', flexGrow: 0 }">
        <DiagPanel :node-id="nodeId" />
      </div>
      <div class="pane-divider" @mousedown="startDrag" @touchstart="startDrag"></div>
      <div class="pane pane-config">
        <ConfigPanel :node-id="nodeId" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import DiagPanel from './DiagPanel.vue'
import ConfigPanel from './ConfigPanel.vue'

defineProps<{
  nodeId: string
}>()

const containerRef = ref<HTMLElement | null>(null)
const diagSize = ref(35) // initial 35%
let isDragging = false

function startDrag(e: MouseEvent | TouchEvent) {
  e.preventDefault()
  isDragging = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchend', stopDrag)
  document.body.style.cursor = window.innerWidth >= 1200 ? 'col-resize' : 'row-resize'
  document.body.style.userSelect = 'none'
}

function onDrag(e: MouseEvent | TouchEvent) {
  if (!isDragging || !containerRef.value) return
  
  const container = containerRef.value.getBoundingClientRect()
  const isWide = window.innerWidth >= 1200
  
  let clientX, clientY
  if (e instanceof MouseEvent) {
    clientX = e.clientX
    clientY = e.clientY
  } else {
    clientX = e.touches[0].clientX
    clientY = e.touches[0].clientY
  }
  
  let newSize = 0
  if (isWide) {
    const delta = clientX - container.left
    newSize = (delta / container.width) * 100
  } else {
    const delta = clientY - container.top
    newSize = (delta / container.height) * 100
  }
  
  // Clamp between 10% and 90%
  if (newSize < 10) newSize = 10
  if (newSize > 90) newSize = 90
  
  diagSize.value = newSize
}

function stopDrag() {
  isDragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchend', stopDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

onUnmounted(() => {
  stopDrag()
})
</script>

<style scoped>
.system-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: var(--bg);
}

.split-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

@media (min-width: 1200px) {
  .split-pane {
    flex-direction: row;
  }
}

.pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 100px;
}

.pane-config {
  flex: 1;
}

.pane-divider {
  width: 100%;
  height: 8px;
  margin: -2px 0;
  background: var(--border);
  cursor: row-resize;
  z-index: 10;
  transition: background 0.2s;
}
.pane-divider:hover, .pane-divider:active {
  background: var(--accent);
}

@media (min-width: 1200px) {
  .pane-divider {
    width: 8px;
    height: 100%;
    margin: 0 -2px;
    cursor: col-resize;
  }
}
</style>
