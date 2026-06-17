<template>
  <div class="bt-view">
    <div class="bt-header">
      <div class="header-title">
        <span class="icon">📡</span> BLUETOOTH CONTROL ROOM
        <span class="pulse" :class="{ active: connected }"></span>
      </div>
      <div class="header-stats">
        <span>{{ sortedDevices.length }} DEVICES DETECTED</span>
        <button v-if="store.selectedId" class="btn btn-outline" style="margin-left: 10px; border-color: var(--green); color: var(--green); padding: 2px 8px; font-size: 10px;" @click="toggleNodeBluetooth(true)">
          TURN ON NODE BT
        </button>
        <button v-if="store.selectedId" class="btn btn-outline" style="margin-left: 10px; border-color: var(--pink); color: var(--pink); padding: 2px 8px; font-size: 10px;" @click="toggleNodeBluetooth(false)">
          TURN OFF NODE BT
        </button>
        <button v-if="store.selectedId" class="btn btn-outline" style="margin-left: 10px; border-color: var(--cyan); color: var(--cyan); padding: 2px 8px; font-size: 10px;" @click="store.select(null)">
          CLEAR NODE FILTER
        </button>

      </div>
    </div>
    
    <div class="bt-content">
      <div class="radar-container aliens-theme">
        <div class="radar-crt-overlay"></div>
        <div class="radar">
          <div class="sweep"></div>
          <div class="ring r1"></div>
          <div class="ring r2"></div>
          <div class="ring r3"></div>
          <div class="ring r4"></div>
          <div class="crosshair-v"></div>
          <div class="crosshair-h"></div>
          
          <template v-if="!triangulationMode">
            <div 
              v-for="dev in sortedDevices" 
              :key="dev.mac" 
              class="blip"
              :class="{ 
                'true-aoa': dev.azimuth !== undefined,
                'jamming-target': jammedTargets[dev.mac] 
              }"
              :style="getBlipStyle(dev)"
              :title="dev.name + ' (' + dev.mac + ')'"
              @click="selectedDevice = dev; triangulationMode = false"
            >
              <div class="blip-ripple"></div>
              <div class="jamming-lightning" v-if="jammedTargets[dev.mac]"></div>
              <div class="blip-label">{{ dev.name !== 'Unknown Device' ? dev.name : dev.mac.substring(0,8) }}</div>
            </div>
          </template>

          <template v-else-if="selectedDevice && selectedDevice.nodes">
            <!-- Triangulation Mode: Render Nodes -->
            <div 
              v-for="(pos, nid) in triangulationData.nodes" 
              :key="nid" 
              class="blip node-blip"
              :style="{ left: pos.x + '%', top: pos.y + '%' }"
            >
              <div class="node-label" style="top: -30px">{{ nid }}<br>{{ selectedDevice.nodes[nid]?.rssi ? rssiToDistance(selectedDevice.nodes[nid].rssi) : '?' }}m</div>
            </div>
            
            <!-- Triangulation Mode: Render Target (Weighted Center) -->
            <div class="blip target-blip" :style="{ left: triangulationData.target.x + '%', top: triangulationData.target.y + '%', background: '#ff3333', boxShadow: '0 0 15px #ff3333, 0 0 30px #ff0000', width: '16px', height: '16px' }">
              <div class="blip-ripple" style="border-color: #ff3333;"></div>
              <div class="blip-label text-pink" style="top: -25px; color: #ff3333 !important; font-size: 12px; background: rgba(0,0,0,0.8); border-color: #ff3333;">TARGET</div>
            </div>
          </template>
        </div>
        <div class="closest-range" v-if="sortedDevices.length">
          <span class="range-label">PROXIMITY</span>
          <span class="range-val">{{ Math.abs(sortedDevices[0].rssi) }} <small>m</small></span>
        </div>
      </div>
      
      <div class="device-list">
        <h3>DISCOVERED DEVICES</h3>
        <div v-if="devices.length === 0" class="empty-list">No devices found. Scanning...</div>
        <div 
          v-for="dev in sortedDevices" 
          :key="dev.mac"
          class="device-card"
          :class="{ selected: selectedDevice && selectedDevice.mac === dev.mac }"
          @click="selectedDevice = dev"
        >
          <div class="card-header">
            <span class="dev-name">{{ dev.name }}</span>
            <span class="dev-rssi" :class="getRssiClass(dev.rssi)">{{ dev.rssi }} dBm</span>
          </div>
          <div class="card-body">
            <div class="dev-mac">{{ dev.mac }}</div>
            <div class="dev-seen">Last seen: {{ Math.round((Date.now() - dev.last_seen * 1000) / 1000) }}s ago</div>
          </div>
        </div>
      </div>
      
      <div class="device-details" v-if="selectedDevice">
        <h3>DEVICE DETAILS</h3>
        <div class="detail-row">
          <span class="lbl">NAME:</span>
          <span class="val">{{ selectedDevice.name }}</span>
        </div>
        <div class="detail-row">
          <span class="lbl">MAC:</span>
          <span class="val">{{ selectedDevice.mac }}</span>
        </div>
        <div class="detail-row" v-if="selectedDevice.azimuth !== undefined">
          <span class="lbl">AOA AZIMUTH:</span>
          <span class="val text-pink">{{ selectedDevice.azimuth }}° (True)</span>
        </div>
        <div class="detail-row">
          <span class="lbl">SIGNAL:</span>
          <span class="val" :class="getRssiClass(selectedDevice.rssi)">{{ selectedDevice.rssi }} dBm</span>
        </div>
        <div class="detail-row" v-if="selectedDevice.tx_power !== undefined && selectedDevice.tx_power !== null">
          <span class="lbl">TX POWER:</span>
          <span class="val">{{ selectedDevice.tx_power }} dBm</span>
        </div>
        <div class="detail-row" v-if="selectedDevice.manufacturer_data && Object.keys(selectedDevice.manufacturer_data).length > 0">
          <span class="lbl">MANUFACTURER:</span>
          <div class="val-box">
            <div v-for="(hex, id) in selectedDevice.manufacturer_data" :key="id">
              [0x{{ Number(id).toString(16).toUpperCase() }}] {{ hex }}
            </div>
          </div>
        </div>
        <div class="detail-row" v-if="selectedDevice.service_uuids && selectedDevice.service_uuids.length > 0">
          <span class="lbl">SERVICES:</span>
          <div class="val-box">
            <div v-for="uuid in selectedDevice.service_uuids" :key="uuid">
              {{ uuid }}
            </div>
          </div>
        </div>
        
        
        <div class="detail-row" v-if="selectedDevice.nodes && Object.keys(selectedDevice.nodes).length > 0">
          <button class="btn btn-outline" style="width: 100%; border-color: var(--cyan); color: var(--cyan);" @click="triangulationMode = !triangulationMode">
            {{ triangulationMode ? 'DEACTIVATE TRIANGULATION' : 'ACTIVATE TRIANGULATION' }}
          </button>
        </div>

        <div class="detail-row" v-if="selectedDevice.nodes && Object.keys(selectedDevice.nodes).length > 0">
          <span class="lbl">SEEN BY:</span>
          <div class="val-box">
            <div v-for="(ndata, nid) in selectedDevice.nodes" :key="nid" :class="{ 'text-cyan': store.selectedId === nid }">
              {{ nid }}: <span :class="getRssiClass(ndata.rssi)">{{ ndata.rssi }} dBm</span> 
              <span class="text-cyan">(Est. {{ rssiToDistance(ndata.rssi) }}m)</span>
            </div>
          </div>
        </div>
        
        <!-- Active Enumeration Data -->
        <div class="detail-row" v-if="selectedDevice.enum_data">
          <span class="lbl text-pink">GATT PROFILE:</span>
          <div class="val-box gatt-box">
            <div v-for="(srv, uuid) in selectedDevice.enum_data" :key="uuid" class="gatt-service">
              <div class="gatt-title">{{ srv.description || uuid }}</div>
              <div v-for="(cval, cname) in srv.characteristics" :key="cname" class="gatt-char">
                <span class="cname">{{ cname }}:</span> <span class="cval">{{ cval }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="actions">
          <button 
            class="btn-action" 
            @click="enumerateDevice(selectedDevice.mac)" 
            :disabled="selectedDevice.enumerating"
          >
            {{ selectedDevice.enumerating ? 'ENUMERATING...' : 'CONNECT / ENUMERATE' }}
          </button>
          <button class="btn-action" @click="pairingModalVisible = true; pairingStatus = ''">
            PAIR DEVICE 🔗
          </button>
          <button 
            v-if="!jammedTargets[selectedDevice.mac]"
            class="btn-action btn-danger" 
            @click="toggleJam(selectedDevice.mac)"
          >
            ENGAGE JAMMER 💥
          </button>
          <button 
            v-else
            class="btn-action btn-danger jamming-active" 
            @click="toggleJam(selectedDevice.mac)"
          >
            STOP JAMMING 🛑
          </button>
        </div>
      </div>
    </div>

    <!-- Pairing Modal -->
    <div class="modal-overlay" v-if="pairingModalVisible">
      <div class="modal-box aliens-theme-box">
        <h3>PAIR BLUETOOTH DEVICE</h3>
        <p>Target: <strong class="text-cyan">{{ selectedDevice?.mac }}</strong> ({{ selectedDevice?.name }})</p>
        <div v-if="pairingStatus" class="pairing-status" :class="{'text-pink': pairingStatus.includes('failed') || pairingStatus.includes('error'), 'text-green': pairingStatus.includes('success')}">
          {{ pairingStatus }}
        </div>
        <div class="actions" style="margin-top: 20px; flex-direction: row; justify-content: center; padding: 0;">
          <button class="btn-action" style="flex: 1" @click="confirmPairing" :disabled="isPairing">
            {{ isPairing ? 'PAIRING...' : 'CONFIRM PAIRING' }}
          </button>
          <button class="btn-action btn-outline text-pink" style="border-color: var(--pink)" @click="pairingModalVisible = false; pairingStatus = ''">CANCEL</button>
        </div>
      </div>
    </div>

    <!-- Recon Modal -->
    <div class="modal-overlay" v-if="reconModalVisible">
      <div class="modal-box aliens-theme-box" style="width: 800px; max-width: 90vw;">
        <h3 class="text-green">ADVANCED RECONNAISSANCE DATA</h3>
        <p>Target Node: <strong class="text-cyan">{{ store.selectedId }}</strong></p>
        <div class="recon-data-container" style="max-height: 60vh; overflow-y: auto; text-align: left; background: rgba(0,0,0,0.8); padding: 15px; font-family: monospace; font-size: 11px; white-space: pre-wrap; color: var(--green); border: 1px solid var(--green); border-radius: 4px; box-shadow: inset 0 0 10px rgba(0,255,0,0.2);">
          {{ reconData || 'Loading OSINT payload...' }}
        </div>
        <div class="actions" style="margin-top: 20px; flex-direction: row; justify-content: center; padding: 0;">
          <button class="btn-action btn-cancel text-cyan" style="border-color: var(--cyan)" @click="reconModalVisible = false">CLOSE RECON</button>
        </div>
      </div>
    </div>

  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { wsBase, wsTokenParam } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'

const store = useNodesStore()

interface BluetoothDevice {
  mac: string
  name: string
  rssi: number
  last_seen: number
  azimuth?: number
  manufacturer_data?: Record<string, string>
  service_uuids?: string[]
  tx_power?: number
  enum_data?: any
  enumerating?: boolean
  nodes?: Record<string, { rssi: number, last_seen: number }>
}

const devices = ref<BluetoothDevice[]>([])
const selectedDevice = ref<BluetoothDevice | null>(null)
const connected = ref(false)
const triangulationMode = ref(false)
const jammedTargets = ref<Record<string, boolean>>({})
let ws: WebSocket | null = null

const pairingModalVisible = ref(false)
const isPairing = ref(false)
const pairingStatus = ref('')

const reconModalVisible = ref(false)
const reconData = ref('')

async function injectRecon(nid: string) {
  reconModalVisible.value = true
  reconData.value = "Initiating Advanced Recon Agent deployment to " + nid + "..."
  try {
    const res = await fetch(`/api/nodes/${nid}/recon/inject`, { 
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    reconData.value = data.detail || data.message || "Unknown error"
  } catch (err) {
    reconData.value = "Deploy Error: " + err
  }
}

async function stopRecon(nid: string) {
  reconModalVisible.value = true
  reconData.value = "Sending kill signal to Recon Agent..."
  try {
    const res = await fetch(`/api/nodes/${nid}/recon/stop`, { 
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    reconData.value = data.detail || data.message || "Unknown error"
  } catch (err) {
    reconData.value = "Stop Error: " + err
  }
}

async function fetchRecon(nid: string) {
  reconData.value = 'Intercepting reconnaissance data stream from ' + nid + '...'
  reconModalVisible.value = true
  try {
    const res = await fetch(`/api/nodes/${nid}/recon/fetch`, {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    const data = await res.json()
    if (!data.data) {
      reconData.value = "No recon data intercepted. Verify if agent is actively running."
    } else {
      reconData.value = data.data
    }
  } catch (err) {
    reconData.value = "Fetch Error: " + err
  }
}

const sortedDevices = computed(() => {
  let list = devices.value

  // If a specific node is selected, only show devices seen by that node
  // and use that node's specific RSSI.
  if (store.selectedId) {
    list = list.filter(d => d.nodes && d.nodes[store.selectedId])
    list = list.map(d => ({
      ...d,
      rssi: d.nodes[store.selectedId].rssi
    }))
  }

  return [...list].sort((a, b) => b.rssi - a.rssi)
})

async function toggleJam(mac: string) {
  const query = store.selectedId ? `?node_id=${store.selectedId}` : ''
  const isJamming = jammedTargets.value[mac]
  const endpoint = isJamming ? `/api/bluetooth/unjam/${mac}${query}` : `/api/bluetooth/jam/${mac}${query}`
  
  try {
    const res = await fetch(endpoint, { method: 'POST' })
    const data = await res.json()
    if (data.status.includes('engaged') || data.status.includes('already')) {
      jammedTargets.value[mac] = true
    } else {
      delete jammedTargets.value[mac]
    }
  } catch (e) {
    console.error("Jam API failed", e)
  }
}

async function confirmPairing() {
  if (!selectedDevice.value) return
  isPairing.value = true
  pairingStatus.value = 'Initiating pairing sequence...'
  try {
    const res = await fetch(`/api/bluetooth/pair/${selectedDevice.value.mac}`, { method: 'POST' })
    const data = await res.json()
    pairingStatus.value = `[${data.status.toUpperCase()}] ${data.message}`
  } catch (e: any) {
    pairingStatus.value = `[ERROR] ${e.message}`
  } finally {
    isPairing.value = false
  }
}

async function toggleNodeBluetooth(enable: boolean) {
  if (!store.selectedId) return
  const cmds = enable ? 
    ["sudo -n rfkill unblock bluetooth || rfkill unblock bluetooth", "sudo -n hciconfig hci0 up || hciconfig hci0 up", "echo 'Bluetooth enabled'"] :
    ["sudo -n rfkill block bluetooth || rfkill block bluetooth", "sudo -n hciconfig hci0 down || hciconfig hci0 down", "echo 'Bluetooth disabled'"]
  
  try {
    const res = await fetch(`/api/nodes/${store.selectedId}/execute`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ commands: cmds })
    })
    const data = await res.json()
    console.log("Toggle BT output:", data)
    alert(`Bluetooth on node ${store.selectedId} ${enable ? 'turned ON' : 'turned OFF'}`)
  } catch (e) {
    console.error("Failed to change Bluetooth state", e)
    alert("Failed to change Bluetooth state")
  }
}

async function enumerateDevice(mac: string) {
  const idx = devices.value.findIndex(d => d.mac === mac)
  if (idx === -1) return
  
  devices.value[idx].enumerating = true
  if (selectedDevice.value && selectedDevice.value.mac === mac) {
    selectedDevice.value.enumerating = true
  }
  
  try {
    const res = await fetch(`/api/bluetooth/enumerate/${mac}`, { method: 'POST' })
    const data = await res.json()
    if (data.status === 'success') {
      devices.value[idx].enum_data = data.services
      if (selectedDevice.value && selectedDevice.value.mac === mac) {
        selectedDevice.value.enum_data = data.services
      }
    } else {
      console.error("Enumeration failed", data.error)
      alert("Enumeration failed: " + data.error)
    }
  } catch (e) {
    console.error("Enumerate API failed", e)
  } finally {
    devices.value[idx].enumerating = false
    if (selectedDevice.value && selectedDevice.value.mac === mac) {
      selectedDevice.value.enumerating = false
    }
  }
}

function getRssiClass(rssi: number) {
  if (rssi > -60) return 'signal-strong'
  if (rssi > -80) return 'signal-med'
  return 'signal-weak'
}

function rssiToDistance(rssi: number): string {
  // Distance = 10 ^ ((TxPower - RSSI) / (10 * N))
  const txPower = -59
  const n = 2.0
  if (!rssi) return "?"
  const dist = Math.pow(10, (txPower - rssi) / (10 * n))
  return dist.toFixed(1)
}

function getBlipStyle(dev: BluetoothDevice) {
  // Map RSSI (-100 to -40) to distance from center (100% to 0%)
  // -40 is very close (radius ~ 10%), -100 is far (radius ~ 90%)
  let distance = (Math.abs(dev.rssi) - 30) / 70
  distance = Math.max(0.1, Math.min(0.95, distance))
  
  let angle = 0;
  
  if (dev.azimuth !== undefined) {
    // True hardware AoA angle
    angle = dev.azimuth
  } else {
    // Fallback: Use MAC address to generate a stable pseudo-random angle
    let hash = 0
    for (let i = 0; i < dev.mac.length; i++) {
      hash = dev.mac.charCodeAt(i) + ((hash << 5) - hash)
    }
    angle = Math.abs(hash % 360)
  }
  
  // subtract 90 so 0 is "North" (top)
  const rad = (angle - 90) * (Math.PI / 180)
  const cx = 50 + distance * 50 * Math.cos(rad)
  const cy = 50 + distance * 50 * Math.sin(rad)
  
  return {
    left: `${cx}%`,
    top: `${cy}%`,
    /* Let CSS classes handle the color for Aliens theme */
  }
}

const triangulationData = computed(() => {
  const result = {
    nodes: {} as Record<string, { x: number, y: number }>,
    target: { x: 50, y: 50 }
  };
  
  if (!selectedDevice.value || !selectedDevice.value.nodes) return result;
  
  const nodeKeys = Object.keys(selectedDevice.value.nodes);
  if (nodeKeys.length === 0) return result;
  
  // Faste positioner til noderne (i en ring på 40% afstand fra midten)
  nodeKeys.forEach((nid, index) => {
    if (nodeKeys.length === 1) {
      result.nodes[nid] = { x: 50, y: 50 }; // Placer i midten, hvis der kun er 1 node
    } else {
      const angle = (360 / nodeKeys.length) * index;
      const rad = (angle - 90) * (Math.PI / 180);
      result.nodes[nid] = { 
        x: 50 + 40 * Math.cos(rad), 
        y: 50 + 40 * Math.sin(rad) 
      };
    }
  });
  
  if (nodeKeys.length === 1) {
    // Falsk sonar-visning hvis der kun er 1 node (som før)
    const nid = nodeKeys[0];
    const ndata = selectedDevice.value.nodes[nid];
    let distance = (Math.abs(ndata.rssi) - 30) / 70;
    distance = Math.max(0.15, Math.min(0.95, distance));
    
    let hash = 0;
    for (let i = 0; i < selectedDevice.value.mac.length; i++) {
      hash = selectedDevice.value.mac.charCodeAt(i) + ((hash << 5) - hash);
    }
    const angle = Math.abs(hash % 360);
    const rad = (angle - 90) * (Math.PI / 180);
    
    result.target = {
      x: 50 + distance * 50 * Math.cos(rad),
      y: 50 + distance * 50 * Math.sin(rad)
    };
  } else {
    // Ægte Trilateration (Weighted Average / Center of Mass)
    let totalWeight = 0;
    let sumX = 0;
    let sumY = 0;
    
    nodeKeys.forEach(nid => {
      const ndata = selectedDevice.value!.nodes![nid];
      const dist = Math.pow(10, (-59 - ndata.rssi) / 20); // Simpel path loss model
      const weight = 1 / (dist + 0.1); // Undgå division by zero
      
      sumX += result.nodes[nid].x * weight;
      sumY += result.nodes[nid].y * weight;
      totalWeight += weight;
    });
    
    result.target = {
      x: sumX / totalWeight,
      y: sumY / totalWeight
    };
  }
  
  return result;
});

onMounted(() => {
  const wsUrl = `${wsBase()}/api/bluetooth/ws${wsTokenParam()}`
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    connected.value = true
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'init') {
        devices.value = data.devices
      } else if (data.type === 'device_update') {
        const idx = devices.value.findIndex(d => d.mac === data.device.mac)
        if (idx !== -1) {
          devices.value[idx] = data.device
        } else {
          devices.value.push(data.device)
        }
        if (selectedDevice.value && selectedDevice.value.mac === data.device.mac) {
          selectedDevice.value = data.device
        }
      } else if (data.type === 'device_removed') {
        devices.value = devices.value.filter(d => d.mac !== data.mac)
        if (selectedDevice.value && selectedDevice.value.mac === data.mac) {
          selectedDevice.value = null
        }
      }
    } catch (e) {
      console.error("Failed to parse BT WS message", e)
    }
  }
  
  ws.onclose = () => {
    connected.value = false
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.bt-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  color: var(--textwh);
  font-family: var(--font-ui);
}

.bt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
}

.header-title {
  font-family: var(--font-hd);
  font-size: 18px;
  letter-spacing: 2px;
  color: #00e5ff;
  display: flex;
  align-items: center;
  gap: 12px;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pink);
  box-shadow: 0 0 8px var(--pink);
}
.pulse.active {
  background: #00e5ff;
  box-shadow: 0 0 10px #00e5ff;
  animation: pulse-anim 2s infinite alternate;
}
@keyframes pulse-anim {
  from { opacity: 0.5; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1.2); }
}

