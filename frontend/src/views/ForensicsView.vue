<template>
  <div class="forensics-view">
    <div class="header">
      <h1>🔬 Forensics Lab</h1>
      <p class="subtitle">Memory & Disk Forensics with Volatility3 Integration</p>
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

    <!-- Evidence Board -->
    <div v-if="activeTab === 'evidence'" class="tab-content">
      <div class="panel">
        <h2>Evidence Board</h2>
        <div class="evidence-grid">
          <div v-for="item in evidence" :key="item.id" class="evidence-card">
            <div class="evidence-header">
              <span class="evidence-type">{{ item.type }}</span>
              <span class="evidence-id">{{ item.id }}</span>
            </div>
            <div class="evidence-details">
              <p><strong>Source:</strong> {{ item.source_host }}</p>
              <p><strong>Method:</strong> {{ item.method }}</p>
              <p><strong>Size:</strong> {{ formatSize(item.file_size) }}</p>
              <p><strong>SHA256:</strong> {{ item.sha256?.substring(0, 16) }}...</p>
              <p><strong>Acquired:</strong> {{ formatDate(item.acquired_at) }}</p>
            </div>
            <div class="evidence-actions">
              <button @click="selectEvidence(item)" class="btn-small">Select</button>
            </div>
          </div>
          <div v-if="evidence.length === 0" class="empty-state">
            No evidence collected yet. Use Memory Dump to acquire evidence.
          </div>
        </div>
      </div>
    </div>

    <!-- Memory Acquisition -->
    <div v-if="activeTab === 'acquire'" class="tab-content">
      <div class="panel">
        <h2>Memory Dump Acquisition</h2>
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
          <label>Acquisition Method</label>
          <select v-model="acquireMethod">
            <option value="lime">LiME (Recommended)</option>
            <option value="dd">Direct dd dump</option>
            <option value="proc">/proc/kcore (Limited)</option>
          </select>
        </div>
        <div class="method-info">
          <div v-if="acquireMethod === 'lime'">
            <p><strong>LiME</strong> — Most reliable method. Requires kernel headers and gcc on target.</p>
          </div>
          <div v-else-if="acquireMethod === 'dd'">
            <p><strong>Direct dump</strong> — Uses dd to read /dev/mem. Requires root.</p>
          </div>
          <div v-else>
            <p><strong>/proc/kcore</strong> — Limited kernel memory. Not a full dump.</p>
          </div>
        </div>
        <button
          @click="acquireMemory"
          :disabled="!selectedNode || acquiring"
          class="btn-primary"
        >
          {{ acquiring ? '⏳ Acquiring...' : '📥 Start Memory Dump' }}
        </button>
        <div v-if="acquireStatus" :class="['status', acquireStatus.type]">
          {{ acquireStatus.message }}
        </div>
      </div>
    </div>

    <!-- Volatility Analysis -->
    <div v-if="activeTab === 'volatility'" class="tab-content">
      <div class="panel">
        <h2>Volatility3 Analysis</h2>
        <div class="form-group">
          <label>Evidence</label>
          <select v-model="selectedEvidenceId">
            <option value="">Select evidence...</option>
            <option v-for="item in evidence" :key="item.id" :value="item.id">
              {{ item.id }} — {{ item.type }} ({{ item.source_host }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Plugin</label>
          <select v-model="selectedPlugin">
            <optgroup v-for="(plugins, platform) in volPlugins" :key="platform" :label="platform">
              <option v-for="p in plugins" :key="p.name" :value="p.name">
                {{ p.name }} — {{ p.description }}
              </option>
            </optgroup>
          </select>
        </div>
        <div class="form-group">
          <label>Extra Arguments (optional)</label>
          <input v-model="extraArgs" type="text" placeholder="--pid 1234" />
        </div>
        <button
          @click="runVolatility"
          :disabled="!selectedEvidenceId || !selectedPlugin || analyzing"
          class="btn-primary"
        >
          {{ analyzing ? '⏳ Analyzing...' : '🔍 Run Plugin' }}
        </button>
      </div>

      <!-- Volatility Results -->
      <div v-if="volResults" class="panel results-panel">
        <h3>Results: {{ volResults.plugin }}</h3>
        <div class="results-table-wrapper">
          <table v-if="volResults.parsed && volResults.parsed.length > 0" class="results-table">
            <thead>
              <tr>
                <th v-for="key in Object.keys(volResults.parsed[0])" :key="key">{{ key }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in volResults.parsed" :key="idx">
                <td v-for="(val, key) in row" :key="key">{{ val }}</td>
              </tr>
            </tbody>
          </table>
          <pre v-else class="raw-output">{{ volResults.output }}</pre>
        </div>
      </div>
    </div>

    <!-- Disk Analysis -->
    <div v-if="activeTab === 'disk'" class="tab-content">
      <div class="panel">
        <h2>Disk Image Analysis</h2>
        <div class="form-group">
          <label>Disk Image Path</label>
          <input v-model="diskImagePath" type="text" placeholder="/path/to/disk.img" />
        </div>
        <button
          @click="analyzeDisk"
          :disabled="!diskImagePath || diskAnalyzing"
          class="btn-primary"
        >
          {{ diskAnalyzing ? '⏳ Analyzing...' : '💿 Analyze Disk Image' }}
        </button>
      </div>

      <div v-if="diskResults" class="panel results-panel">
        <h3>Disk Analysis Results</h3>
        <div class="disk-info">
          <p><strong>SHA256:</strong> {{ diskResults.results?.sha256 }}</p>
          <p><strong>Size:</strong> {{ formatSize(diskResults.results?.file_size) }}</p>
        </div>
        <div v-if="diskResults.results?.file_system" class="file-tree">
          <h4>File System</h4>
          <div v-for="entry in diskResults.results.file_system" :key="entry.name" class="file-entry">
            <span class="file-meta">{{ entry.metadata }}</span>
            <span class="file-name">{{ entry.name }}</span>
          </div>
        </div>
        <div v-if="diskResults.results?.disk_layout" class="disk-layout">
          <h4>Disk Layout</h4>
          <pre>{{ diskResults.results.disk_layout }}</pre>
        </div>
      </div>
    </div>

    <!-- Timeline -->
    <div v-if="activeTab === 'timeline'" class="tab-content">
      <div class="panel">
        <h2>Timeline Analysis</h2>
        <div class="form-group">
          <label>Select Evidence for Timeline</label>
          <div class="checkbox-group">
            <label v-for="item in evidence" :key="item.id" class="checkbox-label">
              <input type="checkbox" :value="item.id" v-model="timelineEvidenceIds" />
              {{ item.id }} — {{ item.type }}
            </label>
          </div>
        </div>
        <button
          @click="generateTimeline"
          :disabled="timelineEvidenceIds.length === 0 || timelineGenerating"
          class="btn-primary"
        >
          {{ timelineGenerating ? '⏳ Generating...' : '📅 Generate Timeline' }}
        </button>
      </div>

      <div v-if="timelineResults" class="panel results-panel">
        <h3>Timeline ({{ timelineResults.event_count }} events)</h3>
        <div class="timeline">
          <div v-for="(event, idx) in timelineResults.events" :key="idx" class="timeline-event">
            <div class="event-time">{{ event.timestamp }}</div>
            <div class="event-type">{{ event.type }}</div>
            <div class="event-source">{{ event.source }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const tabs = [
  { id: 'evidence', label: 'Evidence Board', icon: '📋' },
  { id: 'acquire', label: 'Memory Dump', icon: '📥' },
  { id: 'volatility', label: 'Volatility', icon: '🔍' },
  { id: 'disk', label: 'Disk Analysis', icon: '💿' },
  { id: 'timeline', label: 'Timeline', icon: '📅' },
]

const activeTab = ref('evidence')
const nodes = ref<any[]>([])
const evidence = ref<any[]>([])
const selectedNode = ref('')
const acquireMethod = ref('lime')
const acquiring = ref(false)
const acquireStatus = ref<{ type: string; message: string } | null>(null)

const selectedEvidenceId = ref('')
const selectedPlugin = ref('linux.pslist')
const extraArgs = ref('')
const analyzing = ref(false)
const volResults = ref<any>(null)
const volPlugins = ref<any>({})

const diskImagePath = ref('')
const diskAnalyzing = ref(false)
const diskResults = ref<any>(null)

const timelineEvidenceIds = ref<string[]>([])
const timelineGenerating = ref(false)
const timelineResults = ref<any>(null)

onMounted(async () => {
  try {
    const nodesRes = await api.get('/nodes')
    nodes.value = nodesRes.data?.nodes || []
  } catch (e) {
    console.error('Failed to load nodes', e)
  }

  try {
    const evRes = await api.get('/forensics/evidence')
    evidence.value = evRes.data?.evidence || []
  } catch (e) {
    console.error('Failed to load evidence', e)
  }

  try {
    const pluginRes = await api.get('/forensics/plugins')
    volPlugins.value = pluginRes.data?.plugins || {}
  } catch (e) {
    console.error('Failed to load plugins', e)
  }
})

async function acquireMemory() {
  acquiring.value = true
  acquireStatus.value = null
  try {
    const res = await api.post('/forensics/memory-dump', {
      node_id: selectedNode.value,
      method: acquireMethod.value,
    })
    acquireStatus.value = { type: 'success', message: `Memory dump acquired: ${res.data.evidence_id}` }
    const evRes = await api.get('/forensics/evidence')
    evidence.value = evRes.data?.evidence || []
  } catch (e: any) {
    acquireStatus.value = { type: 'error', message: e.response?.data?.detail || 'Failed' }
  } finally {
    acquiring.value = false
  }
}

function selectEvidence(item: any) {
  selectedEvidenceId.value = item.id
  activeTab.value = 'volatility'
}

async function runVolatility() {
  analyzing.value = true
  volResults.value = null
  try {
    const res = await api.post('/forensics/volatility', {
      evidence_id: selectedEvidenceId.value,
      plugin: selectedPlugin.value,
      extra_args: extraArgs.value,
    })
    volResults.value = res.data
  } catch (e: any) {
    volResults.value = { output: e.response?.data?.detail || 'Analysis failed' }
  } finally {
    analyzing.value = false
  }
}

async function analyzeDisk() {
  diskAnalyzing.value = true
  diskResults.value = null
  try {
    const res = await api.post('/forensics/disk-analysis', {
      image_path: diskImagePath.value,
    })
    diskResults.value = res.data
  } catch (e: any) {
    diskResults.value = { error: e.response?.data?.detail || 'Analysis failed' }
  } finally {
    diskAnalyzing.value = false
  }
}

async function generateTimeline() {
  timelineGenerating.value = true
  timelineResults.value = null
  try {
    const res = await api.post('/forensics/timeline', {
      evidence_ids: timelineEvidenceIds.value,
    })
    timelineResults.value = res.data
  } catch (e: any) {
    timelineResults.value = { error: e.response?.data?.detail || 'Timeline generation failed' }
  } finally {
    timelineGenerating.value = false
  }
}

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleString()
}
</script>

<style scoped>
.forensics-view {
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
  transition: all 0.2s;
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
  font-size: 0.9em;
}

.form-group select,
.form-group input {
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
  cursor: not-allowed;
}

.btn-small {
  padding: 4px 12px;
  background: #0f3460;
  color: #00ff88;
  border: 1px solid #00ff88;
  border-radius: 4px;
  cursor: pointer;
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

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.evidence-card {
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 12px;
}

.evidence-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.evidence-type {
  background: #0f3460;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  color: #00ff88;
}

.evidence-id {
  color: #888;
  font-size: 0.8em;
}

.evidence-details p {
  margin: 4px 0;
  font-size: 0.85em;
}

.evidence-actions {
  margin-top: 8px;
}

.empty-state {
  text-align: center;
  color: #666;
  padding: 40px;
}

.results-panel {
  max-height: 600px;
  overflow-y: auto;
}

.results-table-wrapper {
  overflow-x: auto;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table th {
  background: #0f3460;
  padding: 8px;
  text-align: left;
  color: #00ff88;
  font-size: 0.85em;
}

.results-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #222;
  font-size: 0.85em;
}

.raw-output {
  background: #0d1117;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.85em;
  white-space: pre-wrap;
}

.method-info {
  background: #0d1117;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  border-left: 3px solid #00ff88;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.timeline {
  position: relative;
  padding-left: 20px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #333;
}

.timeline-event {
  position: relative;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #0d1117;
  border-radius: 4px;
  border-left: 3px solid #0f3460;
}

.timeline-event::before {
  content: '';
  position: absolute;
  left: -16px;
  top: 12px;
  width: 8px;
  height: 8px;
  background: #00ff88;
  border-radius: 50%;
}

.event-time {
  font-size: 0.8em;
  color: #888;
}

.event-type {
  color: #00ff88;
  font-weight: bold;
}

.event-source {
  font-size: 0.85em;
  color: #aaa;
}
</style>
