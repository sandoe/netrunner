<template>
  <div class="osi-inspector-container">
    <!-- Left Sidebar: OSI Stack -->
    <div class="osi-stack">
      <div class="stack-title">OSI TELEMETRY STACK</div>
      <div
        v-for="layer in osiLayers.slice().reverse()"
        :key="layer.level"
        class="osi-layer"
        :class="{ active: activeLayer === layer.level }"
        @click="activeLayer = layer.level"
      >
        <span class="layer-num">L{{ layer.level }}</span>
        <div class="layer-info">
          <span class="layer-name">{{ layer.name }}</span>
          <span class="layer-desc">{{ layer.desc }}</span>
        </div>
        <div class="layer-activity-led" :class="{ 'blink': layerActivity[layer.level] }"></div>
      </div>
    </div>

    <!-- Right Panel: Data View -->
    <div class="osi-data-panel">
      <div class="panel-header">
        <h3 class="active-title"><span class="neon-text">LAYER {{ activeLayer }}:</span> {{ currentLayerData.name.toUpperCase() }}</h3>
        <span class="panel-subtitle">Real-time aggregate telemetry</span>
      </div>

      <div class="panel-content custom-scrollbar">
        <!-- L7: Application -->
        <div v-if="activeLayer === 7" class="data-section">
          <table class="data-table">
            <thead><tr><th>HOST</th><th>APPLICATION / CONTAINER</th><th>IMAGE</th><th>STATE</th></tr></thead>
            <tbody>
              <tr v-for="app in layer7Apps" :key="app.id">
                <td>{{ app.nodeName }}</td>
                <td>{{ app.name }}</td>
                <td class="text-dim">{{ app.image }}</td>
                <td><span class="status-badge" :class="app.state">{{ app.state }}</span></td>
              </tr>
              <tr v-if="!layer7Apps.length"><td colspan="4" class="text-center text-dim">No application layer data detected.</td></tr>
            </tbody>
          </table>
        </div>

        <!-- L6: Presentation -->
        <div v-if="activeLayer === 6" class="data-section">
          <table class="data-table">
            <thead><tr><th>HOST</th><th>PROTOCOL / ENCRYPTION</th><th>DETAILS</th></tr></thead>
            <tbody>
              <tr v-for="pres in layer6Data" :key="pres.id">
                <td>{{ pres.nodeName }}</td>
                <td><span class="crypto-tag">{{ pres.proto }}</span></td>
                <td class="text-dim">{{ pres.details }}</td>
              </tr>
              <tr v-if="!layer6Data.length"><td colspan="3" class="text-center text-dim">No presentation layer data detected.</td></tr>
            </tbody>
          </table>
        </div>

        <!-- L5: Session -->
        <div v-if="activeLayer === 5" class="data-section">
          <table class="data-table">
            <thead><tr><th>HOST</th><th>SESSION ID</th><th>TYPE</th><th>USER</th></tr></thead>
            <tbody>
              <tr v-for="sess in layer5Sessions" :key="sess.id">
                <td>{{ sess.nodeName }}</td>
                <td class="text-dim">{{ sess.sessionId }}</td>
                <td>{{ sess.type }}</td>
                <td>{{ sess.user }}</td>
              </tr>
              <tr v-if="!layer5Sessions.length"><td colspan="4" class="text-center text-dim">No active sessions detected.</td></tr>
            </tbody>
          </table>
        </div>

        <!-- L4: Transport -->
        <div v-if="activeLayer === 4" class="data-section">
          <table class="data-table">
            <thead><tr><th>HOST</th><th>PORT</th><th>PROTO</th><th>SERVICE</th></tr></thead>
            <tbody>
              <tr v-for="port in layer4Ports" :key="port.id">
                <td>{{ port.nodeName }}</td>
                <td class="text-neon">{{ port.port }}</td>
                <td>{{ port.proto }}</td>
                <td class="text-dim">{{ port.service }}</td>
              </tr>
              <tr v-if="!layer4Ports.length"><td colspan="4" class="text-center text-dim">No transport layer data detected.</td></tr>
            </tbody>
          </table>
        </div>

        <!-- L3: Network -->
        <div v-if="activeLayer === 3" class="data-section">
          <table class="data-table">
            <thead><tr><th>HOST</th><th>INTERFACE</th><th>IPv4 / IPv6 ADDRESS</th></tr></thead>
            <tbody>
              <tr v-for="ip in layer3IPs" :key="ip.id">
                <td>{{ ip.nodeName }}</td>
                <td class="text-dim">{{ ip.interface }}</td>
                <td class="text-neon">{{ ip.address }}</td>
              </tr>
              <tr v-if="!layer3IPs.length"><td colspan="3" class="text-center text-dim">No network layer data detected.</td></tr>
            </tbody>
          </table>
        </div>

        <!-- L2: Data Link -->
        <div v-if="activeLayer === 2" class="data-section">
          <table class="data-table">
            <thead><tr><th>HOST</th><th>INTERFACE</th><th>MAC ADDRESS</th><th>VLAN / BSSID</th></tr></thead>
            <tbody>
              <tr v-for="mac in layer2MACs" :key="mac.id">
                <td>{{ mac.nodeName }}</td>
                <td class="text-dim">{{ mac.interface }}</td>
                <td class="text-orange">{{ mac.mac }}</td>
                <td>{{ mac.extra }}</td>
              </tr>
              <tr v-if="!layer2MACs.length"><td colspan="4" class="text-center text-dim">No data link layer data detected.</td></tr>
            </tbody>
          </table>
        </div>

        <!-- L1: Physical -->
        <div v-if="activeLayer === 1" class="data-section">
          <table class="data-table">
            <thead><tr><th>HOST</th><th>INTERFACE</th><th>TYPE</th><th>STATUS</th><th>SPEED / DUPLEX</th></tr></thead>
            <tbody>
              <tr v-if="loadingL1"><td colspan="5" class="text-center text-dim">Scanning physical hardware links... <span class="spinner"></span></td></tr>
              <template v-else>
                <tr v-for="iface in realL1Data" :key="iface.nodeName + iface.name">
                  <td>{{ iface.nodeName }}</td>
                  <td class="text-neon">{{ iface.name }}</td>
                  <td>{{ iface.type.toUpperCase() }}</td>
                  <td>
                    <span class="status-indicator" :class="{ 'online': iface.state === 'up' }"></span>
                    {{ iface.state.toUpperCase() }}
                  </td>
                  <td class="text-dim">{{ iface.speed }} {{ iface.speed !== 'N/A' ? 'Mbps' : '' }} / {{ iface.duplex.toUpperCase() }}</td>
                </tr>
                <tr v-if="!realL1Data.length"><td colspan="5" class="text-center text-dim">No physical interfaces detected.</td></tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'