.header-stats {
  font-family: var(--font-hd);
  font-size: 12px;
  color: var(--text);
  letter-spacing: 1px;
}

.bt-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.aliens-theme {
  --alien-green: #4ade80;
  --alien-dark: #064e3b;
  --alien-bg: #022c22;
  --alien-text: #bbf7d0;
  background: radial-gradient(circle at center, var(--alien-bg) 0%, #000 100%) !important;
}

.radar-container {
  flex: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at center, var(--bg2) 0%, var(--bg) 100%);
  position: relative;
  overflow: hidden;
}

.radar-crt-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(0,0,0,0.15),
    rgba(0,0,0,0.15) 1px,
    transparent 1px,
    transparent 2px
  );
  pointer-events: none;
  z-index: 10;
}

.closest-range {
  position: absolute;
  bottom: 32px;
  left: 32px;
  display: flex;
  flex-direction: column;
  background: rgba(2, 44, 34, 0.8);
  border: 2px solid var(--alien-green);
  padding: 12px 24px;
  border-radius: 4px;
  box-shadow: 0 0 15px rgba(74, 222, 128, 0.2);
  z-index: 5;
}
.range-label {
  color: var(--alien-green);
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 2px;
  opacity: 0.8;
}
.range-val {
  color: #fff;
  font-family: var(--font-co);
  font-size: 32px;
  font-weight: bold;
  text-shadow: 0 0 10px var(--alien-green);
}

