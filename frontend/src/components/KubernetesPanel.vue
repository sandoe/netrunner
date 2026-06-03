<template>
  <div class="k8s-panel">
    <div class="panel-header">
      <h3>Kubernetes Control Room</h3>
      <div class="header-status">
        <label class="switch-label">
          <span class="switch-text">SIMULATION</span>
          <div class="switch">
            <input type="checkbox" v-model="forceMock" @change="handleToggle" />
            <span class="slider"></span>
          </div>
        </label>
        <span class="status-indicator" :class="clusterHealth.toLowerCase()"></span>
        {{ clusterHealth }}
        <span v-if="isMock" class="mock-badge">SIMULATED</span>
      </div>
    </div>

    <div v-if="installing" class="loading-overlay">
      <div class="spinner"></div>
      <div class="glitch">INJECTING KUBERNETES (K3S) PAYLOAD...</div>
      <div class="wait-text">This may take up to 60 seconds. Please wait...</div>
      <pre v-if="installLogs" class="install-terminal">{{ installLogs }}</pre>
    </div>

    <div v-else-if="error" class="error-box">
      <div>{{ error }}</div>
      <button v-if="error.includes('not detected') && !forceMock" class="btn-deploy" @click="installK3s">
        [ DEPLOY K3S CLUSTER ]
      </button>
      <pre v-if="installLogs" class="install-terminal">{{ installLogs }}</pre>
    </div>

    <div v-else-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <div>Establishing Kube-API connection...</div>
    </div>

    <div v-else-if="clusterData" class="k8s-dashboard">
      <!-- Top Stats Row -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-value">{{ clusterData.nodes.length }}</div>
          <div class="stat-label">NODES</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ clusterData.pods.length }}</div>
          <div class="stat-label">PODS</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ clusterData.total_cpu }}</div>
          <div class="stat-label">CORES</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ clusterData.total_memory_gb }}</div>
          <div class="stat-label">GB RAM</div>
        </div>
      </div>

      <!-- Pod Matrix -->
      <div class="section-title">POD MATRIX <span style="font-size: 10px; color: #8b949e;">(CLICK TO KILL POD)</span></div>
      <div class="pod-matrix">
        <div 
          v-for="pod in sortedPods" 
          :key="pod.name"
          class="pod-cell"
          :class="pod.status.toLowerCase()"
          :title="`${pod.name}\nNamespace: ${pod.namespace}\nStatus: ${pod.status}\nRestarts: ${pod.restarts}`"
          @click="killPod(pod)"
        ></div>
      </div>
      
      <!-- Deployments and Nodes -->
      <div class="split-view">
        <div class="list-container">
          <div class="section-title">ACTIVE DEPLOYMENTS</div>
          <div class="list-header">
            <span>NAME</span>
            <span>REPLICAS / SCALE</span>
          </div>
          <div class="list-item" v-for="dep in clusterData.deployments" :key="dep.name">
            <span class="item-name" :title="dep.name">{{ dep.name }}</span>
            <span class="item-value" :class="{'degraded': dep.available < dep.desired}" style="display: flex; align-items: center; gap: 8px;">
              {{ dep.available }} / {{ dep.desired }}
              <div class="scale-controls">
                <button @click="scaleDeployment(dep, -1)" class="btn-icon-action" style="font-size: 10px; padding: 2px 4px;" :disabled="dep.desired <= 0">-</button>
                <button @click="scaleDeployment(dep, 1)" class="btn-icon-action" style="font-size: 10px; padding: 2px 4px;">+</button>
              </div>
            </span>
          </div>
        </div>
        
        <div class="list-container">
          <div class="section-title">CLUSTER NODES</div>
          <div class="list-header">
            <span>NODE</span>
            <span>STATUS</span>
          </div>
          <div class="list-item" v-for="node in clusterData.nodes" :key="node.name">
            <span class="item-name" :title="node.name">{{ node.name }}</span>
            <span class="item-value" :class="node.status.toLowerCase()">{{ node.status }}</span>
          </div>
        </div>
      </div>
      
      <!-- Vulnerable Targets -->
      <div class="section-title" style="margin-top: 20px;">VULNERABLE TARGETS</div>
      <div class="targets-container">
        <div class="target-card">
          <div class="target-header">OWASP Juice Shop</div>
          <div class="target-desc">Modern web application with security flaws intended for security training.</div>
          <button class="btn-deploy" @click="deployTarget('juice-shop')">[ DEPLOY TO CLUSTER ]</button>
        </div>
        <!-- Add more targets here later -->
      </div>
      
      <!-- Detailed Pod Table -->
      <div class="section-title" style="margin-top: 20px;">DETAILED POD REGISTRY</div>
      <div class="cyber-card">
        <table class="cyber-table">
          <thead>
            <tr>
              <th>NAMESPACE</th>
              <th>POD NAME</th>
              <th>STATUS</th>
              <th>RESTARTS</th>
              <th>NODE</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pod in sortedPods" :key="pod.name" class="container-row">
              <td class="mono font-gray font-small">{{ pod.namespace }}</td>
              <td class="font-white font-bold">{{ pod.name }}</td>
              <td>
                <span class="status-badge" :class="pod.status.toLowerCase()">
                  {{ pod.status }}
                </span>
              </td>
              <td class="mono font-cyan font-small">{{ pod.restarts }}</td>
              <td class="mono font-gray font-small">{{ pod.node }}</td>
              <td>
                <div class="actions-cell">
                  <button class="btn-icon-action btn-logs" title="View Logs" @click="viewLogs(pod)">📝</button>
                  <button class="btn-icon-action btn-delete-peer" title="Delete Pod" @click="killPod(pod)">✕</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Logs / Inspect Panel -->
      <div v-if="activeLogs" class="cyber-card logs-card" style="margin-top: 15px;">
        <div class="card-title-bar">
          <span>📝 LOGS: {{ activeTargetPod }}</span>
          <button class="btn-close-logs" @click="closeLogs" style="background: transparent; border: none; color: var(--pink); cursor: pointer; font-size: 10px;">✕ CLOSE</button>
        </div>
        <div class="logs-viewport" ref="logsViewport" style="max-height: 400px; overflow-y: auto; background: #000; padding: 10px;">
          <pre class="logs-pre" v-html="logsOutput" style="color: #00ff00; font-family: monospace; white-space: pre-wrap; font-size: 11px;"></pre>
        </div>
      </div>
    </div>
    
    <!-- Sudo Prompt Modal -->
    <div v-if="showSudoPrompt" class="modal-overlay" @click.self="cancelSudo">
      <div class="modal-content sudo-modal">
        <h2 class="modal-title">Authentication Required</h2>
        <p class="modal-text">Enter sudo password for this node (leave blank if NOPASSWD):</p>
        <input
          v-model="sudoInput"
          type="password"
          class="cyber-input"
          placeholder="Password..."
          @keyup.enter="submitSudo"
        />
        <div class="modal-actions">
          <button class="btn-cancel" @click="cancelSudo">CANCEL</button>
          <button class="btn-submit" @click="submitSudo">AUTHENTICATE</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ nodeId: string }>()

