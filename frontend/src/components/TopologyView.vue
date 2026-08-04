<template>
  <div class="topology-container" :class="{ 'simulation-branch': environmentMode === 'simulation' }" style="position: relative; width: 100%; height: 100%;">
    <!-- Background Globe Layer -->
    <div ref="globeCanvasRef" style="position: absolute; inset: 0; z-index: 0; pointer-events: none;"></div>

    <!-- Foreground Network Layer -->
    <div ref="canvasRef" class="cy-canvas" style="position: absolute; inset: 0; z-index: 10;"></div>

    <div class="topology-toolbar">
      <div class="toolbar-group">
        <button class="btn-tool" :class="{ active: mode === 'select' }" @click="mode = 'select'">
          <span class="icon" aria-hidden="true">🖱️</span> SELECT
        </button>
        <button class="btn-tool" :class="{ active: mode === 'draw' }" @click="mode = 'draw'">
          <span class="icon" aria-hidden="true">🔌</span> DRAW LINK
        </button>
      </div>
      <div class="toolbar-group">
        <button class="btn-tool" @click="fit">CENTER</button>
        <button class="btn-tool" @click="toggleLayout">
          <span class="icon" aria-hidden="true">🕸️</span> {{ layoutMode === 'floating' ? 'FLOATING' : 'UNIFI' }}
        </button>
        <button class="btn-tool btn-discover" @click="doAutoDiscover" :disabled="discovering">
          <span class="icon" aria-hidden="true"><span v-if="discovering" class="spinner"></span><template v-else>📡</template></span> AUTO-DISCOVER
        </button>
        <button class="btn-tool btn-gns3" @click="pickGns3Project" :disabled="syncing">
          <span class="icon" aria-hidden="true"><span v-if="syncing" class="spinner"></span><template v-else>☁️</template></span> GNS3 SYNC
        </button>
        <button class="btn-tool" :class="{ active: showReachPanel }" @click="showReachPanel = !showReachPanel">
          <span class="icon" aria-hidden="true">📶</span> REACHABILITY
        </button>
      </div>
      <div class="toolbar-group">
        <label class="btn-tool layer-toggle" :class="{ active: environmentMode === 'simulation' }">
          <input type="checkbox" :checked="environmentMode === 'simulation'" @change="toggleEnvironment" class="sr-only" />
          <span class="icon" aria-hidden="true">🔮</span> {{ environmentMode === 'simulation' ? 'SIMULATION BRANCH' : 'LIVE TRUNK' }}
        </label>
        <label class="btn-tool layer-toggle" :class="{ active: attackerView }">
          <input type="checkbox" v-model="attackerView" class="sr-only" @change="updateGraph" />
          <span class="icon" aria-hidden="true">🩸</span> ATTACKER VIEW
        </label>
        <label class="btn-tool layer-toggle" :class="{ active: showThreats }">
          <input type="checkbox" v-model="showThreats" class="sr-only" />
          <span class="icon" aria-hidden="true">🔴</span> THREATS
        </label>
        <label class="btn-tool layer-toggle" :class="{ active: showAgents }">
          <input type="checkbox" v-model="showAgents" class="sr-only" />
          <span class="icon" aria-hidden="true">🤖</span> AGENTS
        </label>
        <label class="btn-tool layer-toggle" :class="{ active: deceptionMode }">
          <input type="checkbox" v-model="deceptionMode" class="sr-only" @change="updateVisualState" />
          <span class="icon" aria-hidden="true">🎭</span> DECEPTION MODE
        </label>
        <button v-if="deceptionMode" class="btn-tool btn-gns3" @click="launchGhostRunner" :disabled="ghostRunning">
          <span class="icon" aria-hidden="true">👻</span> LAUNCH GHOST RUNNER
        </button>
        <label class="btn-tool layer-toggle" :class="{ active: enableBloom }">
          <input type="checkbox" v-model="enableBloom" class="sr-only" @change="toggleBloom" />
          <span class="icon" aria-hidden="true">✨</span> BLOOM
        </label>
      </div>
      <div class="toolbar-info" v-if="mode === 'draw'">
        CLICK SOURCE NODE, THEN TARGET NODE TO LINK.
      </div>
      <div v-if="debugStats" class="debug-stats">
        DEBUG: {{ debugStats.nodes }} Nodes | {{ debugStats.links }} Links | Ghosts: {{ ghostNodes.length }}
      </div>
      <div v-else class="debug-stats offline">
        DEBUG: AWAITING ENGINE INGESTION...
      </div>
    </div>

    <!-- Critical-event shockwave -->
    <div v-if="shockwave" class="shockwave"></div>

    <!-- Reachability overview -->
    <div v-if="showReachPanel" class="reach-panel">
      <div class="reach-head">
        <span>📶 REACHABILITY</span>
        <button class="reach-close" aria-label="Close reachability panel" @click="showReachPanel = false">×</button>
      </div>
      <div v-for="row in reachRows" :key="row.id" class="reach-row" :class="{ active: store.selectedId === row.id }" role="button" tabindex="0" @click="store.select(row.id)" @keydown.enter="store.select(row.id)" @keydown.space.prevent="store.select(row.id)">
        <span class="reach-dot" :style="{ background: row.color }"></span>
        <span class="reach-name">{{ row.name }}</span>
        <span class="reach-lat">{{ row.label }}</span>
      </div>
      <div v-if="reachRows.length === 0" class="reach-empty">No nodes.</div>
    </div>

    <!-- Right-click node context menu -->
    <template v-if="ctxMenu.show">
      <div class="ctx-backdrop" @click="closeCtx" @contextmenu.prevent="closeCtx"></div>
      <div class="ctx-menu" :style="{ left: ctxMenu.x + 'px', top: ctxMenu.y + 'px' }">
        <div class="ctx-title">{{ ctxMenu.name }}</div>
        <template v-if="ctxMenu.type === 'node'">
          <button class="ctx-item" @click="ctxEdit">✎ Reconfigure (IP, telnet/SSH…)</button>
          <template v-if="!isConsoleless(ctxMenu.targetId)">
            <button v-if="!store.isConnected(ctxMenu.targetId)" class="ctx-item ok" @click="ctxConnect">▶ Connect</button>
            <button v-else class="ctx-item warn" @click="ctxDisconnect">■ Disconnect</button>
          </template>
          <div v-else class="ctx-note">⚡ L2 device — no console</div>
          <button class="ctx-item" style="color: var(--pink); border-color: var(--pink);" @click="ctxBruteForce">💥 Launch Brute Force</button>
          <button class="ctx-item" @click="ctxTogglePin">
            {{ pinnedId === ctxMenu.targetId ? '📌 Unpin from centre' : '📌 Pin to centre' }}
          </button>
        </template>
        <template v-if="ctxMenu.type === 'link'">
          <button v-if="environmentMode === 'simulation'" class="ctx-item warn" @click="ctxSeverLink">
            ✂️ Sever Link (Simulate Block)
          </button>
          <div v-else class="ctx-note">Switch to Simulation Branch to test firewall rules.</div>
        </template>
        <button class="ctx-item" @click="ctxStartPacketCapture">📡 Start Packet Capture</button>
      </div>
    </template>

    <!-- Sub Modal for Brute Force Attack -->
    <dialog ref="attackDialog" v-if="attackTarget" class="modal-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); z-index: 9999; border: none; width: 100%; height: 100%;" @click.self="attackTarget = null; $refs.attackDialog.close()">
      <div class="cyber-modal-card" style="width: 100%; max-width: 400px; background: rgba(10,12,18,0.95); border: 1px solid var(--pink);">
        <div class="cyber-modal-header">
          <div class="modal-title" style="color: var(--pink)">💥 LAUNCH BRUTE FORCE</div>
          <button class="btn-close-modal" aria-label="Close modal" @click="attackTarget = null; $refs.attackDialog.close()">×</button>
        </div>
        <div class="cyber-modal-body" style="text-align: center">
          <p style="color: #a0a0a0; margin-bottom: 20px;">TARGET NODE: <strong style="color: var(--cyan)">{{ attackTarget }}</strong></p>
          <div style="display: flex; gap: 10px; justify-content: center">
            <button class="btn-action btn-danger" @click="launchAttack('ssh')">[ CRACK SSH ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('ftp')">[ CRACK FTP ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('mysql')">[ CRACK MYSQL ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('postgres')">[ CRACK POSTGRES ]</button>
          </div>
          <div v-if="attackStatus" style="margin-top: 15px; font-family: monospace; font-weight: bold;" :style="{ color: attackStatus.includes('ERROR') ? 'var(--pink)' : 'var(--green)', textShadow: attackStatus.includes('ERROR') ? '0 0 8px var(--pink)' : '0 0 8px var(--green)' }" aria-live="assertive">{{ attackStatus }}</div>
        </div>
      </div>
    </dialog>

    <!-- Floating Packet Captures Widget -->
    <div v-if="activeCaptures.length > 0" class="packet-captures-widget">
      <div class="pc-head">📡 PACKET CAPTURES</div>
      <div v-for="cap in activeCaptures" :key="cap.capture_id" class="pc-item">
        <div class="pc-info">
          <div><strong class="pc-target">{{ cap.interface }}</strong></div>
          <div class="pc-details">{{ cap.status }} · {{ Math.round(cap.file_size_bytes / 1024) }} KB</div>
        </div>
        <button v-if="cap.status === 'running'" class="btn-stop-capture" @click="stopCapture(cap.capture_id)">■ Stop</button>
      </div>
    </div>

    <div v-if="initError" class="init-error">
      <h3>🚨 CORE DISRUPTION DETECTED</h3>
      <p>{{ initError }}</p>
      <button class="btn-tool" @click="retryInit">REBOOT NEURAL LINK</button>
    </div>

    <!-- AI Narrative Incident Card (Ghost Runner Mode) -->
    <div v-if="deceptionMode && store.selectedId && infectedNodes.has(store.selectedId)" class="ai-incident-card">
      <div class="ai-header">
        <span class="icon">🤖</span> AI INCIDENT NARRATIVE
      </div>
      <div class="ai-body">
        <h4 style="margin: 0 0 10px 0; color: var(--pink)">CRITICAL BREACH DETECTED</h4>
        <p style="color: #ccc; margin: 0 0 15px 0; font-size: 14px; line-height: 1.4;">
          <strong>Ghost Runner</strong> has successfully breached <span style="color: var(--cyan)">{{ store.selected?.name || store.selectedId }}</span>.
          The attacker utilized an advanced lateral movement technique to bypass local segmentation. Immediate containment is highly recommended to halt the spread of the Blast Radius.
        </p>
        <div class="ai-actions">
          <button v-if="!store.isolatedNodes.has(store.selectedId)" class="btn-action btn-danger" @click="isolateHost(store.selectedId)" style="width: 100%;">
            [ AGENTIC PLAYBOOK: ISOLATE HOST ]
          </button>
          <button v-else class="btn-action btn-warning" @click="rollbackHost(store.selectedId)" style="width: 100%;">
            [ ROLLBACK CONTAINMENT ]
          </button>
        </div>
      </div>
    </div>

    <!-- XAI Event Feed (Ghost Runner Mode) -->
    <div v-if="deceptionMode && currentEvents.length > 0" class="xai-event-feed">
      <div class="xai-header">
        <span class="icon">🧠</span> XAI EVENT FEED
      </div>
      <div class="xai-body">
        <div v-for="(evt, idx) in currentEvents" :key="idx" class="xai-event">
          <span class="xai-time">{{ evt.time }}</span>
          <span class="xai-text">{{ evt.text }}</span>
        </div>
      </div>
    </div>

    <!-- Chronos DVR Scrubber (Ghost Runner Mode) -->
    <div v-if="deceptionMode && attackHistory.length > 0" class="chronos-scrubber">
      <div class="scrubber-label">
        CHRONOS DVR: <span class="time-display">{{ attackHistory[currentTimeIndex]?.timestamp }}</span>
      </div>
      <input
        type="range"
        min="0"
        :max="attackHistory.length - 1"
        v-model.number="currentTimeIndex"
        class="scrubber-input"
        :style="{ background: heatmapBackground }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, computed, nextTick, shallowRef } from 'vue'
import ForceGraph3D from '3d-force-graph'
import Globe from 'globe.gl'
import * as THREE from 'three'
import SpriteText from 'three-spritetext'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { useNodesStore } from '@/stores/nodes'
import { api, wsTokenParam, wsBase } from '@/api/client'

// Nexus Engine Worker state
let nexusHeader: Int32Array | null = null
let nexusData0: Float32Array | null = null
let nexusData1: Float32Array | null = null
let nexusNodeMap = new Map<string, number>()
let telemetryWorker: Worker | null = null

const store = useNodesStore()
const emit = defineEmits<{ editNode: [string] }>()
const canvasRef = ref<HTMLElement | null>(null)
const globeCanvasRef = ref<HTMLElement | null>(null)
const selectedNodeData = computed(() => store.selected)

// Red shockwave when a critical event hits (e.g. the demo storm)
const shockwave = ref(false)
let shockTimer: any = null
function triggerShockwave() {
  shockwave.value = false
  requestAnimationFrame(() => { shockwave.value = true })
  if (shockTimer) clearTimeout(shockTimer)
  shockTimer = setTimeout(() => { shockwave.value = false }, 1600)
}

// Reachability overview panel
const showReachPanel = ref(false)
const reachRows = computed(() => {
  return store.nodeList.map((n: any) => {
    if (isConsoleless(n.id)) {
      return { id: n.id, name: n.name, color: '#ffbe0b', label: 'L2 fabric' }
    }
    const r = nodeReach.value[n.id]
    if (!r) return { id: n.id, name: n.name, color: '#555', label: '—' }
    return {
      id: n.id, name: n.name,
      color: r.reachable ? '#00ff9d' : '#ff2d6e',
      label: r.reachable ? `${r.latency_ms} ms` : 'offline',
    }
  }).sort((a, b) => a.name.localeCompare(b.name))
})

// Right-click context menu on nodes
const ctxMenu = ref<{ show: boolean, x: number, y: number, targetId: string, name: string, type: 'node' | 'link' }>(
  { show: false, x: 0, y: 0, targetId: '', name: '', type: 'node' })
// GNS3 node types that have no usable interactive console (L2 fabric etc.)
const CONSOLELESS = new Set(['ethernet_switch', 'ethernet_hub', 'frame_relay_switch', 'atm_switch', 'cloud', 'nat'])
function isConsoleless(id: string): boolean {
  const nt = (store.nodes[id] as any)?.metadata?.gns3?.node_type
  return !!nt && CONSOLELESS.has(nt)
}
// A node counts as "up" for link-traffic purposes if it has a live session,
// or it's L2 fabric (a switch/hub is always up — you don't log into it).
function nodeUp(id: string): boolean {
  return store.isConnected(id) || isConsoleless(id)
}
// Reachability health of a link from the active TCP probes ('up' | 'down' | 'unknown')
function endId(e: any): string { return typeof e === 'object' ? e?.id : e }
function linkHealth(link: any): 'up' | 'down' | 'unknown' {
  const ends = [endId(link.source), endId(link.target)]
  let known = 0, up = 0
  for (const id of ends) {
    if (isConsoleless(id)) { known++; up++; continue }
    const r = nodeReach.value[id]
    if (r) { known++; if (r.reachable) up++ }
  }
  if (known === 0) return 'unknown'
  if (up < known) return 'down'
  return known === 2 ? 'up' : 'unknown'
}
function closeCtx() { ctxMenu.value.show = false }
function ctxEdit() { store.select(ctxMenu.value.targetId); emit('editNode', ctxMenu.value.targetId); closeCtx() }

const activeCaptures = ref<any[]>([])
let captureInterval: any = null

async function fetchCaptures() {
  try {
    const res = await fetch('/api/packet_capture/list', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    if (res.ok) {
      const list = await res.json()
      const fullList = await Promise.all(list.map(async (cap: any) => {
        const sRes = await fetch(`/api/packet_capture/status/${cap.capture_id}`, {
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
        })
        return sRes.ok ? await sRes.json() : cap
      }))
      activeCaptures.value = fullList
    }
  } catch (e) {
    console.error('Failed to fetch captures:', e)
  }
}

async function ctxStartPacketCapture() {
  const targetId = ctxMenu.value.targetId
  closeCtx()
  try {
    const res = await fetch('/api/packet_capture/start', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('nr_token'),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ interface: targetId })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Start capture failed')
    fetchCaptures()
  } catch (err: any) {
    alert('Start capture failed: ' + err.message)
  }
}

async function stopCapture(id: string) {
  try {
    const res = await fetch(`/api/packet_capture/stop/${id}`, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('nr_token') }
    })
    if (res.ok) {
      fetchCaptures()
    } else {
      const data = await res.json()
      alert('Stop capture failed: ' + data.detail)
    }
  } catch (err: any) {
    alert('Stop capture failed: ' + err.message)
  }
}

