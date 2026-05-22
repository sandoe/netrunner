<template>
  <LoginView v-if="!loggedIn" @authenticated="onAuthenticated" />
  <div v-else class="app">
    <div class="scanline"></div>
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-title">NETRUNNER</span>
          <span class="logo-sub">OS v1.0.0</span>
        </div>
        <div class="header-tools">
          <button class="btn-icon" @click="showSettings = true" title="Settings">⚙️</button>
          <button class="btn-add" @click="showAddForm = true" title="Add node">+</button>
        </div>
      </div>

      <div class="sidebar-stats">
        <div class="sidebar-stat">
          <div class="stat-label">NODES</div>
          <div class="stat-value">{{ store.nodeList.length }}</div>
        </div>
        <div class="sidebar-stat">
          <div class="stat-label">LIVE</div>
          <div class="stat-value" :class="{ 'text-green': store.connectedCount > 0 }">{{ store.connectedCount }}</div>
        </div>
      </div>

      <nav class="nav-menu">
        <button :class="{ active: viewMode === 'node' }" @click="viewMode = 'node'">NODES</button>
        <button :class="{ active: viewMode === 'topology' }" @click="viewMode = 'topology'">TOPOLOGY</button>
        <button :class="{ active: viewMode === 'threat' }" @click="viewMode = 'threat'">THREAT MAP</button>
        <button class="btn-warroom" :class="{ active: viewMode === 'warroom' }" @click="viewMode = 'warroom'">🚨 WAR ROOM</button>
      </nav>

      <div v-if="store.loading" class="sidebar-info">SCANNING NEURAL LINK...</div>
      <div v-if="store.error" class="sidebar-error">{{ store.error }}</div>

      <div class="sidebar-search">
        <input v-model="searchQuery" placeholder="FILTER NODES..." class="search-input" />
      </div>

      <div class="node-list">
        <div v-for="(group, type) in groupedNodes" :key="type" class="node-group">
          <div class="node-group-head" @click="toggleSidebarCat(type as string)">
            <span>{{ getDeviceTypeLabel(type as string) }}</span>
            <span class="node-group-chevron" :class="{ collapsed: collapsedSidebarCats.has(type as string) }">⌃</span>
          </div>
          <div v-if="!collapsedSidebarCats.has(type as string)" class="node-group-items">
            <div
              v-for="node in group"
              :key="node.id"
              class="node-item"
              :class="{ active: store.selectedId === node.id }"
              @click="store.select(node.id)"
            >
              <div 
                class="node-dot" 
                :class="{ 
                  connected: store.isConnected(node.id),
                  'manually-off': !store.isConnected(node.id) && store.manuallyDisconnected.has(node.id)
                }"
              ></div>
              <div class="node-meta">
                <div class="node-name">{{ node.name }}</div>
                <div class="node-host">{{ node.host }}:{{ node.port }}</div>
                <div class="node-tags" v-if="node.tags && node.tags.length">
                  <span v-for="tag in node.tags.slice(0, 3)" :key="tag" class="tag-chip">{{ tag }}</span>
                </div>
              </div>
              <span class="node-transport" :class="node.transport">{{ node.transport }}</span>
            </div>
          </div>
        </div>
        <div v-if="!store.loading && filteredNodes.length === 0" class="sidebar-empty">
          NO NODES DETECTED.
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="main">
      <!-- Background Layer -->
      <div class="main-bg" :class="{ 'is-topology': viewMode === 'topology', 'is-threat': viewMode === 'threat' }">
        <TopologyView v-if="viewMode === 'topology'" />
        <ThreatMap v-else-if="viewMode === 'threat'" />
        <WarRoomDashboard 
          v-else-if="viewMode === 'warroom'" 
          :autopilotActive="systemState.autopilot"
          :chaosActive="systemState.chaos"
          @toggle-autopilot="toggleAutopilot"
          @toggle-chaos="toggleChaos"
        />
        
        <div v-else-if="!store.selected" class="welcome">
          <div class="welcome-inner">
            <div class="welcome-logo">NETRUNNER</div>
            <div class="welcome-sub">AWAITING NEURAL CONNECTION...</div>
          </div>
        </div>
      </div>

      <!-- Foreground Layer: Glass Panel -->
      <transition name="slide-panel">
        <div v-if="store.selected && viewMode === 'node'" class="glass-panel" :class="{ 'is-overlay': viewMode === 'topology' }">
          <!-- Node header bar -->
          <div class="node-header">
            <div class="node-title">
              <div class="node-dot-lg" :class="{ connected: store.isConnected(store.selected.id) }"></div>
              <div>
                <div class="node-title-name">{{ store.selected.name }}</div>
                <div class="node-title-sub">
                  {{ store.selected.host }}:{{ store.selected.port }} · {{ store.selected.transport }}
                  <span class="device-badge" :class="store.selected.device_type">{{ store.selected.device_type }}</span>
                </div>
              </div>
            </div>
            <div class="header-actions">
              <button v-if="!store.isConnected(store.selected.id)" @click="doConnect" class="btn-action" :disabled="connBusy">CONNECT</button>
              <template v-else>
                <button @click="doDisconnect" class="btn-action" :disabled="connBusy">DISCONNECT</button>
                <button @click="doReboot" class="btn-action btn-reboot" :disabled="connBusy">REBOOT</button>
              </template>
              <button @click="detectType" class="btn-action">DETECT</button>
              <button @click="doBackup"   class="btn-action">BACKUP</button>
              <button @click="doRollback" class="btn-action">ROLLBACK</button>
              <button v-if="userRole === 'admin'" @click="deleteNode" class="btn-action btn-danger">NUKE CONFIG</button>
            </div>
          </div>

          <!-- Tab bar -->
          <div class="tab-bar">
            <button
              v-for="tab in dynamicTabs"
              :key="tab.id"
              class="tab"
              :class="{ active: activeTab === tab.id }"
              @click="activeTab = tab.id"
            >{{ tab.label }}</button>
          </div>

          <!-- Tab content -->
          <div class="tab-content">
            <OverviewPanel v-if="activeTab === 'overview'" :node-id="store.selected.id" />
            <Gns3Panel    v-if="activeTab === 'gns3-api'" :node-id="store.selected.id" />
            <DiagPanel    v-if="activeTab === 'diag'"     :node-id="store.selected.id" />
            <ConfigPanel  v-if="activeTab === 'config'"   :node-id="store.selected.id" />
            <ExecPanel    v-if="activeTab === 'exec'"     :node-id="store.selected.id" />
            <ActiveDefensePanel v-if="activeTab === 'defense'" :node-id="store.selected.id" />
            <CapturePanel v-if="activeTab === 'capture'"  :node-id="store.selected.id" />
            <Terminal     v-if="activeTab === 'terminal'" :node="store.selected" />
          </div>
        </div>
      </transition>
    </main>

    <!-- Modals -->
    <NodeForm v-if="showAddForm" @close="showAddForm = false" />
    <NodeForm v-if="showEdit"    :node="store.selected" @close="showEdit = false" />
    <SettingsModal v-if="showSettings" @close="showSettings = false" />

    <!-- Reboot Modal -->
    <div v-if="showRebootModal" class="modal-overlay reboot-overlay" @click.self="showRebootModal = false">
      <div class="cyber-modal-card reboot-card">
        <div class="cyber-modal-header warning">
          <div class="modal-title">⚠️ SYSTEM REBOOT SEQUENCE</div>
          <button class="btn-close-modal" @click="showRebootModal = false">×</button>
        </div>
        <div class="cyber-modal-body">
          <p class="modal-intro-text">
            Choose the reboot vector for <strong class="text-orange">{{ store.selected?.name }}</strong>:
          </p>

          <!-- Method Cards (Only show selector if GNS3 node) -->
          <div v-if="store.selected?.device_type === 'gns3'" class="reboot-vectors">
            <div 
              class="vector-card" 
              :class="{ active: rebootMethod === 'gns3' }" 
              @click="rebootMethod = 'gns3'"
            >
              <div class="vector-icon">⚡</div>
              <div class="vector-info">
                <div class="vector-name">GNS3 Hypervisor API</div>
                <div class="vector-desc">Force reload the VM/container node using the GNS3 control channel. Highly robust fallback if OS shell is frozen.</div>
              </div>
              <div class="vector-badge">HYPERVISOR</div>
            </div>

            <div 
              class="vector-card" 
              :class="{ active: rebootMethod === 'command' }" 
              @click="rebootMethod = 'command'"
            >
              <div class="vector-icon">🐚</div>
              <div class="vector-info">
                <div class="vector-name">Console Terminal Shell</div>
                <div class="vector-desc">Send force-reboot command sequences directly over the Telnet/SSH active session channel.</div>
              </div>
              <div class="vector-badge">CONSOLES</div>
            </div>
          </div>

          <!-- Code Snippet Preview -->
          <div class="vector-preview">
            <div class="preview-header">EXECUTION VECTOR PREVIEW:</div>
            <pre class="preview-code"><code>{{ 
              rebootMethod === 'gns3' 
                ? `POST /v2/projects/${store.selected?.metadata?.gns3?.project_id || '...'}/nodes/${store.selected?.metadata?.gns3?.node_id || '...'}/reload`
                : `reboot -f || sudo reboot -f || reboot` 
            }}</code></pre>
          </div>

          <div class="modal-warning-box">
            <span class="warning-icon">⚠️</span>
            <span class="warning-text">WARNING: Rebooting will immediately drop all socket sessions, interrupt active capture tasks, and temporarily clear live telemetry sparklines.</span>
          </div>

          <!-- Error Feedback -->
          <div v-if="rebootError" class="modal-error-box">
            <div class="error-header">⚡ SEQUENCE TERMINATION FAILURE:</div>
            <div class="error-msg">{{ rebootError }}</div>
          </div>
        </div>

        <div class="cyber-modal-footer">
          <button class="btn-modal-cancel" @click="showRebootModal = false" :disabled="rebootLoading">CANCEL</button>
          <button 
            class="btn-modal-confirm reboot" 
            @click="confirmReboot" 
            :disabled="rebootLoading"
          >
            <span v-if="rebootLoading" class="spinner"></span>
            <span v-else>CONFIRM REBOOT</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Flash messages -->
    <div class="flash-stack">
      <div v-for="msg in flashes" :key="msg.id" class="flash" :class="msg.type">{{ msg.text }}</div>
    </div>

    <!-- AI Sidebar -->
    <AiChatSidebar />

    <!-- Global Error Diagnostics Console -->
    <div v-if="globalErrors.length > 0" class="global-error-console">
      <div class="console-header">
        <span class="console-indicator">⚠️ DIAGNOSTICS: RUNTIME DISRUPTION</span>
        <button class="btn-console-clear" @click="globalErrors = []">DISMISS</button>
      </div>
      <div class="console-body">
        <div v-for="err in globalErrors" :key="err.id" class="console-item">
          <div class="console-msg">{{ err.message }}</div>
          <div v-if="err.stack" class="console-stack">{{ err.stack }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useNodesStore } from '@/stores/nodes'