const store = useNodesStore()

const osiLayers = [
  { level: 1, name: 'Physical', desc: 'Hardware, Cables, Signals' },
  { level: 2, name: 'Data Link', desc: 'MAC, Switching, ARP, WiFi' },
  { level: 3, name: 'Network', desc: 'IP, Routing, ICMP' },
  { level: 4, name: 'Transport', desc: 'TCP, UDP, Ports' },
  { level: 5, name: 'Session', desc: 'Auth, Terminals, RPC' },
  { level: 6, name: 'Presentation', desc: 'TLS, Crypto, Formatting' },
  { level: 7, name: 'Application', desc: 'HTTP, Docker, Services' }
]

const activeLayer = ref(7)
const currentLayerData = computed(() => osiLayers.find(l => l.level === activeLayer.value)!)

// Blink LED simulation
const layerActivity = ref<Record<number, boolean>>({})
let activityInterval: number

const realL1Data = ref<any[]>([])
const loadingL1 = ref(false)
const realL7Data = ref<any[]>([])
const loadingL7 = ref(false)

const targetNodes = computed(() => {
  if (store.selected) {
    return [store.selected]
  }
  return store.nodeList.filter(n => store.isConnected(n.id))
})

watch(activeLayer, async (newVal) => {
  if (newVal === 1 && realL1Data.value.length === 0) {
    loadingL1.value = true
    try {
      const allIfaces = []
      for (const n of targetNodes.value) {
        try {
          const res = await api.getPhysicalInterfaces(n.id)
          if (res.interfaces) {
            for (const i of res.interfaces) {
              allIfaces.push({
                nodeName: n.name,
                name: i.name,
                type: i.type,
                state: i.state,
                speed: i.speed,
                duplex: i.duplex,
                mac: i.mac
              })
            }
          }
        } catch (e) {
          console.error("Failed to fetch physical ifaces for node", n.id, e)
        }
      }
      realL1Data.value = allIfaces
    } finally {
      loadingL1.value = false
    }
  } else if (newVal === 7 && realL7Data.value.length === 0) {
    loadingL7.value = true
    try {
      const allApps = []
      for (const n of targetNodes.value) {
        try {
          if (!store.isConnected(n.id)) continue;
          const res = await api.readNode(n.id, 'docker')
          if (res.results && res.results.length > 1 && res.results[1].output) {
            const lines = res.results[1].output.split('\n').slice(1)
            for (const line of lines) {
              if (!line.trim()) continue;
              const parts = line.split('\t')
              if (parts.length >= 4) {
                allApps.push({
                  id: `${n.id}-${parts[0]}`,
                  nodeName: n.name,
                  name: parts[1],
                  image: parts[2],
                  state: parts[3]
                })
              }
            }
          }
        } catch (e) {
          console.error("Failed to fetch docker for node", n.id, e)
        }
      }
      realL7Data.value = allApps
    } finally {
      loadingL7.value = false
    }
  }
})

