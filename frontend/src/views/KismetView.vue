<template>
  <div class="kismet-container">
    <!-- Header -->
    <div class="header">
      <div class="header-left">
        <h2><span class="glitch-text" data-text="WIRELESS">WIRELESS</span> IDS</h2>
        <p class="subtitle">Kismet Network Detection & Threat Monitoring</p>
      </div>
      <div class="header-right">
        <div class="status-badge" :class="{ active: kismetStatus.running }">
          <span class="status-dot"></span>
          {{ kismetStatus.running ? 'KISMET ACTIVE' : 'KISMET OFFLINE' }}
        </div>
      </div>
    </div>

    <!-- Control Bar -->
    <div class="control-bar">
      <div class="control-group">
        <label>Interface</label>
        <select v-model="selectedInterface" :disabled="kismetStatus.running">
          <option value="">Select interface...</option>
          <option v-for="iface in interfaces" :key="iface.name" :value="iface.name">
            {{ iface.name }} ({{ iface.driver }})
          </option>
          <option value="wlan0">wlan0 (manual)</option>
        </select>
      </div>
      <div class="control-group">
        <label>HTTP Port</label>
        <input type="number" v-model.number="httpPort" :disabled="kismetStatus.running" />
      </div>
      <div class="control-actions">
        <button v-if="!kismetStatus.running" class="cyber-button primary" @click="startKismet" :disabled="starting">
          <span v-if="starting" class="spinner"></span>
          <span v-else>▶ START KISMET</span>
        </button>
        <button v-else class="cyber-button danger" @click="stopKismet">
          ■ STOP KISMET
        </button>
        <button class="cyber-button secondary" @click="refreshInterfaces">↻ Refresh</button>
      </div>
      <div class="status-info">
        <span v-if="kismetStatus.pid">PID: {{ kismetStatus.pid }}</span>
        <span v-if="kismetStatus.interface">Interface: {{ kismetStatus.interface }}</span>
        <span :class="['api-indicator', kismetStatus.api_reachable ? 'up' : 'down']">
          API: {{ kismetStatus.api_reachable ? 'CONNECTED' : 'UNREACHABLE' }}
        </span>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tab-bar">
      <button v-for="tab in tabs" :key="tab.id" class="tab" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
        {{ tab.icon }} {{ tab.label }}
        <span v-if="tab.id === 'alerts' && alerts.length" class="badge">{{ alerts.length }}</span>
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <!-- Networks Tab -->
      <div v-if="activeTab === 'networks'" class="networks-panel">
        <div class="panel-toolbar">
          <input v-model="networkFilter" placeholder="Filter networks..." class="filter-input" />
          <span class="count">{{ filteredNetworks.length }} networks</span>
        </div>
        <div class="table-container">
          <table class="cyber-table">
            <thead>
              <tr>
                <th>SSID</th>
                <th>BSSID</th>
                <th>Channel</th>
                <th>Signal</th>
                <th>Encryption</th>
                <th>Manufacturer</th>
                <th>Packets</th>
                <th>Alerts</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="net in filteredNetworks" :key="net.mac" :class="{ 'alert-row': net.alerts > 0 }">
                <td class="ssid-cell">
                  <span class="ssid-text">{{ net.ssid || '[Hidden]' }}</span>
                </td>
                <td class="mono">{{ net.mac }}</td>
                <td>{{ net.channel }}</td>
                <td>
                  <div class="signal-bar">
                    <div class="signal-fill" :style="{ width: signalPercent(net.signal_dbm) + '%' }" :class="signalClass(net.signal_dbm)"></div>
                    <span class="signal-text">{{ net.signal_dbm }} dBm</span>
                  </div>
                </td>
                <td>
                  <span class="crypt-badge" :class="cryptClass(net.crypt)">{{ net.crypt || 'Open' }}</span>
                </td>
                <td>{{ net.manufacturer }}</td>
                <td class="mono">{{ net.packets.toLocaleString() }}</td>
                <td>
                  <span v-if="net.alerts > 0" class="alert-badge">{{ net.alerts }}</span>
                  <span v-else>—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Clients Tab -->
      <div v-if="activeTab === 'clients'" class="clients-panel">
        <div class="panel-toolbar">
          <input v-model="clientFilter" placeholder="Filter clients..." class="filter-input" />
          <span class="count">{{ filteredClients.length }} clients</span>
        </div>
        <div class="table-container">
          <table class="cyber-table">
            <thead>
              <tr>
                <th>MAC Address</th>
                <th>Name</th>
                <th>Channel</th>
                <th>Signal</th>
                <th>Manufacturer</th>
                <th>Packets</th>
                <th>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="client in filteredClients" :key="client.mac">
                <td class="mono">{{ client.mac }}</td>
                <td>{{ client.name || '—' }}</td>
                <td>{{ client.channel }}</td>
                <td>
                  <div class="signal-bar">
                    <div class="signal-fill" :style="{ width: signalPercent(client.signal_dbm) + '%' }" :class="signalClass(client.signal_dbm)"></div>
                    <span class="signal-text">{{ client.signal_dbm }} dBm</span>
                  </div>
                </td>
                <td>{{ client.manufacturer }}</td>
                <td class="mono">{{ client.packets.toLocaleString() }}</td>
                <td>{{ timeAgo(client.last_seen) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Alerts Tab -->
      <div v-if="activeTab === 'alerts'" class="alerts-panel">
        <div class="panel-toolbar">
          <button class="cyber-button secondary small" @click="clearAlerts">Clear Displayed</button>
          <span class="count">{{ alerts.length }} alerts</span>
        </div>
        <div class="alerts-list">
          <div v-for="(alert, idx) in alerts" :key="idx" class="alert-card" :class="severityClass(alert.severity)">
            <div class="alert-header">
              <span class="alert-type">{{ alert.type }}</span>
              <span class="alert-severity">{{ severityLabel(alert.severity) }}</span>
              <span class="alert-time">{{ timeAgo(alert.timestamp) }}</span>
            </div>
            <div class="alert-body">
              <div class="alert-message">{{ alert.message }}</div>
              <div v-if="alert.mac" class="alert-mac">Source: {{ alert.mac }}</div>
              <div v-if="alert.phy" class="alert-phy">Phy: {{ alert.phy }}</div>
            </div>
          </div>
          <div v-if="alerts.length === 0" class="empty-state">
            No alerts detected. System is clear.
          </div>
        </div>
      </div>

      <!-- Channels Tab -->
      <div v-if="activeTab === 'channels'" class="channels-panel">
        <div class="panel-toolbar">
          <span class="count">{{ Object.keys(channels).length }} channels</span>
        </div>
        <div class="channels-grid">
          <div v-for="(chData, chName) in channels" :key="chName" class="channel-card">
            <div class="channel-header">
              <span class="channel-name">Ch {{ chName }}</span>
              <span class="channel-freq">{{ (chData.frequency / 1000).toFixed(1) }} GHz</span>
            </div>
            <div class="channel-stats">
              <div class="stat">
                <span class="stat-label">Devices</span>
                <span class="stat-value">{{ chData.devices }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">Packets</span>
                <span class="stat-value">{{ chData.packets_total.toLocaleString() }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">Data</span>
                <span class="stat-value">{{ chData.packets_data.toLocaleString() }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">Encrypted</span>
                <span class="stat-value">{{ chData.packets_crypt.toLocaleString() }}</span>
              </div>
            </div>
            <div class="channel-bar">
              <div class="bar-fill" :style="{ width: channelPercent(chData.packets_total) + '%' }"></div>
            </div>
          </div>
          <div v-if="Object.keys(channels).length === 0" class="empty-state">
            No channel data available. Start Kismet to begin monitoring.
          </div>
        </div>
      </div>

      <!-- Datasources Tab -->
      <div v-if="activeTab === 'datasources'" class="datasources-panel">
        <div class="table-container">
          <table class="cyber-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Interface</th>
                <th>Type</th>
                <th>Channel</th>
                <th>Status</th>
                <th>Packets</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="src in datasources" :key="src.uuid">
                <td>{{ src.name }}</td>
                <td class="mono">{{ src.interface }}</td>
                <td>{{ src.type }}</td>
                <td>{{ src.channel || 'Hopping' }}</td>
                <td>
                  <span class="status-badge small" :class="{ active: src.running }">
                    {{ src.running ? 'Running' : 'Stopped' }}
                  </span>
                </td>
                <td class="mono">{{ src.packets.toLocaleString() }}</td>
                <td>
                  <button class="action-btn" @click="lockChannel(src.uuid)" title="Lock to channel">Lock</button>
                  <button class="action-btn" @click="enableHop(src.uuid)" title="Enable hopping">Hop</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="datasources.length === 0" class="empty-state">
            No datasources found. Start Kismet to detect interfaces.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api, wsBase, wsTokenParam } from '@/api/client'

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const activeTab = ref('networks')
const tabs = [
  { id: 'networks', label: 'NETWORKS', icon: '📡' },
  { id: 'clients', label: 'CLIENTS', icon: '💻' },
  { id: 'alerts', label: 'ALERTS', icon: '🚨' },
  { id: 'channels', label: 'CHANNELS', icon: '📊' },
  { id: 'datasources', label: 'DATASOURCES', icon: '🔌' },
]

const kismetStatus = ref<{ running: boolean; api_reachable: boolean; pid: number | null; interface: string; host: string; port: number }>({
  running: false,
  api_reachable: false,
  pid: null,
  interface: '',
  host: '127.0.0.1',
  port: 2501,
})

const interfaces = ref<{ name: string; driver: string; monitor_mode: boolean }[]>([])
const selectedInterface = ref('wlan0')
const httpPort = ref(2501)
const starting = ref(false)

const networks = ref<any[]>([])
const clients = ref<any[]>([])
const alerts = ref<any[]>([])
const channels = ref<Record<string, any>>({})
const datasources = ref<any[]>([])

const networkFilter = ref('')
const clientFilter = ref('')

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------

let ws: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null

function connectWs() {
  if (ws) return
  const url = `${wsBase()}/ws/kismet${wsTokenParam()}`
  ws = new WebSocket(url)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'kismet_update') {
        if (data.networks) {
          // Full array override (fallback)
          networks.value = data.networks
        } else {
          // Delta updates
          if (data.networks_delta) {
            for (const net of data.networks_delta) {
              const idx = networks.value.findIndex(n => n.mac === net.mac)
              if (idx >= 0) networks.value[idx] = net
              else networks.value.push(net)
            }
          }
          if (data.alerts_delta) {
            for (const alt of data.alerts_delta) {
              alerts.value.unshift(alt) // add to top
            }
            if (alerts.value.length > 500) alerts.value.length = 500
          }
        }
        if (data.channels) channels.value = data.channels
      }
    } catch { /* non-fatal */ }
  }

  ws.onclose = () => {
    ws = null
    if (kismetStatus.value.running) {
      wsReconnectTimer = setTimeout(connectWs, 3000)
    }
  }

  ws.onerror = () => {
    ws?.close()
  }
}

function disconnectWs() {
  if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
  if (ws) ws.close()
  ws = null
}

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const filteredNetworks = computed(() => {
  const q = networkFilter.value.toLowerCase()
  let result = networks.value
  if (q) {
    result = networks.value.filter(n =>
      n.ssid.toLowerCase().includes(q) ||
      n.mac.toLowerCase().includes(q) ||
      n.manufacturer.toLowerCase().includes(q)
    )
  }
  // Soft virtual scrolling / pagination: only render top 100 to prevent DOM lag
  return result.slice(0, 100)
})

const filteredClients = computed(() => {
  const q = clientFilter.value.toLowerCase()
  let result = clients.value
  if (q) {
    result = clients.value.filter(c =>
      c.mac.toLowerCase().includes(q) ||
      (c.name || '').toLowerCase().includes(q) ||
      c.manufacturer.toLowerCase().includes(q)
    )
  }
  return result.slice(0, 100)
})

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

async function fetchStatus() {
  try {
    kismetStatus.value = await api.kismetStatus()
  } catch { /* non-fatal */ }
}

async function fetchInterfaces() {
  try {
    const res = await api.kismetInterfaces()
    interfaces.value = res.interfaces || []
  } catch { /* non-fatal */ }
}

async function startKismet() {
  starting.value = true
  try {
    await api.kismetStart({
      interface: selectedInterface.value || 'wlan0',
      http_port: httpPort.value,
    })
    await fetchStatus()
    connectWs()
    await refreshData()
  } catch (e: any) {
    alert('Failed to start Kismet: ' + (e.message || e))
  } finally {
    starting.value = false
  }
}

async function stopKismet() {
  try {
    await api.kismetStop()
    disconnectWs()
    await fetchStatus()
    networks.value = []
    clients.value = []
    alerts.value = []
    channels.value = {}
    datasources.value = []
  } catch (e: any) {
    alert('Failed to stop Kismet: ' + (e.message || e))
  }
}

async function refreshInterfaces() {
  await fetchInterfaces()
}

async function refreshData() {
  if (!kismetStatus.value.api_reachable) return
  try {
    const [netsRes, clientsRes, alertsRes, channelsRes, dsRes] = await Promise.all([
      api.kismetNetworks(),
      api.kismetClients(),
      api.kismetAlerts(),
      api.kismetChannels(),
      api.kismetDatasources(),
    ])
    networks.value = netsRes.networks || []
    clients.value = clientsRes.clients || []
    alerts.value = alertsRes.alerts || []
    channels.value = channelsRes.channels || {}
    datasources.value = dsRes.datasources || []
  } catch { /* non-fatal */ }
}

function clearAlerts() {
  alerts.value = []
}

async function lockChannel(uuid: string) {
  const ch = prompt('Enter channel number:')
  if (ch) {
    await api.kismetSetChannel(uuid, parseInt(ch))
    await refreshData()
  }
}

async function enableHop(uuid: string) {
  await api.kismetSetChannel(uuid)
  await refreshData()
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function signalPercent(dbm: number): number {
  // Map -100..0 dBm to 0..100%
  return Math.max(0, Math.min(100, (dbm + 100)))
}

function signalClass(dbm: number): string {
  if (dbm >= -50) return 'excellent'
  if (dbm >= -65) return 'good'
  if (dbm >= -75) return 'fair'
  return 'poor'
}

function cryptClass(crypt: string): string {
  if (!crypt || crypt.toLowerCase() === 'none') return 'open'
  if (crypt.includes('WPA3') || crypt.includes('SAE')) return 'wpa3'
  if (crypt.includes('WPA2')) return 'wpa2'
  if (crypt.includes('WPA')) return 'wpa'
  if (crypt.includes('WEP')) return 'wep'
  return 'encrypted'
}

function severityClass(sev: number): string {
  if (sev >= 15) return 'critical'
  if (sev >= 10) return 'high'
  if (sev >= 5) return 'medium'
  return 'low'
}

function severityLabel(sev: number): string {
  if (sev >= 15) return 'CRITICAL'
  if (sev >= 10) return 'HIGH'
  if (sev >= 5) return 'MEDIUM'
  return 'LOW'
}

function timeAgo(ts: number): string {
  if (!ts) return '—'
  const now = Date.now() / 1000
  const diff = now - ts
  if (diff < 0) return 'just now'
  if (diff < 60) return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function channelPercent(packets: number): number {
  const maxPackets = Math.max(1, ...Object.values(channels.value).map((c: any) => c.packets_total || 0))
  return (packets / maxPackets) * 100
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await fetchStatus()
  await fetchInterfaces()

  if (kismetStatus.value.running && kismetStatus.value.api_reachable) {
    connectWs()
    await refreshData()
  }

  refreshTimer = setInterval(async () => {
    await fetchStatus()
    if (kismetStatus.value.api_reachable) {
      await refreshData()
    }
  }, 5000)
})

onUnmounted(() => {
  disconnectWs()
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.kismet-container {
  padding: 1.5rem;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 1rem;
}

.header h2 {
  font-family: var(--font-hd);
  color: var(--cyan);
  margin: 0;
  font-size: 1.5rem;
  letter-spacing: 2px;
}

.header .subtitle {
  color: var(--textbr);
  font-family: var(--font-co);
  font-size: 0.75rem;
  letter-spacing: 1px;
  margin-top: 4px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-co);
  font-size: 0.75rem;
  letter-spacing: 1px;
  padding: 6px 12px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--textbr);
}

.status-badge.active {
  color: var(--green);
  border-color: var(--green);
  background: rgba(0, 255, 157, 0.1);
}

.status-badge .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--textbr);
}

