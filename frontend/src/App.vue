<template>
  <BootSequence v-if="showBoot" @done="showBoot = false" />
  <LoginView v-if="!loggedIn" @authenticated="onAuthenticated" />
  <div v-else class="app" :class="[{ holo: holoMode, 'glitch-effect': isGlitching }, `defcon-${store.defconLevel}`]">
    <div class="scanline"></div>

    <!-- HOLO MODE overlay -->
    <div v-if="holoMode" class="holo-fx">
      <div class="holo-grid"></div>
      <div class="holo-scan"></div>
      <div class="holo-corner tl"></div><div class="holo-corner tr"></div>
      <div class="holo-corner bl"></div><div class="holo-corner br"></div>
      <div class="holo-hud">▣ NETRUNNER HOLO-DECK · NEURAL LINK ACTIVE · {{ online }}/{{ monitoredCount }} NODES ONLINE</div>
    </div>



    <div class="app-body">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-stats">
        <div class="sidebar-stat">
          <div class="stat-label">NODES</div>
          <div class="stat-value">{{ store.nodeList.length }}</div>
        </div>
        <div class="sidebar-stat" @click="showSessionManager = true" style="cursor: pointer;" title="Manage Active Sessions">
          <div class="stat-label">LIVE</div>
          <div class="stat-value" :class="{ 'text-green': store.connectedCount > 0 }">{{ store.connectedCount }}</div>
        </div>
      </div>



      <div v-if="store.loading" class="sidebar-info">SCANNING NEURAL LINK...</div>
      <div v-if="store.error" class="sidebar-error">{{ store.error }}</div>

      <div class="sidebar-search" style="display: flex; gap: 8px;">
        <input v-model="searchQuery" placeholder="FILTER NODES..." class="search-input" style="flex: 1;" />
        <button v-if="userRole !== 'student'" class="btn-action" @click="showAddForm = true" title="Add New Node" style="height: 28px; padding: 0 10px; font-weight: bold;">[+] ADD</button>
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
              class="node-card stagger-item"
              :class="{ selected: store.selected?.id === node.id }"
              @click="selectNode(node)"
              @contextmenu.prevent="onEditNode(node.id)"
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
                <div class="node-host">
                  {{ node.host }}:{{ node.port }}
                  <span v-if="reachOf(node.id)" class="node-reach" :class="reachOf(node.id)!.cls">{{ reachOf(node.id)!.text }}</span>
                </div>
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
      <!-- Desktop Area -->
      <div class="desktop-area main-bg">
        <AmbientBackground :alert-level="alertLevel" />
      </div>
      <!-- Foreground Layer: Glass Panel -->
      <transition name="slide-panel">
        <div v-if="store.selected" class="glass-panel">
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
              <span v-if="selectedConsoleless" class="l2-note" title="GNS3 L2 device (switch/hub/cloud) — no interactive console">⚡ L2 DEVICE — NO CONSOLE</span>
              <template v-else>
                <button v-if="!store.isConnected(store.selected.id)" @click="doConnect" class="btn-action" :disabled="connBusy">CONNECT</button>
                <template v-else>
                  <button @click="doDisconnect" class="btn-action" :disabled="connBusy">DISCONNECT</button>
                  <button @click="doReboot" class="btn-action btn-reboot" :disabled="connBusy">REBOOT</button>
                </template>
              </template>
              <button @click="showEdit = true" class="btn-action btn-edit" title="Edit connection (host, port, transport, credentials)">EDIT</button>
              <button @click="detectType" class="btn-action">DETECT</button>
              <button @click="doBackup"   class="btn-action">BACKUP</button>
              <button @click="doRollback" class="btn-action">ROLLBACK</button>
              <button v-if="canDeleteNode" @click="deleteNode" class="btn-action btn-danger">NUKE CONFIG</button>
              <button @click="store.selectedId = null" class="btn-action" title="Close Node Dashboard">✕ CLOSE</button>
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
            >
              {{ tab.label }}
              <span v-if="tab.needsDocker" class="docker-led" title="Relies on Docker API"></span>
            </button>
          </div>

          <!-- Tab content -->
          <div class="tab-content">
            <OverviewPanel v-if="activeTab === 'overview'" :node-id="store.selected.id" />
            <SystemPanel  v-if="activeTab === 'system'"   :node-id="store.selected.id" />
            <WorkloadsPanel v-if="activeTab === 'workloads'" :node-id="store.selected.id" />
            <SecurityPanel v-if="activeTab === 'security'" :node-id="store.selected.id" />
            <CapturePanel v-if="activeTab === 'network'"  :node-id="store.selected.id" />
            <UsbPanel     v-if="activeTab === 'usb'"      :node-id="store.selected.id" />
            <ShellPanel   v-if="activeTab === 'terminal'" :node="store.selected" :active="activeTab === 'terminal'" />
            <FileExplorerPanel v-if="activeTab === 'files'" :node-id="store.selected.id" />
          </div>
        </div>
      </transition>

      <!-- Desktop OS Apps via WindowManager -->
      <WindowFrame
        v-for="win in windowStore.windows"
        :key="win.id"
        :winId="win.id"
      >
        <component
          :is="getComponentMap(win.component)"
          v-bind="win.props"
          :autopilotActive="systemState.autopilot"
          :chaosActive="systemState.chaos"
          :systemState="systemState"
          @toggle-autopilot="toggleAutopilot"
          @toggle-chaos="toggleChaos"
        />
      </WindowFrame>
    </main>
    </div>

    <!-- Modals -->
    <NodeForm v-if="showAddForm" @close="showAddForm = false" />
    <NodeForm v-if="showEdit"    :node="store.selected" @close="showEdit = false" />
    <SessionManagerModal v-if="showSessionManager" @close="showSessionManager = false" />
    <SettingsModal v-if="showSettings" @close="showSettings = false" />
    <UserManagementModal v-if="showUsers" @close="showUsers = false" />
    <VpnManagerModal v-if="showVpn" @close="showVpn = false" />

    <!-- Command palette (Ctrl/Cmd+K) -->
    <div v-if="showPalette" class="cmd-overlay" @click.self="showPalette = false">
      <div class="cmd-box">
        <input ref="cmdInput" v-model="paletteQuery" class="cmd-input" placeholder="› command or node…  (Ctrl+K)" @keydown="paletteKeydown" />
        <div class="cmd-list">
          <div
            v-for="(c, i) in paletteResults" :key="c.id"
            class="cmd-item" :class="{ active: i === paletteIndex }"
            @click="runPaletteItem(c)" @mouseenter="paletteIndex = i"
          >
            <span class="cmd-icon">{{ c.icon }}</span><span class="cmd-label">{{ c.label }}</span>
          </div>
          <div v-if="paletteResults.length === 0" class="cmd-empty">No matches.</div>
        </div>
        <div class="cmd-hint">↑↓ navigate · ↵ run · esc close</div>
      </div>
    </div>

    <!-- Alerts feed -->
    <div v-if="showAlerts" class="alerts-overlay" @click.self="showAlerts = false">
      <div class="alerts-panel">
        <div class="alerts-head">
          <span>🔔 ALERTS &amp; EVENTS</span>
          <div class="alerts-head-actions">
            <button v-if="events.length" class="alerts-clear" @click="clearEvents">CLEAR</button>
            <button class="alerts-close" @click="showAlerts = false">×</button>
          </div>
        </div>
        <div class="alerts-filter">
          <button class="af-chip" :class="{ active: alertFilter === 'all' }" @click="alertFilter = 'all'">ALL · {{ events.length }}</button>
          <button class="af-chip" :class="{ active: alertFilter === 'important' }" @click="alertFilter = 'important'">IMPORTANT · {{ alertCounts.critical + alertCounts.warning }}</button>
          <span class="af-counts">🔴 {{ alertCounts.critical }} · 🟡 {{ alertCounts.warning }} · 🔵 {{ alertCounts.info }}</span>
        </div>
        <div class="alerts-body">
          <div v-for="e in filteredAlerts" :key="e.id" class="alert-row" :class="e.severity">
            <span class="alert-sev">{{ sevIcon(e.severity) }}</span>
            <div class="alert-meta">
              <div class="alert-msg">{{ e.message }}</div>
              <div class="alert-sub">{{ e.kind }} · {{ eventAgo(e.ts) }}</div>
            </div>
          </div>
          <div v-if="filteredAlerts.length === 0" class="alerts-empty">
            {{ events.length === 0 ? 'No events yet — all clear. ✅' : 'No important alerts. ✅' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Nuke Node Modal -->
    <div v-if="showConfirmDelete" class="modal-overlay nuke-overlay" @click.self="showConfirmDelete = false">
      <div class="cyber-modal-card nuke-card glitch-box">
        <div class="cyber-modal-header critical">
          <div class="modal-title">⚠️ CRITICAL WARNING</div>
          <button class="btn-close-modal" @click="showConfirmDelete = false">×</button>
        </div>
        <div class="cyber-modal-body" style="text-align: center;">
          <p class="nuke-warning-text">
            You are about to <span class="neon-pink">NUKE</span> the node:<br/>
            <strong class="target-node">[{{ store.selected?.name }}]</strong>
          </p>
          <p class="nuke-subtext">
            This action is irreversible. All configurations and connections will be lost.
          </p>
        </div>
        <div class="cyber-modal-footer center-actions">
          <button class="btn-action" @click="showConfirmDelete = false">ABORT</button>
          <button class="btn-action btn-nuke-confirm" @click="executeNuke">CONFIRM NUKE</button>
        </div>
      </div>
    </div>

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

    <StartMenu
      :isOpen="startMenuOpen"
      :holoMode="holoMode"
      :audioEnabled="audioEnabled"
      :currentUsername="store.username || 'unknown'"
      :userRole="userRole"
      @launch-app="launchApp"
      @toggle-holo="toggleHolo"
      @toggle-audio="toggleAudio"
      @open-settings="showSettings = true"
      @logout="logout"
      @close="startMenuOpen = false"
    />

    <Taskbar
      :startMenuOpen="startMenuOpen"
      :backendApiStatus="backendApiStatus"
      :serviceStatus="serviceStatus"
      @toggle-start="startMenuOpen = !startMenuOpen"
      @show-desktop="handleShowDesktop"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, provide, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNodesStore } from '@/stores/nodes'
import { useWindowStore } from '@/stores/windows'
import Taskbar from './components/Taskbar.vue'
import StartMenu from './components/StartMenu.vue'
import WindowFrame from './components/WindowFrame.vue'
import AmbientBackground from './components/AmbientBackground.vue'
import { AppRegistry } from './registry'
import { api, sendUiEvent } from '@/api/client'
const SystemPanel = defineAsyncComponent(() => import('./components/SystemPanel.vue'))
const WorkloadsPanel = defineAsyncComponent(() => import('./components/WorkloadsPanel.vue'))
const SecurityPanel = defineAsyncComponent(() => import('./components/SecurityPanel.vue'))
const CapturePanel = defineAsyncComponent(() => import('./components/CapturePanel.vue'))
const OverviewPanel    = defineAsyncComponent(() => import('./components/OverviewPanel.vue'))
const ShellPanel       = defineAsyncComponent(() => import('./components/ShellPanel.vue'))
const UsbPanel         = defineAsyncComponent(() => import('./components/UsbPanel.vue'))
const FileExplorerPanel = defineAsyncComponent(() => import('./components/FileExplorerPanel.vue'))
const VpnManagerModal  = defineAsyncComponent(() => import('./components/VpnManagerModal.vue'))
const AttackMatrix = defineAsyncComponent(() => import('./components/AttackMatrix.vue'))
import { useNocAudio } from '@/composables/useNocAudio'
import { useAmbient } from '@/composables/useAmbient'
const BootSequence = defineAsyncComponent(() => import('./components/BootSequence.vue'))
const NodeForm  = defineAsyncComponent(() => import('./components/NodeForm.vue'))
const SessionManagerModal = defineAsyncComponent(() => import('./components/SessionManagerModal.vue'))
const TopologyView = defineAsyncComponent(() => import('./components/TopologyView.vue'))
const ReconView = defineAsyncComponent(() => import('./components/ReconView.vue'))
const BruteforceControlRoom = defineAsyncComponent(() => import('@/components/BruteforceControlRoom.vue'))
const DatabaseControlView = defineAsyncComponent(() => import('@/views/DatabaseControlView.vue'))
const KnowledgeGraph = defineAsyncComponent(() => import('./components/KnowledgeGraph.vue'))
const ThreatTimeline = defineAsyncComponent(() => import('./components/ThreatTimeline.vue'))
const AiChatSidebar = defineAsyncComponent(() => import('./components/AiChatSidebar.vue'))
const SettingsModal = defineAsyncComponent(() => import('./components/SettingsModal.vue'))
const UserManagementModal = defineAsyncComponent(() => import('./components/UserManagementModal.vue'))
const LoginView = defineAsyncComponent(() => import('./components/LoginView.vue'))
const HostControlView = defineAsyncComponent(() => import('@/views/HostControlView.vue'))
import type { NrNode } from '@/types'

const route = useRoute()
const router = useRouter()

const loggedIn = ref(!!localStorage.getItem('nr_token'))
const userRole = ref(localStorage.getItem('nr_role') || 'analyst')
const canDeleteNode = computed(() => {
  if (userRole.value === 'admin') return true;
  if (!store.selected) return false;
  const deviceType = store.selected.device_type?.toLowerCase() || '';
  if (['gns3', 'rpi', 'raspberry pi', 'raspberry_pi'].includes(deviceType)) {
    return true;
  }
  return false;
})
const currentUsername = ref(localStorage.getItem('nr_username') || '')

const showSessionManager = ref(false)
const showConfirmDelete = ref(false)
const showBoot = ref(false)
const showAddForm = ref(false)
provide('userRole', userRole)

const CONSOLELESS_TYPES = ['ethernet_switch', 'ethernet_hub', 'frame_relay_switch', 'atm_switch', 'cloud', 'nat']
const selectedConsoleless = computed(() => {
  const nt = (store.selected as any)?.metadata?.gns3?.node_type
  return !!nt && CONSOLELESS_TYPES.includes(nt)
})

// NOC audio (voice + synth alarms on alerts)
const { enabled: audioEnabled, toggle: toggleAudio, announce: announceEvent } = useNocAudio()

// HOLO MODE — holographic overlay + reactive ambient drone
const ambient = useAmbient()
const holoMode = ref(localStorage.getItem('nr_holo') === 'on')
function toggleHolo() {
  holoMode.value = !holoMode.value
  localStorage.setItem('nr_holo', holoMode.value ? 'on' : 'off')
  if (holoMode.value) ambient.start(); else ambient.stop()
}

// Infrastructure events / alerts
interface EventItem { id: number; ts: number; severity: string; node_id: string; node_name: string; kind: string; message: string }
const events = ref<EventItem[]>([])

onMounted(() => {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    const interactable = target.closest('button, a, .node, .btn, .nav-link, .tab')
    if (interactable) {
      const text = interactable.textContent?.replace(/\s+/g, ' ').trim().substring(0, 50) 
        || interactable.getAttribute('title') 
        || interactable.id 
        || 'unknown'
      sendUiEvent('click', window.location.pathname, text)
    }
  })
})
const showAlerts = ref(false)
const seenEventId = ref(0)
let eventsBaselineSet = false
const unreadCount = computed(() => events.value.filter(e => e.id > seenEventId.value).length)