.radar {
  width: 500px;
  height: 500px;
  border-radius: 50%;
  position: relative;
  background: rgba(74, 222, 128, 0.05);
  box-shadow: 0 0 40px rgba(74, 222, 128, 0.1), inset 0 0 50px rgba(74, 222, 128, 0.1);
  overflow: hidden;
  border: 2px solid var(--alien-green);
}

.radar::after {
  content: "N";
  position: absolute;
  top: 5px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--alien-green);
  font-family: var(--font-hd);
  font-size: 14px;
  opacity: 0.8;
}

.ring {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px dashed rgba(74, 222, 128, 0.3);
}
.r1 { width: 25%; height: 25%; }
.r2 { width: 50%; height: 50%; }
.r3 { width: 75%; height: 75%; border-style: solid; border-width: 2px; border-color: rgba(74, 222, 128, 0.4); }
.r4 { width: 100%; height: 100%; }

.crosshair-v, .crosshair-h {
  position: absolute;
  background: rgba(74, 222, 128, 0.2);
}
.crosshair-v { top: 0; bottom: 0; left: 50%; width: 1px; transform: translateX(-50%); }
.crosshair-h { left: 0; right: 0; top: 50%; height: 1px; transform: translateY(-50%); }

.sweep {
  position: absolute;
  top: 50%; left: 50%;
  width: 50%; height: 50%;
  transform-origin: 0% 0%;
  background: conic-gradient(from 0deg, transparent 70%, rgba(74, 222, 128, 0.6) 100%);
  animation: sweep 3s linear infinite;
  pointer-events: none;
}

