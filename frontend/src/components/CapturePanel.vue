<template>
  <div class="capture-panel">
    <div class="cap-header">
      <div class="cap-title-area">
        <span class="cap-title-icon">📡</span>
        <div class="cap-title-text">
          <div class="cap-main-title">WIRESHARK PROXY</div>
          <div class="cap-sub-title">PACKET INTERCEPTION SYSTEM v2.1</div>
        </div>
      </div>
    </div>

    <div class="cap-input-area">
      <div class="form-grid">
        <div class="form-group">
          <label>INTERFACE</label>
          <input v-model="form.interface" placeholder="eth0" class="cyber-input" />
        </div>
        <div class="form-group">
          <label>PORT / BPF FILTER</label>
          <div class="filter-input-wrap">
            <input v-model="form.filter" placeholder="port 80 or icmp" class="cyber-input" />
            <div class="quick-ports">
              <button @click="form.filter = 'port 80'" class="btn-tiny">HTTP</button>
              <button @click="form.filter = 'port 443'" class="btn-tiny">HTTPS</button>
              <button @click="form.filter = 'port 22'" class="btn-tiny">SSH</button>
              <button @click="form.filter = 'port 53'" class="btn-tiny">DNS</button>
            </div>
          </div>
        </div>
        <div class="form-group small">
          <label>PKT LIMIT</label>
          <input v-model.number="form.packet_limit" type="number" min="0" placeholder="0" class="cyber-input" />
        </div>
      </div>
      <div class="cap-actions">
        <button @click="start" :disabled="starting || !form.interface.trim()" class="btn-cyber-start">
          {{ starting ? 'INITIATING...' : 'START INTERCEPTION' }}
        </button>
        <button @click="refresh" class="btn-cyber-secondary" :disabled="loading">RE-SCAN</button>
      </div>

      <!-- Traffic Generator Section -->
      <div class="traffic-generator">
        <div class="tg-label">
          TRAFFIC GENERATOR (PING)
          <button v-if="pingOutput" @click="pingOutput = ''" class="btn-clear-tg">CLEAR</button>
        </div>
        <div class="tg-controls">
          <input v-model="pingForm.target" placeholder="TARGET IP..." class="cyber-input-sm" @keyup.enter="runPing" />
          <input v-model.number="pingForm.count" type="number" class="cyber-input-xs" title="COUNT" />
          <button @click="runPing" :disabled="pingBusy" class="btn-tiny-neon">GENERATE PACKETS</button>
        </div>
        <div v-if="pingOutput" class="tg-output">{{ pingOutput }}</div>
      </div>

      <div v-if="error" class="cap-error">
        <span class="error-icon">⚠️</span>
        <span class="error-msg">{{ error }}</span>
      </div>
    </div>

    <div class="cap-list">
      <div v-if="!captures.length && !loading" class="cap-empty">
        NO ACTIVE INTERCEPTIONS.
      </div>
      <div v-for="cap in captures" :key="cap.id" class="cap-row">
        <div class="cap-head">
          <div class="cap-meta-main">
            <span class="cap-state" :class="cap.state">
              <span class="dot" :class="cap.state"></span>
              {{ cap.state }}
            </span>
            <span class="cap-id">#{{ cap.id }}</span>
            <span class="cap-iface">{{ cap.interface }}</span>
          </div>
          <div class="cap-meta-details">
            <span v-if="cap.filter" class="cap-filter">FILTER: {{ cap.filter }}</span>
            <span class="cap-size">{{ formatBytes(cap.size || 0) }}</span>
            <span class="cap-time">{{ formatTime(cap.started) }}</span>
          </div>
          <div class="cap-row-actions">
            <button v-if="cap.state === 'running'" @click="stop(cap.id)" class="btn-row btn-stop" :disabled="busy[cap.id]">STOP</button>
            <a v-if="cap.size" :href="downloadUrl(cap.id)" :download="cap.id + '.pcap'" class="btn-row btn-dl">DOWNLOAD</a>
            <button @click="del(cap.id)" class="btn-row btn-del" :disabled="busy[cap.id]">✕</button>
          </div>
        </div>
        <pre v-if="cap.tail" class="cap-tail">{{ cap.tail }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'
import type { CaptureMeta } from '@/types'

type CaptureRow = CaptureMeta & { state?: 'running' | 'stopped'; size?: number; tail?: string }

const props = defineProps<{ nodeId: string }>()

const form = reactive({ interface: 'eth0', filter: '', packet_limit: 0, id: '' })
const captures  = ref<CaptureRow[]>([])
const busy      = reactive<Record<string, boolean>>({})
const starting  = ref(false)
const loading   = ref(false)
const error     = ref('')

const pingForm = reactive({ target: '', count: 4 })
const pingBusy = ref(false)
const pingOutput = ref('')

async function runPing() {
  if (!pingForm.target.trim()) return
  pingBusy.value = true
  pingOutput.value = `GENERATING TRAFFIC TO ${pingForm.target.toUpperCase()}...`
  try {
    const data = await api.executeNode(props.nodeId, [`ping -c ${pingForm.count} ${pingForm.target}`])
    const r = data.results[0]
    pingOutput.value = (r.output || r.error || 'NO RESPONSE').trim()
  } catch (e) {
    pingOutput.value = `ERROR: ${e}`
  } finally {
    pingBusy.value = false
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null

function downloadUrl(capId: string): string {
  return api.captureDownloadUrl(props.nodeId, capId)
}

function formatBytes(n: number): string {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0; let v = n
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${units[i]}`
}

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString()
  } catch { return iso }
}

async function refresh() {
  loading.value = true
  error.value   = ''
  try {
    const { captures: list } = await api.captureList(props.nodeId)
    const previous = new Map(captures.value.map(c => [c.id, c]))
    captures.value = list.map(c => ({ ...previous.get(c.id), ...c }))
    await refreshStatuses()
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

async function refreshStatuses() {
  const updated = await Promise.all(
    captures.value.map(async cap => {
      try {
        const { capture } = await api.captureStatus(props.nodeId, cap.id)
        return { ...cap, ...capture }
      } catch {
        return cap
      }
    })
  )
  captures.value = updated
  syncPolling()
}

function syncPolling() {
  const anyRunning = captures.value.some(c => c.state === 'running')
  if (anyRunning && !pollTimer) {
    pollTimer = setInterval(refreshStatuses, 3000)
  } else if (!anyRunning && pollTimer) {
    clearInterval(pollTimer); pollTimer = null
  }
}

async function start() {
  starting.value = true
  error.value    = ''
  try {
    await api.captureStart(props.nodeId, {
      id: form.id.trim() || undefined,
      interface: form.interface.trim(),
      filter: form.filter.trim() || undefined,
      packet_limit: form.packet_limit || 0,
    })
    form.id = ''
    await refresh()
  } catch (e: any) {
    // Check if it's the tcpdump missing error from backend
    if (e.message && e.message.includes('tcpdump is not installed')) {
        error.value = "CRITICAL: TCPDUMP NOT DETECTED ON NODE. INTERCEPTION ABORTED."
    } else {
        error.value = String(e)
    }
  } finally {
    starting.value = false
  }
}

async function stop(capId: string) {
  busy[capId] = true
  try {
    await api.captureStop(props.nodeId, capId)
    await refreshStatuses()
  } catch (e) {
    error.value = String(e)
  } finally {
    busy[capId] = false
  }
}

async function del(capId: string) {
  if (!confirm(`Permanently wipe capture data #${capId}?`)) return
  busy[capId] = true
  try {
    await api.captureDelete(props.nodeId, capId)
    captures.value = captures.value.filter(c => c.id !== capId)
    syncPolling()
  } catch (e) {
    error.value = String(e)
  } finally {
    busy[capId] = false
  }
}

watch(() => props.nodeId, () => {
  captures.value = []
  error.value    = ''
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  refresh()
})

onMounted(refresh)
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.capture-panel { display: flex; flex-direction: column; height: 100%; background: var(--bg); overflow: hidden; }

.cap-header { padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--bg2); }
.cap-title-area { display: flex; align-items: center; gap: 14px; }
.cap-title-icon { font-size: 24px; color: var(--cyan); text-shadow: 0 0 10px var(--cyan); }
.cap-main-title { font-family: var(--font-hd); font-size: 16px; font-weight: 900; letter-spacing: 2px; color: var(--textwh); }
.cap-sub-title { font-family: var(--font-co); font-size: 9px; color: var(--text); letter-spacing: 1px; }

.cap-input-area { padding: 20px; border-bottom: 1px solid var(--border); background: var(--bg3); }
.form-grid { display: grid; grid-template-columns: 1fr 2fr 100px; gap: 16px; margin-bottom: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-family: var(--font-hd); font-size: 8px; color: var(--text); letter-spacing: 1px; }

.cyber-input {
  background: var(--bg); border: 1px solid var(--border); border-radius: var(--r);
  color: var(--green); font-family: var(--font-co); font-size: 12px; padding: 10px 12px; outline: none; transition: all .2s;
}
.cyber-input:focus { border-color: var(--cyan); box-shadow: 0 0 10px rgba(0, 229, 255, 0.2); }

.filter-input-wrap { position: relative; display: flex; flex-direction: column; gap: 4px; }
.quick-ports { display: flex; gap: 4px; }
.btn-tiny {
  padding: 2px 6px; font-family: var(--font-hd); font-size: 7px; background: var(--bg2); border: 1px solid var(--border); color: var(--text); cursor: pointer; transition: all .2s;
}
.btn-tiny:hover { color: var(--cyan); border-color: var(--cyan); }

.cap-actions { display: flex; gap: 12px; }
.btn-cyber-start {
  padding: 10px 24px; background: var(--bg); border: 1px solid var(--green); border-radius: var(--r);
  color: var(--green); font-family: var(--font-hd); font-size: 10px; letter-spacing: 1.5px; cursor: pointer; transition: all .3s;
}
.btn-cyber-start:hover:not(:disabled) { background: var(--green); color: var(--bg); box-shadow: var(--shadow-g); }
.btn-cyber-start:disabled { opacity: .4; cursor: not-allowed; }

.btn-cyber-secondary {
  padding: 10px 16px; background: var(--bg2); border: 1px solid var(--border); border-radius: var(--r);
  color: var(--textwh); font-family: var(--font-hd); font-size: 10px; letter-spacing: 1px; cursor: pointer;
}
.btn-cyber-secondary:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); }