import { api } from '@/api/client'
import DiagPanel from './components/DiagPanel.vue'
import ExecPanel from './components/ExecPanel.vue'
import ConfigPanel from './components/ConfigPanel.vue'
import CapturePanel from './components/CapturePanel.vue'
import OverviewPanel from './components/OverviewPanel.vue'
import Terminal  from './components/Terminal.vue'
import NodeForm  from './components/NodeForm.vue'
import TopologyView from './components/TopologyView.vue'
import ThreatMap from './components/ThreatMap.vue'
import ActiveDefensePanel from './components/ActiveDefensePanel.vue'
import AiChatSidebar from './components/AiChatSidebar.vue'
import SettingsModal from './components/SettingsModal.vue'
import LoginView from './components/LoginView.vue'
import WarRoomDashboard from './components/WarRoomDashboard.vue'
import Gns3Panel from './components/Gns3Panel.vue'
import type { NrNode } from '@/types'
import { provide } from 'vue'

const loggedIn = ref(!!localStorage.getItem('nr_token'))
const userRole = ref(localStorage.getItem('nr_role') || 'analyst')
provide('userRole', userRole)

function onAuthenticated(role: string) {
  userRole.value = role
  loggedIn.value = true
  store.refresh()
  pollSystem()
}

// Automatically logout when token expires
window.addEventListener('auth-expired', () => {
  loggedIn.value = false
  userRole.value = 'analyst'
})

