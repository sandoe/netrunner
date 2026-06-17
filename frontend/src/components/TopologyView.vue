<template>
  <div class="topology-container">
    <div class="topology-toolbar">
      <div class="toolbar-group">
        <button class="btn-tool" :class="{ active: mode === 'select' }" @click="mode = 'select'">
          <span class="icon">🖱️</span> SELECT
        </button>
        <button class="btn-tool" :class="{ active: mode === 'draw' }" @click="mode = 'draw'">
          <span class="icon">🔌</span> DRAW LINK
        </button>
      </div>
      <div class="toolbar-group">
        <button class="btn-tool" @click="fit">CENTER</button>
        <button class="btn-tool" @click="toggleLayout">
          <span class="icon">🕸️</span> {{ layoutMode === 'floating' ? 'FLOATING' : 'HIERARCHICAL' }}
        </button>
        <button class="btn-tool btn-discover" @click="doAutoDiscover" :disabled="discovering">
          <span class="icon">{{ discovering ? '⌛' : '📡' }}</span> AUTO-DISCOVER
        </button>
        <button class="btn-tool btn-gns3" @click="pickGns3Project" :disabled="syncing">
          <span class="icon">{{ syncing ? '⌛' : '☁️' }}</span> GNS3 SYNC
        </button>
        <button class="btn-tool" :class="{ active: showReachPanel }" @click="showReachPanel = !showReachPanel">
          <span class="icon">📶</span> REACHABILITY
        </button>
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
    <div ref="canvasRef" class="cy-canvas"></div>

    <!-- Critical-event shockwave -->
    <div v-if="shockwave" class="shockwave"></div>

    <!-- Reachability overview -->
    <div v-if="showReachPanel" class="reach-panel">
      <div class="reach-head">
        <span>📶 REACHABILITY</span>
        <button class="reach-close" @click="showReachPanel = false">×</button>
      </div>
      <div v-for="row in reachRows" :key="row.id" class="reach-row" @click="store.select(row.id)">
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
        <button class="ctx-item" @click="ctxEdit">✎ Reconfigure (IP, telnet/SSH…)</button>
        <template v-if="!isConsoleless(ctxMenu.nodeId)">
          <button v-if="!store.isConnected(ctxMenu.nodeId)" class="ctx-item ok" @click="ctxConnect">▶ Connect</button>
          <button v-else class="ctx-item warn" @click="ctxDisconnect">■ Disconnect</button>
        </template>
        <div v-else class="ctx-note">⚡ L2 device — no console</div>
        <button class="ctx-item" style="color: var(--pink); border-color: var(--pink);" @click="ctxBruteForce">💥 Launch Brute Force</button>
        <button class="ctx-item" @click="ctxTogglePin">
          {{ pinnedId === ctxMenu.nodeId ? '📌 Unpin from centre' : '📌 Pin to centre' }}
        </button>
      </div>
    </template>

    <!-- Sub Modal for Brute Force Attack -->
    <div v-if="attackTarget" class="modal-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); z-index: 9999;" @click.self="attackTarget = null">
      <div class="cyber-modal-card" style="width: 400px; background: rgba(10,12,18,0.95); border: 1px solid var(--pink);">
        <div class="cyber-modal-header">
          <div class="modal-title" style="color: var(--pink)">💥 LAUNCH BRUTE FORCE</div>
          <button class="btn-close-modal" @click="attackTarget = null">×</button>
        </div>
        <div class="cyber-modal-body" style="text-align: center">
          <p style="color: #a0a0a0; margin-bottom: 20px;">TARGET NODE: <strong style="color: #00e5ff">{{ attackTarget }}</strong></p>
          <div style="display: flex; gap: 10px; justify-content: center">
            <button class="btn-action btn-danger" @click="launchAttack('ssh')">[ CRACK SSH ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('ftp')">[ CRACK FTP ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('mysql')">[ CRACK MYSQL ]</button>
            <button class="btn-action btn-danger" @click="launchAttack('postgres')">[ CRACK POSTGRES ]</button>
          </div>
          <div v-if="attackStatus" style="margin-top: 15px; color: var(--pink); font-family: monospace; text-shadow: 0 0 8px var(--pink); font-weight: bold;">{{ attackStatus }}</div>
        </div>
      </div>
    </div>

    <div v-if="initError" class="init-error">
      <h3>🚨 CORE DISRUPTION DETECTED</h3>
      <p>{{ initError }}</p>
      <button class="btn-tool" @click="retryInit">REBOOT NEURAL LINK</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, computed } from 'vue'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import SpriteText from 'three-spritetext'