const isGlitching = ref(false)
function triggerGlitch() {
  isGlitching.value = true
  setTimeout(() => isGlitching.value = false, 400)
}

const alertFilter = ref<'all' | 'important'>('all')
const alertCounts = computed(() => ({
  critical: events.value.filter(e => e.severity === 'critical').length,
  warning: events.value.filter(e => e.severity === 'warning').length,
  info: events.value.filter(e => e.severity === 'info').length,
}))
const alertLevel = computed(() => {
  if (alertCounts.value.critical > 0) return 'critical'
  if (alertCounts.value.warning > 0) return 'elevated'
  return 'normal'
})
const filteredAlerts = computed(() => alertFilter.value === 'important'
  ? events.value.filter(e => e.severity !== 'info')
  : events.value)

// Ambient drone tenses up as alerts accumulate
watch(alertCounts, (c) => ambient.setIntensity(Math.min(1, c.critical / 3 + c.warning / 8)))

function sevIcon(s: string) { return s === 'critical' ? '🔴' : s === 'warning' ? '🟡' : '🔵' }
function eventAgo(ts: number) {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts))
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

async function fetchEvents() {
  try {
    const res = await api.events()
    const incoming = res.events  // newest first
    const prevMax = events.value.length ? events.value[0].id : 0
    if (!eventsBaselineSet) {
      // Don't toast historical events on first load
      seenEventId.value = incoming.length ? incoming[0].id : 0
      eventsBaselineSet = true
    } else {
      for (const e of incoming.filter(e => e.id > prevMax).reverse()) {
        if (e.severity === 'critical' || e.severity === 'warning') {
          flash(`${sevIcon(e.severity)} ${e.message}`, 'err')
          announceEvent(e)
          if (e.severity === 'critical') triggerGlitch()
        }
      }
    }
    events.value = incoming
  } catch { /* non-fatal */ }
}

