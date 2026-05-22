<template>
  <div class="defense-panel">
    <div class="defense-layout">
      <!-- Controls -->
      <div class="defense-controls">
        <div class="section-title">THREAT MONITOR AGENT</div>
        <div class="control-group monitoring-zone" :class="{ active: currentNode?.threat_monitoring }">
          <div class="status-header">
            <span class="status-dot" :class="{ active: currentNode?.threat_monitoring, blinking: installing || removing }"></span>
            <span class="status-label" :class="{ 'status-active': currentNode?.threat_monitoring }">
              {{ currentNode?.threat_monitoring ? 'AGENT ONLINE' : 'AGENT OFFLINE' }}
            </span>
          </div>
          <p class="desc text-amber">
            Multi-Vector Agent: Tails real-time SSH auth logs, Web access logs (detecting SQLi, XSS, Path Traversal), and Firewall (UFW) logs. Captures, geolocates and streams live cyberthreats.
          </p>
          <button v-if="isAdmin" class="btn-tool btn-monitor" :class="{ 'btn-deactivate': currentNode?.threat_monitoring }" @click="toggleMonitoring" :disabled="installing || removing">
            {{ installing ? 'VERIFYING & INSTALLING...' : removing ? 'DEACTIVATING...' : currentNode?.threat_monitoring ? 'REMOVE MONITOR AGENT' : 'INSTALL MONITOR AGENT' }}
          </button>
          <div v-else class="desc text-amber" style="font-weight:bold;">[LOCKED: ADMIN CLEARANCE REQUIRED]</div>
        </div>

        <div class="section-title mt-4">VULNERABILITY SCANNER</div>
        <div class="control-group">
          <p class="desc">Perform an active Nmap scan against this node to discover open ports and services.</p>
          <button class="btn-tool" @click="runScan" :disabled="scanning">
            {{ scanning ? 'SCANNING...' : 'RUN NMAP SCAN' }}
          </button>
        </div>

        <div class="section-title mt-4">INCIDENT RESPONSE</div>
        <div class="control-group danger-zone">
          <p class="desc text-pink">Isolate this node from the network immediately using iptables DROP rules. Management connections will be maintained.</p>
          <button v-if="isAdmin" class="btn-tool btn-danger" @click="isolateNode" :disabled="isolating">
            {{ isolating ? 'ISOLATING...' : 'ISOLATE NODE (PANIC)' }}
          </button>
          <div v-else class="desc text-pink" style="font-weight:bold;">[LOCKED: ADMIN CLEARANCE REQUIRED]</div>
        </div>
        <div class="section-title mt-4">ZERO TRUST ARCHITECTURE</div>
        <div class="control-group zta-zone">
          <p class="desc text-cyan">Micro-segmentation. Enforce strict default DROP policies, block lateral movement, and whitelist explicit verified connections.</p>
          <button v-if="isAdmin" class="btn-tool btn-zta" @click="enforceZTA" :disabled="ztaEnforcing || isolating">
            {{ ztaEnforcing ? 'ENFORCING ZTA...' : 'ENFORCE ZTA (HARDEN)' }}
          </button>
          <div v-else class="desc text-cyan" style="font-weight:bold;">[LOCKED: ADMIN CLEARANCE REQUIRED]</div>
        </div>
      </div>

      <!-- Output Log -->
      <div class="defense-log">
        <div class="log-header">ACTION LOG</div>
        <pre class="log-content">{{ logOutput || 'Awaiting action...' }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, inject, computed } from 'vue'
import { api } from '@/api/client'
import { useNodesStore } from '@/stores/nodes'

const props = defineProps<{
  nodeId: string
}>()

const store = useNodesStore()
const currentNode = computed(() => store.nodes[props.nodeId])

const userRole = inject<any>('userRole')
const isAdmin = computed(() => {
  if (!userRole) return false
  const val = typeof userRole === 'object' && 'value' in userRole ? userRole.value : userRole
  return val === 'admin'
})

const scanning = ref(false)
const isolating = ref(false)
const ztaEnforcing = ref(false)
const installing = ref(false)
const removing = ref(false)
const logOutput = ref('')

function appendLog(msg: string) {
  const ts = new Date().toISOString().split('T')[1].split('.')[0]
  logOutput.value += `[${ts}] ${msg}\n`
}

async function toggleMonitoring() {
  if (!props.nodeId) return
  const isInstalled = !!currentNode.value?.threat_monitoring
  
  if (isInstalled) {
    if (!confirm("Are you sure you want to deactivate the Threat Monitor Agent? Real-time intrusion feeds from this node will stop.")) return
    removing.value = true
    appendLog(`Deactivating Threat Monitor Agent on node ${props.nodeId}...`)
    try {
      const res = await api.removeMonitoring(props.nodeId)
      appendLog(res.message || "Agent deactivated successfully.")
      if (store.nodes[props.nodeId]) {
        store.nodes[props.nodeId].threat_monitoring = false
      }
    } catch (e: any) {
      appendLog(`ERROR deactivating agent: ${e.message}`)
    } finally {
      removing.value = false
    }
  } else {
    installing.value = true
    appendLog(`Installing Threat Monitor Agent on node ${props.nodeId}...`)
    appendLog("Verifying syslog/journalctl readability permissions over remote SSH connection...")
    try {
      const res = await api.installMonitoring(props.nodeId)
      appendLog(res.message || "Agent successfully installed! Tailing daemon active.")
      if (store.nodes[props.nodeId]) {
        store.nodes[props.nodeId].threat_monitoring = true
      }
    } catch (e: any) {
      appendLog(`INSTALLATION ERROR: ${e.message}`)
    } finally {
      installing.value = false
    }
  }
}