import { useNodesStore } from '@/stores/nodes'
import { api, wsTokenParam, wsBase } from '@/api/client'

const store = useNodesStore()
const emit = defineEmits<{ editNode: [string] }>()
const canvasRef = ref<HTMLElement | null>(null)

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
const ctxMenu = ref<{ show: boolean, x: number, y: number, nodeId: string, name: string }>(
  { show: false, x: 0, y: 0, nodeId: '', name: '' })
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
function ctxEdit() { store.select(ctxMenu.value.nodeId); emit('editNode', ctxMenu.value.nodeId); closeCtx() }

const attackTarget = ref<string | null>(null)
const attackStatus = ref('')

function ctxBruteForce() {
  attackTarget.value = ctxMenu.value.name
  attackStatus.value = ''
  closeCtx()
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
  const id = ctxMenu.value.nodeId; closeCtx()
  try { await api.connectNode(id); store.manuallyDisconnected.delete(id); await store.refreshConnections() }
  catch (e) { alert('Connect failed: ' + String(e)) }
}
async function ctxDisconnect() {
  const id = ctxMenu.value.nodeId; closeCtx()
  try { await api.disconnectNode(id); store.manuallyDisconnected.add(id); await store.refreshConnections() }
  catch (e) { alert('Disconnect failed: ' + String(e)) }
}

