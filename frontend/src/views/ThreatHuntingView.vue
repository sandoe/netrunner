<template>
  <div class="hunting-container">
    <div class="header">
      <h2><span class="glitch-text" data-text="THREAT">THREAT</span> HUNTING</h2>
      <p class="subtitle">Netrunner Query Language (NQL) & Storyline Process Graphs</p>
    </div>

    <div class="search-box ai-box" style="margin-top: 1rem; margin-bottom: 2rem;">
      <div class="nql-indicator" style="background: var(--pink); color: white; border-right: none;">AI Co-Pilot</div>
      <input
        v-model="aiQuery"
        @keyup.enter="performAiSearch"
        type="text"
        class="cyber-input"
        style="border-color: var(--pink);"
        placeholder="e.g. 'Show me all SSH connections to the DB server'"
      >
      <button class="cyber-button primary" style="background: rgba(255, 51, 102, 0.2); color: var(--pink); border-color: var(--pink);" @click="performAiSearch" :disabled="loadingAi">
        {{ loadingAi ? 'THINKING...' : 'GENERATE CYPHER' }}
      </button>
    </div>

    <div class="search-box">
      <div class="nql-indicator">NQL</div>
      <input
        v-model="query"
        @keyup.enter="performSearch"
        type="text"
        class="cyber-input"
        placeholder="e.g. 'find process where name=bash join network where port=443 group by storyline'"
      >
      <button class="cyber-button primary" @click="performSearch" :disabled="loading">
        {{ loading ? 'COMPILING...' : 'EXECUTE NQL' }}
      </button>
    </div>

    <div class="results" v-if="results">
      <div class="stats">
        <span v-if="results.execution_time_ms">Execution Time: {{ results.execution_time_ms }} ms</span>
        <span v-if="results.parsed_ast">AST: {{ results.parsed_ast.operation.toUpperCase() }} -> {{ results.parsed_ast.target.toUpperCase() }}</span>
      </div>

      <div v-if="results?.cypher_query" class="stats" style="color: var(--pink); margin-top: 1rem; font-family: monospace; padding: 10px; background: rgba(255,51,102,0.1); border-left: 4px solid var(--pink);">
        Generated Cypher: {{ results.cypher_query }}
      </div>

      <div class="tabs">
        <button
          :class="['tab', { active: activeTab === 'graph' }]"
          @click="activeTab = 'graph'" v-if="results.storyline_graph">
          Storyline Graph
        </button>
        <button
          :class="['tab', { active: activeTab === 'alerts' }]"
          @click="activeTab = 'alerts'">
          Raw Alerts ({{ results.alerts?.length || 0 }})
        </button>
      </div>

      <div class="tab-content" v-if="activeTab === 'graph' && results.storyline_graph">
        <div class="process-graph glass-panel" style="width: 100%; height: 500px;">
          <svg ref="d3Container" class="d3-canvas" width="100%" height="100%"></svg>
        </div>
      </div>

      <div class="tab-content" v-if="activeTab === 'alerts'">
        <table v-if="results.alerts && results.alerts.length > 0">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Severity</th>
              <th>Title</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="alert in results.alerts" :key="alert.id">
              <td>{{ new Date(alert.created_at * 1000).toLocaleString() }}</td>
              <td><span :class="['badge', alert.severity]">{{ alert.severity }}</span></td>
              <td>{{ alert.title }}</td>
              <td>{{ alert.status }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="no-data">No alerts matched the NQL query.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { api } from '@/api/client'
import * as d3 from 'd3'

const query = ref('find process where name="bash" join network where port=443 group by storyline')
const loading = ref(false)
const aiQuery = ref('')
const loadingAi = ref(false)
const results = ref<any>(null)
const activeTab = ref('graph')
const d3Container = ref<SVGElement | null>(null)

const performSearch = async () => {
  if (!query.value.trim()) return
  loading.value = true
  try {
    const { data, error } = await api.req('POST', '/hunting/nql-search', { nql_query: query.value })
    if (data && data.success) {
      results.value = data
      if (data.storyline_graph) activeTab.value = 'graph'
      else activeTab.value = 'alerts'
    } else {
      alert("NQL Compilation Error: " + (error || "Unknown Error"))
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const performAiSearch = async () => {
  if (!aiQuery.value.trim()) return
  loadingAi.value = true
  try {
    const { data, error } = await api.req('POST', '/hunting/ai-cypher', { natural_language_query: aiQuery.value })
    if (data && data.success) {
      results.value = data
      activeTab.value = 'graph'
    } else {
      alert("AI Co-Pilot Error: " + (error || "Unknown Error"))
    }
  } catch (err) {
    console.error(err)
  } finally {
    loadingAi.value = false
  }
}

const renderGraph = () => {
  if (!d3Container.value || !results.value || !results.value.storyline_graph) return

  const width = d3Container.value.clientWidth || 800
  const height = d3Container.value.clientHeight || 500

  const nodes = results.value.storyline_graph.nodes.map((d: any) => Object.create(d))

  // D3 force simulation links expect source and target by node index or object ref.
  // The backend might return {source, target} referencing node IDs.
  // For the mock engine, it might just return an array of links. Let's assume nodes have id and links have source/target.
  // If not, we will map them linearly if possible.
  let links = results.value.storyline_graph.links.map((d: any, idx: number) => {
     return {
         source: d.source || (idx < nodes.length - 1 ? nodes[idx].id : nodes[0].id),
         target: d.target || (idx < nodes.length - 1 ? nodes[idx+1].id : nodes[nodes.length-1].id),
         label: d.label
     }
  })

  d3.select(d3Container.value).selectAll("*").remove()

  const svg = d3.select(d3Container.value)
    .attr("viewBox", [0, 0, width, height])

  const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(150))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))

  // Draw links
  const link = svg.append("g")
      .attr("stroke", "rgba(0, 240, 255, 0.4)")
      .attr("stroke-opacity", 0.6)
    .selectAll("line")
    .data(links)
    .join("line")
      .attr("stroke-width", 2)

  // Draw link labels
  const linkText = svg.append("g")
      .attr("fill", "#00f0ff")
      .style("font-family", "monospace")
      .style("font-size", "10px")
    .selectAll("text")
    .data(links)
    .join("text")
      .text((d: any) => d.label)

  // Draw nodes
  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
      .call(d3.drag()
        .on("start", (event, d: any) => {
           if (!event.active) simulation.alphaTarget(0.3).restart();
           d.fx = d.x; d.fy = d.y;
        })
        .on("drag", (event, d: any) => {
           d.fx = event.x; d.fy = event.y;
        })
        .on("end", (event, d: any) => {
           if (!event.active) simulation.alphaTarget(0);
           d.fx = null; d.fy = null;
        }) as any)

  // Node circles
  node.append("circle")
      .attr("r", 25)
      .attr("fill", (d: any) => {
        if(d.risk === 'critical') return 'rgba(255,51,51,0.2)'
        if(d.risk === 'high') return 'rgba(255,165,0,0.2)'
        return 'rgba(0,240,255,0.2)'
      })
      .attr("stroke", (d: any) => {
        if(d.risk === 'critical') return '#ff3333'
        if(d.risk === 'high') return '#ffa500'
        return '#00f0ff'
      })
      .attr("stroke-width", 2)

  // Node icons
  node.append("text")
      .text((d: any) => {
         if(d.type === 'process') return '⚙️'
         if(d.type === 'network') return '🌐'
         return '📦'
      })
      .attr("text-anchor", "middle")
      .attr("dy", 5)
      .attr("font-size", "20px")

  // Node labels
  node.append("text")
      .text((d: any) => d.label)
      .attr("fill", "#fff")
      .attr("text-anchor", "middle")
      .attr("dy", 40)
      .style("font-family", "monospace")
      .style("font-size", "12px")

  simulation.on("tick", () => {
    link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y)

    linkText
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2 - 5)

    node
        .attr("transform", (d: any) => `translate(${d.x},${d.y})`)
  })
}