function openAlerts() {
  showAlerts.value = true
  if (events.value.length) seenEventId.value = events.value[0].id  // mark read
}

async function clearEvents() {
  try {
    await api.clearEvents()
    events.value = []
    seenEventId.value = 0
  } catch (e) { flash(String(e), 'err') }
}

// --- Command palette (Ctrl/Cmd+K) ---
const showPalette = ref(false)
const paletteQuery = ref('')
const paletteIndex = ref(0)
const cmdInput = ref<HTMLInputElement | null>(null)

async function connectById(id: string) {
  try { await api.connectNode(id); store.manuallyDisconnected.delete(id); await store.refreshConnections(); flash('Connected') }
  catch (e) { flash(String(e), 'err') }
}
async function disconnectById(id: string) {
  try { await api.disconnectNode(id); store.manuallyDisconnected.add(id); await store.refreshConnections() }
  catch (e) { flash(String(e), 'err') }
}

async function runDemoStorm() {
  try { await api.demoStorm(); flash('⚡ Incident simulation started…') }
  catch (e) { flash(String(e), 'err') }
}

interface Cmd { id: string; label: string; icon: string; run: () => void }
const allCommands = computed<Cmd[]>(() => {
  const cmds: Cmd[] = []
  const views: [string, string][] = [
    ['pulse', '⚡ Network Pulse'], ['node', '🖥️ Nodes'], ['topology', '🕸️ Topology'],
    ['attack', '🎯 ATT&CK Matrix'], ['threat', '🌐 Threat Map'], ['history', '🕗 History'], ['bruteforce', '🎯 Control Room'], ['database', '🗄️ Database Control'], ['wifi', '📶 WiFi & CSI'], ['warroom', '🚨 War Room'],
  ]
  for (const [vm, label] of views) cmds.push({ id: 'view-' + vm, label: 'Go to ' + label, icon: '↦', run: () => { viewMode.value = vm as any } })
  for (const n of store.nodeList) {
    cmds.push({ id: 'sel-' + n.id, label: `Select ${n.name}`, icon: '📍', run: () => { store.select(n.id); viewMode.value = 'node' as any } })
    if (store.isConnected(n.id)) cmds.push({ id: 'disc-' + n.id, label: `Disconnect ${n.name}`, icon: '■', run: () => disconnectById(n.id) })
    else cmds.push({ id: 'conn-' + n.id, label: `Connect ${n.name}`, icon: '▶', run: () => connectById(n.id) })
  }
  cmds.push({ id: 'add', label: 'Add node', icon: '➕', run: () => { showAddForm.value = true } })
  cmds.push({ id: 'codex', label: 'Open Cyberdeck Codex', icon: '📖', run: () => launchApp({ id: 'app_codex', component: 'codex', title: 'Cyberdeck Codex', icon: '📖' }) })
  if (userRole.value === 'admin') cmds.push({ id: 'users', label: 'User management', icon: '👤', run: () => { showUsers.value = true } })
  if (userRole.value === 'admin') cmds.push({ id: 'vpn', label: 'VPN Manager', icon: '🛡️', run: () => { showVpn.value = true } })
  cmds.push({ id: 'settings', label: 'Settings', icon: '⚙️', run: () => { showSettings.value = true } })
  cmds.push({ id: 'alerts', label: 'Open alerts', icon: '🔔', run: openAlerts })
  cmds.push({ id: 'pmf', label: 'PMF (802.11w) Config', icon: '🔒', run: () => { if (store.selected?.id) { viewMode.value = 'node' as any; activeTab.value = 'system' as any; nextTick(() => window.dispatchEvent(new CustomEvent('open-config-type', { detail: 'pmf' }))) } else { flash('Select a node first', 'err') } } })
  cmds.push({ id: 'wpa3', label: 'WPA3-SAE Config', icon: '🔐', run: () => { if (store.selected?.id) { viewMode.value = 'node' as any; activeTab.value = 'system' as any; nextTick(() => window.dispatchEvent(new CustomEvent('open-config-type', { detail: 'wpa3-sae' }))) } else { flash('Select a node first', 'err') } } })
  cmds.push({ id: 'owe', label: 'OWE (Open Encryption)', icon: '📡', run: () => { if (store.selected?.id) { viewMode.value = 'node' as any; activeTab.value = 'system' as any; nextTick(() => window.dispatchEvent(new CustomEvent('open-config-type', { detail: 'owe' }))) } else { flash('Select a node first', 'err') } } })
  cmds.push({ id: 'eaptls', label: '802.1X / EAP-TLS', icon: '🏛️', run: () => { if (store.selected?.id) { viewMode.value = 'node' as any; activeTab.value = 'system' as any; nextTick(() => window.dispatchEvent(new CustomEvent('open-config-type', { detail: 'eaptls' }))) } else { flash('Select a node first', 'err') } } })
  cmds.push({ id: 'audio', label: audioEnabled.value ? 'Mute NOC audio' : 'Enable NOC audio', icon: '🔊', run: toggleAudio })
  cmds.push({ id: 'holo', label: holoMode.value ? 'Disable HOLO mode' : 'Enable HOLO mode', icon: '🛸', run: toggleHolo })
  if (userRole.value === 'admin' && store.simulationMode) cmds.push({ id: 'storm', label: 'Simulate incident (demo storm)', icon: '⚡', run: runDemoStorm })
  cmds.push({ id: 'logout', label: 'Log out', icon: '⏻', run: logout })

  if (userRole.value === 'student') {
    return cmds.filter(c => {
      if (c.id.startsWith('conn-') || c.id.startsWith('disc-') || c.id === 'add') return false
      if (c.id === 'view-attack' || c.id === 'view-database' || c.id === 'view-bruteforce') return false
      if (['pmf', 'wpa3', 'owe', 'eaptls'].includes(c.id)) return false
      return true
    })
  }
  return cmds
})
const paletteResults = computed<Cmd[]>(() => {
  const q = paletteQuery.value.trim().toLowerCase()
  const list = q ? allCommands.value.filter(c => c.label.toLowerCase().includes(q)) : allCommands.value
  return list.slice(0, 14)
})
watch(paletteQuery, () => { paletteIndex.value = 0 })

