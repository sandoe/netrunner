<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content cyber-panel" role="dialog" aria-modal="true" aria-labelledby="vpn-manager-title">
      <div class="modal-header">
        <h2 class="title" id="vpn-manager-title">WIREGUARD VPN MANAGER</h2>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body" v-if="!loading">
        <div v-if="error" class="error-box">
          {{ error }}
        </div>

        <div class="server-status">
          <div class="status-indicator" :class="{ 'active': status?.status === 'active' }"></div>
          <div class="status-text">
            <span>VPN SERVICE: {{ status?.status?.toUpperCase() || 'UNKNOWN' }}</span>
            <span class="endpoint">ENDPOINT: {{ status?.server_endpoint }}</span>
          </div>
        </div>

        <div class="action-bar">
          <input type="text" v-model="newClientName" placeholder="Client Name (e.g. Elev-01)" class="cyber-input" @keyup.enter="createClient" />
          <button class="btn-tool btn-add" @click="createClient" :disabled="!newClientName || creating">
            <span v-if="creating" class="spinner"></span>
            <span v-else>ADD CLIENT</span>
          </button>
        </div>

        <div class="client-list">
          <div class="section-title">ACTIVE PEERS ({{ status?.peers?.length || 0 }})</div>
          
          <div class="table-header" v-if="status?.peers?.length">
            <span class="col-ip">ALLOWED IPs</span>
            <span class="col-end">ENDPOINT</span>
            <span class="col-pub">PUBLIC KEY</span>
            <span class="col-act">ACTION</span>
          </div>

          <div class="peer-item" v-for="peer in status?.peers" :key="peer.pubkey">
            <span class="col-ip">{{ peer.allowed_ips }}</span>
            <span class="col-end">{{ peer.endpoint || 'Offline' }}</span>
            <span class="col-pub" :title="peer.pubkey">{{ truncate(peer.pubkey) }}</span>
            <span class="col-act">
              <button class="btn-icon btn-del" @click="deleteClient(peer.pubkey)" title="Remove Peer">✖</button>
            </span>
          </div>
          <div class="empty-state" v-if="!status?.peers?.length">
            No active VPN peers.
          </div>
        </div>
      </div>
      <div class="modal-body" v-else>
        <div class="loading">Loading VPN status...</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['close'])

onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))
function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

const loading = ref(true)
const creating = ref(false)
const error = ref('')
const newClientName = ref('')
const status = ref<any>(null)

async function fetchStatus() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/vpn/status', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Failed to fetch status')
    status.value = data
  } catch (e: any) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

async function createClient() {
  if (!newClientName.value) return
  creating.value = true
  error.value = ''
  try {
    const res = await fetch('/api/vpn/clients', {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${localStorage.getItem('nr_token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name: newClientName.value })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Failed to create client')
    
    downloadFile(`${data.name}.conf`, data.config)
    newClientName.value = ''
    await fetchStatus()
  } catch (e: any) {
    error.value = String(e)
  } finally {
    creating.value = false
  }
}

async function deleteClient(pubkey: string) {
  if (!confirm("Are you sure you want to revoke this client's access?")) return
  try {
    const res = await fetch(`/api/vpn/clients/${encodeURIComponent(pubkey)}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Failed to delete client')
    
    await fetchStatus()
  } catch (e: any) {
    alert(`Error: ${e}`)
  }
}

function truncate(str: string) {
  if (str.length <= 16) return str
  return str.substring(0, 8) + '...' + str.substring(str.length - 8)
}

function downloadFile(filename: string, content: string) {
  const element = document.createElement('a')
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content))
  element.setAttribute('download', filename)
  element.style.display = 'none'
  document.body.appendChild(element)
  element.click()
  document.body.removeChild(element)
}

onMounted(() => {
  fetchStatus()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: rgba(0, 229, 255, 0.1);
  border-bottom: 1px solid var(--border);
}

.title {
  font-family: var(--font-hd);
  font-size: 14px;
  color: var(--cyan);
  margin: 0;
  letter-spacing: 2px;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text);
  font-size: 24px;
  cursor: pointer;
}

.btn-close:hover {
  color: var(--pink);
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.server-status {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg2);
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: 4px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--pink);
  box-shadow: 0 0 10px var(--pink);
}

.status-indicator.active {
  background: var(--green);
  box-shadow: 0 0 10px var(--green);
}

.status-text {
  display: flex;
  flex-direction: column;
  font-family: var(--font-hd);
  font-size: 12px;
  color: var(--textwh);
  gap: 4px;
}
.endpoint {
  color: var(--textbr);
  font-family: var(--font-co);
}

.action-bar {
  display: flex;
  gap: 10px;
}

.cyber-input {
  flex: 1;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--textwh);
  padding: 10px;
  font-family: var(--font-ui);
  font-size: 13px;
  outline: none;
}
.cyber-input:focus {
  border-color: var(--cyan);
}

.btn-add {
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 0 20px;
  cursor: pointer;
  font-family: var(--font-hd);
  font-size: 12px;
  transition: all 0.2s;
}
.btn-add:hover:not(:disabled) {
  background: var(--cyan);
  color: #000;
  box-shadow: 0 0 15px var(--cyan);
}
.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.client-list {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--textbr);
  letter-spacing: 1px;
}

.table-header, .peer-item {
  display: flex;
  padding: 8px;
  border-bottom: 1px solid var(--border);
  font-family: var(--font-co);
  font-size: 12px;
  align-items: center;
}
.table-header {
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 10px;
  border-bottom-color: rgba(0,229,255,0.3);
}

.peer-item {
  color: var(--textwh);
}

.col-ip { flex: 1; }
.col-end { flex: 1; color: var(--text); }
.col-pub { flex: 1.5; color: var(--text); }
.col-act { width: 40px; text-align: center; }

.btn-icon {
  background: none;
  border: none;
  color: var(--text);
  cursor: pointer;
  font-size: 14px;
}
.btn-del:hover {
  color: var(--pink);
  text-shadow: 0 0 8px var(--pink);
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 13px;
  font-style: italic;
}

.error-box {
  background: rgba(255, 45, 110, 0.1);
  border: 1px solid var(--pink);
  color: var(--pink);
  padding: 12px;
  font-family: var(--font-co);
  font-size: 12px;
  border-radius: 4px;
}
.loading {
  text-align: center;
  color: var(--cyan);
  font-family: var(--font-hd);
  padding: 40px;
}
button:focus-visible, .btn-action:focus-visible, .btn-close:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
</style>