.status-badge.active .status-dot {
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
}

.status-badge.small {
  font-size: 0.65rem;
  padding: 3px 8px;
}

/* Control Bar */
.control-bar {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.control-group label {
  font-family: var(--font-co);
  font-size: 0.65rem;
  letter-spacing: 1px;
  color: var(--textbr);
  text-transform: uppercase;
}

.control-group select,
.control-group input {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--textwh);
  padding: 6px 10px;
  border-radius: 4px;
  font-family: var(--font-co);
  font-size: 0.8rem;
  min-width: 150px;
}

.control-group select:focus,
.control-group input:focus {
  border-color: var(--cyan);
  outline: none;
  box-shadow: 0 0 6px rgba(0, 229, 255, 0.2);
}

.control-actions {
  display: flex;
  gap: 8px;
}

.status-info {
  display: flex;
  gap: 12px;
  font-family: var(--font-co);
  font-size: 0.7rem;
  color: var(--textbr);
  margin-left: auto;
}

.api-indicator.up { color: var(--green); }
.api-indicator.down { color: var(--pink); }

/* Buttons */
.cyber-button {
  font-family: var(--font-hd);
  font-size: 0.7rem;
  letter-spacing: 1px;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid;
}

.cyber-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cyber-button.primary {
  background: rgba(0, 229, 255, 0.1);
  border-color: var(--cyan);
  color: var(--cyan);
}