function openPalette() {
  showPalette.value = true; paletteQuery.value = ''; paletteIndex.value = 0
  nextTick(() => cmdInput.value?.focus())
}
function runPaletteItem(c: Cmd) { showPalette.value = false; c.run() }
function paletteKeydown(e: KeyboardEvent) {
  const n = paletteResults.value.length
  if (e.key === 'ArrowDown') { e.preventDefault(); paletteIndex.value = Math.min(paletteIndex.value + 1, n - 1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); paletteIndex.value = Math.max(0, paletteIndex.value - 1) }
  else if (e.key === 'Enter') { e.preventDefault(); const c = paletteResults.value[paletteIndex.value]; if (c) runPaletteItem(c) }
  else if (e.key === 'Escape') { showPalette.value = false }
}
function globalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    if (loggedIn.value) { showPalette.value ? (showPalette.value = false) : openPalette() }
  }
}

// --- Voice control (speech → command) ---
const listening = ref(false)
let recog: any = null
function speakBack(text: string) {
  if (!('speechSynthesis' in window)) return
  try { const u = new SpeechSynthesisUtterance(text); u.rate = 1.05; u.pitch = 0.9; window.speechSynthesis.speak(u) } catch { /* */ }
}
const VOICE_SYN: Record<string, string> = { attack: 'incident', storm: 'incident', map: 'topology', dashboard: 'pulse', disconnect: 'disconnect', mute: 'audio', unmute: 'audio', logout: 'log out' }
function matchVoice(transcript: string) {
  let lower = ' ' + transcript.toLowerCase().replace(/[^a-z0-9 ]/g, '') + ' '
  for (const [k, v] of Object.entries(VOICE_SYN)) lower = lower.replace(new RegExp(`\\b${k}\\b`, 'g'), v)
  const words = lower.trim().split(/\s+/).filter(w => w.length > 1)
  let best: any = null, bestScore = 0
  for (const c of allCommands.value) {
    const label = c.label.toLowerCase().replace(/[^a-z0-9 ]/g, '')
    const score = words.reduce((s, w) => s + (label.includes(w) ? 1 : 0), 0)
    if (score > bestScore) { bestScore = score; best = c }
  }
  if (best && bestScore > 0) {
    const clean = best.label.replace(/[^\w\s]/g, '').trim()
    flash(`🎙️ "${transcript}" → ${best.label}`)
    speakBack(clean)
    best.run()
  } else {
    flash(`🎙️ "${transcript}" — no match`, 'err')
    speakBack('Command not recognized')
  }
}
function startVoice() {
  const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
  if (!SR) { flash('Voice control not supported in this browser', 'err'); return }
  if (listening.value && recog) { recog.stop(); return }
  recog = new SR()
  recog.lang = 'en-US'; recog.interimResults = false; recog.maxAlternatives = 1
  recog.onresult = (e: any) => { matchVoice(e.results[0][0].transcript) }
  recog.onend = () => { listening.value = false }
  recog.onerror = () => { listening.value = false }
  try { recog.start(); listening.value = true; flash('🎙️ Listening…') } catch { listening.value = false }
}

// Active reachability (TCP probe) shown as a dot/latency in the node list
const reachability = ref<Record<string, { reachable: boolean, latency_ms: number | null }>>({})
const monitoredCount = computed(() => store.nodeList.filter(n => !CONSOLELESS_TYPES.includes((n as any).metadata?.gns3?.node_type)).length)
const online = computed(() => store.nodeList.filter(n => !CONSOLELESS_TYPES.includes((n as any).metadata?.gns3?.node_type) && reachability.value[n.id]?.reachable).length)
async function fetchReachability() {
  try { reachability.value = await api.nodeReachability() } catch { /* non-fatal */ }
}
function reachOf(id: string): { cls: string, text: string } | null {
  const nt = (store.nodes[id] as any)?.metadata?.gns3?.node_type
  if (nt && CONSOLELESS_TYPES.includes(nt)) return { cls: 'l2', text: '⚡ L2' }
  const r = reachability.value[id]
  if (!r) return null
  return r.reachable
    ? { cls: 'up', text: `🟢 ${r.latency_ms}ms` }
    : { cls: 'down', text: '🔴 offline' }
}

function onEditNode(id: string) {
  store.select(id)
  showEdit.value = true
}

async function nukeAllNodes() {
  if (!confirm("Er du sikker på, at du vil slette ALLE nodes fra systemet (inkl. nedlægge evt. docker-containere)?")) return
  try {
    const res = await api.nukeTestDockers()
    if (res.ok) {
      alert("Alle nodes og test-containere er blevet fjernet!")
      store.refresh() // Refresh UI list
    } else {
      alert("Fejl: " + res.error)
    }
  } catch (err) {
    console.error(err)
    alert("Kunne ikke forbinde til serveren for at slette nodes.")
  }
}

function logout() {
  localStorage.removeItem('nr_token')
  localStorage.removeItem('nr_role')
  localStorage.removeItem('nr_username')
  loggedIn.value = false
  userRole.value = 'analyst'
  currentUsername.value = ''
  windowStore.$reset()
  disconnectLiveAlerts()
}

const isGlobalFullscreen = ref(false)

function toggleGlobalFullscreen() {
  isGlobalFullscreen.value = !isGlobalFullscreen.value
  if (isGlobalFullscreen.value) {
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {})
    }
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(() => {})
    }
  }
}

