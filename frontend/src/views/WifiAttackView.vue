<template>
  <div class="wifi-view">
    <div class="header">
      <h1>📶 WiFi Attacks</h1>
      <p class="subtitle">Wireless penetration testing — deauth, evil twin, handshake capture & cracking</p>
    </div>

    <div class="tabs">
      <button v-for="tab in tabs" :key="tab.id" :class="['tab-btn', { active: activeTab === tab.id }]" @click="activeTab = tab.id">
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- Interfaces -->
    <div v-if="activeTab === 'interfaces'" class="tab-content">
      <div class="panel">
        <h2>Wireless Interfaces</h2>
        <button @click="loadInterfaces" class="btn-secondary">Refresh</button>
        <div v-if="interfaces.length" class="iface-grid">
          <div v-for="iface in interfaces" :key="iface.name" class="iface-card">
            <div class="iface-name">{{ iface.name }}</div>
            <div class="iface-driver">{{ iface.driver }}</div>
            <span :class="['iface-badge', iface.monitor_mode ? 'monitor' : 'managed']">
              {{ iface.monitor_mode ? 'MONITOR' : 'MANAGED' }}
            </span>
          </div>
        </div>
        <div v-else class="empty">No wireless interfaces detected. WiFi attacks require monitor mode.</div>
      </div>
    </div>

    <!-- Scan -->
    <div v-if="activeTab === 'scan'" class="tab-content">
      <div class="panel">
        <h2>WiFi Network Scan</h2>
        <div class="form-row">
          <div class="form-group">
            <label>Interface</label>
            <select v-model="scanForm.interface">
              <option value="">Select interface...</option>
              <option v-for="iface in interfaces" :key="iface.name" :value="iface.name">{{ iface.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Duration (seconds)</label>
            <input v-model.number="scanForm.duration" type="number" min="5" max="60" />
          </div>
          <button @click="runScan" :disabled="!scanForm.interface || scanning" class="btn-primary">
            {{ scanning ? '⏳ Scanning...' : '📡 Scan' }}
          </button>
        </div>
        <div v-if="scanStatus" :class="['status', scanStatus.type]">{{ scanStatus.message }}</div>
      </div>

      <div v-if="networks.length" class="panel">
        <h2>Discovered Networks ({{ networks.length }})</h2>
        <div class="network-grid">
          <div v-for="net in networks" :key="net.bssid" class="network-card" :class="{ selected: selectedNetwork?.bssid === net.bssid }" @click="selectedNetwork = net">
            <div class="net-header">
              <span class="net-ssid">{{ net.ssid || '<Hidden>' }}</span>
              <span :class="['net-enc', net.encryption?.toLowerCase()]">{{ net.encryption || '?' }}</span>
            </div>
            <div class="net-meta">
              <span>BSSID: {{ net.bssid }}</span>
              <span>CH: {{ net.channel }}</span>
              <span>Signal: {{ net.signal }}dBm</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="!scanning && scanDone" class="panel">
        <div class="empty">No networks found. The interface may need to be in monitor mode.</div>
        <div class="hint">Try: <code>sudo airmon-ng start {{ scanForm.interface }}</code> on the host machine, then switch to monitor mode interface.</div>
      </div>
    </div>

    <!-- Deauth -->
    <div v-if="activeTab === 'deauth'" class="tab-content">
      <div class="panel">
        <h2>Deauthentication Attack</h2>
        <p class="warning">⚠️ Disconnects clients from a target access point. Requires monitor mode.</p>
        <div class="form-group">
          <label>Interface</label>
          <select v-model="deauthForm.interface">
            <option value="">Select interface...</option>
            <option v-for="iface in interfaces" :key="iface.name" :value="iface.name">{{ iface.name }}</option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Target BSSID (AP MAC)</label>
            <input v-model="deauthForm.target_bssid" type="text" placeholder="AA:BB:CC:DD:EE:FF" />
          </div>
          <div class="form-group">
            <label>Target Client (blank = broadcast)</label>
            <input v-model="deauthForm.target_client" type="text" placeholder="ff:ff:ff:ff:ff:ff" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Packet Count</label>
            <input v-model.number="deauthForm.count" type="number" min="1" max="100" />
          </div>
          <div class="form-group">
            <label>Interval (s)</label>
            <input v-model.number="deauthForm.interval" type="number" min="0.05" max="2" step="0.05" />
          </div>
        </div>
        <button @click="runDeauth" :disabled="!deauthForm.target_bssid || !deauthForm.interface || attacking" class="btn-danger">
          {{ attacking ? '⏳ Attacking...' : '💥 Launch Deauth' }}
        </button>
        <div v-if="deauthResult" :class="['status', deauthResult.success ? 'success' : 'error']">
          {{ deauthResult.message || (deauthResult.success ? 'Deauth packets sent' : deauthResult.error) }}
        </div>
      </div>
    </div>

    <!-- Evil Twin -->
    <div v-if="activeTab === 'evil-twin'" class="tab-content">
      <div class="panel">
        <h2>Evil Twin AP</h2>
        <p class="warning">⚠️ Creates a rogue access point mimicking a target network. Requires hostapd.</p>
        <div class="form-group">
          <label>Interface</label>
          <select v-model="twinForm.interface">
            <option value="">Select interface...</option>
            <option v-for="iface in interfaces" :key="iface.name" :value="iface.name">{{ iface.name }}</option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Target SSID</label>
            <input v-model="twinForm.target_ssid" type="text" placeholder="TargetNetwork" />
          </div>
          <div class="form-group">
            <label>Target BSSID</label>
            <input v-model="twinForm.target_bssid" type="text" placeholder="AA:BB:CC:DD:EE:FF" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Channel</label>
            <input v-model.number="twinForm.channel" type="number" min="1" max="14" />
          </div>
          <div class="form-group">
            <label>Duration (s)</label>
            <input v-model.number="twinForm.duration" type="number" min="10" max="600" />
          </div>
        </div>
        <button @click="runEvilTwin" :disabled="!twinForm.target_bssid || !twinForm.interface || attacking" class="btn-danger">
          {{ attacking ? '⏳ Running...' : '👻 Launch Evil Twin' }}
        </button>
        <div v-if="twinResult" :class="['status', twinResult.success ? 'success' : 'error']">
          {{ twinResult.message || (twinResult.success ? 'Evil twin active' : twinResult.error) }}
        </div>
      </div>
    </div>

    <!-- Handshake -->
    <div v-if="activeTab === 'handshake'" class="tab-content">
      <div class="panel">
        <h2>WPA Handshake Capture</h2>
        <p class="warning">⚠️ Captures the 4-way WPA handshake for offline cracking.</p>
        <div class="form-group">
          <label>Interface</label>
          <select v-model="hsForm.interface">
            <option value="">Select interface...</option>
            <option v-for="iface in interfaces" :key="iface.name" :value="iface.name">{{ iface.name }}</option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Target BSSID</label>
            <input v-model="hsForm.target_bssid" type="text" placeholder="AA:BB:CC:DD:EE:FF" />
          </div>
          <div class="form-group">
            <label>Target Client (blank = broadcast)</label>
            <input v-model="hsForm.target_client" type="text" placeholder="ff:ff:ff:ff:ff:ff" />
          </div>
        </div>
        <div class="form-group">
          <label>Duration (s)</label>
          <input v-model.number="hsForm.duration" type="number" min="10" max="120" />
        </div>
        <button @click="runHandshake" :disabled="!hsForm.target_bssid || !hsForm.interface || attacking" class="btn-danger">
          {{ attacking ? '⏳ Capturing...' : '🔑 Capture Handshake' }}
        </button>
        <div v-if="hsResult" :class="['status', hsResult.success ? 'success' : 'error']">
          {{ hsResult.message || (hsResult.success ? 'Handshake captured!' : hsResult.error) }}
          <div v-if="hsResult.capture_file">File: <code>{{ hsResult.capture_file }}</code></div>
        </div>
      </div>

      <!-- WPA Crack -->
      <div class="panel">
        <h2>WPA Handshake Crack</h2>
        <div class="form-group">
          <label>Capture File</label>
          <input v-model="crackForm.capture_file" type="text" placeholder="/tmp/handshake_*.cap" />
        </div>
        <div class="form-group">
          <label>Wordlist</label>
          <input v-model="crackForm.wordlist" type="text" />
        </div>
        <button @click="runCrack" :disabled="!crackForm.capture_file || cracking" class="btn-danger">
          {{ cracking ? '⏳ Cracking...' : '🔓 Crack Handshake' }}
        </button>
        <div v-if="crackResult" :class="['status', crackResult.success ? 'success' : 'error']">
          {{ crackResult.message || (crackResult.success ? `Password found: ${crackResult.password}` : crackResult.error) }}
        </div>
      </div>
    </div>

    <!-- Probe Clients -->
    <div v-if="activeTab === 'clients'" class="tab-content">
      <div class="panel">
        <h2>Probe Clients</h2>
        <div class="form-group">
          <label>Interface</label>
          <select v-model="probeForm.interface">
            <option value="">Select interface...</option>
            <option v-for="iface in interfaces" :key="iface.name" :value="iface.name">{{ iface.name }}</option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Target BSSID</label>
            <input v-model="probeForm.target_bssid" type="text" placeholder="AA:BB:CC:DD:EE:FF" />
          </div>
          <div class="form-group">
            <label>Duration (s)</label>
            <input v-model.number="probeForm.duration" type="number" min="5" max="60" />
          </div>
        </div>
        <button @click="runProbe" :disabled="!probeForm.target_bssid || !probeForm.interface || probing" class="btn-primary">
          {{ probing ? '⏳ Probing...' : '🔍 Probe Clients' }}
        </button>
      </div>
      <div v-if="clients.length" class="panel">
        <h2>Discovered Clients ({{ clients.length }})</h2>
        <div v-for="c in clients" :key="c.mac" class="client-card">
          <span class="client-mac">{{ c.mac }}</span>
          <span class="client-signal">{{ c.signal }}dBm</span>
          <span v-if="c.probes?.length" class="client-probes">{{ c.probes.join(', ') }}</span>
        </div>
      </div>
    </div>

    <!-- Active Attacks -->
    <div v-if="activeTab === 'active'" class="tab-content">
      <div class="panel">
        <h2>Active / Completed Attacks</h2>
        <button @click="loadActiveAttacks" class="btn-secondary">Refresh</button>
        <div v-for="atk in activeAttacks" :key="atk.id" class="attack-card">
          <div class="atk-header">
            <span :class="['atk-type', atk.type]">{{ atk.type.toUpperCase() }}</span>
            <span :class="['atk-status', atk.status]">{{ atk.status }}</span>
          </div>
          <div class="atk-meta">
            <span>Target: {{ atk.target }}</span>
            <span>Started: {{ formatDate(atk.started_at) }}</span>
          </div>
          <div v-if="atk.message" class="atk-message">{{ atk.message }}</div>
        </div>
        <div v-if="activeAttacks.length === 0" class="empty">No active attacks.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const tabs = [
  { id: 'interfaces', label: 'Interfaces', icon: '📡' },
  { id: 'scan', label: 'Scan', icon: '🔍' },
  { id: 'deauth', label: 'Deauth', icon: '💥' },
  { id: 'evil-twin', label: 'Evil Twin', icon: '👻' },
  { id: 'handshake', label: 'Handshake', icon: '🔑' },
  { id: 'clients', label: 'Clients', icon: '👥' },
  { id: 'active', label: 'Active Attacks', icon: '⚡' },
]

const activeTab = ref('interfaces')
const interfaces = ref<any[]>([])
const networks = ref<any[]>([])
const selectedNetwork = ref<any>(null)
const clients = ref<any[]>([])
const activeAttacks = ref<any[]>([])

const scanning = ref(false)
const scanDone = ref(false)
const attacking = ref(false)
const probing = ref(false)
const cracking = ref(false)

const scanForm = ref({ interface: '', duration: 15 })
const scanStatus = ref<{ type: string; message: string } | null>(null)
const deauthForm = ref({ interface: '', target_bssid: '', target_client: 'ff:ff:ff:ff:ff:ff', count: 10, interval: 0.1 })
const twinForm = ref({ interface: '', target_ssid: '', target_bssid: '', channel: 6, duration: 60 })
const hsForm = ref({ interface: '', target_bssid: '', target_client: 'ff:ff:ff:ff:ff:ff', duration: 30 })
const crackForm = ref({ capture_file: '', wordlist: '/usr/share/wordlists/rockyou.txt' })
const probeForm = ref({ interface: '', target_bssid: '', duration: 10 })

const deauthResult = ref<any>(null)
const twinResult = ref<any>(null)
const hsResult = ref<any>(null)
const crackResult = ref<any>(null)

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString()
}

async function loadInterfaces() {
  try {
    const res = await api.get('/wifi-attack/interfaces')
    interfaces.value = res.data?.interfaces || []
  } catch (e) {
    console.error('Failed to load interfaces', e)
  }
}

async function runScan() {
  scanning.value = true
  scanDone.value = false
  scanStatus.value = { type: 'info', message: `Scanning ${scanForm.value.interface} for ${scanForm.value.duration}s...` }
  try {
    const res = await api.post('/wifi-attack/scan', scanForm.value)
    const data = res.data
    networks.value = data?.networks || []
    scanStatus.value = { type: 'success', message: `Found ${networks.value.length} network(s)` }
  } catch (e: any) {
    const msg = typeof e.message === 'string' ? e.message : 'Scan failed'
    scanStatus.value = { type: 'error', message: msg }
  } finally {
    scanning.value = false
    scanDone.value = true
  }
}

async function runDeauth() {
  attacking.value = true
  deauthResult.value = null
  try {
    deauthResult.value = await api.post('/wifi-attack/deauth', deauthForm.value)
  } catch (e: any) {
    deauthResult.value = { success: false, error: e.message || 'Failed' }
  } finally {
    attacking.value = false
  }
}

async function runEvilTwin() {
  attacking.value = true
  twinResult.value = null
  try {
    twinResult.value = await api.post('/wifi-attack/evil-twin', twinForm.value)
  } catch (e: any) {
    twinResult.value = { success: false, error: e.message || 'Failed' }
  } finally {
    attacking.value = false
  }
}

async function runHandshake() {
  attacking.value = true
  hsResult.value = null
  try {
    hsResult.value = await api.post('/wifi-attack/capture-handshake', hsForm.value)
  } catch (e: any) {
    hsResult.value = { success: false, error: e.message || 'Failed' }
  } finally {
    attacking.value = false
  }
}

async function runCrack() {
  cracking.value = true
  crackResult.value = null
  try {
    crackResult.value = await api.post('/wifi-attack/crack', crackForm.value)
  } catch (e: any) {
    crackResult.value = { success: false, error: e.message || 'Failed' }
  } finally {
    cracking.value = false
  }
}

async function runProbe() {
  probing.value = true
  try {
    const res = await api.post('/wifi-attack/probe-clients', probeForm.value)
    clients.value = res.data?.clients || []
  } catch (e: any) {
    alert(e.message || 'Probe failed')
  } finally {
    probing.value = false
  }
}

async function loadActiveAttacks() {
  try {
    const res = await api.get('/wifi-attack/active')
    activeAttacks.value = res.data?.attacks || []
  } catch (e) {
    console.error('Failed to load attacks', e)
  }
}

onMounted(() => {
  loadInterfaces()
  loadActiveAttacks()
})
</script>

<style scoped>
.wifi-view { padding: 20px; color: #e0e0e0; }
.header h1 { color: #00ff88; margin-bottom: 4px; }
.subtitle { color: #888; margin-bottom: 20px; }
.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 8px; flex-wrap: wrap; }
.tab-btn { padding: 8px 16px; background: #1a1a2e; border: 1px solid #333; color: #aaa; cursor: pointer; border-radius: 4px 4px 0 0; }
.tab-btn.active { background: #0f3460; color: #00ff88; border-color: #00ff88; }
.panel { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.panel h2 { color: #00ff88; margin-bottom: 16px; }
.warning { color: #ff8800; font-size: 0.9em; margin-bottom: 16px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 4px; color: #aaa; }
.form-group input, .form-group select { width: 100%; padding: 8px; background: #0d1117; border: 1px solid #333; color: #e0e0e0; border-radius: 4px; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }
.btn-primary { padding: 10px 20px; background: #00ff88; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-primary:hover:not(:disabled) { background: #00cc6a; }
.btn-primary:disabled { opacity: 0.5; }
.btn-secondary { padding: 8px 16px; background: #333; color: #e0e0e0; border: 1px solid #555; border-radius: 4px; cursor: pointer; margin-bottom: 12px; }
.btn-danger { padding: 10px 20px; background: #ff4444; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-danger:hover:not(:disabled) { background: #cc0000; }
.btn-danger:disabled { opacity: 0.5; }
.status { margin-top: 12px; padding: 8px; border-radius: 4px; }
.status.success { background: rgba(0, 255, 136, 0.1); border: 1px solid #00ff88; color: #00ff88; }
.status.error { background: rgba(255, 0, 0, 0.1); border: 1px solid #ff4444; color: #ff4444; }
.status.info { background: rgba(0, 170, 255, 0.1); border: 1px solid #00aaff; color: #00aaff; }
.iface-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-top: 12px; }
.iface-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; }
.iface-name { font-weight: bold; font-size: 1.1em; }
.iface-driver { color: #888; font-size: 0.85em; }
.iface-badge { display: inline-block; margin-top: 6px; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
.iface-badge.monitor { background: rgba(0, 255, 136, 0.2); color: #00ff88; }
.iface-badge.managed { background: rgba(136, 136, 136, 0.2); color: #888; }
.network-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.network-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; cursor: pointer; transition: border-color 0.2s; }
.network-card:hover, .network-card.selected { border-color: #00ff88; }
.net-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.net-ssid { font-weight: bold; }
.net-enc { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
.net-enc.wpa2 { background: rgba(255, 136, 0, 0.2); color: #ff8800; }
.net-enc.wpa { background: rgba(255, 170, 0, 0.2); color: #ffaa00; }
.net-enc.wep { background: rgba(255, 68, 68, 0.2); color: #ff4444; }
.net-enc.open { background: rgba(0, 170, 255, 0.2); color: #00aaff; }
.net-meta { display: flex; gap: 12px; font-size: 0.85em; color: #888; }
.client-card { display: flex; gap: 16px; align-items: center; background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.client-mac { font-family: monospace; font-weight: bold; }
.client-signal { color: #888; }
.client-probes { color: #00aaff; font-size: 0.85em; }
.attack-card { background: #0d1117; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.atk-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.atk-type { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
.atk-type.deauth { background: rgba(255, 68, 68, 0.2); color: #ff4444; }
.atk-type.evil_twin { background: rgba(255, 136, 0, 0.2); color: #ff8800; }
.atk-type.handshake { background: rgba(0, 255, 136, 0.2); color: #00ff88; }
.atk-status { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
.atk-status.running { background: rgba(0, 170, 255, 0.2); color: #00aaff; }
.atk-status.completed { background: rgba(136, 136, 136, 0.2); color: #888; }
.atk-meta { display: flex; gap: 16px; font-size: 0.85em; color: #888; }
.atk-message { margin-top: 8px; font-size: 0.9em; color: #aaa; }
.empty { text-align: center; color: #666; padding: 20px; }
.hint { text-align: center; color: #888; font-size: 0.9em; margin-top: 8px; }
.hint code { background: #111; padding: 2px 6px; border-radius: 3px; color: #00ff88; }
</style>