@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.blip {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 15px #fff, 0 0 30px var(--alien-green);
  cursor: pointer;
  transition: all 0.3s;
  z-index: 2;
}
.blip.true-aoa {
  background: #ff3333;
  box-shadow: 0 0 15px #ff3333, 0 0 30px #ff0000;
}
.blip:hover {
  transform: translate(-50%, -50%) scale(1.5);
  background: #fff;
}

.blip-ripple {
  position: absolute;
  top: 50%; left: 50%;
  width: 100%; height: 100%;
  border-radius: 50%;
  border: 2px solid #fff;
  transform: translate(-50%, -50%);
  animation: blip-ping 1.5s ease-out infinite;
}
@keyframes blip-ping {
  0% { width: 100%; height: 100%; opacity: 1; }
  100% { width: 400%; height: 400%; opacity: 0; }
}

.blip-label {
  position: absolute;
  top: 16px; left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  font-family: var(--font-co);
  font-weight: bold;
  white-space: nowrap;
  color: var(--alien-text);
  pointer-events: none;
  background: rgba(2, 44, 34, 0.8);
  padding: 2px 6px;
  border: 1px solid rgba(74, 222, 128, 0.4);
  border-radius: 2px;
}

.device-list {
  flex: 1;
  min-width: 300px;
  max-width: 400px;
  border-left: 1px solid var(--border);
  background: var(--bg2);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.device-list h3, .device-details h3 {
  padding: 16px;
  margin: 0;
  font-family: var(--font-hd);
  font-size: 13px;
  letter-spacing: 2px;
  color: var(--cyan);
  border-bottom: 1px solid var(--border);
  background: rgba(0,0,0,0.2);
}

.empty-list {
  padding: 24px;
  text-align: center;
  color: var(--text);
  font-size: 12px;
  letter-spacing: 1px;
}

.device-card {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.2s;
}
.device-card:hover {
  background: rgba(0, 229, 255, 0.05);
}
.device-card.selected {
  background: rgba(0, 229, 255, 0.1);
  border-left: 3px solid var(--cyan);
}

.card-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.dev-name {
  font-weight: 600;
  font-size: 13px;
}
.dev-rssi {
  font-family: var(--font-co);
  font-size: 11px;
}

.card-body {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text);
  font-family: var(--font-co);
}

