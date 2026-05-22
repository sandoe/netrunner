<template>
  <div class="threat-map-container">
    <div class="threat-overlay">
      <div class="overlay-header">
        <div class="glitch-title" data-text="GLOBAL THREAT INTEL">GLOBAL THREAT INTEL</div>
        <div class="status-indicator">
          <span class="dot pulse"></span>
          <span>LIVE CTI FEED</span>
        </div>
      </div>
      
      <div class="feed-panel">
        <div class="feed-tabs">
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'targeted' }" 
            @click="activeTab = 'targeted'"
          >
            MIT NETVÆRK
            <span class="tab-badge" v-if="targetedThreats.length">{{ targetedThreats.length }}</span>
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'global' }" 
            @click="activeTab = 'global'"
          >
            GLOBALT FEED
          </button>
        </div>
        
        <transition-group name="list" tag="div" class="feed-list">
          <div 
            v-for="threat in filteredThreats" 
            :key="threat.id" 
            class="feed-item" 
            :class="[threat.severity, { targeted: threat.targeted }]"
          >
            <div class="feed-time-row">
              <span class="feed-time">{{ formatTime(threat.timestamp) }}</span>
              <span v-if="threat.targeted" class="target-badge">TARGETED_ALERT</span>
            </div>
            <div class="feed-content">
              <span class="threat-type" :class="{ 'neon-alert': threat.targeted }">{{ threat.type }}</span>
              <span class="threat-route">
                {{ threat.source.city }} → 
                <span :class="{ 'highlight-target': threat.targeted }">{{ threat.target.city }}</span>
              </span>
            </div>
          </div>
        </transition-group>
      </div>
    </div>
    
    <div ref="globeEl" class="globe-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, shallowRef, computed } from 'vue'
import Globe from 'globe.gl'

const globeEl = ref<HTMLElement | null>(null)
let globe: any = null
let ws: WebSocket | null = null

interface ThreatEvent {
  id: string
  timestamp: number
  source: { ip: string; city: string; lat: number; lng: number }
  target: { ip: string; city: string; lat: number; lng: number }
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  targeted?: boolean
}

const activeTab = ref<'targeted' | 'global'>('targeted')
const targetedThreats = ref<ThreatEvent[]>([])
const globalThreats = ref<ThreatEvent[]>([])
const arcsData = shallowRef<any[]>([])
const beaconsData = ref<any[]>([])

const filteredThreats = computed(() => {
  return activeTab.value === 'targeted' ? targetedThreats.value : globalThreats.value
})

function formatTime(ts: number) {
  const d = new Date(ts * 1000)
  return d.toISOString().split('T')[1].split('.')[0]
}

function getColor(severity: string) {
  switch (severity) {
    case 'critical': return '#ff0055'
    case 'high': return '#ff6b35'
    case 'medium': return '#ffbe0b'
    default: return '#00e5ff'
  }
}

async function fetchNodes() {
  try {
    const res = await fetch('/api/threats/nodes')
    if (res.ok) {
      const nodes = await res.json()
      beaconsData.value = nodes.map((n: any) => ({
        ...n,
        color: n.name.toLowerCase().includes('rpi') ? '#00e5ff' : '#ff00aa'
      }))
      
      if (globe) {
        // Draw Beacons (Rings)
        globe.ringsData(beaconsData.value)
             .ringColor(d => d.color)
             .ringMaxRadius(3.5)
             .ringPropagationSpeed(1.2)
             .ringRepeatNum(2)

        // Draw svævende 3D Navneskilte (Labels)
        globe.labelsData(beaconsData.value)
             .labelLat(d => d.lat)
             .labelLng(d => d.lng)
             .labelText(d => d.name)
             .labelColor(d => d.color)
             .labelSize(1.8)
             .labelDotRadius(0.6)
             .labelResolution(2)
      }
    }
  } catch (e) {
    console.error("Failed to fetch threat nodes", e)
  }
}

