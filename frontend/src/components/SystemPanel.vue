<template>
  <div class="system-panel">
    <div class="sec sec-fixed" :class="{ collapsed: isC('vitals') }">
      <div class="sec-head" @click="toggle('vitals')">
        <span class="sec-title">⚡ LIVE VITALS</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('vitals')" class="sec-body">
        <SystemVitals :node-id="nodeId" />
      </div>
    </div>

    <div class="sec sec-grow" :class="{ collapsed: isC('diag') }">
      <div class="sec-head" @click="toggle('diag')">
        <span class="sec-title">🔍 DIAGNOSTICS</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('diag')" class="sec-body grow">
        <DiagPanel :node-id="nodeId" />
      </div>
    </div>

    <div class="sec sec-grow" :class="{ collapsed: isC('config') }">
      <div class="sec-head" @click="toggle('config')">
        <span class="sec-title">🛠️ CONFIGURATION</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('config')" class="sec-body grow">
        <ConfigPanel :node-id="nodeId" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import DiagPanel from './DiagPanel.vue'
import ConfigPanel from './ConfigPanel.vue'
import SystemVitals from './SystemVitals.vue'

defineProps<{ nodeId: string }>()

const KEY = 'nr_system_collapsed'
const collapsed = ref<Set<string>>(new Set(JSON.parse(localStorage.getItem(KEY) || '[]')))
function isC(k: string) { return collapsed.value.has(k) }
function toggle(k: string) {
  const s = new Set(collapsed.value)
  s.has(k) ? s.delete(k) : s.add(k)
  collapsed.value = s
  localStorage.setItem(KEY, JSON.stringify([...s]))
}
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

.sec {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--border);
  min-height: 0;
}
/* Vitals is a short strip — never grow. */
.sec-fixed { flex: 0 0 auto; }
/* Diagnostics / Config share the remaining height when expanded. */
.sec-grow:not(.collapsed) { flex: 1 1 0; }
.sec-grow.collapsed { flex: 0 0 auto; }

.sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 16px;
  background: var(--bg2);
  cursor: pointer;
  user-select: none;
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--cyan);
  transition: background 0.15s;
  flex-shrink: 0;
}
.sec-head:hover { background: var(--bg3); color: var(--textwh); }
.sec-chev { transition: transform 0.2s; font-size: 14px; }
.sec.collapsed .sec-chev { transform: rotate(-90deg); }

.sec-body { overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
.sec-body.grow { flex: 1 1 0; }
</style>
