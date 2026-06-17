<template>
  <div class="agent-map-container">
    <div class="header-panel">
      <div>
        <h1 class="glitch-text" data-text="GLOBAL AGENT DEPLOYMENT">GLOBAL AGENT DEPLOYMENT</h1>
        <p class="subtitle">Live Tracking & Reconnaissance Map</p>
      </div>
      
      <div class="action-panel">
        <button class="btn btn-ghost-protocol" @click="confirmGhostProtocol">
          <i class="fas fa-skull"></i>
          GHOST PROTOCOL (Scrub Traces)
        </button>
      </div>
    </div>

    <!-- Map Container -->
    <div class="map-wrapper">
      <div id="agent-map" class="map-element"></div>
      
      <!-- Overlay Stats -->
      <div class="map-overlay-stats">
        <div class="stat-box">
          <span class="stat-label">ACTIVE BEACONS</span>
          <span class="stat-value">{{ beaconsCount }}</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">TOTAL NODES</span>
          <span class="stat-value">{{ nodesCount }}</span>
        </div>
      </div>
    </div>

    <!-- Confirmation Modal -->
    <div v-if="showConfirm" class="modal-overlay">
      <div class="modal-content danger-modal">
        <h2><i class="fas fa-exclamation-triangle"></i> INITIATE GHOST PROTOCOL?</h2>
        <p>This action will <strong>permanently erase</strong> all agent deployments, wipe local logs, and drop the entire intelligence database.</p>
        <p class="warning-text">THERE IS NO UNDO. ALL TRACES WILL BE SCRUBBED.</p>
        
        <div class="modal-actions">
          <button class="btn btn-cancel" @click="showConfirm = false">CANCEL</button>
          <button class="btn btn-nuke" @click="executeGhostProtocol" :disabled="isExecuting">
            <span v-if="isExecuting"><i class="fas fa-spinner fa-spin"></i> SCRUBBING...</span>
            <span v-else>EXECUTE GHOST PROTOCOL</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for Leaflet default icon paths in Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
});

// Custom Cyberpunk Icon
const cyberIcon = L.divIcon({
  className: 'cyber-marker',
  html: '<div class="pulse-marker"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10]
})

const map = ref(null)
const markers = ref({})
const nodesCount = ref(0)
const beaconsCount = ref(0)

const showConfirm = ref(false)
const isExecuting = ref(false)

const initMap = () => {
  // Initialize map centered roughly on Europe/Global
  map.value = L.map('agent-map', {
    center: [20, 0],
    zoom: 2,
    zoomControl: false,
    attributionControl: false
  })

  // Dark/Cyberpunk style tiles (using CartoDB Dark Matter)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd'
  }).addTo(map.value)

  // Add zoom control to top right
  L.control.zoom({ position: 'topright' }).addTo(map.value)
}

