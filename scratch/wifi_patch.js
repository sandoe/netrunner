const fs = require('fs')
let content = fs.readFileSync('frontend/src/components/WifiView.vue', 'utf8')

// 1. Change v-if to v-show
content = content.replace(/<div v-if="activeMode === 'single'" class="single-mode">/, `<div v-show="activeMode === 'single'" class="single-mode">`)
content = content.replace(/<div v-else-if="activeMode === 'mesh'" class="mesh-mode">/, `<div v-show="activeMode === 'mesh'" class="mesh-mode">`)
content = content.replace(/<div v-else-if="activeMode === '3d-map'" class="map3d-mode">/, `<div v-show="activeMode === '3d-map'" class="map3d-mode">`)
content = content.replace(/<div v-else-if="activeMode === 'observatory' && !isRebuildingObservatory" class="observatory-mode">/, `<div v-show="activeMode === 'observatory' && !isRebuildingObservatory" class="observatory-mode">`)

// 2. Add selectedNodeId and nodeLastSeen
const addVars = `
const selectedNodeId = ref<string>("")
const nodeLastSeen = ref<Record<string, number>>({})

const isNodeActive = (id: string) => {
  if (isSimulation.value) return true;
  return (Date.now() - (nodeLastSeen.value[id] || 0)) < 5000;
}
`
content = content.replace(/const activeMode = ref\('single'\)/, `const activeMode = ref('single')\n${addVars}`)

// 3. Update the node badge and dot to support selection and red status
// Node Badge (horizontal top)
content = content.replace(
  /<div v-for="\(node, index\) in activeNodes" :key="index" class="node-badge" :style="{ borderColor: getHexColorStr\(node.color\) }">/g,
  `<div v-for="(node, index) in activeNodes" :key="index" class="node-badge" :class="{'selected-badge': selectedNodeId === node.id}" :style="{ borderColor: isNodeActive(node.id) ? getHexColorStr(node.color) : '#ff2d6e' }" @click="selectedNodeId = node.id">`
)

content = content.replace(
  /<div class="node-badge-indicator" :style="{ background: getHexColorStr\(node.color\) }"><\/div>/g,
  `<div class="node-badge-indicator" :style="{ background: isNodeActive(node.id) ? getHexColorStr(node.color) : '#ff2d6e' }"></div>`
)

// Node Dot (sidebar)
content = content.replace(
  /<div class="node-dot" :style="{ backgroundColor: getHexColorStr\(node.color\) }"><\/div>/g,
  `<div class="node-dot" :style="{ backgroundColor: isNodeActive(node.id) ? getHexColorStr(node.color) : '#ff2d6e' }"></div>`
)

// Add selectedNode UI style to selected node item in sidebar
content = content.replace(
  /<div class="node-item" v-for="node in activeNodes" :key="node.id">/g,
  `<div class="node-item" v-for="node in activeNodes" :key="node.id" :class="{'selected-node': selectedNodeId === node.id}" @click="selectedNodeId = node.id">`
)

// 4. Update ws.onmessage
// First, update the nodeLastSeen inside ws.onmessage
content = content.replace(
  /const data = JSON\.parse\(event\.data\)/,
  `const data = JSON.parse(event.data)
      if (data.node_id) {
         nodeLastSeen.value[data.node_id.replace('beacon_', '')] = Date.now()
         nodeLastSeen.value[data.node_id] = Date.now() // Support both formats
      }
  `
)

// Second, wrap single node logic in if statement
const singleNodeLogic = `      } else {
        // Single Node CSI Amplitude Matrix logic`
content = content.replace(
  singleNodeLogic,
  `${singleNodeLogic}\n        const nId = data.node_id ? data.node_id.replace('beacon_', '') : '';\n        if (selectedNodeId.value && nId !== selectedNodeId.value && nId !== 'beacon_' + selectedNodeId.value) { return; }\n`
)

fs.writeFileSync('frontend/src/components/WifiView.vue', content)