const attackTarget = ref<string | null>(null)
const attackStatus = ref('')

function ctxBruteForce() {
  attackTarget.value = ctxMenu.value.name
  attackStatus.value = ''
  closeCtx()
  nextTick(() => {
    // Focus or showModal logic if necessary, handled by Vue reactivity on <dialog>
    const dialog = document.querySelector('dialog')
    if (dialog && typeof dialog.showModal === 'function' && !dialog.open) {
      dialog.showModal()
    }
  })
}

async function launchAttack(service: string) {
  if (!attackTarget.value) return

  // Find a connected node to act as the attacker
  let attackerNodeId = store.nodeList.find((n: any) => store.isConnected(n.id))?.id
  if (!attackerNodeId && store.nodeList.length > 0) {
    attackerNodeId = store.nodeList[0].id // Fallback
  }
  if (!attackerNodeId) {
    attackStatus.value = 'ERROR: No active node available to launch attack from.'
    return
  }

  attackStatus.value = 'Deploying payload...'
  try {
    const res = await fetch(`/api/nodes/${attackerNodeId}/agents/attack/bruteforce`, {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('nr_token'),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: attackTarget.value,
        service: service
      })
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || data.message || 'Attack failed')

    if (data.credentials) {
      attackStatus.value = `CRACKED! User: ${data.credentials.username} | Pass: ${data.credentials.password}`
    } else {
      attackStatus.value = data.message || 'Attack launched!'
    }

    setTimeout(() => {
      attackTarget.value = null
    }, 5000)
  } catch(err: any) {
    attackStatus.value = 'ERROR: ' + err.message
  }
}

async function ctxConnect() {
  const id = ctxMenu.value.targetId; closeCtx()
  try { await api.connectNode(id); store.manuallyDisconnected.delete(id); await store.refreshConnections() }
  catch (e) { alert('Connect failed: ' + String(e)) }
}
async function ctxDisconnect() {
  const id = ctxMenu.value.targetId; closeCtx()
  try { await api.disconnectNode(id); store.manuallyDisconnected.add(id); await store.refreshConnections() }
  catch (e) { alert('Disconnect failed: ' + String(e)) }
}

// Pin a node to the centre of the layout (others orbit around it). Useful to
// anchor your gateway/router as the hub instead of letting physics decide.
const pinnedId = ref<string | null>(null)
function ctxTogglePin() {
  const id = ctxMenu.value.targetId
  closeCtx()
  togglePin(id)
}
function ctxSeverLink() {
  const id = ctxMenu.value.targetId
  closeCtx()
  if (environmentMode.value === 'simulation') {
    severedLinks.value.add(id)
    updateVisualState()
  }
}

function togglePin(id: string) {
  const setFixed = (nid: string, v: number | undefined) => {
    const n = nodeCache.get(nid)
    if (n) { n.fx = v; n.fy = v; n.fz = v }
  }
  if (pinnedId.value === id) {
    setFixed(id, undefined); pinnedId.value = null
  } else {
    if (pinnedId.value) setFixed(pinnedId.value, undefined)
    setFixed(id, 0); pinnedId.value = id
  }
  updateGraph()
  if (graph && typeof graph.d3ReheatSimulation === 'function') graph.d3ReheatSimulation()
}
let graph: any = null
let globeInstance: any = null
let attackInterval: number | null = null



let resizeObserver: ResizeObserver | null = null

const mode = ref<'select' | 'draw'>('select')
const layoutMode = ref<'floating' | 'hierarchical'>('floating')
const drawSource = ref<string | null>(null)
const discovering = ref(false)
const syncing = ref(false)
const debugStats = ref<{nodes: number, links: number} | null>(null)
const initError = ref<string | null>(null)
const telemetryData = ref<Record<string, Record<string, any>>>({})
const showThreats = ref(false)
const showAgents = ref(false)
const attackerView = ref(false)

const deceptionMode = ref(false)
const ghostRunning = ref(false)

// Digital Twin Environment State
const environmentMode = ref<'live' | 'simulation'>('live')
const severedLinks = ref<Set<string>>(new Set())

function toggleEnvironment() {
  environmentMode.value = environmentMode.value === 'live' ? 'simulation' : 'live'
  if (environmentMode.value === 'live') {
    severedLinks.value.clear()
  }
  updateVisualState()
}

// DVR State
const attackHistory = ref<Array<{ timestamp: string, infected: string[], events: string[] }>>([])
const currentTimeIndex = ref(0)
const infectedNodes = computed(() => {
  if (attackHistory.value.length === 0) return new Set<string>()
  const snap = attackHistory.value[currentTimeIndex.value]
  return new Set(snap ? snap.infected : [])
})
const currentEvents = computed(() => {
  if (attackHistory.value.length === 0) return []
  return attackHistory.value.slice(0, currentTimeIndex.value + 1).flatMap(snap =>
    snap.events.map(e => ({ time: snap.timestamp, text: e }))
  )
})

const heatmapBackground = computed(() => {
  if (attackHistory.value.length < 2) return 'var(--glass-bg)'
  const maxEvents = Math.max(...attackHistory.value.map(s => s.events.length), 1)
  const stops = attackHistory.value.map((snap, i) => {
    const intensity = snap.events.length / maxEvents
    const percent = (i / (attackHistory.value.length - 1)) * 100
    return `rgba(255, 45, 110, ${Math.max(0.1, intensity)}) ${percent}%`
  })
  return `linear-gradient(to right, ${stops.join(', ')})`
})

let ghostRunnerInterval: number | null = null

watch(currentTimeIndex, () => {
  updateVisualState()
})

