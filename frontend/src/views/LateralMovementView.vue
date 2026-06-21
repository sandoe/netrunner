<template>
  <div class="lateral-view">
    <div class="header">
      <h1>🔗 Lateral Movement</h1>
      <p class="subtitle">SSH Tunnels, SOCKS Proxy & Pivot Chains</p>
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

    <!-- Active Tunnels -->
    <div v-if="activeTab === 'tunnels'" class="tab-content">
      <div class="panel">
        <h2>Active Tunnels</h2>
        <div class="tunnel-list">
          <div v-for="tunnel in tunnels" :key="tunnel.id" class="tunnel-card">
            <div class="tunnel-header">
              <span :class="['tunnel-type', tunnel.type]">{{ tunnel.type.toUpperCase() }}</span>
              <span class="tunnel-id">{{ tunnel.id }}</span>
              <span class="tunnel-status">🟢 Active</span>
            </div>
            <div class="tunnel-details">
              <p v-if="tunnel.type === 'socks'">
                <strong>SOCKS5 Proxy:</strong> 127.0.0.1:{{ tunnel.local_port }}
              </p>
              <p v-if="tunnel.type === 'local'">
                <strong>Forward:</strong> localhost:{{ tunnel.local_port }} → {{ tunnel.remote_host }}:{{ tunnel.remote_port }}
              </p>
              <p v-if="tunnel.type === 'remote'">
                <strong>Reverse:</strong> {{ tunnel.host }}:{{ tunnel.remote_port }} → {{ tunnel.local_host }}:{{ tunnel.local_port }}
              </p>
              <p><strong>Target:</strong> {{ tunnel.host }}:{{ tunnel.remote_port || tunnel.ssh_port }}</p>
              <p><strong>Created:</strong> {{ formatDate(tunnel.created_at) }}</p>
            </div>
            <div class="tunnel-actions">
              <button @click="closeTunnel(tunnel.id)" class="btn-danger btn-small">Close</button>
            </div>
          </div>
          <div v-if="tunnels.length === 0" class="empty-state">
            No active tunnels. Create one below.
          </div>
        </div>
      </div>

      <!-- Create Tunnel -->
      <div class="panel">
        <h2>Create Tunnel</h2>
        <div class="tunnel-forms">
          <div :class="['tunnel-form', { active: tunnelType === 'socks' }]" @click="tunnelType = 'socks'">
            <h3>🔌 SOCKS Proxy</h3>
            <p>Create a local SOCKS5 proxy for browser/tool traffic</p>
          </div>
          <div :class="['tunnel-form', { active: tunnelType === 'local' }]" @click="tunnelType = 'local'">
            <h3>➡️ Local Forward</h3>
            <p>Forward local port to remote service</p>
          </div>
          <div :class="['tunnel-form', { active: tunnelType === 'remote' }]" @click="tunnelType = 'remote'">
            <h3>⬅️ Remote Forward</h3>
            <p>Remote port forwards back to local service</p>
          </div>
        </div>

        <!-- SOCKS Form -->
        <div v-if="tunnelType === 'socks'" class="form-content">
          <div class="form-group">
            <label>Target Node</label>
            <select v-model="socksForm.node_id">
              <option value="">Select node...</option>
              <option v-for="node in nodes" :key="node.id" :value="node.id">
                {{ node.name }} ({{ node.host }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>Local Port</label>
            <input v-model.number="socksForm.local_port" type="number" placeholder="1080" />
          </div>
          <div class="form-group">
            <label>SSH Port</label>
            <input v-model.number="socksForm.remote_port" type="number" placeholder="22" />
          </div>
          <button @click="createSOCKS" :disabled="!socksForm.node_id" class="btn-primary">
            Create SOCKS Proxy
          </button>
        </div>

        <!-- Local Forward Form -->
        <div v-if="tunnelType === 'local'" class="form-content">
          <div class="form-group">
            <label>Target Node (SSH Jump Host)</label>
            <select v-model="localForm.node_id">
              <option value="">Select node...</option>
              <option v-for="node in nodes" :key="node.id" :value="node.id">
                {{ node.name }} ({{ node.host }})
              </option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Local Port</label>
              <input v-model.number="localForm.local_port" type="number" placeholder="8080" />
            </div>
            <div class="form-group">
              <label>Remote Host</label>
              <input v-model="localForm.remote_host" type="text" placeholder="192.168.1.100" />
            </div>
            <div class="form-group">
              <label>Remote Port</label>
              <input v-model.number="localForm.remote_port" type="number" placeholder="80" />
            </div>
          </div>
          <button @click="createLocalForward" :disabled="!localForm.node_id" class="btn-primary">
            Create Local Forward
          </button>
        </div>

        <!-- Remote Forward Form -->
        <div v-if="tunnelType === 'remote'" class="form-content">
          <div class="form-group">
            <label>Target Node (SSH Jump Host)</label>
            <select v-model="remoteForm.node_id">
              <option value="">Select node...</option>
              <option v-for="node in nodes" :key="node.id" :value="node.id">
                {{ node.name }} ({{ node.host }})
              </option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Remote Port (on SSH server)</label>
              <input v-model.number="remoteForm.remote_port" type="number" placeholder="9090" />
            </div>
            <div class="form-group">
              <label>Local Host</label>
              <input v-model="remoteForm.local_host" type="text" placeholder="127.0.0.1" />
            </div>
            <div class="form-group">
              <label>Local Port</label>
              <input v-model.number="remoteForm.local_port" type="number" placeholder="80" />
            </div>
          </div>
          <button @click="createRemoteForward" :disabled="!remoteForm.node_id" class="btn-primary">
            Create Remote Forward
          </button>
        </div>

        <div v-if="tunnelStatus" :class="['status', tunnelStatus.type]">
          {{ tunnelStatus.message }}
        </div>
      </div>
    </div>

    <!-- Pivot Chains -->
    <div v-if="activeTab === 'pivots'" class="tab-content">
      <div class="panel">
        <h2>Active Pivot Chains</h2>
        <div v-for="chain in pivotChains" :key="chain.id" class="chain-card">
          <div class="chain-header">
            <span class="chain-name">{{ chain.name }}</span>
            <span class="chain-status">🟢 Active</span>
          </div>
          <div class="chain-hops">
            <div v-for="(hop, idx) in chain.hops" :key="idx" class="hop">
              <span class="hop-number">{{ idx + 1 }}</span>
              <span class="hop-host">{{ hop.host }}</span>
              <span v-if="idx < chain.hops.length - 1" class="hop-arrow">→</span>
            </div>
          </div>
          <button @click="closePivotChain(chain.id)" class="btn-danger btn-small">Close Chain</button>
        </div>
        <div v-if="pivotChains.length === 0" class="empty-state">
          No active pivot chains.
        </div>
      </div>

      <!-- Create Pivot Chain -->
      <div class="panel">
        <h2>Create Pivot Chain</h2>
        <div class="form-group">
          <label>Chain Name</label>
          <input v-model="pivotName" type="text" placeholder="Internal Network Pivot" />
        </div>
        <div class="hops-editor">
          <h4>Hops (in order)</h4>
          <div v-for="(hop, idx) in pivotHops" :key="idx" class="hop-editor">
            <span class="hop-number">{{ idx + 1 }}</span>
            <select v-model="hop.node_id" @change="onHopNodeChange(idx)">
              <option value="">Select node...</option>
              <option v-for="node in nodes" :key="node.id" :value="node.id">
                {{ node.name }}
              </option>
            </select>
            <input v-model="hop.host" placeholder="Host" />
            <input v-model="hop.username" placeholder="User" />
            <input v-model="hop.password" type="password" placeholder="Pass" />
            <button @click="removeHop(idx)" class="btn-danger btn-small">✕</button>
          </div>
          <button @click="addHop" class="btn-secondary">+ Add Hop</button>
        </div>
        <button @click="createPivotChain" :disabled="!pivotName || pivotHops.length < 2" class="btn-primary">
          Create Pivot Chain
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const tabs = [
  { id: 'tunnels', label: 'Active Tunnels', icon: '🔌' },
  { id: 'pivots', label: 'Pivot Chains', icon: '🔗' },
]

const activeTab = ref('tunnels')
const nodes = ref<any[]>([])
const tunnels = ref<any[]>([])
const pivotChains = ref<any[]>([])
const tunnelType = ref('socks')
const tunnelStatus = ref<{ type: string; message: string } | null>(null)

const socksForm = ref({ node_id: '', local_port: 1080, remote_port: 22 })
const localForm = ref({ node_id: '', local_port: 8080, remote_host: '', remote_port: 80 })
const remoteForm = ref({ node_id: '', remote_port: 9090, local_host: '127.0.0.1', local_port: 80 })

const pivotName = ref('')
const pivotHops = ref([
  { node_id: '', host: '', username: 'root', password: '' },
  { node_id: '', host: '', username: 'root', password: '' },
])

onMounted(async () => {
  try {
    const nodesRes = await api.get('/nodes')
    nodes.value = Object.values(nodesRes.data || {})
  } catch (e) {
    console.error('Failed to load nodes', e)
  }

  await refreshTunnels()
  await refreshPivots()
})

async function refreshTunnels() {
  try {
    const res = await api.get('/lateral/tunnels')
    tunnels.value = res.data?.tunnels || []
  } catch (e) {
    console.error('Failed to load tunnels', e)
  }
}

async function refreshPivots() {
  try {
    const res = await api.get('/lateral/pivots')
    pivotChains.value = res.data?.chains || []
  } catch (e) {
    console.error('Failed to load pivots', e)
  }
}

async function createSOCKS() {
  tunnelStatus.value = null
  try {
    const res = await api.post('/lateral/socks-proxy', socksForm.value)
    tunnelStatus.value = { type: 'success', message: `SOCKS proxy created: ${res.data.proxy_address}` }
    await refreshTunnels()
  } catch (e: any) {
    tunnelStatus.value = { type: 'error', message: e.response?.data?.detail || 'Failed' }
  }
}

async function createLocalForward() {
  tunnelStatus.value = null
  try {
    const res = await api.post('/lateral/local-forward', localForm.value)
    tunnelStatus.value = { type: 'success', message: `Local forward created: localhost:${res.data.local_port} → ${res.data.remote_target}` }
    await refreshTunnels()
  } catch (e: any) {
    tunnelStatus.value = { type: 'error', message: e.response?.data?.detail || 'Failed' }
  }
}

async function createRemoteForward() {
  tunnelStatus.value = null
  try {
    const res = await api.post('/lateral/remote-forward', remoteForm.value)
    tunnelStatus.value = { type: 'success', message: `Remote forward created: port ${res.data.remote_port} → ${res.data.local_target}` }
    await refreshTunnels()
  } catch (e: any) {
    tunnelStatus.value = { type: 'error', message: e.response?.data?.detail || 'Failed' }
  }
}

async function closeTunnel(id: string) {
  try {
    await api.post('/lateral/close', { tunnel_id: id })
    await refreshTunnels()
  } catch (e) {
    console.error('Failed to close tunnel', e)
  }
}

function addHop() {
  pivotHops.value.push({ node_id: '', host: '', username: 'root', password: '' })
}

function removeHop(idx: number) {
  pivotHops.value.splice(idx, 1)
}

function onHopNodeChange(idx: number) {
  const hop = pivotHops.value[idx]
  const node = nodes.value.find((n: any) => n.id === hop.node_id)
  if (node) {
    hop.host = node.host
  }
}

async function createPivotChain() {
  tunnelStatus.value = null
  try {
    const hops = pivotHops.value.map(h => ({
      ...h,
      port: 22,
    }))
    const res = await api.post('/lateral/pivot-chain', { name: pivotName.value, hops })
    tunnelStatus.value = { type: 'success', message: `Pivot chain created: ${res.data.name} (${res.data.hops} hops)` }
    await refreshPivots()
  } catch (e: any) {
    tunnelStatus.value = { type: 'error', message: e.response?.data?.detail || 'Failed' }
  }
}

async function closePivotChain(id: string) {
  try {
    await api.post(`/lateral/close-chain/${id}`)
    await refreshPivots()
  } catch (e) {
    console.error('Failed to close pivot chain', e)
  }
}

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleString()
}
</script>

<style scoped>
.lateral-view {
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

.panel h2 {
  color: #00ff88;
  margin-bottom: 16px;
}

.tunnel-card {
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
}

.tunnel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.tunnel-type {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.85em;
}

.tunnel-type.socks { background: #0f3460; color: #00ff88; }
.tunnel-type.local { background: #1a4a1a; color: #88ff00; }
.tunnel-type.remote { background: #4a1a1a; color: #ff8800; }

.tunnel-id {
  color: #888;
  font-size: 0.85em;
}

.tunnel-status {
  margin-left: auto;
}

.tunnel-details p {
  margin: 2px 0;
  font-size: 0.85em;
}

.tunnel-actions {
  margin-top: 8px;
}

.tunnel-forms {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.tunnel-form {
  background: #0d1117;
  border: 2px solid #333;
  border-radius: 6px;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.tunnel-form:hover {
  border-color: #555;
}

.tunnel-form.active {
  border-color: #00ff88;
  background: #0a1a0a;
}

.tunnel-form h3 {
  margin-bottom: 4px;
  font-size: 1em;
}

.tunnel-form p {
  font-size: 0.85em;
  color: #888;
}

.form-content {
  background: #0d1117;
  padding: 16px;
  border-radius: 6px;
}

.form-group {
  margin-bottom: 12px;
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
  background: #111;
  border: 1px solid #333;
  color: #e0e0e0;
  border-radius: 4px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
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

.btn-secondary {
  padding: 8px 16px;
  background: #0f3460;
  color: #00ff88;
  border: 1px solid #00ff88;
  border-radius: 4px;
  cursor: pointer;
}

.btn-danger {
  padding: 4px 12px;
  background: #ff4444;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-small {
  padding: 4px 12px;
  font-size: 0.85em;
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

.empty-state {
  text-align: center;
  color: #666;
  padding: 40px;
}

.chain-card {
  background: #0d1117;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
}

.chain-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.chain-name {
  font-weight: bold;
  color: #00ff88;
}

.chain-hops {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.hop {
  display: flex;
  align-items: center;
  gap: 4px;
}

.hop-number {
  background: #0f3460;
  color: #00ff88;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8em;
}

.hop-host {
  background: #1a1a2e;
  padding: 4px 8px;
  border-radius: 4px;
}

.hop-arrow {
  color: #888;
}

.hops-editor {
  margin-bottom: 16px;
}

.hop-editor {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.hop-editor select,
.hop-editor input {
  flex: 1;
  padding: 8px;
  background: #111;
  border: 1px solid #333;
  color: #e0e0e0;
  border-radius: 4px;
}
</style>
