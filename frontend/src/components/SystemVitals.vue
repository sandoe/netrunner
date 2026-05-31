<template>
  <div class="sv">
    <template v-if="snap && snap.connected">
      <div class="sv-gauges">
        <div class="g" v-for="g in gauges" :key="g.lbl">
          <svg viewBox="0 0 80 80" class="g-ring">
            <circle class="g-bg" cx="40" cy="40" r="34" />
            <circle class="g-fg" cx="40" cy="40" r="34" :style="{ stroke: g.color }"
                    :stroke-dasharray="GC" :stroke-dashoffset="GC * (1 - (g.pct ?? 0) / 100)" />
          </svg>
          <div class="g-center"><span class="g-val">{{ g.val }}</span><span class="g-u">{{ g.unit }}</span></div>
          <div class="g-lbl">{{ g.lbl }}</div>
        </div>

        <div class="sv-meta">
          <div class="m-row"><span class="m-k">HOST</span><span class="m-v">{{ snap.hostname || '—' }}</span></div>
          <div class="m-row"><span class="m-k">KERNEL</span><span class="m-v">{{ snap.kernel || '—' }}</span></div>
          <div class="m-row"><span class="m-k">UPTIME</span><span class="m-v text-green">{{ uptimeStr }}</span></div>
          <div class="m-row"><span class="m-k">LOAD</span><span class="m-v">{{ snap.load ? snap.load.map((x:number)=>x.toFixed(2)).join(' · ') : '—' }}</span></div>
          <div class="m-row"><span class="m-k">NET</span><span class="m-v text-cyan">↓{{ snap.net_rx ?? 0 }} ↑{{ snap.net_tx ?? 0 }} Mbps</span></div>
        </div>
      </div>

      <div class="sv-procs">
        <div class="sv-procs-head">TOP PROCESSES</div>
        <div class="proc-row proc-h"><span>USER</span><span>CPU%</span><span>MEM%</span><span class="proc-cmd">COMMAND</span></div>
        <div class="proc-row" v-for="(p, i) in snap.processes" :key="i">
          <span>{{ p.user }}</span>
          <span :class="{ hot: p.cpu > 50 }">{{ p.cpu.toFixed(1) }}</span>
          <span>{{ p.mem.toFixed(1) }}</span>
          <span class="proc-cmd">{{ p.cmd }}</span>
        </div>
        <div v-if="!snap.processes || snap.processes.length === 0" class="proc-empty">No process data.</div>
      </div>
    </template>

    <div v-else class="sv-off">
      <span class="sv-off-dot"></span>
      {{ snap && snap.connected === false ? 'Node not connected — CONNECT to stream live system vitals.' : 'Synchronizing system telemetry…' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ nodeId: string }>()
const snap = ref<any>(null)
let timer: any = null
const GC = 2 * Math.PI * 34

async function load() {
  try { snap.value = await api.nodeSystemSnapshot(props.nodeId) } catch { /* non-fatal */ }
}

const gauges = computed(() => {
  const s = snap.value || {}
  const col = (p: number | null | undefined) => p == null ? '#4a5a72' : p < 60 ? '#00ff9d' : p < 85 ? '#ffbe0b' : '#ff2d6e'
  return [
    { lbl: 'CPU', unit: '%', pct: s.cpu, val: s.cpu == null ? '–' : Math.round(s.cpu), color: col(s.cpu) },
    { lbl: 'RAM', unit: '%', pct: s.ram, val: s.ram == null ? '–' : Math.round(s.ram), color: col(s.ram) },
    { lbl: 'DISK', unit: '%', pct: s.disk?.used_pct, val: s.disk ? s.disk.used_pct : '–', color: col(s.disk?.used_pct) },
  ]
})

const uptimeStr = computed(() => {
  const u = snap.value?.uptime_secs
  if (u == null) return '—'
  const d = Math.floor(u / 86400), h = Math.floor((u % 86400) / 3600), m = Math.floor((u % 3600) / 60)
  return d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`
})

watch(() => props.nodeId, () => { snap.value = null; load() })
onMounted(() => { load(); timer = setInterval(load, 3000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.sv { border-bottom: 1px solid var(--border); background: rgba(8,14,26,0.5); padding: 14px 16px; display: flex; gap: 20px; flex-wrap: wrap; font-family: var(--font-co); }
.sv-gauges { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.g { position: relative; width: 80px; text-align: center; }
.g-ring { width: 80px; height: 80px; transform: rotate(-90deg); }
.g-bg { fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 6; }
.g-fg { fill: none; stroke-width: 6; stroke-linecap: round; transition: stroke-dashoffset 0.6s, stroke 0.3s; filter: drop-shadow(0 0 4px currentColor); }
.g-center { position: absolute; top: 26px; left: 0; right: 0; }
.g-val { font-family: var(--font-hd); font-size: 20px; font-weight: 900; color: #fff; }
.g-u { font-size: 10px; color: var(--text); }
.g-lbl { font-size: 9px; letter-spacing: 2px; color: var(--text); margin-top: 2px; }

.sv-meta { display: flex; flex-direction: column; gap: 4px; font-size: 11px; min-width: 200px; }
.m-row { display: flex; gap: 10px; }
.m-k { color: var(--text); width: 56px; font-size: 9px; letter-spacing: 1px; padding-top: 1px; }
.m-v { color: var(--textwh); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.text-green { color: var(--green); } .text-cyan { color: var(--cyan); }

.sv-procs { flex: 1; min-width: 280px; }
.sv-procs-head { font-family: var(--font-hd); font-size: 9px; letter-spacing: 2px; color: var(--cyan); margin-bottom: 6px; }
.proc-row { display: grid; grid-template-columns: 70px 48px 48px 1fr; gap: 6px; font-size: 11px; padding: 2px 0; color: var(--textwh); }
.proc-h { color: var(--text); font-size: 9px; letter-spacing: 1px; border-bottom: 1px solid var(--border); padding-bottom: 4px; margin-bottom: 2px; }
.proc-cmd { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--cyan); }
.proc-row .hot { color: var(--pink); font-weight: bold; }
.proc-empty { color: var(--text); font-size: 11px; padding: 8px 0; }

.sv-off { display: flex; align-items: center; gap: 10px; color: var(--text); font-size: 12px; padding: 8px 0; }
.sv-off-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pink); box-shadow: 0 0 8px var(--pink); }
</style>