function launchGhostRunner() {
  if (!deceptionMode.value) return
  if (ghostRunning.value) {
    // Stop runner
    ghostRunning.value = false
    store.setDefcon(5)
    if (ghostRunnerInterval) clearInterval(ghostRunnerInterval)
    return
  }

  // Start runner
  ghostRunning.value = true
  store.setDefcon(1)

  // Start from the cloud / edge router
  const startNodes = store.nodeList.filter(n =>
    n.id === 'Router-1' ||
    (n.tags && n.tags.includes('cloud')) ||
    (n.type === 'ghost')
  )

  const edges = startNodes.length > 0 ? startNodes : [store.nodeList[0]]
  const initialInfected = edges.map(n => n.id)

  const nowStr = new Date().toLocaleTimeString('en-US', { hour12: false })
  attackHistory.value = [{
    timestamp: nowStr,
    infected: initialInfected,
    events: ['Anomalous ping sweep detected at edge boundary.', 'AI Confidence 72% - Potential Initial Access.']
  }]
  currentTimeIndex.value = 0

  updateVisualState()

  // Propagate temporally every 2.5 seconds
  ghostRunnerInterval = window.setInterval(() => {
    const lastSnap = attackHistory.value[attackHistory.value.length - 1]
    const currentInfected = new Set(lastSnap.infected)
    let newInfectedCount = 0
    let newEvents: string[] = []

    // Build adjacency list matching edges
    const adj: Record<string, { target: string, edgeId: string }[]> = {}
    store.links.forEach((l: any) => {
      const s = endId(l.source)
      const t = endId(l.target)
      if (!adj[s]) adj[s] = []
      if (!adj[t]) adj[t] = []
      adj[s].push({ target: t, edgeId: l.id })
      adj[t].push({ target: s, edgeId: l.id })
    })

    // Spread to neighbors
    currentInfected.forEach(nodeId => {
      const neighbors = adj[nodeId] || []
      neighbors.forEach(n => {
        // Enforce simulation branch severed links
        if (environmentMode.value === 'simulation' && severedLinks.value.has(n.edgeId)) {
          // Attack path blocked
          if (Math.random() > 0.8) {
            newEvents.push(`[SIMULATION] Blocked attempt to reach ${n.target} via severed link ${n.edgeId}.`)
          }
          return
        }

        // Legion Autonomous Defense (Phase 3)
        if (showAgents.value) {
          const targetNode = store.nodeList.find(x => x.id === n.target)
          const isGhost = targetNode?.type === 'ghost'
          if (!isGhost && !store.isolatedNodes.has(n.target)) {
             // Agent autonomously detects the threat over the link
             severedLinks.value.add(n.edgeId)
             newEvents.push(`[LEGION] Autonomous agent on ${n.target} detected lateral movement and severed incoming connection.`)
             // Make sure we are in simulation mode for it to be visually red/dashed
             if (environmentMode.value !== 'simulation') {
               environmentMode.value = 'simulation'
             }
             return
          }
        }

        // 40% chance to infect connected node
        if (!store.isolatedNodes.has(n.target) && !currentInfected.has(n.target) && Math.random() > 0.6) {
          currentInfected.add(n.target)
          newInfectedCount++
          newEvents.push(`Lateral movement to ${n.target}.`)
        }
      })
    })

    if (newInfectedCount > 0) {
      newEvents.push(`AI Confidence 96% - Ghost Runner Active.`)
      attackHistory.value.push({
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        infected: Array.from(currentInfected),
        events: newEvents
      })
      // Auto-advance scrubber if we are at the latest
      if (currentTimeIndex.value === attackHistory.value.length - 2) {
        currentTimeIndex.value = attackHistory.value.length - 1
      }
    } else {
      // If no new nodes, maybe just data exfil activity
      if (Math.random() > 0.7 && currentInfected.size > 1) {
         attackHistory.value.push({
          timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
          infected: Array.from(currentInfected),
          events: ['Data exfiltration payload staged.', 'Massive outbound traffic spike to unknown external IP.']
        })
        if (currentTimeIndex.value === attackHistory.value.length - 2) {
          currentTimeIndex.value = attackHistory.value.length - 1
        }
      }
    }
  }, 2500)
}

function isolateHost(nodeId: string) {
  if (!nodeId) return
  store.isolateNode(nodeId)

  // Record action in history
  if (deceptionMode.value && attackHistory.value.length > 0) {
    attackHistory.value.push({
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      infected: Array.from(infectedNodes.value),
      events: [`[SYSTEM] Agentic Playbook executed: Isolate ${nodeId}.`, `Containment Box activated. Edge traffic zeroed.`]
    })
    currentTimeIndex.value = attackHistory.value.length - 1
  }

  updateVisualState()
}

function rollbackHost(nodeId: string) {
  if (!nodeId) return
  store.isolatedNodes.delete(nodeId)

  if (deceptionMode.value && attackHistory.value.length > 0) {
    attackHistory.value.push({
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      infected: Array.from(infectedNodes.value),
      events: [`[SYSTEM] Rollback Containment on ${nodeId}.`, `Node restored to normal traffic. User overridden AI.`]
    })
    currentTimeIndex.value = attackHistory.value.length - 1
  }

  updateVisualState()
}

// Real per-node vitals (CPU/RAM/net) from the telemetry poller
const nodeVitals = ref<Record<string, { cpu: number | null, ram: number | null, net_tx: number, net_rx: number }>>({})
// Active TCP reachability per node (online + connect latency)
const nodeReach = ref<Record<string, { reachable: boolean, latency_ms: number | null }>>({})
let telemetryWs: WebSocket | null = null

// Bloom effect state
const enableBloom = ref(true)
let bloomPass: any = null

const blastRadius = computed(() => {
  const isAttacker = attackerView.value
  const isCompromisedSelected = deceptionMode.value && store.selectedId && infectedNodes.value.has(store.selectedId)

  if (!store.selectedId) return null
  if (!isAttacker && !isCompromisedSelected) return null
  const distances: Record<string, number> = {}
  const q = [{ id: store.selectedId, dist: 0 }]
  distances[store.selectedId] = 0

  const adj: Record<string, string[]> = {}
  store.links.forEach((l: any) => {
    const s = endId(l.source)
    const t = endId(l.target)
    if (!adj[s]) adj[s] = []
    if (!adj[t]) adj[t] = []
    adj[s].push(t)
    adj[t].push(s)
  })

  let head = 0
  while(head < q.length) {
    const curr = q[head++]
    if (curr.dist >= 2) continue
    const neighbors = adj[curr.id] || []
    for(const n of neighbors) {
      if (distances[n] === undefined) {
        distances[n] = curr.dist + 1
        q.push({ id: n, dist: curr.dist + 1 })
      }
    }
  }
  return distances
})

// Update Visual State without reloading graph data
function updateVisualState() {
  if (!graph) return
  graph.nodeColor(graph.nodeColor())
  graph.nodeThreeObject(graph.nodeThreeObject())
  graph.linkColor(graph.linkColor())
  graph.linkDirectionalParticles(graph.linkDirectionalParticles())
}

watch(() => store.selectedId, () => {
  if (attackerView.value) updateGraph()
})

function toggleBloom() {
  if (bloomPass) {
    bloomPass.strength = enableBloom.value ? 1.5 : 0
  }
}

function toggleLayout() {
  layoutMode.value = layoutMode.value === 'floating' ? 'hierarchical' : 'floating'
  if (graph && typeof graph.dagMode === 'function') {
    graph.dagMode(layoutMode.value === 'hierarchical' ? 'td' : null)
    if (layoutMode.value === 'hierarchical') {
      graph.dagLevelDistance(80)
      // Lock camera to a flat 2D top-down perspective (Unifi style)
      graph.cameraPosition({ x: 0, y: -40, z: 250 }, { x: 0, y: -40, z: 0 }, 1000)
    } else {
      // Return to a nice 3D angle
      graph.cameraPosition({ x: 0, y: 150, z: 300 }, { x: 0, y: 0, z: 0 }, 1000)
    }
  }
}

async function doAutoDiscover() {
  discovering.value = true
  try {
    const res = await api.autoDiscoverLinks()
    alert(`Auto-discovery complete!\nFound ${res.new_links} new links via LLDP.`)
    await store.refresh() // Refresh store to pull new links
    updateGraph()
  } catch (e) {
    alert(String(e))
  } finally {
    discovering.value = false
  }
}


// Ghost nodes from discovery (persisted in localStorage)
const getInitialGhostNodes = () => {
  try {
    const item = localStorage.getItem('nr_ghost_nodes')
    if (item) {
      const parsed = JSON.parse(item)
      if (Array.isArray(parsed)) return parsed
    }
  } catch (e) {
    console.error("Failed to parse nr_ghost_nodes from localStorage:", e)
  }
  return []
}

const ghostNodes = ref<any[]>(getInitialGhostNodes())

function saveGhostNodes(nodesList: any[]) {
  ghostNodes.value = nodesList
  try {
    localStorage.setItem('nr_ghost_nodes', JSON.stringify(nodesList))
  } catch (e) {
    console.error("Failed to save nr_ghost_nodes to localStorage:", e)
  }
}

function retryInit() {
  initError.value = null
  if (canvasRef.value) {
    canvasRef.value.innerHTML = ''
  }
  initGraph()
  updateGraph()
}

async function pickGns3Project() {
  syncing.value = true
  try {
    const [remoteProjects, localProjects] = await Promise.all([
      api.listGns3Projects().catch(() => [] as any[]),
      api.listLocalGns3Projects().catch(() => [] as any[])
    ])

    const allProjects: { name: string; id: string; path?: string; isLocal: boolean }[] = [
      ...remoteProjects.map(p => ({ ...p, id: p.project_id, isLocal: false })),
      ...localProjects.map(p => ({ ...p, isLocal: true }))
    ]

    if (allProjects.length === 0) {
      alert('No GNS3 projects found. Check your GNS3 server URL or local projects path (/home/aso/GNS3/projects).')
      return
    }

    const names = allProjects.map((p, i) => `${i + 1}: ${p.name} ${p.isLocal ? '(LOCAL)' : '(REMOTE)'}`).join('\n')
    const choice = prompt(`Select GNS3 Project to sync:\n\n${names}\n\n(Enter number)`)

    if (choice) {
      const idx = parseInt(choice) - 1
      const selected = allProjects[idx]
      if (selected) {
        let res
        if (selected.isLocal) {
          res = await api.syncLocalGns3Project(selected.path!)
        } else {
          res = await api.syncGns3Project(selected.id)
        }
        await store.refresh()
        alert(`Success!\n\nImported ${res.nodes} nodes and ${res.links} links from ${selected.name}.`)
      }
    }
  } catch (e) {
    alert(String(e))
  } finally {
    syncing.value = false
  }
}

async function doDiscover() {
  discovering.value = true
  try {
    let res: any
    try {
      res = await store.discover()
    } catch (e) {
      console.warn("Backend discovery failed, entering high-fidelity simulation mode:", e)
      res = { status: 'error', message: String(e) }
    }

    let msg = ""
    let discoveredGhosts: any[] = []

    if (res.status === 'success') {
      msg = `Scanning complete!\n\nDiscovered ${res.discovered} new links.`
      discoveredGhosts = res.unknown_neighbors || []
    } else {
      msg = `Cyber Range Scan Initiated (Simulated Fallback Mode).\n\nBackend status: ${res.message || 'Offline'}`
      discoveredGhosts = []
    }

    // FALLBACK / DEMO MODE: If no real ghost nodes are found on this network interface,
    // inject high-fidelity simulated ghost nodes for an immersive Cyber Defense experience!
    if (discoveredGhosts.length === 0) {
      console.log("No real unknown neighbors discovered. Injecting active defense simulated ghost nodes.")
      discoveredGhosts = [
        {
          ip: '192.168.1.189',
          name: 'ROGUE-TAP.MILITARY.SEC',
          source_node: store.nodeList[0]?.name || 'Router-1',
          method: 'arp'
        },
        {
          ip: '10.0.4.52',
          name: 'GHOST-STRETCH-IOT',
          source_node: store.nodeList[1]?.name || store.nodeList[0]?.name || 'RPI',
          method: 'lldp'
        }
      ]
    }

    saveGhostNodes(discoveredGhosts)

    msg += `\n\nFound ${discoveredGhosts.length} unknown neighbors/ghost nodes on the network!\n`
    msg += `These have been mapped to the 3D space as red "Ghost Nodes" with active traffic animations.`

    updateGraph()
    alert(msg)
  } catch (e) {
    alert(String(e))
  } finally {
    discovering.value = false
  }
}

