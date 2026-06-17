<template>
  <div class="bruteforce-room">
    <div class="bf-header">
      <div class="bf-title">KAIROS CYBERNETICS // BRUTE FORCE ATTACK MODULE</div>
      <div class="bf-subtitle">SYSTEM // ACTIVE | ADMIN: LOCAL_USER</div>
    </div>

    <div class="bf-grid">
      
      <!-- PANEL 1: TARGET CONFIGURATION -->
      <div class="bf-panel target-config">
        <div class="panel-header">
          TARGET CONFIGURATION <span class="icon float-right">⚙️</span>
        </div>
        <div class="panel-body">
          <div class="form-group">
            <label>TARGET NODE</label>
            <select v-model="targetNode" class="cyber-select glow-focus">
              <option disabled value="">-- SELECT TARGET NODE --</option>
              <option v-for="n in store.nodeList" :key="n.id" :value="n.id">
                {{ n.name }} ({{ n.host }})
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>TARGET SERVICE</label>
            <select v-model="targetService" class="cyber-select glow-focus">
              <option value="ssh">SSH (Port 22)</option>
              <option value="ftp">FTP (Port 21)</option>
              <option value="mysql">MySQL (Port 3306)</option>
              <option value="postgres">PostgreSQL (Port 5432)</option>
              <option value="rdp">RDP (Port 3389)</option>
            </select>
          </div>

          <div class="form-group mt-3" v-if="attackMode === 'wordlist'">
            <label>WORDLIST SELECTION</label>
            <select v-model="targetWordlist" class="cyber-select glow-focus text-cyan">
              <option disabled value="">-- SELECT WORDLIST --</option>
              <option v-for="w in wordlists" :key="w" :value="w">{{ w }}</option>
            </select>
            
            <div class="upload-area mt-2">
              <input type="file" ref="fileInput" @change="handleFileUpload" accept=".txt" style="display: none" />
              <button class="btn-action btn-upload" @click="$refs.fileInput.click()" :disabled="uploading">
                {{ uploading ? 'UPLOADING...' : 'UPLOAD NEW (.txt)' }}
              </button>
            </div>
            
            <div class="wordlist-list mt-3">
              <div v-for="w in wordlists" :key="w" class="wordlist-item">
                <span class="wl-name">{{ w }}</span>
              </div>
            </div>
          </div>
          
          <div class="form-group mt-3" v-if="attackMode === 'algo'">
            <label>TARGET USERNAME</label>
            <input v-model="algoUser" type="text" class="cyber-input glow-focus" placeholder="e.g. root" />
          </div>
        </div>
      </div>

      <!-- PANEL 2: ATTACK PARAMETERS -->
      <div class="bf-panel attack-params">
        <div class="panel-header">
          ATTACK PARAMETERS <span class="icon float-right">🎛️</span>
        </div>
        <div class="panel-body">
          <div class="mode-toggles">
            <div class="toggle-row" @click="attackMode = 'wordlist'">
              <span>Dictionary Attack</span>
              <div class="cyber-toggle" :class="{ active: attackMode === 'wordlist' }"><div class="nub"></div></div>
            </div>
            <div class="toggle-row" @click="attackMode = 'algo'">
              <span>Algorithmic Generation</span>
              <div class="cyber-toggle" :class="{ active: attackMode === 'algo' }"><div class="nub"></div></div>
            </div>
          </div>
          
          <div v-if="attackMode === 'algo'" class="algo-options mt-4">
            <div class="form-group">
              <label>CHARACTER SET (e.g. aA1)</label>
              <input v-model="algoCharset" type="text" class="cyber-input glow-focus text-cyan" />
            </div>
            <div class="flex gap-2 mt-2">
              <div class="form-group flex-1">
                <label>MIN LEN</label>
                <input v-model.number="algoMin" type="number" class="cyber-input glow-focus text-cyan" />
              </div>
              <div class="form-group flex-1">
                <label>MAX LEN</label>
                <input v-model.number="algoMax" type="number" class="cyber-input glow-focus text-cyan" />
              </div>
            </div>
          </div>

          <div class="launch-container mt-auto pt-6">
            <div class="launch-ring" :class="{ disabled: !canLaunch, launching: launching }" @click="launchAttack">
              <div class="launch-inner">
                <div class="status-text">STATUS: {{ launching ? 'INITIATING' : (canLaunch ? 'READY' : 'WAITING') }}</div>
                <div class="launch-text">LAUNCH</div>
              </div>
            </div>
            <div v-if="launchError" class="text-red text-center mt-2 text-xs">{{ launchError }}</div>
          </div>
        </div>
      </div>

      <!-- PANEL 3: LIVE MONITORING -->
      <div class="bf-panel live-monitor">
        <div class="panel-header">
          LIVE MONITORING <span class="icon float-right">📊</span>
        </div>
        <div class="panel-body p-0 monitor-scroll">
          
          <div v-if="Object.keys(activeAttacks).length === 0" class="empty-state p-6 text-center">
            NO ACTIVE OPERATIONS
          </div>
          
          <div v-for="(status, nid) in activeAttacks" :key="nid" class="monitor-card">
            <div class="monitor-top">
              <div class="target-name">{{ getNodeName(String(nid)) }}</div>
              <div class="status-indicator" :class="status.status">{{ status.status.toUpperCase() }}</div>
            </div>
            
            <div class="progress-section mt-3" v-if="status.status === 'running' && status.total > 0">
              <div class="flex justify-between text-xs mb-1">
                <span class="text-gray-400">PROGRESS</span>
                <span class="text-cyan">{{ Math.round((status.progress / status.total) * 100) || 0 }}%</span>
              </div>
              <div class="neon-progress-bar">
                <div class="neon-progress-fill" :style="{ width: Math.min(100, Math.max(0, (status.progress / status.total) * 100)) + '%' }"></div>
              </div>
            </div>
            
            <div class="metrics-grid mt-4">
              <div class="metric-box">
                <div class="metric-label">TOTAL ATTEMPTS</div>
                <div class="metric-value">{{ (status.progress || 0).toLocaleString() }} <span class="text-gray-500 text-xs">/ {{ (status.total || 0).toLocaleString() }}</span></div>
              </div>
              
              <div class="metric-box">
                <div class="metric-label">ATTACKS/SEC</div>
                <div class="metric-value text-cyan">{{ getRate(String(nid)) }} <span class="text-xs">APS</span></div>
              </div>
              
              <div class="metric-box">
                <div class="metric-label">ESTIMATED ETA</div>
                <div class="metric-value">{{ status.eta !== undefined ? formatETA(status.eta) : '--:--' }}</div>
              </div>
            </div>
            
            <div class="attack-result mt-4" v-if="status.credentials">
              <div class="cred-label mb-1">CURRENT GUESSED (CRACKED)</div>
              <div class="cred-val">{{ status.credentials.username }} : {{ status.credentials.password }}</div>
            </div>
            <div class="attack-result mt-4" v-else-if="status.message">
              <div class="cred-label mb-1">LAST MESSAGE</div>
              <div class="cred-val text-gray-400" style="font-size: 0.8rem">{{ status.message }}</div>
            </div>
            
            <div class="monitor-actions mt-4">
               <button v-if="status.status === 'running'" @click="pauseAttack(String(nid))" class="btn-action-small border-orange text-orange">PAUSE</button>
               <button v-if="status.status === 'paused'" @click="resumeAttack(String(nid))" class="btn-action-small border-green text-green">RESUME</button>
               <button v-if="['running', 'paused'].includes(status.status)" @click="stopAttack(String(nid))" class="btn-action-small border-red text-red">ABORT</button>
            </div>
          </div>
          
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'