function handleGlobalNativeFullscreenChange() {
  isGlobalFullscreen.value = !!document.fullscreenElement
}

async function onAuthenticated(role: string) {
  userRole.value = role
  currentUsername.value = localStorage.getItem('nr_username') || ''
  loggedIn.value = true
  showBoot.value = true

  if (role === 'student' && !isStudentRouteAllowed(route.name)) {
    await router.replace({ name: 'dashboard' })
  }

  store.refresh()
  pollSystem()
  fetchReachability()
  fetchEvents()
  connectLiveAlerts()
  await nextTick()
  launchRouteApp(route.name)
}

// Automatically logout when token expires
window.addEventListener('auth-expired', () => {
  loggedIn.value = false
  userRole.value = 'analyst'
  currentUsername.value = ''
  windowStore.$reset()
  disconnectLiveAlerts()
})

let liveAlertsWs: WebSocket | null = null

function disconnectLiveAlerts() {
  const socket = liveAlertsWs
  liveAlertsWs = null
  socket?.close()
}

function connectLiveAlerts() {
  if (liveAlertsWs) return
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = import.meta.env.VITE_API_URL 
    ? import.meta.env.VITE_API_URL.replace(/^http/, 'ws') + `/ws/alerts${wsTokenParam()}`
    : `${protocol}//${window.location.host}/ws/alerts${wsTokenParam()}`

  liveAlertsWs = new WebSocket(wsUrl)
  
  liveAlertsWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'NODE_DATA') {
        // Node stats received (Agent Injection)
        flash(`Stats received for node ${data.data.node_id}`, 'info')
        console.log("Agent Stats:", data.data)
      } else if (data.type === 'NODE_ERROR') {
        flash(`Error from agent on node ${data.node_id}: ${data.error}`, 'err')
      }
    } catch (e) {
      console.error("Live alerts error:", e)
    }
  }
  
  liveAlertsWs.onclose = () => {
    liveAlertsWs = null
    if (loggedIn.value) {
      setTimeout(connectLiveAlerts, 5000)
    }
  }
}

const store       = useNodesStore()
const windowStore = useWindowStore()

const selectNode = (n: NrNode) => {
  console.log("Left click detected on:", n.name)
  store.select(n.id)
  windowStore.windows.forEach(w => w.isMinimized = true)
  flash('Skiftede til ' + n.name, 'ok')
}

watch(() => store.selectedId, (newId) => {
  if (newId) {
    windowStore.windows.forEach(w => w.isMinimized = true)
  }
})

const startMenuOpen = ref(false)

const launchApp = (appDef: { id: string, component: string, title: string, icon: string, width?: number, height?: number }) => {
  windowStore.openWindow({
    id: appDef.id,
    title: appDef.title,
    component: appDef.component,
    icon: appDef.icon,
    width: appDef.width || 900,
    height: appDef.height || 600,
    x: 150 + (windowStore.windows.length * 40),
    y: 100 + (windowStore.windows.length * 40)
  })
}

const STUDENT_ROUTE_NAMES = new Set(['dashboard', 'reports', 'topology', 'alerts', 'home', 'network', 'node'])

const ROUTE_WINDOW_META: Record<string, { title: string, icon: string, width?: number, height?: number }> = {
  alerts: { title: 'Alert Inbox', icon: '🚨' },
  attack: { title: 'Attack Matrix', icon: '☠️' },
  bruteforce: { title: 'Bruteforce Ops', icon: '🎯' },
  compliance: { title: 'Compliance', icon: '📋' },
  dashboard: { title: 'Dashboard', icon: '⎈' },
  database: { title: 'Database Control', icon: '🗄️', width: 1000, height: 800 },
  exfil: { title: 'Exfiltration', icon: '📤' },
  forensics: { title: 'Forensics', icon: '🔬' },
  history: { title: 'Threat Timeline', icon: '🕓' },
  host: { title: 'Local Host', icon: '💻' },
  hunting: { title: 'Threat Hunting', icon: '🔍' },
  intelligence: { title: 'Intelligence', icon: '🧠' },
  integrations: { title: 'Integrations', icon: '🔗' },
  ir: { title: 'Incident Response', icon: '🚑' },
  kismet: { title: 'Wireless IDS', icon: '📶' },
  lateral: { title: 'Lateral Movement', icon: '↔️' },
  layer2: { title: 'L2 Tactical', icon: '🔌' },
  layer3: { title: 'L3 Tactical', icon: '🌐' },
  layer4: { title: 'L4 Tactical', icon: '⚡' },
  layer5: { title: 'L5 Tactical', icon: '🎭' },
  layer6: { title: 'L6 Tactical', icon: '📦' },
  layer7: { title: 'L7 Tactical', icon: '🕸️' },
  logs: { title: 'Log Aggregation', icon: '📜' },
  network: { title: 'Network Controller', icon: '🔌' },
  playbooks: { title: 'Playbooks', icon: '🧠' },
  privesc: { title: 'Privilege Escalation', icon: '⬆️' },
  recon: { title: 'Subnet Scan', icon: '📡' },
  reports: { title: 'Reports', icon: '📑', width: 1000, height: 800 },
  'social-engineering': { title: 'Social Engineering', icon: '🎭' },
  topology: { title: 'Topology', icon: '🕸️' },
  'wifi-attack': { title: 'WiFi Attacks', icon: '📶' },
}

function isStudentRouteAllowed(routeName: unknown) {
  return typeof routeName === 'string' && STUDENT_ROUTE_NAMES.has(routeName)
}

function launchRouteApp(routeName: unknown) {
  let component = typeof routeName === 'string' && AppRegistry[routeName]
    ? routeName
    : 'dashboard'

  if (userRole.value === 'student' && !isStudentRouteAllowed(component)) {
    component = 'dashboard'
  }

  const meta = ROUTE_WINDOW_META[component] || {
    title: component.replace(/(^|-)(\w)/g, (_match, _separator, letter) => ` ${letter.toUpperCase()}`).trim(),
    icon: '▣',
  }
  launchApp({ id: `app_${component}`, component, ...meta })
}

watch(() => route.name, (routeName) => {
  if (loggedIn.value) {
    nextTick(() => launchRouteApp(routeName))
  }
})

const getComponentMap = (name: string) => {
  return AppRegistry[name] || 'div'
}
const viewMode = computed({
  get: () => (route.name as string) || 'node',
  set: (v) => router.push({ name: v })
})
const activeTab   = ref<'overview' | 'gns3-api' | 'diag' | 'config' | 'defense' | 'agents' | 'shaper' | 'capture' | 'terminal' | 'usb' | 'files'>(
  (localStorage.getItem('netrunner_active_tab') as any) || 'overview'
)
watch(activeTab, t => {
  localStorage.setItem('netrunner_active_tab', t)
  if (t === 'terminal') {
    nextTick(() => {
      // Focus will be handled by ShellPanel/Terminal active prop watcher & mount
    })
  }
})

function handleShowDesktop() {
  store.selectedId = null
  windowStore.windows.forEach(w => w.isMinimized = true)
}

const showEdit    = ref(false)
const showSettings = ref(false)
const showUsers   = ref(false)
const showVpn     = ref(false)
const searchQuery = ref('')
const connBusy    = ref(false)
const exporting   = ref(false)