// Keep a persistent cache of node objects to reuse across graph updates.
// This is critical for D3 force simulation to preserve and update coordinates correctly in-place.
const nodeCache = new Map<string, any>()
const linkCache = new Map<string, any>()

function getGraphData() {
  const activeIds = new Set<string>()
  const activeLinkIds = new Set<string>()

  // 1. Build nodes list
  const nodesList: any[] = []

  // Regular GNS3 nodes
  store.nodeList.forEach(node => {
    activeIds.add(node.id)
    let cached = nodeCache.get(node.id)
    if (!cached) {
      cached = { id: node.id }
      nodeCache.set(node.id, cached)
    }
    // Update dynamic properties without touching x, y, z, vx, vy, vz
    cached.name = node.name
    cached.type = node.device_type
    cached.connected = store.isConnected(node.id)
    cached.val = 4
    cached.tags = node.tags || []
    nodesList.push(cached)
  })



  // Inject ghost nodes safely
  ghostNodes.value.forEach((ghost, i) => {
    const ghostId = `ghost-${i}-${ghost.ip || ghost.name || 'unknown'}`
    activeIds.add(ghostId)
    let cached = nodeCache.get(ghostId)
    if (!cached) {
      cached = { id: ghostId }
      nodeCache.set(ghostId, cached)
    }
    // Update dynamic properties without touching x, y, z, vx, vy, vz
    cached.name = ghost.ip || ghost.name || 'Unknown Device'
    cached.type = 'ghost'
    cached.connected = false
    cached.val = 8 // Make ghost nodes larger
    nodesList.push(cached)
  })

  // Clean up cache for deleted nodes
  for (const id of nodeCache.keys()) {
    if (!activeIds.has(id)) {
      nodeCache.delete(id)
    }
  }

  // 2. Build links list
  const linksList: any[] = []

  // Regular links
  store.links.forEach(link => {
    activeLinkIds.add(link.id)
    let cached = linkCache.get(link.id)
    if (!cached) {
      cached = { id: link.id }
      const protocols = ['MQTT', 'Modbus', 'QUIC', 'TCP', 'HTTPS', 'DNP3']
      cached.protocol_type = protocols[Math.floor(Math.random() * protocols.length)]
      linkCache.set(link.id, cached)
    }
    if (link.metadata && link.metadata.protocol) {
      cached.protocol_type = link.metadata.protocol
    }
    // Only (re)assign source/target when they actually change. D3 resolves
    // string IDs into node objects in place; blindly overwriting them with the
    // string again (without a graphData reset) makes the simulation choke
    // ("Cannot create property 'vx' on string ...").
    const curSrc = typeof cached.source === 'object' ? cached.source?.id : cached.source
    const curTgt = typeof cached.target === 'object' ? cached.target?.id : cached.target
    if (curSrc !== link.source) cached.source = link.source
    if (curTgt !== link.target) cached.target = link.target
    cached.auto = link.auto_discovered
    // A link carries traffic when both ends are "up". L2 fabric (switch/hub)
    // can't be "connected" but is always up if a real neighbour is connected,
    // so traffic still flows e.g. pc1 → switch → router.
    cached.active = nodeUp(link.source) && nodeUp(link.target)
    cached.isGhostLink = false
    linksList.push(cached)
  })



  // Ghost links
  ghostNodes.value.forEach((ghost, i) => {
    const ghostId = `ghost-${i}-${ghost.ip || ghost.name || 'unknown'}`
    const linkId = `link-${ghostId}`
    activeLinkIds.add(linkId)

    const srcNode = store.nodeList.find(n =>
      n.name.trim().toLowerCase() === (ghost.source_node || '').trim().toLowerCase()
    ) || store.nodeList[0] || { id: 'unknown-source' }

    let cached = linkCache.get(linkId)
    if (!cached) {
      cached = { id: linkId }
      linkCache.set(linkId, cached)
    }
    // Only reassign on change (D3 resolves these to node objects in place)
    const curSrc = typeof cached.source === 'object' ? cached.source?.id : cached.source
    const curTgt = typeof cached.target === 'object' ? cached.target?.id : cached.target
    if (curSrc !== srcNode.id) cached.source = srcNode.id
    if (curTgt !== ghostId) cached.target = ghostId
    cached.auto = true
    cached.active = false
    cached.isGhostLink = true
    linksList.push(cached)
  })

  // Clean up cache for deleted links
  for (const id of linkCache.keys()) {
    if (!activeLinkIds.has(id)) {
      linkCache.delete(id)
    }
  }

  // Filter out any links whose source or target node is not present in activeIds.
  // This is critical to prevent D3 force simulation from hitting undefined node references
  // which causes NaN coordinates and a black screen.
  const validLinksList = linksList.filter(link => {
    const sId = typeof link.source === 'object' ? link.source.id : link.source
    const tId = typeof link.target === 'object' ? link.target.id : link.target
    const hasSource = activeIds.has(sId)
    const hasTarget = activeIds.has(tId)
    if (!hasSource || !hasTarget) {
      console.warn(`Filtering out orphan link ${link.id}: source (${sId}) exists: ${hasSource}, target (${tId}) exists: ${hasTarget}`)
      return false
    }
    return true
  })

  return { nodes: nodesList, links: validLinksList }
}

// --- 3D Mesh Generator & Animation Loop ---
let animationFrameId: number// --- 3D Geometry Cache ---
const geoCache = {
  sphereCore: new THREE.SphereGeometry(3.5, 16, 16),
  sphereDormant: new THREE.SphereGeometry(3, 8, 8),
  boxCore: new THREE.BoxGeometry(4.5, 4.5, 4.5),
  boxCage: new THREE.BoxGeometry(9, 9, 9),
  octahedronCage: new THREE.OctahedronGeometry(6.5, 0),
  ring: new THREE.RingGeometry(7, 9, 32),
  torusKnot: new THREE.TorusKnotGeometry(2.5, 0.7, 64, 8),
  torusOrbit: new THREE.TorusGeometry(7.5, 0.3, 8, 32),
  icosahedronCage: new THREE.IcosahedronGeometry(6, 1),
  auraSphere: new THREE.SphereGeometry(7.5, 32, 32)
}

// --- 3D Material Cache ---
const matCache = new Map<string, THREE.Material>()
function getMaterial(type: string, color: number, opacity: number = 1.0, wireframe: boolean = false, additive: boolean = false, doubleSide: boolean = false): THREE.Material {
  const key = `${type}_${color}_${opacity}_${wireframe}_${additive}_${doubleSide}`
  if (matCache.has(key)) return matCache.get(key)!

  const params: THREE.MeshBasicMaterialParameters = {
    color,
    transparent: opacity < 1.0 || additive,
    opacity,
    wireframe
  }
  if (additive) params.blending = THREE.AdditiveBlending
  if (additive) params.depthWrite = false
  if (doubleSide) params.side = THREE.DoubleSide

  const mat = new THREE.MeshBasicMaterial(params)
  matCache.set(key, mat)
  return mat
}

function getHolographicMaterial(color: number, opacity: number = 1.0, wireframe: boolean = false): THREE.Material {
  const key = `holo_${color}_${opacity}_${wireframe}`
  if (matCache.has(key)) return matCache.get(key)!

  const mat = new THREE.MeshPhysicalMaterial({
    color,
    transparent: true,
    opacity: opacity,
    wireframe,
    roughness: 0.1,
    transmission: opacity > 0.5 ? 0.9 : 0.0, // glass-like if opaque
    thickness: 1.5,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1
  })
  matCache.set(key, mat)
  return mat
}