const store = useNodesStore()
const wordlists = ref<string[]>([])
const activeAttacks = ref<Record<string, any>>({})
const uploading = ref(false)
const launching = ref(false)
const launchError = ref('')
const etaTracker = ref<Record<string, { lastProgress: number, lastTime: number, rate: number }>>({})

function formatETA(seconds: number) {
  if (seconds < 0 || !isFinite(seconds)) return '--:--'
  if (seconds < 60) return `00:00:${Math.round(seconds).toString().padStart(2, '0')}`
  if (seconds < 3600) return `00:${Math.floor(seconds/60).toString().padStart(2, '0')}:${Math.round(seconds%60).toString().padStart(2, '0')}`
  return `${Math.floor(seconds/3600).toString().padStart(2, '0')}:${Math.floor((seconds%3600)/60).toString().padStart(2, '0')}:${Math.round(seconds%60).toString().padStart(2, '0')}`
}

function getRate(nid: string) {
  if (!etaTracker.value[nid] || etaTracker.value[nid].rate <= 0) return 0;
  return Math.round(etaTracker.value[nid].rate).toLocaleString();
}

const targetNode = ref('')
const targetService = ref('ssh')
const targetWordlist = ref('')

const attackMode = ref<'wordlist'|'algo'>('wordlist')
const algoUser = ref('root')
const algoCharset = ref('1') 
const algoMin = ref(1)
const algoMax = ref(4)

