<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'

const store = useNodesStore()
const selectedNodeId = ref<string>('')

const target = ref('')
const profile = ref('quick')
const sudoPass = ref('')

const isScanning = ref(false)
const scanError = ref('')
const scanSuccess = ref(false)

const discoveredHosts = ref<any[]>([])
const importedCount = ref(0)
const isImporting = ref(false)

onMounted(() => {
  store.refresh()
})

const activeNodes = computed(() => store.nodeList)

async function startScan() {
  if (!selectedNodeId.value) {
    scanError.value = 'Please select a scanning agent.'
    return
  }
  if (!target.value) {
    scanError.value = 'Please enter a target (e.g. 192.168.1.0/24).'
    return
  }

  isScanning.value = true
  scanError.value = ''
  scanSuccess.value = false
  discoveredHosts.value = []
  importedCount.value = 0

  try {
    const res = await api.runRecon(selectedNodeId.value, target.value, profile.value, sudoPass.value)
    if (res.hosts && res.hosts.length > 0) {
      discoveredHosts.value = res.hosts
      scanSuccess.value = true
    } else {
      scanError.value = 'Scan completed, but no hosts were found.'
    }
  } catch (e: any) {
    scanError.value = e.message || String(e)
  } finally {
    isScanning.value = false
  }
}

async function importToTopology() {
  if (discoveredHosts.value.length === 0) return
  isImporting.value = true
  try {
    const res = await api.importRecon(selectedNodeId.value, discoveredHosts.value)
    importedCount.value = res.imported
    store.refresh() // Refresh local store
  } catch (e: any) {
    scanError.value = 'Import failed: ' + (e.message || String(e))
  } finally {
    isImporting.value = false
  }
}

function getOsIcon(os: string) {
  const l = os.toLowerCase()
  if (l.includes('win')) return '🪟'
  if (l.includes('linux')) return '🐧'
  if (l.includes('mac') || l.includes('apple')) return '🍎'
  if (l.includes('cisco')) return '📡'
  return '🖥️'
}
</script>

