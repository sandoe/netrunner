<template>
  <div class="privesc-view">
    <div class="header">
      <h1>⬆️ Privilege Escalation Scanner</h1>
      <p class="subtitle">Automated privesc path detection</p>
    </div>

    <div class="panel">
      <h2>New Scan</h2>
      <div class="form-group">
        <label>Target Node</label>
        <select v-model="selectedNode">
          <option value="">Select node...</option>
          <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }} ({{ node.host }})</option>
        </select>
      </div>
      <button @click="startScan" :disabled="!selectedNode || scanning" class="btn-primary">
        {{ scanning ? '⏳ Scanning...' : '🔍 Start Scan' }}
      </button>
    </div>

    <div v-if="scanResult" class="panel">
      <div class="scan-header">
        <h2>Scan Results — Risk Score: <span :class="['risk', riskClass]">{{ scanResult.risk_score }}%</span></h2>
      </div>

      <div v-if="scanResult.findings?.length > 0" class="findings-section">
        <h3>🔴 Critical Findings ({{ scanResult.findings.length }})</h3>
        <div v-for="f in scanResult.findings" :key="f.type" class="finding-card">
          <div class="finding-header">
            <span :class="['severity', f.severity]">{{ f.severity }}</span>
            <span class="finding-type">{{ f.type }}</span>
          </div>
          <p>{{ f.description }}</p>
          <div v-if="f.exploit" class="exploit-code">{{ f.exploit }}</div>
          <div v-if="f.recommendation" class="recommendation">💡 {{ f.recommendation }}</div>
        </div>
      </div>

      <div class="results-section">
        <h3>Detailed Results</h3>
        <div v-for="r in scanResult.results" :key="r.id" :class="['result-card', r.raw_lines > 0 ? 'has-output' : '']">
          <div class="result-header">
            <span class="result-name">{{ r.name }}</span>
            <span :class="['severity', r.severity]">{{ r.severity }}</span>
          </div>
          <pre v-if="r.output" class="result-output">{{ r.output }}</pre>
        </div>
      </div>
    </div>

    <div class="panel">
      <h2>Scan History</h2>
      <div v-for="s in scans" :key="s.scan_id" class="scan-card" @click="viewScan(s.scan_id)">
        <span class="scan-host">{{ s.host }}</span>
        <span :class="['risk', s.risk_score > 70 ? 'high' : s.risk_score > 40 ? 'medium' : 'low']">
          Risk: {{ s.risk_score }}%
        </span>
        <span class="scan-findings">{{ s.findings_count }} findings</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../api/client'

const nodes = ref<any[]>([])
const scans = ref<any[]>([])
const selectedNode = ref('')
const scanning = ref(false)
const scanResult = ref<any>(null)

const riskClass = computed(() => {
  if (!scanResult.value) return ''
  return scanResult.value.risk_score > 70 ? 'high' : scanResult.value.risk_score > 40 ? 'medium' : 'low'
})

onMounted(async () => {
  try {
    const [nodesRes, scansRes] = await Promise.all([
      api.get('/nodes'),
      api.get('/privesc/scans'),
    ])
    nodes.value = nodesRes.data?.nodes || []
    scans.value = scansRes.data?.scans || []
  } catch (e) {
    console.error('Failed to load data', e)
  }
})

async function startScan() {
  scanning.value = true
  try {
    const res = await api.post('/privesc/scan', { node_id: selectedNode.value })
    scanResult.value = res.data
    const scansRes = await api.get('/privesc/scans')
    scans.value = scansRes.data?.scans || []
  } catch (e: any) {
    alert(e.response?.data?.detail || 'Scan failed')
  } finally {
    scanning.value = false
  }
}

async function viewScan(scanId: string) {
  try {
    const res = await api.get(`/privesc/scans/${scanId}`)
    scanResult.value = res.data
  } catch (e) {
    console.error('Failed to load scan', e)
  }
}
</script>

<style scoped>
.privesc-view { padding: 20px; color: #e0e0e0; }
.header h1 { color: #00ff88; margin-bottom: 4px; }
.subtitle { color: #888; margin-bottom: 20px; }
.panel { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.panel h2 { color: #00ff88; margin-bottom: 16px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 4px; color: #aaa; }
.form-group select { width: 100%; padding: 8px; background: #0d1117; border: 1px solid #333; color: #e0e0e0; border-radius: 4px; }
.btn-primary { padding: 10px 20px; background: #00ff88; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-primary:hover:not(:disabled) { background: #00cc6a; }
.btn-primary:disabled { opacity: 0.5; }
.risk { font-weight: bold; }
.risk.high { color: #ff4444; }
.risk.medium { color: #ffaa00; }
.risk.low { color: #00ff88; }
.findings-section { margin-bottom: 20px; }
.findings-section h3 { color: #ff4444; margin-bottom: 12px; }
.finding-card { background: #0d1117; border: 1px solid #ff4444; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.finding-header { display: flex; gap: 8px; margin-bottom: 8px; }
.severity { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; text-transform: uppercase; }
.severity.critical { background: #ff4444; color: #fff; }
.severity.high { background: #ff8800; color: #000; }
.severity.medium { background: #ffaa00; color: #000; }
.severity.info { background: #00aaff; color: #000; }
.finding-type { color: #888; }
.exploit-code { background: #111; padding: 8px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin-top: 8px; color: #ff8800; border-left: 3px solid #ff4444; }
.recommendation { background: rgba(0, 255, 136, 0.1); padding: 8px; border-radius: 4px; margin-top: 8px; border-left: 3px solid #00ff88; }
.result-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.result-card.has-output { border-left-color: #00ff88; }
.result-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.result-name { font-weight: bold; }
.result-output { background: #111; padding: 8px; border-radius: 4px; font-size: 0.85em; overflow-x: auto; max-height: 200px; overflow-y: auto; }
.scan-card { display: flex; gap: 16px; align-items: center; background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 8px; cursor: pointer; }
.scan-card:hover { border-color: #00ff88; }
</style>