async function runScan() {
  if (!props.nodeId) return
  scanning.value = true
  appendLog(`Initiating Nmap scan against node ${props.nodeId}...`)
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/nmap`, { method: 'POST' })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Scan failed')
    
    appendLog("Scan completed successfully.")
    logOutput.value += `\n${data.scan_results}\n\n`
  } catch (e: any) {
    appendLog(`ERROR: ${e.message}`)
  } finally {
    scanning.value = false
  }
}

async function isolateNode() {
  if (!props.nodeId) return
  if (!confirm("WARNING: This will deploy DROP rules on the node, blocking all incoming traffic except management. Proceed?")) return
  
  isolating.value = true
  appendLog(`Initiating ISOLATION PROTOCOL on node ${props.nodeId}...`)
  try {
    const res = await fetch(`/api/nodes/${props.nodeId}/isolate`, { method: 'POST' })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Isolation failed')
    
    appendLog("Isolation protocol executed.")
    logOutput.value += `\n${data.isolation_log}\n\n`
  } catch (e: any) {
    appendLog(`ERROR: ${e.message}`)
  } finally {
    isolating.value = false
  }
}

async function enforceZTA() {
  if (!props.nodeId) return
  if (!confirm("WARNING: This will enforce strict Zero Trust Micro-Segmentation. All implicit traffic will be dropped. Proceed?")) return
  
  ztaEnforcing.value = true
  appendLog(`Initiating ZERO TRUST ENFORCER on node ${props.nodeId}...`)
  try {
    const res = await api.enforceZeroTrust(props.nodeId)
    appendLog("ZTA protocol executed.")
    logOutput.value += `\n${res.message}\n\n`
  } catch (e: any) {
    appendLog(`ERROR: ${e.message}`)
  } finally {
    ztaEnforcing.value = false
  }
}
</script>

<style scoped>
.defense-panel {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.defense-layout {
  display: flex;
  gap: 20px;
  height: 100%;
}

.defense-controls {
  flex: 1;
  max-width: 300px;
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

.mt-4 {
  margin-top: 24px;
}

.control-group {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.monitoring-zone {
  border-color: rgba(255, 179, 0, 0.3);
  background: rgba(255, 179, 0, 0.02);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.monitoring-zone.active {
  border-color: rgba(0, 230, 118, 0.4);
  background: rgba(0, 230, 118, 0.04);
  box-shadow: 0 0 15px rgba(0, 230, 118, 0.05);
}

.status-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff5252;
  box-shadow: 0 0 8px rgba(255, 82, 82, 0.5);
  transition: all 0.3s ease;
}

.status-dot.active {
  background: #00e676;
  box-shadow: 0 0 12px rgba(0, 230, 118, 0.8);
  animation: pulse 2s infinite ease-in-out;
}

.status-dot.blinking {
  animation: fast-pulse 0.6s infinite ease-in-out;
}

.status-label {
  font-family: var(--font-hd);
  font-size: 10px;
  letter-spacing: 1px;
  color: #ff5252;
  font-weight: bold;
}

.status-label.status-active {
  color: #00e676;
}

.danger-zone {
  border-color: rgba(255, 45, 110, 0.3);
  background: rgba(255, 45, 110, 0.05);
}

.desc {
  font-family: var(--font-ui);
  font-size: 12px;
  color: var(--text);
  line-height: 1.4;
}

.text-pink {
  color: var(--pink);
}

.text-cyan {
  color: var(--cyan);
}

.text-amber {
  color: #ffb300;
}

.zta-zone {
  border-color: rgba(0, 229, 255, 0.3);
  background: rgba(0, 229, 255, 0.05);
}

.btn-tool {
  background: var(--bg3);
  border: 1px solid var(--cyan-d);
  color: var(--cyan);
  padding: 10px;
  font-family: var(--font-hd);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: var(--r);
  width: 100%;
}

.btn-tool:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.btn-tool:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: var(--border);
  color: var(--text);
}

.btn-danger {
  border-color: var(--pink);
  color: var(--pink);
}

.btn-danger:hover:not(:disabled) {
  background: rgba(255, 45, 110, 0.1);
  box-shadow: 0 0 10px rgba(255, 45, 110, 0.2);
}

.btn-zta {
  border-color: var(--cyan);
  color: var(--cyan);
}

.btn-zta:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
  text-shadow: 0 0 5px var(--cyan);
}

.btn-monitor {
  border-color: #ffb300;
  color: #ffb300;
}

.btn-monitor:hover:not(:disabled) {
  background: rgba(255, 179, 0, 0.1);
  box-shadow: 0 0 15px rgba(255, 179, 0, 0.2);
}

.btn-monitor.btn-deactivate {
  border-color: #ff5252;
  color: #ff5252;
}

.btn-monitor.btn-deactivate:hover:not(:disabled) {
  background: rgba(255, 82, 82, 0.1);
  box-shadow: 0 0 15px rgba(255, 82, 82, 0.3);
}

.defense-log {
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
  0% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7);
  }
  70% {
    transform: scale(1.1);
    box-shadow: 0 0 0 8px rgba(0, 230, 118, 0);
  }
  100% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(0, 230, 118, 0);
  }
}

@keyframes fast-pulse {
  0% {
    opacity: 0.3;
    transform: scale(0.9);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
  100% {
    opacity: 0.3;
    transform: scale(0.9);
  }
}
</style>