.device-details {
  flex: 1;
  min-width: 300px;
  max-width: 350px;
  border-left: 1px solid var(--border);
  background: var(--bg);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.detail-row .lbl {
  color: var(--text);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 1px;
}
.detail-row .val {
  font-family: var(--font-co);
}

.detail-row .val-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-family: var(--font-co);
  text-align: right;
  font-size: 11px;
}
.gatt-box {
  text-align: left !important;
  margin-top: 8px;
  background: rgba(0,0,0,0.2);
  padding: 8px;
  border-radius: 4px;
  width: 100%;
}
.gatt-service {
  margin-bottom: 8px;
}
.gatt-service:last-child {
  margin-bottom: 0;
}
.gatt-title {
  color: var(--pink);
  font-size: 10px;
  margin-bottom: 4px;
  border-bottom: 1px solid rgba(255,51,102,0.2);
  padding-bottom: 2px;
}
.gatt-char {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2px;
}
.gatt-char .cname { color: var(--text); }
.gatt-char .cval { color: var(--cyan); text-align: right; word-break: break-all; max-width: 60%; }

.actions {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.btn-action {
  padding: 12px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--cyan);
  font-family: var(--font-hd);
  font-size: 11px;
  letter-spacing: 1px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-action:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.1);
}
.btn-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  color: var(--text);
}

