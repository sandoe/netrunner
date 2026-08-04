<template>
  <div :class="['attacks-container', themeClass]">
    <div class="sidebar">
      <h2 :class="titleClass">{{ title }}</h2>
      <ul>
        <li
          v-for="tab in tabs"
          :key="tab.id"
          :class="{ active: activeTab === tab.id }"
          @click="$emit('update:activeTab', tab.id)"
        >
          {{ tab.label }}
        </li>
      </ul>
    </div>

    <div class="main-content">
      <div class="attack-panel">
        <slot :name="activeTab"></slot>
      </div>

      <div class="terminal-panel">
        <div class="terminal-header">{{ title }} TERMINAL</div>
        <slot name="terminal"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  titleClass?: string
  themeClass?: string
  tabs: { id: string, label: string }[]
  activeTab: string
}>()

defineEmits<{
  (e: 'update:activeTab', val: string): void
}>()
</script>

<style scoped>
.attacks-container {
  display: flex;
  height: 100%;
  color: #fff;
  background-color: #0f111a;
  font-family: 'Space Mono', monospace;
}

.sidebar {
  width: 250px;
  background: #151822;
  border-right: 1px solid #1f2937;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.sidebar h2 {
  font-size: 1.2rem;
  margin-bottom: 2rem;
  text-align: center;
  letter-spacing: 2px;
}

