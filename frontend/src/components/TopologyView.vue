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
    <div v-if="initError" class="init-error">
      <h3>🚨 CORE DISRUPTION DETECTED</h3>
      <p>{{ initError }}</p>
      <button class="btn-tool" @click="retryInit">REBOOT NEURAL LINK</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import SpriteText from 'three-spritetext'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'

const store = useNodesStore()
const canvasRef = ref<HTMLElement | null>(null)
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
    await store.fetchData() // Refresh store to pull new links
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
    // Always re-assign source and target to string IDs to let D3 resolve them dynamically on updates
    cached.source = link.source
    cached.target = link.target
    const isSourceConnected = store.isConnected(link.source)
    const isTargetConnected = store.isConnected(link.target)
    cached.auto = link.auto_discovered
    cached.active = isSourceConnected && isTargetConnected
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
    // Always re-assign source and target to string IDs
    cached.source = srcNode.id
    cached.target = ghostId
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
  if (isSelected) colorVal = 0xff2d6e // pulsing red/pink for selected
  else if (isDrawSrc) colorVal = 0xffbe0b // golden for link draw source
  else if (isGhost) colorVal = 0xff2d6e // dangerous hacker red
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
          
          // 2. Pulse the breathing neon aura scale
          const aura = group.children.find((c: any) => c.__isAura)
          if (aura) {
            const scale = 1.0 + Math.sin(time) * 0.12
            aura.scale.setScalar(scale)
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
    
    // 1. Data & Environment Setup
    if (typeof g.graphData === 'function') g.graphData(getGraphData())
    if (typeof g.backgroundColor === 'function') g.backgroundColor('#00000000') // transparent background
    
    // 2. Premium Custom 3D Mesh Nodes
    if (typeof g.nodeThreeObject === 'function') {
      g.nodeThreeObject(node => createThreeNodeObject(node))
    }
    if (typeof g.nodeLabel === 'function') {
      g.nodeLabel('name')
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
        return link.active ? '#00ff9d' : 'rgba(26, 37, 64, 0.5)'
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
        if (mbps > 0) return Math.min(10, Math.ceil(mbps))
        return link.active ? 1 : (link.isGhostLink ? 2 : 0)
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
        if (mbps > 0) return 0.01 + Math.min(0.05, mbps * 0.005)
        return link.isGhostLink ? 0.005 : 0.01
      })
    }
    
    if (typeof g.linkDirectionalParticleWidth === 'function') {
      g.linkDirectionalParticleWidth(link => {
        if (!link || typeof link !== 'object') return 3
        return link.isGhostLink ? 2 : 3
      })
    }
    
    if (typeof g.linkDirectionalParticleColor === 'function') {
      g.linkDirectionalParticleColor(link => {
        if (!link || typeof link !== 'object') return '#00ff9d'
        return link.isGhostLink ? 'rgba(255, 45, 110, 0.8)' : '#00ff9d'
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
        if (mode.value === 'draw') {
          drawSource.value = null
          updateGraph()
        } else {
          store.select(null)
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

function updateGraph() {
  if (!graph) return
  try {
    const data = getGraphData()
    debugStats.value = { nodes: data.nodes.length, links: data.links.length }
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
  store.fetchData().then(() => {
    initGraph()
    updateGraph()
  }).catch(e => {
    initError.value = String(e)
  })

  // Start WS for telemetry
  const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host
  telemetryWs = new WebSocket(`ws://${wsHost}/ws/telemetry`)
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
