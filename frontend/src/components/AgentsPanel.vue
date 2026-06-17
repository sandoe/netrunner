<template>
  <div class="agents-panel">
    <div class="panel-header">
      <div class="panel-title">DISTRIBUTED AGENT MANAGEMENT</div>
      <div class="panel-actions">
        <button class="btn-action" @click="refreshStatus" :disabled="loading">
          <span v-if="loading">SCANNING...</span>
          <span v-else>REFRESH STATUS</span>
        </button>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div class="agents-grid">
      <div v-for="agent in agents" :key="agent.id" class="agent-card">
        <div class="agent-header">
          <div class="agent-title">
            <span class="status-dot" :class="{
              'dot-green': agent.running,
              'dot-red': agent.installed && !agent.running,
              'dot-gray': !agent.installed
            }"></span>
            {{ agent.name }}
          </div>
          <div class="agent-status-text" :class="{
            'text-green': agent.running,
            'text-red': agent.installed && !agent.running,
            'text-gray': !agent.installed
          }">
            {{ agent.running ? 'ACTIVE' : (agent.installed ? 'STOPPED' : 'NOT INSTALLED') }}
          </div>
        </div>
        
        <div class="agent-desc">{{ agent.description }}</div>
        
        <div class="agent-actions">
          <template v-if="!agent.installed">
            <button class="btn-action" @click="doAction(agent.id, 'install')">INSTALL</button>
          </template>
          <template v-else>
            <button v-if="!agent.running" class="btn-action" @click="doAction(agent.id, 'start')">START</button>
            <button v-if="agent.running" class="btn-action btn-danger" @click="doAction(agent.id, 'stop')">STOP</button>
            
            <button v-if="agent.id === 'tracker'" class="btn-action btn-edit" @click="fetchData(agent)">VIEW MAP</button>
            <button v-else-if="agent.id === 'scanner'" class="btn-action btn-edit" @click="fetchData(agent)">TOPOLOGY</button>
            <button v-else-if="agent.id === 'sniffer'" class="btn-action btn-edit" @click="fetchData(agent)">LIVE STREAM</button>
            <button v-else-if="['honeypot', 'auth_monitor', 'usb_monitor'].includes(agent.id)" class="btn-action btn-edit" style="color: var(--pink); border-color: var(--pink)" @click="fetchData(agent)">ALERT LOG</button>
            <button v-else class="btn-action btn-edit" @click="fetchData(agent)">FETCH DATA</button>
            
            <button class="btn-action" style="border-color: #888; color: #888;" @click="doAction(agent.id, 'remove')">REMOVE</button>
          </template>
        </div>
      </div>
    </div>

    <!-- Data Modal (Raw Text / Alerts) -->
    <div v-if="modalVisible" class="modal-overlay" @click.self="modalVisible = false">
      <div class="cyber-modal-card">
        <div class="cyber-modal-header">
          <div class="modal-title" :class="{'text-pink': isAlertAgent}">{{ isAlertAgent ? '🚨 SECURITY ALERTS' : 'AGENT DATA' }}: {{ modalAgentName }}</div>
          <button class="btn-close-modal" @click="modalVisible = false">×</button>
        </div>
        <div class="cyber-modal-body">
          <pre class="agent-data-preview" :class="{'alert-preview': isAlertAgent}">{{ modalData }}</pre>
        </div>
        <div class="cyber-modal-footer">
          <button class="btn-action" @click="modalVisible = false">CLOSE</button>
        </div>
      </div>
    </div>

    <!-- Specialized Modals -->
    <MapModal v-if="mapModalVisible" :title="modalAgentName" :dataRaw="modalData" @close="mapModalVisible = false" />
    <SnifferModal v-if="snifferModalVisible" :dataRaw="modalData" @close="snifferModalVisible = false" />
    <ScannerModal v-if="scannerModalVisible" :dataRaw="modalData" :nodeId="props.nodeId" @close="scannerModalVisible = false" />

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import MapModal from './MapModal.vue'
import SnifferModal from './SnifferModal.vue'
import ScannerModal from './ScannerModal.vue'

const props = defineProps<{
  nodeId: string
}>()

interface Agent {
  id: string
  name: string
  description: string
  installed: boolean
  running: boolean
}

const agents = ref<Agent[]>([])
const loading = ref(false)
const error = ref('')
let timer: ReturnType<typeof setInterval> | null = null

const modalVisible = ref(false)
const mapModalVisible = ref(false)
const snifferModalVisible = ref(false)
const scannerModalVisible = ref(false)
const modalAgentName = ref('')
const modalData = ref('')
const currentAgentId = ref('')

