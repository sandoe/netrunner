<template>
  <div class="atk">
    <div class="atk-scan"></div>
    <div class="atk-head">
      <div>
        <div class="atk-title">MITRE ATT&CK · LIVE TECHNIQUE MATRIX</div>
        <div class="atk-sub">{{ observedCount }} techniques observed · {{ totalHits }} detections</div>
      </div>
      <div class="atk-legend">
        <span><i class="dot hot"></i> active</span>
        <span><i class="dot seen"></i> seen</span>
        <span><i class="dot idle"></i> idle</span>
      </div>
    </div>

    <div class="atk-grid">
      <div v-for="t in TACTICS" :key="t.id" class="tac-col">
        <div class="tac-head">{{ t.label }}</div>
        <div v-for="tech in t.techs" :key="tech.id" class="cell" :class="cellState(tech.id)">
          <span class="cell-id">{{ tech.id }}</span>
          <span class="cell-name">{{ tech.name }}</span>
          <span v-if="hits[tech.id]" class="cell-count">{{ hits[tech.id].count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'

const TACTICS = [
  { id: 'discovery', label: 'Discovery', techs: [{ id: 'T1046', name: 'Network Service Discovery' }] },
  { id: 'initial-access', label: 'Initial Access', techs: [{ id: 'T1190', name: 'Exploit Public-Facing App' }] },
  { id: 'execution', label: 'Execution', techs: [{ id: 'T1059', name: 'Command & Scripting' }] },
  { id: 'persistence', label: 'Persistence', techs: [{ id: 'T1053', name: 'Scheduled Task / Job' }] },
  { id: 'privilege-escalation', label: 'Priv Esc', techs: [{ id: 'T1068', name: 'Privilege Escalation' }] },
  { id: 'defense-evasion', label: 'Defense Evasion', techs: [{ id: 'T1562', name: 'Impair Defenses' }] },
  { id: 'credential-access', label: 'Credential Access', techs: [{ id: 'T1110', name: 'Brute Force' }, { id: 'T1003', name: 'Credential Dumping' }] },
  { id: 'lateral-movement', label: 'Lateral Movement', techs: [{ id: 'T1021', name: 'Remote Services' }] },
  { id: 'collection', label: 'Collection', techs: [{ id: 'T1074', name: 'Data Staged' }] },
  { id: 'command-and-control', label: 'Command & Control', techs: [{ id: 'T1071', name: 'App Layer Protocol' }] },
  { id: 'exfiltration', label: 'Exfiltration', techs: [{ id: 'T1041', name: 'Exfiltration Over C2' }] },
  { id: 'impact', label: 'Impact', techs: [{ id: 'T1498', name: 'Network DoS' }, { id: 'T1496', name: 'Resource Hijacking' }] },
]

const hits = ref<Record<string, { count: number, ts: number }>>({})
const now = ref(Date.now() / 1000)
let pollTimer: any = null, tickTimer: any = null

async function poll() {
  try {
    const ev = (await api.events()).events
    const h: Record<string, { count: number, ts: number }> = {}
    for (const e of ev) {
      if (!e.technique) continue
      const id = e.technique.id
      if (!h[id]) h[id] = { count: 0, ts: 0 }
      h[id].count++
      h[id].ts = Math.max(h[id].ts, e.ts)
    }
    hits.value = h
  } catch { /* non-fatal */ }
}

function cellState(id: string) {
  const h = hits.value[id]
  if (!h) return 'idle'
  return (now.value - h.ts) < 20 ? 'hot' : 'seen'
}
const observedCount = computed(() => Object.keys(hits.value).length)
const totalHits = computed(() => Object.values(hits.value).reduce((s, h) => s + h.count, 0))

onMounted(() => {
  poll(); pollTimer = setInterval(poll, 3000)
  tickTimer = setInterval(() => { now.value = Date.now() / 1000 }, 1000)
})
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); if (tickTimer) clearInterval(tickTimer) })
</script>

<style scoped>
.atk { width: 100%; height: 100%; overflow: auto; padding: 24px; position: relative;
  background: radial-gradient(circle at 50% 0%, #100716 0%, #020305 70%); font-family: var(--font-co); }
.atk-scan { position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(0deg, rgba(255,45,110,0.03) 0 2px, transparent 2px 4px); }
.atk-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.atk-title { font-family: var(--font-hd); font-size: 22px; font-weight: 900; letter-spacing: 3px; color: #fff; text-shadow: 0 0 16px rgba(255,45,110,0.4); }
.atk-sub { font-size: 12px; color: var(--text); margin-top: 4px; }
.atk-legend { display: flex; gap: 14px; font-size: 10px; color: var(--text); }
.atk-legend .dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; }
.dot.hot { background: #ff2d6e; box-shadow: 0 0 6px #ff2d6e; } .dot.seen { background: #ffbe0b; } .dot.idle { background: #2a3a5a; }

.atk-grid { display: flex; gap: 8px; align-items: flex-start; min-width: min-content; }
.tac-col { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 116px; }
.tac-head { font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; color: var(--cyan); text-align: center;
  padding: 6px 4px; border-bottom: 1px solid var(--border); min-height: 30px; display: flex; align-items: center; justify-content: center; }
.cell { position: relative; border: 1px solid var(--border); border-radius: 5px; padding: 8px; background: rgba(20,28,45,0.4);
  transition: all 0.4s; min-height: 52px; }
.cell-id { display: block; font-size: 9px; color: var(--text); letter-spacing: 1px; }
.cell-name { display: block; font-size: 11px; color: #6b7a99; margin-top: 2px; line-height: 1.25; }
.cell-count { position: absolute; top: 6px; right: 6px; font-family: var(--font-hd); font-size: 10px; font-weight: 900;
  background: rgba(0,0,0,0.4); padding: 1px 6px; border-radius: 8px; }
.cell.seen { border-color: #ffbe0b; background: rgba(255,190,11,0.08); }
.cell.seen .cell-name { color: #ffd87a; }
.cell.seen .cell-count { color: #ffbe0b; }
.cell.hot { border-color: #ff2d6e; background: rgba(255,45,110,0.16); box-shadow: 0 0 18px rgba(255,45,110,0.4); animation: cellpulse 0.9s infinite; }
.cell.hot .cell-name { color: #fff; }
.cell.hot .cell-id { color: #ff2d6e; }
.cell.hot .cell-count { color: #fff; background: #ff2d6e; }
@keyframes cellpulse { 50% { box-shadow: 0 0 28px rgba(255,45,110,0.7); } }
</style>
