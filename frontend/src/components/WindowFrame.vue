<template>
  <div
    v-show="!win.isMinimized"
    class="window-frame glass-panel"
    :class="{ 'is-maximized': win.isMaximized, 'is-focused': isFocused }"
    :style="windowStyle"
    @mousedown="focus"
  >
    <!-- Window Title Bar -->
    <div class="window-header" ref="handle">
      <div class="window-title">
        <span class="window-icon">{{ win.icon }}</span>
        {{ win.title }}
      </div>
      <div class="window-controls">
        <button class="win-btn win-minimize" @click.stop="minimize">_</button>
        <button class="win-btn win-maximize" @click.stop="toggleMaximize">□</button>
        <button class="win-btn win-close" @click.stop="close">✕</button>
      </div>
    </div>

    <!-- Window Body -->
    <div class="window-body">
      <slot></slot>
    </div>

    <!-- Resize Handle -->
    <div v-if="!win.isMaximized" class="window-resize-handle" @mousedown.stop="startResize"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDraggable } from '@vueuse/core'
import { useWindowStore, type WindowState } from '../stores/windows'

const props = defineProps<{
  winId: string
}>()

const winStore = useWindowStore()
const win = computed(() => winStore.windows.find(w => w.id === props.winId) as WindowState)
const isFocused = computed(() => {
  if (!win.value) return false;
  return win.value.zIndex === winStore.nextZIndex - 1
})

const handle = ref<HTMLElement | null>(null)
const initialValue = ref({ x: win.value?.x || 100, y: win.value?.y || 100 })

const { x, y } = useDraggable(handle, {
  initialValue: initialValue.value,
  onMove: (position) => {
    if (!win.value.isMaximized) {
      winStore.updatePosition(props.winId, position.x, position.y)
    }
  }
})

// Sync back if external changes happen
watch(() => win.value?.x, (newX) => { if (newX !== undefined) x.value = newX })
watch(() => win.value?.y, (newY) => { if (newY !== undefined) y.value = newY })

const windowStyle = computed(() => {
  if (!win.value) return {}

  if (win.value.isMaximized) {
    return {
      top: '0px',
      left: '0px',
      width: '100vw',
      height: 'calc(100vh - 50px)', // Account for taskbar
      zIndex: win.value.zIndex,
      transform: 'none'
    }
  }

  return {
    top: `${win.value.y}px`,
    left: `${win.value.x}px`,
    width: `${win.value.width}px`,
    height: `${win.value.height}px`,
    zIndex: win.value.zIndex,
  }
})

const focus = () => winStore.focusWindow(props.winId)
const minimize = () => winStore.minimizeWindow(props.winId)
const toggleMaximize = () => winStore.toggleMaximize(props.winId)
const close = () => winStore.closeWindow(props.winId)

const isResizing = ref(false)
const startResizeState = ref({ x: 0, y: 0, w: 0, h: 0 })

const startResize = (e: MouseEvent) => {
  e.preventDefault()
  isResizing.value = true
  startResizeState.value = {
    x: e.clientX,
    y: e.clientY,
    w: win.value.width,
    h: win.value.height
  }
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  focus()
}

const onResize = (e: MouseEvent) => {
  if (!isResizing.value) return
  const dx = e.clientX - startResizeState.value.x
  const dy = e.clientY - startResizeState.value.y
  const newWidth = Math.max(300, startResizeState.value.w + dx)
  const newHeight = Math.max(200, startResizeState.value.h + dy)
  winStore.updateSize(props.winId, newWidth, newHeight)
}

const stopResize = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}
</script>

<style scoped>
.window-frame {
  position: absolute;
  display: flex;
  flex-direction: column;
  background: rgba(8, 13, 24, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  transition: opacity 0.2s, transform 0.1s, box-shadow 0.2s;
}

.window-frame.is-focused {
  border-color: rgba(0, 229, 255, 0.5);
  box-shadow: 0 10px 40px rgba(0, 229, 255, 0.15), 0 0 0 1px rgba(0, 229, 255, 0.2);
}

.window-frame.is-maximized {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
}

.window-header {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
  cursor: grab;
  user-select: none;
}
.window-header:active {
  cursor: grabbing;
}

.window-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--textwh);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.window-icon {
  font-size: 14px;
}

.window-controls {
  display: flex;
  gap: 6px;
}
.win-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.win-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--textwh);
}
.win-close:hover {
  background: rgba(255, 45, 110, 0.8);
  color: white;
}

.window-body {
  flex: 1;
  position: relative;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.window-resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 15px;
  height: 15px;
  cursor: nwse-resize;
  z-index: 100;
}

.window-resize-handle::after {
  content: '';
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 6px;
  height: 6px;
  border-right: 2px solid rgba(0, 229, 255, 0.4);
  border-bottom: 2px solid rgba(0, 229, 255, 0.4);
  border-radius: 1px;
}
</style>