// Create custom 3D objects for nodes
const createThreeNodeObject = (node: any) => {
  const group = new THREE.Group()
  const id = node.id
  const isGhost = node.type === 'ghost'
  const isRpi = id === 'RPI'
  const isRouter = id === 'Router-1'
  const isCloud = node.tags && node.tags.includes('cloud')
  const isSelected = id === store.selectedId
  const isDrawSrc = id === drawSource.value
  const connected = node.connected

  // Determine neon primary color
  let colorVal = 0x00e5ff // standard electric cyan
  const isVulnerable = node.tags && node.tags.includes('vulnerable')
  let opacityVal = 1.0
  let isGhosted = false

  if (deceptionMode.value) {
    // In Deception Mode, everything is a dark holographic blue, unless infected
    if (infectedNodes.value.has(id)) {
      colorVal = 0xff0055 // Bright red for compromised nodes
      opacityVal = 1.0
    } else {
      colorVal = 0x0055ff // Holographic blue for legitimate network
      opacityVal = 0.3
      isGhosted = true // Make it look wireframe/dormant
    }
  } else if (blastRadius.value) {
    const dist = blastRadius.value[id]
    if (dist === undefined) {
      isGhosted = true
      colorVal = 0x333333
      opacityVal = 0.1
    } else if (dist === 0) {
      colorVal = 0xff0055 // epicenter
    } else if (dist === 1) {
      colorVal = 0xff2d6e // 1 hop
    } else if (dist === 2) {
      colorVal = 0xff8c00 // 2 hops
    }
  } else {
    if (store.isolatedNodes.has(id)) {
      colorVal = 0xffa500 // Containment Orange
    } else if (isSelected) colorVal = 0xff2d6e // pulsing red/pink for selected
    else if (isDrawSrc) colorVal = 0xffbe0b // golden for link draw source
    else if (isGhost || isVulnerable) colorVal = 0xff2d6e // dangerous hacker red
    else if (connected) colorVal = 0x00ff9d // cyber green for active nodes
  }

  // Use cached materials
  const wireframe = deceptionMode.value && !infectedNodes.value.has(id)
  const mat = getHolographicMaterial(colorVal, opacityVal, wireframe)
  let core: THREE.Mesh
  const animGroup = new THREE.Group() // group for rotating meshes
  ;(animGroup as any).__isAnimGroup = true

  if (deceptionMode.value) {
    core = new THREE.Mesh(geoCache.sphereCore, mat)
    if (infectedNodes.value.has(id)) {
      // Show aggressive cage for infected
      const cageMat = getMaterial('cage', colorVal, 0.8, true)
      const cage = new THREE.Mesh(geoCache.octahedronCage, cageMat)
      animGroup.add(cage)
    }
  } else if (isGhost) {
    core = new THREE.Mesh(geoCache.sphereCore, mat)
    const cageMat = getMaterial('cage', colorVal, 0.6, true)
    const cage = new THREE.Mesh(geoCache.octahedronCage, cageMat)
    animGroup.add(cage)
  } else if (isRpi) {
    core = new THREE.Mesh(geoCache.boxCore, mat)
    const ringMat = getMaterial('ring', colorVal, 0.6, false, false, true)
    const ring = new THREE.Mesh(geoCache.ring, ringMat)
    ring.rotation.x = Math.PI / 2.5
    animGroup.add(ring)
  } else if (isRouter) {
    const knotMat = getMaterial('wire', colorVal, 1.0, true)
    core = new THREE.Mesh(geoCache.torusKnot, knotMat)
    const orbitMat = getMaterial('orbit', colorVal, 0.5)
    const orbit = new THREE.Mesh(geoCache.torusOrbit, orbitMat)
    orbit.rotation.x = Math.PI / 2
    animGroup.add(orbit)
  } else if (connected) {
    core = new THREE.Mesh(geoCache.sphereCore, mat)
    const cageMat = getMaterial('cage', colorVal, 0.4, true)
    const cage = new THREE.Mesh(geoCache.icosahedronCage, cageMat)
    animGroup.add(cage)
  } else if (store.isolatedNodes.has(id)) {
    core = new THREE.Mesh(geoCache.sphereCore, mat)
    const cageMat = getMaterial('cage', 0xffa500, 0.8, true)
    const cage = new THREE.Mesh(geoCache.boxCage, cageMat)
    animGroup.add(cage)
  } else {
    const dormantMat = getMaterial('dormant', isGhosted ? colorVal : 0x757575, isGhosted ? 0.1 : 0.5)
    core = new THREE.Mesh(geoCache.sphereDormant, dormantMat)
  }

  group.add(core)
  group.add(animGroup)

  if (showAgents.value && !isGhost && connected) {
    // Add orbiting Legion agent (bright blue orb)
    const agentMat = getMaterial('agent', 0x0088ff, 1.0, false, true)
    const agent = new THREE.Mesh(geoCache.sphereDormant, agentMat)
    agent.position.set(6, 0, 0) // offset from center
    agent.scale.set(0.5, 0.5, 0.5)

    // Add a pulsing aura to the agent
    const agentAuraMat = getMaterial('agent_aura', 0x0088ff, 0.4, false, true)
    const agentAura = new THREE.Mesh(geoCache.auraSphere, agentAuraMat)
    agentAura.scale.set(0.2, 0.2, 0.2)
    agent.add(agentAura)

    // Wrap in an orbit group
    const agentOrbitGroup = new THREE.Group()
    ;(agentOrbitGroup as any).__isAgentOrbit = true
    // Randomize initial angle
    agentOrbitGroup.rotation.y = Math.random() * Math.PI * 2
    agentOrbitGroup.rotation.x = (Math.random() - 0.5) * Math.PI * 0.5
    agentOrbitGroup.add(agent)
    animGroup.add(agentOrbitGroup)
  }

  if (isCloud && connected) {
    // Orbital Swarm for ephemeral pods
    const podMat = getMaterial('pod', 0x00e5ff, 0.8, false, true)
    const podCount = 30
    const iMesh = new THREE.InstancedMesh(geoCache.sphereDormant, podMat, podCount)
    ;(iMesh as any).__isSwarm = true
    const dummy = new THREE.Object3D()
    const podData = []
    for (let i = 0; i < podCount; i++) {
      const radius = 6 + Math.random() * 4
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const speed = 0.01 + Math.random() * 0.02
      podData.push({ radius, theta, phi, speed })

      dummy.position.set(
        radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.sin(phi) * Math.sin(theta),
        radius * Math.cos(phi)
      )
      dummy.scale.set(0.3, 0.3, 0.3)
      dummy.updateMatrix()
      iMesh.setMatrixAt(i, dummy.matrix)
    }
    ;(iMesh as any).__dummy = dummy
    ;(iMesh as any).__podData = podData
    animGroup.add(iMesh)
  }

  if (!isGhosted && (connected || isGhost || isRpi || isRouter || blastRadius.value)) {
    const auraMat = getMaterial('aura', colorVal, 0.15, false, true)
    const aura = new THREE.Mesh(geoCache.auraSphere, auraMat)
    ;(aura as any).__isAura = true
    group.add(aura)
  }

  return group
}

function startAnimationLoop() {
  const colorGreen = new THREE.Color(0x00ff9d)
  const colorAmber = new THREE.Color(0xffbe0b)
  const colorRed = new THREE.Color(0xff2d6e)
  const tempColor = new THREE.Color()

  function animate() {
    animationFrameId = requestAnimationFrame(animate)

    if (graph) {
      const time = Date.now() * 0.003
      const nodes = graph.graphData().nodes

      nodes.forEach((node: any) => {
        if (node.__threeObj) {
          const group = node.__threeObj

          const isVulnerable = node.tags && node.tags.includes('vulnerable')
          const isGhost = node.type === 'ghost'
          // For demonstration, we simulate 'agents' as nodes tagged 'agent' or if their name implies it
          const isAgent = (node.tags && node.tags.includes('agent')) || (node.name && node.name.toLowerCase().includes('agent'))

          // 0. Update base colors dynamically based on layers
          let targetColor = 0x00e5ff
          if (store.isolatedNodes.has(node.id)) targetColor = 0xffa500
          else if (node.id === store.selectedId) targetColor = 0xff2d6e
          else if (node.id === drawSource.value) targetColor = 0xffbe0b
          else if (showThreats.value && (isGhost || isVulnerable)) targetColor = 0xff0000 // Pure red for active threat layer
          else if (showAgents.value && isAgent) targetColor = 0x0088ff // Deep blue for active agent layer
          else if (isGhost || isVulnerable) targetColor = 0xff2d6e
          else if (node.connected) targetColor = 0x00ff9d

          // Apply color to core
          const core = group.children[0]
          if (core && core.material && core.material.color) {
            core.material.color.setHex(targetColor)
          }

          // 1. Rotate the custom animGroup and apply colors
          const animGroup = group.children.find((c: any) => c.__isAnimGroup)
          if (animGroup) {
            animGroup.rotation.x += 0.01
            animGroup.rotation.y += 0.015

            // orbit legion agents and pod swarms
            animGroup.children.forEach((subChild: any) => {
              if (subChild.__isAgentOrbit) {
                subChild.rotation.y += 0.04
              }
              if (subChild.__isSwarm) {
                 const dummy = subChild.__dummy
                 const podData = subChild.__podData
                 for(let i=0; i<podData.length; i++) {
                    const p = podData[i]
                    p.theta += p.speed
                    dummy.position.set(
                      p.radius * Math.sin(p.phi) * Math.cos(p.theta),
                      p.radius * Math.sin(p.phi) * Math.sin(p.theta),
                      p.radius * Math.cos(p.phi)
                    )
                    dummy.scale.set(0.3, 0.3, 0.3)
                    dummy.updateMatrix()
                    subChild.setMatrixAt(i, dummy.matrix)
                 }
                 subChild.instanceMatrix.needsUpdate = true
              }
            })

            animGroup.traverse((child: any) => {
              if (child.material && child.material.color) {
                child.material.color.setHex(targetColor)
              }
            })
          }

          // 2. Pulse the breathing neon aura scale (Volumetric Blast Radius)
          const aura = group.children.find((c: any) => c.__isAura)
          if (aura) {
            if (showThreats.value && (isGhost || isVulnerable)) {
              // Volumetric Blast Radius for compromised nodes
              const speed = 5
              const scale = 2.5 + Math.sin(time * speed) * 0.8 // Huge expanding sphere
              aura.scale.setScalar(scale)
              aura.material.color.setHex(0xff0000) // Deep red for ground zero
              aura.material.opacity = 0.4 + Math.sin(time * speed) * 0.2
            } else if (blastRadius.value && blastRadius.value[node.id] !== undefined) {
              // Amber tint for adjacent vulnerable nodes in blast radius
              const speed = 4
              const scale = 1.5 + Math.sin(time * speed) * 0.5
              aura.scale.setScalar(scale)
              aura.material.color.setHex(0xffa500) // Amber
              aura.material.opacity = 0.3 + Math.sin(time * speed) * 0.15
            } else if (showAgents.value && isAgent) {
              const speed = 3
              const scale = 1.1 + Math.sin(time * speed) * 0.3
              aura.scale.setScalar(scale)
              aura.material.color.setHex(0x0088ff)
              aura.material.opacity = 0.4 + Math.sin(time * speed) * 0.2
            } else {
              const v = nodeVitals.value[node.id]
              const cpu = v && v.cpu !== null ? v.cpu : null
              // Load-driven aura: faster/larger pulse and green→amber→red tint
              const load = cpu !== null ? cpu / 100 : 0
              const speed = 1 + load * 3
              const scale = 1.0 + Math.sin(time * speed) * (0.12 + load * 0.25)
              aura.scale.setScalar(scale)

              if (cpu !== null) {
                // green (0x00ff9d) -> amber (0xffbe0b) -> red (0xff2d6e)
                if (cpu < 50) {
                  tempColor.copy(colorGreen).lerp(colorAmber, cpu / 50)
                } else {
                  tempColor.copy(colorAmber).lerp(colorRed, (cpu - 50) / 50)
                }
                aura.material.color.copy(tempColor)
                aura.material.opacity = 0.12 + load * 0.25
              } else {
                aura.material.color.setHex(targetColor)
                aura.material.opacity = 0.15
              }
            }
          }
        }
      })
    }
  }
  animate()
}

function stopAnimationLoop() {
  if (animationFrameId !== null) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
}

