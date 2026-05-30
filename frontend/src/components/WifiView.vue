<template>
  <div class="wifi-container">
    <div class="wifi-sidebar">
      <h2>WIFI & CSI ANALYSIS</h2>
      
      <div class="node-status">
        <h3>ACTIVE NODES</h3>
        <div class="node-item" v-for="node in activeNodes" :key="node.id" :class="{'selected-node': selectedNodeId === node.id}" @click="selectedNodeId = node.id">
          <div class="node-dot" :style="{ backgroundColor: isNodeActive(node.id) ? '#00ff9d' : '#ff2d6e' }"></div>
          <div class="node-info">
            <div class="node-name">{{ node.ip }}</div>
            <div class="node-controls">
              <button @click="startNode(node.id)" class="ctrl-btn start-btn" title="Deploy / Start">▶</button>
              <button @click="stopNode(node.id)" class="ctrl-btn stop-btn" title="Kill Process">■</button>
              <button @click="deleteNode(node.id)" class="ctrl-btn delete-btn" title="Remove Config">✕</button>
            </div>
          </div>
        </div>
        <div v-if="activeNodes.length === 0" style="color:#555; font-size:11px; padding: 5px;">No beacons configured.</div>
      </div>
      
      <div class="stats-panel">
        <h3>RADIO TELEMETRY</h3>
        <div class="stat-row">
          <span>Status:</span>
          <span class="highlight">MONITOR MODE</span>
        </div>
        <div class="stat-row">
          <span>Band:</span>
          <span class="highlight">5 GHz (Ch 36)</span>
        </div>
        <div class="stat-row">
          <span>Bandwidth:</span>
          <span class="highlight">20 MHz</span>
        </div>
        <div class="stat-row">
          <span>Subcarriers:</span>
          <span class="highlight">64 (OFDM)</span>
        </div>
        <div class="stat-row">
          <span>Motion Detect:</span>
          <span :class="motionDetected ? 'highlight-alert' : 'highlight'">
            {{ motionDetected ? 'ALERT' : 'CLEAR' }}
          </span>
        </div>
        <div class="stat-row">
          <span>Keylogger:</span>
          <span :class="typingActive ? 'highlight-alert' : 'highlight'">
            {{ typingActive ? 'INTERCEPTING' : 'IDLE' }}
          </span>
        </div>
      </div>
    </div>
    
    <div class="wifi-main">
      <div class="mode-toggle">
        <button :class="{'active': activeMode === 'single'}" @click="activeMode = 'single'">[ SINGLE NODE DECODER ]</button>
        <button :class="{'active': activeMode === 'mesh'}" @click="activeMode = 'mesh'">[ MULTI-NODE MESH ]</button>
        <button :class="{'active': activeMode === '3d-map'}" @click="activeMode = '3d-map'">[ 3D SIGNAL MAPPING ]</button>
        <button :class="{'active': activeMode === 'observatory'}" @click="activeMode = 'observatory'">[ DENSEPOSE OBSERVATORY ]</button>
      </div>
      
      <!-- DYNAMIC NODE MANAGER -->
      <div class="node-manager">
        <div class="mode-switch">
          <button :class="{'active': isSimulation}" @click="setMode(true)">[ SIMULATION ]</button>
          <button :class="{'danger-active': !isSimulation}" @click="setMode(false)" class="danger-btn">[ REALTIME SENSORS ]</button>
        </div>
        
        <div class="divider"></div>

        <!-- RECORD CONTROL -->
        <div class="record-control">
          <button v-if="!isRecording" class="rec-btn" @click="startRecording">
             <span class="rec-dot"></span> RECORD
          </button>
          <button v-else class="rec-btn recording" @click="stopRecording">
             <span class="stop-square"></span> STOP {{ formatRecTime }}
          </button>
          <a v-if="lastDownloadLink" :href="lastDownloadLink" target="_blank" class="download-link">[ GET .JSONL ]</a>
        </div>
        
        <div class="divider"></div>
        
        <div class="node-input-group" style="text-align: center;">
          <button @click="showDeployModal = true" class="deploy-btn">[ + DEPLOY NEW NODE ]</button>
        </div>
        
        <div class="divider"></div>
        
        <button :class="{'active': showAdvancedStream}" class="node-btn" @click="showAdvancedStream = !showAdvancedStream">[ ADVANCED RAW ]</button>
        
        <div class="active-nodes-list">
          <span v-if="activeNodes.length === 0" class="no-nodes">No external nodes connected. Simulating 3 nodes.</span>
          <div v-for="(node, index) in activeNodes" :key="index" class="node-badge" :class="{'selected-badge': selectedNodeId === node.id}" :style="{ borderColor: isNodeActive(node.id) ? '#00ff9d' : '#ff2d6e' }" @click="selectedNodeId = node.id">
            <div class="node-badge-indicator" :style="{ background: isNodeActive(node.id) ? '#00ff9d' : '#ff2d6e' }"></div>
            <span class="node-ip">{{ node.ip }}</span>
            <button @click="removeNode(index)" class="node-remove">×</button>
          </div>
        </div>
      </div>

      <!-- SINGLE NODE MODE -->
      <div v-show="activeMode === 'single'" class="single-mode">
        <div class="chart-header">
          <div class="glitch-title">CSI SUBCARRIER AMPLITUDE MATRIX</div>
          <div class="live-badge"><span class="pulse"></span> LIVE STREAM</div>
        </div>
      <div class="chart-container">
        <canvas ref="chartCanvas"></canvas>
      </div>
      
      <div class="decoders-grid">
        <!-- Panel 1: WiKey -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">KEYSTROKE (WiKey)</div>
            <div v-if="typingActive" class="live-badge alert-badge"><span class="pulse-alert"></span> INTERCEPTING...</div>
          </div>
          <div class="decoder-terminal">
            <div class="terminal-text">{{ decodedText }}<span class="cursor" v-show="cursorVisible">_</span></div>
          </div>
        </div>
        
        <!-- Panel 2: Vital Signs -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">VITAL SIGNS (ECG)</div>
            <div class="live-badge"><span class="pulse-alert" style="background:#ff2d6e;"></span> {{ bpm }} BPM</div>
          </div>
          <div class="decoder-content" style="display:flex;align-items:center;justify-content:center;">
             <div class="heartbeat-line"></div>
          </div>
        </div>

        <!-- Panel 3: Radar -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">THROUGH-WALL RADAR</div>
          </div>
          <div class="decoder-content" style="position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;">
            <div class="radar-scope">
              <div class="radar-sweep"></div>
              <div class="radar-blip" :style="{ left: (radarX * 100) + '%', top: (radarY * 100) + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- Panel 4: Behavior -->
        <div class="decoder-panel">
          <div class="decoder-header">
            <div class="glitch-title-sm">BEHAVIOR & SPEECH</div>
          </div>
          <div class="decoder-terminal behavior-terminal">
            <div v-for="(log, idx) in behaviorLogs" :key="idx" class="terminal-text" :class="{'speech-log': log.includes('[SPEECH]'), 'gesture-log': log.includes('[GESTURE]')}">
              {{ log }}
            </div>
          </div>
        </div>
        </div>
      </div>

      <!-- MESH NODE MODE -->
      <div v-show="activeMode === 'mesh'" class="mesh-mode">
        <div class="chart-header">
          <div class="glitch-title">MULTI-NODE SENSOR ARRAY (3D SPATIAL TRACKING)</div>
          <div class="live-badge"><span class="pulse"></span> LIVE TRIANGULATION</div>
        </div>
        
        <div class="mesh-container">
          <!-- Mesh Map -->
          <div class="mesh-map-panel">
            <div class="mesh-canvas-container">
              <canvas ref="meshCanvas"></canvas>
            </div>
          </div>
          
          <!-- Mesh Side Telemetry -->
          <div class="mesh-telemetry-panel">
            <div class="link-status" v-for="(link, id) in meshLinks" :key="id">
              <div class="link-header">
                <span class="link-name">LINK {{ id }}</span>
                <span class="link-dist" :class="{'high-dist': link.disturbance > 0.5}">
                  {{ (link.disturbance * 100).toFixed(0) }}% DISTURBANCE
                </span>
              </div>
              <div class="link-bar-bg">
                <div class="link-bar-fill" :style="{ width: (link.disturbance * 100) + '%', backgroundColor: link.disturbance > 0.5 ? '#ff2d6e' : '#00ff9d' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3D SIGNAL MAPPING MODE -->
      <div v-show="activeMode === '3d-map'" class="map3d-mode">
        <div class="chart-header">
          <div class="glitch-title">3D SIGNAL STRENGTH VISUALIZATION (CSI SPATIAL MATRIX)</div>
          <div class="live-badge"><span class="pulse"></span> LIVE RENDER</div>
        </div>
        
        <div class="map3d-grid">
          <div class="map3d-panel">
            <div ref="map3dSurface" class="plotly-container"></div>
          </div>
          <div class="map3d-panel">
            <div ref="mapTopView" class="plotly-container"></div>
          </div>
          <div class="map3d-panel">
            <div ref="mapSideX" class="plotly-container"></div>
          </div>
          <div class="map3d-panel">
            <div ref="mapSideY" class="plotly-container"></div>
          </div>
        </div>
      </div>

      <!-- DENSEPOSE OBSERVATORY MODE -->
      <div v-show="activeMode === 'observatory' && !isRebuildingObservatory" class="observatory-mode">
        <div class="obs-container" ref="obsContainer">
          <canvas ref="obsCanvas" class="obs-canvas"></canvas>
          
          <!-- Top UI Overlay -->
          <div class="obs-top">
            <h2>π RuView</h2>
            <div class="obs-sub">WIFI DENSEPOSE SENSING OBSERVATORY</div>
          </div>
          
          <!-- UI Overlay Left -->
          <div class="obs-ui obs-ui-left">
            <div class="obs-panel">
              <div class="obs-panel-title">VITAL SIGNS</div>
              <div class="obs-stat">
                <span class="obs-icon" style="color:#ff2d6e;">❤️</span>
                <div class="obs-val">
                  <span class="obs-num">85</span><span class="obs-unit">BPM</span>
                </div>
                <div class="obs-label">HEART RATE</div>
              </div>
              <div class="obs-divider"></div>
              <div class="obs-stat">
                <span class="obs-icon" style="color:#00ff9d;">☀️</span>
                <div class="obs-val">
                  <span class="obs-num">18</span><span class="obs-unit">RPM</span>
                </div>
                <div class="obs-label">RESPIRATION</div>
              </div>
              <div class="obs-divider"></div>
              <div class="obs-stat">
                <span class="obs-icon" style="color:#ffb800;">⚖️</span>
                <div class="obs-val">
                  <span class="obs-num">81</span><span class="obs-unit">%</span>
                </div>
                <div class="obs-label">CONFIDENCE</div>
                <div class="obs-bar"><div class="obs-bar-fill" style="width:81%; background:#00ff9d;"></div></div>
              </div>
            </div>
          </div>
          
          <!-- UI Overlay Right -->
          <div class="obs-ui obs-ui-right">
            <div class="obs-panel">
              <div class="obs-panel-title">WIFI SIGNAL</div>
              <div class="obs-row"><span>RSSI</span><span style="color:#0088ff;">-36 dBm</span></div>
              <div class="obs-row"><span>Variance</span><span style="color:#0088ff;">2.43</span></div>
              <div class="obs-row"><span>Motion</span><span style="color:#0088ff;">0.394</span></div>
              <div class="obs-row"><span>Persons</span><span style="color:#0088ff;">2 🟢🟢⚫⚫⚫</span></div>
              <div class="obs-wave"></div>
              <div class="obs-panel-title" style="margin-top:20px;">PRESENCE</div>
              <div class="obs-btn-active">ACTIVE</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- ADVANCED RAW STREAM PANEL -->
      <div v-if="showAdvancedStream" class="advanced-stream-panel">
        <div class="advanced-header">
           <span>RAW CSI DATA STREAM [JSON]</span>
           <button @click="showAdvancedStream = false" class="close-btn">×</button>
        </div>
        <div class="advanced-content" ref="advancedContent">
           <div v-for="(log, idx) in rawLogs" :key="idx" class="log-line">
              {{ log }}
           </div>
        </div>
      </div>

      <!-- NODE CONFIGURATION MODAL -->
      <div v-if="showDeployModal" class="modal-overlay" @click.self="showDeployModal = false">
        <div class="modal-content glitch-box">
          <div class="modal-header">
            <h2>NODE CONFIGURATION PAYLOAD</h2>
            <button @click="showDeployModal = false" class="close-btn">×</button>
          </div>
          
          <div class="modal-body">
            <div class="form-group">
              <label>TARGET IP (SSH)</label>
              <input v-model="deployForm.ip" type="text" placeholder="e.g. 192.168.1.100" class="hack-input"/>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>USERNAME</label>
                <input v-model="deployForm.username" type="text" placeholder="pi" class="hack-input"/>
              </div>
              <div class="form-group">
                <label>PASSWORD</label>
                <input v-model="deployForm.password" type="password" placeholder="***" class="hack-input"/>
              </div>
            </div>
            
            <div class="form-group">
              <label>CSI EXTRACTION MODE</label>
              <select v-model="deployForm.csi_mode" class="hack-select">
                <option value="AUTO">AUTO (Nexmon -> Synthetic)</option>
                <option value="RAW_NEXMON">RAW_NEXMON (Force hardware)</option>
                <option value="SYNTHETIC">SYNTHETIC (Simulation)</option>
              </select>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>SAMPLE RATE (Hz)</label>
                <input v-model="deployForm.sample_rate" type="number" class="hack-input"/>
              </div>
              <div class="form-group">
                <label>UDP TARGET PORT</label>
                <input v-model="deployForm.udp_port" type="number" class="hack-input"/>
              </div>
            </div>
            
            <div class="form-group">
              <label>TARGET SERVER IP (This computer's IP, e.g. 192.168.1.X)</label>
              <input v-model="deployForm.target_server_ip" type="text" class="hack-input"/>
            </div>
          </div>
          
          <div class="modal-footer">
            <button @click="saveAndDeployNode" class="hack-btn primary">[ INJECT BEACON ]</button>
            <button @click="showDeployModal = false" class="hack-btn secondary">[ ABORT ]</button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import Chart from 'chart.js/auto'
import Plotly from 'plotly.js-dist-min'
import * as THREE from 'three'

interface NetworkNode {
  ip: string;
  color: number;
}

const activeMode = ref('single')

const selectedNodeId = ref<string>("")
const nodeLastSeen = ref<Record<string, number>>({})

const isNodeActive = (id: string) => {
  if (isSimulation.value) return true;
  return (Date.now() - (nodeLastSeen.value[id] || 0)) < 5000;
}

const newNodeIp = ref('')
const activeNodes = ref<NetworkNode[]>([])
const isSimulation = ref(true)

// Modal & Deploy State
const showDeployModal = ref(false)
const deployForm = ref({
  id: '',
  ip: '',
  username: '',
  password: '',
  csi_mode: 'AUTO',
  sample_rate: 30,
  udp_port: 8001,
  target_server_ip: window.location.hostname !== 'localhost' ? window.location.hostname : '127.0.0.1'
})

const fetchSavedNodes = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/wifi/beacons')
    const data = await res.json()
    if (data.beacons) {
      activeNodes.value = data.beacons.map((b: any) => ({
        ip: b.ip,
        color: availableColors[Math.floor(Math.random() * availableColors.length)],
        id: b.id
      }))
    }
  } catch(e) {
    console.error("Failed to fetch beacons", e)
  }
}