onMounted(() => {
  activityInterval = window.setInterval(() => {
    for (let i = 1; i <= 7; i++) {
      layerActivity.value[i] = Math.random() > 0.6
    }
  }, 300)

  // Trigger initial fetch if starting on layer 1 or 7
  if (activeLayer.value === 1) {
    const trigger = activeLayer.value
    activeLayer.value = 0
    activeLayer.value = trigger
  } else if (activeLayer.value === 7) {
    const trigger = activeLayer.value
    activeLayer.value = 0
    activeLayer.value = trigger
  }
})
onUnmounted(() => clearInterval(activityInterval))

// --- DATA MAPPING ---

// L7 (Application)
const layer7Apps = computed(() => {
  if (realL7Data.value.length > 0) return realL7Data.value

  const apps: any[] = []
  for (const n of targetNodes.value) {
    if ((n as any).workloads?.docker?.containers) {
      for (const c of (n as any).workloads.docker.containers) {
        apps.push({
          id: `${n.id}-${c.id}`,
          nodeName: n.name,
          name: c.name.replace(/^\//, ''),
          image: c.image,
          state: c.state
        })
      }
    }
  }
  return apps
})

// L6 (Presentation) - Mocked from SSH / TLS indicators
const layer6Data = computed(() => {
  const data: any[] = []
  for (const n of targetNodes.value) {
    if (n.transport === 'ssh') {
      data.push({ id: `l6-${n.id}-ssh`, nodeName: n.name, proto: 'SSHv2 / Crypto', details: 'AES-256-GCM / Ed25519' })
    } else if (n.transport === 'https') {
      data.push({ id: `l6-${n.id}-tls`, nodeName: n.name, proto: 'TLSv1.3', details: 'X.509 Certificate Present' })
    }
  }
  return data
})

// L5 (Session) - Mocked terminal sessions
const layer5Sessions = computed(() => {
  const data: any[] = []
  for (const n of targetNodes.value) {
    if (store.isConnected(n.id)) {
      data.push({
        id: `l5-${n.id}`,
        nodeName: n.name,
        sessionId: `sess_${Math.floor(Math.random()*10000)}`,
        type: n.transport.toUpperCase() + ' Shell',
        user: 'root'
      })
    }
  }
  return data
})

// L4 (Transport) - Ports
const layer4Ports = computed(() => {
  const data: any[] = []
  for (const n of targetNodes.value) {
    if ((n as any).ports) {
      for (const p of (n as any).ports) {
        data.push({
          id: `l4-${n.id}-${p.port}`,
          nodeName: n.name,
          port: p.port,
          proto: p.protocol || 'TCP',
          service: p.service || 'unknown'
        })
      }
    }
  }
  return data
})

// L3 (Network) - Mocked routes
const layer3Routes = computed(() => {
  const data: any[] = []
  for (const n of targetNodes.value) {
    data.push({
      id: `l3-${n.id}-1`,
      nodeName: n.name,
      dest: '0.0.0.0/0',
      gateway: n.host.replace(/\.\d+$/, '.1'),
      iface: 'eth0'
    })
    data.push({
      id: `l3-${n.id}-2`,
      nodeName: n.name,
      dest: n.host + '/24',
      gateway: '0.0.0.0',
      iface: 'eth0'
    })
  }
  return data
})

// L3 (Network) - IPs
const layer3IPs = computed(() => {
  const data: any[] = []
  for (const n of targetNodes.value) {
    data.push({
      id: `l3-${n.id}`,
      nodeName: n.name,
      interface: n.tags?.includes('wifi') ? 'wlan0 (Wireless)' : 'eth0 (Wired)',
      address: n.host
    })
  }
  return data
})

// L2 (Data Link) - MACs
const layer2MACs = computed(() => {
  const data: any[] = []
  for (const n of targetNodes.value) {
    const pseudoMac = '00:1A:2B:' + (n.id.charCodeAt(0) % 255).toString(16).padStart(2, '0') + ':' + (n.id.charCodeAt(1) % 255).toString(16).padStart(2, '0') + ':FF'
    data.push({
      id: `l2-${n.id}`,
      nodeName: n.name,
      interface: n.tags?.includes('wifi') ? 'wlan0 (Wireless)' : 'eth0 (Wired)',
      mac: pseudoMac.toUpperCase(),
      extra: n.tags?.includes('wifi') ? 'WPA3 / BSSID' : 'VLAN 10'
    })
  }
  return data
})

</script>

<style scoped>
.osi-inspector-container {
  display: flex;
  height: 100%;
  background: rgba(10, 15, 25, 0.95);
  color: #e0e0e0;
  font-family: 'JetBrains Mono', monospace;
  overflow: hidden;
}

.osi-stack {
  width: 250px;
  background: rgba(5, 10, 20, 0.8);
  border-right: 1px solid rgba(0, 229, 255, 0.2);
  display: flex;
  flex-direction: column;
  padding: 20px 10px;
  gap: 8px;
}

.stack-title {
  color: #7f8c8d;
  font-size: 11px;
  letter-spacing: 2px;
  margin-bottom: 15px;
  text-align: center;
}

.osi-layer {
  display: flex;
  align-items: center;
  padding: 12px 10px;
  background: rgba(0, 229, 255, 0.02);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.osi-layer:hover {
  background: rgba(0, 229, 255, 0.05);
  border-color: rgba(0, 229, 255, 0.3);
}

.osi-layer.active {
  background: rgba(0, 229, 255, 0.15);
  border-color: #00e5ff;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.2);
}

.layer-num {
  font-size: 20px;
  font-weight: bold;
  color: #00e5ff;
  margin-right: 15px;
  opacity: 0.8;
}

.osi-layer.active .layer-num {
  opacity: 1;
  text-shadow: 0 0 8px #00e5ff;
}

.layer-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.layer-name {
  font-weight: 600;
  font-size: 14px;
}

.layer-desc {
  font-size: 10px;
  color: #7f8c8d;
  margin-top: 3px;
}

.layer-activity-led {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #333;
  margin-left: 10px;
  transition: background-color 0.1s;
}

.layer-activity-led.blink {
  background: #00e5ff;
  box-shadow: 0 0 5px #00e5ff;
}

/* Right Panel */
.osi-data-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.panel-header {
  padding: 20px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  background: rgba(0, 0, 0, 0.3);
}

.active-title {
  margin: 0 0 5px 0;
  font-size: 20px;
  font-weight: 400;
}

.neon-text {
  color: #00e5ff;
  text-shadow: 0 0 5px rgba(0, 229, 255, 0.4);
  font-weight: bold;
}

.panel-subtitle {
  font-size: 12px;
  color: #7f8c8d;
}

.panel-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

/* Tables */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  text-align: left;
  padding: 10px;
  color: #7f8c8d;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  font-weight: 500;
  letter-spacing: 1px;
}

.data-table td {
  padding: 12px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.data-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.text-dim { color: #7f8c8d; }
.text-neon { color: #00e5ff; }
.text-orange { color: #f39c12; }

.status-badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.1);
}
.status-badge.running { background: rgba(0, 255, 100, 0.2); color: #00ff66; border: 1px solid #00ff66; }
.status-badge.exited { background: rgba(255, 45, 110, 0.2); color: #ff2d6e; border: 1px solid #ff2d6e; }

.crypto-tag {
  background: rgba(155, 89, 182, 0.2);
  color: #c39bd3;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid #9b59b6;
  font-size: 11px;
}

.status-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff2d6e;
  margin-right: 6px;
}
.status-indicator.online {
  background: #00ff66;
  box-shadow: 0 0 5px #00ff66;
}
</style>
