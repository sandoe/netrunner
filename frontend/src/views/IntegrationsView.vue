<template>
  <div class="integrations-container">
    <div class="header">
      <h2><span class="glitch-text" data-text="ENTERPRISE">ENTERPRISE</span> INTEGRATIONS</h2>
      <p class="subtitle">Manage external webhooks and SIEM connections</p>
    </div>

    <div class="top-actions">
      <button class="cyber-button primary" @click="openModal()">+ Add Integration</button>
    </div>

    <div v-if="loading" class="loading">Loading integrations...</div>
    <div v-else class="integrations-grid">
      <div v-for="integration in integrations" :key="integration.id" class="integration-card">
        <div class="card-header">
          <div class="provider-icon">{{ getIcon(integration.provider) }}</div>
          <div class="status-toggle">
            <span :class="['status-dot', integration.is_active ? 'active' : 'inactive']"></span>
            {{ integration.is_active ? 'ENABLED' : 'DISABLED' }}
          </div>
        </div>
        
        <div class="card-body">
          <h3>{{ integration.name }}</h3>
          <p class="url-text">{{ integration.url }}</p>
        </div>

        <div class="card-actions">
          <button class="action-btn" @click="testIntegration(integration.id)" title="Send Test Payload">Test</button>
          <button class="action-btn danger" @click="deleteIntegration(integration.id)">Delete</button>
        </div>
      </div>

      <!-- NetBox Sync Card -->
      <div class="integration-card netbox-card">
        <div class="card-header">
          <div class="provider-icon">📦</div>
          <div class="status-toggle">
            <span class="status-dot active" style="background: var(--cyan); box-shadow: var(--shadow-c);"></span>
            NETBOX SYNC
          </div>
        </div>
        
        <div class="card-body">
          <h3>Synchronize Inventory</h3>
          <div class="form-group nb-form">
            <label>NetBox URL</label>
            <input type="text" v-model="netboxUrl" placeholder="https://netbox.local">
          </div>
          <div class="form-group nb-form">
            <label>API Token</label>
            <input type="password" v-model="netboxToken" placeholder="Token">
          </div>
          <div v-if="netboxStatus" :class="['status-msg', netboxStatusType]">
            {{ netboxStatus }}
          </div>
        </div>

        <div class="card-actions">
          <button class="action-btn sync-btn" @click="syncNetbox" :disabled="netboxLoading">
            <span v-if="netboxLoading" class="spinner"></span>
            <span v-else>Sync to NetBox</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal for new integration -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal">
        <h3>New Integration</h3>
        <div class="form-group">
          <label>Provider</label>
          <select v-model="form.provider">
            <option value="slack">Slack Webhook</option>
            <option value="splunk">Splunk HEC</option>
            <option value="teams">Microsoft Teams</option>
            <option value="webhook">Custom Webhook</option>
          </select>
        </div>
        <div class="form-group">
          <label>Name</label>
          <input type="text" v-model="form.name" placeholder="e.g. SecOps Slack Channel">
        </div>
        <div class="form-group">
          <label>Webhook URL</label>
          <input type="text" v-model="form.url" placeholder="https://hooks.slack.com/services/...">
        </div>
        <div class="modal-actions">
          <button class="cyber-button secondary" @click="showModal = false">Cancel</button>
          <button class="cyber-button primary" @click="saveIntegration">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  getIntegrationsIntegrationsGet,
  createIntegrationIntegrationsPost,
  deleteIntegrationIntegrationsIntegrationIdDelete,
  testIntegrationIntegrationsIntegrationIdTestPost
} from '@/api_client'

const integrations = ref<any[]>([])
const loading = ref(true)
const showModal = ref(false)

const form = ref({
  provider: 'slack',
  name: '',
  url: '',
  is_active: true
})

const netboxUrl = ref('')
const netboxToken = ref('')
const netboxLoading = ref(false)
const netboxStatus = ref('')
const netboxStatusType = ref('')