const store       = useNodesStore()
const viewMode    = ref<'node' | 'topology' | 'threat' | 'warroom'>('node')
const activeTab   = ref<'overview' | 'gns3-api' | 'diag' | 'config' | 'exec' | 'defense' | 'capture' | 'terminal'>('overview')
const showAddForm = ref(false)
const showEdit    = ref(false)
const showSettings = ref(false)
const searchQuery = ref('')
const connBusy    = ref(false)
const exporting   = ref(false)

// Reboot options modal state
const showRebootModal = ref(false)
const rebootMethod = ref<'command' | 'gns3'>('command')
const rebootLoading = ref(false)
const rebootError = ref('')

const systemState = ref({ autopilot: false, chaos: false })
let lastLogCount = 0

// Global error tracking for remote diagnostics
const globalErrors = ref<{ id: number; message: string; stack?: string }[]>([])
let nextErrorId = 0

function logGlobalError(message: string, stack?: string) {
  const id = nextErrorId++
  globalErrors.value.push({ id, message, stack })
}

const handleWindowError = (event: ErrorEvent) => {
  logGlobalError(event.message || 'Uncaught JavaScript Error', event.filename ? `${event.filename}:${event.lineno}` : undefined)
}

const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
  logGlobalError(`Unhandled Promise Rejection: ${String(event.reason)}`, event.reason?.stack)
}