.cap-error {
  margin-top: 16px; padding: 12px; background: rgba(255, 45, 110, 0.1); border: 1px solid var(--pink);
  border-radius: var(--r); color: var(--pink); font-family: var(--font-co); font-size: 11px; display: flex; align-items: center; gap: 10px;
}
.error-icon { font-size: 16px; }

.cap-list { flex: 1; overflow-y: auto; padding: 20px; }
.cap-empty { padding: 40px; text-align: center; font-family: var(--font-hd); font-size: 10px; color: var(--text); letter-spacing: 2px; }

.cap-row {
  background: var(--bg2); border: 1px solid var(--border); border-radius: var(--r);
  padding: 16px; margin-bottom: 12px; transition: all .2s;
}
.cap-row:hover { border-color: var(--border2); }

.cap-head { display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap; }
.cap-meta-main { display: flex; align-items: center; gap: 12px; }
.cap-state { font-family: var(--font-hd); font-size: 8px; letter-spacing: 1px; display: flex; align-items: center; gap: 6px; }
.cap-state.running { color: var(--green); }
.cap-state.stopped { color: var(--text); }

.dot { width: 6px; height: 6px; border-radius: 50%; }
.dot.running { background: var(--green); box-shadow: 0 0 8px var(--green); animation: pulse 1s infinite; }
.dot.stopped { background: var(--border2); }
@keyframes pulse { 0% { opacity: 1 } 50% { opacity: .3 } 100% { opacity: 1 } }

