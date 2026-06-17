<template>
  <div class="security-panel">
    <div class="sec sec-grow" :class="{ collapsed: isC('threat_report') }">
      <div class="sec-head" @click="toggle('threat_report')">
        <span class="sec-title">⚠️ VULNERABILITY SCANNER</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('threat_report')" class="sec-body grow">
        <ThreatReportPanel :node-id="nodeId" />
      </div>
    </div>

    <div class="sec sec-grow" :class="{ collapsed: isC('defense') }">
      <div class="sec-head" @click="toggle('defense')">
        <span class="sec-title">🛡️ ACTIVE DEFENSE</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('defense')" class="sec-body grow">
        <ActiveDefensePanel :node-id="nodeId" />
      </div>
    </div>

    <div class="sec sec-grow" :class="{ collapsed: isC('agents') }">
      <div class="sec-head" @click="toggle('agents')">
        <span class="sec-title">🤖 BACKGROUND AGENTS</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('agents')" class="sec-body grow">
        <AgentsPanel :node-id="nodeId" />
      </div>
    </div>

    <div class="sec sec-grow" :class="{ collapsed: isC('shaper') }">
      <div class="sec-head" @click="toggle('shaper')">
        <span class="sec-title">🌀 CHAOS SHAPER</span>
        <span class="sec-chev">⌄</span>
      </div>
      <div v-show="!isC('shaper')" class="sec-body grow">
        <ChaosShaperPanel :node-id="nodeId" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ThreatReportPanel from './ThreatReportPanel.vue'
import ActiveDefensePanel from './ActiveDefensePanel.vue'
import AgentsPanel from './AgentsPanel.vue'
import ChaosShaperPanel from './ChaosShaperPanel.vue'

defineProps<{ nodeId: string }>()

const KEY = 'nr_security_collapsed'
// Collapse Agents and Chaos by default, show Vulnerabilities and Defense
const collapsed = ref<Set<string>>(new Set(JSON.parse(localStorage.getItem(KEY) || '["agents","shaper"]')))
function isC(k: string) { return collapsed.value.has(k) }
function toggle(k: string) {
  const s = new Set(collapsed.value)
  s.has(k) ? s.delete(k) : s.add(k)
  collapsed.value = s
  localStorage.setItem(KEY, JSON.stringify([...s]))
}
</script>

<style scoped>
.security-panel {
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
