<template>
  <div class="workloads-panel">
    <div class="sec sec-grow" :class="{ collapsed: isC('docker') }">
      <div class="sec-head" @click="toggle('docker')">
        <span class="sec-title">🐳 DOCKER CONTAINERS</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('docker')" class="sec-body grow">
        <DockerPanel :node-id="nodeId" />
      </div>
    </div>

    <div class="sec sec-grow" :class="{ collapsed: isC('kubernetes') }">
      <div class="sec-head" @click="toggle('kubernetes')">
        <span class="sec-title">☸️ KUBERNETES</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('kubernetes')" class="sec-body grow">
        <KubernetesPanel :node-id="nodeId" />
      </div>
    </div>

    <div class="sec sec-grow" :class="{ collapsed: isC('database') }">
      <div class="sec-head" @click="toggle('database')">
        <span class="sec-title">🗄️ DATABASE</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('database')" class="sec-body grow">
        <DatabasePanel :node-id="nodeId" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import DockerPanel from './DockerPanel.vue'
import KubernetesPanel from './KubernetesPanel.vue'
import DatabasePanel from './DatabasePanel.vue'

defineProps<{ nodeId: string }>()

const KEY = 'nr_workloads_collapsed'
// Collapse Kubernetes and Database by default, show Docker
const collapsed = ref<Set<string>>(new Set(JSON.parse(localStorage.getItem(KEY) || '["kubernetes","database"]')))
function isC(k: string) { return collapsed.value.has(k) }
function toggle(k: string) {
  const s = new Set(collapsed.value)
  s.has(k) ? s.delete(k) : s.add(k)
  collapsed.value = s
  localStorage.setItem(KEY, JSON.stringify([...s]))
}
</script>

<style scoped>
.workloads-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow-y: auto;
  background: var(--bg);
}

.sec {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--border);
  min-height: 0;
}

.sec-grow:not(.collapsed) { flex: 0 0 auto; }
.sec-grow.collapsed { flex: 0 0 auto; }

.sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: var(--bg2);
  cursor: pointer;
  user-select: none;
}
.sec-head:hover { background: var(--bg3); }
.sec-title {
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 2px;
  font-weight: 800;
  color: var(--text);
  transition: color 0.2s;
}
.sec-head:hover .sec-title { color: var(--cyan); }

.sec-chev {
  color: var(--text);
  font-size: 12px;
  transition: transform 0.3s;
}
.collapsed .sec-chev { transform: rotate(180deg); }

.sec-body {
  background: var(--bg);
  position: relative;
}
.sec-body.grow {
  display: flex;
  flex-direction: column;
}
</style>
