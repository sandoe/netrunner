<template>
  <div class="pulse">
    <div class="pulse-scanline"></div>

    <!-- Hero: health ring + headline -->
    <div class="pulse-hero">
      <div class="health-ring" :style="{ '--c': healthColor }">
        <svg viewBox="0 0 120 120">
          <circle class="ring-bg" cx="60" cy="60" r="52" />
          <circle class="ring-fg" cx="60" cy="60" r="52"
                  :stroke-dasharray="ringCirc"
                  :stroke-dashoffset="ringCirc * (1 - health / 100)" />
        </svg>
        <div class="health-num">
          <span class="health-val">{{ health }}</span>
          <span class="health-lbl">HEALTH</span>
        </div>
      </div>
      <div class="hero-text">
        <div class="hero-title">NETWORK PULSE</div>
        <div class="hero-status" :style="{ color: healthColor }">{{ healthLabel }}</div>
        <div class="hero-sub">{{ online }}/{{ monitored }} nodes reachable · {{ activeAlerts }} active alert(s)</div>
      </div>
    </div>

    <!-- Stat tiles -->
    <div class="pulse-tiles">
      <div class="tile">
        <div class="tile-val text-green">{{ online }}</div>
        <div class="tile-lbl">ONLINE</div>
      </div>
      <div class="tile" :class="{ alarm: offline > 0 }">
        <div class="tile-val" :class="offline > 0 ? 'text-pink' : 'text-dim'">{{ offline }}</div>
        <div class="tile-lbl">OFFLINE</div>
      </div>
      <div class="tile">
        <div class="tile-val text-cyan">{{ avgLatency === null ? '–' : avgLatency }}<span class="u">ms</span></div>
        <div class="tile-lbl">AVG LATENCY</div>
      </div>
      <div class="tile">
        <div class="tile-val" :class="fleetCpu > 80 ? 'text-pink' : 'text-cyan'">{{ fleetCpu === null ? '–' : fleetCpu }}<span class="u">%</span></div>
        <div class="tile-lbl">FLEET CPU</div>
      </div>
      <div class="tile">
        <div class="tile-val" :class="fleetRam > 80 ? 'text-pink' : 'text-purple'">{{ fleetRam === null ? '–' : fleetRam }}<span class="u">%</span></div>
        <div class="tile-lbl">FLEET RAM</div>
      </div>
      <div class="tile" :class="{ alarm: critCount > 0 }">
        <div class="tile-val" :class="critCount > 0 ? 'text-pink' : 'text-dim'">{{ critCount }}</div>
        <div class="tile-lbl">CRITICAL</div>
      </div>
    </div>

    <div class="pulse-grid">
      <!-- Node matrix -->
      <div class="panel node-matrix">
        <div class="panel-head">FLEET · {{ nodeRows.length }} NODES</div>
        <div class="matrix-body">
          <div v-for="n in nodeRows" :key="n.id" class="ncard" :class="n.state">
            <div class="ncard-top">
              <span class="ncard-dot" :style="{ background: n.dot }"></span>
              <span class="ncard-name">{{ n.name }}</span>
              <span class="ncard-lat">{{ n.lat }}</span>
            </div>
            <div class="ncard-bars">
              <div class="bar"><span class="bar-lbl">CPU</span><div class="bar-track"><div class="bar-fill cpu" :style="{ width: (n.cpu||0) + '%' }"></div></div></div>
              <div class="bar"><span class="bar-lbl">RAM</span><div class="bar-track"><div class="bar-fill ram" :style="{ width: (n.ram||0) + '%' }"></div></div></div>
            </div>
          </div>
          <div v-if="nodeRows.length === 0" class="matrix-empty">No nodes registered.</div>
        </div>
      </div>

      <!-- Live event ticker -->
      <div class="panel event-feed">
        <div class="panel-head feed-head">
          <span>LIVE EVENTS</span>
          <button v-if="events.length" class="feed-clear" @click="clearEvents">CLEAR</button>
        </div>
        <div class="feed-body">
          <div v-for="e in filteredEvents" :key="e.id" class="feed-row" :class="e.severity">
            <span class="feed-sev">{{ sevIcon(e.severity) }}</span>
            <span class="feed-msg">{{ e.message }}</span>
            <span class="feed-ago">{{ ago(e.ts) }}</span>
          </div>
          <div v-if="filteredEvents.length === 0" class="feed-empty">— ALL SYSTEMS NOMINAL —</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'

const store = useNodesStore()
const reach = ref<Record<string, any>>({})
const vitals = ref<Record<string, any>>({})
const events = ref<any[]>([])
let timer: any = null