const filteredNodes = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return store.nodeList
  return store.nodeList.filter(n =>
    n.name.toLowerCase().includes(q) ||
    n.host.toLowerCase().includes(q) ||
    (n.tags ?? []).some(t => t.toLowerCase().includes(q))
  )
})

const collapsedSidebarCats = ref<Set<string>>(new Set())

const groupedNodes = computed(() => {
  const groups: Record<string, NrNode[]> = {}
  for (const n of filteredNodes.value) {
    const type = n.device_type || 'unknown'
    if (!groups[type]) groups[type] = []
    groups[type].push(n)
  }
  return groups
})

function getDeviceTypeLabel(type: string) {
  const labels: Record<string, string> = {
    linux: 'LINUX',
    rpi: 'RASPBERRY PI',
    gns3: 'NETWORK',
    unknown: 'UNKNOWN'
  }
  return labels[type] || type.toUpperCase()
}

function toggleSidebarCat(type: string) {
  if (collapsedSidebarCats.value.has(type)) collapsedSidebarCats.value.delete(type)
  else collapsedSidebarCats.value.add(type)
}

const dynamicTabs = computed(() => {
  const list = [
    { id: 'overview', label: 'OVERVIEW' },
  ] as { id: string; label: string }[]
  if (store.selected?.device_type === 'gns3') {
    list.push({ id: 'gns3-api', label: 'GNS3 CONTROL' })
  }
  list.push(
    { id: 'diag',     label: 'DIAGNOSTICS' },
    { id: 'config',   label: 'CONFIG' },
    { id: 'exec',     label: 'EXECUTE' },
    { id: 'defense',  label: 'ACTIVE DEFENSE' },
    { id: 'capture',  label: 'CAPTURE' },
    { id: 'terminal', label: 'TERMINAL' }
  )
  return list
})

interface Flash { id: number; text: string; type: 'ok' | 'err' }
const flashes = ref<Flash[]>([])
let flashId = 0

function flash(text: string, type: 'ok' | 'err' = 'ok') {
  const id = flashId++
  flashes.value.push({ id, text, type })
  setTimeout(() => { flashes.value = flashes.value.filter(f => f.id !== id) }, 3500)
}

async function doConnect() {
  if (!store.selected) return
  connBusy.value = true
  try {
    await api.connectNode(store.selected.id)
    store.manuallyDisconnected.delete(store.selected.id)
    await store.refreshConnections()
    flash(`Connected to ${store.selected.name}`)
  } catch (e) {
    flash(String(e), 'err')
  } finally {
    connBusy.value = false
  }
}

async function doDisconnect() {
  if (!store.selected) return
  connBusy.value = true
  try {
    await api.disconnectNode(store.selected.id)
    store.manuallyDisconnected.add(store.selected.id)
    await store.refreshConnections()
    flash(`Disconnected ${store.selected.name}`)
  } catch (e) {
    flash(String(e), 'err')
  } finally {
    connBusy.value = false
  }
}

function doReboot() {
  if (!store.selected) return
  rebootError.value = ''
  rebootLoading.value = false
  if (store.selected.device_type === 'gns3') {
    rebootMethod.value = 'gns3'
  } else {
    rebootMethod.value = 'command'
  }
  showRebootModal.value = true
}

async function confirmReboot() {
  if (!store.selected) return
  rebootLoading.value = true
  rebootError.value = ''
  try {
    const res = await api.rebootNode(store.selected.id, rebootMethod.value)
    flash(res.message || `Reboot initiated for ${store.selected.name}`)
    showRebootModal.value = false
    store.manuallyDisconnected.add(store.selected.id)
    await store.refreshConnections()
  } catch (e) {
    const errMsg = (e as any).response?.data?.detail || String(e)
    rebootError.value = errMsg
    flash(`Reboot failed: ${errMsg}`, 'err')
  } finally {
    rebootLoading.value = false
  }
}

async function detectType() {
  if (!store.selected) return
  try {
    const t = await store.detectType(store.selected.id)
    flash(`Device detected: ${t}`)
  } catch (e) {
    flash(String(e), 'err')
  }
}

async function doBackup() {
  if (!store.selected) return
  try {
    await api.backupNode(store.selected.id)
    flash('Backup created')
  } catch (e) {
    flash(String(e), 'err')
  }
}

async function doExport() {
  if (!store.selected) return
  exporting.value = true
  try {
    const res = await api.exportNode(store.selected.id, {})
    const errs = Object.keys(res.diagnostic_errors || {}).length
    flash(errs ? `Export ready (${errs} diag errors)` : 'Export ready')
    const a = document.createElement('a')
    a.href = api.exportDownloadUrl(res.name)
    a.download = res.name
    document.body.appendChild(a); a.click(); a.remove()
  } catch (e) {
    flash(String(e), 'err')
  } finally {
    exporting.value = false
  }
}