// Reboot options modal state
const showRebootModal = ref(false)
const rebootMethod = ref<'command' | 'gns3'>('command')
const rebootLoading = ref(false)
const rebootError = ref('')

const systemState = ref({ autopilot: false, chaos: false })
const backendApiStatus = ref<'up' | 'down'>('up')
const serviceStatus = ref<Record<string, boolean>>({})
let lastLogCount = 0

// Global error tracking for remote diagnostics
const globalErrors = ref<{ id: number; message: string; stack?: string }[]>([])
let nextErrorId = 0

function logGlobalError(message: string, stack?: string) {
  const id = nextErrorId++
  globalErrors.value.push({ id, message, stack })
}

const handleWindowError = (event: ErrorEvent) => {
  if (event.message && event.message.includes('ResizeObserver loop')) {
    return; // Safely ignore benign ResizeObserver layout shifts
  }
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
function toggleSidebarCat(type: string) {
  const newSet = new Set(collapsedSidebarCats.value)
  if (newSet.has(type)) newSet.delete(type)
  else newSet.add(type)
  collapsedSidebarCats.value = newSet
}

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

const collapsedNavCats = ref(new Set(['infrastructure', 'recon', 'offensive']))
function toggleNavCat(cat: string) {
  if (collapsedNavCats.value.has(cat)) collapsedNavCats.value.delete(cat)
  else collapsedNavCats.value.add(cat)
}

const dynamicTabs = computed(() => {
  const list = [
    { id: 'overview', label: 'OVERVIEW' },
    { id: 'system',   label: 'SYSTEM', needsDocker: true },
    { id: 'workloads', label: 'WORKLOADS', needsDocker: true },
    { id: 'security', label: 'SECURITY' },
    { id: 'network',  label: 'NETWORK' },
    { id: 'usb',      label: 'USB DEVICES' },
    { id: 'terminal', label: 'TERMINAL' },
    { id: 'files',    label: 'FILES' }
  ] as { id: string; label: string; needsDocker?: boolean }[]
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

function deleteNode() {
  if (!store.selected) return
  showConfirmDelete.value = true
}

async function executeNuke() {
  if (!store.selected) return
  showConfirmDelete.value = false
  try {
    await store.remove(store.selected.id)
    flash('Node deleted')
  } catch (e) {
    flash(String(e), 'err')
  }
}

watch(() => store.selectedId, () => {
  // Keep the active tab persistent across node switches.
  // Fallback to overview if moving away from GNS3 control to a non-GNS3 device.
  const isGns3 = store.selected?.device_type === 'gns3'
  if (activeTab.value === 'gns3-api' && !isGns3) {
    activeTab.value = 'overview'
  }
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
    backendApiStatus.value = 'up'
    systemState.value = st
    serviceStatus.value = st.services || {}
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
  } catch(e) {
    backendApiStatus.value = 'down'
  }
}

let connTimer: ReturnType<typeof setInterval> | null = null
let sysTimer: ReturnType<typeof setInterval> | null = null
let reachTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  window.addEventListener('error', handleWindowError)
  window.addEventListener('unhandledrejection', handleUnhandledRejection)
  document.addEventListener('fullscreenchange', handleGlobalNativeFullscreenChange)
  window.addEventListener('keydown', globalKeydown)

  if (loggedIn.value) {
    store.refresh()
    pollSystem()
    fetchReachability()
    fetchEvents()
    if (holoMode.value) ambient.start()

    // Open the window that matches the current deep link.
    if (windowStore.windows.length === 0) {
      launchRouteApp(route.name)
    }
  }
  connTimer = setInterval(() => { if (loggedIn.value) store.refreshConnections() }, 4000)
  sysTimer  = setInterval(() => { if (loggedIn.value) pollSystem() }, 2000)
  reachTimer = setInterval(() => { if (loggedIn.value) { fetchReachability(); fetchEvents() } }, 5000)
})
onUnmounted(() => {
  window.removeEventListener('error', handleWindowError)
  window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  document.removeEventListener('fullscreenchange', handleGlobalNativeFullscreenChange)
  window.removeEventListener('keydown', globalKeydown)

  if (connTimer) clearInterval(connTimer)
  if (sysTimer) clearInterval(sysTimer)
  if (reachTimer) clearInterval(reachTimer)
})
</script>

<style scoped>
.app { display: flex; flex-direction: column; height: 100vh; overflow: hidden; position: relative; z-index: 1; background: var(--bg); }
.app-body { display: flex; flex: 1; overflow: hidden; position: relative; }

/* Topbar */
.topbar { display: flex; align-items: center; justify-content: space-between; height: 55px; padding: 0 20px; background: rgba(8, 13, 24, 0.65); backdrop-filter: blur(16px); border-bottom: 1px solid rgba(0, 229, 255, 0.15); z-index: 10; flex-shrink: 0; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5); }
.topbar-right { display: flex; align-items: center; gap: 24px; }
.topbar-status { display: flex; align-items: center; gap: 20px; font-family: var(--font-hd); font-size: 10px; color: var(--textbr); letter-spacing: 1px; }
.status-indicator { display: flex; align-items: center; gap: 6px; }

/* Sidebar (Floating Widget) */
.sidebar { position: absolute; right: 20px; top: 20px; bottom: 64px; width: 280px; background: rgba(12, 18, 32, 0.65); backdrop-filter: blur(16px); display: flex; flex-direction: column; z-index: 100; border-radius: var(--r2); border: 1px solid rgba(0,229,255,0.15); box-shadow: 0 15px 40px rgba(0,0,0,0.6); overflow: hidden; transition: all 0.3s ease; }
.sidebar::before { content: 'DEVICE MANAGER'; display: block; text-align: center; font-family: var(--font-hd); font-size: 10px; letter-spacing: 2px; color: var(--cyan); padding: 8px 0; background: rgba(0, 229, 255, 0.05); border-bottom: 1px solid rgba(0, 229, 255, 0.1); }
.sidebar::after { display: none; }

.header-tools { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 10px; margin-top: 5px; }
.tool-group { display: flex; align-items: center; gap: 6px; }

.logo { line-height: 1; }
.logo-title { font-family: var(--font-hd); font-size: 15px; font-weight: 900; letter-spacing: 3px; color: var(--green); text-shadow: 0 0 12px rgba(0,255,157,.6); }
.logo-sub { display: block; font-family: var(--font-co); font-size: 9px; letter-spacing: 2px; color: var(--text); margin-top: 5px; text-transform: uppercase; }
.api-led { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-left: 6px; vertical-align: middle; background: var(--border2); transition: all 0.3s; }
.api-led.up { background: var(--green); box-shadow: 0 0 6px var(--green); }
.api-led.down { background: var(--pink); box-shadow: 0 0 6px var(--pink); animation: led-pulse 1s infinite alternate; }
@keyframes led-pulse { from { opacity: 0.4; } to { opacity: 1; } }

.btn-icon { background: rgba(0,229,255,0.02); border: 1px solid rgba(0,229,255,0.1); font-size: 14px; cursor: pointer; color: var(--textbr); opacity: 0.8; transition: all 0.2s; padding: 4px; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 4px; }
.btn-icon:hover { opacity: 1; color: var(--cyan); border-color: var(--cyan); filter: drop-shadow(0 0 8px rgba(0,229,255,0.4)); background: rgba(0,229,255,0.1); transform: translateY(-1px); }

