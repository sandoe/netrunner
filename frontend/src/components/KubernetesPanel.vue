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
    </div>

    <div v-else-if="error" class="error-box">
      <div>{{ error }}</div>
      <button v-if="error.includes('not detected') && !forceMock" class="btn-deploy" @click="installK3s">
        [ DEPLOY K3S CLUSTER ]
      </button>
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
      <div class="section-title">POD MATRIX</div>
      <div class="pod-matrix">
        <div 
          v-for="pod in sortedPods" 
          :key="pod.name"
          class="pod-cell"
          :class="pod.status.toLowerCase()"
          :title="`${pod.name}\nNamespace: ${pod.namespace}\nStatus: ${pod.status}\nRestarts: ${pod.restarts}`"
        ></div>
      </div>
      
      <!-- Deployments and Nodes -->
      <div class="split-view">
        <div class="list-container">
          <div class="section-title">ACTIVE DEPLOYMENTS</div>
          <div class="list-header">
            <span>NAME</span>
            <span>REPLICAS</span>
          </div>
          <div class="list-item" v-for="dep in clusterData.deployments" :key="dep.name">
            <span class="item-name" :title="dep.name">{{ dep.name }}</span>
            <span class="item-value" :class="{'degraded': dep.available < dep.desired}">
              {{ dep.available }} / {{ dep.desired }}
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ nodeId: string }>()

const loading = ref(true)
const installing = ref(false)
const error = ref('')
const clusterData = ref<any>(null)
const forceMock = ref(false)

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

async function fetchClusterState(isBackground = true) {
  // Only show loading spinner on first load or explicit toggle
  if (!isBackground || (!clusterData.value && !error.value)) {
    loading.value = true
  }
  
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
    error.value = err.message || String(err)
    clusterData.value = null
  } finally {
    loading.value = false
  }
}

async function installK3s() {
  installing.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/kubernetes/${props.nodeId}/install`, {
      method: 'POST',
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
    
    // Refresh cluster state once installed
    await fetchClusterState(false)
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    installing.value = false
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
  transition: transform 0.1s;
}

.pod-cell:hover {
  transform: scale(1.5);
  z-index: 2;
  box-shadow: 0 0 10px rgba(255,255,255,0.5);
}

.pod-cell.running { background: #3fb950; }
.pod-cell.pending { background: #d29922; }
.pod-cell.crashloopbackoff { background: #f85149; animation: blink 1s infinite; }
.pod-cell.completed { background: #58a6ff; }
.pod-cell.error { background: #ff2d6e; animation: blink 0.5s infinite; }

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.split-view {
  display: flex;
  gap: 16px;
}

.list-container {
  flex: 1;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 12px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #8b949e;
  margin-bottom: 8px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #21262d;
  font-size: 12px;
}

.list-item:last-child {
  border-bottom: none;
}

.item-name {
  color: #e6edf3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.item-value {
  color: #3fb950;
  font-weight: bold;
}

.item-value.degraded, .item-value.notready {
  color: #f85149;
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

@keyframes glitch-anim {
  0% { opacity: 0.8; transform: skewX(0deg); }
  20% { opacity: 1; transform: skewX(-2deg); }
  40% { opacity: 0.9; transform: skewX(1deg); }
  60% { opacity: 1; transform: skewX(-1deg); }
  80% { opacity: 0.8; transform: skewX(2deg); }
  100% { opacity: 1; transform: skewX(0deg); }
}
</style>