// Persist state
onMounted(() => {
  fetchSavedNodes()
  
  const savedMode = localStorage.getItem('netrunner_sim_mode')
  if (savedMode !== null) {
    isSimulation.value = savedMode === 'true'
  }
  
  // Sync with backend on load
  fetch('http://localhost:8000/api/wifi/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      simulation: isSimulation.value,
      nodes: activeNodes.value.map(n => n.ip)
    })
  }).catch(e => console.error("Initial sync failed", e))
})

watch(activeNodes, (newVal) => {
  localStorage.setItem('netrunner_nodes', JSON.stringify(newVal))
}, { deep: true })

watch(isSimulation, (newVal) => {
  localStorage.setItem('netrunner_sim_mode', String(newVal))
})

const showAdvancedStream = ref(false)
const rawLogs = ref<string[]>([])
const advancedContent = ref<HTMLElement | null>(null)

// Recorder state
const isRecording = ref(false)
const recordingSeconds = ref(0)
const lastDownloadLink = ref('')
let recInterval: any = null

const formatRecTime = computed(() => {
  const m = Math.floor(recordingSeconds.value / 60).toString().padStart(2, '0')
  const s = (recordingSeconds.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

const startRecording = async () => {
  try {
    await fetch('http://localhost:8000/api/wifi/record/start', { method: 'POST' })
    isRecording.value = true
    recordingSeconds.value = 0
    lastDownloadLink.value = ''
    recInterval = setInterval(() => { recordingSeconds.value++ }, 1000)
  } catch(e) {
    console.error("Start recording failed", e)
  }
}

const stopRecording = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/wifi/record/stop', { method: 'POST' })
    const data = await res.json()
    isRecording.value = false
    if (recInterval) clearInterval(recInterval)
    if (data.filename) {
      lastDownloadLink.value = `http://localhost:8000/api/wifi/record/download/${data.filename}`
    }
  } catch(e) {
    console.error("Stop recording failed", e)
  }
}

const availableColors = [0x0055ff, 0xff2d6e, 0x00ff9d, 0xffb800, 0x9d00ff, 0x00ffff]

const setMode = async (sim: boolean) => {
  isSimulation.value = sim
  await pushModeToBackend()
}

const pushModeToBackend = async () => {
  try {
    await fetch('http://localhost:8000/api/wifi/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulation: isSimulation.value,
        nodes: activeNodes.value.map(n => n.ip)
      })
    })
  } catch(e) {
    console.error("Failed to set mode", e)
  }
}