.cyber-button.primary:hover:not(:disabled) {
  background: var(--cyan);
  color: var(--bg);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.4);
}

.cyber-button.secondary {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--border);
  color: var(--text);
}

.cyber-button.secondary:hover:not(:disabled) {
  border-color: var(--textbr);
  color: var(--textwh);
}

.cyber-button.danger {
  background: rgba(255, 45, 110, 0.1);
  border-color: var(--pink);
  color: var(--pink);
}

.cyber-button.danger:hover:not(:disabled) {
  background: var(--pink);
  color: #fff;
  box-shadow: 0 0 12px rgba(255, 45, 110, 0.4);
}

.cyber-button.small {
  font-size: 0.6rem;
  padding: 4px 10px;
}

/* Tabs */
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
}

.tab {
  font-family: var(--font-hd);
  font-size: 0.7rem;
  letter-spacing: 1px;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px 4px 0 0;
  color: var(--textbr);
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.tab:hover {
  color: var(--textwh);
  background: rgba(255, 255, 255, 0.05);
}

.tab.active {
  color: var(--cyan);
  border-color: var(--cyan);
  border-bottom-color: transparent;
  background: rgba(0, 229, 255, 0.05);
}

.tab .badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--pink);
  color: #fff;
  font-size: 0.55rem;
  padding: 2px 5px;
  border-radius: 8px;
  font-family: var(--font-co);
}