<template>
  <div class="recon-container">
    <div class="recon-header cyber-panel">
      <h2>NETWORK RECONNAISSANCE</h2>
      <p>Engage Nmap scanning engines to auto-discover network topologies.</p>
    </div>

    <div class="recon-layout">
      <!-- Left sidebar for controls -->
      <div class="recon-controls cyber-panel">
        <h3 class="panel-title">SCAN PARAMETERS</h3>
        
        <div class="form-group">
          <label>Scanning Agent (Node)</label>
          <select v-model="selectedNodeId" class="cyber-input">
            <option value="" disabled>Select an agent node...</option>
            <option v-for="n in activeNodes" :key="n.id" :value="n.id">
              {{ n.name }} ({{ n.host }})
            </option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Target IP/Subnet</label>
          <input v-model="target" type="text" class="cyber-input" placeholder="e.g. 192.168.1.0/24 or 10.0.0.5" />
        </div>
        
        <div class="form-group">
          <label>Intensity Profile</label>
          <select v-model="profile" class="cyber-input">
            <option value="quick">Quick Scan (-F -T4)</option>
            <option value="comprehensive">Comprehensive (-p- -sV -O)</option>
            <option value="vuln">Vulnerability Scan (--script vuln)</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Sudo Password (Optional)</label>
          <input v-model="sudoPass" type="password" class="cyber-input" placeholder="Required for OS/Vuln scans" />
        </div>

        <button 
          class="btn-engage" 
          :disabled="isScanning || !selectedNodeId || !target"
          @click="startScan"
        >
          {{ isScanning ? 'SCANNING IN PROGRESS...' : 'ENGAGE SCAN' }}
        </button>

        <div v-if="scanError" class="scan-error">
          {{ scanError }}
        </div>
      </div>

      <!-- Right area for results and radar -->
      <div class="recon-results cyber-panel">
        
        <div v-if="isScanning" class="radar-container">
          <div class="radar">
            <div class="radar-sweep"></div>
          </div>
          <p class="radar-text">SCANNING SECTOR...</p>
        </div>
        
        <div v-else-if="discoveredHosts.length > 0" class="results-container">
          <div class="results-header">
            <h3>DISCOVERED HOSTS ({{ discoveredHosts.length }})</h3>
            <button 
              class="btn-import" 
              @click="importToTopology"
              :disabled="isImporting || importedCount > 0"
            >
              <span v-if="importedCount > 0">✓ IMPORTED ({{ importedCount }})</span>
              <span v-else-if="isImporting">IMPORTING...</span>
              <span v-else>IMPORT TO TOPOLOGY</span>
            </button>
          </div>
          
          <div class="host-grid">
            <div v-for="(h, idx) in discoveredHosts" :key="idx" class="host-card">
              <div class="host-card-header">
                <span class="os-icon">{{ getOsIcon(h.os) }}</span>
                <span class="host-ip">{{ h.ip }}</span>
              </div>
              
              <div class="host-details">
                <div v-if="h.hostnames && h.hostnames.length > 0" class="detail-row">
                  <span class="lbl">NAME:</span> <span class="val">{{ h.hostnames[0] }}</span>
                </div>
                <div v-if="h.mac" class="detail-row">
                  <span class="lbl">MAC:</span> <span class="val">{{ h.mac }}</span>
                </div>
                <div class="detail-row">
                  <span class="lbl">OS:</span> <span class="val">{{ h.os }}</span>
                </div>
              </div>
              
              <div class="ports-container">
                <span class="lbl">OPEN PORTS:</span>
                <div class="port-tags">
                  <span v-if="h.ports.length === 0" class="no-ports">None detected</span>
                  <span 
                    v-for="p in h.ports" 
                    :key="p.port" 
                    class="port-tag"
                  >
                    {{ p.port }}/{{ p.service }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="empty-state">
          <div class="empty-icon">📡</div>
          <p>Awaiting scan initialization...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.recon-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.recon-header {
  padding: 20px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.recon-header h2 {
  color: var(--cyan);
  margin: 0 0 8px 0;
  font-family: var(--font-hd);
  letter-spacing: 2px;
}
.recon-header p {
  margin: 0;
  color: var(--textbr);
  font-size: 14px;
}

.recon-layout {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.recon-controls {
  width: 320px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.panel-title {
  color: var(--cyan);
  margin: 0;
  font-size: 14px;
  font-family: var(--font-hd);
  letter-spacing: 1px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  color: var(--textbr);
  font-size: 12px;
  text-transform: uppercase;
  font-family: var(--font-hd);
}
.cyber-input {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--textwh);
  padding: 10px;
  border-radius: 4px;
  font-family: var(--font-co);
  outline: none;
}
.cyber-input:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}

.btn-engage {
  margin-top: 10px;
  background: rgba(255, 0, 85, 0.1);
  color: var(--pink);
  border: 1px solid var(--pink);
  padding: 12px;
  border-radius: 4px;
  font-family: var(--font-hd);
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.btn-engage:not(:disabled):hover {
  background: var(--pink);
  color: var(--bg);
  box-shadow: 0 0 15px rgba(255, 0, 85, 0.4);
}
.btn-engage:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: transparent;
  border-color: var(--border);
  color: var(--text);
}

.scan-error {
  margin-top: 10px;
  padding: 12px;
  background: rgba(255, 45, 110, 0.1);
  border: 1px solid var(--pink);
  color: var(--pink);
  border-radius: 4px;
  font-size: 13px;
}

.recon-results {
  flex: 1;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow-y: auto;
}

/* Radar Animation */
.radar-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.radar {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 2px solid var(--cyan);
  background: rgba(0, 229, 255, 0.05);
  position: relative;
  overflow: hidden;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
}
.radar::before {
  content: '';
  position: absolute;
  top: 50%; left: 0; right: 0;
  height: 1px;
  background: rgba(0, 229, 255, 0.3);
}
.radar::after {
  content: '';
  position: absolute;
  top: 0; bottom: 0; left: 50%;
  width: 1px;
  background: rgba(0, 229, 255, 0.3);
}
.radar-sweep {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100px;
  height: 100px;
  background: linear-gradient(45deg, rgba(0,229,255,1) 0%, rgba(0,229,255,0) 70%);
  transform-origin: 0% 0%;
  animation: radar-spin 2s linear infinite;
}
@keyframes radar-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.radar-text {
  margin-top: 20px;
  color: var(--cyan);
  font-family: var(--font-hd);
  letter-spacing: 2px;
  animation: pulse 1s infinite alternate;
}
@keyframes pulse {
  from { opacity: 0.5; }
  to { opacity: 1; }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text);
  font-family: var(--font-hd);
  letter-spacing: 1px;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 10px;
  opacity: 0.3;
}

/* Results Grid */
.results-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.results-header h3 {
  margin: 0;
  color: var(--cyan);
  font-family: var(--font-hd);
}
.btn-import {
  background: rgba(106, 190, 48, 0.1);
  color: var(--green);
  border: 1px solid var(--green);
  padding: 8px 16px;
  border-radius: 4px;
  font-family: var(--font-hd);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-import:not(:disabled):hover {
  background: var(--green);
  color: var(--bg);
  box-shadow: 0 0 10px rgba(106, 190, 48, 0.3);
}
.btn-import:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.host-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
  overflow-y: auto;
}
.host-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
  transition: all 0.2s;
}
.host-card:hover {
  border-color: var(--cyan);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.1);
}
.host-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(255,255,255,0.1);
}
.os-icon {
  font-size: 20px;
}
.host-ip {
  font-family: var(--font-hd);
  color: var(--textwh);
  font-size: 16px;
  font-weight: bold;
}
.host-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}
.lbl {
  color: var(--text);
  font-family: var(--font-hd);
}
.val {
  color: var(--textbr);
  font-family: var(--font-co);
}

.ports-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.port-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.port-tag {
  background: rgba(0, 229, 255, 0.1);
  color: var(--cyan);
  border: 1px solid rgba(0, 229, 255, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-family: var(--font-co);
}
.no-ports {
  color: var(--text);
  font-size: 10px;
  font-style: italic;
}
</style>