const loading = ref(true)
const installing = ref(false)
const installLogs = ref('')
const error = ref('')
let logsInterval: any = null
const clusterData = ref<any>(null)
const forceMock = ref(false)

const activeLogs = ref(false)
const activeTargetPod = ref('')
const logsOutput = ref('')
const logsViewport = ref<HTMLElement | null>(null)

const showSudoPrompt = ref(false)
const sudoInput = ref('')
const sudoResolve = ref<((pass: string | null) => void) | null>(null)

function promptSudo(): Promise<string | null> {
  sudoInput.value = ''
  showSudoPrompt.value = true
  setTimeout(() => {
    const el = document.querySelector('.modal-overlay .cyber-input') as HTMLInputElement
    if (el) el.focus()
  }, 50)
  return new Promise(resolve => {
    sudoResolve.value = resolve
  })
}

function submitSudo() {
  if (sudoResolve.value) sudoResolve.value(sudoInput.value)
  showSudoPrompt.value = false
  sudoResolve.value = null
}

function cancelSudo() {
  if (sudoResolve.value) sudoResolve.value(null)
  showSudoPrompt.value = false
  sudoResolve.value = null
}

const clusterHealth = computed(() => clusterData.value?.cluster_health || 'Unknown')
const isMock = computed(() => clusterData.value?.mock === true)