const isAlertAgent = computed(() => {
  return ['honeypot', 'auth_monitor', 'usb_monitor'].includes(currentAgentId.value)
})

async function refreshStatus() {
  if (!props.nodeId) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/agents/status`, {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    if (!res.ok) throw new Error("Failed to fetch agent status")
    const data = await res.json()
    agents.value = data.agents || []
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function doAction(agentId: string, action: 'install' | 'start' | 'stop' | 'remove') {
  error.value = ''
  try {
    const method = action === 'remove' ? 'DELETE' : 'POST'
    const endpoint = action === 'remove' 
      ? `/api/nodes/${props.nodeId}/agents/${agentId}`
      : `/api/nodes/${props.nodeId}/agents/${agentId}/${action}`
      
    const res = await fetch(endpoint, {
      method,
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || data.message || `Action ${action} failed`)
    
    // Refresh to show updated status
    await refreshStatus()
  } catch (err: any) {
    error.value = err.message
  }
}

async function fetchData(agent: any) {
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/agents/${agent.id}/fetch`, {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || data.message || "Fetch failed")
    
    modalAgentName.value = agent.name
    currentAgentId.value = agent.id
    
    if (!data.data || data.data.trim() === '') {
      modalData.value = "No data recorded yet."
      modalVisible.value = true
    } else {
      modalData.value = data.data
      
      // Hide all first
      mapModalVisible.value = false
      snifferModalVisible.value = false
      scannerModalVisible.value = false
      modalVisible.value = false

      if (agent.id === 'tracker') {
        mapModalVisible.value = true
      } else if (agent.id === 'sniffer') {
        snifferModalVisible.value = true
      } else if (agent.id === 'scanner') {
        scannerModalVisible.value = true
      } else {
        modalVisible.value = true
      }
    }
  } catch (err: any) {
    modalData.value = "Error fetching data: " + err.message
    modalVisible.value = true
  }
}

onMounted(() => {
  refreshStatus()
  // Auto refresh every 10 seconds
  timer = setInterval(refreshStatus, 10000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.agents-panel {
  padding: 20px;
  color: #a0a0a0;
  height: 100%;
  overflow-y: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 255, 204, 0.2);
}

.panel-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: 20px;
  color: #00ffcc;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(0, 255, 204, 0.3);
}

.error-banner {
  background: rgba(255, 51, 102, 0.1);
  color: #ff3366;
  border: 1px solid rgba(255, 51, 102, 0.3);
  padding: 10px 15px;
  margin-bottom: 20px;
  font-family: monospace;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.agent-card {
  background: rgba(10, 15, 20, 0.8);
  border: 1px solid rgba(0, 255, 204, 0.2);
  border-radius: 4px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.agent-title {
  font-size: 16px;
  color: #e0e0e0;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: bold;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 5px currentColor;
}

.dot-green { color: #00ffcc; background: #00ffcc; }
.dot-red { color: #ff3366; background: #ff3366; }
.dot-gray { color: #555; background: #555; box-shadow: none; }

.text-green { color: #00ffcc; }
.text-red { color: #ff3366; }
.text-gray { color: #888; }

.agent-status-text {
  font-family: monospace;
  font-size: 12px;
  font-weight: bold;
}

.agent-desc {
  font-size: 13px;
  color: #888;
  margin-bottom: 20px;
  flex-grow: 1;
}

.agent-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-action { background: rgba(12, 18, 32, 0.6); border: 1px solid var(--border); color: var(--textwh); padding: 6px 12px; border-radius: var(--r); font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; cursor: pointer; transition: all .2s; }
.btn-action:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); box-shadow: var(--shadow-c); background: rgba(0, 229, 255, 0.1); }
.btn-action:disabled { opacity: .4; cursor: not-allowed; }

.btn-danger { border-color: var(--pink); color: var(--pink); }
.btn-danger:hover:not(:disabled) {
  background: rgba(255, 45, 110, 0.2);
  border-color: #ff0055;
  color: #ff0055;
  box-shadow: 0 0 15px #ff0055, inset 0 0 10px rgba(255, 0, 85, 0.3);
  text-shadow: 0 0 5px #ff0055;
}

.btn-edit { border-color: var(--cyan-d); color: var(--cyan); }

.agent-data-preview {
  background: rgba(0,0,0,0.5);
  padding: 15px;
  border: 1px solid #333;
  color: #fff;
  font-family: var(--font-co);
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 50vh;
  overflow-y: auto;
}

.alert-preview {
  border-color: rgba(255, 45, 110, 0.5);
  color: #ffb3c6;
}
.text-pink {
  color: var(--pink) !important;
  text-shadow: 0 0 10px var(--pink);
}
</style>
