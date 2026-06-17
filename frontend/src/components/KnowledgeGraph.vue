<template>
  <div class="knowledge-graph-panel">
    <div class="panel-header">
      <span class="icon">🧠</span> CYBER INTELLIGENCE MEMORY
      <div class="actions">
        <button @click="fetchGraph" class="btn btn-sm">Refresh Graph</button>
      </div>
    </div>
    
    <div class="panel-body p-0" style="position: relative; height: calc(100vh - 120px); background: #000; display: flex; flex-direction: column;">
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <span>Syncing Intelligence...</span>
      </div>
      
      <div id="3d-graph" style="flex: 1; min-height: 0;"></div>
      
      <!-- GraphRAG Interface -->
      <div class="rag-container">
        <div class="rag-chat" v-if="ragAnswer">
          <div class="rag-message ai"><strong>AI Analyst:</strong> {{ ragAnswer }}</div>
        </div>
        <div class="rag-input-area">
          <input 
            v-model="ragQuery" 
            @keyup.enter="submitQuery"
            placeholder="Ask GraphRAG (e.g. 'How can I pivot from the web server to the database?')" 
            class="rag-input" 
            :disabled="querying"
          />
          <button @click="submitQuery" class="btn btn-primary" :disabled="!ragQuery || querying">
            {{ querying ? 'Analyzing...' : 'Ask Graph' }}
          </button>
        </div>
      </div>
      
      <div v-if="selectedNode" class="node-details">
        <h3>{{ selectedNode.label || selectedNode.id }}</h3>
        <div class="detail-row" v-for="(val, key) in filterDetails(selectedNode)" :key="key">
          <span class="detail-key">{{ key }}:</span>
          <span class="detail-val">{{ val }}</span>
        </div>
        <button @click="selectedNode = null" class="btn btn-sm mt-2 w-full">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, shallowRef } from 'vue'
import { api } from '@/api/client'
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'

const loading = ref(false)
const querying = ref(false)
const ragQuery = ref('')
const ragAnswer = ref('')
const selectedNode = ref<any>(null)
const graphData = ref({ nodes: [], links: [] })
let graphInstance: any = null

const filterDetails = (node: any) => {
  const skip = ['x','y','z','vx','vy','vz','index','color','__threeObj','shape','icon']
  const res: any = {}
  for (const k in node) {
    if (!skip.includes(k) && typeof node[k] !== 'object') {
      res[k] = node[k]
    }
  }
  return res
}

const submitQuery = async () => {
  if (!ragQuery.value.trim() || querying.value) return
  
  querying.value = true
  ragAnswer.value = ''
  
  try {
    const res = await api.queryIntelligence(ragQuery.value)
    ragAnswer.value = res.answer || "No response received."
  } catch (e: any) {
    ragAnswer.value = "Error: " + e.message
  } finally {
    querying.value = false
    ragQuery.value = ''
  }
}

const initGraph = () => {
  const elem = document.getElementById('3d-graph')
  if (!elem) return

  // Use a deeply cloned copy to avoid Vue Proxy interference with Three.js
  const rawData = JSON.parse(JSON.stringify(graphData.value))

  graphInstance = ForceGraph3D()(elem)
    .graphData(rawData)
    .nodeAutoColorBy('type')
    .nodeThreeObject((node: any) => {
      // Use SpriteText for labels
      const sprite = new SpriteText(node.label || node.id)
      sprite.color = node.color || '#fff'
      sprite.textHeight = 8
      
      // If it's a specific type, we can add icons, but basic text is very readable in 3D
      if (node.type === 'Machine') sprite.color = '#00ffcc'
      else if (node.type === 'Attacker') sprite.color = '#ff0055'
      else if (node.type === 'Credential') sprite.color = '#ffcc00'
      else if (node.type === 'Event') sprite.color = '#ff8800'
      else if (['Entity', 'Episode', 'Community'].includes(node.type)) sprite.color = '#bb00ff'
      
      return sprite
    })
    .linkDirectionalArrowLength(3.5)
    .linkDirectionalArrowRelPos(1)
    .linkCurvature(0.2)
    .linkColor(() => 'rgba(255,255,255,0.2)')
    .onNodeClick((node: any) => {
      selectedNode.value = node
      // Aim at node
      const distance = 40;
      const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
      graphInstance.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
        node, // lookAt
        3000  // ms transition
      );
    })
    .backgroundColor('#050510')
}

const fetchGraph = async () => {
  loading.value = true
  try {
    const res = await api.getIntelligenceGraph()
    // Convert vis.js edges to 3d-force-graph links
    const links = (res.edges || []).map((e: any) => ({
      source: e.from,
      target: e.to,
      label: e.label
    }))
    graphData.value = { nodes: res.nodes || [], links }
    
    if (graphInstance) {
      const rawData = JSON.parse(JSON.stringify(graphData.value))
      graphInstance.graphData(rawData)
    } else {
      initGraph()
    }
  } catch (e) {
    console.error("Failed to fetch graph", e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchGraph()
  
  // Resize listener
  const handleResize = () => {
    if (graphInstance) {
      const elem = document.getElementById('3d-graph')
      if (elem) {
        graphInstance.width(elem.clientWidth).height(elem.clientHeight)
      }
    }
  }
  window.addEventListener('resize', handleResize)
  onUnmounted(() => window.removeEventListener('resize', handleResize))
})
</script>

<style scoped>
.knowledge-graph-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.panel-header {
  background: var(--surface-2);
  padding: 12px 16px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--neon-blue);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.loading-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  color: var(--neon-blue);
  font-family: var(--font-mono);
}

.node-details {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 300px;
  background: rgba(10, 10, 20, 0.85);
  backdrop-filter: blur(4px);
  border: 1px solid var(--neon-blue);
  border-radius: 8px;
  padding: 16px;
  color: #fff;
  z-index: 5;
  box-shadow: 0 0 20px rgba(0, 255, 204, 0.2);
}

.node-details h3 {
  margin: 0 0 12px 0;
  color: var(--neon-blue);
  font-family: var(--font-mono);
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 0.85rem;
}

.detail-key {
  color: #888;
}

.detail-val {
  font-family: var(--font-mono);
  max-width: 60%;
  text-align: right;
  word-break: break-all;
}

/* RAG Interface */
.rag-container {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(10, 10, 20, 0.9);
  backdrop-filter: blur(8px);
  border-top: 1px solid var(--neon-blue);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 10;
}

.rag-chat {
  max-height: 200px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  padding-bottom: 8px;
}

.rag-message {
  padding: 8px 12px;
  border-radius: 4px;
  background: rgba(0, 255, 204, 0.1);
  color: #fff;
  border-left: 3px solid var(--neon-blue);
  line-height: 1.5;
  white-space: pre-wrap;
}

.rag-input-area {
  display: flex;
  gap: 12px;
}

.rag-input {
  flex: 1;
  background: rgba(0,0,0,0.5);
  border: 1px solid var(--border-color);
  color: #fff;
  padding: 10px 16px;
  border-radius: 4px;
  font-family: var(--font-mono);
  outline: none;
}

.rag-input:focus {
  border-color: var(--neon-blue);
}
</style>