const getHexColorStr = (hex: number) => {
  return '#' + hex.toString(16).padStart(6, '0')
}

const saveAndDeployNode = async () => {
  if (!deployForm.value.ip) return
  
  // Generate ID if new
  const nodeId = deployForm.value.id || 'node_' + Date.now()
  deployForm.value.id = nodeId
  
  try {
    // 1. Save to DB
    await fetch('http://localhost:8000/api/wifi/beacons', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(deployForm.value)
    })
    
    // 2. Trigger Deploy regardless of mode
    const res = await fetch('http://localhost:8000/api/wifi/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: nodeId })
    })
    const deployData = await res.json()
    if (deployData.error) {
        alert("DEPLOYMENT FAILED: " + deployData.error)
        return
    }
    
    // Auto switch to realtime mode
    if (isSimulation.value) {
        setMode(false)
    }
    
    showDeployModal.value = false
    await fetchSavedNodes()
    pushModeToBackend()
    
    if (activeMode.value === 'observatory') {
      rebuildObservatory()
    }
    
    // reset form but keep target_server_ip
    const currentTargetIp = deployForm.value.target_server_ip
    deployForm.value = {
      id: '', ip: '', username: '', password: '', csi_mode: 'AUTO', sample_rate: 30, udp_port: 8001, target_server_ip: currentTargetIp
    }
  } catch (e: any) {
    console.error("Deploy failed", e)
    alert("DEPLOYMENT FAILED: " + e.message)
  }
}

const startNode = async (nodeId: string) => {
  try {
    const res = await fetch('http://localhost:8000/api/wifi/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: nodeId })
    })
    const data = await res.json()
    if (data.error) {
      alert("START FAILED: " + data.error)
    } else {
      alert("Beacon Started Successfully.")
      if (isSimulation.value) {
        setMode(false)
      }
    }
  } catch (e: any) {
    alert("START FAILED: " + e.message)
  }
}

const stopNode = async (nodeId: string) => {
  try {
    const res = await fetch(`http://localhost:8000/api/wifi/beacons/${nodeId}/stop`, {
      method: 'POST'
    })
    const data = await res.json()
    if (data.error) {
      alert("STOP FAILED: " + data.error)
    } else {
      alert("Beacon Stopped Successfully.")
    }
  } catch (e: any) {
    alert("STOP FAILED: " + e.message)
  }
}

const deleteNode = async (nodeId: string) => {
  if (!confirm("Are you sure you want to remove this node configuration?")) return
  try {
    await fetch(`http://localhost:8000/api/wifi/beacons/${nodeId}`, {
      method: 'DELETE'
    })
    await fetchSavedNodes()
  } catch(e) {
    console.error("Delete failed", e)
  }
}

const removeNode = async (index: number) => {
  const node = activeNodes.value[index]
  if ((node as any).id) {
    try {
      await fetch(`http://localhost:8000/api/wifi/beacons/${(node as any).id}`, {
        method: 'DELETE'
      })
    } catch(e) {}
  }
  activeNodes.value.splice(index, 1)
  pushModeToBackend()
  if (activeMode.value === 'observatory') {
    rebuildObservatory()
  }
}

const isRebuildingObservatory = ref(false)

const rebuildObservatory = () => {
  if (obsReqFrame) cancelAnimationFrame(obsReqFrame)
  isRebuildingObservatory.value = true
  setTimeout(() => {
    isRebuildingObservatory.value = false
    setTimeout(() => {
      initObservatory()
    }, 50)
  }, 50)
}
const chartCanvas = ref<HTMLCanvasElement | null>(null)
const meshCanvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null
let ws: WebSocket | null = null

const motionDetected = ref(false)
const typingActive = ref(false)
const decodedText = ref("")
const cursorVisible = ref(true)

const bpm = ref(72)
const radarX = ref(0.5)
const radarY = ref(0.5)
const behaviorLogs = ref<string[]>([])

// Mesh state
const meshNodes = ref<any>({})
const meshTarget = ref<any>({x: 50, y: 50})
const meshLinks = ref<any>({
  "AB": { disturbance: 0 },
  "BC": { disturbance: 0 },
  "CA": { disturbance: 0 }
})
let meshAnimFrame: number | null = null

// 3D map references
const map3dSurface = ref<HTMLElement | null>(null)
const mapTopView = ref<HTMLElement | null>(null)
const mapSideX = ref<HTMLElement | null>(null)
const mapSideY = ref<HTMLElement | null>(null)
let mapAnimFrame: number | null = null
let mapAnimTimer: number | null = null