.cap-id { font-family: var(--font-co); color: var(--cyan); font-size: 12px; }
.cap-iface { padding: 2px 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; color: var(--textwh); font-family: var(--font-co); font-size: 10px; }

.cap-meta-details { display: flex; gap: 16px; align-items: center; }
.cap-filter { font-family: var(--font-co); color: var(--yellow); font-size: 10px; }
.cap-size { font-family: var(--font-co); color: var(--textbr); font-size: 11px; }
.cap-time { font-family: var(--font-co); color: var(--text); font-size: 10px; }

.cap-row-actions { display: flex; gap: 8px; }
.btn-row {
  padding: 6px 12px; font-family: var(--font-hd); font-size: 8px; letter-spacing: 1px; border-radius: 4px;
  background: var(--bg3); border: 1px solid var(--border); color: var(--textwh); cursor: pointer; text-decoration: none;
}
.btn-row:hover { border-color: var(--cyan); color: var(--cyan); }
.btn-stop { border-color: var(--yellow); color: var(--yellow); }
.btn-stop:hover { background: rgba(255, 190, 11, 0.1); }
.btn-del { border-color: var(--pink); color: var(--pink); }
.btn-del:hover { background: rgba(255, 45, 110, 0.1); }

.cap-tail {
  margin-top: 12px; padding: 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
  color: var(--text); font-family: var(--font-co); font-size: 10px; line-height: 1.5;
  white-space: pre-wrap; word-break: break-all; max-height: 120px; overflow-y: auto;
}

.traffic-generator {
  margin-top: 20px;
  padding: 16px;
  background: var(--bg);
  border: 1px dashed var(--border2);
  border-radius: var(--r);
}
.tg-label {
  font-family: var(--font-hd);
  font-size: 8px;
  color: var(--cyan);
  letter-spacing: 1.5px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.btn-clear-tg {
  background: none; border: 1px solid var(--border); color: var(--text);
  font-size: 7px; padding: 1px 4px; cursor: pointer;
}
.btn-clear-tg:hover { color: var(--pink); border-color: var(--pink); }
.tg-controls {
  display: flex;
  gap: 8px;
}
.tg-output {
  margin-top: 12px;
  padding: 8px;
  background: #000;
  border: 1px solid var(--border);
  color: var(--green);
  font-family: var(--font-co);
  font-size: 10px;
  max-height: 80px;
  overflow-y: auto;
  white-space: pre-wrap;
}
.cyber-input-sm {
  flex: 1;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--textwh);
  font-family: var(--font-co);
  font-size: 11px;
  padding: 6px 10px;
  outline: none;
}
.cyber-input-xs {
  width: 50px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--textwh);
  font-family: var(--font-co);
  font-size: 11px;
  padding: 6px;
  text-align: center;
  outline: none;
}
.btn-tiny-neon {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--cyan);
  border-radius: 4px;
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 8px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all .2s;
}
.btn-tiny-neon:hover:not(:disabled) {
  background: var(--cyan);
  color: var(--bg);
  box-shadow: 0 0 10px var(--cyan);
}
.btn-tiny-neon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