async function doRollback() {
  if (!store.selected) return
  if (!confirm(`Rollback ${store.selected.name}? This restores the last backup.`)) return
  try {
    await api.rollbackNode(store.selected.id)
    flash('Rollback complete')
  } catch (e) {
    flash(String(e), 'err')
  }
}

async function deleteNode() {
  if (!store.selected) return
  if (!confirm(`Delete node "${store.selected.name}"?`)) return
  try {
    await store.remove(store.selected.id)
    flash('Node deleted')
  } catch (e) {
    flash(String(e), 'err')
  }
}

watch(() => store.selectedId, () => {
  activeTab.value = 'overview'
  store.refreshConnections()
})

async function toggleAutopilot() {
  try {
    const newState = !systemState.value.autopilot
    const res = await api.updateSystemState({ autopilot: newState })
    systemState.value.autopilot = res.autopilot
    flash(res.autopilot ? 'AI Autopilot ACTIVATED' : 'AI Autopilot DEACTIVATED', res.autopilot ? 'ok' : 'err')
  } catch(e) { flash(String(e), 'err') }
}

async function toggleChaos() {
  try {
    const newState = !systemState.value.chaos
    const res = await api.updateSystemState({ chaos: newState })
    systemState.value.chaos = res.chaos
    flash(res.chaos ? 'CHAOS MODE UNLEASHED' : 'Chaos Mode disabled', res.chaos ? 'err' : 'ok')
    if (res.chaos) {
      document.body.classList.add('chaos-active')
    } else {
      document.body.classList.remove('chaos-active')
    }
  } catch(e) { flash(String(e), 'err') }
}

async function pollSystem() {
  try {
    const st = await api.systemState()
    systemState.value = st
    if (st.chaos) document.body.classList.add('chaos-active')
    else document.body.classList.remove('chaos-active')

    const res = await api.systemLogs()
    const logs = res.logs || []
    if (logs.length > lastLogCount && lastLogCount > 0) {
      // New logs arrived
      const newLogs = logs.slice(0, logs.length - lastLogCount)
      for (const lg of newLogs) {
        flash(lg.message, 'ok')
      }
    }
    lastLogCount = logs.length
  } catch(e) {}
}

let connTimer: ReturnType<typeof setInterval> | null = null
let sysTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  window.addEventListener('error', handleWindowError)
  window.addEventListener('unhandledrejection', handleUnhandledRejection)

  if (loggedIn.value) {
    store.refresh()
    pollSystem()
  }
  connTimer = setInterval(() => { if (loggedIn.value) store.refreshConnections() }, 4000)
  sysTimer  = setInterval(() => { if (loggedIn.value) pollSystem() }, 2000)
})
onUnmounted(() => { 
  window.removeEventListener('error', handleWindowError)
  window.removeEventListener('unhandledrejection', handleUnhandledRejection)

  if (connTimer) clearInterval(connTimer)
  if (sysTimer) clearInterval(sysTimer)
})
</script>

<style scoped>
.app { display: flex; height: 100vh; overflow: hidden; position: relative; z-index: 1; }

/* Sidebar */
.sidebar { width: 270px; min-width: 270px; background: var(--bg2); border-right: 1px solid var(--border); display: flex; flex-direction: column; position: relative; }
.sidebar::after { content: ''; position: absolute; top: 0; right: 0; width: 1px; height: 100%; background: linear-gradient(to bottom, transparent, var(--cyan), transparent); opacity: .4; }

.sidebar-header { padding: 22px 20px 18px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.header-tools { display: flex; align-items: center; gap: 10px; }
.logo { line-height: 1; }
.logo-title { font-family: var(--font-hd); font-size: 15px; font-weight: 900; letter-spacing: 3px; color: var(--green); text-shadow: 0 0 12px rgba(0,255,157,.6); }
.logo-sub { display: block; font-family: var(--font-co); font-size: 9px; letter-spacing: 2px; color: var(--text); margin-top: 5px; text-transform: uppercase; }

.btn-icon { background: none; border: none; font-size: 16px; cursor: pointer; opacity: 0.6; transition: opacity 0.2s; padding: 0; display: flex; align-items: center; justify-content: center; }
.btn-icon:hover { opacity: 1; filter: drop-shadow(0 0 5px var(--cyan)); }

.btn-add { width: 28px; height: 28px; border-radius: 50%; background: none; border: 1px solid var(--cyan); color: var(--cyan); font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .2s; }
.btn-add:hover { background: var(--cyan); color: var(--bg); box-shadow: var(--shadow-c); }

.sidebar-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 14px 20px; border-bottom: 1px solid var(--border); }
.sidebar-stat { background: linear-gradient(180deg, rgba(0,229,255,.08), rgba(16,24,40,.5)); border: 1px solid var(--border); border-radius: var(--r); padding: 10px; }
.stat-label { font-family: var(--font-hd); font-size: 8px; letter-spacing: 1.5px; color: var(--text); text-transform: uppercase; }
.stat-value { margin-top: 4px; font-family: var(--font-co); font-size: 16px; color: var(--textwh); }
.text-green { color: var(--green); text-shadow: 0 0 8px var(--green); }