const fileInput = ref<HTMLInputElement | null>(null)
let pollTimer: any = null

const canLaunch = computed(() => {
  if (!targetNode.value || !targetService.value) return false
  if (attackMode.value === 'wordlist' && !targetWordlist.value) return false
  if (attackMode.value === 'algo' && (!algoUser.value || !algoCharset.value || algoMin.value < 1 || algoMax.value < algoMin.value)) return false
  return true
})

function getNodeName(id: string) {
  const node = store.nodes[id]
  return node ? node.name : id
}

async function loadWordlists() {
  try {
    wordlists.value = await api.listWordlists()
  } catch (e) {
    console.error("Failed to load wordlists", e)
  }
}

async function loadStatus() {
  try {
    const data = await api.getAttackStatus()
    const now = Date.now()
    
    for (const nid in data) {
      const status = data[nid]
      if (status.status === 'running' && status.total > 0 && status.progress > 0) {
        if (!etaTracker.value[nid]) {
          etaTracker.value[nid] = { lastProgress: status.progress, lastTime: now, rate: 0 }
        } else {
          const tracker = etaTracker.value[nid]
          const deltaProgress = status.progress - tracker.lastProgress
          const deltaTime = (now - tracker.lastTime) / 1000 
          
          if (deltaProgress > 0 && deltaTime > 0) {
             const currentRate = deltaProgress / deltaTime
             tracker.rate = tracker.rate === 0 ? currentRate : (tracker.rate * 0.7 + currentRate * 0.3)
             tracker.lastProgress = status.progress
             tracker.lastTime = now
          }
          
          if (tracker.rate > 0) {
            const remaining = status.total - status.progress
            status.eta = remaining / tracker.rate
          }
        }
      }
    }
    activeAttacks.value = data
  } catch (e) {
    console.error("Failed to get attack status", e)
  }
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  
  if (!file.name.endsWith('.txt')) {
    alert("Only .txt files are allowed")
    return
  }

  uploading.value = true
  try {
    await api.uploadWordlist(file)
    await loadWordlists()
    targetWordlist.value = file.name 
  } catch (e: any) {
    alert("Upload failed: " + e.message)
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function launchAttack() {
  if (!canLaunch.value) return
  
  launching.value = true
  launchError.value = ''
  
  try {
    let payload: any = {
      node_id: targetNode.value,
      service: targetService.value,
      attack_mode: attackMode.value
    }
    
    if (attackMode.value === 'wordlist') {
      payload.wordlist = targetWordlist.value
    } else {
      payload.algo_user = algoUser.value
      payload.algo_charset = algoCharset.value
      payload.algo_min = algoMin.value
      payload.algo_max = algoMax.value
    }
    
    await api.launchAttack(payload)
    
    targetNode.value = ''
    setTimeout(loadStatus, 1000)
  } catch (e: any) {
    launchError.value = e.message || 'Failed to launch attack'
  } finally {
    launching.value = false
  }
}

async function stopAttack(nid: string) {
  try {
    await api.stopAttack(nid)
    delete etaTracker.value[nid]
    await loadStatus()
  } catch (e: any) {
    alert("Failed to stop attack: " + e.message)
  }
}

async function pauseAttack(nid: string) {
  try {
    await api.pauseAttack(nid)
    await loadStatus()
  } catch (e: any) {
    alert("Failed to pause attack: " + e.message)
  }
}

async function resumeAttack(nid: string) {
  try {
    if (etaTracker.value[nid]) {
      etaTracker.value[nid].lastTime = Date.now()
    }
    await api.resumeAttack(nid)
    await loadStatus()
  } catch (e: any) {
    alert("Failed to resume attack: " + e.message)
  }
}

onMounted(() => {
  loadWordlists()
  loadStatus()
  pollTimer = setInterval(loadStatus, 2000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

.bruteforce-room {
  padding: 20px 30px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--textwh);
  font-family: 'Inter', sans-serif;
}

.bf-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0,229,255,0.2);
  padding-bottom: 10px;
}
.bf-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 1.2rem;
  color: #fff;
  letter-spacing: 2px;
}
.bf-subtitle {
  font-family: 'Orbitron', sans-serif;
  color: var(--cyan);
  font-size: 0.8rem;
  letter-spacing: 1px;
}

.bf-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1.5fr;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

/* Glassmorphism Panels */
.bf-panel {
  background: rgba(10, 15, 24, 0.4);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.02), 0 10px 30px rgba(0,0,0,0.5);
}