const loadNodes = async () => {
  try {
    const token = localStorage.getItem('nr_token');
    const res = await fetch('/api/nodes', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error('Failed to fetch nodes');
    const data = await res.json();
    
    let nCnt = 0
    let bCnt = 0
    
    // Clear old markers
    Object.values(markers.value).forEach(m => map.value.removeLayer(m))
    markers.value = {}

    for (const [nid, node] of Object.entries(data)) {
      nCnt++
      if (node.device_type === 'linux' || node.has_password) bCnt++ // rough proxy for beacons

      const lat = node.metadata?.lat
      const lng = node.metadata?.lng
      const city = node.metadata?.city || 'Unknown Location'

      if (lat !== undefined && lng !== undefined) {
        const marker = L.marker([lat, lng], { icon: cyberIcon })
          .addTo(map.value)
          .bindPopup(`
            <div class="cyber-popup">
              <h3>${node.name}</h3>
              <p><strong>IP:</strong> ${node.host}</p>
              <p><strong>Location:</strong> ${city}</p>
              <p><strong>Status:</strong> <span class="text-green">Active</span></p>
            </div>
          `)
        markers.value[nid] = marker
      }
    }
    
    nodesCount.value = nCnt
    beaconsCount.value = bCnt
  } catch (err) {
    console.error("Failed to load nodes for map:", err)
  }
}

const confirmGhostProtocol = () => {
  showConfirm.value = true
}

const executeGhostProtocol = async () => {
  isExecuting.value = true
  try {
    const token = localStorage.getItem('nr_token');
    const res = await fetch('/api/v1/system/cleanup', { 
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error('Cleanup API failed');
    const result = await res.json();
    alert("Ghost Protocol Executed: " + result.message)
    showConfirm.value = false
    // Reload map to show it empty
    await loadNodes()
  } catch (err) {
    alert("Failed to execute Ghost Protocol: " + err.message)
  } finally {
    isExecuting.value = false
  }
}

let pollInterval;

onMounted(() => {
  initMap()
  loadNodes()
  // Refresh nodes every 30s
  pollInterval = setInterval(loadNodes, 30000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (map.value) {
    map.value.remove()
  }
})
</script>

<style scoped>
.agent-map-container {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.header-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface-1);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.subtitle {
  color: var(--text-muted);
  margin-top: 5px;
  font-family: 'Space Mono', monospace;
  font-size: 0.9rem;
}

.map-wrapper {
  flex-grow: 1;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--primary-color);
  box-shadow: 0 0 20px rgba(0, 255, 170, 0.1);
}

.map-element {
  width: 100%;
  height: 100%;
  background: #1a1a1a;
  z-index: 1;
}

/* Override Leaflet styles to match theme */
:deep(.leaflet-popup-content-wrapper) {
  background: var(--surface-1);
  color: var(--text-color);
  border: 1px solid var(--primary-color);
  border-radius: 4px;
}
:deep(.leaflet-popup-tip) {
  background: var(--surface-1);
  border: 1px solid var(--primary-color);
}
:deep(.cyber-popup) {
  font-family: 'Inter', sans-serif;
}
:deep(.cyber-popup h3) {
  margin: 0 0 10px 0;
  color: var(--primary-color);
  font-family: 'Space Mono', monospace;
}
:deep(.cyber-popup p) {
  margin: 5px 0;
  font-size: 0.9rem;
}
:deep(.text-green) {
  color: #00ffaa;
}

/* Custom CSS marker */
:deep(.pulse-marker) {
  width: 12px;
  height: 12px;
  background-color: var(--primary-color);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--primary-color);
  position: relative;
}
:deep(.pulse-marker::after) {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background-color: var(--primary-color);
  border-radius: 50%;
  z-index: -1;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(3); opacity: 0; }
}

.map-overlay-stats {
  position: absolute;
  bottom: 20px;
  left: 20px;
  z-index: 1000;
  display: flex;
  gap: 15px;
}

.stat-box {
  background: rgba(10, 10, 12, 0.85);
  border: 1px solid var(--border-color);
  padding: 15px 20px;
  border-radius: 6px;
  backdrop-filter: blur(5px);
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: 'Space Mono', monospace;
  color: var(--primary-color);
}

.btn-ghost-protocol {
  background: rgba(255, 51, 102, 0.1);
  color: #ff3366;
  border: 1px solid #ff3366;
  font-weight: bold;
  letter-spacing: 1px;
  padding: 12px 24px;
  transition: all 0.3s ease;
}

.btn-ghost-protocol:hover {
  background: #ff3366;
  color: #fff;
  box-shadow: 0 0 20px rgba(255, 51, 102, 0.5);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(5px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.danger-modal {
  background: #111;
  border: 2px solid #ff3366;
  padding: 30px;
  border-radius: 8px;
  max-width: 500px;
  text-align: center;
  box-shadow: 0 0 40px rgba(255, 51, 102, 0.2);
}

.danger-modal h2 {
  color: #ff3366;
  margin-bottom: 20px;
  font-family: 'Space Mono', monospace;
}

.danger-modal p {
  color: var(--text-color);
  margin-bottom: 15px;
  line-height: 1.5;
}

.warning-text {
  color: #ff3366;
  font-weight: bold;
  font-size: 0.9rem;
  letter-spacing: 1px;
}

.modal-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 30px;
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--text-muted);
  color: var(--text-color);
}
.btn-cancel:hover {
  background: rgba(255,255,255,0.1);
}

.btn-nuke {
  background: #ff3366;
  color: white;
  border: none;
  font-weight: bold;
  padding: 10px 20px;
}
.btn-nuke:hover:not(:disabled) {
  background: #ff0040;
  box-shadow: 0 0 20px rgba(255, 51, 102, 0.8);
}
.btn-nuke:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
