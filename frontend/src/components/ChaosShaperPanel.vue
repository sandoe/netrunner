<template>
  <div class="shaper-panel">
    <div class="shaper-layout">
      <!-- Controls -->
      <div class="shaper-controls">
        <div class="section-title">TRAFFIC SHAPING (LINUX TC & NETEM)</div>
        <div class="control-group">
          <p class="desc text-red">
            Advarsel: Dette manipulerer Linux-kernen (`tc qdisc`) og vil forringe netværksforbindelsen til denne node i realtid. Sætter du Packet Loss for højt, kan du miste SSH/Dashboard-adgang!
          </p>

          <div class="slider-group">
            <label>LATENCY (ms): {{ latency }}</label>
            <input type="range" v-model.number="latency" min="0" max="1000" step="10" class="cyber-slider" />
          </div>

          <div class="slider-group">
            <label>JITTER (ms): {{ jitter }}</label>
            <input type="range" v-model.number="jitter" min="0" max="500" step="5" class="cyber-slider" />
          </div>

          <div class="slider-group">
            <label>PACKET LOSS (%): {{ loss }} <span v-if="loss > 30" class="warning-text">(DANGER)</span></label>
            <input type="range" v-model.number="loss" min="0" max="50" step="1" class="cyber-slider loss-slider" />
          </div>

          <div class="button-row">
            <button class="btn-tool btn-apply" @click="applyChaos" :disabled="applying">
              {{ applying ? 'APPLYING...' : 'APPLY CHAOS RULES' }}
            </button>
            <button class="btn-tool btn-reset" @click="resetChaos" :disabled="applying">
              RESET (NORMAL)
            </button>
          </div>
        </div>
      </div>

      <!-- Output Log -->
      <div class="shaper-log">
        <div class="log-header">CHAOS LOG</div>
        <pre class="log-content">{{ logOutput || 'Awaiting chaos...' }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  nodeId: string
}>()

const applying = ref(false)
const latency = ref(0)
const jitter = ref(0)
const loss = ref(0)
const logOutput = ref('')

function appendLog(msg: string) {
  const ts = new Date().toISOString().split('T')[1].split('.')[0]
  logOutput.value += `[${ts}] ${msg}\n`
}

async function applyChaos() {
  if (!props.nodeId) return
  if (loss.value > 30 && !confirm("Warning: High packet loss can break your dashboard connection to this node. Proceed?")) return

  applying.value = true
  appendLog(`Deploying 'tc qdisc netem' rules to node ${props.nodeId}...`)
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/chaos/shaping`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('nr_token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        latency_ms: latency.value,
        jitter_ms: jitter.value,
        loss_percent: loss.value
      })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Shaping failed')
    
    appendLog(data.message)
  } catch (e: any) {
    appendLog(`ERROR: ${e.message}`)
  } finally {
    applying.value = false
  }
}

async function resetChaos() {
  if (!props.nodeId) return
  applying.value = true
  appendLog(`Removing all 'tc' rules from node ${props.nodeId}...`)
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/chaos/shaping/reset`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('nr_token')}` }
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Reset failed')
    
    appendLog(data.message)
    latency.value = 0
    jitter.value = 0
    loss.value = 0
  } catch (e: any) {
    appendLog(`ERROR: ${e.message}`)
  } finally {
    applying.value = false
  }
}
</script>

<style scoped>
.shaper-panel {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.shaper-layout {
  display: flex;
  gap: 20px;
  min-height: 100%;
}

.shaper-controls {
  flex: 1;
  max-width: 350px;
  display: flex;
  flex-direction: column;
}

.section-title {
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--textwh);
  letter-spacing: 2px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
}

.control-group {
  background: var(--bg2);
  border: 1px solid rgba(255, 45, 110, 0.3);
  background: rgba(255, 45, 110, 0.02);
  border-radius: var(--r);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.desc {
  font-family: var(--font-ui);
  font-size: 12px;
  color: var(--text);
  line-height: 1.4;
}

.text-red {
  color: #ff5252;
}

.warning-text {
  color: #ff5252;
  font-weight: bold;
  animation: pulse 1s infinite;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slider-group label {
  font-family: var(--font-hd);
  font-size: 11px;
  color: var(--textbr);
}

.cyber-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  background: var(--bg3);
  border-radius: 3px;
  outline: none;
  border: 1px solid var(--border);
}

.cyber-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--cyan);
  cursor: pointer;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

.loss-slider::-webkit-slider-thumb {
  background: var(--pink);
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.5);
}

.button-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.btn-tool {
  flex: 1;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 10px;
  font-family: var(--font-hd);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: var(--r);
}

.btn-apply {
  border-color: var(--pink);
  color: var(--pink);
  background: rgba(255, 45, 110, 0.1);
}

.btn-apply:hover:not(:disabled) {
  background: var(--pink);
  color: #fff;
  box-shadow: 0 0 15px rgba(255, 45, 110, 0.5);
}

.btn-reset {
  border-color: var(--cyan);
  color: var(--cyan);
  background: rgba(0, 229, 255, 0.1);
}

.btn-reset:hover:not(:disabled) {
  background: var(--cyan);
  color: #fff;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.5);
}

.shaper-log {
  flex: 2;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.log-header {
  padding: 10px 16px;
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
  font-family: var(--font-hd);
  font-size: 10px;
  color: var(--text);
  letter-spacing: 2px;
}

.log-content {
  flex: 1;
  padding: 16px;
  font-family: var(--font-co);
  font-size: 11px;
  color: var(--textbr);
  overflow-y: auto;
  white-space: pre-wrap;
  background: #020305;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.3; }
  100% { opacity: 1; }
}
</style>
