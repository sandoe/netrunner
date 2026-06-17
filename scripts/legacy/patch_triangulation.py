import re

with open('frontend/src/components/BluetoothView.vue', 'r') as f:
    content = f.read()

# 1. Add triangulationMode ref
content = re.sub(
    r"const connected = ref\(false\)",
    "const connected = ref(false)\nconst triangulationMode = ref(false)",
    content
)

# 2. Add ACTIVATE TRIANGULATION button in details panel
button_html = """
        <div class="detail-row" v-if="selectedDevice.nodes && Object.keys(selectedDevice.nodes).length > 1">
          <button class="btn btn-outline" style="width: 100%; border-color: var(--cyan); color: var(--cyan);" @click="triangulationMode = !triangulationMode">
            {{ triangulationMode ? 'DEACTIVATE TRIANGULATION' : 'ACTIVATE TRIANGULATION' }}
          </button>
        </div>
"""
content = re.sub(
    r"(<div class=\"detail-row\" v-if=\"selectedDevice.nodes)",
    button_html + r"\n        \1",
    content,
    count=1
)

# 3. Add Triangulation nodes to radar
radar_html = """
          <template v-if="!triangulationMode || !selectedDevice">
            <div 
              v-for="dev in sortedDevices" 
              :key="dev.mac" 
              class="blip"
              :class="{ 
                'jammed': jammedTargets[dev.mac], 
                'active': dev.last_seen > Date.now() / 1000 - 5,
                'selected': selectedDevice && selectedDevice.mac === dev.mac
              }"
              :style="getDeviceStyle(dev)"
              @click="selectDevice(dev)"
            ></div>
          </template>
          <template v-else>
            <!-- Target Center -->
            <div class="blip selected" style="left: 50%; top: 50%; box-shadow: 0 0 15px var(--cyan);"></div>
            <!-- Nodes as blips around it -->
            <div 
              v-for="(ndata, nid, index) in selectedDevice.nodes" 
              :key="nid" 
              class="blip node-blip"
              :style="getNodeTriangulationStyle(ndata.rssi, index, Object.keys(selectedDevice.nodes).length)"
            >
              <div class="node-label">{{ nid }}</div>
            </div>
          </template>
"""

content = re.sub(
    r"<div \s*v-for=\"dev in sortedDevices\"[\s\S]*?@click=\"selectDevice\(dev\)\"\s*></div>",
    radar_html,
    content
)

# 4. Add getNodeTriangulationStyle function
js_func = """
function getNodeTriangulationStyle(rssi: number, index: number, totalNodes: number) {
  // Evenly space the nodes around the target based on index
  const angle = (index / totalNodes) * Math.PI * 2;
  
  // Convert RSSI to a normalized distance radius (similar to getDeviceStyle)
  const rssiClamped = Math.max(-100, Math.min(-30, rssi))
  const range = (rssiClamped + 100) / 70 
  const distance = (1 - range) * 45 // 0 to 45% radius
  
  const x = 50 + distance * Math.cos(angle)
  const y = 50 + distance * Math.sin(angle)
  
  return { left: `${x}%`, top: `${y}%`, backgroundColor: 'var(--cyan)' }
}
"""
content = re.sub(
    r"(function getDeviceStyle\()",
    js_func + r"\n\1",
    content
)

# 5. Add .node-blip and .node-label CSS
css_str = """
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
"""
content = content.replace("</style>", css_str + "\n</style>")

with open('frontend/src/components/BluetoothView.vue', 'w') as f:
    f.write(content)

print("Patched BluetoothView.vue")
