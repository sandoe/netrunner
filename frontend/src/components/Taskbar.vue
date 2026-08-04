<template>
  <footer class="taskbar">
    <div class="taskbar-left">
      <button class="start-btn" :class="{ active: startMenuOpen }" @click="$emit('toggle-start')" title="Start Menu">
        <span class="logo-text">NETRUNNER</span>
      </button>

      <!-- Open Windows Tasks -->
      <div class="task-list">
        <button
          v-for="win in windowStore.windows"
          :key="win.id"
          class="task-item"
          :class="{ active: win.zIndex === windowStore.nextZIndex - 1 && !win.isMinimized }"
          @click="toggleWindow(win.id)"
        >
          <span class="task-icon">{{ win.icon }}</span>
          <span class="task-title">{{ win.title }}</span>
        </button>
      </div>
    </div>

    <!-- System Tray (formerly Topbar status) -->
    <div class="system-tray">
      <div class="mode-toggle-wrap" title="Toggle Simulation/Live Mode">
        <button
          class="mode-toggle-btn"
          :class="{ 'sim-active': nodeStore.simulationMode }"
          @click="nodeStore.toggleSimulationMode()"
        >
          {{ nodeStore.simulationMode ? 'SIMULATION MODE' : 'LIVE OPS' }}
        </button>
      </div>

      <div class="tray-leds">
        <span title="Frontend UI" class="tray-led-wrap">
          UI <span class="api-led up"></span>
        </span>
        <span :title="'Backend API: ' + backendApiStatus" class="tray-led-wrap">
          API <span class="api-led" :class="backendApiStatus"></span>
        </span>
        <span title="Terminal MUX" class="tray-led-wrap">
          MUX <span class="api-led" :class="serviceStatus.mux ? 'up' : 'down'"></span>
        </span>
        <span title="Redis Queue" class="tray-led-wrap">
          Q <span class="api-led" :class="serviceStatus.redis ? 'up' : 'down'"></span>
        </span>
      </div>

      <div class="tray-clock">
        {{ time }}
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useWindowStore } from '../stores/windows'
import { useNodesStore } from '../stores/nodes'

defineProps<{
  startMenuOpen: boolean
  backendApiStatus: string
  serviceStatus: Record<string, boolean>
}>()

defineEmits(['toggle-start', 'show-desktop'])

const windowStore = useWindowStore()
const nodeStore = useNodesStore()

const toggleWindow = (id: string) => {
  const win = windowStore.windows.find(w => w.id === id)
  if (!win) return

  if (win.isMinimized) {
    win.isMinimized = false
    windowStore.focusWindow(id)
  } else if (win.zIndex === windowStore.nextZIndex - 1) {
    win.isMinimized = true
  } else {
    windowStore.focusWindow(id)
  }
}

const time = ref('')
let timer: ReturnType<typeof setInterval>
onMounted(() => {
  timer = setInterval(() => {
    const d = new Date()
    time.value = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.taskbar {
  height: 44px;
  background: rgba(8, 13, 24, 0.85);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(0, 229, 255, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 10px;
  z-index: 1000;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.6);
}

.taskbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 100%;
}

.start-btn {
  background: transparent;
  border: none;
  color: var(--cyan);
  font-family: var(--font-hd);
  font-weight: 900;
  font-size: 14px;
  letter-spacing: 2px;
  cursor: pointer;
  padding: 0 16px;
  height: 32px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  transition: all 0.2s;
  text-shadow: 0 0 10px rgba(0,255,157,0.4);
}
.start-btn:hover, .start-btn.active {
  background: rgba(0, 229, 255, 0.15);
  box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.3);
}

.task-list {
  display: flex;
  gap: 4px;
  height: 100%;
  align-items: center;
}

.task-item {
  height: 32px;
  padding: 0 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: var(--textbr);
  font-family: var(--font-hd);
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s;
  max-width: 150px;
}
.task-item:hover {
  background: rgba(255, 255, 255, 0.08);
}
.task-item.active {
  background: rgba(0, 229, 255, 0.1);
  border-color: rgba(0, 229, 255, 0.4);
  color: var(--textwh);
  box-shadow: 0 2px 8px rgba(0, 229, 255, 0.2);
}
.task-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.system-tray {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 100%;
}

.tray-leds {
  display: flex;
  gap: 12px;
}
.tray-led-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-hd);
  font-size: 9px;
  color: var(--text);
  letter-spacing: 1px;
}

.api-led {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: var(--border2); transition: all 0.3s;
}
.api-led.up { background: var(--green); box-shadow: 0 0 6px var(--green); }
.api-led.down { background: var(--pink); box-shadow: 0 0 6px var(--pink); animation: led-pulse 1s infinite alternate; }

.tray-clock {
  font-family: var(--font-co);
  font-size: 13px;
  color: var(--textwh);
  padding-left: 12px;
  border-left: 1px solid var(--border);
}

.mode-toggle-btn {
  background: rgba(0, 255, 157, 0.1);
  border: 1px solid var(--green);
  color: var(--green);
  font-family: var(--font-hd);
  font-size: 10px;
  font-weight: bold;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  letter-spacing: 1px;
  transition: all 0.3s ease;
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.2);
}
.mode-toggle-btn:hover {
  background: rgba(0, 255, 157, 0.2);
}
.mode-toggle-btn.sim-active {
  background: rgba(255, 0, 85, 0.15);
  border-color: var(--pink);
  color: var(--pink);
  box-shadow: 0 0 15px rgba(255, 0, 85, 0.3);
  animation: sim-pulse 2s infinite alternate;
}
@keyframes sim-pulse {
  0% { box-shadow: 0 0 5px rgba(255, 0, 85, 0.2); }
  100% { box-shadow: 0 0 20px rgba(255, 0, 85, 0.6); }
}

@keyframes led-pulse { from { opacity: 0.4; } to { opacity: 1; } }
</style>