const sortedPods = computed(() => {
  if (!clusterData.value?.pods) return []
  // Sort pods by status to group them visually (errors first)
  return [...clusterData.value.pods].sort((a, b) => {
    const aVal = a.status === 'CrashLoopBackOff' ? 0 : (a.status === 'Pending' ? 1 : 2)
    const bVal = b.status === 'CrashLoopBackOff' ? 0 : (b.status === 'Pending' ? 1 : 2)
    return aVal - bVal
  })
})

async function fetchClusterState(isPoll = false) {
  if (installing.value) return
  if (!isPoll) loading.value = true
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/status?mock=${forceMock.value}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    })
    
    if (!res.ok) {
      let msg = res.statusText
      try {
        const errData = await res.json()
        if (errData.detail) msg = errData.detail
      } catch (e) {}
      throw new Error(msg)
    }
    
    clusterData.value = await res.json()
    error.value = ''
  } catch (err: any) {
    if (err.message && err.message.includes("not detected")) {
      clusterData.value = null
      error.value = "Kubernetes cluster not detected or kubectl failed."
    } else {
      console.error(err)
      if (!clusterData.value) {
        error.value = err.message || 'Failed to fetch cluster state'
      }
    }
  } finally {
    loading.value = false
  }
}

async function killPod(pod: any) {
  if (forceMock.value) return;
  if (!confirm(`Are you sure you want to kill pod ${pod.name}?`)) return;
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/pods/${pod.namespace}/${pod.name}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    });
    if (!res.ok) throw new Error('Failed to delete pod');
    fetchClusterState(true);
  } catch(err) {
    console.error(err);
    alert('Failed to kill pod');
  }
}

async function deployTarget(target: string) {
  if (forceMock.value) return;
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/deploy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('nr_token')}`
      },
      body: JSON.stringify({ target })
    });
    if (!res.ok) throw new Error('Failed to deploy target');
    fetchClusterState(true);
  } catch(err) {
    console.error(err);
    alert('Failed to deploy target');
  }
}

async function pollLogs() {
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/install/logs`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    })
    if (res.ok) {
      const data = await res.json()
      if (data.logs) {
        installLogs.value = data.logs
        setTimeout(() => {
          const terms = document.querySelectorAll('.install-terminal')
          terms.forEach(term => term.scrollTop = term.scrollHeight)
        }, 100)
      }
    }
  } catch (e) {}
}

async function installK3s() {
  const sudoPass = await promptSudo()
  if (sudoPass === null) return // user cancelled

  installing.value = true
  error.value = ''
  installLogs.value = ''
  logsInterval = setInterval(pollLogs, 1500)
  
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/install`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${localStorage.getItem('nr_token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ sudo_password: sudoPass })
    })
    
    if (!res.ok) {
      let msg = res.statusText
      try {
        const errData = await res.json()
        if (errData.detail) msg = errData.detail
      } catch (e) {}
      throw new Error(msg)
    }
    
    // Refresh cluster state once installed
    await fetchClusterState(false)
    installLogs.value = '' // clear logs on success so it doesn't show up later
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    installing.value = false
    if (logsInterval) {
      clearInterval(logsInterval)
      logsInterval = null
    }
  }
}

function handleToggle() {
  fetchClusterState(false)
}

onMounted(() => {
  fetchClusterState(false)
  // Refresh every 10 seconds
  const interval = setInterval(() => fetchClusterState(true), 10000)
  return () => clearInterval(interval)
})

async function scaleDeployment(dep: any, delta: number) {
  if (isMock.value) return
  const newReplicas = dep.desired + delta
  if (newReplicas < 0) return
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/deployments/default/${dep.name}/scale`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${localStorage.getItem('nr_token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ replicas: newReplicas })
    })
    if (!res.ok) throw new Error('Scale request failed')
    await fetchClusterState()
  } catch (err: any) {
    alert(`Fejl under skalering: ${err.message}`)
  }
}