.nav-menu button {
  display: block;
  width: 100%;
  padding: 15px;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  font-family: var(--font-hd);
  font-size: 11px;
  text-align: center;
  cursor: pointer;
  letter-spacing: 2px;
  transition: all 0.3s;
}

.nav-menu button:hover {
  background: var(--bg3);
  color: var(--cyan);
}

.nav-menu button.active {
  background: var(--cyan);
  color: var(--bg);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
}

.btn-warroom {
  margin-top: 20px;
  border-top: 1px solid var(--pink) !important;
  border-bottom: 1px solid var(--pink) !important;
  color: var(--pink) !important;
  font-weight: bold;
}

.btn-warroom:hover {
  background: rgba(255, 45, 110, 0.1) !important;
  box-shadow: 0 0 15px rgba(255, 45, 110, 0.3);
}

.btn-warroom.active {
  background: var(--pink) !important;
  color: #fff !important;
  box-shadow: 0 0 20px rgba(255, 45, 110, 0.6) !important;
}

.sidebar-search { padding: 12px 14px; }
.search-input { width: 100%; padding: 10px 12px; background: var(--bg3); border: 1px solid var(--border); border-radius: var(--r); color: var(--textwh); font-family: var(--font-co); font-size: 11px; outline: none; }
.search-input:focus { border-color: var(--cyan); box-shadow: 0 0 8px rgba(0,229,255,.2); }

.node-list { flex: 1; overflow-y: auto; padding: 4px 10px; }

.node-group { margin-bottom: 12px; }
.node-group-head {
  padding: 8px 12px; font-family: var(--font-hd); font-size: 9px; font-weight: 800;
  color: var(--text); letter-spacing: 1.5px; cursor: pointer;
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid transparent; transition: all .2s;
  user-select: none;
}
.node-group-head:hover { color: var(--textwh); background: rgba(255,255,255,0.02); }
.node-group-chevron { font-size: 10px; transition: transform .3s; }
.node-group-chevron.collapsed { transform: rotate(180deg); }
.node-group-items { margin-top: 4px; }

.node-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: var(--r); cursor: pointer; border: 1px solid transparent; margin-bottom: 4px; transition: all .18s; position: relative; }
.node-item:hover { background: var(--bg3); border-color: var(--border); }
.node-item.active { background: rgba(0,255,157,.06); border-color: rgba(0,255,157,.3); }
.node-item.active::before { content: ''; position: absolute; left: 0; top: 20%; height: 60%; width: 2px; background: var(--green); box-shadow: 0 0 8px var(--green); }

.node-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--border2); flex-shrink: 0; }
.node-dot.connected { background: var(--green); box-shadow: 0 0 8px var(--green); animation: pulse-green 2s infinite; }
.node-dot.manually-off { background: var(--pink); box-shadow: 0 0 8px var(--pink); }

@keyframes pulse-green { 0% { opacity: 1; } 50% { opacity: .5; } 100% { opacity: 1; } }

.node-meta { flex: 1; min-width: 0; }
.node-name { font-family: var(--font-co); font-size: 12px; color: var(--textwh); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-host { font-family: var(--font-co); font-size: 10px; color: var(--text); }
.node-transport { font-family: var(--font-hd); font-size: 8px; letter-spacing: 1px; padding: 2px 6px; border-radius: 4px; background: var(--bg4); border: 1px solid var(--border); text-transform: uppercase; }
.node-transport.ssh { color: var(--cyan); border-color: var(--cyan-d); }
.node-transport.telnet { color: var(--yellow); border-color: var(--orange); }

.sidebar-info, .sidebar-empty { padding: 20px; text-align: center; font-family: var(--font-hd); font-size: 10px; color: var(--text); letter-spacing: 1px; }

/* Main */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg); position: relative; }

.main-bg { flex: 1; display: flex; flex-direction: column; position: absolute; inset: 0; z-index: 1; }
.main-bg.is-topology, .main-bg.is-threat { background: transparent; }

.glass-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 2;
  background: var(--bg);
  overflow: hidden;
}