const fetchIntegrations = async () => {
  try {
    loading.value = true
    const res = await getIntegrationsIntegrationsGet()
    integrations.value = res.data || []
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchIntegrations)

const getIcon = (provider: string) => {
  const map: any = {
    'slack': '💬',
    'splunk': '🔥',
    'teams': '🛡️',
    'webhook': '🔗'
  }
  return map[provider] || '🔗'
}

const openModal = () => {
  form.value = { provider: 'slack', name: '', url: '', is_active: true }
  showModal.value = true
}

const saveIntegration = async () => {
  try {
    await createIntegrationIntegrationsPost({ body: form.value })
    showModal.value = false
    fetchIntegrations()
  } catch (err) {
    console.error(err)
    alert("Error saving integration")
  }
}

const deleteIntegration = async (id: string) => {
  if(!confirm("Are you sure?")) return;
  try {
    await deleteIntegrationIntegrationsIntegrationIdDelete({ path: { integration_id: id } })
    fetchIntegrations()
  } catch (err) {
    console.error(err)
  }
}

const testIntegration = async (id: string) => {
  try {
    await testIntegrationIntegrationsIntegrationIdTestPost({ path: { integration_id: id } })
    alert("Test payload dispatched successfully!")
  } catch(err) {
    alert("Error sending test payload")
  }
}

const syncNetbox = async () => {
  if (!netboxUrl.value || !netboxToken.value) {
    netboxStatus.value = 'Please provide URL and Token.'
    netboxStatusType.value = 'error'
    return
  }
  
  netboxLoading.value = true
  netboxStatus.value = ''
  
  try {
    const devicesRes = await fetch('/api/netbox_sync/devices', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ url: netboxUrl.value, token: netboxToken.value })
    })
    if (!devicesRes.ok) throw new Error('Devices sync failed')
    
    const ipsRes = await fetch('/api/netbox_sync/ips', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ url: netboxUrl.value, token: netboxToken.value })
    })
    if (!ipsRes.ok) throw new Error('IPs sync failed')
    
    netboxStatus.value = 'Sync completed successfully!'
    netboxStatusType.value = 'success'
  } catch (err: any) {
    console.error(err)
    netboxStatus.value = err.message || 'Sync failed.'
    netboxStatusType.value = 'error'
  } finally {
    netboxLoading.value = false
  }
}
</script>

<style scoped>
.integrations-container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  color: #fff;
}

.header {
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--accent-blue);
  padding-bottom: 1rem;
}
.header h2 {
  font-family: 'Orbitron', sans-serif;
  color: var(--accent-blue);
  margin: 0;
  font-size: 2rem;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

.top-actions {
  margin-bottom: 2rem;
  display: flex;
  justify-content: flex-end;
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.integration-card {
  background: rgba(10, 15, 30, 0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.provider-icon {
  font-size: 2rem;
}

.status-toggle {
  font-size: 0.8rem;
  color: #aaa;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: #555;
}
.status-dot.active { background: #00f0ff; box-shadow: 0 0 8px #00f0ff; }

.card-body h3 {
  margin: 0 0 0.5rem 0;
  color: #fff;
}
.url-text {
  font-family: monospace;
  color: #888;
  font-size: 0.85rem;
  word-break: break-all;
  margin: 0;
}

.card-actions {
  margin-top: auto;
  display: flex;
  gap: 1rem;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 1rem;
}

.action-btn {
  background: none;
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  flex: 1;
}
.action-btn:hover { background: rgba(255,255,255,0.1); }
.action-btn.danger { border-color: rgba(255, 51, 102, 0.5); color: #ff3366; }
.action-btn.danger:hover { background: rgba(255, 51, 102, 0.1); }

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #0d1117;
  padding: 2rem;
  border-radius: 8px;
  width: 400px;
  border: 1px solid var(--accent-blue);
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
}

.form-group {
  margin-bottom: 1.5rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #aaa;
}
.form-group input, .form-group select {
  width: 100%;
  padding: 0.8rem;
  background: rgba(0,0,0,0.5);
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
  border-radius: 4px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}

/* NetBox specific styles */
.netbox-card {
  background: var(--bg3, rgba(12, 18, 32, 0.8));
  border: 1px solid var(--border2, rgba(36, 51, 82, 0.5));
}
.netbox-card h3 {
  color: var(--cyan, #00e5ff);
  margin-bottom: 1rem;
}
.nb-form {
  margin-bottom: 1rem;
}
.nb-form label {
  color: var(--textbr, #a8b2c1);
  display: block;
  margin-bottom: 0.3rem;
  font-size: 0.9rem;
}
.nb-form input {
  background: var(--bg, #05080f);
  border: 1px solid var(--border, #1a2540);
  color: var(--textwh, #e2e8f0);
  padding: 0.6rem;
  border-radius: var(--r, 6px);
  width: 100%;
}
.nb-form input:focus {
  border-color: var(--cyan, #00e5ff);
  outline: none;
  box-shadow: var(--shadow-c, 0 0 10px rgba(0, 229, 255, 0.2));
}
.sync-btn {
  background: var(--border2, #243352);
  color: var(--textwh, #e2e8f0);
  border: 1px solid var(--cyan, #00e5ff);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
}
.sync-btn:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.1);
  box-shadow: var(--shadow-c, 0 0 10px rgba(0, 229, 255, 0.2));
}
.sync-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.status-msg {
  margin-top: 1rem;
  padding: 0.5rem;
  border-radius: var(--r, 6px);
  font-size: 0.9rem;
  text-align: center;
}
.status-msg.success {
  color: var(--green, #00ff9d);
  border: 1px solid var(--green, #00ff9d);
  background: rgba(0, 255, 157, 0.1);
}
.status-msg.error {
  color: var(--pink, #ff2d6e);
  border: 1px solid var(--pink, #ff2d6e);
  background: rgba(255, 45, 110, 0.1);
}
</style>