/* Tab Content */
.tab-content {
  flex: 1;
  overflow: hidden;
}

.panel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.filter-input {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--textwh);
  padding: 6px 12px;
  border-radius: 4px;
  font-family: var(--font-co);
  font-size: 0.75rem;
  width: 250px;
}

.filter-input:focus {
  border-color: var(--cyan);
  outline: none;
}

.count {
  font-family: var(--font-co);
  font-size: 0.7rem;
  color: var(--textbr);
  letter-spacing: 1px;
}

/* Table */
.table-container {
  overflow: auto;
  max-height: calc(100vh - 320px);
}

.cyber-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-co);
  font-size: 0.75rem;
}

.cyber-table th {
  position: sticky;
  top: 0;
  background: var(--bg2);
  color: var(--textbr);
  text-align: left;
  padding: 8px 12px;
  font-weight: normal;
  letter-spacing: 1px;
  text-transform: uppercase;
  font-size: 0.65rem;
  border-bottom: 1px solid var(--border);
  z-index: 1;
}

.cyber-table td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  color: var(--textwh);
}

.cyber-table tr:hover td {
  background: rgba(0, 229, 255, 0.03);
}

.cyber-table .alert-row td {
  background: rgba(255, 45, 110, 0.05);
}

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
}

.ssid-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Signal Bar */
.signal-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 100px;
}