async function viewLogs(pod: any) {
  if (isMock.value) return
  activeLogs.value = true
  activeTargetPod.value = pod.name
  logsOutput.value = 'Henter logs...'
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/pods/${pod.namespace}/${pod.name}/logs`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    })
    if (!res.ok) throw new Error('Failed to fetch logs')
    const data = await res.json()
    logsOutput.value = data.logs || '(Ingen logs fundet)'
  } catch (err: any) {
    logsOutput.value = `Fejl: ${err.message}`
  }
}

function closeLogs() {
  activeLogs.value = false
  activeTargetPod.value = ''
  logsOutput.value = ''
}
</script>

<style scoped>
.k8s-panel {
  padding: 16px;
  color: #c9d1d9;
  font-family: 'Courier New', Courier, monospace;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #30363d;
  padding-bottom: 12px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #58a6ff;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.switch-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 16px;
  cursor: pointer;
}

.switch-text {
  font-size: 10px;
  color: #8b949e;
  letter-spacing: 1px;
}

.switch {
  position: relative;
  width: 34px;
  height: 18px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #30363d;
  transition: .4s;
  border-radius: 18px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 12px;
  width: 12px;
  left: 3px;
  bottom: 3px;
  background-color: #8b949e;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #d29922;
}

input:checked + .slider:before {
  transform: translateX(16px);
  background-color: #fff;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #8b949e;
}

.status-indicator.healthy {
  background: #3fb950;
  box-shadow: 0 0 8px #3fb950;
}

.status-indicator.degraded {
  background: #ff2d6e;
  box-shadow: 0 0 8px #ff2d6e;
  animation: pulse 1s infinite alternate;
}

.mock-badge {
  background: rgba(210, 153, 34, 0.2);
  color: #d29922;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  margin-left: 8px;
  border: 1px solid #d29922;
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #58a6ff;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(88, 166, 255, 0.2);
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { to { opacity: 0.5; } }

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  flex: 1;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #e6edf3;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 10px;
  color: #8b949e;
  letter-spacing: 1px;
}

.section-title {
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 12px;
  border-bottom: 1px dotted #30363d;
  padding-bottom: 4px;
}

.pod-matrix {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  background: #0d1117;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #30363d;
  margin-bottom: 24px;
  max-height: 200px;
  overflow-y: auto;
}

.pod-cell {
  width: 14px;
  height: 14px;
  background: #30363d;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pod-cell:hover {
  transform: scale(1.3);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
  z-index: 10;
}

.pod-cell.running {
  background: #238636;
  box-shadow: 0 0 5px rgba(35, 134, 54, 0.5);
}

.pod-cell.pending {
  background: #d29922;
  animation: pulse 1.5s infinite;
}

.pod-cell.failed, .pod-cell.error, .pod-cell.crashloopbackoff {
  background: #f85149;
  box-shadow: 0 0 5px rgba(248, 81, 73, 0.5);
}

.pod-cell.terminating {
  background: #8b949e;
  animation: fade 1s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

@keyframes fade {
  0% { opacity: 1; }
  50% { opacity: 0.3; }
  100% { opacity: 1; }
}

/* List views */
.split-view {
  display: flex;
  gap: 20px;
}

.list-container {
  flex: 1;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 4px;
  padding: 12px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #8b949e;
  padding-bottom: 8px;
  border-bottom: 1px solid #30363d;
  margin-bottom: 8px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(48, 54, 61, 0.5);
}

.list-item:last-child {
  border-bottom: none;
}

.item-name {
  color: #c9d1d9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.item-value {
  color: #8b949e;
}

.item-value.degraded {
  color: #d29922;
}

.item-value.ready {
  color: #238636;
}

.item-value.notready {
  color: #f85149;
}

/* Targets */
.targets-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.target-card {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.target-header {
  color: #58a6ff;
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 8px;
}

.target-desc {
  color: #8b949e;
  font-size: 12px;
  margin-bottom: 16px;
  flex-grow: 1;
}

.btn-deploy {
  background: transparent;
  border: 1px solid #238636;
  color: #238636;
  padding: 6px 0;
  border-radius: 4px;
  cursor: pointer;
  font-family: monospace;
  font-size: 12px;
  transition: all 0.2s ease;
}

.btn-deploy:hover {
  background: rgba(35, 134, 54, 0.1);
  box-shadow: 0 0 8px rgba(35, 134, 54, 0.4);
}

.error-box {
  background: #330a0a;
  border: 1px solid #f85149;
  color: #f85149;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  font-weight: bold;
}

.btn-deploy {
  background: #238636;
  color: #fff;
  border: 1px solid rgba(240, 246, 252, 0.1);
  padding: 10px 20px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 0 10px rgba(46, 160, 67, 0.4);
}

.btn-deploy:hover {
  background: #2ea043;
  transform: translateY(-2px);
  box-shadow: 0 0 15px rgba(46, 160, 67, 0.6);
}

.glitch {
  color: #58a6ff;
  font-size: 16px;
  font-weight: bold;
  letter-spacing: 2px;
  animation: glitch-anim 1s infinite alternate;
}

.wait-text {
  font-size: 10px;
  color: #8b949e;
  margin-top: 12px;
  letter-spacing: 1px;
}

.install-terminal {
  width: 100%;
  max-width: 800px;
  height: 250px;
  overflow-y: auto;
  background: #0d1117;
  border: 1px solid #30363d;
  color: #c9d1d9;
  padding: 12px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 11px;
  text-align: left;
  margin-top: 20px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

@keyframes glitch-anim {
  0% { opacity: 0.8; transform: skewX(0deg); }
  20% { opacity: 1; transform: skewX(-2deg); }
  40% { opacity: 0.9; transform: skewX(1deg); }
  60% { opacity: 1; transform: skewX(-1deg); }
  80% { opacity: 0.8; transform: skewX(2deg); }
  100% { opacity: 1; transform: skewX(0deg); }
}
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content.sudo-modal {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 24px;
  width: 400px;
  max-width: 90%;
  box-shadow: 0 0 20px rgba(88, 166, 255, 0.2);
}

.modal-title {
  margin: 0 0 12px 0;
  color: #ff7b72;
  font-size: 18px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.modal-text {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: #8b949e;
}

.cyber-input {
  width: 100%;
  padding: 10px;
  background: #010409;
  border: 1px solid #30363d;
  color: #c9d1d9;
  border-radius: 4px;
  font-family: monospace;
  margin-bottom: 20px;
  box-sizing: border-box;
}

.cyber-input:focus {
  outline: none;
  border-color: #58a6ff;
  box-shadow: 0 0 5px rgba(88, 166, 255, 0.5);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-cancel {
  background: transparent;
  border: 1px solid #30363d;
  color: #8b949e;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #21262d;
  color: #c9d1d9;
}

.btn-submit {
  background: #238636;
  border: 1px solid rgba(240,246,252,0.1);
  color: #ffffff;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-submit:hover {
  background: #2ea043;
}
</style>