const CONSOLELESS = ['ethernet_switch', 'ethernet_hub', 'frame_relay_switch', 'atm_switch', 'cloud', 'nat']
const isL2 = (n: any) => CONSOLELESS.includes(n?.metadata?.gns3?.node_type)

const ringCirc = 2 * Math.PI * 52

async function poll() {
  try {
    const [r, v, e] = await Promise.all([
      api.nodeReachability().catch(() => ({})),
      api.nodeVitals().catch(() => ({})),
      api.events().then(x => x.events).catch(() => []),
    ])
    reach.value = r as any
    vitals.value = v as any
    events.value = e as any
  } catch { /* non-fatal */ }
}

const selectedNodeList = computed(() => {
  if (store.selectedId) {
    return store.nodeList.filter(n => n.id === store.selectedId)
  }
  return store.nodeList
})

// monitored = non-L2 nodes
const monitored = computed(() => selectedNodeList.value.filter(n => !isL2(n)).length)
const online = computed(() => selectedNodeList.value.filter(n => !isL2(n) && reach.value[n.id]?.reachable).length)
const offline = computed(() => Math.max(0, monitored.value - online.value))

const avgLatency = computed(() => {
  const lats = selectedNodeList.value.map(n => reach.value[n.id]).filter(r => r?.reachable && r.latency_ms != null).map(r => r.latency_ms)
  if (!lats.length) return null
  return Math.round(lats.reduce((a, b) => a + b, 0) / lats.length)
})
const fleetCpu = computed(() => avgVital('cpu'))
const fleetRam = computed(() => avgVital('ram'))
function avgVital(k: string) {
  const ids = selectedNodeList.value.map(n => n.id)
  const vals = ids.map(id => vitals.value[id]?.[k]).filter((x: any) => x != null)
  if (!vals.length) return null
  return Math.round(vals.reduce((a: number, b: number) => a + b, 0) / vals.length)
}

const filteredEvents = computed(() => {
  if (!store.selectedId) return events.value
  // For events, we might need to filter by node name if available, or just show all global events
  // Assuming events don't have a specific node_id right now, or maybe they do?
  // They are from api.events() which are system events. Let's just show all events for now, or filter if we can.
  // We will leave events unfiltered or filter if they contain the node name.
  return events.value.filter((e: any) => {
    const n = store.nodeList.find(n => n.id === store.selectedId)
    if (!n) return true
    return e.message.includes(n.name) || e.message.includes(n.host) || !e.node_id // basic heuristic
  })
})

const critCount = computed(() => filteredEvents.value.filter(e => e.severity === 'critical' && (Date.now() / 1000 - e.ts) < 600).length)
const activeAlerts = computed(() => filteredEvents.value.filter(e => e.severity !== 'info' && (Date.now() / 1000 - e.ts) < 600).length)

const health = computed(() => {
  if (monitored.value === 0) return 100
  let h = (online.value / monitored.value) * 100
  if (fleetCpu.value !== null && fleetCpu.value > 80) h -= 10
  if (fleetRam.value !== null && fleetRam.value > 80) h -= 10
  h -= critCount.value * 5
  return Math.max(0, Math.min(100, Math.round(h)))
})
const healthColor = computed(() => health.value >= 80 ? '#00ff9d' : health.value >= 50 ? '#ffbe0b' : '#ff2d6e')
const healthLabel = computed(() => health.value >= 90 ? 'OPERATIONAL' : health.value >= 50 ? 'DEGRADED' : 'CRITICAL')

const nodeRows = computed(() => selectedNodeList.value.map(n => {
  const r = reach.value[n.id]; const v = vitals.value[n.id]
  let state = 'unknown', dot = '#555', lat = '—'
  if (isL2(n)) { state = 'l2'; dot = '#ffbe0b'; lat = 'L2' }
  else if (r) { state = r.reachable ? 'up' : 'down'; dot = r.reachable ? '#00ff9d' : '#ff2d6e'; lat = r.reachable ? `${r.latency_ms}ms` : 'offline' }
  return { id: n.id, name: n.name, state, dot, lat, cpu: v?.cpu, ram: v?.ram }
}).sort((a, b) => (a.state === 'down' ? -1 : 1) - (b.state === 'down' ? -1 : 1) || a.name.localeCompare(b.name)))