.glass-panel.is-overlay {
  position: absolute;
  top: 20px;
  right: 20px;
  bottom: 20px;
  width: 600px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: var(--r2);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.slide-panel-enter-active, .slide-panel-leave-active { transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-panel-enter-from, .slide-panel-leave-to { transform: translateX(120%); opacity: 0; }

.welcome { flex: 1; display: flex; align-items: center; justify-content: center; }
.welcome-logo { font-family: var(--font-hd); font-size: 42px; font-weight: 900; letter-spacing: 8px; color: var(--green); text-shadow: 0 0 20px var(--green); margin-bottom: 10px; }
.welcome-sub { font-family: var(--font-co); font-size: 11px; letter-spacing: 3px; color: var(--text); }

.node-header { padding: 16px 24px; background: rgba(8, 13, 24, 0.4); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.node-title { display: flex; align-items: center; gap: 14px; }
.node-dot-lg { width: 12px; height: 12px; border-radius: 50%; background: var(--border2); }
.node-dot-lg.connected { background: var(--green); box-shadow: 0 0 12px var(--green); }
.node-title-name { font-family: var(--font-hd); font-size: 18px; font-weight: 700; color: var(--textwh); letter-spacing: 1px; }
.node-title-sub { font-family: var(--font-co); font-size: 11px; color: var(--text); margin-top: 4px; }
.device-badge { margin-left: 8px; padding: 2px 8px; border-radius: 4px; font-size: 9px; text-transform: uppercase; font-family: var(--font-hd); border: 1px solid var(--border); }
.device-badge.linux { color: var(--green); border-color: var(--green); }
.device-badge.rpi { color: var(--pink); border-color: var(--pink); }
.device-badge.gns3 { color: var(--cyan); border-color: var(--cyan); }

.header-actions { display: flex; gap: 8px; }
.btn-action { background: rgba(12, 18, 32, 0.6); border: 1px solid var(--border); color: var(--textwh); padding: 6px 12px; border-radius: var(--r); font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; cursor: pointer; transition: all .2s; }
.btn-action:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); box-shadow: var(--shadow-c); background: rgba(0, 229, 255, 0.1); }
.btn-action:disabled { opacity: .4; cursor: not-allowed; }

.btn-danger { border-color: var(--pink); color: var(--pink); }
.btn-danger:hover:not(:disabled) { 
  background: rgba(255, 45, 110, 0.2); 
  border-color: #ff0055; 
  color: #ff0055; 
  box-shadow: 0 0 15px #ff0055, inset 0 0 10px rgba(255, 0, 85, 0.3);
  text-shadow: 0 0 5px #ff0055;
}

.btn-reboot { border-color: #ffaa00; color: #ffaa00; }
.btn-reboot:hover:not(:disabled) {
  background: rgba(255, 170, 0, 0.2);
  border-color: #ffcc00;
  color: #ffcc00;
  box-shadow: 0 0 15px #ffaa00, inset 0 0 10px rgba(255, 170, 0, 0.3);
  text-shadow: 0 0 5px #ffaa00;
}

.tab-bar { background: rgba(8, 13, 24, 0.4); border-bottom: 1px solid var(--border); display: flex; padding: 0 14px; overflow-x: auto; }
.tab { white-space: nowrap; background: none; border: none; padding: 12px 18px; font-family: var(--font-hd); font-size: 10px; letter-spacing: 2px; color: var(--text); cursor: pointer; position: relative; transition: color .2s; }
.tab:hover { color: var(--textwh); }
.tab.active { color: var(--cyan); }
.tab.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: var(--cyan); box-shadow: 0 0 8px var(--cyan); }

.tab-content { flex: 1; overflow: hidden; position: relative; background: rgba(5, 8, 15, 0.3); }

.flash-stack { position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; gap: 10px; z-index: 1000; }
.flash { padding: 14px 20px; border-radius: var(--r); font-family: var(--font-co); font-size: 12px; border: 1px solid var(--border); min-width: 240px; box-shadow: 0 8px 32px rgba(0,0,0,.5); backdrop-filter: blur(8px); animation: slide-in .3s ease-out; }
@keyframes slide-in { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.flash.ok { background: rgba(0,255,157,.1); border-color: var(--green); color: var(--green); }
.flash.err { background: rgba(255,45,110,.1); border-color: var(--pink); color: var(--pink); }

.global-error-console {
  position: fixed;
  bottom: 24px;
  left: 24px;
  width: 480px;
  max-width: 90vw;
  background: rgba(18, 2, 2, 0.95);
  border: 2px solid #ff2d6e;
  box-shadow: 0 0 25px rgba(255, 45, 110, 0.4);
  border-radius: var(--r);
  z-index: 9999;
  font-family: monospace;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.console-header {
  background: rgba(255, 45, 110, 0.15);
  border-bottom: 1px solid rgba(255, 45, 110, 0.3);
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.console-indicator {
  color: #ff2d6e;
  font-size: 11px;
  font-weight: bold;
  letter-spacing: 1px;
  text-shadow: 0 0 8px #ff2d6e;
}

.btn-console-clear {
  background: transparent;
  border: 1px solid #ff2d6e;
  color: #ff2d6e;
  padding: 2px 8px;
  font-size: 9px;
  cursor: pointer;
  border-radius: 4px;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-console-clear:hover {
  background: #ff2d6e;
  color: #fff;
  box-shadow: 0 0 10px #ff2d6e;
}

.console-body {
  padding: 10px;
  max-height: 180px;
  overflow-y: auto;
  font-size: 11px;
}

.console-item {
  margin-bottom: 8px;
  border-bottom: 1px dashed rgba(255, 45, 110, 0.2);
  padding-bottom: 8px;
}

.console-item:last-child {
  margin-bottom: 0;
  border-bottom: none;
  padding-bottom: 0;
}

.console-msg {
  color: #ff2d6e;
  font-weight: bold;
}

.console-stack {
  color: #a0a0a0;
  font-size: 10px;
  margin-top: 4px;
  white-space: pre-wrap;
  max-height: 80px;
  overflow-y: auto;
}

/* Reboot Modal styles */
.reboot-overlay {
  backdrop-filter: blur(12px) saturate(120%);
  -webkit-backdrop-filter: blur(12px) saturate(120%);
  background: rgba(2, 4, 8, 0.7);
  transition: all 0.3s;
}
.reboot-card {
  border: 1px solid #ffaa00 !important;
  box-shadow: 0 0 25px rgba(255, 170, 0, 0.25) !important;
}
.reboot-card .cyber-modal-header.warning {
  background: rgba(255, 170, 0, 0.1) !important;
  border-bottom: 1px solid rgba(255, 170, 0, 0.3) !important;
}
.reboot-card .modal-title {
  color: #ffaa00 !important;
  text-shadow: 0 0 10px rgba(255, 170, 0, 0.5) !important;
}
.reboot-vectors {
  display: flex;
  gap: 16px;
  margin: 18px 0;
}
.vector-card {
  flex: 1;
  border: 1px solid var(--border);
  padding: 14px;
  cursor: pointer;
  border-radius: var(--r);
  position: relative;
  transition: all 0.2s ease-in-out;
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.vector-card:hover {
  border-color: var(--border2);
  background: rgba(255, 255, 255, 0.04);
}
.vector-card.active {
  border-color: #ffaa00;
  background: rgba(255, 170, 0, 0.06);
  box-shadow: 0 0 15px rgba(255, 170, 0, 0.15);
}
.vector-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 8px;
  color: var(--text);
  border: 1px solid var(--border);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-hd);
}
.vector-card.active .vector-badge {
  color: #ffaa00;
  border-color: #ffaa00;
  text-shadow: 0 0 4px #ffaa00;
}
.vector-icon {
  font-size: 24px;
  margin-bottom: 4px;
}
.vector-name {
  font-weight: bold;
  font-family: var(--font-hd);
  font-size: 11px;
  margin-bottom: 4px;
  color: var(--textwh);
}
.vector-desc {
  font-size: 10px;
  color: var(--text);
  line-height: 1.4;
}
.vector-preview {
  margin-top: 14px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--r);
  overflow: hidden;
}
.preview-header {
  font-size: 9px;
  color: var(--text);
  font-family: var(--font-hd);
  padding: 6px 10px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.02);
}
.preview-code {
  padding: 10px;
  margin: 0;
  font-family: var(--font-co);
  font-size: 10px;
  color: var(--cyan);
  white-space: pre-wrap;
  overflow-x: auto;
}
.modal-warning-box {
  margin-top: 14px;
  padding: 10px;
  border: 1px dashed rgba(255, 170, 0, 0.4);
  border-radius: var(--r);
  display: flex;
  gap: 10px;
  align-items: center;
  background: rgba(255, 170, 0, 0.02);
}
.warning-icon {
  font-size: 16px;
}
.warning-text {
  font-size: 10px;
  color: var(--text);
  line-height: 1.4;
}
.modal-error-box {
  margin-top: 14px;
  padding: 10px;
  border: 1px solid var(--pink);
  background: rgba(255, 45, 110, 0.05);
  border-radius: var(--r);
  font-family: var(--font-co);
}
.error-header {
  color: var(--pink);
  font-size: 10px;
  font-weight: bold;
  text-shadow: 0 0 5px var(--pink);
}
.error-msg {
  font-size: 10px;
  color: var(--textwh);
  margin-top: 4px;
}
</style>