.title-l2 { color: #00ffcc; text-shadow: 0 0 10px rgba(0, 255, 204, 0.5); }
.title-l3 { color: #fb923c; text-shadow: 0 0 10px rgba(251, 146, 60, 0.5); }
.title-l4 { color: #60a5fa; text-shadow: 0 0 10px rgba(96, 165, 250, 0.5); }
.title-l5 { color: #c084fc; text-shadow: 0 0 10px rgba(192, 132, 252, 0.5); }
.title-l6 { color: #facc15; text-shadow: 0 0 10px rgba(250, 204, 21, 0.5); }
.title-l7 { color: #facc15; text-shadow: 0 0 10px rgba(250, 204, 21, 0.5); }

.sidebar ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sidebar li {
  padding: 0.8rem 1rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 4px;
  transition: all 0.2s;
  font-weight: bold;
}

.theme-l2 .sidebar li:hover { background: rgba(0, 255, 204, 0.1); border-color: #00ffcc; }
.theme-l2 .sidebar li.active { background: rgba(0, 255, 204, 0.2); border-color: #00ffcc; color: #00ffcc; box-shadow: 0 0 10px rgba(0, 255, 204, 0.2) inset; }

.theme-l3 .sidebar li:hover { background: rgba(251, 146, 60, 0.1); border-color: #fb923c; }
.theme-l3 .sidebar li.active { background: rgba(251, 146, 60, 0.2); border-color: #fb923c; color: #fb923c; box-shadow: 0 0 10px rgba(251, 146, 60, 0.2) inset; }

.theme-l4 .sidebar li:hover { background: rgba(96, 165, 250, 0.1); border-color: #60a5fa; }
.theme-l4 .sidebar li.active { background: rgba(96, 165, 250, 0.2); border-color: #60a5fa; color: #60a5fa; box-shadow: 0 0 10px rgba(96, 165, 250, 0.2) inset; }

.theme-l5 .sidebar li:hover { background: rgba(192, 132, 252, 0.1); border-color: #c084fc; }
.theme-l5 .sidebar li.active { background: rgba(192, 132, 252, 0.2); border-color: #c084fc; color: #c084fc; box-shadow: 0 0 10px rgba(192, 132, 252, 0.2) inset; }

.theme-l6 .sidebar li:hover { background: rgba(250, 204, 21, 0.1); border-color: #facc15; }
.theme-l6 .sidebar li.active { background: rgba(250, 204, 21, 0.2); border-color: #facc15; color: #facc15; box-shadow: 0 0 10px rgba(250, 204, 21, 0.2) inset; }

.theme-l7 .sidebar li:hover { background: rgba(250, 204, 21, 0.1); border-color: #facc15; }
.theme-l7 .sidebar li.active { background: rgba(250, 204, 21, 0.2); border-color: #facc15; color: #facc15; box-shadow: 0 0 10px rgba(250, 204, 21, 0.2) inset; }

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 2rem;
  gap: 2rem;
}

.attack-panel {
  background: #1a1d27;
  border: 1px solid #2d3748;
  border-radius: 8px;
  padding: 2rem;
  flex: 0 0 auto;
}

.terminal-panel {
  flex: 1;
  background: #000;
  border: 1px solid #374151;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.terminal-header {
  background: #1f2937;
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
  color: #9ca3af;
  border-bottom: 1px solid #374151;
}

:deep(.attack-panel h3) {
  margin-top: 0;
  color: #f87171;
  letter-spacing: 1px;
}

:deep(.description) {
  color: #9ca3af;
  margin-bottom: 2rem;
}

:deep(.form-group) {
  margin-bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

:deep(.form-group label) {
  font-size: 0.9rem;
  color: #e5e7eb;
}

:deep(.form-group input), :deep(.dark-select), :deep(.dark-textarea) {
  background: #111827;
  border: 1px solid #374151;
  padding: 0.8rem;
  border-radius: 4px;
  font-family: inherit;
  color: inherit;
}

.theme-l2 :deep(.form-group input), .theme-l2 :deep(.dark-select), .theme-l2 :deep(.dark-textarea) { color: #00ffcc; }
.theme-l2 :deep(.form-group input:focus), .theme-l2 :deep(.dark-select:focus), .theme-l2 :deep(.dark-textarea:focus) { outline: none; border-color: #00ffcc; box-shadow: 0 0 0 2px rgba(0, 255, 204, 0.2); }

.theme-l3 :deep(.form-group input), .theme-l3 :deep(.dark-select), .theme-l3 :deep(.dark-textarea) { color: #fb923c; }
.theme-l3 :deep(.form-group input:focus), .theme-l3 :deep(.dark-select:focus), .theme-l3 :deep(.dark-textarea:focus) { outline: none; border-color: #fb923c; box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.2); }

.theme-l4 :deep(.form-group input), .theme-l4 :deep(.dark-select), .theme-l4 :deep(.dark-textarea) { color: #60a5fa; }
.theme-l4 :deep(.form-group input:focus), .theme-l4 :deep(.dark-select:focus), .theme-l4 :deep(.dark-textarea:focus) { outline: none; border-color: #60a5fa; box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.2); }

.theme-l5 :deep(.form-group input), .theme-l5 :deep(.dark-select), .theme-l5 :deep(.dark-textarea) { color: #c084fc; }
.theme-l5 :deep(.form-group input:focus), .theme-l5 :deep(.dark-select:focus), .theme-l5 :deep(.dark-textarea:focus) { outline: none; border-color: #c084fc; box-shadow: 0 0 0 2px rgba(192, 132, 252, 0.2); }

.theme-l6 :deep(.form-group input), .theme-l6 :deep(.dark-select), .theme-l6 :deep(.dark-textarea) { color: #facc15; }
.theme-l6 :deep(.form-group input:focus), .theme-l6 :deep(.dark-select:focus), .theme-l6 :deep(.dark-textarea:focus) { outline: none; border-color: #facc15; box-shadow: 0 0 0 2px rgba(250, 204, 21, 0.2); }

.theme-l7 :deep(.form-group input), .theme-l7 :deep(.dark-select), .theme-l7 :deep(.dark-textarea) { color: #facc15; }
.theme-l7 :deep(.form-group input:focus), .theme-l7 :deep(.dark-select:focus), .theme-l7 :deep(.dark-textarea:focus) { outline: none; border-color: #facc15; box-shadow: 0 0 0 2px rgba(250, 204, 21, 0.2); }

:deep(.btn) {
  padding: 1rem 2rem;
  border: none;
  border-radius: 4px;
  font-family: inherit;
  font-weight: bold;
  cursor: pointer;
  letter-spacing: 1px;
  transition: all 0.2s;
  width: 100%;
}

:deep(.btn-danger) { background: #ef4444; color: white; }
:deep(.btn-danger:hover) { background: #dc2626; box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }
:deep(.btn-primary) { background: #3b82f6; color: white; }
:deep(.btn-primary:hover) { background: #2563eb; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); }

:deep(.device-list) {
  margin-top: 2rem;
  background: #111827;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #374151;
}

:deep(.device-item) {
  padding: 1rem 0;
  border-bottom: 1px solid #374151;
}

:deep(.device-item:last-child) {
  border-bottom: none;
  padding-bottom: 0;
}

:deep(.text-muted) {
  color: #6b7280;
  font-size: 0.9rem;
  margin-top: 0.3rem;
}

:deep(.result-box) {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #111827;
  border: 1px dashed inherit;
  border-radius: 4px;
}

:deep(.encoded-text) {
  margin-top: 0.5rem;
  color: #a7f3d0;
  word-break: break-all;
  font-size: 0.9rem;
}
</style>