watch([activeTab, results], () => {
  if (activeTab.value === 'graph' && results.value?.storyline_graph) {
    nextTick(() => {
      renderGraph()
    })
  }
})
</script>

<style scoped>
.hunting-container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  color: #fff;
}

.header {
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--accent-blue);
  padding-bottom: 1rem;
}
.header h2 {
  font-family: 'Orbitron', sans-serif;
  color: var(--accent-blue);
  margin: 0;
  font-size: 2rem;
}

.search-box {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.cyber-input {
  flex: 1;
  background: rgba(0, 20, 40, 0.5);
  border: 1px solid var(--accent-blue);
  color: #fff;
  padding: 1rem;
  font-size: 1.2rem;
  font-family: monospace;
  outline: none;
  border-radius: 4px;
}
.cyber-input:focus {
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
}

.stats {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.5rem;
  font-family: monospace;
  color: #00f0ff;
}

.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.tab {
  background: none;
  border: none;
  color: #888;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-family: 'Orbitron', sans-serif;
  font-size: 1.1rem;
}
.tab.active {
  color: #00f0ff;
  border-bottom: 2px solid #00f0ff;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(10, 15, 30, 0.8);
}
th, td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
th {
  color: #aaa;
  font-weight: normal;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  font-size: 0.8rem;
  text-transform: uppercase;
}
.badge.critical { background: rgba(255, 0, 0, 0.2); color: #ff3333; border: 1px solid #ff3333; }
.badge.high { background: rgba(255, 165, 0, 0.2); color: #ffa500; border: 1px solid #ffa500; }
.badge.medium { background: rgba(255, 255, 0, 0.2); color: #ffff00; border: 1px solid #ffff00; }
.badge.low { background: rgba(0, 255, 0, 0.2); color: #00ff00; border: 1px solid #00ff00; }
.badge.info { background: rgba(0, 240, 255, 0.2); color: #00f0ff; border: 1px solid #00f0ff; }

.no-data {
  padding: 2rem;
  text-align: center;
  color: #888;
  font-style: italic;
}

.process-graph {
  display: flex;
  background: rgba(10, 15, 30, 0.8);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  padding: 2rem;
  gap: 3rem;
}

.graph-nodes {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex: 1;
}

.process-node {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #333;
  border-radius: 6px;
  transition: all 0.2s;
}

.process-node:hover {
  transform: translateX(10px);
  box-shadow: -5px 0 15px rgba(0, 240, 255, 0.2);
}

.process-node.critical { border-left: 4px solid #ff3333; }
.process-node.high { border-left: 4px solid #ffa500; }
.process-node.medium { border-left: 4px solid #ffff00; }
.process-node.low { border-left: 4px solid #00f0ff; }

.node-icon {
  font-size: 1.5rem;
}

.node-label {
  font-weight: bold;
  font-family: monospace;
  font-size: 1.1rem;
}

.node-type {
  font-size: 0.8rem;
  color: #888;
  text-transform: uppercase;
}

.graph-links {
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  color: #00f0ff;
  font-family: monospace;
  font-size: 0.9rem;
  flex: 1;
}

.process-link {
  padding: 1rem;
  border-bottom: 1px dashed rgba(0, 240, 255, 0.3);
}
</style>
