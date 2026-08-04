<template>
  <div class="logs-view">
    <div class="header">
      <h1>📜 Log Aggregation</h1>
      <p class="subtitle">Centralized logging from all managed nodes</p>
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

    <!-- Live Logs -->
    <div v-if="activeTab === 'live'" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <h2>Live Log Viewer</h2>
          <button @click="refreshLogs" :disabled="fetching" class="btn-secondary">
            {{ fetching ? '⏳' : '🔄' }} Refresh
          </button>
        </div>
        <div class="filter-bar">
          <select v-model="selectedNode">
            <option value="">All Nodes</option>
            <option v-for="node in nodes" :key="node.id" :value="node.id">
              {{ node.name }}
            </option>
          </select>
          <select v-model="logType">
            <option value="journalctl">Systemd Journal</option>
            <option value="syslog">Syslog</option>
            <option value="auth">Auth Log</option>
            <option value="kern">Kernel Log</option>
            <option value="dmesg">Dmesg</option>
          </select>
          <select v-model="severityFilter">
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High/Error</option>
            <option value="medium">Warning</option>
            <option value="info">Info</option>
          </select>
          <input v-model="searchQuery" type="text" placeholder="Filter logs..." class="search-input" />
        </div>
        <div class="log-container" ref="logContainer" @mouseup="handleTextSelection">
          <div v-for="(entry, idx) in filteredLogs" :key="idx" :class="['log-entry', entry.severity || 'info']">
            <span class="log-node">{{ entry.node_id }}</span>
            <span class="log-type">[{{ entry.log_type }}]</span>
            <span class="log-process" v-if="entry.process">{{ entry.process }}</span>
            <span class="log-message">{{ entry.raw }}</span>
          </div>
          <div v-if="filteredLogs.length === 0" class="empty-state">
            No logs to display. Click Refresh to fetch from nodes.
          </div>
        </div>
      </div>

      <!-- AI Parse Menu -->
      <div v-if="showParseMenu" class="parse-menu" :style="{ left: menuPosition.x + 'px', top: menuPosition.y + 'px' }">
        <button @click="executeAIParse" class="btn-ai-parse">
          ⚡ AI Parse Selected Field
        </button>
      </div>

      <!-- AI Parse Result Modal -->
      <div v-if="parseResult || parsingLog" class="parse-modal-overlay" @click.self="parseResult = null; parsingLog = false">
        <div class="parse-modal">
          <div class="modal-header">
            <h3>⚡ AI Log Parser</h3>
            <button class="btn-close" @click="parseResult = null; parsingLog = false">✕</button>
          </div>

          <div v-if="parsingLog" class="parsing-loader">
            <span class="spinner">🌀</span> Analyzing log structure...
          </div>

          <div v-if="parseResult" class="parse-result-content">
            <div class="result-section">
              <h4>Generated Regex/Grok Pattern</h4>
              <div class="code-block">{{ parseResult.pattern }}</div>
            </div>

            <div class="result-section">
              <h4>Explanation</h4>
              <p>{{ parseResult.explanation }}</p>
            </div>

            <div class="result-section">
              <h4>Extracted Fields Preview</h4>
              <table class="extraction-table">
                <thead>
                  <tr>
                    <th>Field Name</th>
                    <th>Extracted Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(value, key) in parseResult.extracted_fields" :key="key">
                    <td class="field-key">{{ key }}</td>
                    <td class="field-value">{{ value }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="modal-actions">
              <button class="btn-primary">Save Pipeline Rule</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Search -->
    <div v-if="activeTab === 'search'" class="tab-content">
      <div class="panel">
        <h2>Search Logs</h2>
        <div class="search-form">
          <div class="form-group">
            <label>Search Query</label>
            <input v-model="searchQueryFull" type="text" placeholder="Enter search term..." />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Node</label>
              <select v-model="searchNodeId">
                <option value="">All Nodes</option>
                <option v-for="node in nodes" :key="node.id" :value="node.id">
                  {{ node.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>Log Type</label>
              <select v-model="searchLogType">
                <option value="">All Types</option>
                <option value="journalctl">Journal</option>
                <option value="syslog">Syslog</option>
                <option value="auth">Auth</option>
              </select>
            </div>
            <div class="form-group">
              <label>Severity</label>
              <select v-model="searchSeverity">
                <option value="">All</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="info">Info</option>
              </select>
            </div>
          </div>
          <button @click="performSearch" :disabled="searching" class="btn-primary">
            {{ searching ? '⏳ Searching...' : '🔍 Search' }}
          </button>
        </div>
      </div>

      <div v-if="searchResults.length > 0" class="panel">
        <h3>Search Results ({{ searchResults.length }})</h3>
        <div class="log-container">
          <div v-for="(entry, idx) in searchResults" :key="idx" :class="['log-entry', entry.severity || 'info']">
            <span class="log-node">{{ entry.node_id }}</span>
            <span class="log-type">[{{ entry.log_type }}]</span>
            <span class="log-message">{{ entry.raw }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Statistics -->
    <div v-if="activeTab === 'stats'" class="tab-content">
      <div class="panel">
        <h2>Log Statistics</h2>
        <button @click="loadStats" class="btn-secondary">Refresh Stats</button>
        <div class="stats-grid" v-if="stats">
          <div class="stat-card">
            <span class="stat-value">{{ stats.total_entries }}</span>
            <span class="stat-label">Total Entries</span>
          </div>
        </div>

        <div class="stats-section" v-if="stats?.by_node">
          <h3>By Node</h3>
          <div class="stats-bar">
            <div v-for="(count, node) in stats.by_node" :key="node" class="stat-bar-item">
              <span class="bar-label">{{ node }}</span>
              <div class="bar-fill" :style="{ width: getBarWidth(count, stats.total_entries) }"></div>
              <span class="bar-count">{{ count }}</span>
            </div>
          </div>
        </div>

        <div class="stats-section" v-if="stats?.by_type">
          <h3>By Log Type</h3>
          <div class="stats-bar">
            <div v-for="(count, type) in stats.by_type" :key="type" class="stat-bar-item">
              <span class="bar-label">{{ type }}</span>
              <div class="bar-fill type" :style="{ width: getBarWidth(count, stats.total_entries) }"></div>
              <span class="bar-count">{{ count }}</span>
            </div>
          </div>
        </div>

        <div class="stats-section" v-if="stats?.by_severity">
          <h3>By Severity</h3>
          <div class="stats-bar">
            <div v-for="(count, sev) in stats.by_severity" :key="sev" class="stat-bar-item">
              <span class="bar-label">{{ sev }}</span>
              <div :class="['bar-fill', sev]" :style="{ width: getBarWidth(count, stats.total_entries) }"></div>
              <span class="bar-count">{{ count }}</span>
            </div>
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
  { id: 'live', label: 'Live Logs', icon: '📜' },
  { id: 'search', label: 'Search', icon: '🔍' },
  { id: 'stats', label: 'Statistics', icon: '📊' },
]

const activeTab = ref('live')
const nodes = ref<any[]>([])
const logs = ref<any[]>([])
const stats = ref<any>(null)
const selectedNode = ref('')
const logType = ref('journalctl')
const severityFilter = ref('')
const searchQuery = ref('')
const searchQueryFull = ref('')
const searchNodeId = ref('')
const searchLogType = ref('')
const searchSeverity = ref('')
const searchResults = ref<any[]>([])
const fetching = ref(false)
const searching = ref(false)

// AI Parse State
const showParseMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })
const selectedText = ref('')
const selectedLogEntry = ref('')
const parseResult = ref<any>(null)
const parsingLog = ref(false)

const filteredLogs = computed(() => {
  return logs.value.filter(entry => {
    if (severityFilter.value && entry.severity !== severityFilter.value) return false
    if (searchQuery.value && !entry.raw?.toLowerCase().includes(searchQuery.value.toLowerCase())) return false
    return true
  })
})

onMounted(async () => {
  try {
    const nodesRes = await api.get('/nodes')
    nodes.value = Object.values(nodesRes.data || {})
  } catch (e) {
    console.error('Failed to load nodes', e)
  }
  await loadStats()
})

async function refreshLogs() {
  fetching.value = true
  try {
    if (selectedNode.value) {
      const res = await api.get(`/logs/${selectedNode.value}`, { params: { log_type: logType.value, lines: 200 } })
      logs.value = res.data?.entries || []
    } else {
      const res = await api.get('/logs/recent', { params: { limit: 200 } })
      logs.value = res.data?.entries || []
    }
  } catch (e) {
    console.error('Failed to fetch logs', e)
  } finally {
    fetching.value = false
  }
}

async function performSearch() {
  searching.value = true
  searchResults.value = []
  try {
    const res = await api.post('/logs/search', {
      query: searchQueryFull.value,
      node_id: searchNodeId.value || undefined,
      log_type: searchLogType.value || undefined,
      severity: searchSeverity.value || undefined,
      limit: 200,
    })
    searchResults.value = res.data?.entries || []
  } catch (e) {
    console.error('Search failed', e)
  } finally {
    searching.value = false
  }
}

async function loadStats() {
  try {
    const res = await api.get('/logs/stats')
    stats.value = res.data
  } catch (e) {
    console.error('Failed to load stats', e)
  }
}

function getBarWidth(count: number, total: number) {
  return `${Math.max(5, (count / total) * 100)}%`
}

function handleTextSelection(e: MouseEvent) {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) {
    showParseMenu.value = false
    return
  }

  const text = selection.toString().trim()
  if (text.length === 0) return

  let target = e.target as HTMLElement
  const logRow = target.closest('.log-entry')
  if (logRow) {
    const rawMsgEl = logRow.querySelector('.log-message')
    if (rawMsgEl) {
      selectedLogEntry.value = rawMsgEl.textContent || ''
      selectedText.value = text

      menuPosition.value = {
        x: e.pageX,
        y: e.pageY + 10
      }
      showParseMenu.value = true
    }
  }
}