// Observatory state
const obsContainer = ref<HTMLElement | null>(null)
const obsCanvas = ref<HTMLCanvasElement | null>(null)
let obsReqFrame: number | null = null

setInterval(() => {
  cursorVisible.value = !cursorVisible.value
}, 500)

onMounted(() => {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  // Initialize chart
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array.from({ length: 64 }, (_, i) => i - 32),
      datasets: [{
        label: 'Amplitude',
        data: Array(64).fill(0),
        borderColor: '#00ff9d',
        backgroundColor: 'rgba(0, 255, 157, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 0 // turn off animation for high FPS updates
      },
      scales: {
        y: {
          min: 0,
          max: 60,
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: '#aaa' }
        },
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#aaa' }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  })

  // Setup WebSocket
  const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host
  ws = new WebSocket(`ws://${wsHost}/ws/csi`)
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      let resolvedNodeId = data.node_id ? data.node_id.replace('beacon_', '') : '';
      if (!resolvedNodeId && data.node_ip) {
        const matchingNode = activeNodes.value.find(n => n.ip === data.node_ip);
        if (matchingNode) {
          resolvedNodeId = matchingNode.id;
        }
      }
      
      if (resolvedNodeId) {
         nodeLastSeen.value[resolvedNodeId] = Date.now()
         // Also set with the raw node_ip just in case
         if (data.node_ip) {
           nodeLastSeen.value[data.node_ip] = Date.now()
         }
      }
  
      
      if (data.type === 'mesh') {
        // Process mesh telemetry
        meshNodes.value = data.nodes
        meshTarget.value = data.target
        meshLinks.value = data.links
        
        if (showAdvancedStream.value) {
          rawLogs.value.push(`[MESH] ${JSON.stringify(data.links)}`)
          if (rawLogs.value.length > 20) rawLogs.value.shift()
          nextTick(() => {
            if (advancedContent.value) advancedContent.value.scrollTop = advancedContent.value.scrollHeight
          })
        }
        
      } else {
        // Single Node CSI Amplitude Matrix logic
        if (selectedNodeId.value && resolvedNodeId !== selectedNodeId.value) { return; }

        
        if (showAdvancedStream.value) {
          rawLogs.value.push(`[CSI] ${JSON.stringify({ts: data.timestamp, amps: data.amplitudes.slice(0, 5) + '...'})}`)
          if (rawLogs.value.length > 20) rawLogs.value.shift()
          nextTick(() => {
            if (advancedContent.value) advancedContent.value.scrollTop = advancedContent.value.scrollHeight
          })
        }

        if (chart && data.amplitudes) {
          chart.data.datasets[0].data = data.amplitudes
          chart.update()
        }
      }

      motionDetected.value = data.motion_detected || false
      typingActive.value = data.typing_active !== undefined ? data.typing_active : (data.keystroke ? true : false)
      
      const parsedBpm = data.bpm || data.heart_rate;
      if (parsedBpm) bpm.value = Math.round(parsedBpm);
      
      if (data.radar) {
        radarX.value = data.radar.x
        radarY.value = data.radar.y
      } else if (data.radar_x !== undefined && data.radar_y !== undefined) {
        radarX.value = data.radar_x
        radarY.value = data.radar_y
      }
      if (data.behavior) {
        behaviorLogs.value.push(`[${new Date().toISOString().split('T')[1].slice(0,8)}] ${data.behavior}`)
        if (behaviorLogs.value.length > 8) behaviorLogs.value.shift()
      }

      if (data.keystroke) {
        decodedText.value += data.keystroke
        if (decodedText.value.length > 300) {
          decodedText.value = decodedText.value.substring(decodedText.value.length - 300)
        }
      }
      
      if (chart) {
        if (data.amplitudes) {
           chart.data.datasets[0].data = data.amplitudes
        }
        if (data.motion_detected) {
          chart.data.datasets[0].borderColor = '#ff2d6e'
          chart.data.datasets[0].backgroundColor = 'rgba(255, 45, 110, 0.2)'
        } else if (data.typing_active) {
          chart.data.datasets[0].borderColor = '#ffc000'
          chart.data.datasets[0].backgroundColor = 'rgba(255, 192, 0, 0.2)'
        } else {
          chart.data.datasets[0].borderColor = '#00ff9d'
          chart.data.datasets[0].backgroundColor = 'rgba(0, 255, 157, 0.1)'
        }
        chart.update()
      }
    } catch (e) {}
  }
  
  // Render loop for Mesh Canvas
  const renderMesh = () => {
    if (activeMode.value === 'mesh' && meshCanvas.value) {
      const canvas = meshCanvas.value
      const ctx = canvas.getContext('2d')
      if (ctx) {
        // Adjust canvas size to match container
        const parent = canvas.parentElement
        if (parent && (canvas.width !== parent.clientWidth || canvas.height !== parent.clientHeight)) {
          canvas.width = parent.clientWidth
          canvas.height = parent.clientHeight
        }
        
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        
        // Draw grid
        ctx.strokeStyle = 'rgba(0, 255, 157, 0.05)'
        ctx.lineWidth = 1
        for(let i=0; i<canvas.width; i+=40) {
          ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
        }
        for(let i=0; i<canvas.height; i+=40) {
          ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke();
        }

        const nodes = meshNodes.value
        const w = canvas.width
        const h = canvas.height

        const getCoord = (p: {x:number, y:number}) => ({ x: (p.x/100)*w, y: (p.y/100)*h })
        
        if (nodes.A && nodes.B && nodes.C) {
          const a = getCoord(nodes.A)
          const b = getCoord(nodes.B)
          const c = getCoord(nodes.C)
          
          // Draw Links
          const drawLink = (p1: any, p2: any, dist: number) => {
            ctx.beginPath()
            ctx.moveTo(p1.x, p1.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.lineWidth = 2 + (dist * 5)
            const r = dist > 0.5 ? 255 : 0
            const g = dist > 0.5 ? 45 : 255
            const b_c = dist > 0.5 ? 110 : 157
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b_c}, ${0.3 + (dist * 0.7)})`
            ctx.stroke()
            
            // Draw disturbance waves
            if (dist > 0.2) {
              const midX = (p1.x + p2.x) / 2
              const midY = (p1.y + p2.y) / 2
              ctx.beginPath()
              ctx.arc(midX, midY, 10 + (Math.random() * 20 * dist), 0, Math.PI * 2)
              ctx.strokeStyle = `rgba(${r}, ${g}, ${b_c}, ${0.5})`
              ctx.lineWidth = 1
              ctx.stroke()
            }
          }
          
          drawLink(a, b, meshLinks.value.AB?.disturbance || 0)
          drawLink(b, c, meshLinks.value.BC?.disturbance || 0)
          drawLink(c, a, meshLinks.value.CA?.disturbance || 0)
          
          // Draw Nodes
          const drawNode = (p: any, label: string) => {
            ctx.beginPath()
            ctx.arc(p.x, p.y, 8, 0, Math.PI * 2)
            ctx.fillStyle = '#00ff9d'
            ctx.fill()
            ctx.shadowBlur = 10
            ctx.shadowColor = '#00ff9d'
            ctx.fillStyle = '#fff'
            ctx.font = '12px JetBrains Mono'
            ctx.fillText(`RPI-${label}`, p.x + 15, p.y + 4)
            ctx.shadowBlur = 0
          }
          drawNode(a, "A")
          drawNode(b, "B")
          drawNode(c, "C")
        }

        // Draw Target
        const t = getCoord(meshTarget.value)
        ctx.beginPath()
        ctx.arc(t.x, t.y, 6, 0, Math.PI * 2)
        ctx.fillStyle = '#ff2d6e'
        ctx.fill()
        ctx.shadowBlur = 15
        ctx.shadowColor = '#ff2d6e'
        ctx.stroke()
        ctx.shadowBlur = 0
        
        // Target pulse
        ctx.beginPath()
        ctx.arc(t.x, t.y, 10 + (Math.random()*5), 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(255, 45, 110, 0.5)'
        ctx.lineWidth = 2
        ctx.stroke()
      }
    }
    meshAnimFrame = requestAnimationFrame(renderMesh)
  }
  meshAnimFrame = requestAnimationFrame(renderMesh)
})

// Generate simulated CSI 2D array
const generateZ = (t: number) => {
  const z: number[][] = []
  for (let y = 0; y < 50; y++) {
    const row: number[] = []
    for (let x = 0; x < 50; x++) {
      // Base noise
      let val = -100 + Math.random() * 5
      // Target 1
      const distTarget1 = Math.sqrt(Math.pow(x - 25 + Math.cos(t)*10, 2) + Math.pow(y - 25 + Math.sin(t)*10, 2))
      if (distTarget1 < 10) val += 40 * (1 - distTarget1/10)
      
      // Target 2
      const distTarget2 = Math.sqrt(Math.pow(x - 10 + Math.sin(t*0.5)*5, 2) + Math.pow(y - 10 + Math.cos(t*0.5)*5, 2))
      if (distTarget2 < 6) val += 20 * (1 - distTarget2/6)

      // Walls / Interference shadow
      if (x > 30 && x < 40 && y > 10 && y < 20) val = -140
      if (x > 15 && x < 20 && y > 35 && y < 45) val = -135
      
      row.push(val)
    }
    z.push(row)
  }
  return z
}

const render3DMap = () => {
  if (activeMode.value !== '3d-map') return
  
  let t = 0
  const update = () => {
    if (activeMode.value !== '3d-map') return
    t += 0.2
    const zData = generateZ(t)
    
    const paperBg = 'rgba(0,0,0,0)'
    const plotBg = 'rgba(0,0,0,0)'
    const fontColor = '#00ff9d'
    
    // update Surface
    if (map3dSurface.value) {
      Plotly.react(map3dSurface.value, [{
        z: zData,
        type: 'surface',
        colorscale: 'Jet',
        cmin: -150,
        cmax: -20,
        showscale: true,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: '3D Signal Strength (45° view)', font: { color: fontColor } },
        margin: {l:0, r:0, b:0, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        scene: {
          zaxis: { range: [-150, 0], title: { text: 'RSSI (dBm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          xaxis: { title: { text: 'X (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          yaxis: { title: { text: 'Y (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
        }
      })
    }
    
    const getFloorPlanShapes = () => {
      const shapes: any[] = [];
      const lines = [
        // Outer boundaries
        [2, 2, 48, 2], [48, 2, 48, 48], [48, 48, 2, 48], [2, 48, 2, 2],
        // Rooms
        [15, 48, 15, 30], [15, 30, 2, 30], // Top left room
        [15, 48, 30, 48], [30, 48, 30, 35], [30, 35, 15, 35], // Top middle room
        [30, 48, 48, 48], [48, 35, 30, 35], // Top right room
        [15, 30, 25, 30], [25, 30, 25, 15], [25, 15, 48, 15], // Middle sections
        [35, 30, 35, 15], [2, 15, 15, 15], [15, 15, 15, 2]
      ];
      
      for (const [x0, y0, x1, y1] of lines) {
        shapes.push({
          type: 'line',
          x0: x0, y0: y0, x1: x1, y1: y1,
          line: { color: 'rgba(0, 255, 157, 0.6)', width: 2 }
        });
      }
      return shapes;
    }

    // update Heatmap
    if (mapTopView.value) {
      Plotly.react(mapTopView.value, [{
        z: zData,
        type: 'heatmap',
        colorscale: 'Jet',
        zmin: -150,
        zmax: -20,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: 'Top View (Floor Plan Overlay)', font: { color: fontColor } },
        margin: {l:40, r:10, b:40, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        xaxis: { title: { text: 'X (m)', font: {color: fontColor} }, tickfont: {color: fontColor} },
        yaxis: { title: { text: 'Y (m)', font: {color: fontColor} }, tickfont: {color: fontColor} },
        shapes: getFloorPlanShapes()
      })
    }
    
    // X-Z Plane
    if (mapSideX.value) {
      Plotly.react(mapSideX.value, [{
        z: zData,
        type: 'surface',
        colorscale: 'Jet',
        cmin: -150, cmax: -20, showscale: true,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: 'Side View (X-Z plane)', font: { color: fontColor } },
        margin: {l:0, r:0, b:0, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        scene: {
          camera: { eye: {x: 0, y: -2, z: 0} }, // look from Y
          zaxis: { range: [-150, 0], title: { text: 'RSSI (dBm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          xaxis: { title: { text: 'X (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          yaxis: { title: { text: 'Y (cm)', font: {color: fontColor} }, tickfont: {color: fontColor}, showticklabels: false }
        }
      })
    }

    // Y-Z Plane
    if (mapSideY.value) {
      Plotly.react(mapSideY.value, [{
        z: zData,
        type: 'surface',
        colorscale: 'Jet',
        cmin: -150, cmax: -20, showscale: true,
        colorbar: { tickfont: { color: fontColor } }
      }], {
        title: { text: 'Side View (Y-Z plane)', font: { color: fontColor } },
        margin: {l:0, r:0, b:0, t:30},
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        scene: {
          camera: { eye: {x: -2, y: 0, z: 0} }, // look from X
          zaxis: { range: [-150, 0], title: { text: 'RSSI (dBm)', font: {color: fontColor} }, tickfont: {color: fontColor} },
          xaxis: { title: { text: 'X (cm)', font: {color: fontColor} }, tickfont: {color: fontColor}, showticklabels: false },
          yaxis: { title: { text: 'Y (cm)', font: {color: fontColor} }, tickfont: {color: fontColor} }
        }
      })
    }

    mapAnimTimer = window.setTimeout(() => {
      mapAnimFrame = requestAnimationFrame(update)
    }, 500) // 2 FPS to not overload browser with 4 plotlys
  }
  update()
}

watch(activeMode, async (newVal) => {
    if (newVal === 'mesh') {
      await nextTick()
      startMeshAnimation()
    } else {
      if (meshAnimFrame) cancelAnimationFrame(meshAnimFrame)
    }
    
    if (newVal === '3d-map') {
      await nextTick()
      render3DMap()
    } else {
      if (mapAnimFrame) cancelAnimationFrame(mapAnimFrame)
      if (mapAnimTimer) clearTimeout(mapAnimTimer)
    }
    
    if (newVal === 'observatory') {
      await nextTick()
      initObservatory()
    } else {
      if (obsReqFrame) cancelAnimationFrame(obsReqFrame)
    }
  })

const initObservatory = () => {
  if (!obsCanvas.value || !obsContainer.value) return;
  const canvas = obsCanvas.value;
  const container = obsContainer.value;
  
  const width = container.clientWidth;
  const height = container.clientHeight;
  
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x050505);
  scene.fog = new THREE.Fog(0x050505, 10, 50);
  
  const camera = new THREE.PerspectiveCamera(45, width/height, 0.1, 100);
  camera.position.set(0, 10, 25);
  camera.lookAt(0, 0, 0);
  
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  
  // Floor Grid Points
  const pointsGeo = new THREE.BufferGeometry();
  const pointsPos = [];
  for(let x=-20; x<=20; x+=1.5) {
    for(let z=-20; z<=20; z+=1.5) {
      pointsPos.push(x, 0.01, z);
    }
  }
  pointsGeo.setAttribute('position', new THREE.Float32BufferAttribute(pointsPos, 3));
  const pointsMat = new THREE.PointsMaterial({ color: 0x00ff9d, size: 0.15, transparent: true, opacity: 0.4 });
  const gridPoints = new THREE.Points(pointsGeo, pointsMat);
  scene.add(gridPoints);
  
  // Floor transparent plane
  const floorGeo = new THREE.PlaneGeometry(50, 50);
  const floorMat = new THREE.MeshBasicMaterial({ color: 0x00ff9d, transparent: true, opacity: 0.02 });
  const floorPlane = new THREE.Mesh(floorGeo, floorMat);
  floorPlane.rotation.x = -Math.PI / 2;
  scene.add(floorPlane);
  
  // 3 Nodes (Raspberry Pi's) with Concentric spheres
  let nodesToRender = [];
  if (activeNodes.value.length === 0) {
    // Fallback to simulated 3 nodes if none connected
    nodesToRender = [
      { position: new THREE.Vector3(-15, 2, -10), color: 0x0055ff, spheres: [] as THREE.Mesh[] },
      { position: new THREE.Vector3(15, 2, -5), color: 0xff2d6e, spheres: [] as THREE.Mesh[] },
      { position: new THREE.Vector3(0, 2, 15), color: 0x00ff9d, spheres: [] as THREE.Mesh[] },
    ];
  } else {
    // Distribute nodes dynamically in a circle
    const radius = 15;
    activeNodes.value.forEach((an, idx) => {
      const angle = (idx / activeNodes.value.length) * Math.PI * 2;
      nodesToRender.push({
        position: new THREE.Vector3(Math.cos(angle)*radius, 2, Math.sin(angle)*radius),
        color: an.color,
        spheres: [] as THREE.Mesh[]
      });
    });
  }
  
  nodesToRender.forEach((node, index) => {
    // Visual representation of the RPi Node
    const boxGeo = new THREE.BoxGeometry(0.8, 0.8, 0.8);
    const boxMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true });
    const box = new THREE.Mesh(boxGeo, boxMat);
    box.position.copy(node.position);
    scene.add(box);
    
    // Creating spheres for the waves
    for(let i=0; i<3; i++) {
      const sGeo = new THREE.SphereGeometry(1, 32, 16);
      const sMat = new THREE.MeshBasicMaterial({ color: node.color, wireframe: true, transparent: true, opacity: 0.1 });
      const sphere = new THREE.Mesh(sGeo, sMat);
      sphere.position.copy(node.position);
      // stagger the initial scale so they look asynchronous between nodes
      const startScale = (i * 10 + 1) + (index * 3);
      sphere.scale.set(startScale, startScale, startScale);
      scene.add(sphere);
      node.spheres.push(sphere);
    }
  });
  
  // DensePose targets
  const createSkeleton = () => {
    const group = new THREE.Group();
    // Glowing capsule
    const cGeo = new THREE.CapsuleGeometry(0.7, 2.0, 4, 16);
    const cMat = new THREE.MeshBasicMaterial({ color: 0x00ff9d, transparent: true, opacity: 0.3 });
    const capsule = new THREE.Mesh(cGeo, cMat);
    capsule.position.y = 1.7;
    group.add(capsule);
    
    // Add skeleton lines inside
    const lineMat = new THREE.LineBasicMaterial({ color: 0xff0000 });
    const points = [];
    points.push(new THREE.Vector3(0,3,0)); // head
    points.push(new THREE.Vector3(0,2,0)); // neck
    points.push(new THREE.Vector3(-0.8,2,0)); // left shoulder
    points.push(new THREE.Vector3(-0.8,0.5,0)); // left hand
    points.push(new THREE.Vector3(0,2,0)); // neck
    points.push(new THREE.Vector3(0.8,2,0)); // right shoulder
    points.push(new THREE.Vector3(0.8,0.5,0)); // right hand
    points.push(new THREE.Vector3(0,2,0)); // neck
    points.push(new THREE.Vector3(0,0.5,0)); // pelvis
    points.push(new THREE.Vector3(-0.4,-1.5,0)); // left foot
    points.push(new THREE.Vector3(0,0.5,0)); // pelvis
    points.push(new THREE.Vector3(0.4,-1.5,0)); // right foot
    const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
    const skeleton = new THREE.Line(lineGeo, lineMat);
    skeleton.position.y = 1.7;
    group.add(skeleton);
    
    // Red joint dots
    const jointGeo = new THREE.SphereGeometry(0.1, 8, 8);
    const jointMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
    points.forEach(p => {
      const j = new THREE.Mesh(jointGeo, jointMat);
      j.position.copy(p);
      j.position.y += 1.7;
      group.add(j);
    });
    
    return group;
  }
  
  const target1 = createSkeleton();
  target1.position.set(-3, 0, 0);
  scene.add(target1);
  
  const target2 = createSkeleton();
  target2.position.set(4, 0, 2);
  scene.add(target2);

  let time = 0;
  
  const renderLoop = () => {
    if (activeMode.value !== 'observatory') return;
    
    time += 0.01;
    
    // Animate spheres for all nodes
    nodesToRender.forEach(node => {
      node.spheres.forEach((s) => {
        let scale = s.scale.x + 0.05;
        if (scale > 35) scale = 0.1;
        s.scale.set(scale, scale, scale);
        // Fade out as it expands
        s.material.opacity = Math.max(0, 0.15 - (scale / 233));
      });
    });
    
    // Animate targets
    target1.position.x = -3 + Math.sin(time) * 3;
    target1.position.z = Math.cos(time * 0.5) * 2;
    
    target2.position.x = 4 + Math.cos(time * 0.8) * 4;
    target2.position.z = 2 + Math.sin(time * 1.2) * 3;
    
    // Slowly rotate camera
    camera.position.x = Math.sin(time * 0.1) * 25;
    camera.position.z = Math.cos(time * 0.1) * 25;
    camera.lookAt(0, 2, 0);
    
    renderer.render(scene, camera);
    obsReqFrame = requestAnimationFrame(renderLoop);
  }
  
  renderLoop();
}

onUnmounted(() => {
  if (ws) ws.close()
  if (chart) chart.destroy()
  if (meshAnimFrame) cancelAnimationFrame(meshAnimFrame)
  if (mapAnimFrame) cancelAnimationFrame(mapAnimFrame)
  if (mapAnimTimer) clearTimeout(mapAnimTimer)
  if (obsReqFrame) cancelAnimationFrame(obsReqFrame)
})
</script>

<style scoped>
.wifi-container {
  display: flex;
  width: 100%;
  height: 100%;
  background: #020408;
  color: #fff;
  font-family: 'JetBrains Mono', monospace;
}

.wifi-sidebar {
  width: 300px;
  background: rgba(10, 20, 40, 0.6);
  border-right: 1px solid rgba(0, 255, 157, 0.3);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.wifi-sidebar h2 {
  color: #00ff9d;
  font-size: 1.2rem;
  letter-spacing: 2px;
  margin: 0;
  text-shadow: 0 0 10px rgba(0, 255, 157, 0.5);
}

.wifi-sidebar h3 {
  color: #888;
  font-size: 0.9rem;
  margin-top: 0;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 5px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
  background: rgba(0, 255, 157, 0.05);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 4px;
}

.node-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #444;
}

.node-dot.active {
  background: #00ff9d;
  box-shadow: 0 0 8px #00ff9d;
}

.node-name {
  font-weight: bold;
}

.node-controls {
  display: flex;
  gap: 5px;
  margin-top: 5px;
}

.ctrl-btn {
  background: transparent;
  border: 1px solid #555;
  color: #888;
  padding: 2px 6px;
  font-size: 10px;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.2s;
}

.ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-color: #888;
}

.start-btn:hover {
  color: #00ff9d;
  border-color: #00ff9d;
  background: rgba(0, 255, 157, 0.1);
}

.stop-btn:hover {
  color: #ffb800;
  border-color: #ffb800;
  background: rgba(255, 184, 0, 0.1);
}

.delete-btn:hover {
  color: #ff2d6e;
  border-color: #ff2d6e;
  background: rgba(255, 45, 110, 0.1);
}

.node-interface {
  font-size: 0.8rem;
  color: #aaa;
}

.stats-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.highlight {
  color: #00ff9d;
}

.highlight-alert {
  color: #ff2d6e;
  font-weight: bold;
  animation: flash 1s infinite alternate;
}

@keyframes flash {
  from { text-shadow: 0 0 5px #ff2d6e; }
  to { text-shadow: 0 0 20px #ff2d6e, 0 0 30px #ff2d6e; }
}

.wifi-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 30px;
  gap: 20px;
  position: relative;
}

.mode-toggle {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.mode-toggle button {
  background: rgba(0, 255, 157, 0.05);
  border: 1px solid rgba(0, 255, 157, 0.3);
  color: #aaa;
  padding: 8px 16px;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.mode-toggle button:hover {
  background: rgba(0, 255, 157, 0.1);
  color: #00ff9d;
}

.mode-toggle button.active {
  background: rgba(0, 255, 157, 0.2);
  border-color: #00ff9d;
  color: #fff;
  text-shadow: 0 0 5px #00ff9d;
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.2);
}

.single-mode, .mesh-mode, .map3d-mode {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.glitch-title {
  color: #00ff9d;
  font-size: 1.5rem;
  letter-spacing: 2px;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #00ff9d;
  font-size: 0.9rem;
  border: 1px solid #00ff9d;
  padding: 4px 10px;
  border-radius: 4px;
  background: rgba(0, 255, 157, 0.1);
}

.pulse {
  width: 8px;
  height: 8px;
  background: #00ff9d;
  border-radius: 50%;
  animation: heartbeat 1s infinite;
}

@keyframes heartbeat {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.chart-container {
  flex: 2;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  padding: 20px;
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.5);
  min-height: 200px;
}

.decoders-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  flex: 3;
}

.decoder-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  padding: 20px;
}

.decoder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.glitch-title-sm {
  color: #00ff9d;
  font-size: 1.1rem;
  letter-spacing: 1px;
}

.alert-badge {
  color: #ffc000;
  border-color: #ffc000;
  background: rgba(255, 192, 0, 0.1);
}

.pulse-alert {
  width: 8px;
  height: 8px;
  background: #ffc000;
  border-radius: 50%;
  animation: heartbeat 0.5s infinite;
}

.decoder-terminal {
  flex: 1;
  background: #000;
  border: 1px solid #333;
  padding: 15px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  overflow-y: auto;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
  white-space: pre-wrap;
  word-wrap: break-word;
  display: flex;
  flex-direction: column;
}

.behavior-terminal {
  justify-content: flex-end;
}

.decoder-content {
  flex: 1;
  background: #000;
  border: 1px solid #333;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
}

.terminal-text {
  color: #00ff9d;
  text-shadow: 0 0 5px #00ff9d;
}

.speech-log { color: #00d2ff; text-shadow: 0 0 5px #00d2ff; }
.gesture-log { color: #ffc000; text-shadow: 0 0 5px #ffc000; }

.cursor {
  color: #00ff9d;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* ECG Line */
.heartbeat-line {
  width: 100%;
  height: 2px;
  background: #ff2d6e;
  box-shadow: 0 0 10px #ff2d6e;
  position: relative;
}
.heartbeat-line::after {
  content: '';
  position: absolute;
  top: -20px;
  left: 50%;
  width: 20px;
  height: 40px;
  border-left: 2px solid #ff2d6e;
  border-right: 2px solid #ff2d6e;
  transform: skewX(-30deg);
  box-shadow: 0 0 10px #ff2d6e;
  animation: beat 1s infinite;
}
@keyframes beat {
  0%, 100% { transform: skewX(-30deg) scaleY(1); }
  50% { transform: skewX(-30deg) scaleY(1.5); }
}

/* Radar Scope */
.radar-scope {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  border: 2px solid #00ff9d;
  position: relative;
  background: radial-gradient(circle, rgba(0,255,157,0.1) 0%, rgba(0,0,0,1) 70%);
  box-shadow: 0 0 20px rgba(0,255,157,0.2);
}
.radar-scope::before {
  content: '';
  position: absolute;
  top: 50%; left: 0; right: 0; height: 1px;
  background: rgba(0,255,157,0.3);
}
.radar-scope::after {
  content: '';
  position: absolute;
  left: 50%; top: 0; bottom: 0; width: 1px;
  background: rgba(0,255,157,0.3);
}
.radar-sweep {
  position: absolute;
  top: 0; left: 50%;
  width: 50%; height: 50%;
  background: linear-gradient(90deg, rgba(0,255,157,0) 0%, rgba(0,255,157,0.8) 100%);
  transform-origin: bottom left;
  animation: sweep 2s linear infinite;
}
@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.radar-blip {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #ff2d6e;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 10px #ff2d6e;
  animation: blipfade 2s infinite;
}
@keyframes blipfade {
  0% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(2); }
}

/* Mesh Mode Styles */
.mesh-container {
  display: flex;
  flex: 1;
  gap: 20px;
  height: 100%;
}

.mesh-map-panel {
  flex: 3;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.5);
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.mesh-canvas-container {
  flex: 1;
  position: relative;
  background: #000;
  border: 1px solid #333;
}

.mesh-telemetry-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  padding: 20px;
}

.link-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(0, 0, 0, 0.5);
  padding: 15px;
  border: 1px solid #333;
  border-radius: 4px;
}

.link-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.link-name {
  color: #fff;
  font-weight: bold;
}

.link-dist {
  color: #00ff9d;
}

.link-dist.high-dist {
  color: #ff2d6e;
  animation: flash 1s infinite alternate;
}

.link-bar-bg {
  height: 8px;
  background: #222;
  border-radius: 4px;
  overflow: hidden;
}

.link-bar-fill {
  height: 100%;
  transition: width 0.1s linear, background-color 0.2s;
}

/* 3D Map Mode Styles */
.map3d-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  flex: 1;
  height: 100%;
}

.map3d-panel {
  background: rgba(10, 20, 40, 0.4);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.5);
  display: flex;
  padding: 10px;
}

.plotly-container {
  width: 100%;
  height: 100%;
  border-radius: 4px;
}

/* Observatory Mode Styles */
.observatory-mode {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 8px;
}

.obs-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #050505;
}

.obs-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.obs-top {
  position: absolute;
  top: 20px;
  left: 20px;
  pointer-events: none;
  z-index: 10;
}

.obs-top h2 {
  color: #00ff9d;
  font-size: 24px;
  margin: 0;
  font-weight: bold;
}

.obs-sub {
  color: #888;
  font-size: 10px;
  letter-spacing: 2px;
}

.obs-ui {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 10;
}

.obs-ui-left {
  left: 20px;
}

.obs-ui-right {
  right: 20px;
}

.obs-panel {
  background: rgba(10, 15, 25, 0.7);
  border: 1px solid rgba(0, 255, 157, 0.2);
  border-radius: 12px;
  padding: 20px;
  width: 220px;
  backdrop-filter: blur(5px);
  box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

.obs-panel-title {
  color: #888;
  font-size: 10px;
  letter-spacing: 2px;
  margin-bottom: 20px;
}

.obs-stat {
  margin-bottom: 10px;
  position: relative;
  padding-left: 30px;
}

.obs-icon {
  position: absolute;
  left: 0;
  top: 5px;
  font-size: 16px;
}

.obs-val {
  display: flex;
  align-items: baseline;
  gap: 5px;
}

.obs-num {
  font-size: 24px;
  color: #00ff9d;
  font-weight: bold;
}

.obs-unit {
  font-size: 12px;
  color: #888;
}

.obs-label {
  font-size: 10px;
  color: #666;
  letter-spacing: 1px;
}

.obs-divider {
  height: 1px;
  background: rgba(255,255,255,0.05);
  margin: 15px 0;
}

.obs-bar {
  height: 4px;
  background: rgba(255,255,255,0.1);
  margin-top: 5px;
  border-radius: 2px;
  overflow: hidden;
}

.obs-bar-fill {
  height: 100%;
}

.obs-row {
  display: flex;
  justify-content: space-between;
  color: #888;
  font-size: 12px;
  margin-bottom: 10px;
}

.obs-wave {
  height: 20px;
  border-bottom: 2px solid #0088ff;
  border-radius: 50%;
  margin: 20px 0;
  box-shadow: 0 10px 20px -10px #0088ff;
}

.obs-btn-active {
  background: rgba(255, 184, 0, 0.1);
  border: 1px solid #ffb800;
  color: #ffb800;
  text-align: center;
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  letter-spacing: 2px;
}

/* Node Manager Styles */
.node-manager {
  margin-top: 15px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 255, 157, 0.2);
  padding: 15px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.mode-switch {
  display: flex;
  gap: 10px;
}

.mode-switch button {
  background: transparent;
  border: 1px solid #555;
  color: #888;
  padding: 8px 12px;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-size: 11px;
}

.mode-switch button.active {
  background: rgba(0, 255, 157, 0.1);
  border-color: #00ff9d;
  color: #00ff9d;
}

.mode-switch button.danger-active {
  background: rgba(255, 45, 110, 0.1);
  border-color: #ff2d6e;
  color: #ff2d6e;
}

.mode-switch button.danger-btn:hover {
  border-color: #ff2d6e;
  color: #ff2d6e;
}

.divider {
  width: 1px;
  height: 30px;
  background: #333;
}

.record-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rec-btn {
  background: transparent;
  border: 1px solid #ff2d6e;
  color: #ff2d6e;
  padding: 8px 15px;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rec-btn:hover {
  background: rgba(255, 45, 110, 0.1);
}

.rec-btn.recording {
  background: rgba(255, 45, 110, 0.2);
  animation: pulse-red 1s infinite;
}

.rec-dot {
  width: 10px;
  height: 10px;
  background: #ff2d6e;
  border-radius: 50%;
  display: inline-block;
}

.stop-square {
  width: 10px;
  height: 10px;
  background: #ff2d6e;
  display: inline-block;
}

.download-link {
  color: #00ff9d;
  font-family: 'Orbitron', sans-serif;
  font-size: 11px;
  text-decoration: none;
  cursor: pointer;
}

.download-link:hover {
  text-decoration: underline;
}

@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(255, 45, 110, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(255, 45, 110, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 45, 110, 0); }
}

.advanced-stream-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 450px;
  height: 300px;
  background: rgba(10, 15, 20, 0.95);
  border: 1px solid #ffb800;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  z-index: 1000;
  box-shadow: 0 0 20px rgba(255, 184, 0, 0.2);
}

.advanced-header {
  background: #ffb800;
  color: #000;
  font-family: 'Orbitron', sans-serif;
  font-weight: bold;
  font-size: 12px;
  padding: 8px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  background: transparent;
  border: none;
  color: #000;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
}

.advanced-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  font-family: 'JetBrains Mono', monospace;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  backdrop-filter: blur(5px);
}

.modal-content.glitch-box {
  background: rgba(10, 15, 20, 0.95);
  border: 1px solid #00ff9d;
  border-radius: 4px;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 0 20px rgba(0, 255, 157, 0.2);
}

.modal-header {
  background: rgba(0, 255, 157, 0.1);
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 255, 157, 0.3);
}

.modal-header h2 {
  color: #00ff9d;
  margin: 0;
  font-family: 'Orbitron', sans-serif;
  font-size: 14px;
  letter-spacing: 1px;
}

.modal-header .close-btn {
  color: #00ff9d;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
}

.form-row {
  display: flex;
  gap: 15px;
}

.form-group label {
  color: #888;
  font-size: 11px;
  letter-spacing: 1px;
}

.hack-input, .hack-select {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #333;
  color: #00ff9d;
  padding: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
}

.hack-input:focus, .hack-select:focus {
  outline: none;
  border-color: #00ff9d;
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.2);
}

.modal-footer {
  padding: 15px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid rgba(0, 255, 157, 0.2);
}

.hack-btn {
  padding: 10px 20px;
  font-family: 'Orbitron', sans-serif;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid;
  background: transparent;
  transition: all 0.2s;
}

.hack-btn.primary {
  color: #00ff9d;
  border-color: #00ff9d;
  background: rgba(0, 255, 157, 0.1);
}

.hack-btn.primary:hover {
  background: rgba(0, 255, 157, 0.3);
  box-shadow: 0 0 15px rgba(0, 255, 157, 0.4);
}

.hack-btn.secondary {
  color: #aaa;
  border-color: #555;
}

.hack-btn.secondary:hover {
  color: #fff;
  border-color: #888;
}

.deploy-btn {
  background: rgba(0, 255, 157, 0.1);
  border: 1px solid #00ff9d;
  color: #00ff9d;
  padding: 10px 20px;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-weight: bold;
  letter-spacing: 1px;
  transition: all 0.2s;
}

.deploy-btn:hover {
  background: rgba(0, 255, 157, 0.3);
  box-shadow: 0 0 15px rgba(0, 255, 157, 0.4);
}

.log-line {
  border-bottom: 1px solid rgba(0, 255, 157, 0.1);
  padding: 4px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.node-input-group {
  display: flex;
  gap: 10px;
}

.node-input {
  background: #000;
  border: 1px solid #333;
  color: #00ff9d;
  padding: 8px 15px;
  font-family: monospace;
  outline: none;
  width: 250px;
}

.node-input:focus {
  border-color: #00ff9d;
}

.node-btn {
  background: rgba(0, 255, 157, 0.1);
  border: 1px solid #00ff9d;
  color: #00ff9d;
  padding: 8px 15px;
  cursor: pointer;
  font-weight: bold;
}

.node-btn:hover {
  background: rgba(0, 255, 157, 0.3);
}

.active-nodes-list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.no-nodes {
  color: #888;
  font-size: 12px;
  font-style: italic;
}

.node-badge {
  display: flex;
  align-items: center;
  background: rgba(10, 20, 30, 0.8);
  border: 1px solid;
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 12px;
  color: #fff;
}

.node-badge-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  box-shadow: 0 0 5px currentColor;
}

.node-ip {
  font-family: monospace;
  margin-right: 10px;
}

.node-remove {
  background: transparent;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

.node-remove:hover {
  color: #ff2d6e;
}

</style>

<style scoped>
.selected-badge {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 10px rgba(0, 255, 157, 0.5);
}
.selected-node {
  background: rgba(0, 255, 157, 0.15);
  border-left: 3px solid #00ff9d;
}
</style>