.btn-add { width: 28px; height: 28px; border-radius: 50%; background: none; border: 1px solid var(--cyan); color: var(--cyan); font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .2s; margin-left: 5px;}
.btn-add:hover { background: var(--cyan); color: var(--bg); box-shadow: var(--shadow-c); transform: translateY(-1px); }

.user-bar { display: flex; align-items: center; gap: 12px; font-family: var(--font-co); }
.user-bar .user-id { color: var(--textwh); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 110px; }
.user-bar .user-role { flex-shrink: 0; font-size: 9px; letter-spacing: 1px; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; font-weight: bold; }
.user-bar .user-role.admin { background: rgba(255,45,110,0.15); color: var(--pink); border: 1px solid rgba(255,45,110,0.5); box-shadow: 0 0 10px rgba(255,45,110,0.2); }
.user-bar .user-role.analyst { background: rgba(0,229,255,0.1); color: var(--cyan); border: 1px solid var(--cyan-d); box-shadow: 0 0 10px rgba(0,229,255,0.2); }
.user-actions { display: flex; gap: 8px; flex-shrink: 0; }
.btn-user-action { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.02); border: 1px solid var(--border2); color: var(--textbr); font-size: 14px; border-radius: 4px; cursor: pointer; transition: all .2s; }
.btn-user-action:hover { border-color: var(--cyan); color: var(--cyan); box-shadow: 0 0 8px rgba(0,229,255,0.2); transform: translateY(-1px); }
.btn-logout:hover { border-color: var(--pink); color: var(--pink); box-shadow: 0 0 8px rgba(255,45,110,0.2); transform: translateY(-1px); }

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

.node-card { display: flex; align-items: center; gap: 12px; padding: 12px; background: rgba(16, 24, 40, 0.4); border-radius: var(--r2); cursor: pointer; border: 1px solid rgba(0, 229, 255, 0.05); margin-bottom: 8px; transition: all .25s cubic-bezier(0.4, 0, 0.2, 1); position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.2); overflow: hidden; }
.node-card::before { content: ''; position: absolute; inset: 0; background: linear-gradient(135deg, rgba(0,229,255,0.1), transparent); opacity: 0; transition: opacity .3s; }
.node-card:hover { background: rgba(16, 24, 40, 0.8); border-color: rgba(0,229,255,0.3); transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.4), 0 0 12px rgba(0,229,255,0.1); }
.node-card:hover::before { opacity: 1; }
.node-card.selected { background: rgba(0,255,157,.08); border-color: rgba(0,255,157,.4); box-shadow: 0 0 15px rgba(0,255,157,.15); }
.node-card.selected::after { content: ''; position: absolute; left: 0; top: 0; height: 100%; width: 3px; background: var(--green); box-shadow: 0 0 10px var(--green); }

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

/* Main Desktop Workspace */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: transparent; position: relative; }
.main-bg { flex: 1; display: flex; flex-direction: column; position: absolute; inset: 0; z-index: 1; }
.main-bg.is-topology, .main-bg.is-threat { background: transparent; }

.glass-panel {
  position: absolute;
  top: 10px;
  bottom: 60px; /* leaves room for taskbar */
  left: 10px;
  right: 320px; /* leaves room for sidebar */
  display: flex;
  flex-direction: column;
  z-index: 10;
  background: var(--bg);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: var(--r2);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
  overflow: hidden;
}

.glass-panel.is-overlay {
  position: absolute;
  top: 20px;
  right: 320px; /* Offset by the sidebar width (280 + 40 margin) */
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
.welcome-logo { font-family: var(--font-hd); font-size: 42px; font-weight: 900; letter-spacing: 8px; color: var(--green); text-shadow: 0 0 20px var(--green); margin-bottom: 10px; text-align: center; }
.welcome-sub { font-family: var(--font-co); font-size: 11px; letter-spacing: 3px; color: var(--text); text-align: center; margin-bottom: 20px; }
.dashboard-stats { display: flex; gap: 20px; margin-top: 40px; justify-content: center; }
.dash-stat-box { background: rgba(8, 13, 24, 0.6); border: 1px solid var(--border2); padding: 25px 40px; border-radius: var(--r); text-align: center; cursor: pointer; transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94); box-shadow: 0 4px 15px rgba(0,0,0,0.4); backdrop-filter: blur(8px); }
.dash-stat-box:hover { transform: translateY(-3px); border-color: var(--cyan); box-shadow: 0 8px 25px rgba(0,229,255,0.15); background: rgba(8, 13, 24, 0.8); }
.ds-value { font-family: var(--font-hd); font-size: 32px; font-weight: bold; margin-bottom: 5px; color: var(--textwh); }
.ds-label { font-family: var(--font-co); font-size: 10px; color: var(--text); letter-spacing: 1px; }

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

.btn-edit { border-color: var(--cyan-d); color: var(--cyan); }
.l2-note { font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; color: var(--text); border: 1px dashed var(--border2); padding: 6px 10px; border-radius: var(--r); opacity: 0.8; }
.node-reach { margin-left: 8px; font-size: 9px; white-space: nowrap; }
.node-reach.up { color: var(--green); }
.node-reach.down { color: var(--pink); }
.node-reach.l2 { color: #ffbe0b; }
.btn-pulse { color: var(--cyan); font-weight: 700; }
.btn-pulse.active { box-shadow: inset 0 0 12px rgba(0,229,255,0.25); }

.cmd-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 11000; display: flex; justify-content: center; align-items: flex-start; padding-top: 14vh; backdrop-filter: blur(3px); }
.cmd-box { width: 560px; max-width: 92vw; background: rgba(10,16,30,0.98); border: 1px solid var(--cyan-d); border-radius: 10px; box-shadow: 0 20px 60px rgba(0,0,0,0.6), 0 0 30px rgba(0,229,255,0.15); overflow: hidden; }
.cmd-input { width: 100%; box-sizing: border-box; background: transparent; border: none; border-bottom: 1px solid var(--border); color: var(--textwh); font-family: var(--font-co); font-size: 16px; padding: 16px 18px; outline: none; }
.cmd-list { max-height: 50vh; overflow-y: auto; padding: 6px; }
.cmd-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 6px; cursor: pointer; font-family: var(--font-co); font-size: 13px; color: var(--text); }
.cmd-item.active { background: rgba(0,229,255,0.12); color: var(--textwh); box-shadow: inset 2px 0 0 var(--cyan); }
.cmd-icon { opacity: 0.6; font-size: 13px; display: inline-block; width: 16px; text-align: center; }
.cmd-label { flex: 1; font-size: 13px; }