function initGraph() {
  if (!canvasRef.value) return

  try {
    const ForceGraphConstructor = typeof ForceGraph3D === 'function'
      ? ForceGraph3D
      : ((ForceGraph3D as any).default || ForceGraph3D)

    if (typeof ForceGraphConstructor !== 'function') {
      throw new Error(`3d-force-graph resolved to a non-function constructor: ${typeof ForceGraphConstructor}`)
    }

    // Initialize Globe.gl as the background skybox
    if (globeCanvasRef.value && !globeInstance) {
      globeInstance = Globe()(globeCanvasRef.value)
        .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
        .backgroundColor('rgba(0,0,0,0)')
        .arcColor((arc: any) => arc.exfil ? '#ff2d6e' : 'rgba(0, 229, 255, 0.4)')
        .arcStroke((arc: any) => arc.exfil ? 2.5 : 0.2)
        .arcDashAnimateTime((arc: any) => arc.exfil ? 300 : 2000)
        .arcDashLength((arc: any) => arc.exfil ? 0.8 : 0.4)
        .arcDashGap(4)
        .arcDashInitialGap(() => Math.random() * 5)
        .hexPolygonsData([])
        .hexPolygonColor(() => 'rgba(255, 45, 110, 0.8)')
        .hexPolygonAltitude((d: any) => d.volume ? Math.min(0.5, d.volume / 100) : 0.01)
        .hexPolygonResolution(3)
        .hexPolygonMargin(0.3)

      globeInstance.controls().enabled = false
      globeInstance.controls().autoRotate = true
      globeInstance.controls().autoRotateSpeed = 0.5
      globeInstance.camera().position.z = 800
      globeInstance.scene().position.y = -200

      // Fake Pew Pew Attack Arcs
      const myDatacenter = { lat: 37.7749, lng: -122.4194 }
      let arcs: any[] = []

      attackInterval = window.setInterval(() => {
        if (!globeInstance) return

        const isExfil = store.defconLevel === 1

        if (isExfil) {
           // Massive exfiltration to a single sinkhole
           const sinkholeLat = 55.7558
           const sinkholeLng = 37.6173
           arcs.push({
             startLat: myDatacenter.lat,
             startLng: myDatacenter.lng,
             endLat: sinkholeLat,
             endLng: sinkholeLng,
             exfil: true
           })

           const currentHex = globeInstance.hexPolygonsData() || []
           const sink = currentHex.find((h: any) => h.lat === sinkholeLat && h.lng === sinkholeLng)
           if (sink) {
             sink.volume = (sink.volume || 0) + 10
           } else {
             currentHex.push({ lat: sinkholeLat, lng: sinkholeLng, volume: 10 })
           }
           globeInstance.hexPolygonsData([...currentHex])

        } else {
           // Normal attacks / traffic
           const attackerLat = (Math.random() - 0.5) * 180
           const attackerLng = (Math.random() - 0.5) * 360

           arcs.push({
             startLat: attackerLat,
             startLng: attackerLng,
             endLat: myDatacenter.lat,
             endLng: myDatacenter.lng,
             exfil: false
           })
        }

        if (arcs.length > (isExfil ? 50 : 20)) arcs.shift()

        globeInstance.arcsData([...arcs])
      }, 800)
    }

    const g = ForceGraphConstructor()(canvasRef.value)

    // Network graphs have cycles (rings, redundant paths); the hierarchical
    // (DAG) layout would otherwise throw "Invalid DAG structure". Skip the
    // offending links gracefully instead of crashing.
    if (typeof g.onDagError === 'function') g.onDagError(() => false)

    // 1. Data & Environment Setup
    if (typeof g.graphData === 'function') g.graphData(getGraphData())
    if (typeof g.backgroundColor === 'function') g.backgroundColor('rgba(0,0,0,0)') // transparent background

    // 2. Premium Custom 3D Mesh Nodes
    if (typeof g.nodeThreeObject === 'function') {
      g.nodeThreeObject(node => createThreeNodeObject(node))
    }
    if (typeof g.nodeLabel === 'function') {
      g.nodeLabel((n: any) => {
        let label = n.name
        if (deceptionMode.value && infectedNodes.value.has(n.id)) {
          return `${label}\n🔴 COMPROMISED (Ghost Runner)`
        }
        // Reachability line
        if (isConsoleless(n.id)) {
          label += `\n⚡ L2 fabric (no console)`
        } else {
          const r = nodeReach.value[n.id]
          if (r) label += r.reachable
            ? `\n🟢 reachable · ${r.latency_ms} ms`
            : `\n🔴 unreachable`
        }
        // Live vitals line (connected SSH nodes)
        const v = nodeVitals.value[n.id]
        if (v && (v.cpu !== null || v.ram !== null)) {
          const cpu = v.cpu !== null ? `${v.cpu}%` : '–'
          const ram = v.ram !== null ? `${v.ram}%` : '–'
          label += `\nCPU ${cpu} · RAM ${ram} · ↓${v.net_rx} ↑${v.net_tx} Mbps`
        }
        return label
      })
    }
    // 3. Floating Cyber-Grids for Layer Decks (Semantic Z-Tiering)
    const scene = g.scene()
    if (scene) {
      // External / Cloud Deck (Y = 120)
      const extGrid = new THREE.GridHelper(600, 30, 0xffbe0b, 0x3d300b)
      extGrid.position.y = 120
      ;(extGrid.material as any).transparent = true
      ;(extGrid.material as any).opacity = 0.08
      scene.add(extGrid)

      // DMZ Deck (Y = 40)
      const dmzGrid = new THREE.GridHelper(600, 30, 0xb829ea, 0x47105a)
      dmzGrid.position.y = 40
      ;(dmzGrid.material as any).transparent = true
      ;(dmzGrid.material as any).opacity = 0.08
      scene.add(dmzGrid)

      // Internal / Local Deck (Y = -40)
      const intGrid = new THREE.GridHelper(600, 30, 0x00e5ff, 0x0a333d)
      intGrid.position.y = -40
      ;(intGrid.material as any).transparent = true
      ;(intGrid.material as any).opacity = 0.08
      scene.add(intGrid)

      // Application / Identity Deck (Y = -120)
      const coreGrid = new THREE.GridHelper(600, 30, 0x2962ff, 0x0b173d)
      coreGrid.position.y = -120
      ;(coreGrid.material as any).transparent = true
      ;(coreGrid.material as any).opacity = 0.08
      scene.add(coreGrid)
    }

    // 4. Custom D3 Physics Force for Vertical Platform Layering (Semantic Z-Tiering)
    if (typeof g.d3Force === 'function') {
      g.d3Force('layer', (alpha: number) => {
        if (layoutMode.value === 'hierarchical') return // Skip layering if hierarchical

        const nodes = g.graphData().nodes
        nodes.forEach((node: any) => {
          // Default to Internal Deck
          let targetY = -40

          const name = (node.name || "").toLowerCase()
          const host = node.host || ""

          // Determine Tier
          if (name.includes('router') || name.includes('wan') || node.tags?.includes('cloud') || (host && !host.startsWith('192.') && !host.startsWith('10.') && host !== '127.0.0.1')) {
            targetY = 120 // External
          } else if (name.includes('dmz') || name.includes('proxy') || name.includes('nginx') || name.includes('web')) {
            targetY = 40  // DMZ
          } else if (name.includes('db') || name.includes('sql') || name.includes('ad') || name.includes('ldap') || name.includes('vault') || name.includes('identity')) {
            targetY = -120 // Core Identity/Data
          }

          node.vy += (targetY - node.y) * 0.15 * alpha
        })
      })
    }

    // 5. Link Customization
    if (typeof g.linkColor === 'function') {
      g.linkColor(link => {
        if (!link || typeof link !== 'object') return 'rgba(26, 37, 64, 0.5)'

        const sId = endId(link.source)
        const tId = endId(link.target)

        if (environmentMode.value === 'simulation' && severedLinks.value.has(link.id)) {
          return '#ff0000' // Severed link is bright red in simulation
        }

        if (store.isolatedNodes.has(sId) || store.isolatedNodes.has(tId)) {
          return 'rgba(255, 165, 0, 0.2)' // isolated, dim orange
        }

        if (deceptionMode.value) {
          if (infectedNodes.value.has(sId) && infectedNodes.value.has(tId)) return '#ff0055' // compromised link
          return 'rgba(0, 85, 255, 0.1)' // dormant blue link
        }

        if (blastRadius.value) {
           const sDist = blastRadius.value[sId]
           const tDist = blastRadius.value[tId]
           if (sDist === undefined || tDist === undefined) {
             return 'rgba(26, 37, 64, 0.05)' // ghost out links not in path
           }
           return 'rgba(255, 45, 110, 0.8)' // thick red kill chain
        }

        if (link.isGhostLink) return 'rgba(255, 45, 110, 0.4)'
        const h = linkHealth(link)
        if (h === 'down') return 'rgba(255, 45, 110, 0.7)'              // unreachable endpoint → red

        let baseColor = '#00ff9d' // default green
        if (link.protocol_type === 'MQTT') baseColor = '#00ff00'
        else if (link.protocol_type === 'Modbus') baseColor = '#ff0000'
        else if (link.protocol_type === 'QUIC') baseColor = '#a855f7'
        else if (link.protocol_type === 'TCP') baseColor = '#00e5ff'
        else if (link.protocol_type === 'HTTPS') baseColor = '#eab308'
        else if (link.protocol_type === 'DNP3') baseColor = '#ff5500'

        let opacity = link.active ? 0.6 : 0.2
        const hex = baseColor.replace('#', '')
        const r = parseInt(hex.substring(0, 2), 16) || 0
        const g_color = parseInt(hex.substring(2, 4), 16) || 255
        const b = parseInt(hex.substring(4, 6), 16) || 157

        return `rgba(${r}, ${g_color}, ${b}, ${opacity})`
      })
    }

    if (typeof g.linkWidth === 'function') {
      g.linkWidth(link => {
        if (!link || typeof link !== 'object') return 0.5
        const speed = link.metadata?.speed || 1000 // default 1Gbps
        let baseWidth = speed >= 10000 ? 2.5 : (speed >= 1000 ? 1.5 : 0.8)

        const medium = link.metadata?.medium || 'wired'
        if (medium === 'wireless' || medium === 'bluetooth') baseWidth *= 0.5 // Thinner for air

        return link.active ? baseWidth : (link.isGhostLink ? 1 : baseWidth * 0.5)
      })
    }

    // 6. Directional Particles / Animated Traffic Customization
    if (typeof g.linkDirectionalParticles === 'function') {
      g.linkDirectionalParticles(link => {
        if (!link || typeof link !== 'object') return 0
        const sId = endId(link.source)
        const tId = endId(link.target)

        if (environmentMode.value === 'simulation' && severedLinks.value.has(link.id)) {
          return 0
        }

        if (store.isolatedNodes.has(sId) || store.isolatedNodes.has(tId)) {
          return 0
        }

        if (deceptionMode.value) {
          if (infectedNodes.value.has(sId) || infectedNodes.value.has(tId)) return 4
          return 0 // hide normal traffic in deception mode
        }

        if (blastRadius.value) {
           const sDist = blastRadius.value[sId]
           const tDist = blastRadius.value[tId]
           if (sDist === undefined || tDist === undefined) return 0
           return 8 // show high particles on the kill chain
        }

        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }

        const medium = link.metadata?.medium || 'wired'
        // Base traffic for active links (simulate idle ping)
        let base = link.active ? 2 : (link.isGhostLink ? 4 : 0)

        if (medium === 'wireless') base += 2 // Wireless looks like a particle stream
        if (medium === 'bluetooth') base = 1 // Bluetooth is a slow ping

        // Spawn up to 20 fast particles to look like a solid laser stream under heavy load
        if (mbps > 0) return base + Math.min(20, Math.ceil(mbps * 3))
        return base
      })
    }

    if (typeof g.linkDirectionalParticleSpeed === 'function') {
      g.linkDirectionalParticleSpeed(link => {
        if (!link || typeof link !== 'object') return 0.01

        if (deceptionMode.value) return 0.02

        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }

        const speed = link.metadata?.speed || 1000
        let baseSpeed = speed >= 10000 ? 0.015 : (speed >= 1000 ? 0.008 : 0.004)
        if (link.isGhostLink) baseSpeed = 0.015

        const duplex = link.metadata?.duplex || 'full'
        // If half-duplex, slow it down and make it pulse (ping-pong logic handled elsewhere or simulated here by speed changes over time)
        if (duplex === 'half') {
          // Pulse the speed based on time to simulate half-duplex ping-pong
          baseSpeed *= (Date.now() % 2000 > 1000) ? 1.5 : 0.5
        }

        if (mbps > 0) return baseSpeed + Math.min(0.06, mbps * 0.003)
        return baseSpeed
      })
    }

    if (typeof g.linkDirectionalParticleWidth === 'function') {
      g.linkDirectionalParticleWidth(link => {
        if (!link || typeof link !== 'object') return 2
        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }

        const speed = link.metadata?.speed || 1000
        let baseWidth = speed >= 10000 ? 3 : (speed >= 1000 ? 2 : 1.2)

        // Make heavy traffic fatter
        const width = baseWidth + Math.min(5, mbps * 0.8)
        return link.isGhostLink ? 2.5 : width
      })
    }

    if (typeof g.linkLineDash === 'function') {
      g.linkLineDash(link => {
        if (environmentMode.value === 'simulation' && severedLinks.value.has(link.id)) {
          return [4, 4]
        }
        return null
      })
    }

    if (typeof g.linkDirectionalParticleColor === 'function') {
      g.linkDirectionalParticleColor(link => {
        if (!link || typeof link !== 'object') return '#00ff9d'
        if (deceptionMode.value) return '#ff0055' // Crimson Red
        if (link.isGhostLink) return 'rgba(255, 45, 110, 0.9)' // Red laser for threats

        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }
        // Turn bright cyan or white under heavy load
        if (mbps > 10) return '#ffffff'

        let baseColor = '#00ff9d'
        if (link.protocol_type === 'MQTT') baseColor = '#00ff00'
        else if (link.protocol_type === 'Modbus') baseColor = '#ff0000'
        else if (link.protocol_type === 'QUIC') baseColor = '#a855f7'
        else if (link.protocol_type === 'TCP') baseColor = '#00e5ff'
        else if (link.protocol_type === 'HTTPS') baseColor = '#eab308'
        else if (link.protocol_type === 'DNP3') baseColor = '#ff5500'

        return baseColor
      })
    }

    // Add Telemetry Text Sprites on Links
    if (typeof g.linkThreeObjectExtend === 'function') {
      g.linkThreeObjectExtend(true)
      g.linkThreeObject(link => {
        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }

        const speed = link.metadata?.speed || 1000
        const medium = link.metadata?.medium || 'wired'
        const duplex = link.metadata?.duplex || 'full'

        let icon = '🔌'
        if (medium === 'wireless') icon = '📶'
        if (medium === 'bluetooth') icon = '🛜' // Or bluetooth char

        const speedStr = speed >= 1000 ? `${speed/1000}G` : `${speed}M`
        const dupStr = duplex === 'full' ? 'FDX' : (duplex === 'half' ? 'HDX' : 'SPX')

        // Display both the static info and real-time speed if active
        let text = `${icon} ${speedStr} ${dupStr}`
        if (mbps > 0.05) {
          text += ` | ${mbps.toFixed(1)} Mbps`
        }
        if (link.protocol_type) {
          text += ` | ${link.protocol_type}`
        }

        const sprite = new SpriteText(text)

        if (link.protocol_type === 'MQTT') sprite.color = '#00ff00'
        else if (link.protocol_type === 'Modbus') sprite.color = '#ff0000'
        else if (link.protocol_type === 'QUIC') sprite.color = '#a855f7'
        else if (link.protocol_type === 'TCP') sprite.color = '#00e5ff'
        else if (link.protocol_type === 'HTTPS') sprite.color = '#eab308'
        else if (link.protocol_type === 'DNP3') sprite.color = '#ff5500'
        else sprite.color = medium === 'wireless' ? '#00e5ff' : (medium === 'bluetooth' ? '#0064ff' : '#00ff9d')

        sprite.textHeight = 2.5
        sprite.padding = 1.5
        sprite.backgroundColor = 'rgba(0,0,0,0.7)'
        sprite.borderRadius = 3
        return sprite
      })
      g.linkPositionUpdate((sprite, { start, end }) => {
        if (sprite && sprite.position) {
          const middlePos = Object.assign(...['x', 'y', 'z'].map(c => ({
            [c]: start[c as keyof typeof start] + (end[c as keyof typeof end] - start[c as keyof typeof start]) / 2
          })))
          Object.assign(sprite.position, middlePos)

          // Hover the text slightly above the line
          sprite.position.y += 3
        }
        return false // don't block default link positioning
      })
    }

    // 7. Interactive Event Handlers
    if (typeof g.onNodeClick === 'function') {
      g.onNodeClick(node => {
        if (!node) return
        const id = typeof node === 'object' ? node.id as string : node as string

        if (mode.value === 'draw') {
          if (!drawSource.value) {
            drawSource.value = id
            updateGraph()
          } else {
            if (drawSource.value !== id) {
              store.createLink(drawSource.value, id)
            }
            drawSource.value = null
            updateGraph()
          }
        } else {
          store.select(id)
        }
      })
    }

    if (typeof g.onBackgroundClick === 'function') {
      g.onBackgroundClick(() => {
        closeCtx()
        if (mode.value === 'draw') {
          drawSource.value = null
          updateGraph()
        } else {
          store.select(null)
        }
      })
    }

    if (typeof g.onNodeRightClick === 'function') {
      g.onNodeRightClick((node: any, event: MouseEvent) => {
        if (!node) return
        event.preventDefault?.()
        let x = event.clientX
        let y = event.clientY
        const menuWidth = 220
        const menuHeight = 200
        if (x + menuWidth > window.innerWidth) x = window.innerWidth - menuWidth - 10
        if (y + menuHeight > window.innerHeight) y = window.innerHeight - menuHeight - 10
        ctxMenu.value = {
          show: true,
          x,
          y,
          targetId: node.id as string,
          name: node.name || node.id,
          type: 'node'
        }
      })
    }

    if (typeof g.onLinkRightClick === 'function') {
      g.onLinkRightClick((link: any, event: MouseEvent) => {
        if (!link) return
        event.preventDefault?.()
        let x = event.clientX
        let y = event.clientY
        const menuWidth = 220
        const menuHeight = 200
        if (x + menuWidth > window.innerWidth) x = window.innerWidth - menuWidth - 10
        if (y + menuHeight > window.innerHeight) y = window.innerHeight - menuHeight - 10
        ctxMenu.value = {
          show: true,
          x,
          y,
          targetId: link.id as string,
          name: 'Link ' + link.id,
          type: 'link'
        }
      })
    }

    // 8. Camera Position & View Initialization
    if (typeof g.cameraPosition === 'function') {
      g.cameraPosition({ x: 0, y: 0, z: 800 })
    }

    // 9. Auto-Resize Observer
    resizeObserver = new ResizeObserver(() => {
      if (canvasRef.value && g) {
        const width = canvasRef.value.clientWidth
        const height = canvasRef.value.clientHeight
        if (typeof g.width === 'function') g.width(width)
        if (typeof g.height === 'function') g.height(height)
        if (bloomPass) {
          bloomPass.resolution.set(width, height)
        }
      }
    })
    resizeObserver.observe(canvasRef.value)

    // 10. Post-processing Composer (Bloom)
    if (typeof g.postProcessingComposer === 'function') {
      const composer = g.postProcessingComposer()
      bloomPass = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 1.5, 0.4, 0.85)
      bloomPass.threshold = 0.1
      bloomPass.strength = enableBloom.value ? 2.5 : 0  // Make it glow strongly
      bloomPass.radius = 0.8
      composer.addPass(bloomPass)
    }

    if (typeof g.onEngineTick === 'function') {
      g.onEngineTick(() => {
        if (environmentMode.value !== 'simulation') return
        if (!nexusHeader || !nexusData0 || !nexusData1) return

        const activeIndex = Atomics.load(nexusHeader, 0)
        const data = activeIndex === 0 ? nexusData0 : nexusData1

        g.graphData().nodes.forEach((node: any) => {
          const idx = nexusNodeMap.get(node.id)
          if (idx !== undefined) {
            const offset = idx * 4
            node.fx = data[offset]
            node.fy = data[offset + 1]
            node.fz = data[offset + 2]
          }
        })
      })
    }

    graph = g

    // Start continuous 3D rendering animation loop
    startAnimationLoop()
  } catch (err: any) {
    initError.value = String(err)
    console.error("ForceGraph3D initialization error:", err)
  }
}

