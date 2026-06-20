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
        <div class="log-container" ref="logContainer">
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
    nodes.value = nodesRes.data?.nodes || []
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
</style>