onMounted(() => {
  if (!globeEl.value) return

  // Initialize Globe
  globe = Globe()(globeEl.value)
    .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
    .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
    .backgroundColor('rgba(0,0,0,0)')
    .arcColor('color')
    .arcDashLength(d => d.isTargeted ? 0.5 : 0.3)
    .arcDashGap(d => d.isTargeted ? 0.15 : 0.3)
    .arcDashInitialGap(() => Math.random())
    .arcDashAnimateTime(d => d.isTargeted ? 1200 : 2200)
    .arcAltitudeAutoScale(0.3)
    .arcStroke(d => d.isTargeted ? 0.85 : 0.28)

  // Configure camera/controls
  globe.controls().autoRotate = true
  globe.controls().autoRotateSpeed = 1.2
  globe.controls().enableZoom = false

  // Handle window resize
  const onResize = () => {
    if (globeEl.value) {
      globe.width(globeEl.value.clientWidth)
      globe.height(globeEl.value.clientHeight)
    }
  }
  window.addEventListener('resize', onResize)
  onResize() // initial size

  // Fetch nodes and draw beacons/labels
  fetchNodes()

  // Connect WebSocket
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/threats`
  ws = new WebSocket(wsUrl)
  
  ws.onmessage = (event) => {
    try {
      const threat: ThreatEvent = JSON.parse(event.data)
      const isTargeted = !!threat.targeted
      
      // Update UI lists
      if (isTargeted) {
        targetedThreats.value.unshift(threat)
        if (targetedThreats.value.length > 20) {
          targetedThreats.value.pop()
        }
      } else {
        globalThreats.value.unshift(threat)
        if (globalThreats.value.length > 20) {
          globalThreats.value.pop()
        }
      }
      
      // Update arcs
      const baseColor = getColor(threat.severity)
      // Targeted arcs are bright neon; global ambient arcs are dæmpet semi-transparent orange
      const color = isTargeted ? baseColor : 'rgba(255, 107, 53, 0.35)'
      
      const newArc = {
        startLat: threat.source.lat,
        startLng: threat.source.lng,
        endLat: threat.target.lat,
        endLng: threat.target.lng,
        color: [color, color],
        isTargeted: isTargeted
      }
      
      const currentArcs = arcsData.value
      arcsData.value = [...currentArcs, newArc]
      
      // Keep only last 40 arcs for performance
      if (arcsData.value.length > 40) {
        arcsData.value = arcsData.value.slice(-40)
      }
      
      globe.arcsData(arcsData.value)
    } catch (e) {
      console.error("Failed to parse threat event", e)
    }
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
  if (globe) {
    if (globeEl.value) {
      globeEl.value.innerHTML = ''
    }
  }
})
</script>

<style scoped>
.threat-map-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: radial-gradient(circle at center, #081a25 0%, #020408 100%);
  overflow: hidden;
}

.globe-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
}

.threat-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 10;
  pointer-events: none;
  padding: 30px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.overlay-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.glitch-title {
  font-family: var(--font-hd);
  font-size: 32px;
  font-weight: 900;
  color: var(--cyan);
  text-transform: uppercase;
  letter-spacing: 4px;
  text-shadow: 0 0 20px var(--cyan);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(8, 13, 24, 0.7);
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--r);
  backdrop-filter: blur(8px);
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--green);
  letter-spacing: 2px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green);
}

.dot.pulse {
  box-shadow: 0 0 10px var(--green);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.5); }
  100% { opacity: 1; transform: scale(1); }
}

.feed-panel {
  width: 380px;
  background: rgba(5, 8, 15, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: var(--r2);
  backdrop-filter: blur(10px);
  padding: 20px;
  pointer-events: auto;
  margin-bottom: 20px;
}

.feed-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  padding-bottom: 12px;
}

.tab-btn {
  flex: 1;
  background: rgba(12, 18, 32, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.15);
  color: var(--textbr);
  padding: 8px 12px;
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 1.5px;
  border-radius: var(--r);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover {
  background: rgba(0, 229, 255, 0.05);
  border-color: rgba(0, 229, 255, 0.4);
  color: var(--textwh);
}

.tab-btn.active {
  background: rgba(0, 229, 255, 0.1);
  border-color: var(--cyan);
  color: var(--cyan);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
  box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.1);
}

.tab-badge {
  background: #ff0055;
  color: #fff;
  font-size: 8px;
  font-family: var(--font-co);
  padding: 1px 5px;
  border-radius: 10px;
  text-shadow: none;
  animation: pulse-red 1.5s infinite;
}

@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0.7); }
  70% { box-shadow: 0 0 0 5px rgba(255, 0, 85, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0); }
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}

/* Custom Scrollbar for list */
.feed-list::-webkit-scrollbar {
  width: 4px;
}
.feed-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}
.feed-list::-webkit-scrollbar-thumb {
  background: rgba(0, 229, 255, 0.2);
  border-radius: 2px;
}

.feed-item {
  display: flex;
  flex-direction: column;
  background: rgba(12, 18, 32, 0.8);
  padding: 10px;
  border-radius: var(--r);
  border-left: 3px solid var(--cyan);
  transition: all 0.3s ease;
}

.feed-item.critical { border-left-color: #ff0055; background: rgba(255, 0, 85, 0.05); }
.feed-item.high { border-left-color: #ff6b35; background: rgba(255, 107, 53, 0.05); }
.feed-item.medium { border-left-color: #ffbe0b; }

.feed-item.targeted {
  border-left: 3px dashed #ff0055;
  background: rgba(255, 0, 85, 0.05);
  box-shadow: inset 0 0 15px rgba(255, 0, 85, 0.03);
}

.feed-item.targeted:hover {
  background: rgba(255, 0, 85, 0.08);
}

.feed-time-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.feed-time {
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--text);
}

.target-badge {
  font-family: var(--font-hd);
  font-size: 8px;
  background: rgba(255, 0, 85, 0.15);
  color: #ff0055;
  border: 1px solid rgba(255, 0, 85, 0.5);
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 1px;
  text-shadow: 0 0 5px rgba(255, 0, 85, 0.5);
  animation: heartbeat 1.5s infinite;
}

@keyframes heartbeat {
  0% { transform: scale(1); }
  14% { transform: scale(1.08); }
  28% { transform: scale(1); }
  42% { transform: scale(1.08); }
  70% { transform: scale(1); }
}

.feed-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.threat-type {
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--textwh);
}

.neon-alert {
  color: #ff0055 !important;
  text-shadow: 0 0 8px rgba(255, 0, 85, 0.4);
}

.threat-route {
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--textbr);
}

.highlight-target {
  color: var(--cyan) !important;
  text-shadow: 0 0 5px rgba(0, 229, 255, 0.5);
  font-weight: bold;
}

/* List Transitions */
.list-enter-active, .list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}
.list-leave-to {
  opacity: 0;
  transform: translateY(30px);
}
</style>
