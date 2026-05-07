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
        <button class="btn-tool" @click="runLayout">AUTO LAYOUT</button>
        <button class="btn-tool btn-discover" @click="doDiscover" :disabled="discovering">
          <span class="icon">{{ discovering ? '⌛' : '📡' }}</span> SCAN NETWORK
        </button>
        <button class="btn-tool btn-gns3" @click="pickGns3Project" :disabled="syncing">
          <span class="icon">{{ syncing ? '⌛' : '☁️' }}</span> GNS3 SYNC
        </button>
      </div>
      <div class="toolbar-info" v-if="mode === 'draw'">
        CLICK SOURCE NODE, THEN TARGET NODE TO LINK.
      </div>
    </div>
    <div ref="cyRef" class="cy-canvas"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import cytoscape from 'cytoscape'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'

const store = useNodesStore()
const cyRef = ref<HTMLElement | null>(null)
let cy: cytoscape.Core | null = null

const mode = ref<'select' | 'draw'>('select')
const drawSource = ref<string | null>(null)
const discovering = ref(false)
const syncing = ref(false)

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
        runLayout()
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
    const res = await store.discover()
    if (res.status === 'success') {
      let msg = `Scanning complete!\n\nDiscovered ${res.discovered} new links.`
      if (res.unknown_neighbors.length > 0) {
        msg += `\n\nFound ${res.unknown_neighbors.length} unknown neighbors that are not in your node list:\n`
        res.unknown_neighbors.forEach(n => {
          msg += `- ${n.name || n.ip} (detected via ${n.source_node})\n`
        })
        msg += `\nPlease add these as nodes to see them in the topology.`
      }
      alert(msg)
      runLayout()
    } else {
      alert(res.message || 'Discovery failed')
    }
  } catch (e) {
    alert(String(e))
  } finally {
    discovering.value = false
  }
}

function getElements() {
  const elements: any[] = []
  
  // Nodes
  store.nodeList.forEach(node => {
    elements.push({
      data: { 
        id: node.id, 
        label: node.name,
        type: node.device_type,
        connected: store.isConnected(node.id)
      }
    })
  })

  // Edges
  store.links.forEach(link => {
    elements.push({
      data: {
        id: link.id,
        source: link.source,
        target: link.target,
        auto: link.auto_discovered
      }
    })
  })

  return elements
}

const cyStyle: any[] = [
  {
    selector: 'node',
    style: {
      'label': 'data(label)',
      'color': '#6b7a8d',
      'font-family': 'Orbitron, sans-serif',
      'font-size': '10px',
      'text-valign': 'bottom',
      'text-margin-y': 5,
      'background-color': '#0c1220',
      'border-width': 2,
      'border-color': '#1a2540',
      'width': 30,
      'height': 30,
      'shape': 'round-rectangle',
      'overlay-opacity': 0
    }
  },
  {
    selector: 'node[connected]',
    style: {
      'border-color': '#00ff9d',
      'border-opacity': 0.8,
      'background-color': '#0c1220'
    }
  },
  {
    selector: 'node:selected',
    style: {
      'border-color': '#00e5ff',
      'border-width': 3,
      'background-color': '#101828'
    }
  },
  {
    selector: 'edge',
    style: {
      'width': 2,
      'line-color': '#1a2540',
      'curve-style': 'bezier',
      'target-arrow-shape': 'none',
      'overlay-opacity': 0
    }
  },
  {
    selector: 'edge[auto]',
    style: {
      'line-style': 'dashed',
      'line-dash-pattern': [4, 4]
    }
  }
]

function initCy() {
  if (!cyRef.value) return

  cy = cytoscape({
    container: cyRef.value,
    elements: getElements(),
    style: cyStyle,
    layout: { name: 'cose', animate: false },
    userZoomingEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: false
  })

  cy.on('tap', 'node', (evt) => {
    const node = evt.target
    const id = node.id()

    if (mode.value === 'draw') {
      if (!drawSource.value) {
        drawSource.value = id
        node.addClass('draw-source')
      } else {
        if (drawSource.value !== id) {
          store.createLink(drawSource.value, id)
        }
        drawSource.value = null
        cy?.nodes().removeClass('draw-source')
      }
    } else {
      store.select(id)
    }
  })

  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      if (mode.value === 'draw') {
        drawSource.value = null
        cy?.nodes().removeClass('draw-source')
      } else {
        store.select(null)
      }
    }
  })
}

function runLayout() {
  cy?.layout({ 
    name: 'cose', 
    animate: true,
    animationDuration: 500,
    randomize: false,
    componentSpacing: 100,
    nodeRepulsion: () => 400000,
  } as any).run()
}

function fit() {
  cy?.fit(undefined, 50)
}

watch(() => store.nodeList, () => {
  cy?.json({ elements: getElements() })
}, { deep: true })

watch(() => store.links, () => {
  cy?.json({ elements: getElements() })
}, { deep: true })

watch(() => store.selectedId, (newId) => {
  cy?.nodes().unselect()
  if (newId) {
    cy?.getElementById(newId).select()
  }
})

onMounted(() => {
  initCy()
  // Sync initial selection
  if (store.selectedId) {
    cy?.getElementById(store.selectedId).select()
  }
})

onUnmounted(() => {
  cy?.destroy()
})
</script>

<style scoped>
.topology-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: var(--bg);
}

.cy-canvas {
  width: 100%;
  height: 100%;
  z-index: 1;
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
}

.btn-tool {
  background: var(--bg2);
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
}

@keyframes pulse {
  0% { opacity: 0.8; }
  50% { opacity: 1; }
  100% { opacity: 0.8; }
}

:deep(.draw-source) {
  border-color: var(--pink) !important;
  border-width: 4px !important;
}
</style>