.panel-header {
  background: rgba(0, 229, 255, 0.05);
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  padding: 12px 20px;
  font-family: 'Orbitron', sans-serif;
  font-weight: 600;
  color: var(--textwh);
  font-size: 0.9rem;
  letter-spacing: 1px;
}

.panel-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 15px;
}
.form-group label {
  font-size: 0.75rem;
  color: var(--text);
  letter-spacing: 1px;
}

/* Inputs */
.cyber-select, .cyber-input {
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--border2);
  color: var(--textwh);
  padding: 10px 12px;
  border-radius: 4px;
  font-family: 'Inter', sans-serif;
  outline: none;
  width: 100%;
  transition: all 0.3s ease;
}
.glow-focus:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 10px rgba(0,229,255,0.2);
  background: rgba(0,229,255,0.05);
}
.text-cyan { color: var(--cyan); }

/* File Upload */
.upload-area { margin-bottom: 10px; }
.btn-upload {
  width: 100%;
  padding: 10px;
  background: transparent;
  border: 1px dashed var(--cyan-d);
  color: var(--cyan);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
  font-size: 0.8rem;
}
.btn-upload:hover:not(:disabled) {
  background: rgba(0,229,255,0.1);
  border-color: var(--cyan);
}

.wordlist-list {
  background: rgba(0,0,0,0.2);
  border: 1px solid var(--border2);
  border-radius: 4px;
  padding: 10px;
  max-height: 150px;
  overflow-y: auto;
}
.wordlist-item {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: var(--textbr);
  padding: 4px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.wordlist-item:last-child { border-bottom: none; }

/* Toggles */
.mode-toggles {
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  color: var(--textwh);
  font-size: 0.9rem;
}
.cyber-toggle {
  width: 40px;
  height: 20px;
  border-radius: 10px;
  background: rgba(255,255,255,0.1);
  border: 1px solid var(--border2);
  position: relative;
  transition: all 0.3s;
}
.cyber-toggle .nub {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--text);
  position: absolute;
  top: 2px;
  left: 3px;
  transition: all 0.3s;
}
.cyber-toggle.active {
  background: rgba(0,229,255,0.2);
  border-color: var(--cyan);
}
.cyber-toggle.active .nub {
  background: var(--cyan);
  left: 21px;
  box-shadow: 0 0 8px var(--cyan);
}