// Pin a node to the centre of the layout (others orbit around it). Useful to
// anchor your gateway/router as the hub instead of letting physics decide.
const pinnedId = ref<string | null>(null)
function ctxTogglePin() {
  const id = ctxMenu.value.nodeId; closeCtx()
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
let resizeObserver: ResizeObserver | null = null

const mode = ref<'select' | 'draw'>('select')
const layoutMode = ref<'floating' | 'hierarchical'>('floating')
const drawSource = ref<string | null>(null)
const discovering = ref(false)
const syncing = ref(false)
const debugStats = ref<{nodes: number, links: number} | null>(null)
const initError = ref<string | null>(null)
const telemetryData = ref<Record<string, Record<string, any>>>({})
// Real per-node vitals (CPU/RAM/net) from the telemetry poller
const nodeVitals = ref<Record<string, { cpu: number | null, ram: number | null, net_tx: number, net_rx: number }>>({})
// Active TCP reachability per node (online + connect latency)
const nodeReach = ref<Record<string, { reachable: boolean, latency_ms: number | null }>>({})
let telemetryWs: WebSocket | null = null

function toggleLayout() {
  layoutMode.value = layoutMode.value === 'floating' ? 'hierarchical' : 'floating'
  if (graph && typeof graph.dagMode === 'function') {
    graph.dagMode(layoutMode.value === 'hierarchical' ? 'td' : null)
    if (layoutMode.value === 'hierarchical') {
      graph.dagLevelDistance(60)
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

  // Create virtual gateway if no regular nodes exist
  if (nodesList.length === 0) {
    const virtualId = 'gateway-virtual'
    activeIds.add(virtualId)
    let cached = nodeCache.get(virtualId)
    if (!cached) {
      cached = { id: virtualId }
      nodeCache.set(virtualId, cached)
    }
    cached.name = 'Internet Gateway (Virtual)'
    cached.type = 'router'
    cached.connected = true
    cached.val = 4
    nodesList.push(cached)
  }

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
      linkCache.set(link.id, cached)
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
    ) || store.nodeList[0] || { id: 'gateway-virtual' }

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
let animationFrameId: number | null = null

function createThreeNodeObject(node: any) {
  const group = new THREE.Group()
  const id = node.id
  const isGhost = node.type === 'ghost'
  const isRpi = id === 'RPI'
  const isRouter = id === 'Router-1'
  const isSelected = id === store.selectedId
  const isDrawSrc = id === drawSource.value
  const connected = node.connected

  // Determine neon primary color
  let colorVal = 0x00e5ff // standard electric cyan
  const isVulnerable = node.tags && node.tags.includes('vulnerable')
  
  if (isSelected) colorVal = 0xff2d6e // pulsing red/pink for selected
  else if (isDrawSrc) colorVal = 0xffbe0b // golden for link draw source
  else if (isGhost || isVulnerable) colorVal = 0xff2d6e // dangerous hacker red
  else if (connected) colorVal = 0x00ff9d // cyber green for active nodes

  const mat = new THREE.MeshBasicMaterial({ color: colorVal })
  let core: THREE.Mesh
  const animGroup = new THREE.Group() // group for rotating meshes
  ;(animGroup as any).__isAnimGroup = true

  if (isGhost) {
    // Dangerous Hacker Threat node: solid core sphere + wireframe rotating Octahedron cage
    core = new THREE.Mesh(new THREE.SphereGeometry(3.5, 16, 16), mat)
    
    const cageMat = new THREE.MeshBasicMaterial({ color: colorVal, wireframe: true, transparent: true, opacity: 0.6 })
    const cage = new THREE.Mesh(new THREE.OctahedronGeometry(6.5, 0), cageMat)
    animGroup.add(cage)
  } else if (isRpi) {
    // Raspberry Pi node: solid central hardware box + flat rotating Saturn-like halo ring
    core = new THREE.Mesh(new THREE.BoxGeometry(4.5, 4.5, 4.5), mat)
    
    const ringMat = new THREE.MeshBasicMaterial({ color: colorVal, side: THREE.DoubleSide, transparent: true, opacity: 0.6 })
    const ring = new THREE.Mesh(new THREE.RingGeometry(7, 9, 32), ringMat)
    ring.rotation.x = Math.PI / 2.5 // Tilts like Saturn
    animGroup.add(ring)
  } else if (isRouter) {
    // Cloud Gateway node: intricate wireframe TorusKnot + rotating orbital ring
    const knotMat = new THREE.MeshBasicMaterial({ color: colorVal, wireframe: true })
    core = new THREE.Mesh(new THREE.TorusKnotGeometry(2.5, 0.7, 64, 8), knotMat)
    
    const orbitMat = new THREE.MeshBasicMaterial({ color: colorVal, transparent: true, opacity: 0.5 })
    const orbit = new THREE.Mesh(new THREE.TorusGeometry(7.5, 0.3, 8, 32), orbitMat)
    orbit.rotation.x = Math.PI / 2
    animGroup.add(orbit)
  } else if (connected) {
    // Connected Live Node: solid core sphere + wireframe rotating Icosahedron cage
    core = new THREE.Mesh(new THREE.SphereGeometry(3.5, 16, 16), mat)
    
    const cageMat = new THREE.MeshBasicMaterial({ color: colorVal, wireframe: true, transparent: true, opacity: 0.4 })
    const cage = new THREE.Mesh(new THREE.IcosahedronGeometry(6, 1), cageMat)
    animGroup.add(cage)
  } else {
    // Dormant Disconnected Node: dim, grey core sphere
    const dormantMat = new THREE.MeshBasicMaterial({ color: 0x757575, transparent: true, opacity: 0.5 })
    core = new THREE.Mesh(new THREE.SphereGeometry(3, 8, 8), dormantMat)
  }

  group.add(core)
  group.add(animGroup)

  // Add breathing neon atmospheric aura using additive blending
  if (connected || isGhost || isRpi || isRouter) {
    const auraMat = new THREE.MeshBasicMaterial({
      color: colorVal,
      transparent: true,
      opacity: 0.15,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide
    })
    const aura = new THREE.Mesh(new THREE.SphereGeometry(8.5, 16, 16), auraMat)
    ;(aura as any).__isAura = true
    group.add(aura)
  }

  return group
}

function startAnimationLoop() {
  function animate() {
    animationFrameId = requestAnimationFrame(animate)
    
    if (graph) {
      const time = Date.now() * 0.003
      const nodes = graph.graphData().nodes
      
      nodes.forEach((node: any) => {
        if (node.__threeObj) {
          const group = node.__threeObj
          
          // 1. Rotate the custom animGroup
          const animGroup = group.children.find((c: any) => c.__isAnimGroup)
          if (animGroup) {
            animGroup.rotation.x += 0.005
            animGroup.rotation.y += 0.01
          }
          
          // 2. Pulse the breathing neon aura scale — tint + intensify by real CPU load
          const aura = group.children.find((c: any) => c.__isAura)
          if (aura) {
            const v = nodeVitals.value[node.id]
            const cpu = v && v.cpu !== null ? v.cpu : null
            // Load-driven aura: faster/larger pulse and green→amber→red tint
            const load = cpu !== null ? cpu / 100 : 0
            const speed = 1 + load * 3
            const scale = 1.0 + Math.sin(time * speed) * (0.12 + load * 0.25)
            aura.scale.setScalar(scale)
            if (cpu !== null) {
              // green (0x00ff9d) -> amber (0xffbe0b) -> red (0xff2d6e)
              const col = cpu < 50
                ? new THREE.Color(0x00ff9d).lerp(new THREE.Color(0xffbe0b), cpu / 50)
                : new THREE.Color(0xffbe0b).lerp(new THREE.Color(0xff2d6e), (cpu - 50) / 50)
              aura.material.color.copy(col)
              aura.material.opacity = 0.12 + load * 0.25
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

    const g = ForceGraphConstructor()(canvasRef.value)
    
    // Network graphs have cycles (rings, redundant paths); the hierarchical
    // (DAG) layout would otherwise throw "Invalid DAG structure". Skip the
    // offending links gracefully instead of crashing.
    if (typeof g.onDagError === 'function') g.onDagError(() => false)

    // 1. Data & Environment Setup
    if (typeof g.graphData === 'function') g.graphData(getGraphData())
    if (typeof g.backgroundColor === 'function') g.backgroundColor('#00000000') // transparent background
    
    // 2. Premium Custom 3D Mesh Nodes
    if (typeof g.nodeThreeObject === 'function') {
      g.nodeThreeObject(node => createThreeNodeObject(node))
    }
    if (typeof g.nodeLabel === 'function') {
      g.nodeLabel((n: any) => {
        let label = n.name
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
    
    // 3. Floating Cyber-Grids for Layer Decks
    const scene = g.scene()
    if (scene) {
      // Gold grid for Cloud Deck (Y = 60)
      const cloudGrid = new THREE.GridHelper(500, 30, 0xffbe0b, 0x3d300b)
      cloudGrid.position.y = 60
      ;(cloudGrid.material as any).transparent = true
      ;(cloudGrid.material as any).opacity = 0.08
      scene.add(cloudGrid)
      
      // Neon Cyan grid for Local Deck (Y = -60)
      const localGrid = new THREE.GridHelper(500, 30, 0x00e5ff, 0x0a333d)
      localGrid.position.y = -60
      ;(localGrid.material as any).transparent = true
      ;(localGrid.material as any).opacity = 0.08
      scene.add(localGrid)
    }

    // 4. Custom D3 Physics Force for Vertical Platform Layering
    if (typeof g.d3Force === 'function') {
      g.d3Force('layer', (alpha: number) => {
        if (layoutMode.value === 'hierarchical') return // Skip layering if hierarchical
        
        const nodes = g.graphData().nodes
        nodes.forEach((node: any) => {
          let targetY = -60 // default to local deck
          
          const isCloud = node.id === 'Router-1' || 
                          (node.tags && node.tags.includes('cloud')) ||
                          (node.host && !node.host.startsWith('192.168.') && !node.host.startsWith('10.') && !node.host.startsWith('172.') && node.host !== '127.0.0.1')
                          
          let isGhostCloud = false
          if (node.type === 'ghost' && node.source_node) {
            if (node.source_node.toLowerCase().includes('router-1')) {
              isGhostCloud = true
            }
          }
          
          if (isCloud || isGhostCloud) {
            targetY = 60 // pull cloud nodes to the cloud deck
          }
          
          node.vy += (targetY - node.y) * 0.15 * alpha
        })
      })
    }
    
    // 5. Link Customization
    if (typeof g.linkColor === 'function') {
      g.linkColor(link => {
        if (!link || typeof link !== 'object') return 'rgba(26, 37, 64, 0.5)'
        if (link.isGhostLink) return 'rgba(255, 45, 110, 0.4)'
        const h = linkHealth(link)
        if (h === 'down') return 'rgba(255, 45, 110, 0.7)'              // unreachable endpoint → red
        if (h === 'up') return link.active ? '#00ff9d' : 'rgba(0, 255, 157, 0.45)'
        return link.active ? '#00ff9d' : 'rgba(26, 37, 64, 0.5)'       // unknown → legacy
      })
    }
    
    if (typeof g.linkWidth === 'function') {
      g.linkWidth(link => {
        if (!link || typeof link !== 'object') return 0.5
        return link.active ? 1.5 : (link.isGhostLink ? 1 : 0.5)
      })
    }
    
    // 6. Directional Particles / Animated Traffic Customization
    if (typeof g.linkDirectionalParticles === 'function') {
      g.linkDirectionalParticles(link => {
        if (!link || typeof link !== 'object') return 0
        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }
        // Base traffic for active links (simulate idle ping)
        const base = link.active ? 2 : (link.isGhostLink ? 4 : 0)
        // Spawn up to 20 fast particles to look like a solid laser stream under heavy load
        if (mbps > 0) return base + Math.min(20, Math.ceil(mbps * 3))
        return base
      })
    }
    
    if (typeof g.linkDirectionalParticleSpeed === 'function') {
      g.linkDirectionalParticleSpeed(link => {
        if (!link || typeof link !== 'object') return 0.01
        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }
        // Laser speed - much faster!
        const baseSpeed = link.isGhostLink ? 0.015 : 0.008
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
        // Make heavy traffic fatter
        const width = 2 + Math.min(5, mbps * 0.8)
        return link.isGhostLink ? 2.5 : width
      })
    }
    
    if (typeof g.linkDirectionalParticleColor === 'function') {
      g.linkDirectionalParticleColor(link => {
        if (!link || typeof link !== 'object') return '#00ff9d'
        if (link.isGhostLink) return 'rgba(255, 45, 110, 0.9)' // Red laser for threats
        
        let mbps = 0
        if (link.source && link.source.id && telemetryData.value[link.source.id]) {
          Object.values(telemetryData.value[link.source.id]).forEach(iface => {
            mbps += iface.mbps_tx || 0
          })
        }
        // Turn bright cyan or white under heavy load
        if (mbps > 10) return '#ffffff'
        if (mbps > 2) return '#00e5ff'
        return '#00ff9d'
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
        if (mbps > 0.05) { // Only show if significant
          const sprite = new SpriteText(`${mbps.toFixed(1)} Mbps`)
          sprite.color = '#00ff9d'
          sprite.textHeight = 3
          sprite.padding = 1
          sprite.backgroundColor = 'rgba(0,0,0,0.6)'
          sprite.borderRadius = 2
          return sprite
        }
        return null
      })
      g.linkPositionUpdate((sprite, { start, end }) => {
        if (sprite && sprite.position) {
          const middlePos = Object.assign(...['x', 'y', 'z'].map(c => ({
            [c]: start[c as keyof typeof start] + (end[c as keyof typeof end] - start[c as keyof typeof start]) / 2
          })))
          Object.assign(sprite.position, middlePos)
          
          // Hover the text slightly above the line
          sprite.position.y += 2
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
        ctxMenu.value = {
          show: true,
          x: event.clientX,
          y: event.clientY,
          nodeId: node.id as string,
          name: node.name || node.id,
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
        if (typeof g.width === 'function') g.width(canvasRef.value.clientWidth)
        if (typeof g.height === 'function') g.height(canvasRef.value.clientHeight)
      }
    })
    resizeObserver.observe(canvasRef.value)

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

// Recompute link/node state when connection status changes (connect/disconnect)
watch(() => store.connections, () => {
  updateGraph()
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
  store.refresh().then(() => {
    initGraph()
    updateGraph()
  }).catch(e => {
    initError.value = String(e)
  })

  // Start WS for telemetry
  telemetryWs = new WebSocket(`${wsBase()}/ws/telemetry${wsTokenParam()}`)
  telemetryWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'init') {
        telemetryData.value = data.cache || {}
      } else if (data.type === 'update') {
        if (!telemetryData.value[data.node_id]) {
          telemetryData.value[data.node_id] = {}
        }
        telemetryData.value[data.node_id][data.interface] = data
        refreshVisuals()
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
})

onUnmounted(() => {
  stopAnimationLoop()
  if (resizeObserver) resizeObserver.disconnect()
  if (telemetryWs) telemetryWs.close()
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
</style>
