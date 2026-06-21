<template>
  <div class="compliance-view">
    <div class="header">
      <h1>🛡️ Compliance Scanner</h1>
      <p class="subtitle">CIS Benchmarks & NIST 800-53 Framework Analysis</p>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['tab-btn', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- Scan History -->
    <div v-if="activeTab === 'history'" class="tab-content">
      <div class="panel">
        <h2>Scan History</h2>
        <div class="scan-list">
          <div v-for="scan in scanHistory" :key="scan.scan_id" class="scan-card" @click="viewScan(scan.scan_id)">
            <div class="scan-header">
              <span class="scan-framework">{{ scan.framework }}</span>
              <span class="scan-date">{{ formatDate(scan.timestamp) }}</span>
            </div>
            <div class="scan-summary">
              <div class="score-ring" :class="getScoreClass(scan.summary.score)">
                <span class="score-value">{{ scan.summary.score }}%</span>
              </div>
              <div class="scan-details">
                <p><strong>Node:</strong> {{ scan.host }}</p>
                <p><strong>Passed:</strong> {{ scan.summary.passed }}/{{ scan.summary.total }}</p>
                <p><strong>Failed:</strong> {{ scan.summary.failed }}</p>
              </div>
            </div>
          </div>
          <div v-if="scanHistory.length === 0" class="empty-state">
            No scans yet. Start a scan to see results here.
          </div>
        </div>
      </div>
    </div>

    <!-- New Scan -->
    <div v-if="activeTab === 'scan'" class="tab-content">
      <div class="panel">
        <h2>New Compliance Scan</h2>
        <div class="form-group">
          <label>Target Node</label>
          <select v-model="selectedNode">
            <option value="">Select a node...</option>
            <option v-for="node in nodes" :key="node.id" :value="node.id">
              {{ node.name }} ({{ node.host }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Framework</label>
          <select v-model="selectedFramework">
            <option v-for="fw in frameworks" :key="fw.id" :value="fw.id">
              {{ fw.id }} ({{ fw.check_count }} checks)
            </option>
          </select>
        </div>
        <button
          @click="startScan"
          :disabled="!selectedNode || scanning"
          class="btn-primary"
        >
          {{ scanning ? '⏳ Scanning...' : '🔍 Start Scan' }}
        </button>
        <div v-if="scanStatus" :class="['status', scanStatus.type]">
          {{ scanStatus.message }}
        </div>
      </div>
    </div>

    <!-- Scan Results -->
    <div v-if="activeTab === 'results' && currentScan" class="tab-content">
      <div class="panel">
        <div class="results-header">
          <h2>Scan Results — {{ currentScan.framework }}</h2>
          <div class="score-display" :class="getScoreClass(currentScan.summary.score)">
            <span class="score-big">{{ currentScan.summary.score }}%</span>
            <span class="score-label">Compliance Score</span>
          </div>
        </div>
        <div class="summary-cards">
          <div class="summary-card pass">
            <span class="summary-value">{{ currentScan.summary.passed }}</span>
            <span class="summary-label">Passed</span>
          </div>
          <div class="summary-card fail">
            <span class="summary-value">{{ currentScan.summary.failed }}</span>
            <span class="summary-label">Failed</span>
          </div>
          <div class="summary-card warn">
            <span class="summary-value">{{ currentScan.summary.warnings }}</span>
            <span class="summary-label">Warnings</span>
          </div>
          <div class="summary-card total">
            <span class="summary-value">{{ currentScan.summary.total }}</span>
            <span class="summary-label">Total Checks</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <h3>Detailed Results</h3>
        <div class="filter-bar">
          <select v-model="resultFilter">
            <option value="all">All ({{ currentScan.results.length }})</option>
            <option value="fail">Failed ({{ currentScan.results.filter(r => r.status === 'fail').length }})</option>
            <option value="pass">Passed ({{ currentScan.results.filter(r => r.status === 'pass').length }})</option>
            <option value="warning">Warnings ({{ currentScan.results.filter(r => r.status === 'warning').length }})</option>
          </select>
          <select v-model="categoryFilter">
            <option value="all">All Categories</option>
            <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>
        <div class="results-list">
          <div v-for="result in filteredResults" :key="result.id" :class="['result-card', result.status]">
            <div class="result-header">
              <span class="result-status">{{ result.status === 'pass' ? '✅' : result.status === 'fail' ? '❌' : '⚠️' }}</span>
              <span class="result-id">{{ result.id }}</span>
              <span :class="['severity-badge', result.severity]">{{ result.severity }}</span>
            </div>
            <div class="result-title">{{ result.title }}</div>
            <div class="result-output" v-if="result.output">{{ result.output }}</div>
            <div class="result-remediation" v-if="result.status === 'fail' && result.remediation">
              <strong>Remediation:</strong> {{ result.remediation }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Frameworks -->
    <div v-if="activeTab === 'frameworks'" class="tab-content">
      <div class="panel">
        <h2>Compliance Frameworks</h2>
        <div class="framework-grid">
          <div v-for="fw in frameworks" :key="fw.id" class="framework-card">
            <h3>{{ fw.id }}</h3>
            <p>{{ fw.check_count }} checks available</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../api/client'

const tabs = [
  { id: 'history', label: 'Scan History', icon: '📋' },
  { id: 'scan', label: 'New Scan', icon: '🔍' },
  { id: 'results', label: 'Results', icon: '📊' },
  { id: 'frameworks', label: 'Frameworks', icon: '📚' },
]

const activeTab = ref('history')
const nodes = ref<any[]>([])
const scanHistory = ref<any[]>([])
const currentScan = ref<any>(null)
const selectedNode = ref('')
const selectedFramework = ref('CIS')
const scanning = ref(false)
const scanStatus = ref<{ type: string; message: string } | null>(null)
const resultFilter = ref('all')
const categoryFilter = ref('all')
const frameworks = ref<any[]>([])

const categories = computed(() => {
  if (!currentScan.value) return []
  return [...new Set(currentScan.value.results.map((r: any) => r.category))]
})

const filteredResults = computed(() => {
  if (!currentScan.value) return []
  let results = currentScan.value.results
  if (resultFilter.value !== 'all') {
    results = results.filter((r: any) => r.status === resultFilter.value)
  }
  if (categoryFilter.value !== 'all') {
    results = results.filter((r: any) => r.category === categoryFilter.value)
  }
  return results
})

onMounted(async () => {
  try {
    const nodesRes = await api.get('/nodes')
    nodes.value = Object.values(nodesRes.data || {})
  } catch (e) {
    console.error('Failed to load nodes', e)
  }

  try {
    const scansRes = await api.get('/compliance/scans')
    scanHistory.value = scansRes.data?.scans || []
  } catch (e) {
    console.error('Failed to load scan history', e)
  }

  try {
    const fwRes = await api.get('/compliance/frameworks')
    frameworks.value = fwRes.data?.frameworks || []
  } catch (e) {
    console.error('Failed to load frameworks', e)
  }
})

async function startScan() {
  scanning.value = true
  scanStatus.value = null
  try {
    const res = await api.post('/compliance/scan', {
      node_id: selectedNode.value,
      framework: selectedFramework.value,
    })
    currentScan.value = res.data
    scanStatus.value = { type: 'success', message: `Scan complete: ${res.data.summary.score}% compliance` }
    activeTab.value = 'results'

    // Refresh history
    const scansRes = await api.get('/compliance/scans')
    scanHistory.value = scansRes.data?.scans || []
  } catch (e: any) {
    scanStatus.value = { type: 'error', message: e.response?.data?.detail || 'Scan failed' }
  } finally {
    scanning.value = false
  }
}

async function viewScan(scanId: string) {
  try {
    const res = await api.get(`/compliance/scans/${scanId}`)
    currentScan.value = res.data
    activeTab.value = 'results'
  } catch (e) {
    console.error('Failed to load scan', e)
  }
}

function getScoreClass(score: number) {
  if (score >= 90) return 'excellent'
  if (score >= 70) return 'good'
  if (score >= 50) return 'fair'
  return 'poor'
}

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleString()
}
</script>

<style scoped>
.compliance-view {
  padding: 20px;
  color: #e0e0e0;
}

.header h1 {
  color: #00ff88;
  margin-bottom: 4px;
}

.subtitle {
  color: #888;
  margin-bottom: 20px;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
}

.tab-btn {
  padding: 8px 16px;
  background: #1a1a2e;
  border: 1px solid #333;
  color: #aaa;
  cursor: pointer;
  border-radius: 4px 4px 0 0;
}

.tab-btn:hover {
  background: #16213e;
  color: #fff;
}

.tab-btn.active {
  background: #0f3460;
  color: #00ff88;
  border-color: #00ff88;
}

.panel {
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}

.panel h2 {
  color: #00ff88;
  margin-bottom: 16px;
  font-size: 1.2em;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  color: #aaa;
}

.form-group select {
  width: 100%;
  padding: 8px;
  background: #0d1117;
  border: 1px solid #333;
  color: #e0e0e0;
  border-radius: 4px;
}

.btn-primary {
  padding: 10px 20px;
  background: #00ff88;
  color: #000;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-primary:hover:not(:disabled) {
  background: #00cc6a;
}

.btn-primary:disabled {
  opacity: 0.5;
}

.status {
  margin-top: 12px;
  padding: 8px;
  border-radius: 4px;
}

.status.success {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid #00ff88;
  color: #00ff88;
}

.status.error {
  background: rgba(255, 0, 0, 0.1);
  border: 1px solid #ff4444;
  color: #ff4444;
}

.scan-card {
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.scan-card:hover {
  border-color: #00ff88;
}

.scan-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.scan-framework {
  background: #0f3460;
  padding: 2px 8px;
  border-radius: 4px;
  color: #00ff88;
}

.scan-date {
  color: #888;
  font-size: 0.85em;
}

.scan-summary {
  display: flex;
  align-items: center;
  gap: 16px;
}

.score-ring {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.score-ring.excellent { border: 3px solid #00ff88; color: #00ff88; }
.score-ring.good { border: 3px solid #88ff00; color: #88ff00; }
.score-ring.fair { border: 3px solid #ffaa00; color: #ffaa00; }
.score-ring.poor { border: 3px solid #ff4444; color: #ff4444; }

.score-value {
  font-size: 1.1em;
}

.scan-details p {
  margin: 2px 0;
  font-size: 0.85em;
}

.empty-state {
  text-align: center;
  color: #666;
  padding: 40px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.score-display {
  text-align: center;
  padding: 12px 24px;
  border-radius: 8px;
  background: #0d1117;
}

.score-big {
  font-size: 2em;
  font-weight: bold;
  display: block;
}

.score-label {
  font-size: 0.85em;
  color: #888;
}

.score-display.excellent .score-big { color: #00ff88; }
.score-display.good .score-big { color: #88ff00; }
.score-display.fair .score-big { color: #ffaa00; }
.score-display.poor .score-big { color: #ff4444; }

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.summary-card {
  text-align: center;
  padding: 16px;
  border-radius: 6px;
  background: #0d1117;
}

.summary-card.pass { border-top: 3px solid #00ff88; }
.summary-card.fail { border-top: 3px solid #ff4444; }
.summary-card.warn { border-top: 3px solid #ffaa00; }
.summary-card.total { border-top: 3px solid #888; }

.summary-value {
  font-size: 2em;
  font-weight: bold;
  display: block;
}

.summary-card.pass .summary-value { color: #00ff88; }
.summary-card.fail .summary-value { color: #ff4444; }
.summary-card.warn .summary-value { color: #ffaa00; }
.summary-card.total .summary-value { color: #888; }

.summary-label {
  font-size: 0.85em;
  color: #888;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-bar select {
  padding: 8px;
  background: #0d1117;
  border: 1px solid #333;
  color: #e0e0e0;
  border-radius: 4px;
}

.result-card {
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  border-left: 3px solid #333;
}

.result-card.pass { border-left-color: #00ff88; }
.result-card.fail { border-left-color: #ff4444; }
.result-card.warning { border-left-color: #ffaa00; }

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.result-id {
  color: #888;
  font-size: 0.85em;
}

.severity-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75em;
  text-transform: uppercase;
}

.severity-badge.critical { background: #ff4444; color: #fff; }
.severity-badge.high { background: #ff8800; color: #000; }
.severity-badge.medium { background: #ffaa00; color: #000; }
.severity-badge.low { background: #88ff00; color: #000; }

.result-title {
  font-weight: bold;
  margin-bottom: 4px;
}

.result-output {
  background: #111;
  padding: 6px 8px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.85em;
  margin-top: 4px;
}

.result-remediation {
  background: rgba(0, 100, 255, 0.1);
  border: 1px solid #0066ff;
  padding: 8px;
  border-radius: 4px;
  margin-top: 8px;
  font-size: 0.85em;
}

.framework-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.framework-card {
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 16px;
}

.framework-card h3 {
  color: #00ff88;
  margin-bottom: 4px;
}
</style>