.btn-danger {
  color: #ff3333 !important;
  border-color: rgba(255, 51, 51, 0.4) !important;
  cursor: pointer !important;
  opacity: 1 !important;
}
.btn-danger:hover {
  background: rgba(255, 51, 51, 0.1) !important;
}
.jamming-active {
  animation: bg-pulse-red 1s infinite alternate;
  color: #fff !important;
}

@keyframes bg-pulse-red {
  from { background: rgba(255, 51, 51, 0.2); }
  to { background: rgba(255, 51, 51, 0.6); }
}

.jamming-target .blip-ripple {
  border-color: #ff0000;
  animation-duration: 0.5s; /* Faster ripples */
}

.jamming-lightning {
  position: absolute;
  top: -20px; left: -20px; right: -20px; bottom: -20px;
  background: radial-gradient(circle, transparent 20%, rgba(255,0,0,0.5) 80%);
  border-radius: 50%;
  animation: spin-zap 0.5s infinite linear;
  pointer-events: none;
}

@keyframes spin-zap {
  0% { transform: rotate(0deg) scale(1); opacity: 0.8; }
  50% { transform: rotate(180deg) scale(1.2); opacity: 1; }
  100% { transform: rotate(360deg) scale(1); opacity: 0.8; }
}

.signal-strong { color: var(--green); }
.signal-med { color: var(--yellow); }
.signal-weak { color: var(--pink); }

.node-blip {
  background: var(--cyan);
  box-shadow: 0 0 10px var(--cyan);
  z-index: 100;
}
.node-label {
  position: absolute;
  top: -20px;
  left: -20px;
  width: 60px;
  text-align: center;
  color: var(--cyan);
  font-size: 10px;
  font-family: monospace;
  text-shadow: 0 0 5px rgba(0,0,0,0.8);
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}
.modal-box {
  background: var(--bg-card);
  border: 1px solid var(--cyan);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
  padding: 24px;
  width: 400px;
  max-width: 90vw;
  border-radius: 4px;
}
.modal-box h3 {
  margin-top: 0;
  color: var(--cyan);
  border-bottom: 1px solid rgba(0,229,255,0.3);
  padding-bottom: 8px;
}
.pairing-status {
  margin-top: 16px;
  padding: 12px;
  background: rgba(0,0,0,0.5);
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
}

</style>