let lastStructureSig = ''

// Re-apply visual accessors so link/node state (active, colour, particles)
// updates without calling graphData() — which would reheat the force
// simulation and let repulsion push the nodes further apart every refresh.
function refreshVisuals() {
  if (!graph) return
  for (const fn of ['linkColor', 'linkWidth', 'linkDirectionalParticles',
                    'linkDirectionalParticleSpeed', 'linkDirectionalParticleColor']) {
    if (typeof (graph as any)[fn] === 'function') (graph as any)[fn]((graph as any)[fn]())
  }
}

function updateGraph() {
  if (!graph) return
  try {
    const data = getGraphData()  // also mutates cached node/link objects in place
    debugStats.value = { nodes: data.nodes.length, links: data.links.length }
    const sig = data.nodes.map((n: any) => n.id).sort().join(',') + '|'
              + data.links.map((l: any) => l.id).sort().join(',')
    if (sig === lastStructureSig) {
      // Structure unchanged — just refresh visuals, don't reheat the layout.
      refreshVisuals()
      return
    }
    lastStructureSig = sig
    if (typeof graph.graphData === 'function') {
      graph.graphData(data)
    }
  } catch (err) {
    console.error("updateGraph failed:", err)
    initError.value = "Runtime Graph Sync Failure: " + String(err)
  }
}

function fit() {
  try {
    if (graph && typeof graph.zoomToFit === 'function') {
      graph.zoomToFit(1000, 50)
    } else {
      console.warn("zoomToFit not supported or graph not initialized")
    }
  } catch (e) {
    console.error("zoomToFit failed:", e)
  }
}

watch(() => store.nodeList, () => {
  updateGraph()
}, { deep: true })

watch(() => store.links, () => {
  updateGraph()
}, { deep: true })

watch(() => store.selectedId, () => {
  updateGraph()
})

// Recompute visuals when selection changes
watch(() => store.selectedId, () => {
  updateVisualState()
})

// Recompute link/node state when connection status changes (connect/disconnect)
watch(() => store.connections, () => {
  updateVisualState()
}, { deep: true })

watch(() => store.isolatedNodes, () => {
  updateVisualState()
}, { deep: true })

// Watch telemetry to update graph
watch(telemetryData, () => {
  if (graph) {
    // Trigger a re-evaluation of link particles and objects
    if (typeof graph.linkDirectionalParticles === 'function') {
      graph.linkDirectionalParticles(graph.linkDirectionalParticles())
    }
  }
}, { deep: true })

onMounted(() => {
  fetchCaptures()
  captureInterval = setInterval(fetchCaptures, 3000)

  store.refresh().then(() => {
    initGraph()
    updateGraph()
  }).catch(e => {
    initError.value = String(e)
  })

  // Start WS for legacy JSON telemetry (vitals, etc.)
  let wsUrl = `${wsBase()}/ws/telemetry${wsTokenParam()}`
  telemetryWs = new WebSocket(wsUrl)
  telemetryWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'init') {
        telemetryData.value = data.cache || {}
      } else if (data.type === 'bulk_update') {
        if (!telemetryData.value[data.node_id]) {
          telemetryData.value[data.node_id] = {}
        }
        for (const update of data.updates) {
          telemetryData.value[data.node_id][update.interface] = update
        }
        throttledRefreshVisuals()
      } else if (data.type === 'update') {
        if (!telemetryData.value[data.node_id]) {
          telemetryData.value[data.node_id] = {}
        }
        telemetryData.value[data.node_id][data.interface] = data
        throttledRefreshVisuals()
      } else if (data.type === 'vitals') {
        nodeVitals.value[data.node_id] = {
          cpu: data.cpu, ram: data.ram, net_tx: data.net_tx, net_rx: data.net_rx,
        }
      } else if (data.type === 'reach') {
        nodeReach.value[data.node_id] = { reachable: data.reachable, latency_ms: data.latency_ms }
        refreshVisuals()
      } else if (data.type === 'event' && data.severity === 'critical') {
        triggerShockwave()
      }
    } catch (e) {}
  }

  // Start Nexus Engine Web Worker (Binary Telemetry)
  try {
    const maxNodes = 10000;
    const floatsPerNode = 4;
    const sab = new SharedArrayBuffer(4 + maxNodes * floatsPerNode * 4 * 2);

    nexusHeader = new Int32Array(sab, 0, 1);
    nexusData0 = new Float32Array(sab, 4, maxNodes * floatsPerNode);
    nexusData1 = new Float32Array(sab, 4 + maxNodes * floatsPerNode * 4, maxNodes * floatsPerNode);

    telemetryWorker = new Worker(new URL('../workers/telemetryWorker.js', import.meta.url), { type: 'module' });

    telemetryWorker.postMessage({
      type: 'init',
      wsUrl: `${wsBase()}/ws/nexus`,
      token: wsTokenParam().replace('?token=', ''),
      buffer: sab,
      maxNodes
    });

    telemetryWorker.onmessage = (e) => {
      if (e.data.type === 'node_map') {
        nexusNodeMap = new Map(e.data.map);
      }
    };
  } catch (err) {
    console.error("Failed to initialize Nexus Worker (Check Cross-Origin Headers):", err);
  }
})