.signal-fill {
  height: 6px;
  border-radius: 3px;
  transition: width 0.3s;
}

.signal-fill.excellent { background: var(--green); box-shadow: 0 0 4px var(--green); }
.signal-fill.good { background: var(--cyan); box-shadow: 0 0 4px var(--cyan); }
.signal-fill.fair { background: #f0ad4e; }
.signal-fill.poor { background: var(--pink); }

.signal-text {
  font-size: 0.65rem;
  color: var(--textbr);
  white-space: nowrap;
}

/* Crypt Badge */
.crypt-badge {
  font-size: 0.6rem;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}

.crypt-badge.open { background: rgba(255, 45, 110, 0.15); color: var(--pink); border: 1px solid rgba(255, 45, 110, 0.3); }
.crypt-badge.wep { background: rgba(255, 165, 0, 0.15); color: orange; border: 1px solid rgba(255, 165, 0, 0.3); }
.crypt-badge.wpa { background: rgba(255, 200, 0, 0.15); color: #f0c040; border: 1px solid rgba(255, 200, 0, 0.3); }
.crypt-badge.wpa2 { background: rgba(0, 229, 255, 0.1); color: var(--cyan); border: 1px solid rgba(0, 229, 255, 0.3); }
.crypt-badge.wpa3 { background: rgba(0, 255, 157, 0.1); color: var(--green); border: 1px solid rgba(0, 255, 157, 0.3); }
.crypt-badge.encrypted { background: rgba(255, 255, 255, 0.05); color: var(--text); border: 1px solid var(--border); }

/* Alert Badge */
.alert-badge {
  background: var(--pink);
  color: #fff;
  font-size: 0.6rem;
  padding: 2px 6px;
  border-radius: 8px;
  font-weight: bold;
}

/* Alerts Panel */
.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: auto;
  max-height: calc(100vh - 320px);
}

.alert-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  border-left: 3px solid var(--textbr);
}