async function clearEvents() {
  try { await api.clearEvents(); events.value = [] } catch { /* non-fatal */ }
}
function sevIcon(s: string) { return s === 'critical' ? '🔴' : s === 'warning' ? '🟡' : '🔵' }
function ago(ts: number) {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts))
  return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h`
}

onMounted(() => { poll(); timer = setInterval(poll, 4000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.pulse {
  width: 100%; height: 100%; overflow-y: auto; padding: 28px;
  background: radial-gradient(circle at 30% 0%, #0a1424 0%, #020305 70%);
  font-family: var(--font-co); position: relative;
}
.pulse-scanline { position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(0deg, rgba(0,255,157,0.02) 0 2px, transparent 2px 4px); }

.pulse-hero { display: flex; align-items: center; gap: 30px; margin-bottom: 26px; }
.health-ring { position: relative; width: 130px; height: 130px; flex-shrink: 0; }
.health-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 8; }
.ring-fg { fill: none; stroke: var(--c); stroke-width: 8; stroke-linecap: round;
  transition: stroke-dashoffset 0.8s ease, stroke 0.4s; filter: drop-shadow(0 0 6px var(--c)); }
.health-num { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.health-val { font-family: var(--font-hd); font-size: 38px; font-weight: 900; color: #fff; line-height: 1; text-shadow: 0 0 12px var(--c); }
.health-lbl { font-size: 9px; letter-spacing: 3px; color: var(--text); margin-top: 4px; }
.hero-title { font-family: var(--font-hd); font-size: 30px; font-weight: 900; letter-spacing: 4px; color: #fff; text-shadow: 0 0 18px rgba(0,229,255,0.4); }
.hero-status { font-family: var(--font-hd); font-size: 16px; letter-spacing: 3px; margin: 6px 0; text-shadow: 0 0 10px currentColor; }
.hero-sub { font-size: 12px; color: var(--text); }

.pulse-tiles { display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-bottom: 22px; }
.tile { background: rgba(10,18,34,0.6); border: 1px solid var(--border); border-radius: var(--r); padding: 16px; text-align: center; }
.tile.alarm { border-color: var(--pink); box-shadow: 0 0 16px rgba(255,45,110,0.15); animation: alarm 1.4s infinite; }
@keyframes alarm { 50% { box-shadow: 0 0 24px rgba(255,45,110,0.35); } }
.tile-val { font-family: var(--font-hd); font-size: 30px; font-weight: 900; line-height: 1; }
.tile-val .u { font-size: 13px; opacity: 0.6; margin-left: 2px; }
.tile-lbl { font-size: 9px; letter-spacing: 2px; color: var(--text); margin-top: 8px; }
.text-green { color: var(--green); } .text-pink { color: var(--pink); } .text-cyan { color: var(--cyan); }
.text-purple { color: #a158ff; } .text-dim { color: #4a5a72; }

.pulse-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; }
@media (max-width: 1000px) { .pulse-grid { grid-template-columns: 1fr; } .pulse-tiles { grid-template-columns: repeat(3, 1fr); } }
.panel { background: rgba(8,14,26,0.6); border: 1px solid var(--border); border-radius: var(--r); display: flex; flex-direction: column; overflow: hidden; }
.panel-head { padding: 10px 14px; font-family: var(--font-hd); font-size: 10px; letter-spacing: 2px; color: var(--cyan); border-bottom: 1px solid var(--border); }
.feed-head { display: flex; justify-content: space-between; align-items: center; }
.feed-clear { background: none; border: 1px solid var(--border2); color: var(--text); font-family: var(--font-hd); font-size: 8px; letter-spacing: 1px; padding: 3px 8px; border-radius: 4px; cursor: pointer; }
.feed-clear:hover { border-color: var(--cyan); color: var(--cyan); }

.matrix-body { padding: 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.ncard { background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-left: 3px solid #444; border-radius: 6px; padding: 10px; }
.ncard.up { border-left-color: var(--green); }
.ncard.down { border-left-color: var(--pink); box-shadow: inset 0 0 16px rgba(255,45,110,0.1); }
.ncard.l2 { border-left-color: #ffbe0b; }
.ncard-top { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ncard-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ncard-name { flex: 1; color: #fff; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ncard-lat { font-size: 10px; color: var(--text); }
.ncard-bars { display: flex; flex-direction: column; gap: 4px; }
.bar { display: flex; align-items: center; gap: 6px; }
.bar-lbl { font-size: 8px; color: var(--text); width: 22px; }
.bar-track { flex: 1; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
.bar-fill.cpu { background: var(--cyan); } .bar-fill.ram { background: #a158ff; }
.matrix-empty, .feed-empty { padding: 20px; text-align: center; color: var(--text); font-size: 12px; }

.feed-body { padding: 8px; overflow-y: auto; max-height: 420px; }
.feed-row { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 5px; font-size: 11px; border-left: 2px solid var(--border2); margin-bottom: 4px; }
.feed-row.critical { border-left-color: var(--pink); background: rgba(255,45,110,0.05); }
.feed-row.warning { border-left-color: #ffbe0b; background: rgba(255,190,11,0.05); }
.feed-msg { flex: 1; color: var(--textwh); }
.feed-ago { color: var(--text); font-size: 9px; }
</style>