async function executeAIParse() {
  showParseMenu.value = false
  parsingLog.value = true
  parseResult.value = null

  try {
    const res = await api.parseLog(selectedLogEntry.value, selectedText.value)
    // res is the response body directly because our req() returns it
    parseResult.value = res.data || res
  } catch(e) {
    console.error("AI Parse failed", e)
  } finally {
    parsingLog.value = false
  }
}
</script>

<style scoped>
.logs-view {
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

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel h2 {
  color: #00ff88;
  margin-bottom: 16px;
}

.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.filter-bar select,
.filter-bar input {
  padding: 8px;
  background: #0d1117;
  border: 1px solid #333;
  color: #e0e0e0;
  border-radius: 4px;
}

.search-input {
  flex: 1;
}

.log-container {
  background: #0d1117;
  border: 1px solid #222;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
  font-family: 'Fira Code', monospace;
  font-size: 0.85em;
}

.log-entry {
  padding: 4px 8px;
  border-bottom: 1px solid #1a1a1a;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.log-entry:hover {
  background: #111;
}

.log-entry.critical {
  border-left: 3px solid #ff4444;
  background: rgba(255, 0, 0, 0.05);
}

.log-entry.high {
  border-left: 3px solid #ff8800;
}

.log-entry.medium {
  border-left: 3px solid #ffaa00;
}

.log-node {
  color: #00ff88;
  min-width: 80px;
}

.log-type {
  color: #888;
  min-width: 80px;
}

.log-process {
  color: #88ff00;
  min-width: 60px;
}

.log-message {
  flex: 1;
  word-break: break-all;
}

.empty-state {
  text-align: center;
  color: #666;
  padding: 40px;
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

.btn-secondary {
  padding: 8px 16px;
  background: #0f3460;
  color: #00ff88;
  border: 1px solid #00ff88;
  border-radius: 4px;
  cursor: pointer;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  color: #aaa;
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

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  font-size: 2em;
  font-weight: bold;
  color: #00ff88;
  display: block;
}

.stat-label {
  font-size: 0.85em;
  color: #888;
}

.stats-section {
  margin-bottom: 20px;
}

.stats-section h3 {
  color: #00ff88;
  margin-bottom: 8px;
}

.stat-bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.bar-label {
  min-width: 100px;
  color: #aaa;
}

.bar-fill {
  height: 20px;
  background: #00ff88;
  border-radius: 4px;
  min-width: 5px;
  transition: width 0.3s;
}

.bar-fill.type {
  background: #88ff00;
}

.bar-fill.critical {
  background: #ff4444;
}

.bar-fill.high {
  background: #ff8800;
}

.bar-fill.medium {
  background: #ffaa00;
}

.bar-fill.info {
  background: #00aaff;
}

.bar-fill.debug {
  background: #888;
}

.bar-count {
  min-width: 40px;
  text-align: right;
  color: #888;
}

/* AI Parse Styles */
.parse-menu {
  position: absolute;
  z-index: 100;
  background: rgba(15, 20, 25, 0.95);
  border: 1px solid var(--cyan);
  border-radius: 6px;
  padding: 5px;
  box-shadow: 0 4px 15px rgba(0, 255, 204, 0.2);
  transform: translateX(-50%);
}

.btn-ai-parse {
  background: transparent;
  border: none;
  color: var(--cyan);
  cursor: pointer;
  padding: 8px 12px;
  font-weight: bold;
  font-family: 'Inter', sans-serif;
  transition: all 0.2s;
}

.btn-ai-parse:hover {
  background: rgba(0, 255, 204, 0.1);
  border-radius: 4px;
}

.parse-modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.parse-modal {
  background: #1a1a2e;
  border: 1px solid var(--cyan);
  border-radius: 8px;
  width: 600px;
  max-width: 90vw;
  box-shadow: 0 0 30px rgba(0, 255, 204, 0.15);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid #333;
}

.modal-header h3 {
  margin: 0;
  color: var(--cyan);
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-close {
  background: transparent;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 1.2rem;
}

.btn-close:hover {
  color: #fff;
}

.parsing-loader {
  padding: 40px;
  text-align: center;
  color: #00ff88;
  font-weight: bold;
  font-size: 1.1rem;
}

.spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
  margin-right: 10px;
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

.parse-result-content {
  padding: 20px;
}

.result-section {
  margin-bottom: 20px;
}

.result-section h4 {
  margin: 0 0 10px 0;
  color: #aaa;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.code-block {
  background: #0d1117;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  color: #00ff88;
  border: 1px solid #333;
  word-break: break-all;
}

.extraction-table {
  width: 100%;
  border-collapse: collapse;
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 4px;
}

.extraction-table th, .extraction-table td {
  padding: 10px 15px;
  text-align: left;
  border-bottom: 1px solid #222;
}

.extraction-table th {
  background: rgba(255, 255, 255, 0.05);
  color: #888;
  font-weight: normal;
  font-size: 0.85rem;
}

.field-key {
  color: #00aaff;
  font-weight: bold;
  font-family: monospace;
}

.field-value {
  color: #e0e0e0;
  font-family: monospace;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #333;
}
</style>