.alert-card.critical { border-left-color: var(--pink); background: rgba(255, 45, 110, 0.05); }
.alert-card.high { border-left-color: #ff8c00; background: rgba(255, 140, 0, 0.05); }
.alert-card.medium { border-left-color: #f0c040; }
.alert-card.low { border-left-color: var(--cyan); }

.alert-header {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.alert-type {
  font-family: var(--font-hd);
  font-size: 0.7rem;
  color: var(--textwh);
  letter-spacing: 1px;
}

.alert-severity {
  font-family: var(--font-co);
  font-size: 0.6rem;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 1px;
}

.alert-card.critical .alert-severity { background: rgba(255, 45, 110, 0.2); color: var(--pink); }
.alert-card.high .alert-severity { background: rgba(255, 140, 0, 0.2); color: #ff8c00; }
.alert-card.medium .alert-severity { background: rgba(240, 192, 64, 0.2); color: #f0c040; }
.alert-card.low .alert-severity { background: rgba(0, 229, 255, 0.1); color: var(--cyan); }

.alert-time {
  font-family: var(--font-co);
  font-size: 0.6rem;
  color: var(--textbr);
  margin-left: auto;
}

.alert-body {
  font-family: var(--font-co);
  font-size: 0.75rem;
  color: var(--text);
}

.alert-message {
  margin-bottom: 4px;
}

.alert-mac, .alert-phy {
  font-size: 0.65rem;
  color: var(--textbr);
}

/* Channels Panel */
.channels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  overflow: auto;
  max-height: calc(100vh - 320px);
  padding-right: 4px;
}

.channel-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
}

.channel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.channel-name {
  font-family: var(--font-hd);
  font-size: 0.85rem;
  color: var(--cyan);
}

.channel-freq {
  font-family: var(--font-co);
  font-size: 0.65rem;
  color: var(--textbr);
}

.channel-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 10px;
}

.channel-stats .stat {
  display: flex;
  flex-direction: column;
}

.channel-stats .stat-label {
  font-family: var(--font-co);
  font-size: 0.55rem;
  color: var(--textbr);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.channel-stats .stat-value {
  font-family: var(--font-co);
  font-size: 0.75rem;
  color: var(--textwh);
}

.channel-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.channel-bar .bar-fill {
  height: 100%;
  background: var(--cyan);
  border-radius: 2px;
  transition: width 0.3s;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--textbr);
  font-family: var(--font-co);
  font-size: 0.85rem;
  letter-spacing: 1px;
}

/* Action buttons */
.action-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--textbr);
  padding: 3px 8px;
  border-radius: 3px;
  font-family: var(--font-co);
  font-size: 0.6rem;
  cursor: pointer;
  transition: all 0.2s;
  margin-right: 4px;
}

.action-btn:hover {
  border-color: var(--cyan);
  color: var(--cyan);
}

/* Spinner */
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(0, 229, 255, 0.3);
  border-top-color: var(--cyan);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Glitch effect */
.glitch-text {
  position: relative;
}

.glitch-text::before,
.glitch-text::after {
  content: attr(data-text);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0.8;
}

.glitch-text::before {
  animation: glitch-1 2s infinite linear alternate-reverse;
  clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
  color: var(--pink);
}

.glitch-text::after {
  animation: glitch-2 3s infinite linear alternate-reverse;
  clip-path: polygon(0 60%, 100% 60%, 100% 100%, 0 100%);
  color: var(--cyan);
}

@keyframes glitch-1 {
  0% { transform: translate(0); }
  20% { transform: translate(-2px, 2px); }
  40% { transform: translate(-2px, -2px); }
  60% { transform: translate(2px, 2px); }
  80% { transform: translate(2px, -2px); }
  100% { transform: translate(0); }
}

@keyframes glitch-2 {
  0% { transform: translate(0); }
  20% { transform: translate(2px, -2px); }
  40% { transform: translate(2px, 2px); }
  60% { transform: translate(-2px, -2px); }
  80% { transform: translate(-2px, 2px); }
  100% { transform: translate(0); }
}
</style>