/* Utilities */
.mt-2 { margin-top: 0.5rem; }
.mt-3 { margin-top: 1rem; }
.mt-4 { margin-top: 1.5rem; }
.mt-auto { margin-top: auto; }
.pt-6 { padding-top: 1.5rem; }
.mb-1 { margin-bottom: 0.25rem; }
.gap-2 { gap: 0.5rem; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.justify-between { justify-content: space-between; }
.text-xs { font-size: 0.75rem; }
.text-center { text-align: center; }
.text-gray-400 { color: #9ca3af; }
.text-gray-500 { color: #6b7280; }
.text-red { color: var(--pink); }

/* Circular Launch Button */
.launch-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.launch-ring {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  padding: 4px;
  background: linear-gradient(135deg, var(--pink), var(--purple));
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 0 20px rgba(255,45,110,0.2);
  position: relative;
}
.launch-ring::before {
  content: '';
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 1px solid rgba(255,45,110,0.3);
  animation: pulse-ring 2s infinite cubic-bezier(0.215, 0.61, 0.355, 1);
}
@keyframes pulse-ring {
  0% { transform: scale(0.9); opacity: 1; }
  100% { transform: scale(1.3); opacity: 0; }
}
.launch-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--bg2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  border: 2px solid rgba(0,0,0,0.5);
  transition: all 0.2s;
}
.status-text {
  font-size: 0.6rem;
  color: var(--pink);
  margin-bottom: 5px;
  font-family: 'JetBrains Mono', monospace;
}
.launch-text {
  font-family: 'Orbitron', sans-serif;
  font-size: 1.2rem;
  font-weight: bold;
  color: #fff;
  letter-spacing: 1px;
}
.launch-ring:hover:not(.disabled) .launch-inner {
  background: rgba(255,45,110,0.1);
}
.launch-ring:hover:not(.disabled) {
  box-shadow: 0 0 30px rgba(255,45,110,0.5);
  transform: scale(1.05);
}
.launch-ring.disabled {
  background: var(--border2);
  cursor: not-allowed;
  box-shadow: none;
}
.launch-ring.disabled::before { display: none; }
.launch-ring.disabled .status-text { color: var(--text); }
.launch-ring.disabled .launch-text { color: var(--text); }
.launch-ring.launching {
  animation: spin 1s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }
.launch-ring.launching .launch-inner { animation: spin-reverse 1s linear infinite; }
@keyframes spin-reverse { 100% { transform: rotate(-360deg); } }

/* Live Monitor Cards */
.p-0 { padding: 0; }
.monitor-scroll { padding: 15px; overflow-y: auto; }
.empty-state {
  font-family: 'Orbitron', sans-serif;
  color: rgba(255,255,255,0.2);
  letter-spacing: 2px;
}
.monitor-card {
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--border2);
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 15px;
}
.monitor-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  padding-bottom: 10px;
}
.target-name {
  font-family: 'Orbitron', sans-serif;
  color: var(--textwh);
  font-size: 1rem;
}
.status-indicator {
  font-family: 'Orbitron', sans-serif;
  font-size: 0.8rem;
  letter-spacing: 1px;
}
.status-indicator.running { color: var(--cyan); text-shadow: 0 0 8px rgba(0,229,255,0.5); }
.status-indicator.paused { color: var(--yellow); }
.status-indicator.success { color: var(--green); text-shadow: 0 0 8px rgba(0,255,157,0.5); }
.status-indicator.failed { color: var(--pink); }

/* Neon Progress Bar */
.neon-progress-bar {
  height: 8px;
  background: rgba(0,0,0,0.5);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.05);
}
.neon-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--cyan), var(--pink));
  box-shadow: 0 0 10px var(--pink);
  transition: width 0.3s ease;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.metric-box {
  background: rgba(255,255,255,0.02);
  padding: 10px;
  border-radius: 4px;
  border: 1px solid rgba(255,255,255,0.05);
}
.metric-label {
  font-size: 0.65rem;
  color: var(--text);
  margin-bottom: 4px;
}
.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  color: var(--textwh);
}

/* Cracked / Message */
.cred-label {
  font-size: 0.7rem;
  color: var(--cyan);
  font-family: 'Orbitron', sans-serif;
  letter-spacing: 1px;
}
.cred-val {
  font-family: 'JetBrains Mono', monospace;
  color: var(--green);
  font-size: 1rem;
}

/* Action Buttons */
.monitor-actions {
  display: flex;
  gap: 10px;
}
.btn-action-small {
  background: transparent;
  padding: 4px 12px;
  font-size: 0.7rem;
  font-family: 'Orbitron', sans-serif;
  border-radius: 3px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.btn-action-small:hover { background: rgba(255,255,255,0.1); }
.border-orange { border-color: rgba(255,165,0,0.3); }
.text-orange { color: orange; }
.border-green { border-color: rgba(0,255,157,0.3); }
.text-green { color: var(--green); }
.border-red { border-color: rgba(255,45,110,0.3); }
.text-red { color: var(--pink); }

</style>