/* Nuke Modal Styles */
.nuke-overlay {
  animation: glitch-in 0.2s ease-out;
  backdrop-filter: blur(10px) sepia(50%) hue-rotate(300deg) saturate(200%);
}
.nuke-card {
  border: 1px solid var(--pink);
  box-shadow: 0 0 30px rgba(255, 45, 110, 0.4), inset 0 0 20px rgba(255, 45, 110, 0.1);
}
.cyber-modal-header.critical {
  color: var(--pink);
  border-bottom: 1px solid var(--pink);
  text-shadow: 0 0 10px var(--pink);
  background: rgba(255, 45, 110, 0.1);
}
.nuke-warning-text {
  font-size: 1.1rem;
  margin-top: 1rem;
}
.neon-pink {
  color: var(--pink);
  font-weight: bold;
  text-shadow: 0 0 10px var(--pink);
  animation: glitch-flicker 2s infinite;
}
.target-node {
  font-size: 1.5rem;
  color: #fff;
  display: inline-block;
  margin-top: 0.5rem;
  text-shadow: 0 0 10px var(--pink);
}
.nuke-subtext {
  font-size: 0.9rem;
  color: #ff88aa;
  margin: 1.5rem 0;
  opacity: 0.8;
}
.center-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}
.btn-nuke-confirm {
  background: rgba(255, 45, 110, 0.2) !important;
  color: var(--pink) !important;
  border-color: var(--pink) !important;
  font-weight: bold;
}
.btn-nuke-confirm:hover {
  background: var(--pink) !important;
  color: #000 !important;
  box-shadow: 0 0 20px var(--pink) !important;
}

@keyframes glitch-flicker {
  0% { opacity: 1; }
  5% { opacity: 0.8; }
  10% { opacity: 1; }
  15% { opacity: 0.3; }
  20% { opacity: 1; }
  100% { opacity: 1; }
}
@keyframes glitch-in {
  0% { transform: scale(0.95); opacity: 0; filter: hue-rotate(90deg); }
  50% { transform: scale(1.02); filter: blur(2px); }
  100% { transform: scale(1); opacity: 1; filter: none; }
}

.cmd-empty { padding: 16px; text-align: center; color: var(--text); font-size: 13px; }
.cmd-hint { padding: 8px 14px; border-top: 1px solid var(--border); font-family: var(--font-co); font-size: 10px; color: var(--text); letter-spacing: 1px; }

.holo-on { filter: drop-shadow(0 0 6px var(--cyan)); }

/* HOLO MODE */
.holo-fx { position: fixed; inset: 0; z-index: 8000; pointer-events: none; overflow: hidden; animation: holoflick 6s infinite; }
.holo-grid {
  position: absolute; inset: -50%;
  background-image:
    linear-gradient(rgba(0,229,255,0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,255,0.07) 1px, transparent 1px);
  background-size: 44px 44px;
  transform: perspective(400px) rotateX(58deg) translateY(-10%);
  animation: holoscroll 16s linear infinite;
  opacity: 0.5;
}
.holo-scan {
  position: absolute; left: 0; right: 0; height: 140px;
  background: linear-gradient(180deg, transparent, rgba(0,229,255,0.10), transparent);
  animation: holosweep 5s linear infinite;
}
.holo-corner { position: absolute; width: 46px; height: 46px; border: 2px solid var(--cyan); opacity: 0.6; box-shadow: 0 0 14px rgba(0,229,255,0.4); }
.holo-corner.tl { top: 12px; left: 12px; border-right: none; border-bottom: none; }
.holo-corner.tr { top: 12px; right: 12px; border-left: none; border-bottom: none; }
.holo-corner.bl { bottom: 12px; left: 12px; border-right: none; border-top: none; }
.holo-corner.br { bottom: 12px; right: 12px; border-left: none; border-top: none; }
.holo-hud {
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  font-family: var(--font-hd); font-size: 10px; letter-spacing: 3px; color: var(--cyan);
  text-shadow: 0 0 10px rgba(0,229,255,0.7); white-space: nowrap; opacity: 0.85;
}
.app.holo { animation: holohue 8s infinite; }
.app.holo .main { box-shadow: inset 0 0 120px rgba(0,229,255,0.06); }
@keyframes holoscroll { to { background-position: 0 44px; } }
@keyframes holosweep { 0% { top: -140px; } 100% { top: 100%; } }
@keyframes holoflick { 0%,97%,100% { opacity: 1; } 98% { opacity: 0.82; } 99% { opacity: 0.94; } }
@keyframes holohue { 0%,100% { filter: none; } 50% { filter: hue-rotate(-8deg) saturate(1.1); } }

.btn-mic.listening { color: var(--pink); animation: micpulse 1s infinite; }
@keyframes micpulse { 50% { filter: drop-shadow(0 0 8px var(--pink)); opacity: 0.6; } }
.btn-bell { position: relative; }
.bell-badge {
  position: absolute; top: -6px; right: -8px;
  background: var(--pink); color: #fff; font-family: var(--font-co);
  font-size: 8px; font-weight: bold; line-height: 1;
  padding: 2px 4px; border-radius: 8px; min-width: 14px; text-align: center;
}
.alerts-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9000; backdrop-filter: blur(3px); }
.alerts-panel {
  position: absolute; top: 60px; right: 24px; width: 380px; max-width: 92vw;
  max-height: 70vh; display: flex; flex-direction: column;
  background: rgba(10,16,30,0.97); border: 1px solid var(--border);
  border-radius: var(--r); box-shadow: 0 12px 40px rgba(0,0,0,0.6);
  font-family: var(--font-co); overflow: hidden;
}
.alerts-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid var(--border);
  font-family: var(--font-hd); font-size: 12px; letter-spacing: 1px; color: var(--cyan);
}
.alerts-head-actions { display: flex; align-items: center; gap: 10px; }
.alerts-clear { background: none; border: 1px solid var(--border2); color: var(--text); font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
.alerts-clear:hover { border-color: var(--cyan); color: var(--cyan); }
.alerts-close { background: none; border: none; color: #888; font-size: 22px; cursor: pointer; line-height: 1; }
.alerts-close:hover { color: var(--pink); }
.alerts-filter { display: flex; align-items: center; gap: 8px; padding: 8px 14px; border-bottom: 1px solid var(--border); }
.af-chip { background: var(--bg3); border: 1px solid var(--border); color: var(--text); font-family: var(--font-hd); font-size: 9px; letter-spacing: 1px; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
.af-chip.active { background: var(--bg4); color: var(--cyan); border-color: var(--cyan-d); }
.af-counts { margin-left: auto; font-family: var(--font-co); font-size: 10px; color: var(--text); }
.alerts-body { overflow-y: auto; padding: 6px; }
.alert-row { display: flex; gap: 10px; padding: 10px; border-radius: 6px; border-left: 3px solid var(--border2); margin-bottom: 4px; }
.alert-row.critical { border-left-color: var(--pink); background: rgba(255,45,110,0.06); }
.alert-row.warning  { border-left-color: #ffbe0b; background: rgba(255,190,11,0.06); }
.alert-row.info     { border-left-color: var(--cyan); }
.alert-sev { font-size: 12px; }
.alert-msg { color: var(--textwh); font-size: 12px; }
.alert-sub { color: var(--text); font-size: 10px; margin-top: 2px; text-transform: uppercase; letter-spacing: 1px; }
.alerts-empty { padding: 24px; text-align: center; color: var(--text); font-size: 12px; }
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

.docker-led {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #0db7ed;
  margin-left: 6px;
  box-shadow: 0 0 5px #0db7ed;
  animation: pulse-docker 2s infinite alternate;
}
@keyframes pulse-docker {
  from { box-shadow: 0 0 2px #0db7ed; opacity: 0.6; }
  to { box-shadow: 0 0 10px #0db7ed; opacity: 1; }
}
</style>