onUnmounted(() => {
  if (captureInterval) clearInterval(captureInterval)
  stopAnimationLoop()
  if (resizeObserver) resizeObserver.disconnect()
  if (telemetryWs) telemetryWs.close()
  if (telemetryWorker) telemetryWorker.terminate()
  if (graph && canvasRef.value) {
    canvasRef.value.innerHTML = ''
  }
})
</script>

<style scoped>
.topology-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: radial-gradient(circle at center, #0a1120 0%, #020305 100%);
  overflow: hidden;
  border: 2px solid transparent;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.topology-container.simulation-branch {
  border-color: rgba(147, 51, 234, 0.6); /* Purple holographic border */
  box-shadow: inset 0 0 50px rgba(147, 51, 234, 0.15);
}

.cy-canvas {
  width: 100%;
  height: 100%;
  z-index: 1;
  position: absolute;
  top: 0;
  left: 0;
}

.topology-toolbar {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toolbar-group {
  display: flex;
  gap: 1px;
  background: var(--border);
  padding: 1px;
  border-radius: var(--r);
  overflow: hidden;
  border: 1px solid var(--border);
  backdrop-filter: blur(10px);
}

.btn-tool {
  background: rgba(12, 18, 32, 0.8);
  border: none;
  color: var(--text);
  padding: 8px 12px;
  font-family: var(--font-hd);
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.btn-tool:hover {
  background: var(--bg3);
  color: var(--textwh);
}

.btn-tool.active {
  background: var(--bg4);
  color: var(--cyan);
  box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.1);
}

.btn-discover {
  color: var(--green);
}

.btn-discover:hover:not(:disabled) {
  color: var(--green);
  box-shadow: inset 0 0 10px rgba(0, 255, 157, 0.1);
}

.btn-discover:disabled {
  opacity: 0.5;
  cursor: wait;
}

.btn-gns3 {
  color: var(--purple);
}

.btn-gns3:hover:not(:disabled) {
  color: var(--purple);
  box-shadow: inset 0 0 10px rgba(168, 85, 247, 0.1);
}

.toolbar-info {
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid var(--cyan-d);
  color: var(--cyan);
  padding: 6px 12px;
  font-size: 10px;
  font-family: var(--font-co);
  border-radius: var(--r);
  animation: pulse 2s infinite;
  backdrop-filter: blur(5px);
}

@keyframes pulse {
  0% { opacity: 0.8; }
  50% { opacity: 1; }
  100% { opacity: 0.8; }
}

.debug-stats {
  background: rgba(255, 0, 0, 0.2);
  border: 1px solid red;
  color: red;
  padding: 4px 8px;
  font-family: monospace;
  font-size: 10px;
}

.debug-stats.offline {
  background: rgba(255, 190, 11, 0.1);
  border: 1px dashed #ffbe0b;
  color: #ffbe0b;
}

.shockwave {
  position: absolute; inset: 0; z-index: 11; pointer-events: none;
  background: radial-gradient(circle at 50% 50%, transparent 0%, rgba(255,45,110,0.25) 100%);
  animation: shock 1.5s ease-out forwards;
}
@keyframes shock {
  0% { opacity: 0; box-shadow: inset 0 0 0 rgba(255,45,110,0.9); }
  12% { opacity: 1; box-shadow: inset 0 0 120px 10px rgba(255,45,110,0.7); }
  100% { opacity: 0; box-shadow: inset 0 0 200px 40px rgba(255,45,110,0); }
}

.reach-panel {
  position: absolute; top: 20px; right: 20px; z-index: 12;
  width: 230px; max-height: 60%; overflow-y: auto;
  background: rgba(10, 16, 30, 0.92); border: 1px solid var(--border);
  border-radius: var(--r); backdrop-filter: blur(8px); padding: 6px;
  font-family: var(--font-co);
}
.reach-head {
  display: flex; justify-content: space-between; align-items: center;
  font-family: var(--font-hd); font-size: 10px; letter-spacing: 1px;
  color: var(--cyan); padding: 4px 6px 8px; border-bottom: 1px solid var(--border);
}
.reach-close { background: none; border: none; color: #888; font-size: 16px; cursor: pointer; line-height: 1; }
.reach-close:hover { color: var(--pink); }
.reach-row {
  display: flex; align-items: center; gap: 8px; padding: 6px;
  font-size: 11px; color: var(--textwh); cursor: pointer; border-radius: 4px;
}
.reach-row:hover { background: rgba(0, 229, 255, 0.08); }
.reach-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.reach-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.reach-lat { color: var(--text); font-size: 10px; }
.reach-empty { padding: 10px; color: var(--text); font-size: 11px; }

.ctx-backdrop { position: fixed; inset: 0; z-index: 49; }
.ctx-menu {
  position: fixed;
  z-index: 50;
  min-width: 220px;
  background: rgba(10, 16, 30, 0.97);
  border: 1px solid var(--cyan-d);
  border-radius: var(--r);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), 0 0 16px rgba(0, 229, 255, 0.15);
  padding: 4px;
  backdrop-filter: blur(6px);
  font-family: var(--font-co);
}
.ctx-title {
  padding: 6px 10px; font-size: 11px; color: var(--cyan);
  border-bottom: 1px solid var(--border); margin-bottom: 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ctx-item {
  display: block; width: 100%; text-align: left;
  background: none; border: none; color: var(--textwh);
  padding: 8px 10px; font-size: 12px; cursor: pointer; border-radius: 4px;
  font-family: var(--font-co);
}
.ctx-item:hover { background: rgba(0, 229, 255, 0.12); }
.ctx-item.ok:hover { background: rgba(0, 255, 157, 0.12); color: var(--green); }
.ctx-item.warn:hover { background: rgba(255, 45, 110, 0.12); color: var(--pink); }
.ctx-note { padding: 8px 10px; font-size: 11px; color: var(--text); font-style: italic; }

.init-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(18, 2, 2, 0.95);
  border: 2px solid #ff2d6e;
  box-shadow: 0 0 30px rgba(255, 45, 110, 0.4);
  color: #ff2d6e;
  padding: 24px;
  border-radius: var(--r2);
  z-index: 100;
  font-family: var(--font-co);
  max-width: 80%;
  text-align: center;
  backdrop-filter: blur(10px);
}

.init-error h3 {
  margin-top: 0;
  font-family: var(--font-hd);
  letter-spacing: 2px;
}

.init-error p {
  color: var(--text);
  font-size: 12px;
  margin: 12px 0 20px 0;
}
.btn-tool:focus-visible, .layer-toggle:focus-within {
  outline: 2px solid var(--cyan);
  outline-offset: 2px;
}

.reach-row:focus-visible {
  outline: 2px solid var(--cyan);
  outline-offset: -2px;
}

.btn-close-modal:focus-visible, .reach-close:focus-visible {
  outline: 2px solid var(--pink);
  outline-offset: 2px;
}

.reach-row.active {
  background: rgba(0, 229, 255, 0.15);
  border-left: 2px solid var(--cyan);
  z-index: 50;
}

.ai-incident-card {
  position: absolute;
  top: 80px;
  right: 20px;
  width: 350px;
  background: rgba(10, 12, 18, 0.95);
  border: 1px solid var(--pink);
  border-radius: 4px;
  z-index: 1000;
  box-shadow: 0 0 20px rgba(255, 45, 110, 0.3);
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(10px);
}

.ai-header {
  background: rgba(255, 45, 110, 0.15);
  border-bottom: 1px solid rgba(255, 45, 110, 0.3);
  padding: 10px 15px;
  font-weight: 600;
  color: var(--pink);
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-body {
  padding: 15px;
}

.ai-actions {
  margin-top: 15px;
}
.graph-overlay {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

/* XAI Event Feed */
.xai-event-feed {
  position: absolute;
  bottom: 120px;
  right: 20px;
  width: 350px;
  max-height: 250px;
  background: rgba(10, 12, 18, 0.85);
  border: 1px solid var(--cyan);
  border-radius: 4px;
  z-index: 1000;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.2);
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(8px);
}
.xai-header {
  background: rgba(0, 229, 255, 0.15);
  border-bottom: 1px solid rgba(0, 229, 255, 0.3);
  padding: 8px 12px;
  font-weight: 600;
  color: var(--cyan);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.xai-body {
  padding: 10px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.xai-event {
  font-family: monospace;
  font-size: 12px;
  line-height: 1.3;
}
.xai-time {
  color: var(--pink);
  margin-right: 6px;
}
.xai-text {
  color: #ccc;
}

/* Chronos DVR Scrubber */
.chronos-scrubber {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  width: 500px;
  background: rgba(10, 12, 18, 0.85);
  border: 1px solid var(--pink);
  border-radius: 4px;
  z-index: 1000;
  padding: 10px 20px;
  box-shadow: 0 0 20px rgba(255, 45, 110, 0.3);
  backdrop-filter: blur(10px);
  text-align: center;
}
.scrubber-label {
  color: var(--cyan);
  font-weight: bold;
  font-family: monospace;
  margin-bottom: 8px;
  font-size: 14px;
}
.time-display {
  color: #fff;
}
.scrubber-input {
  width: 100%;
  appearance: none;
  background: rgba(255, 45, 110, 0.2);
  height: 4px;
  border-radius: 2px;
  outline: none;
}
.scrubber-input::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  background: var(--pink);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 10px var(--pink);
}

.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.packet-captures-widget {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 12;
  width: 250px;
  max-height: 40%;
  overflow-y: auto;
  background: rgba(10, 16, 30, 0.92);
  border: 1px solid var(--border);
  border-radius: var(--r);
  backdrop-filter: blur(8px);
  padding: 8px;
  font-family: var(--font-co);
}
.pc-head {
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--cyan);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 6px;
  letter-spacing: 1px;
}
.pc-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border);
  border-radius: 4px;
  margin-bottom: 4px;
}
.pc-info {
  display: flex;
  flex-direction: column;
}
.pc-target {
  color: var(--textwh);
  font-size: 11px;
  word-break: break-all;
}
.pc-details {
  color: var(--text);
  font-size: 10px;
}
.btn-stop-capture {
  background: rgba(255, 45, 110, 0.15);
  color: var(--pink);
  border: 1px solid var(--pink);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 10px;
  transition: all 0.2s;
  white-space: nowrap;
  margin-left: 8px;
}
.btn-stop-capture:hover {
  background: rgba(255, 45, 110, 0.3);
}

@media (max-width: 768px) {
  .topology-toolbar {
    top: 10px;
    left: 10px;
    right: 10px;
    flex-direction: row;
    flex-wrap: wrap;
  }
  .reach-panel {
    top: auto;
    bottom: 20px;
    left: 10px;
    right: 10px;
    width: auto;
    max-height: 40%;
  }
}
</style>
